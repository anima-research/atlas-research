"""Both Luna passes -> ../data/roles.db
labels(text_id, start, end, label, norm, source): one row per label at one position in the text.
source: 'quote' (from a who-quote) or 'line' (from a heading or a sentence the quotes did not cover).
norm: lower case, markup and a leading article removed. Nothing is filtered."""
import json, os, re, sqlite3, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__))
norm = lambda s: re.sub(r'^(the|a|an)\s+', '', re.sub(r'\s+', ' ', re.sub(r'[*_`"“”#]', '', s.replace('’', "'").replace('‘', "'"))).strip().lower())
rows = {}; texts = set(); stat = collections.Counter()
for f in ('out/verdict_luna_v2.jsonl', 'out/corpus_quotes.jsonl'):
    if not os.path.exists(f): continue
    for l in open(f):
        r = json.loads(l)
        if r.get('labels') is None: stat['unreadable quote answers'] += 1; continue
        texts.add(r['text']); stat['dropped'] += len(r['dropped'])
        for x in r['labels']: rows.setdefault((r['text'], x['start'], x['end']), (x['label'], 'quote'))
for f in ('out/verdict_items_v1.jsonl', 'out/corpus_items.jsonl'):
    if not os.path.exists(f): continue
    for l in open(f):
        r = json.loads(l)
        if r.get('labels') is None: stat['unreadable line answers'] += 1; continue
        stat['dropped'] += len(r['dropped'])
        for x in r['labels']: rows.setdefault((x['text'], x['start'], x['end']), (x['label'], 'line'))
p = os.path.join(HERE, '../data/roles.db')
if os.path.exists(p): os.remove(p)
db = sqlite3.connect(p)
db.execute("create table labels (text_id integer, start integer, end integer, label text, norm text, source text)")
db.executemany("insert into labels values (?,?,?,?,?,?)", [(t, s, e, lab, norm(lab), src) for (t, s, e), (lab, src) in rows.items() if norm(lab)])
db.execute("create index l_text on labels(text_id)"); db.execute("create index l_norm on labels(norm)")
db.execute("create table run (key text primary key, value text)")
stat.update({'texts with a quote answer': len(texts), 'labels': len(rows)})
db.execute("insert into run values ('stats', ?)", (json.dumps(stat),)); db.commit()
print(dict(stat)); print('texts with any label', db.execute("select count(distinct text_id) from labels").fetchone()[0], 'distinct norms', db.execute("select count(distinct norm) from labels").fetchone()[0])
print(db.execute("select source, count(*) from labels group by 1").fetchall())
