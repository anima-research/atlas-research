"""Ask a model for names and roles in lines from items.py, 25 lines per request (lines of several
texts may share a request). Output: one JSON line per request:
{chunk, items:[{text,start,end,why}], labels:[{i, text, start, end, label}], dropped, usage}."""
import json, os, re, sys, argparse, concurrent.futures as cf
from luna import find
import luna, items
HERE = os.path.dirname(os.path.abspath(__file__))

def one(ci, chunk, model, prompt, max_tokens):
    raw, usage = luna.ask(model, prompt, [{'quote': re.sub(r'\s*\n\s*', ' ', x['line'])} for x in chunk], max_tokens)
    m = re.search(r'\{.*\}', raw or '', re.S)
    try: d = json.loads(m.group())
    except Exception: d = None
    kept, dropped = [], []
    if isinstance(d, dict):
        for k, v in d.items():
            if not str(k).strip().isdigit() or not isinstance(v, list) or not (1 <= int(k) <= len(chunk)): dropped.append({'i': k, 'label': v}); continue
            x = chunk[int(k) - 1]
            for label in v:
                p = find(label, x['line']) if isinstance(label, str) else None
                if p is None: dropped.append({'i': int(k), 'label': label}); continue
                kept.append({'i': int(k), 'text': x['text'], 'start': x['start'] + p, 'end': x['start'] + p + len(label), 'label': x['line'][p:p + len(label)]})
    return {'chunk': ci, 'model': model, 'items': [{k: x[k] for k in ('text', 'start', 'end', 'why')} for x in chunk],
            'labels': kept if isinstance(d, dict) else None, 'dropped': dropped, 'usage': usage, **({} if isinstance(d, dict) else {'raw': raw})}

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--ids', required=True); ap.add_argument('--model', default='openai/gpt-6-luna')
    ap.add_argument('--prompt', default=os.path.join(HERE, 'prompt_items_v1.md')); ap.add_argument('--out', required=True)
    ap.add_argument('--per', type=int, default=25); ap.add_argument('--max-tokens', type=int, default=8000); ap.add_argument('--workers', type=int, default=32)
    a = ap.parse_args()
    it = items.build(json.load(open(a.ids))); prompt = open(a.prompt).read().strip()
    chunks = [it[i:i + a.per] for i in range(0, len(it), a.per)]
    done = {json.loads(l)['chunk'] for l in open(a.out) if json.loads(l)['labels'] is not None} if os.path.exists(a.out) else set()
    todo = [i for i in range(len(chunks)) if i not in done]
    print(len(it), 'items', len(chunks), 'chunks', len(todo), 'to do', file=sys.stderr)
    with cf.ThreadPoolExecutor(a.workers) as ex, open(a.out, 'a') as f:
        for r in ex.map(lambda i: one(i, chunks[i], a.model, prompt, a.max_tokens), todo):
            f.write(json.dumps(r, ensure_ascii=False) + '\n'); f.flush()
