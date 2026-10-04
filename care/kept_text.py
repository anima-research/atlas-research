"""What is cared for according to the texts: for each being, the nouns in its role sentences that say what
it keeps, tends or guards. A noun is accepted only if it stands in those sentences.
    python3 kept_text.py pilot              the twenty beings of pilot_kept_ids.json, synchronously
    python3 kept_text.py submit | collect   every being with role sentences, through the Batch API
Output: data/kept_text.json {being id: {for: [nouns], against: [nouns]}}"""
import json, os, re, sys, time, sqlite3, urllib.request, concurrent.futures as cf
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../names/roles'))
import luna
from common import *
MODEL = 'openai/gpt-6-luna'; PER = 8; API = 'https://openrouter.ai/api/v1/batches'; prompt = open('prompt_kept_text.md').read().strip()
db = sqlite3.connect('data/care.db'); s = snap()
def groups(ids=None):
    G = {}; cur = None; text = None
    for bid, t, a, b in db.execute("select being_id, text_id, start, end from sentences where question='role' order by text_id, being_id, no"):
        if ids is not None and bid not in ids: continue
        if t != cur: cur = t; text = s.execute("select text from texts where id=?", (t,)).fetchone()[0]
        G.setdefault(bid, []).append(re.sub(r'\s+', ' ', text[a:b]).strip())
    return G
def content(ch, G): return prompt + '\n\n' + '\n\n'.join('%d.\n%s' % (i + 1, '\n'.join(G[b])) for i, b in enumerate(ch))
def parse(raw, ch, G):
    m = re.search(r'\{.*\}', raw or '', re.S)
    try: d = json.loads(m.group())
    except Exception: return None
    out = {b: {'for': [], 'against': []} for b in ch}
    for k, v in d.items():
        if not str(k).isdigit() or not (1 <= int(k) <= len(ch)): continue
        b = ch[int(k) - 1]; hay = ' '.join(G[b]).lower()
        if not isinstance(v, dict): continue
        out[b] = {side: sorted({x.lower().strip() for x in (v.get(side) or []) if isinstance(x, str) and x.strip() and x.lower().strip() in hay}) for side in ('for', 'against')}
    return out
def call(method, url, body=None):
    req = urllib.request.Request(url, data=body, method=method, headers={'Authorization': 'Bearer ' + os.environ['OPENROUTER_API_KEY'], 'Content-Type': 'application/json'})
    try: return json.load(urllib.request.urlopen(req, timeout=900))
    except urllib.error.HTTPError as e: return {'http_error': e.code, 'body': e.read().decode('utf-8', 'replace')[:400]}
cmd = sys.argv[1]
if cmd == 'pilot':
    ids = json.load(open('pilot_kept_ids.json')); G = groups(set(ids)); out = {}
    for k in range(0, len(ids), PER):
        ch = ids[k:k + PER]
        req = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions', data=json.dumps({'model': MODEL, 'messages': [{'role': 'user', 'content': content(ch, G)}], 'max_tokens': 8000, 'response_format': {'type': 'json_object'}}).encode(),
                                     headers={'Authorization': 'Bearer ' + os.environ['OPENROUTER_API_KEY'], 'Content-Type': 'application/json'})
        r = json.load(urllib.request.urlopen(req, timeout=300)); out.update(parse(r['choices'][0]['message']['content'], ch, G) or {})
    for b in ids: print(b, out.get(b))
elif cmd == 'submit':
    G = groups(); ids = sorted(G); chunks = [ids[i:i + PER] for i in range(0, len(ids), PER)]; json.dump(chunks, open('out/kept_text_chunks.json', 'w')); reg = []
    for k in range(0, len(chunks), 500):
        reqs = [{'custom_id': 'c%d' % (k + j), 'body': {'max_tokens': 8000, 'response_format': {'type': 'json_object'}, 'messages': [{'role': 'user', 'content': content(ch, G)}]}} for j, ch in enumerate(chunks[k:k + 500])]
        r = call('POST', API, ('{"endpoint": "/v1/chat/completions", "model": %s, "requests": %s}' % (json.dumps(MODEL), json.dumps(reqs))).encode())
        if 'id' not in r: print('submit failed', r); break
        reg.append({'id': r['id']}); json.dump(reg, open('out/kept_text_batches.json', 'w')); print(r['id'], len(reqs))
elif cmd == 'collect':
    G = groups(); chunks = json.load(open('out/kept_text_chunks.json')); reg = json.load(open('out/kept_text_batches.json'))
    out = json.load(open('data/kept_text.json')) if os.path.exists('data/kept_text.json') else {}; cost = 0
    for b in reg:
        if b.get('done'): cost += b.get('cost') or 0; continue
        r = call('GET', API + '/' + b['id']); print(b['id'], r.get('status'), r.get('request_counts'))
        if r.get('status') != 'completed': continue
        bad = 0
        for res in r['results']:
            ch = chunks[int(res['custom_id'][1:])]
            try: p = parse(res['response']['body']['choices'][0]['message']['content'], ch, G)
            except Exception: p = None
            if p is None: bad += 1; continue
            out.update({str(k): v for k, v in p.items()})
        b['done'] = True; b['cost'] = (r.get('usage') or {}).get('cost'); b['unreadable'] = bad; cost += b['cost'] or 0
    json.dump(out, open('data/kept_text.json', 'w')); json.dump(reg, open('out/kept_text_batches.json', 'w'))
    print('open:', sum(1 for b in reg if not b.get('done')), 'beings answered', len(out), 'unreadable chunks', sum(b.get('unreadable') or 0 for b in reg), 'cost', round(cost, 2))
