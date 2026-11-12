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

## Sorting recordings by sound

Every recording is labelled on the phone by YAMNet, a small sound-recognition model that ships
with the app in `vendor/` (no download at run time): talking, voice sound, snoring, breathing,
cough or sneeze, fart/burp/hiccup, or other noise. Sorting runs by itself after a session and
when the app opens. The Recordings tab can show one kind at a time, and only recordings sorted
as talking are sent to the speech-to-text step.

Dog barks get their own label too. Recordings are played back and saved louder than they were
captured: each one is lifted until its loudest moments are near full volume (up to 80 times),
which also raises the background hiss. The stored originals are not changed.

The **Loudness of each recording** graph draws one bar per recording in time order; tap a bar
to bring that recording up with Play, or use **Jump to the loudest**. The dB figures are
relative to the microphone's quietest level, not calibrated sound pressure.

The audio is stored apart from the list of recordings, so opening the app no longer loads every
recording into memory (this is what made the app crash with a few hundred recordings).

## Stopping before your alarm

Turn on **Stop by itself at** and pick a time. At that time the session ends: the recording in
progress is saved, the microphone and the keep-screen-on lock are released, and the night is
closed for Insights. Set it a few minutes before your alarm.

## Transcripts and Insights

- **Recordings › Write out what I said** turns each recording into text with Whisper
  (transformers.js), running on the phone. The first use downloads the speech model from
  Hugging Face (about 40 MB for English, 80 MB for other languages); audio never leaves the
  phone. Only recordings sorted as talking are written out. Once the model is on
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
