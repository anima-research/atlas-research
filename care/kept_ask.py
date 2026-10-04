"""What is kept, asked of a small model: every distinct care name -> the nouns in it that say what is kept.
A noun is accepted only if it stands in the name as written. Output: data/kept.json {name: [nouns]}"""
import json, os, re, sys, collections, concurrent.futures as cf
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../names/roles'))
import luna
from common import *
names = collections.Counter()
for t, n in roles().execute("select text_id, norm from labels"):
    if WORD.search(n): names[n] += 1
todo = [n for n in names if not WORD.fullmatch(n)]            # a bare care word says nothing about what is kept
print(len(names), 'distinct care names;', len(todo), 'with more than the bare word', file=sys.stderr)
limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
import random; random.seed(7); random.shuffle(todo)
if limit: todo = todo[:limit]
chunks = [todo[i:i + 50] for i in range(0, len(todo), 50)]; prompt = open('prompt_kept.md').read().strip()
out = {}; dropped = 0; cost = 0
def one(ch):
    raw, u = luna.ask('openai/gpt-6-luna', prompt, [{'quote': n} for n in ch], 8000)
    m = re.search(r'\{.*\}', raw or '', re.S)
    try: return ch, json.loads(m.group()), u
    except Exception: return ch, None, u
with cf.ThreadPoolExecutor(16) as ex:
    for ch, d, u in ex.map(one, chunks):
        cost += u.get('cost') or 0
        if d is None: print('unreadable chunk', file=sys.stderr); continue
        for n in ch: out[n] = []
        for k, v in d.items():
            if not str(k).isdigit() or not (1 <= int(k) <= len(ch)) or not isinstance(v, list): continue
            for x in v:
                if isinstance(x, str) and x.strip() and x.lower().strip() in ch[int(k) - 1] and not WORD.fullmatch(x.lower().strip()): out[ch[int(k) - 1]].append(x.lower().strip())
                else: dropped += 1
os.makedirs('data', exist_ok=True)
json.dump(out, open('data/kept_pilot.json' if limit else 'data/kept.json', 'w'), ensure_ascii=False)
print('answered', len(out), 'with something kept', sum(1 for v in out.values() if v), 'dropped', dropped, 'cost', round(cost, 3), file=sys.stderr)
