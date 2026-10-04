#!/usr/bin/env python3
"""Turn extracted quotes into anonymous items, grouped several to a prompt.

    python3 quotes/items.py build --from quotes/extracted_v2/openai__gpt-6-luna.jsonl --name pilotA [--per 5] [--seed 1] [--kinds answer,place,not,who]
        writes quotes/items/<name>/prompt_NN.txt, and map.json (item number -> text id, kept apart from the prompts)
    python3 quotes/items.py run --name pilotA --model <openrouter id>
        answers go to quotes/items/<name>/answers/<model>.jsonl, with the text id restored
An item shows the passages in text order, each with the point of the text where it begins (percent),
and how much of the text the passages cover. It carries no writer and no text id.
"""
import argparse, concurrent.futures as cf, json, os, random, re, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))


def merge(quotes):
    out = []
    for q in sorted(quotes, key=lambda x: x["start"]):
        if out and q["start"] <= out[-1]["end"] + 1:
            out[-1]["end"] = max(out[-1]["end"], q["end"])
        else:
            out.append({"start": q["start"], "end": q["end"]})
    return out


def build(a):
    import sqlite3
    snap = sqlite3.connect("file:%s?mode=ro" % os.path.join(HERE, "..", "..", "names", "data", "snapshot_r15.sqlite"), uri=True)
    rows = [json.loads(l) for l in open(a.src) if '"error"' not in l]
    kinds = set(a.kinds.split(",")) if a.kinds else None
    rnd = random.Random("items:%s:%s" % (a.name, a.seed))
    numbers = rnd.sample(range(1000, 10000), len(rows))
    rnd.shuffle(rows)
    d = os.path.join(HERE, "items", a.name)
    os.makedirs(d, exist_ok=True)
    head = open(os.path.join(HERE, "items_prompt.md")).read()
    mp = {}; prompts = []
    for i in range(0, len(rows), a.per):
        parts = []
        for r, num in zip(rows[i:i + a.per], numbers[i:i + a.per]):
            text = snap.execute("SELECT text FROM texts WHERE id=?", (r["text"],)).fetchone()[0]
            spans = merge([q for q in r["quotes"] if not kinds or q["kind"] in kinds])
            cover = sum(s["end"] - s["start"] for s in spans)
            mp[num] = {"text": r["text"], "prompt": len(prompts), "passages": len(spans), "chars": cover}
            body = "\n".join("[%d%%] %s" % (round(100 * s["start"] / max(1, len(text))), text[s["start"]:s["end"]].strip()) for s in spans)
            parts.append("=== ITEM %d ===\n(the text has %d characters; %d passages below, %d%% of it)\n\n%s" % (num, len(text), len(spans), round(100 * cover / max(1, len(text))), body))
        prompts.append(head + "\n\n" + "\n\n".join(parts) + "\n")
    for i, p in enumerate(prompts):
        open(os.path.join(d, "prompt_%02d.txt" % i), "w").write(p)
    json.dump({"source": a.src, "kinds": a.kinds, "per": a.per, "seed": a.seed, "items": mp}, open(os.path.join(d, "map.json"), "w"), indent=0)
    print("%d items in %d prompts -> %s; characters per prompt: %s" % (len(rows), len(prompts), d, [len(p) for p in prompts]))


def ask(model, prompt, key, tries=4):
    body = json.dumps({"model": model, "temperature": 0, "max_tokens": 16000, "messages": [{"role": "user", "content": prompt}]}).encode()
    err = None
    for t in range(tries):
        try:
            req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                                         headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=300))
            out = r["choices"][0]["message"]["content"] or ""
            ans = json.loads(re.search(r"\[.*\]", out, re.S).group(0))
            return ans, r.get("usage", {}).get("cost")
        except Exception as e:  # noqa
            err = repr(e)[:200]; time.sleep(3 * (t + 1))
    return {"error": err}, None


def restore(d, answers, who):
    """Put text ids back on the answers of one prompt; write them out."""
    mp = {int(k): v for k, v in json.load(open(os.path.join(d, "map.json")))["items"].items()}
    os.makedirs(os.path.join(d, "answers"), exist_ok=True)
    with open(os.path.join(d, "answers", who.replace("/", "__") + ".jsonl"), "a") as f:
        for x in answers:
            num = int(x["item"])
            f.write(json.dumps(dict(x, text=mp[num]["text"], judge=who), ensure_ascii=False) + "\n")


def run(a):
    d = os.path.join(HERE, "items", a.name)
    key = os.environ["OPENROUTER_API_KEY"]
    files = sorted(f for f in os.listdir(d) if f.startswith("prompt_"))
    cost = 0
    with cf.ThreadPoolExecutor(a.workers) as ex:
        fut = {ex.submit(ask, a.model, open(os.path.join(d, f)).read(), key): f for f in files}
        for fu in cf.as_completed(fut):
            ans, c = fu.result()
            if isinstance(ans, dict):
                print("error", fut[fu], ans, file=sys.stderr); continue
            restore(d, ans, a.model); cost += c or 0
    print("%s: %d prompts, cost $%.3f" % (a.model, len(files), cost), file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd")
    b = sub.add_parser("build"); b.add_argument("--from", dest="src", required=True); b.add_argument("--name", required=True)
    b.add_argument("--per", type=int, default=5); b.add_argument("--seed", default="1"); b.add_argument("--kinds", default="")
    r = sub.add_parser("run"); r.add_argument("--name", required=True); r.add_argument("--model", required=True); r.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    {"build": build, "run": run}[a.cmd](a)


if __name__ == "__main__":
    main()
