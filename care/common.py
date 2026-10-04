"""Shared pieces for the care study: the twelve words, the texts that carry them, sentence numbering."""
import os, re, sqlite3, collections
HERE = os.path.dirname(os.path.abspath(__file__))
STEMS = ['keeper', 'tender', 'steward', 'gardener', 'caretaker', 'custodian', 'warden', 'guardian', 'shepherd', 'curator', 'maintainer', 'cultivator']
WORD = re.compile(r"(?<![a-z])(%s)s?(?![a-z])" % '|'.join(STEMS))
roles = lambda: sqlite3.connect(os.path.join(HERE, '../names/data/roles.db'))
snap = lambda: sqlite3.connect(os.path.join(HERE, '../names/data/snapshot_r15.sqlite'))

def care_labels():
    """text_id -> list of distinct labels (as written, first form seen) that hold one of the words"""
    out = collections.defaultdict(dict)
    for t, lab, n in roles().execute("select text_id, label, norm from labels order by text_id, start"):
        if WORD.search(n): out[t].setdefault(n, lab)
    return {t: list(d.values()) for t, d in out.items()}

SENT = re.compile(r'[^\n]+?(?:[.!?]["”’)*_]*(?=\s+["“*_(]*[A-Z])|$)', re.M)
def sentences(text):
    """[(start, end)] of sentences and heading lines, in order"""
    out = []
    for m in SENT.finditer(text):
        s = m.group(); a = m.start() + len(s) - len(s.lstrip())
        if s.strip(' \t-*_#=|'): out.append((a, m.end()))
    return out
