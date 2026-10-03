#!/usr/bin/env python3
"""Second reader: draw a blind sample of hits that already carry a verdict, and record a
second reader's verdicts on them in agreement.jsonl. The first verdicts are not shown.

  python3 agree.py draw --n 200 --seed 1 --reader R      print the sample with contexts
  python3 agree.py record --seed 1 --reader R <verdicts>  one letter per hit, in printed order
"""
import argparse, json, os, random, sqlite3, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODES = "bptsxg"


def draw(n, seed):
    rows = [json.loads(l) for l in open(os.path.join(HERE, "labels.jsonl"), encoding="utf-8") if l.strip()]
    rnd = random.Random("agree:%s" % seed)
    return rnd.sample(rows, min(n, len(rows)))


ap = argparse.ArgumentParser()
ap.add_argument("cmd", choices=["draw", "record"]); ap.add_argument("verdicts", nargs="?")
ap.add_argument("--n", type=int, default=200); ap.add_argument("--seed", default="1")
ap.add_argument("--reader", required=True); ap.add_argument("--ctx", type=int, default=70)
ap.add_argument("--rev", default="15")
a = ap.parse_args()
rows = draw(a.n, a.seed)
if a.cmd == "draw":
    snap = sqlite3.connect("file:%s?mode=ro" % os.path.join(HERE, "data", "snapshot_r%s.sqlite" % a.rev), uri=True)
    for i, d in enumerate(rows):
        model, t = snap.execute("SELECT model, text FROM texts WHERE id=?", (d["text"],)).fetchone()
        s, e = d["start"], d["end"]
        left = t[max(0, s - a.ctx):s].replace("\n", " / "); right = t[e:e + a.ctx].replace("\n", " / ")
        print("%3d #%d %s [%s] | %s«%s»%s" % (i, d["text"], model.split("/")[-1][:18], d["pattern"], left, t[s:e].replace("\n", " / "), right))
else:
    v = (a.verdicts or "").replace(" ", "")
    if len(v) != len(rows):
        sys.exit("verdicts: %d, sample: %d" % (len(v), len(rows)))
    if set(v) - set(CODES):
        sys.exit("unknown verdict code")
    with open(os.path.join(HERE, "agreement.jsonl"), "a", encoding="utf-8") as f:
        for d, code in zip(rows, v):
            f.write(json.dumps(dict(reader=a.reader, seed=a.seed, text=d["text"], pattern=d["pattern"],
                                    start=d["start"], end=d["end"], surface=d["surface"],
                                    first=d["verdict"], second=code), ensure_ascii=False) + "\n")
    print("%d verdicts recorded for reader %s" % (len(v), a.reader))
