# SleepTalk (web)

A single-page version of SleepTalk that runs in Safari on an iPhone, so no Mac or Xcode is
needed. Everything is in `index.html`; there is nothing to build.

It needs to be opened from an `https://` address (the microphone is blocked otherwise). Any
static host works, for example GitHub Pages serving this folder.

## How it differs from the native app in `../sleeptalk-ios`

- **The screen has to stay on.** iOS turns a web page's microphone off when the phone is locked
  or another app is opened. The page keeps the screen awake and offers a black "Dim screen"
  view; keep the phone plugged in.
- **It saves any sound, not only talking.** Loudness is measured in the voice band, which
  ignores hum and rumble, but snoring and coughs are recorded too. The native app's
  talking/snoring labels are not available in a browser.
- Recordings are WAV files kept in the browser's storage on the phone. Use **Save** to keep one
  in Files; Safari can clear site storage that has not been visited for a while.

Checked in desktop Chromium with a simulated microphone (trigger, pre-roll, save, playback).
Not yet run on an iPhone.
