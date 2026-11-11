import Foundation

/// Persists detected clips and decides which ones are worth keeping. Main thread only.
final class ClipStore: ObservableObject {
    @Published private(set) var clips: [Clip] = []

    static let keepOnlyTalkingKey = "keepOnlyTalking"

    static var documents: URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
    }

    static var clipsDirectory: URL {
        let dir = documents.appendingPathComponent("Clips", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir
    }

    private var indexURL: URL { Self.documents.appendingPathComponent("clips.json") }
    private var classifying = Set<UUID>()

    init() {
        UserDefaults.standard.register(defaults: [Self.keepOnlyTalkingKey: true])
        if let data = try? Data(contentsOf: indexURL),
           let saved = try? JSONDecoder().decode([Clip].self, from: data) {
            clips = saved.filter { FileManager.default.fileExists(atPath: $0.url.path) }
        }
    }

    struct Night: Identifiable {
        let id: Date
        let clips: [Clip]
    }

    var nights: [Night] {
        Dictionary(grouping: clips, by: \.night)
            .map { Night(id: $0.key, clips: $0.value.sorted { $0.date < $1.date }) }
            .sorted { $0.id > $1.id }
    }

    func ingest(_ clip: Clip) {
        clips.append(clip)
        save()
        classify(clip)
    }

    func delete(_ clip: Clip) {
        try? FileManager.default.removeItem(at: clip.url)
        clips.removeAll { $0.id == clip.id }
        save()
    }

    func classifyPending() {
        clips.filter { $0.kind == .unknown }.forEach(classify)
    }

    private func classify(_ clip: Clip) {
        guard !classifying.contains(clip.id) else { return }
        classifying.insert(clip.id)
        SoundClassifier.classify(url: clip.url) { [weak self] result in
            guard let self else { return }
            self.classifying.remove(clip.id)
            // nil = analysis could not run (e.g. app in background); retried on next launch.
            guard let result, let index = self.clips.firstIndex(where: { $0.id == clip.id }) else { return }
            let keepOnlyTalking = UserDefaults.standard.bool(forKey: Self.keepOnlyTalkingKey)
            if keepOnlyTalking && result.kind != .talking {
                self.delete(self.clips[index])
            } else {
                self.clips[index].kind = result.kind
                self.clips[index].confidence = result.confidence
                self.save()
            }
        }
    }

    private func save() {
        if let data = try? JSONEncoder().encode(clips) {
            try? data.write(to: indexURL, options: .atomic)
        }
    }
}
