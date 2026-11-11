# SleepTalk (iOS)

An iPhone app that listens while you sleep and saves a recording only when it hears you talk.

**Status: written without a Mac. It has never been compiled or run on a device.** Expect to fix
a few build errors the first time you open it in Xcode, and treat the overnight behaviour
described below as the design, not a measured result.

## How it works

1. You tap **Start sleep session** at bedtime. The microphone is off at all other times.
2. During the session the app measures loudness about 12 times a second and tracks the room's
   background level. Audio is held in memory for 1.5 seconds and then dropped.
3. When a sound rises clearly above the background, the app writes a clip (including the 1.5 s
   before it) and stops 3 seconds after the sound ends.
4. Each clip is labelled by Apple's on-device sound classifier as talking, snoring or other.
   With **Keep only talking** on (the default), everything else is deleted.
5. In the morning, the **Recordings** tab lists clips by night, with play, share and delete.

Nothing leaves the phone; there is no account, server or analytics.

Settings: sensitivity (how far above the background a sound must be), a start delay so you are
not recorded while falling asleep, keep-only-talking, and keep-screen-on.

## Install on your iPhone

Needs a Mac with Xcode 16 or later and an iPhone on iOS 17 or later.

1. Open `SleepTalk.xcodeproj`.
2. Select the SleepTalk target › Signing & Capabilities, pick your team, and change the bundle
   identifier from `com.example.sleeptalk` to something of your own.
3. Plug in the iPhone, select it as the run destination, and press Run.

With a free Apple ID the app expires after 7 days and has to be re-run from Xcode.

If the project file will not open, create a new iOS App project in Xcode, drag the `SleepTalk`
folder into it, add the **Audio** background mode, and add a microphone usage description.

## Things to check on a real device

- **Surviving the night.** The app uses the audio background mode and, by default, keeps the
  screen on behind a black "Dim screen" view. Recent iOS versions are reported to be stricter
  about record-only apps in the background, so test a full night with the phone locked before
  turning **Keep screen on** off.
- **Classification in the background.** Apple's classifier is reported to fail for some apps
  while backgrounded. Clips that could not be analysed are kept as "Not yet analysed" and
  retried the next time the app is opened.
- **Sensitivity.** The thresholds in `AudioMonitor.swift` are first guesses. Quiet mumbling may
  need **High**; a noisy room may need **Low**.
- Keep the phone plugged in, microphone end towards you.

## What existing apps do

| App | Model | Notes |
| --- | --- | --- |
| Sleep Talk Recorder (MadInSweden) | Free + paid upgrade | The original; sound-triggered clips, nightly list, sharing |
| Sleepy – Sleep Talk Recorder | Free + in-app purchases | Records only when it detects noise |
| Sleep Tracker & Talk Recorder | $1.99 | Searchable talk, snore and noise events; Apple Health sync |
| Somnio, Dozuno | Free + in-app purchases | Snore and talk clips, sleep score, on-device storage |
| ShutEye, BetterSleep, Sleep Cycle | Subscription | Full sleep trackers where talk recording is one feature |
| Sleep Talking Recorder | $6.99 a week | Typical of the weekly-subscription clones |

The shared core is what this app implements: a manual bedtime start, a sound trigger, a start
delay, a sensitivity setting, and a morning list of clips. Left out for now: transcripts, sleep
scores, snore statistics, smart alarms, sleep sounds and Apple Health sync.
