"""How each text places its inhabitants relative to the place, read from the who-quotes by a small model,
with sentence numbers (verifiable). Levels as in the who study's codebook: in < part < alive < is.
    python3 relation_pass.py gold            the 180 gold texts, synchronously -> data/relation_gold.json
    python3 relation_pass.py submit|collect  every text, Batch API -> data/relation.json"""
import json, os, re, sys, time, urllib.request, concurrent.futures as cf
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../names/roles')); import luna
MODEL = 'openai/gpt-6-luna'; API = 'https://openrouter.ai/api/v1/batches'; prompt = open('prompt_relation.md').read().strip()
def parse(raw, n):
    m = re.search(r'\{.*\}', raw or '', re.S)
    try: d = json.loads(m.group())
    except Exception: return None
    out = {}
    for k in ('part', 'alive', 'is'):
        v = d.get(k) or []; out[k] = sorted({int(x) for x in v if str(x).strip().isdigit() and 1 <= int(x) <= n}) if isinstance(v, list) else []
    return out
def level(r): return 'is' if r['is'] else 'alive' if r['alive'] else 'part' if r['part'] else 'in'
def call(method, url, body=None):
    req = urllib.request.Request(url, data=body, method=method, headers={'Authorization': 'Bearer ' + os.environ['OPENROUTER_API_KEY'], 'Content-Type': 'application/json'})
    try: return json.load(urllib.request.urlopen(req, timeout=900))
    except urllib.error.HTTPError as e: return {'http_error': e.code, 'body': e.read().decode('utf-8', 'replace')[:300]}
cmd = sys.argv[1]
if cmd == 'gold':
    gold = {int(k): v for k, v in json.load(open('data/gold_relation.json')).items()}; Q = luna.load_quotes(set(gold)); out = {}
    def one(t):
        raw, u = luna.ask(MODEL, prompt, Q[t], 6000); return t, parse(raw, len(Q[t])), u
    with cf.ThreadPoolExecutor(16) as ex:
        for t, p, u in ex.map(one, sorted(Q)):
            if p: out[t] = p
    json.dump(out, open('data/relation_gold.json', 'w'))
    import collections
    ORD = {'in': 0, 'part': 1, 'alive': 2, 'is': 3}; C = collections.Counter(); conf = collections.Counter()
    for t, g in gold.items():
        if t not in out: continue
        l = level(out[t]); conf[(g, l)] += 1; C['n'] += 1; C['exact'] += g == l; C['part-or-more agrees'] += (ORD[g] >= 1) == (ORD[l] >= 1); C['is agrees'] += (g == 'is') == (l == 'is')
    print(dict(C)); print('gold -> luna:', sorted(conf.items()))
elif cmd == 'submit':
    Q = luna.load_quotes(); done = set(json.load(open('data/relation.json')).keys()) if os.path.exists('data/relation.json') else set()
    ids = [t for t in sorted(Q) if str(t) not in done]; reg = json.load(open('out/relation_batches.json')) if os.path.exists('out/relation_batches.json') else []
    sent = {t for b in reg for t in b['texts']}; ids = [t for t in ids if t not in sent]; print('to send', len(ids))
    for k in range(0, len(ids), 500):
        ch = ids[k:k + 500]
        reqs = [{'custom_id': 't%d' % t, 'body': {'max_tokens': 6000, 'response_format': {'type': 'json_object'}, 'messages': [{'role': 'user', 'content': prompt + '\n\n' + '\n'.join('%d. %s' % (i + 1, q['quote']) for i, q in enumerate(Q[t]))}]}} for t in ch]
        for attempt in range(12):
            r = call('POST', API, ('{"endpoint": "/v1/chat/completions", "model": %s, "requests": %s}' % (json.dumps(MODEL), json.dumps(reqs))).encode())
            if r.get('http_error') == 429: print('rate limited, waiting'); time.sleep(75); continue
            break
        if 'id' not in r: print('failed', r); break
        reg.append({'id': r['id'], 'texts': ch}); json.dump(reg, open('out/relation_batches.json', 'w')); print(r['id'], len(ch))
elif cmd == 'collect':
    Q = luna.load_quotes(); reg = json.load(open('out/relation_batches.json')); out = json.load(open('data/relation.json')) if os.path.exists('data/relation.json') else {}; cost = 0
    for b in reg:
        if b.get('done'): cost += b.get('cost') or 0; continue
        r = call('GET', API + '/' + b['id']); print(b['id'], r.get('status'), r.get('request_counts'))
        if r.get('status') != 'completed': continue
        bad = 0
        for res in r['results']:
            t = int(res['custom_id'][1:])
            try: p = parse(res['response']['body']['choices'][0]['message']['content'], len(Q[t]))
            except Exception: p = None
            if p is None: bad += 1; continue
            out[str(t)] = p
        b['done'] = True; b['cost'] = (r.get('usage') or {}).get('cost'); b['bad'] = bad; cost += b['cost'] or 0
    json.dump(out, open('data/relation.json', 'w')); json.dump(reg, open('out/relation_batches.json', 'w'))
    print('open:', sum(1 for b in reg if not b.get('done')), 'texts', len(out), 'unreadable', sum(b.get('bad') or 0 for b in reg), 'cost', round(cost, 2))
