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

## Sensitivity

The microphone runs for the whole session and the last 5 seconds are always held in memory, so
each saved recording starts 5 seconds before the sound that set it off. **Maximum** saves
anything 4 dB above the room's background, even a single short sound; lower settings need a
louder, longer sound. While a session runs, the white line on the level bar is the trigger
point. Insights has a "Was it listening?" card for each night: how long the microphone was
really live, the loudest moment, and how many bumps were too short to keep.

## Stopping before your alarm

Turn on **Stop by itself at** and pick a time. At that time the session ends: the recording in
progress is saved, the microphone and the keep-screen-on lock are released, and the night is
closed for Insights. Set it a few minutes before your alarm.

## Transcripts and Insights

- **Recordings › Write out what I said** turns each recording into text with Whisper
  (transformers.js), running on the phone. The first use downloads the speech model from
  Hugging Face (about 40 MB for English, 80 MB for other languages); audio never leaves the
  phone. Recordings with no words in them are marked "No words heard". Once the model is on
  the phone, later nights are written out automatically when you tap Stop.
- **Insights** shows, per night: times you spoke, sounds recorded, time spent listening, the
  share of 5-minute windows with no sound, the longest quiet stretch, sounds by hour, what you
  said, and a 14-night trend. These come from sound alone, not from sleep stages.

Sleep talk is often mumbled, and the small model will get some of it wrong or invent a short
phrase for a noise. Play the recording when a transcript looks odd.

Transcription has not been run end to end: the test environment could not reach the model
download. Its failure path, the transcript clean-up and the Insights maths were checked.

Checked in desktop Chromium with a simulated microphone (trigger, pre-roll, save, playback).
Not yet run on an iPhone.
