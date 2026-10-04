"""How separate or interwoven the twelve words are: per text and per being.
solo      one being in the text, one care word
stacked   one being in the text, several care words given to it
ensemble  several beings in the text (each may carry one or several words)"""
import sqlite3, collections, itertools, json, sys
from common import STEMS
db = sqlite3.connect('data/care.db')
B = db.execute("select id, text_id, model, words, n_role, n_relation, n_cost, n_origin, n_fate from beings where words != ''").fetchall()
nsent = dict(db.execute("select text_id, n_sentences from texts"))
cover = dict(db.execute("select being_id, count(distinct no) from sentences group by 1"))
T = collections.defaultdict(list)
for b in B: T[b[1]].append(b)
kind = {}
for t, bs in T.items():
    kind[t] = 'ensemble' if len(bs) > 1 else ('stacked' if len(bs[0][3].split()) > 1 else 'solo')
def stats(rows):
    n = len(rows)
    return dict(n=n, cost=sum(r[6] > 0 for r in rows) / n, origin=sum(r[7] > 0 for r in rows) / n, fate=sum(r[8] > 0 for r in rows) / n,
                focus=sum(cover.get(r[0], 0) / nsent[r[1]] for r in rows) / n, sent=sum(nsent[r[1]] for r in rows) / n)
if __name__ == '__main__':
    c = collections.Counter(kind.values()); N = len(T)
    print('texts', N, {k: f"{v} ({v/N:.0%})" for k, v in c.items()})
    print('\nbeings by kind of text: share with cost/origin/fate, focus = share of the text\'s sentences listed for the being, mean text length')
    for k in ('solo', 'stacked', 'ensemble'):
        s = stats([b for b in B if kind[b[1]] == k]); print(f"  {k:9} beings {s['n']:6}  cost {s['cost']:.0%} origin {s['origin']:.0%} fate {s['fate']:.0%}  focus {s['focus']:.0%}  sentences {s['sent']:.0f}")
    print('\nensemble texts: are the beings\' words the same or different?')
    same = sum(1 for t, bs in T.items() if kind[t] == 'ensemble' and len({b[3] for b in bs}) == 1); ens = c['ensemble']
    dw = collections.Counter(len({w for b in bs for w in b[3].split()}) for t, bs in T.items() if kind[t] == 'ensemble')
    print(f"  all beings carry the same word(s): {same} of {ens}; distinct words across the text: {sorted(dw.items())}")
    print('\nper word: how its beings are distributed (solo / stacked on one being with other words / in an ensemble), and what they get')
    print(f"{'word':11}{'beings':>7}{'solo':>7}{'stacked':>9}{'ensemble':>10} | cost: solo stacked ensemble | focus: solo stacked ensemble")
    for w in STEMS:
        g = [b for b in B if w in b[3].split()]; parts = {k: [b for b in g if (kind[b[1]] == k if k != 'stacked' else (kind[b[1]] == 'stacked'))] for k in ('solo', 'stacked', 'ensemble')}
        st = {k: stats(v) if v else None for k, v in parts.items()}
        print(f"{w:11}{len(g):7}" + ''.join(f"{len(parts[k])/len(g):>{x}.0%}" for k, x in (('solo', 7), ('stacked', 9), ('ensemble', 10))) + ' |      ' +
              '  '.join(f"{st[k]['cost']:5.0%}" for k in parts) + '    |       ' + '  '.join(f"{st[k]['focus']:5.0%}" for k in parts))
    # pairs: stacked on one being, and on different beings of one text
    on_being = collections.Counter(); across = collections.Counter(); wb = collections.Counter(); wt = collections.Counter()
    for b in B:
        ws = sorted(set(b[3].split())); wb.update(ws); on_being.update(itertools.combinations(ws, 2))
    for t, bs in T.items():
        ws_t = sorted({w for b in bs for w in b[3].split()}); wt.update(ws_t)
        for x, y in itertools.combinations(range(len(bs)), 2):
            for p in {tuple(sorted((a, c2))) for a in bs[x][3].split() for c2 in bs[y][3].split() if a != c2}: across[p] += 1
    nb = len(B)
    print('\npairs given to ONE being (stacking): count, and lift = observed / expected if independent')
    for (a, c2), v in sorted(on_being.items(), key=lambda kv: -kv[1])[:16]: print(f"  {a:10} + {c2:10} {v:5}  lift {v / (wb[a] * wb[c2] / nb):.1f}")
    print('  lowest lift among pairs with expected >= 30:')
    low = sorted(((v / (wb[a] * wb[c2] / nb), a, c2, v) for (a, c2), v in on_being.items() if wb[a] * wb[c2] / nb >= 30))[:8]
    for l, a, c2, v in low: print(f"  {a:10} + {c2:10} {v:5}  lift {l:.1f}")
    print('\npairs on DIFFERENT beings of one text (division of roles): pairs of beings')
    for (a, c2), v in sorted(across.items(), key=lambda kv: -kv[1])[:16]: print(f"  {a:10} | {c2:10} {v:5}")
    json.dump({'kind': kind}, open('data/weave.json', 'w'))
