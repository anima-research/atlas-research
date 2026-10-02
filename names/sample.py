#!/usr/bin/env python3
"""Draw a seeded random sample of one pattern's hits, with context, for reading by eye.
The same (pattern, seed, n) always gives the same sample for the same names.db.

usage: python3 sample.py <pattern_id> [--n 30] [--seed 1] [--ctx 70] [--model substr]
"""
import argparse, os, random, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))


def draw(db, pattern, n, seed, model=None):
    q = "SELECT m.id, m.text_id, m.start, m.end, m.surface, c.model FROM mentions m JOIN text_cov c ON c.text_id=m.text_id WHERE m.pattern_id=?"
    args = [pattern]
    if model:
        q += " AND c.model LIKE ?"; args.append("%" + model + "%")
    rows = db.execute(q + " ORDER BY m.text_id, m.start", args).fetchall()
    rnd = random.Random("%s:%s" % (pattern, seed))
    return rnd.sample(rows, min(n, len(rows))), len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pattern"); ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", default="1"); ap.add_argument("--ctx", type=int, default=70)
    ap.add_argument("--model", default=None); ap.add_argument("--rev", default="15")
    a = ap.parse_args()
    db = sqlite3.connect("file:%s?mode=ro" % os.path.join(HERE, "data", "names.db"), uri=True)
    snap = sqlite3.connect("file:%s?mode=ro" % os.path.join(HERE, "data", "snapshot_r%s.sqlite" % a.rev), uri=True)
    rows, total = draw(db, a.pattern, a.n, a.seed, a.model)
    print("## %s  seed=%s  n=%d of %d" % (a.pattern, a.seed, len(rows), total))
    for i, (mid, tid, s, e, surf, model) in enumerate(rows):
        t = snap.execute("SELECT text FROM texts WHERE id=?", (tid,)).fetchone()[0]
        left = t[max(0, s - a.ctx):s].replace("\n", " / ")
        right = t[e:e + a.ctx].replace("\n", " / ")
        print("%2d #%d %s | %s«%s»%s" % (i, tid, model.split("/")[-1][:18], left, t[s:e].replace("\n", " / "), right))


if __name__ == "__main__":
    main()
