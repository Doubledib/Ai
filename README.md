# clipfarm

Automated short-form clip pipeline for licensed gaming footage: watch channels for new uploads,
find the exciting moments, render vertical shorts with captions and credit, hold them for review,
then publish across a brand's accounts.

The business plan this supports is in [docs/BUSINESS_PLAN.md](docs/BUSINESS_PLAN.md).

## Setup

```bash
pip install -r requirements.txt        # also needs ffmpeg on PATH
cp config/sources.example.json config/sources.json   # then edit
export ANTHROPIC_API_KEY=...           # optional: AI titles/captions/filtering
```

Every source needs a `license` (`own`, `clipping_program` or `written_permission`) and, unless it
is your own footage, a `license_ref` pointing at the proof. Sources without one are refused.

## Use

```bash
python -m clipfarm.cli process my-own-gameplay session.mp4 --title "Day one"   # local file
python -m clipfarm.cli watch            # poll feeds, download and clip new uploads
python -m clipfarm.cli queue            # clips awaiting review
python -m clipfarm.cli approve 1 2      # or: reject 3
python -m clipfarm.cli publish          # dry run; add --live to upload to YouTube
```

Cron for hands-off running:

```
*/10 * * * *  cd /srv/clipfarm && python -m clipfarm.cli watch
0 * * * *     cd /srv/clipfarm && python -m clipfarm.cli publish --live
```

Publishing rules enforced in code: only approved clips, one post per clip per platform, and a
per-account daily cap.

## Tests

```bash
python -m pytest -q tests
```

The suite builds a synthetic 150 s "stream" with two loud moments and checks that both are found,
that renders come out 1080x1920 with captions, that unlicensed sources are refused, that the
watcher de-duplicates, and that the review gate, daily cap and no-repost rules hold.

Not covered by tests, because they need network access or credentials: live feed polling and
yt-dlp downloads, Whisper transcription, Claude titling, and real uploads.
