"""Detect new uploads by polling each source's public YouTube Atom feed (no API key needed)."""
from __future__ import annotations

import urllib.request
import xml.etree.ElementTree as ET

from . import db
from .config import Config

FEED = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}


def parse_feed(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    out = []
    for e in root.findall("a:entry", NS):
        vid = e.findtext("yt:videoId", namespaces=NS)
        if not vid:
            continue
        link = e.find("a:link", NS)
        out.append({
            "video_id": vid,
            "title": e.findtext("a:title", default="", namespaces=NS),
            "url": link.get("href") if link is not None else f"https://www.youtube.com/watch?v={vid}",
            "published": e.findtext("a:published", default="", namespaces=NS),
        })
    return out


def fetch_feed(channel_id: str, timeout: int = 20) -> str:
    with urllib.request.urlopen(FEED.format(channel_id), timeout=timeout) as r:
        return r.read().decode("utf-8")


def poll(cfg: Config, con, fetch=fetch_feed) -> list[dict]:
    """Return videos not seen before, for licensed sources only."""
    fresh = []
    for src in cfg.sources.values():
        if not src.channel_id:
            continue
        src.require_license()
        for v in parse_feed(fetch(src.channel_id)):
            if db.add_video(con, v["video_id"], src.name, v["title"], v["url"], v["published"]):
                fresh.append({**v, "source": src.name})
    return fresh
