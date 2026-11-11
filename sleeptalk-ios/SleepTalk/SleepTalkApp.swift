import SwiftUI

@main
struct SleepTalkApp: App {
    @StateObject private var store = ClipStore()
    @StateObject private var monitor = AudioMonitor()
    @StateObject private var player = ClipPlayer()
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(store)
                .environmentObject(monitor)
                .environmentObject(player)
                .preferredColorScheme(.dark)
                .onAppear {
                    monitor.onClip = { [weak store] clip in store?.ingest(clip) }
                }
                .onChange(of: scenePhase) { _, phase in
                    // Sound classification can be refused while backgrounded; catch up here.
                    if phase == .active { store.classifyPending() }
                }
        }
    }
}
