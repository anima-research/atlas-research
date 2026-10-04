"""Measure the two passes against what was read by eye, and write checks.json (read by the site).

    python3 check.py

1. The hand verdicts of the names study (../labels.jsonl): for each judged pattern hit, whether the
   first pass, or either pass, gave a label that equals it, contains it, or is contained in it.
2. Twelve words for those who look after something: texts (of the verdict texts) where the word
   occurs, and how many of them have a label holding it.
3. The ten texts marked by hand before any request (pilot_hand.json) against the first pass.
Needs out/ (the raw answers) and ../data/snapshot_r15.sqlite."""
import json, os, re, sqlite3, collections
HERE = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(HERE, *a)
VERDICTS = [("b", "name of a being"), ("p", "name of a place"), ("t", "thing or phenomenon"),
            ("s", "statement about naming"), ("x", "not a name")]
WORDS = ["keeper", "tender", "steward", "gardener", "caretaker", "custodian", "warden", "guardian",
         "shepherd", "curator", "maintainer", "cultivator"]

fold = lambda s: re.sub(r"^(the|a|an) ", "", re.sub(r"[*_\"“”‘’'#:.,]", "", s.lower()).strip())


def has(s, labels):
    L = [fold(x) for x in labels]
    return (s in L or any(re.search(r"(?<![a-z])" + re.escape(s) + r"(?![a-z])", l) for l in L)
            or any(l and re.search(r"(?<![a-z])" + re.escape(l) + r"(?![a-z])", s) for l in L))


def main():
    V = [json.loads(l) for l in open(P("..", "labels.jsonl"))]
    LQ, LI = collections.defaultdict(list), collections.defaultdict(list)
    for l in open(P("out", "verdict_luna_v2.jsonl")):
        r = json.loads(l); LQ[r["text"]] += [x["label"] for x in r["labels"]]
    n_lines = n_lines_labelled = 0
    for l in open(P("out", "verdict_items_v1.jsonl")):
        r = json.loads(l)
        got = {x["i"] for x in r["labels"]}
        n_lines += len(r["items"]); n_lines_labelled += len(got)
        for x in r["labels"]:
            LI[x["text"]].append(x["label"])
    tab = collections.defaultdict(collections.Counter)
    for v in V:
        s = fold(v["surface"]); a = has(s, LQ[v["text"]]); b = has(s, LI[v["text"]])
        c = tab[v["verdict"]]; c["n"] += 1; c["first"] += a; c["both"] += a or b
    verdicts = [dict(code=k, verdict=name, n=tab[k]["n"], first=tab[k]["first"], both=tab[k]["both"]) for k, name in VERDICTS]

    snap = sqlite3.connect("file:%s?mode=ro" % P("..", "data", "snapshot_r15.sqlite"), uri=True)
    ids = json.load(open(P("verdict_ids.json")))
    low = {t: [x.lower() for x in LQ[t] + LI[t]] for t in ids}
    words = []
    for w in WORDS:
        rx = re.compile(r"(?<![A-Za-z])%ss?(?![A-Za-z])" % w, re.I)
        n = held = 0
        for t in ids:
            if rx.search(snap.execute("SELECT text FROM texts WHERE id=?", (t,)).fetchone()[0]):
                n += 1; held += any(rx.search(l) for l in low[t])
        words.append(dict(word=w, texts=n, in_a_label=held))

    hand = json.load(open(P("pilot_hand.json")))
    f2 = lambda s: re.sub(r"^(the|a|an|its|their) ", "", s.lower().translate(str.maketrans("’‘", "''")).strip())
    pil = collections.Counter()
    for l in open(P("out", "pilot_luna_v2.jsonl")):
        r = json.loads(l)
        L = {f2(x["label"]) for x in r["labels"]}
        for g in hand[str(r["text"])]:
            for lab in g:
                h = f2(lab.lstrip("!")); hit = any(h == x or h in x or x in h for x in L)
                pil["marked"] += 1; pil["found"] += hit
                if not hit and lab.startswith("!"):
                    pil["missed_denials"] += 1
    out = dict(verdict_texts=len(ids), verdicts=verdicts, lines_sent=n_lines, lines_with_a_label=n_lines_labelled,
               words=words, pilot=dict(texts=len(hand) - 1, **pil))
    json.dump(out, open(P("checks.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
