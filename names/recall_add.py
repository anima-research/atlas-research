#!/usr/bin/env python3
"""Append a recall check to recall.jsonl, stamping each name with the score it has now.

Reads JSON lines from stdin: {"text": id, "read_chars": n, "names": ["Name", ...],
"forms_missed": [...], "note": "..."}; a text with no name has an empty list.

usage: python3 recall_add.py --check 3 --pool all < new.jsonl
"""
import argparse, json, os, sqlite3, sys, time
from extract import norm

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--check", type=int, required=True); ap.add_argument("--pool", required=True)
a = ap.parse_args()
db = sqlite3.connect("file:%s?mode=ro" % os.path.join(HERE, "data", "names.db"), uri=True)
with open(os.path.join(HERE, "recall.jsonl"), "a", encoding="utf-8") as f:
    for line in sys.stdin:
        if not line.strip():
            continue
        d = json.loads(line)
        stamped = {}
        for name in d["names"]:
            r = db.execute("SELECT score FROM text_names WHERE text_id=? AND norm=?", (d["text"], norm(name))).fetchone()
            stamped[name] = r[0] if r else 0.0
        out = dict(check=a.check, date=time.strftime("%Y-%m-%d"), pool=a.pool, text=d["text"],
                   read_chars=d["read_chars"], names=stamped)
        for k in ("forms_missed", "note"):
            if d.get(k):
                out[k] = d[k]
        f.write(json.dumps(out, ensure_ascii=False) + "\n")
        print(d["text"], stamped)
