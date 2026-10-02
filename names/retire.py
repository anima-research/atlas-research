#!/usr/bin/env python3
"""Copy the current version of one or more patterns into patterns_retired.py, before the
pattern is changed in patterns.py.

usage: python3 retire.py --reason "what was wrong and what the next version does" id [id ...]
"""
import argparse, os
import patterns as P

HERE = os.path.dirname(os.path.abspath(__file__))
ORDER = ["id", "version", "round", "added", "tier", "tier_basis", "remark", "yields", "family", "regex",
         "flags", "stop", "mask", "reject", "max_words", "min_occ", "max_df", "origin", "what",
         "note", "retired_reason"]
ap = argparse.ArgumentParser()
ap.add_argument("ids", nargs="+"); ap.add_argument("--reason", required=True)
a = ap.parse_args()
cur = {p["id"]: p for p in P.PATTERNS}
have = {(p["id"], p["version"]) for p in P.RETIRED}
out = []
for pid in a.ids:
    d = dict(cur[pid])
    if (pid, d["version"]) in have:
        print("already retired: %s v%d" % (pid, d["version"])); continue
    d["retired_reason"] = a.reason
    out.append("    dict(")
    for k in ORDER:
        if d.get(k) not in (None, ""):
            out.append("        %s=%r," % (k, d[k]))
    out.append("    ),")
    print("retired: %s v%d" % (pid, d["version"]))
path = os.path.join(HERE, "patterns_retired.py")
src = open(path, encoding="utf-8").read().rstrip()
assert src.endswith("]")
open(path, "w", encoding="utf-8").write(src[:-1] + "\n".join(out) + "\n]\n")
