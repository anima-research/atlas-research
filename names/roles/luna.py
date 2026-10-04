"""Ask a model for the names and roles in the who-quotes of each text.
Input: who/quotes/corpus/*.jsonl (last row with quotes per text). Output: one JSON line per text:
{text, model, labels: [{q, start, end, label}], dropped: [{q, label}], raw}. A label is kept only
if it is found inside the quote it was given for; start/end are positions in the text."""
import json, os, re, sys, time, argparse, urllib.request, concurrent.futures as cf
HERE = os.path.dirname(os.path.abspath(__file__))
QUOTES = os.path.join(HERE, '../../who/quotes/corpus/anthropic__claude-sonnet-5.5.jsonl')

def load_quotes(ids=None):
    out = {}
    for line in open(QUOTES):
        r = json.loads(line)
        if r.get('quotes') and (ids is None or r['text'] in ids): out[r['text']] = r['quotes']
    return out

def ask(model, prompt, quotes, max_tokens):
    body = prompt + '\n\n' + '\n'.join(f"{i+1}. {q['quote']}" for i, q in enumerate(quotes))
    req = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',
        data=json.dumps({'model': model, 'messages': [{'role': 'user', 'content': body}],
                         'max_tokens': max_tokens, 'response_format': {'type': 'json_object'}}).encode(),
        headers={'Authorization': 'Bearer ' + os.environ['OPENROUTER_API_KEY'], 'Content-Type': 'application/json'})
    for attempt in range(4):
        try:
            r = json.load(urllib.request.urlopen(req, timeout=300))
            return r['choices'][0]['message']['content'], r.get('usage', {})
        except Exception as e:
            err = repr(e); time.sleep(3 * (attempt + 1))
    return None, {'error': err}

def find(label, quote):
    """position of label inside quote: exact, then case-insensitive with quotes/dashes folded"""
    p = quote.find(label)
    if p >= 0: return p
    fold = lambda s: s.lower().translate(str.maketrans('’‘“”—–', "''\"\"--"))
    p = fold(quote).find(fold(label))
    return p if p >= 0 else None

def parse(raw, quotes):
    m = re.search(r'\{.*\}', raw or '', re.S)
    try: d = json.loads(m.group()) if m else None
    except Exception: d = None
    if not isinstance(d, dict): return None, None
    kept, dropped = [], []
    for k, v in d.items():
        if not str(k).strip().isdigit() or not isinstance(v, list): dropped.append({'q': k, 'label': v}); continue
        qi = int(k) - 1
        for label in v:
            if not isinstance(label, str) or not (0 <= qi < len(quotes)): dropped.append({'q': k, 'label': label}); continue
            p = find(label, quotes[qi]['quote'])
            if p is None: dropped.append({'q': qi + 1, 'label': label}); continue
            s = quotes[qi]['start'] + p
            kept.append({'q': qi + 1, 'start': s, 'end': s + len(label), 'label': quotes[qi]['quote'][p:p + len(label)]})
    return kept, dropped

def one(tid, quotes, model, prompt, max_tokens):
    raw, usage = ask(model, prompt, quotes, max_tokens)
    kept, dropped = parse(raw, quotes)
    return {'text': tid, 'model': model, 'n_quotes': len(quotes), 'labels': kept, 'dropped': dropped, 'usage': usage,
            **({'raw': raw} if kept is None else {})}

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--ids'); ap.add_argument('--model', default='openai/gpt-6-luna')
    ap.add_argument('--prompt', default=os.path.join(HERE, 'prompt_v2.md')); ap.add_argument('--out', required=True)
    ap.add_argument('--max-tokens', type=int, default=8000); ap.add_argument('--workers', type=int, default=8)
    a = ap.parse_args()
    ids = set(json.load(open(a.ids))) if a.ids else None
    prompt = open(a.prompt).read().strip(); quotes = load_quotes(ids)
    done = {json.loads(l)['text'] for l in open(a.out)} if os.path.exists(a.out) else set()
    todo = [t for t in sorted(quotes) if t not in done]
    with cf.ThreadPoolExecutor(a.workers) as ex, open(a.out, 'a') as f:
        for r in ex.map(lambda t: one(t, quotes[t], a.model, prompt, a.max_tokens), todo):
            f.write(json.dumps(r, ensure_ascii=False) + '\n'); f.flush()
            print(r['text'], len(r['labels'] or []), 'kept', len(r['dropped'] or []), 'dropped', r['usage'].get('cost'), file=sys.stderr)
