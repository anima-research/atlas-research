"""One request per text: the numbered sentences and the care labels found in it; the answer gives,
per inhabitant the labels belong to, sentence numbers for five questions.
    python3 ask.py --ids pilot_ids.json --model openai/gpt-6-luna --out out/pilot_luna.jsonl"""
import json, os, re, sys, time, argparse, urllib.request, concurrent.futures as cf
from common import *
Q5 = ['role', 'relation', 'cost', 'origin', 'fate']

def body(prompt, text, labels):
    ss = sentences(text)
    return prompt.replace('{labels}', '; '.join(labels)) + '\n\n' + '\n'.join('[%d] %s' % (i + 1, text[a:b]) for i, (a, b) in enumerate(ss)), ss

def call(model, content, max_tokens):
    req = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',
        data=json.dumps({'model': model, 'messages': [{'role': 'user', 'content': content}], 'max_tokens': max_tokens}).encode(),
        headers={'Authorization': 'Bearer ' + os.environ['OPENROUTER_API_KEY'], 'Content-Type': 'application/json'})
    err = None
    for k in range(4):
        try:
            r = json.load(urllib.request.urlopen(req, timeout=600)); return r['choices'][0]['message']['content'], r.get('usage', {})
        except Exception as e: err = repr(e); time.sleep(3 * (k + 1))
    return None, {'error': err}

def parse(raw, n):
    m = re.search(r'\{.*\}', raw or '', re.S)
    try: d = json.loads(m.group())['inhabitants']
    except Exception: return None
    out = []
    for x in d if isinstance(d, list) else []:
        if not isinstance(x, dict): continue
        row = {'called': x.get('called'), 'names': x.get('names') or []}
        for q in Q5: row[q] = sorted({int(i) for i in (x.get(q) or []) if str(i).strip().isdigit() and 1 <= int(i) <= n})
        out.append(row)
    return out

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--ids', required=True); ap.add_argument('--model', required=True)
    ap.add_argument('--prompt', default='prompt_v1.md'); ap.add_argument('--out', required=True); ap.add_argument('--workers', type=int, default=10)
    a = ap.parse_args(); C = care_labels(); s = snap(); prompt = open(a.prompt).read().strip()
    ids = json.load(open(a.ids)); os.makedirs(os.path.dirname(a.out), exist_ok=True)
    texts = {t: s.execute("select text from texts where id=?", (t,)).fetchone()[0] for t in ids}
    def one(t):
        content, ss = body(prompt, texts[t], C[t]); raw, u = call(a.model, content, 16000); p = parse(raw, len(ss))
        return {'text': t, 'model': a.model, 'labels': C[t], 'n_sentences': len(ss), 'inhabitants': p, 'usage': u, **({'raw': raw} if p is None else {})}
    with cf.ThreadPoolExecutor(a.workers) as ex, open(a.out, 'w') as f:
        for r in ex.map(one, ids): f.write(json.dumps(r, ensure_ascii=False) + '\n'); print(r['text'], r['inhabitants'] is not None, r['usage'].get('cost'), file=sys.stderr)
