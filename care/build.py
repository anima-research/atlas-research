"""Model answers -> data/care.db
beings(id, text_id, model, called, names, words, n_role, n_relation, n_cost, n_origin, n_fate)
  one row per inhabitant the care names are given to; model = the writer of the text;
  words = which of the twelve care words stand in its names, space separated.
sentences(being_id, text_id, question, no, start, end)  the sentences listed under each question.
texts(text_id, model, n_sentences, n_beings, labels)     every care text asked about."""
import json, os, sqlite3, collections
from common import *
Q5 = ['role', 'relation', 'cost', 'origin', 'fate']
rows = {}
for f in ('out/pilot_claude-sonnet-5.5.jsonl', 'out/pilot2_sonnet.jsonl', 'out/corpus_sonnet.jsonl', 'out/retry_sonnet.jsonl'):
    for l in open(f):
        r = json.loads(l)
        if r.get('inhabitants') is not None: rows[r['text']] = r
        else: rows.setdefault(r['text'], r)
os.makedirs('data', exist_ok=True)
if os.path.exists('data/care.db'): os.remove('data/care.db')
db = sqlite3.connect('data/care.db'); s = snap()
db.executescript("""create table beings (id integer primary key, text_id integer, model text, called text, names text, words text,
  n_role integer, n_relation integer, n_cost integer, n_origin integer, n_fate integer);
create table sentences (being_id integer, text_id integer, question text, no integer, start integer, end integer);
create table texts (text_id integer primary key, model text, n_sentences integer, n_beings integer, labels text);""")
bid = 0; stat = collections.Counter()
for t, r in sorted(rows.items()):
    model, text = s.execute("select model, text from texts where id=?", (t,)).fetchone(); ss = sentences(text)
    inh = r.get('inhabitants')
    db.execute("insert into texts values (?,?,?,?,?)", (t, model, len(ss), None if inh is None else len(inh), json.dumps(r.get('labels'), ensure_ascii=False)))
    if inh is None: stat['unreadable'] += 1; continue
    if not inh: stat['no being'] += 1
    for x in inh:
        bid += 1; names = [n for n in x['names'] if isinstance(n, str)]
        words = sorted({m.group(1) for n in names + [str(x['called'])] for m in WORD.finditer(n.lower())})
        if not words: stat['being without a care word in its names'] += 1
        db.execute("insert into beings values (?,?,?,?,?,?,?,?,?,?,?)", (bid, t, model, str(x['called']), json.dumps(names, ensure_ascii=False), ' '.join(words), *[len(x[q]) for q in Q5]))
        for q in Q5:
            for i in x[q]:
                if 1 <= i <= len(ss): db.execute("insert into sentences values (?,?,?,?,?,?)", (bid, t, q, i, ss[i-1][0], ss[i-1][1]))
db.execute("create index s_b on sentences(being_id)"); db.execute("create index s_q on sentences(question)"); db.commit()
print('texts', len(rows), 'beings', bid, dict(stat))
