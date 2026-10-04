#!/usr/bin/env python3
"""The heading a quote stands under, found by script (no model).

A heading is a line that is a Markdown heading (# ...), or a line that is wholly in bold or
italics, or a bold phrase that opens a line and is followed by text ("**The Weavers** They ...").
`under(text)` returns a function giving, for a position in the text, the nearest heading above it.

    python3 quotes/headings.py            counts over the corpus, and names found in quote or heading
"""
import bisect, json, os, re, sqlite3
HERE = os.path.dirname(os.path.abspath(__file__))
LINE = re.compile(r"^[ \t]*(?:#{1,6}[ \t]+(?P<h>.+?)[ \t#]*|(?:[-*•][ \t]+|\d+[.)][ \t]+)?(?P<b>\*\*[^*\n]{2,120}\*\*|__[^_\n]{2,120}__|\*[^*\n]{2,120}\*)[ \t]*[:.]?[ \t]*(?P<rest>.*))$", re.M)


def headings(text):
    out = []
    for m in LINE.finditer(text):
        if m.group("h"):
            title = m.group("h")
        else:
            title = m.group("b")
            if m.group("rest") and not title.startswith(("**", "__")):
                continue            # an italic phrase opening a sentence is not a heading
        title = re.sub(r"[*_#`]+", "", title).strip(" :.")
        if title:
            out.append((m.start(), title))
    return out


def under(text):
    hs = headings(text)
    starts = [s for s, _ in hs]

    def f(pos):
        i = bisect.bisect_right(starts, pos) - 1
        return hs[i][1] if i >= 0 else ""
    return f


def main():
    snap = sqlite3.connect("file:%s?mode=ro" % os.path.join(HERE, "..", "..", "names", "data", "snapshot_r15.sqlite"), uri=True)
    ndb = sqlite3.connect("file:%s?mode=ro" % os.path.join(HERE, "..", "..", "names", "data", "names.db"), uri=True)
    names = {}
    for t, n in ndb.execute("SELECT text_id, norm FROM text_names WHERE score >= 0.8 AND body_occ > 0"):
        names.setdefault(t, []).append(n.lower())
    nq = nh = texts_h = tot = inq = inqh = 0
    for line in open(os.path.join(HERE, "corpus", "anthropic__claude-sonnet-5.5.jsonl")):
        r = json.loads(line)
        if "quotes" not in r:
            continue
        text = snap.execute("SELECT text FROM texts WHERE id=?", (r["text"],)).fetchone()[0]
        f = under(text)
        hs = [f(q["start"]) for q in r["quotes"]]
        nq += len(hs); nh += sum(1 for h in hs if h); texts_h += bool(headings(text))
        blob = " \n ".join(q["quote"] for q in r["quotes"]).lower()
        blobh = blob + " \n " + " \n ".join(set(hs)).lower()
        for n in names.get(r["text"], []):
            pat = re.compile(r"(?<![a-z])" + re.escape(n) + r"(?![a-z])")
            tot += 1; inq += pat.search(blob) is not None; inqh += pat.search(blobh) is not None
    print("quotes %d; under a heading %d (%.1f%%); texts with any heading %d" % (nq, nh, 100 * nh / nq, texts_h))
    print("names of the names study (score 0.8+, in the body): %d; inside a quote %d (%.1f%%); inside a quote or its heading %d (%.1f%%)" % (tot, inq, 100 * inq / tot, inqh, 100 * inqh / tot))


if __name__ == "__main__":
    main()
