"""Publishing. Only human-approved clips go out, one post per clip per platform, capped per day."""
from __future__ import annotations

import time
from pathlib import Path

from . import db
from .config import Config


class DryRun:
    """Stand-in publisher: records what would be posted."""
    def __init__(self, platform: str):
        self.platform = platform

    def upload(self, account: str, path: str, title: str, caption: str) -> str:
        return f"dry-{self.platform}-{Path(path).stem}"


class YouTube:
    """Official YouTube Data API v3 upload.

    Needs one OAuth token file per channel (tokens/<handle>.json). Note: until your Google
    Cloud project passes YouTube's API audit, API uploads are forced to private.
    """
    platform = "youtube"

    def __init__(self, token_dir: str = "tokens"):
        self.token_dir = Path(token_dir)

    def upload(self, account: str, path: str, title: str, caption: str) -> str:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        creds = Credentials.from_authorized_user_file(str(self.token_dir / f"{account.lstrip('@')}.json"))
        yt = build("youtube", "v3", credentials=creds)
        body = {"snippet": {"title": title[:100], "description": caption, "categoryId": "20"},
                "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
        req = yt.videos().insert(part="snippet,status", body=body,
                                 media_body=MediaFileUpload(path, chunksize=-1, resumable=True))
        resp = None
        while resp is None:
            _, resp = req.next_chunk()
        return resp["id"]


def run(cfg: Config, con, publishers: dict, now: float | None = None) -> list[dict]:
    """Post approved clips to each of their brand's accounts, respecting daily caps."""
    now = now or time.time()
    done = []
    rows = con.execute("SELECT * FROM clips WHERE status='approved' ORDER BY score DESC").fetchall()
    for clip in rows:
        brand = cfg.brands.get(clip["brand"])
        if not brand:
            continue
        for platform, account in brand.accounts.items():
            pub = publishers.get(platform)
            if pub is None:
                continue
            if con.execute("SELECT 1 FROM posts WHERE clip_id=? AND platform=?",
                           (clip["id"], platform)).fetchone():
                continue                          # never repost the same clip on a platform
            if db.posts_today(con, account, platform, now) >= brand.daily_cap:
                continue                          # cap reached; picked up on a later run
            remote = pub.upload(account, clip["path"], clip["title"], clip["caption"])
            con.execute("INSERT INTO posts VALUES(?,?,?,?,?)", (clip["id"], platform, account, remote, now))
            con.commit()
            done.append({"clip": clip["id"], "platform": platform, "account": account, "id": remote})
        if all(con.execute("SELECT 1 FROM posts WHERE clip_id=? AND platform=?", (clip["id"], p)).fetchone()
               for p in brand.accounts if p in publishers):
            db.set_clip_status(con, clip["id"], "published")
    return done
