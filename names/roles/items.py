"""Lines the who-quotes did not cover: headings, and sentences holding a pattern hit outside every
quote. build(ids) -> list of {text, start, end, line, why}."""
import json, os, re, sqlite3, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../../who/quotes')); from headings import headings
from luna import load_quotes
SENT = re.compile(r'[^\n]+?(?:[.!?]["”’)*_]*(?=\s+["“*_(]*[A-Z])|$)', re.M)

def sentences(text):
    return [(m.start() + len(m.group()) - len(m.group().lstrip()), m.end()) for m in SENT.finditer(text) if m.group().strip()]

def build(ids, cap=700):
    snap = sqlite3.connect(os.path.join(HERE, '../data/snapshot_r15.sqlite')); db = sqlite3.connect(os.path.join(HERE, '../data/names.db'))
    stat = {r[0] for r in db.execute("select id from patterns where family='statement'")}
    Q = load_quotes(set(ids)); out = []
    for t in sorted(ids):
        text = snap.execute("select text from texts where id=?", (t,)).fetchone()[0]
        qs = Q.get(t, []); inq = lambda s, e: any(q['start'] <= s and e <= q['end'] for q in qs)
        sents = sentences(text); got = {}
        for pos, title in headings(text):
            e = text.find('\n', pos); e = len(text) if e < 0 else e
            if not inq(pos, e): got[(pos, e)] = 'heading'
        for s, e, p in db.execute("select start, end, pattern_id from mentions where text_id=?", (t,)):
            if p in stat or inq(s, e): continue
            for a, b in sents:
                if a <= s < b:
                    if not inq(a, b): got.setdefault((a, b), 'sentence')
                    break
        for (a, b), why in sorted(got.items()):
            if b - a > cap: continue
            line = text[a:b].strip()
            if line: out.append({'text': t, 'start': a, 'end': b, 'line': text[a:b], 'why': why})
    return out

if __name__ == '__main__':
    ids = json.load(open(sys.argv[1])); it = build(ids)
    import collections
    print(len(ids), 'texts', len(it), 'items', collections.Counter(x['why'] for x in it), 'chars', sum(len(x['line']) for x in it))
    import random; random.seed(1)
    for x in random.sample(it, 25): print(x['text'], x['why'], '|', x['line'][:160].replace('\n', ' '))
