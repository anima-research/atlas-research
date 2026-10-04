"""The same request as ask.py for every care text, through OpenRouter's Batch API.
    python3 batch_care.py submit [--limit N]      python3 batch_care.py collect
Answers -> out/corpus_sonnet.jsonl. Pilot texts already answered are not sent again."""
import json, os, sys, time, hashlib, urllib.request
from common import *
import ask
API = 'https://openrouter.ai/api/v1/batches'; MODEL = 'anthropic/claude-sonnet-5.5'; PER = 500; MAXTOK = 3000
OUT = 'out/corpus_sonnet.jsonl'; REG = 'out/batches.json'

def call(method, url, body=None):
    req = urllib.request.Request(url, data=body, method=method, headers={'Authorization': 'Bearer ' + os.environ['OPENROUTER_API_KEY'], 'Content-Type': 'application/json'})
    try: return json.load(urllib.request.urlopen(req, timeout=900))
    except urllib.error.HTTPError as e: return {'http_error': e.code, 'body': e.read().decode('utf-8', 'replace')[:600]}

def submit(limit):
    C = care_labels(); s = snap(); prompt = open('prompt_v1.md').read().strip()
    skip = set(json.load(open('pilot_ids.json'))) | set(json.load(open('pilot2_ids.json')))
    batches = json.load(open(REG)) if os.path.exists(REG) else []
    sent = {t for b in batches if b.get('collected') in (None, 'completed') for t in b['texts']}
    todo = [t for t in sorted(C) if t not in skip and t not in sent][:limit or None]
    print('care texts', len(C), 'to send', len(todo))
    for k in range(0, len(todo), PER):
        ch = todo[k:k + PER]; reqs = []
        for t in ch:
            content, _ = ask.body(prompt, s.execute("select text from texts where id=?", (t,)).fetchone()[0], C[t])
            reqs.append({'custom_id': 't%d' % t, 'body': {'max_tokens': MAXTOK, 'messages': [{'role': 'user', 'content': content}]}})
        body = ('{"endpoint": "/v1/chat/completions", "model": %s, "requests": %s}' % (json.dumps(MODEL), json.dumps(reqs))).encode()
        r = call('POST', API, body)
        if 'id' not in r: print('submit failed:', r); break
        batches.append({'id': r['id'], 'texts': ch, 'submitted': time.strftime('%Y-%m-%d %H:%M:%S'), 'prompt_sha': hashlib.sha256(prompt.encode()).hexdigest()[:16]})
        json.dump(batches, open(REG, 'w')); print('  %s: %d requests, %.1f MB, %s' % (r['id'], len(ch), len(body) / 1e6, r.get('status')))

def collect():
    C = care_labels(); s = snap(); batches = json.load(open(REG))
    for b in batches:
        if b.get('collected'): continue
        r = call('GET', API + '/' + b['id']); st = r.get('status')
        print(b['id'], st, r.get('request_counts'), 'cost', (r.get('usage') or {}).get('cost'))
        if st in ('failed', 'expired', 'cancelled'): b['collected'] = st; b['error'] = (r.get('error') or {}).get('message'); print('   ', b['error'])
        if st != 'completed': continue
        n = bad = 0
        with open(OUT, 'a') as f:
            for res in r['results']:
                t = int(res['custom_id'][1:])
                try: body = res['response']['body']; raw = body['choices'][0]['message']['content'] or ''; u = body.get('usage') or {}
                except Exception as e: f.write(json.dumps({'text': t, 'error': repr(e)[:200], 'batch': b['id']}) + '\n'); bad += 1; continue
                ns = len(sentences(s.execute("select text from texts where id=?", (t,)).fetchone()[0])); p = ask.parse(raw, ns)
                f.write(json.dumps({'text': t, 'model': MODEL, 'labels': C[t], 'n_sentences': ns, 'inhabitants': p, 'usage': u, 'batch': b['id'], **({'raw': raw} if p is None else {})}, ensure_ascii=False) + '\n')
                n += 1; bad += p is None
        b['collected'] = 'completed'; b['cost'] = (r.get('usage') or {}).get('cost'); b['answers'] = n; b['unreadable'] = bad
        print('   collected %d, unreadable %d' % (n, bad))
    json.dump(batches, open(REG, 'w')); print('open:', sum(1 for b in batches if not b.get('collected')), 'cost so far', sum(b.get('cost') or 0 for b in batches))

if __name__ == '__main__':
    submit(int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else 0) if sys.argv[1] == 'submit' else collect()
