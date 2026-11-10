"""One video in -> rendered clips sitting in the review queue."""
from __future__ import annotations

from pathlib import Path

from . import ai, db, highlights, render
from .config import Config


def process(cfg: Config, con, source_name: str, video_path: str, video_id: str, video_title: str,
            out_dir: str = "data/clips", top_n: int = 5, whisper: bool = True) -> list[int]:
    src = cfg.sources[source_name]
    src.require_license()
    brand = cfg.brands.get(src.brand)
    windows = highlights.find_windows(video_path, top_n=top_n)
    words = highlights.transcribe(video_path) if (whisper and windows) else []
    highlights.attach_text(windows, words)
    ids = []
    for i, w in enumerate(windows):
        meta = ai.package(w.text, src.credit, video_title, src.brand, brand.angle if brand else "")
        if not meta.get("keep", True):
            continue
        out = Path(out_dir) / f"{video_id}_{i:02d}.mp4"
        render.render_short(video_path, w.start, w.end, out, credit=src.credit, words=words)
        ids.append(db.add_clip(con, video_id=video_id, source=src.name, brand=src.brand,
                               start=w.start, end=w.end, score=w.score,
                               title=meta["title"], caption=meta["caption"], path=str(out)))
    con.execute("UPDATE videos SET status='clipped' WHERE video_id=?", (video_id,))
    con.commit()
    return ids
