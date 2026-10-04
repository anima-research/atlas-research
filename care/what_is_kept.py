"""What is kept: from the labels alone, the word joined to a care word ("moss-tenders",
"memory keepers") and the phrase after "of" ("keepers of the threshold"). Counted by texts."""
import sqlite3, re, collections, json, sys
STEMS = ['keeper', 'tender', 'steward', 'gardener', 'caretaker', 'custodian', 'warden', 'guardian', 'shepherd', 'curator', 'maintainer', 'cultivator']
db = sqlite3.connect('names/data/roles.db')
pre = {s: collections.defaultdict(set) for s in STEMS}; of = {s: collections.defaultdict(set) for s in STEMS}
bare = {s: set() for s in STEMS}; allt = {s: set() for s in STEMS}; poss = {s: set() for s in STEMS}
for t, n in db.execute("select text_id, norm from labels"):
    for s in STEMS:
        if s not in n: continue
        m = re.search(r"(?:([a-z'’]+)[- ])?(?<![a-z])%ss?(?![a-z])(?: of (?:the |this |that |its |their |an? )?([a-z'’-]+(?: [a-z'’-]+)?))?" % s, n)
        if not m: continue
        allt[s].add(t)
        if m.group(2): of[s][m.group(2)].add(t)
        if m.group(1) and '-' + s in n: pre[s][m.group(1)].add(t)
        elif m.group(1) in ('its', "place's", "world's", "city's"): poss[s].add(t)
        if n in (s, s + 's'): bare[s].add(t)
out = {}
for s in STEMS:
    top = lambda d: ', '.join(f"{k} {len(v)}" for k, v in sorted(d.items(), key=lambda kv: -len(kv[1]))[:14])
    P = set().union(*pre[s].values()) if pre[s] else set(); O = set().union(*of[s].values()) if of[s] else set()
    print(f"\n{s}: texts {len(allt[s])}; bare word in {len(bare[s])}; hyphen-compound in {len(P)} ({len(pre[s])} kinds); 'of X' in {len(O)} ({len(of[s])} kinds)")
    print('   X-%s: %s' % (s, top(pre[s]))); print('   %s of X: %s' % (s, top(of[s])))
