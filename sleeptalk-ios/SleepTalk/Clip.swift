import Foundation

struct Clip: Codable, Identifiable, Equatable {
    enum Kind: String, Codable {
        case talking, snoring, other, unknown

        var label: String {
            switch self {
            case .talking: return "Talking"
            case .snoring: return "Snoring"
            case .other: return "Other sound"
            case .unknown: return "Not yet analysed"
            }
        }

        var symbol: String {
            switch self {
            case .talking: return "text.bubble.fill"
            case .snoring: return "zzz"
            case .other: return "waveform"
            case .unknown: return "questionmark.circle"
            }
        }
    }

    var id = UUID()
    var date: Date
    var duration: Double
    var peakDb: Float
    var fileName: String
    var kind: Kind = .unknown
    var confidence: Double = 0

    var url: URL { ClipStore.clipsDirectory.appendingPathComponent(fileName) }

    /// Clips before noon belong to the night that started the previous evening.
    var night: Date {
        Calendar.current.startOfDay(for: date.addingTimeInterval(-12 * 3600))
    }
}
