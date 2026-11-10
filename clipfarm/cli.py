"""python -m clipfarm.cli <command>"""
from __future__ import annotations

import argparse
import json

from . import db, ingest, pipeline, publish, watch
from .config import Config


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="clipfarm")
    p.add_argument("--config", default="config/sources.json")
    p.add_argument("--db", default="data/clipfarm.db")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("watch", help="poll feeds, download + clip any new videos")
    pr = sub.add_parser("process", help="clip a local video file")
    pr.add_argument("source"); pr.add_argument("file"); pr.add_argument("--title", default="")
    pr.add_argument("--no-whisper", action="store_true")
    sub.add_parser("queue", help="list clips awaiting review")
    for name in ("approve", "reject"):
        s = sub.add_parser(name); s.add_argument("ids", nargs="+", type=int)
    pb = sub.add_parser("publish", help="post approved clips")
    pb.add_argument("--live", action="store_true", help="really upload (default is dry run)")
    a = p.parse_args(argv)

    cfg, con = Config.load(a.config), db.connect(a.db)
    if a.cmd == "watch":
        for v in watch.poll(cfg, con):
            path = ingest.download(cfg.sources[v["source"]], v["url"], "data/raw")
            ids = pipeline.process(cfg, con, v["source"], str(path), v["video_id"], v["title"])
            print(f"{v['video_id']} -> {len(ids)} clips queued for review")
    elif a.cmd == "process":
        vid = a.file.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        db.add_video(con, vid, a.source, a.title or vid, a.file, "")
        ids = pipeline.process(cfg, con, a.source, a.file, vid, a.title or vid, whisper=not a.no_whisper)
        print(f"{len(ids)} clips queued for review: {ids}")
    elif a.cmd == "queue":
        for r in con.execute("SELECT id,brand,score,start,end,title,path FROM clips WHERE status='pending_review'"):
            print(json.dumps(dict(r)))
    elif a.cmd in ("approve", "reject"):
        for i in a.ids:
            db.set_clip_status(con, i, "approved" if a.cmd == "approve" else "rejected")
    elif a.cmd == "publish":
        platforms = {pl for b in cfg.brands.values() for pl in b.accounts}
        pubs = {pl: publish.DryRun(pl) for pl in platforms}
        if a.live:
            pubs = {"youtube": publish.YouTube()}   # other platforms: add their official APIs here
        for d in publish.run(cfg, con, pubs):
            print(json.dumps(d))


if __name__ == "__main__":
    main()
