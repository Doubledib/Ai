"""Download a source video. Only runs for sources with a recorded license."""
from __future__ import annotations

from pathlib import Path

from .config import Source


def download(src: Source, url: str, out_dir: str | Path) -> Path:
    src.require_license()
    import yt_dlp  # lazy: only needed for remote sources

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    opts = {
        "outtmpl": str(out_dir / "%(id)s.%(ext)s"),
        "format": "bv*[height<=1080]+ba/b[height<=1080]",
        "merge_output_format": "mp4",
        "quiet": True,
        "noprogress": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return Path(ydl.prepare_filename(info)).with_suffix(".mp4")
