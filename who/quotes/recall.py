#!/usr/bin/env python3
"""How much of the by-eye reference (pilot_reference.json) each extractor's quotes contain.

usage: python3 quotes/recall.py [reference.json] [dir ...]
An anchor counts as caught when it lies wholly inside one quote.
"""
import glob, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))


def load(d):
    return {os.path.basename(p)[:-6].split("__")[-1]: {json.loads(l)["text"]: json.loads(l) for l in open(p) if '"error"' not in l}
            for p in sorted(glob.glob(os.path.join(d, "*.jsonl")))}


def caught(anchor, quotes):
    return any(q["start"] <= anchor["start"] and q["end"] >= anchor["end"] for q in quotes)


def score(ref, quotes_by_text):
    tot = core = got = gotcore = chars = length = 0
    miss = []
    for t, anchors in ref.items():
        r = quotes_by_text.get(int(t))
        if not r:
            continue
        chars += sum(q["end"] - q["start"] for q in merge(r["quotes"])); length += r["length"]
        for a in anchors:
            c = caught(a, r["quotes"]); tot += 1; got += c
            if a["core"]:
                core += 1; gotcore += c
                if not c:
                    miss.append("%s: %s" % (t, a["anchor"][:50]))
    return tot, got, core, gotcore, chars, length, miss


def merge(quotes):
    out = []
    for q in sorted(quotes, key=lambda x: x["start"]):
        if out and q["start"] <= out[-1]["end"] + 1:
            out[-1] = dict(out[-1], end=max(out[-1]["end"], q["end"]))
        else:
            out.append(dict(q))
    return out


def main():
    args = sys.argv[1:]
    refname = "pilot_reference.json"
    if args and args[0].endswith(".json"):
        refname, args = args[0], args[1:]
    ref = json.load(open(os.path.join(HERE, refname)))["texts"]
    dirs = args or [os.path.join(HERE, "extracted")]
    print("%-34s %5s  %-9s %-9s %s" % ("extractor", "texts", "all", "core", "kept % of text"))
    for d in dirs:
        E = load(d)
        for name, by in E.items():
            tot, got, core, gotcore, chars, length, miss = score(ref, by)
            n = sum(1 for t in ref if int(t) in by)
            print("%-34s %5d  %3d/%-5d %3d/%-5d %5.1f   missed core: %s" % (os.path.basename(d)[:12] + ":" + name, n, got, tot, gotcore, core, 100 * chars / max(1, length), "; ".join(miss[:6])))


if __name__ == "__main__":
    main()
