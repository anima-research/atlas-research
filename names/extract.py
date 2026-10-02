#!/usr/bin/env python3
"""Run every pattern in patterns.py over every creature text of a snapshot and write
the results to data/names.db. The database is rebuilt from scratch on each run:

    snapshot (frozen texts) + patterns.py + labels.jsonl + readings.jsonl  ->  names.db

usage:
    python3 extract.py --rev 15                    rebuild names.db
    python3 extract.py --rev 15 --record "note"    rebuild and append a line to rounds.jsonl
"""
import argparse, hashlib, json, os, re, sqlite3, sys, time
from collections import Counter, defaultdict
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import patterns as P

FLAG = {"m": re.M, "i": re.I}


def compile_patterns():
    out = []
    for p in P.PATTERNS:
        f = 0
        for ch in p.get("flags", ""):
            f |= FLAG[ch]
        p = dict(p)
        p["_reject"] = re.compile(p["reject"]) if p.get("reject") else None
        out.append((p, re.compile(p["regex"], f)))
    return out


_ART = re.compile(r"^(?:the|a|an)\s+", re.I)
_EDGE = " \t\r\n*_\"'`“”‘’:;,.—–-()[]"


def clean(surface):
    """The captured string with markup, edge punctuation and a leading article removed."""
    s = surface.replace("’", "'").replace("‘", "'")
    s = re.sub(r"\s+", " ", s).strip(_EDGE)
    s = _ART.sub("", s).strip(_EDGE)
    if s.endswith("'s"):
        s = s[:-2]
    return s


def norm(surface):
    return clean(surface).casefold()


COMPILED = None
STOPS = {k: set(v) for k, v in P.STOPLISTS.items()}
MASKS = {k: re.compile(v, re.M) for k, v in P.MASKS.items()}
FUNCTION_WORDS = set(("the of and a to in is it that are as with for its not they their but "
                      "by from this or on at be an which have has was").split())
_TOK = re.compile(r"[A-Za-z']+")


def text_flag(text, tagged):
    """Why a text is left out of the counts, or '' if it is counted.

    `tagged` is the latest status the corpus taggers recorded for the text, if any
    (ok / broken / refusal / off-topic). Where a tagger said the text is not a creature
    description, that is the flag. Otherwise two checks are made here: the text is
    empty, or under 15% of its words are common English function words (ordinary prose
    has a third or more; the texts under 15% that were looked at were runs of unrelated
    tokens)."""
    if tagged and tagged != "ok":
        return tagged
    if len(text.strip()) < 50:
        return "empty"
    toks = _TOK.findall(text)
    if not toks:
        return "empty"
    share = sum(1 for w in toks if w.lower() in FUNCTION_WORDS) / float(len(toks))
    return "not prose (word check)" if share < 0.15 else ""


DF = {}          # word -> share of texts that contain it (set in each worker)
_WORD = re.compile(r"[a-z][a-z'\u2019-]*")


def init_worker(df):
    global DF
    DF = df


def doc_freq(snap, digest):
    """Share of texts that contain each word (lower-cased), cached per snapshot."""
    path = os.path.join(HERE, "data", "df_%s.json" % digest[:16])
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    c, n = Counter(), 0
    for (text,) in snap.execute("SELECT text FROM texts"):
        c.update(set(_WORD.findall(text.lower()))); n += 1
    df = {w: round(k / float(n), 5) for w, k in c.items() if k >= 3}
    json.dump(df, open(path, "w", encoding="utf-8"))
    return df


def occurrences(low, n):
    """How many times the string n occurs in the lower-cased text as a whole word or phrase."""
    return len(re.findall(r"(?<![a-z])" + re.escape(n) + r"(?![a-z])", low))


def scan(row):
    global COMPILED
    if COMPILED is None:
        COMPILED = compile_patterns()
    tid, text = row
    found = []
    masked = {}
    low = None
    occ = {}
    seen_st = set()
    for p, rx in COMPILED:
        stop = STOPS.get(p.get("stop") or "", ())
        mw = p.get("max_words")
        rej = p.get("_reject")
        src = text
        if p.get("mask"):
            if p["mask"] not in masked:
                masked[p["mask"]] = MASKS[p["mask"]].sub(lambda m: " " * len(m.group(0)), text)
            src = masked[p["mask"]]
        for m in rx.finditer(src):
            if p["yields"] == "statement":
                # the hit is the sentence around the matched phrase
                s, e = m.span()
                while s > 0 and text[s - 1] not in ".!?\n":
                    s -= 1
                while e < len(text) and text[e] not in ".!?\n":
                    e += 1
                if e < len(text) and text[e] != "\n":
                    e += 1
                while s < e and text[s] in " \t":
                    s += 1
                if (p["id"], s) in seen_st:
                    continue
                seen_st.add((p["id"], s))
                surf = text[s:e].strip()
                if surf:
                    found.append((tid, p["id"], s, e, surf, ""))
                continue
            g = "name"
            if m.group("name") is None:
                g = "name2"
            surf = m.group(g)
            if not surf:
                continue
            n = norm(surf)
            if not n or n in stop:
                continue
            if rej is not None and rej.search(clean(surf)):
                continue
            if mw and len(n.split()) > mw:
                continue
            if not re.search(r"[a-z]", n):
                continue
            if p.get("max_df") and " " not in n and DF.get(n, 0) > p["max_df"]:
                continue
            if p.get("min_occ"):
                if low is None:
                    low = text.lower().replace("\u2019", "'")
                if n not in occ:
                    occ[n] = occurrences(low, n)
                if occ[n] < p["min_occ"]:
                    continue
            s, e = m.span(g)
            found.append((tid, p["id"], s, e, surf, n))
    return found


def content_digest(con):
    h = hashlib.sha256()
    for tid, text in con.execute("SELECT id, text FROM texts ORDER BY id"):
        h.update(str(tid).encode()); h.update(b"\0")
        h.update(text.encode("utf-8")); h.update(b"\0")
    return h.hexdigest()


def load_jsonl(name):
    path = os.path.join(HERE, name)
    if not os.path.exists(path):
        return []
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rev", required=True)
    ap.add_argument("--record", default=None, help="append this run to rounds.jsonl with a note")
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()

    snap_path = os.path.join(HERE, "data", "snapshot_r%s.sqlite" % a.rev)
    snap = sqlite3.connect("file:%s?mode=ro" % snap_path, uri=True)
    release = dict(snap.execute("SELECT key, value FROM release"))
    t0 = time.time()
    digest = content_digest(snap)
    rows = snap.execute("SELECT id, text FROM texts ORDER BY id").fetchall()
    meta = {r[0]: (r[1], r[2], r[3]) for r in snap.execute(
        "SELECT t.id, t.model, length(t.text), t.place_id FROM texts t")}
    print("texts: %d   content sha256: %s" % (len(rows), digest[:16]), file=sys.stderr)

    df = doc_freq(snap, digest)
    with Pool(a.jobs, initializer=init_worker, initargs=(df,)) as pool:
        mentions = [m for chunk in pool.imap(scan, rows, chunksize=200) for m in chunk]
    print("mentions: %d  (%.0fs)" % (len(mentions), time.time() - t0), file=sys.stderr)

    out_path = os.path.join(HERE, "data", "names.db")
    tmp = out_path + ".tmp"
    if os.path.exists(tmp):
        os.remove(tmp)
    db = sqlite3.connect(tmp)
    db.executescript("""
    CREATE TABLE run (key TEXT PRIMARY KEY, value TEXT);
    CREATE TABLE patterns (
      id TEXT, version INTEGER, round INTEGER, added TEXT, tier TEXT, yields TEXT,
      family TEXT, regex TEXT, flags TEXT, stop TEXT, max_words INTEGER,
      origin_text INTEGER, origin_excerpt TEXT, what TEXT, note TEXT,
      status TEXT, retired_reason TEXT, mask TEXT, reject TEXT, tier_basis TEXT,
      min_occ INTEGER, max_df REAL);
    CREATE TABLE recall (chk INTEGER, date TEXT, pool TEXT, text_id INTEGER, read_chars INTEGER,
      name TEXT, caught TEXT, caught_now TEXT, forms_missed TEXT, note TEXT);
    CREATE TABLE pattern_eval (
      pattern_id TEXT PRIMARY KEY, n_read INTEGER, n_being INTEGER, n_place INTEGER,
      n_thing INTEGER, n_statement INTEGER, n_not INTEGER, n_broken INTEGER,
      n_gone INTEGER, n_gone_not INTEGER);
    CREATE TABLE stoplists (name TEXT, word TEXT);
    CREATE TABLE mentions (
      id INTEGER PRIMARY KEY, text_id INTEGER, pattern_id TEXT, start INTEGER,
      end INTEGER, surface TEXT, norm TEXT);
    CREATE TABLE text_names (
      text_id INTEGER, norm TEXT, display TEXT, n_mentions INTEGER, patterns TEXT,
      tier TEXT, first_pos INTEGER, occurrences INTEGER, in_place_text INTEGER,
      PRIMARY KEY (text_id, norm));
    CREATE TABLE text_cov (
      text_id INTEGER PRIMARY KEY, model TEXT, length INTEGER,
      n_strict INTEGER, n_wide INTEGER, n_names_strict INTEGER, n_names_wide INTEGER,
      n_statements INTEGER, covered INTEGER, flag TEXT, all_in_place INTEGER, tagged TEXT);
    CREATE TABLE names (
      norm TEXT PRIMARY KEY, display TEXT, n_texts INTEGER, n_texts_strict INTEGER,
      n_texts_new INTEGER, n_models INTEGER, n_models_strict INTEGER, n_mentions INTEGER,
      patterns TEXT, top_models TEXT, df REAL);
    CREATE TABLE pattern_model (pattern_id TEXT, model TEXT, n_mentions INTEGER, n_texts INTEGER);
    CREATE TABLE readings (round INTEGER, text_id INTEGER, basis TEXT, saw TEXT, note TEXT);
    CREATE TABLE labels (text_id INTEGER, pattern_id TEXT, start INTEGER, end INTEGER,
      surface TEXT, verdict TEXT, referent TEXT, note TEXT, round INTEGER);
    CREATE TABLE rounds (round INTEGER, date TEXT, note TEXT, stats TEXT);
    """)

    for k, v in release.items():
        db.execute("INSERT INTO run VALUES (?,?)", ("release_" + k, v))
    db.execute("INSERT INTO run VALUES ('content_sha256', ?)", (digest,))
    db.execute("INSERT INTO run VALUES ('built_at', ?)", (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),))
    src = open(os.path.join(HERE, "patterns.py"), "rb").read()
    db.execute("INSERT INTO run VALUES ('patterns_sha256', ?)", (hashlib.sha256(src).hexdigest(),))

    for status, plist in (("active", P.PATTERNS), ("retired", P.RETIRED)):
        for p in plist:
            db.execute("INSERT INTO patterns VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                p["id"], p["version"], p["round"], p["added"], p["tier"], p["yields"],
                p["family"], p["regex"], p.get("flags", ""), p.get("stop"),
                p.get("max_words"), p["origin"]["text"], p["origin"]["excerpt"],
                p["what"], p.get("note", ""), status, p.get("retired_reason"),
                p.get("mask"), p.get("reject"), p.get("tier_basis"), p.get("min_occ"), p.get("max_df")))
    for name, words in P.STOPLISTS.items():
        db.executemany("INSERT INTO stoplists VALUES (?,?)", [(name, w) for w in words])

    db.executemany("INSERT INTO mentions (text_id, pattern_id, start, end, surface, norm) "
                   "VALUES (?,?,?,?,?,?)", mentions)

    tier = {p["id"]: p["tier"] for p in P.PATTERNS}
    yields = {p["id"]: p["yields"] for p in P.PATTERNS}
    texts = dict(rows)
    places = {}
    for pid, ptext in snap.execute("SELECT id, text FROM places"):
        places[pid] = ptext.casefold()

    per_text = defaultdict(lambda: defaultdict(list))
    cov = defaultdict(lambda: dict(n_strict=0, n_wide=0, n_statements=0))
    pm_m, pm_t = Counter(), defaultdict(set)
    for tid, pid, s, e, surf, n in mentions:
        model = meta[tid][0]
        pm_m[(pid, model)] += 1
        pm_t[(pid, model)].add(tid)
        if yields[pid] == "statement":
            cov[tid]["n_statements"] += 1
            continue
        per_text[tid][n].append((pid, s, surf))
        cov[tid]["n_strict" if tier[pid] == "strict" else "n_wide"] += 1

    name_rows, agg = [], defaultdict(lambda: dict(texts=set(), models=Counter(), n=0,
                                                   disp=Counter(), sdisp=Counter(), pats=set(),
                                                   strict=0, new=0, smodels=set()))
    names_strict, names_wide, names_new = Counter(), Counter(), Counter()
    tagged = {}
    for tid, st in snap.execute("SELECT text_id, status FROM status ORDER BY tagged_at, rowid"):
        if st in ("ok", "broken", "refusal", "off-topic"):
            tagged[tid] = st          # the latest tagging that says something about the text
    flags = {tid: text_flag(texts[tid], tagged.get(tid)) for tid in meta}
    for tid, byname in per_text.items():
        text = texts[tid]
        low = None
        place = places.get(meta[tid][2], "")
        for n, hits in byname.items():
            disp = Counter(clean(h[2]) for h in hits).most_common(1)[0][0]
            pats = sorted(set(h[0] for h in hits))
            is_strict = any(tier[p] == "strict" for p in pats)
            if low is None:
                low = text.casefold()
            occ = low.count(n)
            in_place = 1 if n in place else 0
            name_rows.append((tid, n, disp, len(hits), ",".join(pats),
                              "strict" if is_strict else "wide",
                              min(h[1] for h in hits), occ, in_place))
            (names_strict if is_strict else names_wide)[tid] += 1
            if is_strict and not in_place:
                names_new[tid] += 1
            if flags[tid]:
                continue
            g = agg[n]
            g["texts"].add(tid); g["models"][meta[tid][0]] += 1; g["n"] += len(hits)
            g["disp"][disp] += 1; g["pats"].update(pats)
            if is_strict:
                g["strict"] += 1; g["sdisp"][disp] += 1; g["smodels"].add(meta[tid][0])
                if not in_place:
                    g["new"] += 1
    db.executemany("INSERT INTO text_names VALUES (?,?,?,?,?,?,?,?,?)", name_rows)

    for tid, (model, length, _place) in meta.items():
        c = cov[tid]
        db.execute("INSERT INTO text_cov VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
            tid, model, length, c["n_strict"], c["n_wide"], names_strict[tid],
            names_wide[tid], c["n_statements"], 1 if names_strict[tid] else 0, flags[tid],
            1 if names_strict[tid] and not names_new[tid] else 0, tagged.get(tid, "")))
    for n, g in agg.items():
        top = ", ".join("%s %d" % (m.split("/")[-1], k) for m, k in g["models"].most_common(4))
        disp = (g["sdisp"] or g["disp"]).most_common(1)[0][0]
        db.execute("INSERT INTO names VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
            n, disp, len(g["texts"]), g["strict"], g["new"], len(g["models"]),
            len(g["smodels"]), g["n"], ",".join(sorted(g["pats"])), top,
            df.get(n) if " " not in n else None))
    db.executemany("INSERT INTO pattern_model VALUES (?,?,?,?)",
                   [(pid, model, k, len(pm_t[(pid, model)])) for (pid, model), k in pm_m.items()])

    # Recall checks: names seen by eye in texts read whole. `caught` is what was true when
    # the text was read; `caught_now` is recomputed against the current patterns.
    for r in load_jsonl("recall.jsonl"):
        mine = per_text.get(r["text"], {})
        for name, caught in r["names"].items():
            n = norm(name)
            hits = mine.get(n)
            now = "missed" if not hits else "strict" if any(tier[h[0]] == "strict" for h in hits) else "wide"
            db.execute("INSERT INTO recall VALUES (?,?,?,?,?,?,?,?,?,?)", (
                r["check"], r["date"], r.get("pool", "covered"), r["text"], r["read_chars"], name,
                caught, now, json.dumps(r.get("forms_missed", [])), r.get("note", "")))
        if not r["names"]:
            db.execute("INSERT INTO recall VALUES (?,?,?,?,?,?,?,?,?,?)", (
                r["check"], r["date"], r.get("pool", "covered"), r["text"], r["read_chars"], None,
                None, None, json.dumps(r.get("forms_missed", [])), r.get("note", "")))
    for r in load_jsonl("readings.jsonl"):
        db.execute("INSERT INTO readings VALUES (?,?,?,?,?)", (
            r["round"], r["text"], r.get("basis", ""), json.dumps(r.get("saw", [])), r.get("note", "")))
    for l in load_jsonl("labels.jsonl"):
        db.execute("INSERT INTO labels VALUES (?,?,?,?,?,?,?,?,?)", (
            l["text"], l["pattern"], l["start"], l["end"], l["surface"], l["verdict"],
            l.get("referent", ""), l.get("note", ""), l.get("round")))

    # A verdict stays attached to a hit as long as the pattern still captures a span
    # that overlaps the span that was read.
    live = defaultdict(list)
    for tid, pid, s, e, surf, n in mentions:
        live[(pid, tid)].append((s, e))
    ev = defaultdict(Counter)
    for l in load_jsonl("labels.jsonl"):
        pid = l["pattern"]
        if any(s < l["end"] and e > l["start"] for s, e in live.get((pid, l["text"]), ())):
            ev[pid][l["verdict"]] += 1
        else:
            ev[pid]["gone"] += 1
            if l["verdict"] in "xg":
                ev[pid]["gone_not"] += 1
    for pid, c in ev.items():
        db.execute("INSERT INTO pattern_eval VALUES (?,?,?,?,?,?,?,?,?,?)", (
            pid, sum(c[k] for k in "bptsxg"), c["b"], c["p"], c["t"], c["s"], c["x"], c["g"],
            c["gone"], c["gone_not"]))

    ok = [t for t in meta if not flags[t]]
    n_texts = len(meta)
    stats = dict(
        texts=n_texts, mentions=len(mentions), patterns=len(P.PATTERNS),
        strict_patterns=sum(1 for p in P.PATTERNS if p["tier"] == "strict"),
        flagged=n_texts - len(ok),
        untagged=sum(1 for t in meta if t not in tagged),
        covered=sum(1 for t in ok if names_strict[t]),
        covered_all_in_place=sum(1 for t in ok if names_strict[t] and not names_new[t]),
        wide_only=sum(1 for t in ok if not names_strict[t] and names_wide[t]),
        nothing=sum(1 for t in ok if not names_strict[t] and not names_wide[t]),
        distinct_names=len(agg),
        distinct_names_strict=sum(1 for g in agg.values() if g["strict"]), statements=sum(c["n_statements"] for c in cov.values()),
        content_sha256=digest, revision=release.get("corpus_revision"))
    if a.record is not None:
        # one line per round; recording a round again replaces its line
        rnd = max(p["round"] for p in P.PATTERNS)
        keep = [r for r in load_jsonl("rounds.jsonl") if r["round"] != rnd]
        keep.append(dict(round=rnd, date=time.strftime("%Y-%m-%d"), note=a.record, stats=stats))
        with open(os.path.join(HERE, "rounds.jsonl"), "w", encoding="utf-8") as f:
            for r in sorted(keep, key=lambda r: r["round"]):
                f.write(json.dumps(r) + "\n")
    for r in load_jsonl("rounds.jsonl"):
        db.execute("INSERT INTO rounds VALUES (?,?,?,?)", (
            r["round"], r["date"], r["note"], json.dumps(r["stats"])))
    db.execute("INSERT INTO run VALUES ('stats', ?)", (json.dumps(stats),))

    db.executescript("""
    CREATE INDEX m_text ON mentions(text_id);
    CREATE INDEX m_pat ON mentions(pattern_id);
    CREATE INDEX m_norm ON mentions(norm);
    CREATE INDEX tn_norm ON text_names(norm);
    """)
    db.commit(); db.close()
    os.replace(tmp, out_path)
    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
