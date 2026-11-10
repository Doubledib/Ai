"""SQLite state: seen videos, clips awaiting review, and what was posted where."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos(
  video_id TEXT PRIMARY KEY, source TEXT, title TEXT, url TEXT, published TEXT,
  status TEXT DEFAULT 'new');
CREATE TABLE IF NOT EXISTS clips(
  id INTEGER PRIMARY KEY, video_id TEXT, source TEXT, brand TEXT,
  start REAL, end REAL, score REAL, title TEXT, caption TEXT, path TEXT,
  status TEXT DEFAULT 'pending_review', created REAL);
CREATE TABLE IF NOT EXISTS posts(
  clip_id INTEGER, platform TEXT, account TEXT, remote_id TEXT, posted_at REAL,
  UNIQUE(clip_id, platform));
"""


def connect(path: str | Path) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def add_video(con, video_id, source, title, url, published) -> bool:
    cur = con.execute(
        "INSERT OR IGNORE INTO videos(video_id,source,title,url,published) VALUES(?,?,?,?,?)",
        (video_id, source, title, url, published))
    con.commit()
    return cur.rowcount == 1


def add_clip(con, **f) -> int:
    f.setdefault("created", time.time())
    cols = ",".join(f)
    cur = con.execute(f"INSERT INTO clips({cols}) VALUES({','.join('?' * len(f))})", tuple(f.values()))
    con.commit()
    return cur.lastrowid


def set_clip_status(con, clip_id: int, status: str) -> None:
    con.execute("UPDATE clips SET status=? WHERE id=?", (status, clip_id))
    con.commit()


def posts_today(con, account: str, platform: str, now: float | None = None) -> int:
    since = (now or time.time()) - 86400
    return con.execute(
        "SELECT COUNT(*) FROM posts WHERE account=? AND platform=? AND posted_at>?",
        (account, platform, since)).fetchone()[0]
