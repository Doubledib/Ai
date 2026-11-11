import Foundation
import SoundAnalysis

/// Labels a finished clip with Apple's built-in on-device sound classifier.
enum SoundClassifier {
    struct Result {
        let kind: Clip.Kind
        let confidence: Double
    }

    private static let talkLabels: Set<String> = [
        "speech", "whispering", "shout", "yell", "screaming", "babble", "chatter",
        "laughter", "giggling", "crying_sobbing", "humming", "singing",
    ]
    private static let minimumConfidence = 0.3

    /// Calls back on the main thread; nil means the analysis could not run.
    static func classify(url: URL, completion: @escaping (Result?) -> Void) {
        DispatchQueue.global(qos: .utility).async {
            let result = run(url: url)
            DispatchQueue.main.async { completion(result) }
        }
    }

    private static func run(url: URL) -> Result? {
        let observer = Observer()
        do {
            let analyzer = try SNAudioFileAnalyzer(url: url)
            let request = try SNClassifySoundRequest(classifierIdentifier: .version1)
            try analyzer.add(request, withObserver: observer)
            analyzer.analyze()
        } catch {
            return nil
        }
        guard !observer.failed, !observer.best.isEmpty else { return nil }

        let talk = observer.best.filter { talkLabels.contains($0.key) }.values.max() ?? 0
        let snore = observer.best["snoring"] ?? 0
        if talk >= minimumConfidence && talk >= snore {
            return Result(kind: .talking, confidence: talk)
        }
        if snore >= minimumConfidence {
            return Result(kind: .snoring, confidence: snore)
        }
        return Result(kind: .other, confidence: max(talk, snore))
    }

    private final class Observer: NSObject, SNResultsObserving {
        /// Highest confidence seen for each label across the whole clip.
        var best: [String: Double] = [:]
        var failed = false

        func request(_ request: SNRequest, didProduce result: SNResult) {
            guard let result = result as? SNClassificationResult else { return }
            for item in result.classifications where item.confidence > (best[item.identifier] ?? 0) {
                best[item.identifier] = item.confidence
            }
        }

        func request(_ request: SNRequest, didFailWithError error: Error) {
            failed = true
        }
    }
}
