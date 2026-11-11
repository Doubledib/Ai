import SwiftUI
import UIKit

struct ContentView: View {
    var body: some View {
        TabView {
            TonightView()
                .tabItem { Label("Tonight", systemImage: "moon.stars.fill") }
            RecordingsView()
                .tabItem { Label("Recordings", systemImage: "waveform") }
        }
    }
}

// MARK: - Tonight

struct TonightView: View {
    @EnvironmentObject private var monitor: AudioMonitor
    @EnvironmentObject private var store: ClipStore
    @EnvironmentObject private var player: ClipPlayer

    @AppStorage("sensitivity") private var sensitivity = AudioMonitor.Sensitivity.medium.rawValue
    @AppStorage("delayMinutes") private var delayMinutes = 15
    @AppStorage("keepAwake") private var keepAwake = true
    @AppStorage(ClipStore.keepOnlyTalkingKey) private var keepOnlyTalking = true
    @State private var dimmed = false

    private var clipsTonight: Int {
        guard let start = monitor.sessionStart else { return 0 }
        return store.clips.filter { $0.date >= start }.count
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    VStack(spacing: 16) {
                        Image(systemName: monitor.isCapturing ? "record.circle.fill" : "moon.zzz.fill")
                            .font(.system(size: 56))
                            .foregroundStyle(monitor.isCapturing ? .red : .indigo)
                        Text(statusText)
                            .font(.headline)
                            .multilineTextAlignment(.center)
                        if monitor.isRunning {
                            LevelMeter(levelDb: monitor.levelDb)
                            Text("\(clipsTonight) clip\(clipsTonight == 1 ? "" : "s") saved tonight")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                        Button(action: toggle) {
                            Text(monitor.isRunning ? "Stop" : "Start sleep session")
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.borderedProminent)
                        .controlSize(.large)
                        .tint(monitor.isRunning ? .red : .indigo)
                        if monitor.isRunning {
                            Button("Dim screen") { dimmed = true }
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 8)
                } footer: {
                    if let error = monitor.errorMessage {
                        Text(error).foregroundStyle(.red)
                    }
                }

                Section {
                    Picker("Sensitivity", selection: $sensitivity) {
                        ForEach(AudioMonitor.Sensitivity.allCases) { level in
                            Text(level.label).tag(level.rawValue)
                        }
                    }
                    Picker("Start listening after", selection: $delayMinutes) {
                        Text("Right away").tag(0)
                        ForEach([15, 30, 45, 60], id: \.self) { Text("\($0) min").tag($0) }
                    }
                    Toggle("Keep only talking", isOn: $keepOnlyTalking)
                    Toggle("Keep screen on overnight", isOn: $keepAwake)
                } header: {
                    Text("Settings")
                } footer: {
                    Text("The microphone is only on during a sleep session. Sound is checked on this iPhone and thrown away unless something is heard; nothing leaves the device. Keep the phone plugged in.")
                }
                .disabled(monitor.isRunning)
            }
            .navigationTitle("SleepTalk")
        }
        .fullScreenCover(isPresented: $dimmed) {
            DimView(clips: clipsTonight)
        }
        .onChange(of: monitor.isRunning) { _, running in
            UIApplication.shared.isIdleTimerDisabled = running && keepAwake
            if !running { dimmed = false }
        }
    }

    private var statusText: String {
        guard monitor.isRunning else { return "Start a session when you go to bed" }
        if let armedAt = monitor.armedAt, armedAt > Date() {
            return "Listening starts at \(armedAt.formatted(date: .omitted, time: .shortened))"
        }
        return monitor.isCapturing ? "Recording a sound…" : "Listening — nothing is being saved"
    }

    private func toggle() {
        if monitor.isRunning {
            monitor.stop()
        } else {
            player.stop()
            monitor.start(
                sensitivity: AudioMonitor.Sensitivity(rawValue: sensitivity) ?? .medium,
                delayMinutes: delayMinutes
            )
        }
    }
}

struct LevelMeter: View {
    let levelDb: Float

    var body: some View {
        // Map -70…-10 dB onto the bar.
        ProgressView(value: Double(min(max((levelDb + 70) / 60, 0), 1)))
            .tint(.indigo)
            .animation(.linear(duration: 0.1), value: levelDb)
    }
}

/// A black screen for the night; on OLED iPhones this draws almost no power.
struct DimView: View {
    let clips: Int
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()
            TimelineView(.periodic(from: .now, by: 30)) { context in
                VStack(spacing: 8) {
                    Text(context.date.formatted(date: .omitted, time: .shortened))
                        .font(.system(size: 44, weight: .thin))
                    Text("\(clips) saved · tap to wake")
                        .font(.footnote)
                }
                .foregroundStyle(Color(white: 0.25))
            }
        }
        .contentShape(Rectangle())
        .onTapGesture { dismiss() }
        .statusBarHidden()
        .persistentSystemOverlays(.hidden)
    }
}

// MARK: - Recordings

struct RecordingsView: View {
    @EnvironmentObject private var store: ClipStore
    @EnvironmentObject private var monitor: AudioMonitor
    @EnvironmentObject private var player: ClipPlayer

    var body: some View {
        NavigationStack {
            List {
                if monitor.isRunning {
                    Text("Stop the sleep session to play recordings.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
                ForEach(store.nights) { night in
                    Section("Night of \(night.id.formatted(date: .abbreviated, time: .omitted))") {
                        ForEach(night.clips) { clip in
                            ClipRow(clip: clip)
                                .swipeActions {
                                    Button("Delete", role: .destructive) {
                                        if player.playingID == clip.id { player.stop() }
                                        store.delete(clip)
                                    }
                                }
                        }
                    }
                }
            }
            .overlay {
                if store.clips.isEmpty {
                    ContentUnavailableView(
                        "No recordings yet",
                        systemImage: "moon.zzz",
                        description: Text("Anything you say in your sleep will show up here.")
                    )
                }
            }
            .navigationTitle("Recordings")
        }
    }
}

struct ClipRow: View {
    let clip: Clip
    @EnvironmentObject private var monitor: AudioMonitor
    @EnvironmentObject private var player: ClipPlayer

    var body: some View {
        HStack(spacing: 12) {
            Button {
                player.toggle(clip)
            } label: {
                Image(systemName: player.playingID == clip.id ? "stop.circle.fill" : "play.circle.fill")
                    .font(.title)
            }
            .buttonStyle(.plain)
            .foregroundStyle(.indigo)
            .disabled(monitor.isRunning)

            VStack(alignment: .leading, spacing: 2) {
                Text(clip.date.formatted(date: .omitted, time: .standard))
                    .font(.body.monospacedDigit())
                Label(detail, systemImage: clip.kind.symbol)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            ShareLink(item: clip.url) {
                Image(systemName: "square.and.arrow.up")
            }
            .buttonStyle(.plain)
            .foregroundStyle(.secondary)
        }
    }

    private var detail: String {
        "\(clip.kind.label) · \(Int(clip.duration.rounded())) s"
    }
}
