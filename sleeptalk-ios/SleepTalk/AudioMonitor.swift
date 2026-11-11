import Accelerate
import AVFoundation

/// Listens to the microphone during a sleep session and writes a clip only when a sound rises
/// above the room's background level. Everything else is dropped from memory after ~1.5 s.
final class AudioMonitor: ObservableObject {
    enum Sensitivity: Int, CaseIterable, Identifiable {
        case low, medium, high

        var id: Int { rawValue }

        var label: String {
            switch self {
            case .low: return "Low"
            case .medium: return "Medium"
            case .high: return "High"
            }
        }

        /// How far above the background noise a sound must be to start a clip.
        var marginDb: Float {
            switch self {
            case .low: return 18
            case .medium: return 12
            case .high: return 7
            }
        }
    }

    @Published private(set) var isRunning = false
    @Published private(set) var isCapturing = false
    @Published private(set) var levelDb: Float = -80
    @Published private(set) var sessionStart: Date?
    @Published private(set) var armedAt: Date?
    @Published var errorMessage: String?

    /// Called on the main thread for every clip that was kept.
    var onClip: ((Clip) -> Void)?

    // Tuning
    private let preRollSeconds = 1.5
    private let hangoverSeconds = 3.0
    private let maxClipSeconds = 300.0
    private let minLoudSeconds = 0.4
    private let warmUpSeconds = 4.0
    private let absoluteFloorDb: Float = -55

    private let engine = AVAudioEngine()
    private let queue = DispatchQueue(label: "sleeptalk.audio")
    private var observers: [NSObjectProtocol] = []

    // State below is only touched on `queue`.
    private var marginDb: Float = 12
    private var armTime = Date.distantFuture
    private var noiseFloorDb: Float = -50
    private var loudStreak = 0
    private var preRoll: [AVAudioPCMBuffer] = []
    private var preRollDuration = 0.0
    private var file: AVAudioFile?
    private var clipURL: URL?
    private var clipStart = Date()
    private var clipDuration = 0.0
    private var loudDuration = 0.0
    private var silenceDuration = 0.0
    private var peakDb: Float = -80

    // MARK: - Session control (main thread)

    func start(sensitivity: Sensitivity, delayMinutes: Int) {
        guard !isRunning else { return }
        AVAudioApplication.requestRecordPermission { [weak self] granted in
            DispatchQueue.main.async {
                guard let self else { return }
                if granted {
                    self.begin(sensitivity: sensitivity, delayMinutes: delayMinutes)
                } else {
                    self.errorMessage = "Microphone access is off. Enable it in Settings › SleepTalk."
                }
            }
        }
    }

    func stop() {
        guard isRunning else { return }
        observers.forEach { NotificationCenter.default.removeObserver($0) }
        observers = []
        engine.inputNode.removeTap(onBus: 0)
        engine.stop()
        queue.sync { finishClip() }
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        isRunning = false
        isCapturing = false
        sessionStart = nil
        armedAt = nil
        levelDb = -80
    }

    private func begin(sensitivity: Sensitivity, delayMinutes: Int) {
        let armed = Date().addingTimeInterval(max(Double(delayMinutes) * 60, warmUpSeconds))
        queue.sync {
            marginDb = sensitivity.marginDb
            armTime = armed
            noiseFloorDb = -50
            loudStreak = 0
            preRoll = []
            preRollDuration = 0
        }
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.record, mode: .default)
            try session.setActive(true)
            try startEngine()
        } catch {
            errorMessage = "Could not start listening: \(error.localizedDescription)"
            return
        }
        observe()
        errorMessage = nil
        sessionStart = Date()
        armedAt = armed
        isRunning = true
    }

    private func startEngine() throws {
        let input = engine.inputNode
        let format = input.outputFormat(forBus: 0)
        guard format.sampleRate > 0, format.channelCount > 0 else {
            throw NSError(domain: "SleepTalk", code: 1,
                          userInfo: [NSLocalizedDescriptionKey: "No microphone input available."])
        }
        input.removeTap(onBus: 0)
        input.installTap(onBus: 0, bufferSize: 4096, format: format) { [weak self] buffer, _ in
            guard let self, let copy = Self.copy(buffer) else { return }
            self.queue.async { self.process(copy) }
        }
        engine.prepare()
        try engine.start()
    }

    /// Phone calls, alarms and route changes stop the engine; bring it back afterwards.
    private func observe() {
        let center = NotificationCenter.default
        observers.append(center.addObserver(
            forName: AVAudioSession.interruptionNotification, object: nil, queue: .main
        ) { [weak self] note in
            guard let self,
                  let raw = note.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt,
                  let type = AVAudioSession.InterruptionType(rawValue: raw) else { return }
            if type == .began {
                self.queue.sync { self.finishClip() }
            } else {
                self.restart()
            }
        })
        observers.append(center.addObserver(
            forName: .AVAudioEngineConfigurationChange, object: engine, queue: .main
        ) { [weak self] _ in
            self?.restart()
        })
    }

    private func restart() {
        guard isRunning else { return }
        queue.sync {
            finishClip()
            preRoll = []
            preRollDuration = 0
        }
        do {
            try AVAudioSession.sharedInstance().setActive(true)
            try startEngine()
        } catch {
            errorMessage = "Listening was interrupted and could not resume: \(error.localizedDescription)"
        }
    }

    // MARK: - Detection (audio queue)

    private func process(_ buffer: AVAudioPCMBuffer) {
        let seconds = Double(buffer.frameLength) / buffer.format.sampleRate
        let db = Self.level(of: buffer)
        let isLoud = db > max(noiseFloorDb + marginDb, absoluteFloorDb)

        if file == nil {
            // Follow the room's background level: drop quickly, rise slowly.
            noiseFloorDb += (db - noiseFloorDb) * (db < noiseFloorDb ? 0.2 : 0.005)

            preRoll.append(buffer)
            preRollDuration += seconds
            while preRollDuration > preRollSeconds, let first = preRoll.first {
                preRollDuration -= Double(first.frameLength) / first.format.sampleRate
                preRoll.removeFirst()
            }

            loudStreak = (isLoud && Date() >= armTime) ? loudStreak + 1 : 0
            if loudStreak >= 2 {
                startClip(format: buffer.format)
            }
        } else {
            write(buffer)
            clipDuration += seconds
            peakDb = max(peakDb, db)
            if isLoud {
                loudDuration += seconds
                silenceDuration = 0
            } else {
                silenceDuration += seconds
            }
            if silenceDuration >= hangoverSeconds {
                finishClip()
            } else if clipDuration >= maxClipSeconds {
                // A constant new noise (fan, rain): accept it as the new background.
                noiseFloorDb = db
                finishClip()
            }
        }

        let capturing = file != nil
        DispatchQueue.main.async {
            guard self.isRunning else { return }
            self.levelDb = db
            if self.isCapturing != capturing { self.isCapturing = capturing }
        }
    }

    private func startClip(format: AVAudioFormat) {
        let start = Date().addingTimeInterval(-preRollDuration)
        let name = "clip-\(Int(start.timeIntervalSince1970 * 1000)).m4a"
        let url = ClipStore.clipsDirectory.appendingPathComponent(name)
        let settings: [String: Any] = [
            AVFormatIDKey: kAudioFormatMPEG4AAC,
            AVSampleRateKey: format.sampleRate,
            AVNumberOfChannelsKey: format.channelCount,
            AVEncoderBitRateKey: 64_000,
        ]
        do {
            file = try AVAudioFile(forWriting: url, settings: settings,
                                   commonFormat: format.commonFormat,
                                   interleaved: format.isInterleaved)
        } catch {
            loudStreak = 0
            return
        }
        clipURL = url
        clipStart = start
        clipDuration = preRollDuration
        loudDuration = 0
        silenceDuration = 0
        peakDb = -80
        loudStreak = 0
        preRoll.forEach(write)
        preRoll = []
        preRollDuration = 0
    }

    private func write(_ buffer: AVAudioPCMBuffer) {
        try? file?.write(from: buffer)
    }

    private func finishClip() {
        guard file != nil, let url = clipURL else { return }
        file = nil // closes the file
        clipURL = nil
        guard loudDuration >= minLoudSeconds else {
            // A click or bump, not worth keeping.
            try? FileManager.default.removeItem(at: url)
            return
        }
        let clip = Clip(date: clipStart, duration: clipDuration, peakDb: peakDb,
                        fileName: url.lastPathComponent)
        DispatchQueue.main.async { self.onClip?(clip) }
    }

    // MARK: - Helpers

    private static func level(of buffer: AVAudioPCMBuffer) -> Float {
        guard let data = buffer.floatChannelData, buffer.frameLength > 0 else { return -80 }
        var rms: Float = 0
        vDSP_rmsqv(data[0], 1, &rms, vDSP_Length(buffer.frameLength))
        return max(20 * log10(max(rms, 1e-7)), -80)
    }

    /// The engine reuses tap buffers, so keep our own copy.
    private static func copy(_ buffer: AVAudioPCMBuffer) -> AVAudioPCMBuffer? {
        guard let source = buffer.floatChannelData,
              let copy = AVAudioPCMBuffer(pcmFormat: buffer.format, frameCapacity: buffer.frameLength),
              let target = copy.floatChannelData else { return nil }
        copy.frameLength = buffer.frameLength
        // Non-interleaved: one plane per channel. Interleaved: a single plane holding all channels.
        let planes = buffer.format.isInterleaved ? 1 : Int(buffer.format.channelCount)
        let samplesPerPlane = Int(buffer.frameLength)
            * (buffer.format.isInterleaved ? Int(buffer.format.channelCount) : 1)
        for plane in 0..<planes {
            memcpy(target[plane], source[plane], samplesPerPlane * MemoryLayout<Float>.size)
        }
        return copy
    }
}
