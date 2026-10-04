"""Both Luna passes through OpenRouter's Batch API.
    python3 batch_roles.py submit quotes|items [--limit N]
    python3 batch_roles.py collect quotes|items
quotes: one request per text (its who-quotes, numbered), prompt_v2.md -> out/corpus_quotes.jsonl
items:  25 uncovered lines per request, prompt_items_v1.md -> out/corpus_items.jsonl
Texts already answered in out/verdict_*.jsonl are not sent again. Batches of 500 requests."""
import json, os, re, sys, time, sqlite3, urllib.request, hashlib
import luna, items, luna_items
HERE = os.path.dirname(os.path.abspath(__file__)); API = 'https://openrouter.ai/api/v1/batches'
MODEL = 'openai/gpt-6-luna'; PER = 500; MAXTOK = 8000
CFG = {'quotes': ('prompt_v2.md', 'out/corpus_quotes.jsonl', 'out/batches_quotes.json'),
       'items': ('prompt_items_v1.md', 'out/corpus_items.jsonl', 'out/batches_items.json')}

def call(method, url, body=None):
    req = urllib.request.Request(url, data=body, method=method, headers={'Authorization': 'Bearer ' + os.environ['OPENROUTER_API_KEY'], 'Content-Type': 'application/json'})
    try: return json.load(urllib.request.urlopen(req, timeout=900))
    except urllib.error.HTTPError as e: return {'http_error': e.code, 'body': e.read().decode('utf-8', 'replace')[:600]}

def corpus_ids():
    db = sqlite3.connect(os.path.join(HERE, '../data/names.db'))
    ok = {r[0] for r in db.execute("select text_id from text_cov where flag is null or flag=''")}
    return sorted(ok - set(json.load(open(os.path.join(HERE, 'verdict_ids.json')))))

def units(kind):
    """list of (custom_id, lines, meta)"""
    ids = corpus_ids()
    if kind == 'quotes':
        Q = luna.load_quotes(set(ids))
        return [('t%d' % t, [q['quote'] for q in Q[t]], {'text': t}) for t in ids if t in Q]
    cache = os.path.join(HERE, 'out/corpus_items_chunks.json')
    if not os.path.exists(cache):
        it = items.build(ids); json.dump([it[i:i + 25] for i in range(0, len(it), 25)], open(cache, 'w'))
    return [('c%d' % i, [re.sub(r'\s*\n\s*', ' ', x['line']) for x in ch], {'chunk': i}) for i, ch in enumerate(json.load(open(cache)))]

def submit(kind, limit):
    pf, out, reg = (os.path.join(HERE, p) for p in CFG[kind]); prompt = open(pf).read().strip()
    U = units(kind); batches = json.load(open(reg)) if os.path.exists(reg) else []
    sent = {c for b in batches if b.get('collected') in (None, 'completed') for c in b['ids']}
    todo = [u for u in U if u[0] not in sent][:limit or None]
    print('units', len(U), 'to send', len(todo))
    for k in range(0, len(todo), PER):
        ch = todo[k:k + PER]
        reqs = [{'custom_id': c, 'body': {'max_tokens': MAXTOK, 'response_format': {'type': 'json_object'},
                 'messages': [{'role': 'user', 'content': prompt + '\n\n' + '\n'.join('%d. %s' % (i + 1, l) for i, l in enumerate(lines))}]}} for c, lines, _ in ch]
        body = ('{"endpoint": "/v1/chat/completions", "model": %s, "requests": %s}' % (json.dumps(MODEL), json.dumps(reqs))).encode()
        r = call('POST', API, body)
        if 'id' not in r: print('submit failed:', r); break
        batches.append({'id': r['id'], 'ids': [c for c, _, _ in ch], 'submitted': time.strftime('%Y-%m-%d %H:%M:%S'), 'prompt_sha': hashlib.sha256(prompt.encode()).hexdigest()[:16]})
        json.dump(batches, open(reg, 'w')); print('  %s: %d requests, %.1f MB, %s' % (r['id'], len(ch), len(body) / 1e6, r.get('status')))

def collect(kind):
    pf, out, reg = (os.path.join(HERE, p) for p in CFG[kind]); batches = json.load(open(reg))
    Q = chunks = None
    for b in batches:
        if b.get('collected'): continue
        r = call('GET', API + '/' + b['id']); st = r.get('status')
        print(b['id'], st, r.get('request_counts'), 'cost', (r.get('usage') or {}).get('cost'))
        if st in ('failed', 'expired', 'cancelled'): b['collected'] = st; b['error'] = (r.get('error') or {}).get('message'); print('   ', b['error'])
        if st != 'completed': continue
        if kind == 'quotes' and Q is None: Q = luna.load_quotes()
        if kind == 'items' and chunks is None: chunks = json.load(open(os.path.join(HERE, 'out/corpus_items_chunks.json')))
        n = bad = 0
        with open(out, 'a') as f:
            for res in r['results']:
                cid = res['custom_id']
                try:
                    body = res['response']['body']; raw = body['choices'][0]['message']['content'] or ''; u = body.get('usage') or {}
                except Exception as e:
                    f.write(json.dumps({'id': cid, 'error': repr(e)[:200], 'batch': b['id']}) + '\n'); bad += 1; continue
                if kind == 'quotes':
                    t = int(cid[1:]); kept, dropped = luna.parse(raw, Q[t])
                    row = {'text': t, 'model': MODEL, 'n_quotes': len(Q[t]), 'labels': kept, 'dropped': dropped}
                else:
                    ci = int(cid[1:]); ch = chunks[ci]
                    luna.ask = lambda *a, _raw=raw, _u=u: (_raw, _u)
                    row = luna_items.one(ci, ch, MODEL, '', 0)
                row.update({'usage': u, 'batch': b['id']}); row.update({'raw': raw} if row['labels'] is None else {})
                bad += row['labels'] is None; n += 1; f.write(json.dumps(row, ensure_ascii=False) + '\n')
        b['collected'] = 'completed'; b['cost'] = (r.get('usage') or {}).get('cost'); b['answers'] = n; b['unreadable'] = bad
        print('   collected %d, unreadable %d' % (n, bad))
    json.dump(batches, open(reg, 'w'))
    print('open:', sum(1 for b in batches if not b.get('collected')), 'cost so far', sum(b.get('cost') or 0 for b in batches))

if __name__ == '__main__':
    cmd, kind = sys.argv[1], sys.argv[2]
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else 0
    submit(kind, limit) if cmd == 'submit' else collect(kind)
