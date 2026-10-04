#!/usr/bin/env python3
"""Ask a model to quote, from a text, the passages that say who lives there.

Every quote is looked for in the text, and what is stored is always the text's own stretch,
never the model's string. A quote is found exactly; or after folding spaces, quote marks,
dashes and emphasis marks; or, failing that, by aligning its words with the text's words
(at least 80% of them, in order). A quote not found in any of these ways is dropped and counted.

usage: OPENROUTER_API_KEY=... python3 quotes/extract.py --model <openrouter id> --file ids.json [--workers 8]
writes quotes/extracted/<model>.jsonl, one line per text
"""
import argparse, concurrent.futures as cf, json, os, re, sqlite3, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PROMPT = open(os.path.join(HERE, "extract_prompt.md")).read()
KINDS = ["is", "not", "part", "name", "answer", "place", "who", "does", "visitor"]
FOLD = {"‘": "'", "’": "'", "“": '"', "”": '"', "—": "-", "–": "-", "‑": "-", " ": " ", "…": "..."}


def fold(s):
    """Fold a string for loose matching; returns the folded string and, for each folded
    character, the index in the original it came from."""
    out, idx = [], []
    prev_space = False
    for i, ch in enumerate(s):
        ch = FOLD.get(ch, ch)
        if ch in "*_`":
            continue
        for c in ch:
            if c.isspace():
                if prev_space:
                    continue
                c = " "; prev_space = True
            else:
                prev_space = False
            out.append(c.lower()); idx.append(i)
    return "".join(out), idx


WORDS = re.compile(r"[^\W_]+(?:['’][^\W_]+)*")


def fuzzy(text, quote, min_share=0.8):
    """Find the stretch of the text a quote was taken from when it does not match as written:
    align the quote's words with the text's words and take the text from the first aligned
    word to the last. Accepted when at least `min_share` of the quote's words are aligned, in
    order, and the stretch is not much longer than the quote. Returns (start, end, share) or None."""
    import difflib
    tw = [(m.group(0).lower(), m.start(), m.end()) for m in WORDS.finditer(text)]
    qw = [m.group(0).lower() for m in WORDS.finditer(quote)]
    if len(qw) < 4:
        return None
    # narrow the search to the region around the quote's rarest long words
    tl = [w for w, _, _ in tw]
    first = {}
    for i, w in enumerate(tl):
        first.setdefault(w, []).append(i)
    seeds = sorted((len(first[w]), w) for w in set(qw) if w in first and len(w) > 4)
    if not seeds:
        return None
    best = None
    for _, w in seeds[:3]:
        for i in first[w][:5]:
            lo, hi = max(0, i - len(qw) - 5), min(len(tl), i + len(qw) + 5)
            sm = difflib.SequenceMatcher(None, qw, tl[lo:hi], autojunk=False)
            blocks = [b for b in sm.get_matching_blocks() if b.size]
            if not blocks:
                continue
            got = sum(b.size for b in blocks)
            a, z = lo + blocks[0].b, lo + blocks[-1].b + blocks[-1].size - 1
            share = got / len(qw)
            if share >= min_share and (z - a + 1) <= 1.3 * len(qw) + 3 and (best is None or share > best[2]):
                best = (tw[a][1], tw[z][2], share)
    if best is None:
        return None
    s, e, share = best
    # widen to whole sentences: a fuzzy match seldom starts and ends on the right word
    while s > 0 and text[s - 1] not in ".!?\n":
        s -= 1
    while s < e and text[s] in " \t":
        s += 1
    m = re.compile(r"[.!?\n]").search(text, max(s, e - 1))
    e = m.end() if m else len(text)
    while e < len(text) and text[e] in "*\"”’)":
        e += 1
    return s, e, round(share, 2)


def locate(text, quote, folded=None):
    """(start, end, how) of the quote in the text, or None. how: 'exact', 'folded' or 'fuzzy'."""
    q = quote.strip()
    if not q:
        return None
    a = text.find(q)
    if a >= 0:
        return a, a + len(q), "exact"
    ft, idx = folded or fold(text)
    fq, _ = fold(q)
    fq = fq.strip()
    if len(fq) < 8:
        return None
    b = ft.find(fq)
    if b >= 0:
        return idx[b], idx[b + len(fq) - 1] + 1, "folded"
    f = fuzzy(text, q)
    if f:
        return f[0], f[1], "fuzzy"
    return None


def ask(model, text, key, tries=4):
    body = json.dumps({"model": model, "temperature": 0, "max_tokens": 16000,
                       "messages": [{"role": "user", "content": PROMPT + "\n\nTHE TEXT\n\n" + text}]}).encode()
    err = None
    for t in range(tries):
        try:
            req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                                         headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=300))
            if "choices" not in r:
                err = str(r)[:200]; time.sleep(3 * (t + 1)); continue
            out = r["choices"][0]["message"]["content"] or ""
            m = re.search(r"[\[{].*[\]}]", out, re.S)
            ans = json.loads(m.group(0))
            quotes = ans["quotes"] if isinstance(ans, dict) else ans
            u = r.get("usage", {})
            return quotes, u.get("prompt_tokens"), u.get("completion_tokens"), u.get("cost")
        except Exception as e:  # noqa
            err = repr(e)[:200]; time.sleep(3 * (t + 1))
    return {"error": err}, None, None, None


def check(text, quotes):
    """Locate every quote; return (kept, dropped). Kept quotes carry the text's own characters."""
    folded = fold(text)
    kept, dropped = [], []
    for q in quotes:
        if isinstance(q, str):          # a bare quote, no kind: kinds are assigned later, not by the extractor
            q = {"kind": "", "quote": q}
        if not isinstance(q, dict) or q.get("kind") not in KINDS + [""] or not isinstance(q.get("quote"), str):
            dropped.append({"given": q, "why": "malformed"}); continue
        loc = locate(text, q["quote"], folded)
        if not loc:
            dropped.append({"kind": q["kind"], "given": q["quote"], "why": "not in the text"}); continue
        a, b, how = loc
        row = {"kind": q["kind"], "start": a, "end": b, "quote": text[a:b], "match": how}
        if how == "fuzzy":
            row["given"] = q["quote"]      # what the model returned; what is kept is the text's own stretch
        kept.append(row)
    kept.sort(key=lambda x: x["start"])
    return kept, dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True); ap.add_argument("--file", required=True)
    ap.add_argument("--workers", type=int, default=8); ap.add_argument("--rev", default="15")
    ap.add_argument("--prompt", default="extract_prompt.md"); ap.add_argument("--out", default="extracted")
    a = ap.parse_args()
    global PROMPT
    PROMPT = open(os.path.join(HERE, a.prompt)).read()
    key = os.environ["OPENROUTER_API_KEY"]
    snap = sqlite3.connect("file:%s?mode=ro" % os.path.join(HERE, "..", "..", "names", "data", "snapshot_r%s.sqlite" % a.rev), uri=True)
    ids = json.load(open(a.file))
    os.makedirs(os.path.join(HERE, a.out), exist_ok=True)
    out = os.path.join(HERE, a.out, a.model.replace("/", "__") + ".jsonl")
    done = {json.loads(l)["text"] for l in open(out) if '"error"' not in l} if os.path.exists(out) else set()
    todo = [i for i in ids if i not in done]
    texts = {i: snap.execute("SELECT text FROM texts WHERE id=?", (i,)).fetchone()[0] for i in todo}
    cost = 0.0; n = 0
    with cf.ThreadPoolExecutor(a.workers) as ex, open(out, "a") as f:
        fut = {ex.submit(ask, a.model, texts[i], key): i for i in todo}
        for fu in cf.as_completed(fut):
            i = fut[fu]; quotes, pi, po, c = fu.result()
            if isinstance(quotes, dict) and "error" in quotes:
                f.write(json.dumps({"text": i, "model": a.model, **quotes}) + "\n"); f.flush(); continue
            kept, dropped = check(texts[i], quotes)
            f.write(json.dumps({"text": i, "model": a.model, "length": len(texts[i]), "quotes": kept, "dropped": dropped,
                                "tokens_in": pi, "tokens_out": po}, ensure_ascii=False) + "\n"); f.flush()
            cost += c or 0; n += 1
            if n % 500 == 0:
                print("  %d/%d, cost so far $%.2f" % (n, len(todo), cost), file=sys.stderr, flush=True)
    print("%s: %d texts, cost $%.3f" % (a.model, n, cost), file=sys.stderr)


if __name__ == "__main__":
    main()
