#!/usr/bin/env python3
"""Print texts with the current hits marked inline, for reading by eye.
  [S: ...]  caught by a pattern of precision 0.8 or more      {w: ...}  only by lower ones
  <st: ...> statement about naming
usage: python3 show.py <id> [<id> ...] [--max 6000]
"""
import argparse, os, sqlite3
import patterns as P
HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("ids", nargs="+", type=int); ap.add_argument("--max", type=int, default=6000)
ap.add_argument("--rev", default="15")
a = ap.parse_args()
db = sqlite3.connect("file:%s?mode=ro" % os.path.join(HERE, "data", "names.db"), uri=True)
snap = sqlite3.connect("file:%s?mode=ro" % os.path.join(HERE, "data", "snapshot_r%s.sqlite" % a.rev), uri=True)
prec = dict(db.execute("SELECT id, precision FROM patterns WHERE status='active'"))
kind = {p["id"]: ("st" if p["yields"] == "statement" else "S" if (prec.get(p["id"]) or 0) >= 0.8 else "w") for p in P.PATTERNS}
for tid in a.ids:
    model, text = snap.execute("SELECT model, text FROM texts WHERE id=?", (tid,)).fetchone()
    ms = db.execute("SELECT start, end, pattern_id FROM mentions WHERE text_id=? ORDER BY start, end DESC", (tid,)).fetchall()
    lab = [None] * len(text)
    rank = {"S": 3, "w": 2, "st": 1}
    for s, e, pid in ms:
        k = kind[pid]
        if k == "st":
            continue
        for i in range(s, e):
            if lab[i] is None or rank[k] > rank[lab[i]]:
                lab[i] = k
    out, i, n = [], 0, min(len(text), a.max)
    while i < n:
        if lab[i] is None:
            out.append(text[i]); i += 1; continue
        j = i
        while j < n and lab[j] == lab[i]:
            j += 1
        out.append(("[S:%s]" if lab[i] == "S" else "{w:%s}") % text[i:j]); i = j
    print("\n=========== #%d %s len=%d%s" % (tid, model, len(text), " (cut at %d)" % a.max if len(text) > a.max else ""))
    print("".join(out))
