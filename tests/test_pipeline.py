"""End-to-end test on a synthetic 'stream': quiet baseline with two loud moments."""
import json
import subprocess

import pytest

from clipfarm import db, highlights, pipeline, publish, render, watch
from clipfarm.config import Config, LicenseError

FEED = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"
 xmlns:yt="http://www.youtube.com/xml/schemas/2015">
 <entry><yt:videoId>abc123</yt:videoId><title>GTA VI day 1</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=abc123"/>
  <published>2026-11-19T18:00:00+00:00</published></entry>
 <entry><yt:videoId>def456</yt:videoId><title>Heist gone wrong</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=def456"/>
  <published>2026-11-20T18:00:00+00:00</published></entry></feed>"""


@pytest.fixture(scope="session")
def stream(tmp_path_factory):
    """150 s 1080p landscape video; loud bursts at 40-48 s and 100-110 s."""
    out = tmp_path_factory.mktemp("v") / "stream.mp4"
    vol = "0.02+0.9*between(t,40,48)+0.9*between(t,100,110)"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1920x1080:r=30:d=150",
         "-f", "lavfi", "-i", "anoisesrc=d=150:c=pink:a=0.8",
         "-af", f"volume='{vol}':eval=frame", "-c:v", "libx264", "-preset", "ultrafast",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(out)], check=True)
    return str(out)


@pytest.fixture
def env(tmp_path):
    cfg_path = tmp_path / "sources.json"
    cfg_path.write_text(json.dumps({
        "brands": [{"name": "b1", "angle": "chaos", "daily_cap": 1,
                    "accounts": {"youtube": "@b1", "tiktok": "@b1"}}],
        "sources": [
            {"name": "mine", "license": "own", "brand": "b1", "credit": "@me", "channel_id": "UCmine"},
            {"name": "partner", "license": "clipping_program", "license_ref": "campaign-1", "brand": "b1"},
            {"name": "random", "license": "none", "brand": "b1", "channel_id": "UCrandom"}]}))
    return Config.load(cfg_path), db.connect(tmp_path / "t.db"), tmp_path


def test_highlights_find_the_loud_moments(stream):
    ws = highlights.find_windows(stream, top_n=5)
    assert len(ws) == 2
    assert any(w.start <= 40 and w.end >= 48 for w in ws)
    assert any(w.start <= 100 and w.end >= 110 for w in ws)
    assert all(15 <= w.end - w.start <= 45 for w in ws)


def test_render_is_vertical_short_with_captions(stream, tmp_path):
    words = [(41.0, 41.4, "no"), (41.5, 41.9, "way"), (42.0, 42.6, "bro")]
    out = render.render_short(stream, 34, 50, tmp_path / "c.mp4", credit="@me", words=words)
    info = render.probe(out)
    assert (info["width"], info["height"]) == (1080, 1920)
    assert 15.5 < info["duration"] < 16.5
    assert "NO WAY BRO" in (tmp_path / "c.ass").read_text()


def test_unlicensed_source_is_refused(env, stream):
    cfg, con, tmp = env
    with pytest.raises(LicenseError):
        pipeline.process(cfg, con, "random", stream, "v1", "t", out_dir=str(tmp))
    with pytest.raises(LicenseError):
        watch.poll(cfg, con, fetch=lambda cid: FEED)


def test_watcher_dedupes(env):
    cfg, con, _ = env
    del cfg.sources["random"]
    assert [v["video_id"] for v in watch.poll(cfg, con, fetch=lambda cid: FEED)] == ["abc123", "def456"]
    assert watch.poll(cfg, con, fetch=lambda cid: FEED) == []


def test_review_gate_caps_and_no_duplicates(env, stream):
    cfg, con, tmp = env
    ids = pipeline.process(cfg, con, "mine", stream, "v1", "Day one chaos", out_dir=str(tmp), whisper=False)
    assert len(ids) == 2
    pubs = {"youtube": publish.DryRun("youtube"), "tiktok": publish.DryRun("tiktok")}

    assert publish.run(cfg, con, pubs) == []            # nothing approved -> nothing posted
    for i in ids:
        db.set_clip_status(con, i, "approved")
    first = publish.run(cfg, con, pubs, now=1_000_000)
    assert len(first) == 2 and {d["platform"] for d in first} == {"youtube", "tiktok"}
    assert len({d["clip"] for d in first}) == 1          # daily_cap=1 per account per platform
    assert publish.run(cfg, con, pubs, now=1_000_100) == []          # cap still holds
    second = publish.run(cfg, con, pubs, now=1_000_000 + 90_000)     # next day: the other clip
    assert len(second) == 2 and {d["clip"] for d in second} != {d["clip"] for d in first}
    assert publish.run(cfg, con, pubs, now=1_000_000 + 200_000) == []  # each clip once per platform
