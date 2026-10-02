#!/usr/bin/env python3
"""Record verdicts on a sample drawn by sample.py. The verdicts are one character per
sampled hit, in the order sample.py printed them:

  b  name of a being, a kind of beings, or an individual
  p  name of a place
  t  coined name of a thing, practice, phenomenon or concept
  s  (statement patterns only) a statement about the inhabitants' name
  x  not a name: emphasis, a section title, an ordinary word, a clause
  g  the text itself is not prose (broken generation)

Verdicts are appended to labels.jsonl, keyed by text id and character span, so they stay
attached to the same hit when a pattern is later changed.

usage: python3 label.py <pattern_id> <verdicts> [--n 30] [--seed 1] [--round 1]
"""
import argparse, json, os, sqlite3, sys
from sample import draw, HERE

ap = argparse.ArgumentParser()
ap.add_argument("pattern"); ap.add_argument("verdicts")
ap.add_argument("--n", type=int, default=30); ap.add_argument("--seed", default="1")
ap.add_argument("--round", type=int, default=1); ap.add_argument("--model", default=None)
a = ap.parse_args()
v = a.verdicts.replace(" ", "")
db = sqlite3.connect("file:%s?mode=ro" % os.path.join(HERE, "data", "names.db"), uri=True)
rows, total = draw(db, a.pattern, a.n, a.seed, a.model)
if len(v) != len(rows):
    sys.exit("verdicts: %d, sample: %d" % (len(v), len(rows)))
if set(v) - set("bptsxg"):
    sys.exit("unknown verdict code")
path = os.path.join(HERE, "labels.jsonl")
have = set()
if os.path.exists(path):
    for l in open(path):
        d = json.loads(l); have.add((d["pattern"], d["text"], d["start"], d["end"]))
n = 0
with open(path, "a", encoding="utf-8") as f:
    for (mid, tid, s, e, surf, model), code in zip(rows, v):
        if (a.pattern, tid, s, e) in have:
            continue
        f.write(json.dumps(dict(pattern=a.pattern, text=tid, start=s, end=e, surface=surf,
                                verdict=code, round=a.round, seed=a.seed), ensure_ascii=False) + "\n")
        n += 1
print("%s: %d verdicts recorded" % (a.pattern, n))
