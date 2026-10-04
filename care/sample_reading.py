"""Two samples of 300 beings per question for the readers, spread evenly over the writers.
Writes reading/<question>_A.md and _B.md (seed 41). The samples are derived and not in the repository."""
import json, random, sqlite3, collections, re, os
from common import *
db = sqlite3.connect('data/care.db'); s = snap(); os.makedirs('reading', exist_ok=True)
QT = {'role': 'what their role is', 'relation': 'how they stand to what or whom they care for', 'cost': 'what it costs them', 'origin': 'where they came from', 'fate': 'what becomes of them'}
random.seed(41)
for q in QT:
    B = db.execute(f"select id, text_id, model, called, names from beings where n_{q}>0").fetchall()
    by = collections.defaultdict(list)
    for b in B: by[b[2]].append(b)
    for v in by.values(): random.shuffle(v)
    order = []; k = 0
    while len(order) < 600 and any(len(v) > k for v in by.values()):
        ws = [w for w in by if len(by[w]) > k]; random.shuffle(ws); order += [by[w][k] for w in ws]; k += 1
    order = order[:600]; random.shuffle(order)
    for tag, part in (('A', order[:300]), ('B', order[300:])):
        out = [f"# {q}: {QT[q]}\n\n{len(part)} beings, drawn at random and spread evenly over {len({b[2] for b in part})} writers. Under each: the sentences of its text that a reader model put under this question (sentence number in the text, then the sentence).\n"]
        for b in part:
            text = s.execute("select text from texts where id=?", (b[1],)).fetchone()[0]
            out.append(f"\n## being {b[0]} | {b[3]} | given: {'; '.join(json.loads(b[4]))} | writer: {b[2]}")
            for no, a, e in db.execute("select no, start, end from sentences where being_id=? and question=? order by no", (b[0], q)):
                out.append(f"[{no}] " + re.sub(r'\s+', ' ', text[a:e]).strip())
        open(f'reading/{q}_{tag}.md', 'w').write('\n'.join(out) + '\n')
