#!/usr/bin/env python3
"""The same extraction as extract.py, sent through OpenRouter's Batch API (half price, results within 24 hours).

    python3 quotes/batch.py submit --model anthropic/claude-sonnet-5.5 --file quotes/corpus_ids.json --out corpus [--per 2000] [--limit N]
        sends the texts not yet answered in quotes/<out>/<model>.jsonl, in batches; records the batch ids in quotes/<out>/batches.json
    python3 quotes/batch.py collect --out corpus
        asks each recorded batch for its status; finished ones are checked quote by quote (as in extract.py) and appended to the answers file
"""
import argparse, json, os, re, sqlite3, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import extract as ex  # noqa: E402
API = "https://openrouter.ai/api/v1/batches"


def call(method, url, key, body=None):
    req = urllib.request.Request(url, data=body, method=method, headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=600))
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode("utf-8", "replace")[:600]}


def paths(out, model):
    d = os.path.join(HERE, out)
    return d, os.path.join(d, model.replace("/", "__") + ".jsonl"), os.path.join(d, "batches.json")


def submit(a):
    key = os.environ["OPENROUTER_API_KEY"]
    d, ans, reg = paths(a.out, a.model)
    prompt = open(os.path.join(HERE, "extract_prompt.md")).read()
    snap = sqlite3.connect("file:%s?mode=ro" % os.path.join(HERE, "..", "..", "names", "data", "snapshot_r15.sqlite"), uri=True)
    done = {json.loads(l)["text"] for l in open(ans) if '"error"' not in l} if os.path.exists(ans) else set()
    batches = json.load(open(reg)) if os.path.exists(reg) else []
    pending = {t for b in batches if not b.get("collected") for t in b["texts"]}
    todo = [i for i in json.load(open(a.file)) if i not in done and i not in pending]
    if a.limit:
        todo = todo[:a.limit]
    print("to send: %d (answered %d, already in open batches %d)" % (len(todo), len(done), len(pending)))
    for k in range(0, len(todo), a.per):
        chunk = todo[k:k + a.per]
        reqs = [{"custom_id": "t%d" % i, "body": {"max_tokens": 6000, "messages": [{"role": "user", "content": prompt + "\n\nTHE TEXT\n\n" + snap.execute("SELECT text FROM texts WHERE id=?", (i,)).fetchone()[0]}]}} for i in chunk]
        # endpoint and model must come before requests in the body
        body = ('{"endpoint": "/v1/chat/completions", "model": %s, "requests": %s}' % (json.dumps(a.model), json.dumps(reqs))).encode()
        r = call("POST", API, key, body)
        if "id" not in r:
            print("submit failed:", r); break
        batches.append({"id": r["id"], "model": a.model, "texts": chunk, "submitted": time.strftime("%Y-%m-%d %H:%M:%S"), "prompt_sha": __import__("hashlib").sha256(prompt.encode()).hexdigest()[:16]})
        json.dump(batches, open(reg, "w"))
        print("  %s: %d texts, %.1f MB, status %s" % (r["id"], len(chunk), len(body) / 1e6, r.get("status")))


def collect(a):
    key = os.environ["OPENROUTER_API_KEY"]
    d = os.path.join(HERE, a.out); reg = os.path.join(d, "batches.json")
    batches = json.load(open(reg))
    snap = sqlite3.connect("file:%s?mode=ro" % os.path.join(HERE, "..", "..", "names", "data", "snapshot_r15.sqlite"), uri=True)
    for b in batches:
        if b.get("collected"):
            continue
        r = call("GET", API + "/" + b["id"], key)
        st = r.get("status"); rc = r.get("request_counts") or {}
        print("%s: %s  %s  cost %s" % (b["id"], st, rc, (r.get("usage") or {}).get("cost")))
        if st in ("failed", "expired", "cancelled"):
            b["collected"] = st; b["error"] = (r.get("error") or {}).get("message"); print("   ", b["error"])
        if st != "completed":
            continue
        ans = os.path.join(d, b["model"].replace("/", "__") + ".jsonl")
        n = bad = 0
        with open(ans, "a") as f:
            for res in r["results"]:
                t = int(res["custom_id"][1:])
                try:
                    body = res["response"]["body"]
                    out = body["choices"][0]["message"]["content"] or ""
                    parsed = json.loads(re.search(r"[\[{].*[\]}]", out, re.S).group(0))
                    quotes = parsed["quotes"] if isinstance(parsed, dict) else parsed
                    text = snap.execute("SELECT text FROM texts WHERE id=?", (t,)).fetchone()[0]
                    kept, dropped = ex.check(text, quotes)
                    u = body.get("usage") or {}
                    f.write(json.dumps({"text": t, "model": b["model"], "length": len(text), "quotes": kept, "dropped": dropped,
                                        "tokens_in": u.get("prompt_tokens"), "tokens_out": u.get("completion_tokens"), "batch": b["id"]}, ensure_ascii=False) + "\n"); n += 1
                except Exception as e:  # noqa
                    f.write(json.dumps({"text": t, "model": b["model"], "error": repr(e)[:200], "batch": b["id"]}) + "\n"); bad += 1
        b["collected"] = "completed"; b["cost"] = (r.get("usage") or {}).get("cost"); b["answers"] = n; b["errors"] = bad
        print("   collected %d answers, %d unreadable" % (n, bad))
    json.dump(batches, open(reg, "w"))


def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("submit"); s.add_argument("--model", required=True); s.add_argument("--file", required=True)
    s.add_argument("--out", required=True); s.add_argument("--per", type=int, default=2000); s.add_argument("--limit", type=int, default=0)
    c = sub.add_parser("collect"); c.add_argument("--out", required=True)
    a = ap.parse_args()
    {"submit": submit, "collect": collect}[a.cmd](a)


if __name__ == "__main__":
    main()
