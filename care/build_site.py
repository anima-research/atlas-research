#!/usr/bin/env python3
"""data/care.db -> site/  (static; python3 -m http.server 8798 -d site)
Every number on the pages is computed here from the database or the pilot files."""
import json, os, re, shutil, sqlite3, collections, html, urllib.parse
from common import *

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, 'site'); os.makedirs(SITE, exist_ok=True)
Q5 = ['role', 'relation', 'cost', 'origin', 'fate']
QTEXT = {'role': 'what their role is', 'relation': 'how they stand to what or whom they care for',
         'cost': 'what it costs them', 'origin': 'where they came from', 'fate': 'what becomes of them'}
TEXT_URL = 'https://atlas.lari-island.ai/research/names/text.html?id='
db = sqlite3.connect(os.path.join(HERE, 'data/care.db')); s = snap()
ndb = sqlite3.connect(os.path.join(HERE, '../names/data/names.db'))
esc = html.escape
dump = lambda name, obj: json.dump(obj, open(os.path.join(SITE, name), 'w'), ensure_ascii=False, separators=(',', ':'))
pct = lambda x: '' if x is None else round(100 * x, 1)

for f in ('style.css', 'table.js'):
    shutil.copy(os.path.join(HERE, '../names/site', f), os.path.join(SITE, f))
open(os.path.join(SITE, 'style.css'), 'a').write("""
.card{border:1px solid #ddd;margin:10px 0;padding:8px 12px;max-width:980px}
.card h3{font-size:15px;margin:0 0 2px} .card .meta{font-size:12px;color:#555;margin-bottom:6px}
.card blockquote{font:15px/1.5 Georgia,serif;white-space:normal} .card blockquote sup{color:#888;font:11px system-ui}
.controls{font-size:13px;margin:8px 0;max-width:980px} .controls select,.controls input{font-size:13px;margin-right:10px;max-width:260px}
.qtabs a{margin-right:14px} .qtabs a.on{font-weight:700;text-decoration:none;color:#222}
.q h2{margin-top:1.1em} .none{color:#888;font-style:italic}
.tiles{display:flex;flex-wrap:wrap;gap:10px;max-width:1100px}
.tile{flex:1 1 150px;border:1px solid #bbb;padding:10px 12px;text-decoration:none;color:#222;background:#fafafa}
.tile:hover{background:#eef4ff;border-color:#7a9bd8} .tile b{display:block;font-size:17px;color:#1a4fb0}
.tile span{display:block;margin:2px 0 8px} .tile i{font-style:normal;font-size:12px;color:#555}
td.bar{background:linear-gradient(to right,#dbe9ff var(--w),transparent var(--w))}
""")

NAV = ("<nav><b>Keepers, tenders, guardians</b> &nbsp; <a href='index.html'>Overview</a><a href='findings.html'><b>Findings</b></a>"
       + ''.join(f"<a href='read.html?q={q}'>{q.capitalize()}</a>" for q in Q5) +
       "<a href='portrait.html'>Portraits</a><a href='kinds.html'>Kinds</a><a href='weave.html'>Weave</a>"
       "<a href='beings.html'>Beings</a><a href='writers.html'>Writers</a><a href='words.html'>Words</a>"
       "<a href='kept.html'>What is kept</a><a href='method.html'>Method</a>"
       "<div>A study of the Atlas creature texts, release 15 &middot; <a href='https://atlas.lari-island.ai/research/names/'>names and roles</a></div></nav>")

def page(name, title, body, script=''):
    open(os.path.join(SITE, name), 'w').write(
        "<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>{esc(title)} — Atlas care study</title><link rel=stylesheet href='style.css'><script src='table.js'></script></head><body>{NAV}"
        f"<h1>{esc(title)}</h1>{body}<script>{script}</script></body></html>")

# ---------- data ----------
texts = {t: (m, n, nb) for t, m, n, nb in db.execute("select text_id, model, n_sentences, n_beings from texts")}
beings = db.execute("select id, text_id, model, called, names, words, n_role, n_relation, n_cost, n_origin, n_fate from beings order by id").fetchall()
import weave
WV = {'solo': 's', 'stacked': 'k', 'ensemble': 'e'}
rows = [[b[0], b[1], b[3], '; '.join(json.loads(b[4])), b[5], b[2], texts[b[1]][1], *b[6:], WV.get(weave.kind.get(b[1]) if b[5] else None, '')] for b in beings]
dump('beings.json', rows)   # id, text, called, names, words, writer, sentences in text, role, relation, cost, origin, fate, weave (s solo, k stacked, e ensemble)
cache = {}
def sent(t, a, b):
    if t not in cache:
        if len(cache) > 50: cache.clear()
        cache[t] = s.execute("select text from texts where id=?", (t,)).fetchone()[0]
    return re.sub(r'\s+', ' ', cache[t][a:b]).strip()
byq = {q: collections.defaultdict(list) for q in Q5}
for bid, t, q, no, a, b in db.execute("select being_id, text_id, question, no, start, end from sentences order by text_id, being_id, no"):
    byq[q][bid].append([no, sent(t, a, b)])
for q in Q5: dump(f'q_{q}.json', byq[q])
buckets = collections.defaultdict(dict)
for q in Q5:
    for bid, v in byq[q].items(): buckets[bid // 1000].setdefault(bid, {})[q] = v
for k, v in buckets.items(): dump(f'b_{k}.json', v)

n_beings = len(beings); n_texts = len({b[1] for b in beings})
corpus_by_model = dict(ndb.execute("select model, count(*) from text_cov where flag is null or flag='' group by 1"))
n_corpus = sum(corpus_by_model.values()); n_asked = len(texts)
share = {q: db.execute(f"select avg(n_{q}>0) from beings").fetchone()[0] for q in Q5}
n_sent = {q: sum(len(v) for v in byq[q].values()) for q in Q5}

# ---------- overview ----------
qrows = ''.join(f"<tr><td><a href='read.html?q={q}'>{q}</a></td><td>{QTEXT[q]}</td><td class=num>{sum(1 for b in beings if b[6 + i] > 0):,}</td>"
                f"<td class='num bar' style='--w:{pct(share[q])}%'>{pct(share[q])}%</td><td class=num>{n_sent[q]:,}</td></tr>" for i, q in enumerate(Q5))
tiles = ''.join(f"<a class=tile href='read.html?q={q}'><b>{q.capitalize()}</b><span>{QTEXT[q]}</span>"
                f"<i>{sum(1 for b in beings if b[6 + i] > 0):,} beings &middot; {pct(share[q])}% &middot; {n_sent[q]:,} sentences</i></a>" for i, q in enumerate(Q5))
per = collections.Counter(nb for _, _, nb in texts.values())
page('index.html', 'Keepers, tenders, guardians in the Atlas', f"""
<p>The Atlas holds {n_corpus:,} texts in which a language model answers what lives in an imagined place it has just described.
In {n_texts:,} of them ({pct(n_texts / n_corpus)}%) some inhabitant is given one of twelve names or roles of care:
{', '.join(STEMS)}. This site collects what those texts say about the ones so named.</p>
<p>The unit is a <b>being</b>: an inhabitant, or a kind of inhabitant, that one or more of these words are given to in one text.
There are {n_beings:,} of them, by {len({b[2] for b in beings})} writers. For each, a reader model marked the sentences of the text that answer five questions.
Nothing here is paraphrased: every line shown is a sentence of the text.</p>
<h2>Five questions</h2>
<div class=tiles>{tiles}</div>
<p class=small>Each opens the sentences of the texts under that question, being by being, with filters by word and by writer. "With an answer" means the reader put at least one sentence of the text under the question. A text that says nothing of a cost is counted as saying nothing.</p>
<h2>Where to go</h2>
<ul><li><a href='findings.html'><b>Findings</b></a>: what the study has found so far, each with what it rests on and what could undo it.</li>
<li><a href='portrait.html'>Portraits</a>: pick a writer, a word, or both, and see its numbers against everyone else and its own sentences. For example
<a href='portrait.html?m=google/*&q=cost'>what the Google models say of the cost</a>, or <a href='portrait.html?w=gardener&q=fate'>what becomes of gardeners</a>.</li>
<li><a href='kinds.html'>Kinds</a>: the kinds of answer to each question, found by two readers on separate samples.</li>
<li><a href='weave.html'>Weave</a>: whether a keeper stands alone in its text, carries several of the words, or is one of several.</li>
<li><a href='beings.html'>Beings</a>: all {n_beings:,} in one table; a row opens the being with everything the text says of it.</li>
<li><a href='writers.html'>Writers</a>: each model, how often it writes such beings and which questions its texts answer.</li>
<li><a href='words.html'>Words</a>: the twelve words side by side. <a href='kept.html'>What is kept</a>: what stands next to the word.</li>
<li><a href='method.html'>Method</a>: how the set was made, what it was checked against, where it is thin.</li></ul>
<h2>Beings per text</h2>
<p>{', '.join(f'{k}: {v:,} texts' for k, v in sorted((k, v) for k, v in per.items() if k is not None))}.
In {per.get(0, 0)} texts the word is only mentioned and given to no inhabitant; {per.get(None, 0)} answers could not be read.</p>
""")

# ---------- beings ----------
page('beings.html', 'Beings', """
<p>One row per inhabitant that a care word is given to. The numbers in the last five columns are sentences under each question; filter with <code>&gt;0</code> to keep the beings whose text answers it.
Click a name to open the being.</p><div id=t><span class=small>loading…</span></div>""", f"""
fetch('beings.json').then(r=>r.json()).then(function(B){{
  document.getElementById('t').innerHTML='';
  makeTable(document.getElementById('t'), {{pageSize:150, sort:[0,1], columns:[
    {{title:'#',type:'num'}},{{title:'called',type:'html',tip:'what the text calls it'}},{{title:'care names given to it',type:'text'}},
    {{title:'words',type:'text',tip:'which of the twelve words'}},{{title:'weave',type:'text',tip:'solo: the only such being in its text, one word; stacked: the only one, several words; ensemble: one of several'}},{{title:'writer',type:'html'}},{{title:'text',type:'html'}},
    {{title:'sentences in text',type:'num'}},{{title:'role',type:'num'}},{{title:'relation',type:'num'}},{{title:'cost',type:'num'}},{{title:'origin',type:'num'}},{{title:'fate',type:'num'}}],
   rows:B.map(function(b){{return [b[0],'<a href="being.html?id='+b[0]+'">'+esc(b[2])+'</a>',b[3],b[4],{{s:'solo',k:'stacked',e:'ensemble'}}[b[12]]||'','<a href="portrait.html?m='+encodeURIComponent(b[5])+'">'+esc(b[5])+'</a>','<a href="{TEXT_URL}'+b[1]+'">'+b[1]+'</a>',b[6],b[7],b[8],b[9],b[10],b[11]];}})}});
}});
function esc(s){{return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;');}}""")

# ---------- being ----------
page('being.html', 'Being', "<div id=b></div>", f"""
var Q={json.dumps(QTEXT)}, id=+new URLSearchParams(location.search).get('id');
function esc(s){{return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;');}}
Promise.all([fetch('beings.json').then(r=>r.json()), fetch('b_'+Math.floor(id/1000)+'.json').then(r=>r.json()), fetch('kt.json').then(r=>r.json())]).then(function(a){{
  var b=a[0].find(function(x){{return x[0]===id;}}), S=a[1][id]||{{}}, h='';
  if(!b){{document.getElementById('b').textContent='No such being.';return;}}
  document.querySelector('h1').textContent=b[2]; document.title=b[2]+' — Atlas care study';
  h+='<table class=kv><tr><td>care names given to it</td><td>'+esc(b[3])+'</td></tr><tr><td>writer</td><td>'+esc(b[5])+'</td></tr>'+
     '<tr><td>text</td><td><a href="{TEXT_URL}'+b[1]+'">'+b[1]+'</a>, '+b[6]+' sentences</td></tr>'+
     (a[2][id]?'<tr><td>cares for</td><td>'+(esc(a[2][id][0].join(', '))||'<span class=none>nothing named</span>')+'</td></tr><tr><td>works against</td><td>'+(esc(a[2][id][1].join(', '))||'<span class=none>nothing named</span>')+'</td></tr>':'')+'</table>';
  var others=a[0].filter(function(x){{return x[1]===b[1]&&x[0]!==id;}});
  if(others.length) h+='<p class=small>Other beings in the same text: '+others.map(function(x){{return '<a href="being.html?id='+x[0]+'">'+esc(x[2])+'</a>';}}).join(' &middot; ')+'</p>';
  h+='<div class=q>'; Object.keys(Q).forEach(function(q){{
    h+='<h2>'+q+': '+Q[q]+'</h2>';
    if(!S[q]) h+='<p class=none>The text says nothing the reader put here.</p>';
    else h+='<div class=card>'+S[q].map(function(x){{return '<blockquote><sup>'+x[0]+'</sup> '+esc(x[1])+'</blockquote>';}}).join('')+'</div>';
  }}); h+='</div>'; document.getElementById('b').innerHTML=h;
}});""")

# ---------- read ----------
page('read.html', 'Read', """
<div class='qtabs' id=tabs></div><p id=what></p>
<div class=controls>word <select id=w></select> writer <select id=m></select> contains <input id=s placeholder='text in the sentences'>
order <select id=o><option value=r>shuffled</option><option value=m>by writer</option><option value=n>most sentences first</option></select>
<button id=again>shuffle again</button></div><div class=tbl-info id=info>loading the sentences…</div><div id=list></div><button id=more>more</button>""", f"""
var Q={json.dumps(QTEXT)}, W={json.dumps(STEMS)}, P=new URLSearchParams(location.search), q=Q[P.get('q')]?P.get('q'):'cost', shown=40, seed=1;
function esc(s){{return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;');}}
document.getElementById('tabs').innerHTML=Object.keys(Q).map(function(k){{return '<a href="read.html?q='+k+'"'+(k===q?' class=on':'')+'>'+k+'</a>';}}).join('');
document.getElementById('what').innerHTML='The sentences the reader put under <b>'+Q[q]+'</b>, being by being.';
var side=P.get('against')?1:0, noun=(P.get('against')||P.get('for')||'').toLowerCase(), only=true;
Promise.all([fetch('beings.json').then(r=>r.json()), fetch('q_'+q+'.json').then(r=>r.json()), noun?fetch('kt.json').then(r=>r.json()):Promise.resolve(null)]).then(function(a){{
  var KT=a[2], B=a[0].filter(function(b){{return a[1][b[0]]&&(!noun||(KT[b[0]]&&KT[b[0]][side].indexOf(noun)>=0));}}), S=a[1], cm={{}};
  if(noun){{document.getElementById('what').innerHTML='Beings whose text says they '+(side?'work against':'care for')+' <b>'+esc(noun)+'</b>, with the sentences about their work that hold the word. '+
     '<label><input type=checkbox id=allS> show all their sentences</label> &middot; <a href="kept.html#'+(side?'against':'text')+'">back to the table</a>';
     document.getElementById('allS').onchange=function(e){{only=!e.target.checked; draw();}};
     document.getElementById('tabs').style.display='none';}}
  function mark(t){{if(!noun) return esc(t); var i=t.toLowerCase().indexOf(noun); return i<0?esc(t):esc(t.slice(0,i))+'<mark>'+esc(t.slice(i,i+noun.length))+'</mark>'+esc(t.slice(i+noun.length));}}
  B.forEach(function(b){{cm[b[5]]=(cm[b[5]]||0)+1; b.lc=S[b[0]].map(function(x){{return x[1];}}).join(' ').toLowerCase();}});
  var w=document.getElementById('w'), m=document.getElementById('m');
  w.innerHTML='<option value="">any of the twelve</option>'+W.map(function(x){{return '<option>'+x+'</option>';}}).join('');
  m.innerHTML='<option value="">any writer</option>'+Object.keys(cm).sort().map(function(x){{return '<option value="'+x+'">'+x+' ('+cm[x]+')</option>';}}).join('');
  if(P.get('w')) w.value=P.get('w'); if(P.get('m')) m.value=P.get('m');
  function rnd(i){{var x=Math.sin(i*9301+seed*49297)*233280; return x-Math.floor(x);}}
  function draw(){{
    var fw=w.value, fm=m.value, fs=document.getElementById('s').value.trim().toLowerCase(), o=document.getElementById('o').value;
    var L=B.filter(function(b){{return (!fw||(' '+b[4]+' ').indexOf(' '+fw+' ')>=0)&&(!fm||b[5]===fm)&&(!fs||b.lc.indexOf(fs)>=0);}});
    if(o==='r') L.sort(function(x,y){{return rnd(x[0])-rnd(y[0]);}}); else if(o==='m') L.sort(function(x,y){{return x[5]<y[5]?-1:x[5]>y[5]?1:x[0]-y[0];}});
    else L.sort(function(x,y){{return S[y[0]].length-S[x[0]].length;}});
    document.getElementById('info').textContent=L.length.toLocaleString()+' beings; showing '+Math.min(shown,L.length);
    document.getElementById('list').innerHTML=L.slice(0,shown).map(function(b){{
      return '<div class=card><h3><a href="being.html?id='+b[0]+'">'+esc(b[2])+'</a></h3><div class=meta>'+esc(b[3])+' &middot; '+esc(b[5])+' &middot; text <a href="{TEXT_URL}'+b[1]+'">'+b[1]+'</a></div>'+
        S[b[0]].filter(function(x){{return !noun||!only||x[1].toLowerCase().indexOf(noun)>=0;}}).map(function(x){{return '<blockquote><sup>'+x[0]+'</sup> '+mark(x[1])+'</blockquote>';}}).join('')+'</div>';}}).join('');
    document.getElementById('more').style.display=shown<L.length?'':'none';
  }}
  [w,m,document.getElementById('o')].forEach(function(e){{e.onchange=function(){{shown=40;draw();}};}});
  document.getElementById('s').oninput=function(){{shown=40;draw();}};
  document.getElementById('again').onclick=function(){{seed++;shown=40;draw();}};
  document.getElementById('more').onclick=function(){{shown+=80;draw();}};
  draw();
}});""")

# ---------- writers ----------
W = collections.defaultdict(lambda: collections.Counter())
for b in beings:
    w = W[b[2]]; w['beings'] += 1
    for i, q in enumerate(Q5): w[q] += b[6 + i] > 0
tm = collections.defaultdict(set); sl = collections.defaultdict(list)
for b in beings: tm[b[2]].add(b[1])
for t, (m, n, nb) in texts.items(): sl[m].append(n)
wk = collections.defaultdict(collections.Counter)
for t, bs in weave.T.items(): wk[bs[0][2]][weave.kind[t]] += 1
wrows = [[f"<a href='portrait.html?m={esc(m)}'>{esc(m)}</a>", corpus_by_model.get(m, 0), len(tm[m]), pct(len(tm[m]) / corpus_by_model[m]) if corpus_by_model.get(m) else '', w['beings'],
          round(sorted(sl[m])[len(sl[m]) // 2]), *[pct(w[q] / w['beings']) for q in Q5], *[pct(wk[m][k] / max(1, sum(wk[m].values()))) for k in ('solo', 'stacked', 'ensemble')]] for m, w in W.items()]
page('writers.html', 'Writers', """
<p>One row per model that wrote the texts. "Care texts" are its texts in which a being carries one of the twelve words; the five percentages are the share of its beings whose text answers the question.
Small rows move a lot: filter <code>beings</code> with <code>&gt;=60</code> before comparing. A writer's name opens its portrait.</p>
<p class=small>Longer texts answer more questions: across all writers the share of beings with a cost rises from the shortest eighth of texts to the longest (see Method). The median length is given so that rows can be compared within a band.</p><div id=t></div>""",
     "makeTable(document.getElementById('t'),{pageSize:200,sort:[4,-1],columns:[{title:'writer',type:'html'},{title:'texts in corpus',type:'num'},{title:'care texts',type:'num'},"
     "{title:'% of its texts',type:'num'},{title:'beings',type:'num'},{title:'median sentences',type:'num',tip:'median length of its care texts'},"
     "{title:'role %',type:'num'},{title:'relation %',type:'num'},{title:'cost %',type:'num'},{title:'origin %',type:'num'},{title:'fate %',type:'num'},{title:'solo %',type:'num',tip:'share of its care texts with one being and one word'},{title:'stacked %',type:'num',tip:'one being, several words'},{title:'ensemble %',type:'num',tip:'several beings'}],rows:" + json.dumps(wrows) + "});")

# ---------- words ----------
def band(lo, hi): return [b for b in beings if lo <= texts[b[1]][1] <= hi]
B3060 = band(30, 60)
def within(w, i):
    d = wt = 0
    for m in W:
        a = [b for b in beings if b[2] == m and w in b[5].split()]; c = [b for b in beings if b[2] == m and w not in b[5].split()]
        if len(a) < 8 or len(c) < 8: continue
        k = min(len(a), len(c)); wt += k; d += k * (sum(b[6 + i] > 0 for b in a) / len(a) - sum(b[6 + i] > 0 for b in c) / len(c))
    return round(100 * d / wt, 1) if wt else None
allcost = sum(b[8] > 0 for b in beings) / len(beings)
WITHIN = {w: {q: within(w, i) for i, q in enumerate(Q5)} for w in STEMS}
wd = []
for w in STEMS:
    g = [b for b in beings if w in b[5].split()]; g2 = [b for b in B3060 if w in b[5].split()]
    wd.append([f"<a href='portrait.html?w={w}'>{w}</a>", len(g), len({b[1] for b in g}), len({b[2] for b in g}), *[pct(sum(b[6 + i] > 0 for b in g) / len(g)) for i in range(5)],
               pct(sum(b[8] > 0 for b in g2) / len(g2)), round(100 * (sum(b[8] > 0 for b in g) / len(g) - sum(b[8] > 0 for b in beings if w not in b[5].split()) / sum(1 for b in beings if w not in b[5].split())), 1), WITHIN[w]['cost']])
combo = collections.Counter(b[5] for b in beings if ' ' in b[5])
page('words.html', 'The twelve words', f"""
<p>A being is counted under a word when the word stands in one of the care names the text gives it. A being with several of the words is counted under each.</p><div id=t></div>
<p class=small>"cost %, texts of 30 to 60 sentences" repeats the cost column inside one band of length, since longer texts answer more questions.
The last two columns separate the word from the writers who favour it. "Cost, against other words" is the plain difference in percentage points between beings with the word and all beings without it.
"Inside one writer" takes each writer with at least 8 beings on either side, compares that writer's beings with the word to its beings without, and averages. Where the first is large and the second near zero, the difference belongs to the writers, not to the word; guardian is the clear case. A word opens its portrait.</p>
<h2>Words given together</h2><p>{sum(combo.values()):,} beings carry more than one of the words. Most frequent sets:
{'; '.join(f'{k.replace(" ", " + ")} ({v:,})' for k, v in combo.most_common(14))}.</p>""",
     "makeTable(document.getElementById('t'),{pageSize:50,sort:[1,-1],columns:[{title:'word',type:'html'},{title:'beings',type:'num'},{title:'texts',type:'num'},{title:'writers',type:'num'},"
     "{title:'role %',type:'num'},{title:'relation %',type:'num'},{title:'cost %',type:'num'},{title:'origin %',type:'num'},{title:'fate %',type:'num'},"
     "{title:'cost %, texts of 30 to 60 sentences',type:'num'},{title:'cost, against other words',type:'num'},{title:'cost, inside one writer',type:'num'}],rows:" + json.dumps(wd) + "});")

# ---------- what is kept ----------
rdb = roles(); pre = collections.defaultdict(set); of = collections.defaultdict(set)
for t, n in rdb.execute("select text_id, norm from labels"):
    for m in re.finditer(r"(?:([a-z'’]+)-)?(?<![a-z])(%s)s?(?![a-z])(?: of (?:the |this |that |its |their |an? )?([a-z'’-]+(?: [a-z'’-]+)?))?" % '|'.join(STEMS), n):
        if m.group(1): pre[(m.group(2), m.group(1))].add(t)
        if m.group(3): of[(m.group(2), m.group(3))].add(t)
krows = [[w, 'X-' + w, x, len(v)] for (w, x), v in pre.items() if len(v) >= 2] + [[w, w + ' of X', x, len(v)] for (w, x), v in of.items() if len(v) >= 2]
KEPT = json.load(open(os.path.join(HERE, 'data/kept.json')))       # care name -> nouns that say what is kept (kept_ask.py)
name_texts = collections.defaultdict(set)
for t, n in rdb.execute("select text_id, norm from labels"):
    if n in KEPT: name_texts[n].add(t)
NOUN = collections.defaultdict(lambda: {'t': set(), 'w': collections.defaultdict(set), 'names': collections.Counter()})
for n, nouns in KEPT.items():
    ws = {m.group(1) for m in WORD.finditer(n)}
    for x in set(nouns):
        NOUN[x]['t'] |= name_texts[n]; NOUN[x]['names'][n] += len(name_texts[n])
        for w in ws: NOUN[x]['w'][w] |= name_texts[n]
nrows = [[x, len(v['t']), len(v['w']), '; '.join(k for k, _ in v['names'].most_common(3)), *[len(v['w'][w]) if w in v['w'] else '' for w in STEMS]] for x, v in NOUN.items() if len(v['t']) >= 2]
n_names = len(KEPT); n_with = sum(1 for v in KEPT.values() if v)
def aggregate():
    """X as written (one or two words), across all twelve care words and both forms; distinct texts"""
    A = collections.defaultdict(lambda: {'pre': set(), 'of': set(), 'w': collections.defaultdict(set)})
    for form, d in (('pre', pre), ('of', of)):
        for (w, x), v in d.items(): A[x][form] |= v; A[x]['w'][w] |= v
    return [[k, len(v['pre'] | v['of']), len(v['w']), len(v['pre']), len(v['of']), *[len(v['w'][w]) if w in v['w'] else '' for w in STEMS]] for k, v in A.items() if len(v['pre'] | v['of']) >= 2]
KT = json.load(open(os.path.join(HERE, 'data/kept_text.json')))      # being id -> {for: [...], against: [...]} from its role sentences (kept_text.py)
dump('kt.json', {k: [v['for'], v['against']] for k, v in KT.items() if v['for'] or v['against']})
bwords = {str(b[0]): b[5].split() for b in beings}
def side_table(side, least=3):
    A = collections.defaultdict(lambda: {'b': set(), 'w': collections.defaultdict(set)})
    for bid, v in KT.items():
        for x in set(v[side]):
            A[x]['b'].add(bid)
            for w in bwords.get(bid, []): A[x]['w'][w].add(bid)
    return A, [[f"<a href='read.html?q=role&{side}={urllib.parse.quote(x)}'>{esc(x)}</a>", len(v['b']), len(v['w']), *[len(v['w'][w]) if w in v['w'] else '' for w in STEMS]] for x, v in A.items() if len(v['b']) >= least]
TF, tf_rows = side_table('for'); TA, ta_rows = side_table('against')
n_kt = len(KT); n_for = sum(1 for v in KT.values() if v['for']); n_against = sum(1 for v in KT.values() if v['against'])
wcols = ','.join("{title:'%s',type:'num'}" % w for w in STEMS)
page('kept.html', 'What is kept', f"""
<p>What the keepers keep, seen two ways. <b>By the name</b>: what the name itself says is kept (<i>moss-tenders</i>, <i>keepers of the threshold</i>). <b>By the text</b>: what the sentences about the being's work say it cares for,
and, apart from that, what they say it works against. A keeper of chaos and a keeper who holds chaos off are on different sides.</p>
<p class=qtabs id=views><a href='#noun' data-v=noun>kept, by the name</a><a href='#text' data-v=text>cared for, by the text</a><a href='#against' data-v=against>worked against, by the text</a><a href='#phrase' data-v=phrase>names by pattern</a><a href='#forms' data-v=forms>every form</a></p>
<p class=small id=note></p><div id=t></div>""",
     "var V={noun:{note:" + json.dumps(
         f"A small model (openai/gpt-6-luna) was given each of the {n_names:,} distinct care names and asked for the main noun of each thing kept, as written in the name, without the words that describe it: "
         "<i>keepers of the ancient knowledge etched into the stone</i> gives <b>knowledge</b>; <i>self-appointed curators of moisture and light</i> gives <b>moisture</b> and <b>light</b>; <i>silent curators</i> gives nothing. "
         f"A noun is accepted only if it stands in the name. {n_with:,} names say what is kept. Whichever of the twelve words keeps it and in whatever form (hyphen, of, or two words side by side), it is counted here once per text. "
         "Singular and plural are not folded (<i>memory</i>, <i>memories</i>). The instruction is in <code>care/prompt_kept.md</code>.") +
     ",cols:[{title:'kept',type:'text'},{title:'texts',type:'num',tip:'distinct texts, all twelve words, all forms'},{title:'care words',type:'num',tip:'how many of the twelve keep it'},{title:'as in',type:'text',tip:'the three most frequent names'}," + wcols + "],rows:" + json.dumps(nrows) + ",sort:[1,-1]},"
     "text:{note:" + json.dumps(
         f"For each of the {n_kt:,} beings with sentences under the question of its role, a small model (openai/gpt-6-luna) read those sentences and listed what the being cares for and, separately, what it works against, as the main noun of each, exactly as written. "
         f"A noun is accepted only if it stands in the sentences. {n_for:,} beings care for something named; counted by beings, nouns of fewer than three beings left out. A noun opens the sentences it comes from. The instruction is in <code>care/prompt_kept_text.md</code>.") +
     ",cols:[{title:'cared for',type:'html',tip:'opens the sentences'},{title:'beings',type:'num'},{title:'care words',type:'num'}," + wcols + "],rows:" + json.dumps(tf_rows) + ",sort:[1,-1]},"
     "against:{note:" + json.dumps(
         f"From the same reading: what the sentences say the being holds off, removes, prevents, or protects what it keeps from. {n_against:,} of the {n_kt:,} beings work against something named. "
         "The same noun can stand on both sides in different texts: growth, moss and decay are cared for by some and worked against by others.") +
     ",cols:[{title:'worked against',type:'html',tip:'opens the sentences'},{title:'beings',type:'num'},{title:'care words',type:'num'}," + wcols + "],rows:" + json.dumps(ta_rows) + ",sort:[1,-1]},"
     "phrase:{note:'By pattern, without a model: the word joined to a care word by a hyphen, and the one or two words after \"of\", as written. A two-word capture can stop before the noun (<i>keepers of the ancient ...</i>), which is why the first view asks a reader for the noun instead.',"
     "cols:[{title:'X',type:'text'},{title:'texts',type:'num'},{title:'care words',type:'num'},{title:'X-word',type:'num',tip:'texts with the hyphen form'},{title:'word of X',type:'num',tip:'texts with the of form'}," + wcols + "],rows:" + json.dumps(aggregate()) + ",sort:[1,-1]},"
     "forms:{note:'By pattern: one row per care word, form and X.',cols:[{title:'word',type:'text'},{title:'form',type:'text'},{title:'X',type:'text'},{title:'texts',type:'num'}],rows:" + json.dumps(krows) + ",sort:[3,-1]}};"
     "function show(v){if(!V[v])v='noun';document.getElementById('t').innerHTML='';document.getElementById('note').innerHTML=V[v].note;"
     "Array.prototype.forEach.call(document.querySelectorAll('#views a'),function(a){a.className=a.dataset.v===v?'on':'';});"
     "makeTable(document.getElementById('t'),{key:v,pageSize:200,sort:V[v].sort,columns:V[v].cols,rows:V[v].rows});}"
     "window.onhashchange=function(){show(location.hash.slice(1));};show(location.hash.slice(1));")

# ---------- method ----------
def pilot():
    H = json.load(open(os.path.join(HERE, 'pilot_hand.json'))); out = []
    for m in ('gpt-6-luna', 'gpt-6-sol', 'claude-sonnet-5.5'):
        R = {json.loads(l)['text']: json.loads(l) for l in open(os.path.join(HERE, f'out/pilot_{m}.jsonl'))}; agree = n = 0
        per = {q: 0 for q in Q5}
        for t in R:
            for q in Q5:
                hs = {i for h in H[str(t)] for i in h[q]}; ms = {i for x in R[t]['inhabitants'] for i in x[q]}
                n += 1; ok = bool(hs) == bool(ms); agree += ok; per[q] += ok
        out.append((m, agree, n, per))
    return out
R = sorted(((texts[b[1]][1], b[8] > 0, b[9] > 0, b[10] > 0) for b in beings)); k = len(R) // 8
lenrows = ''.join(f"<tr><td>{g[0][0]} to {g[-1][0]}</td><td class=num>{pct(sum(r[1] for r in g) / len(g))}%</td><td class=num>{pct(sum(r[2] for r in g) / len(g))}%</td><td class=num>{pct(sum(r[3] for r in g) / len(g))}%</td></tr>"
                  for g in (R[i * k:(i + 1) * k] for i in range(8)))
prow = ''.join(f"<tr><td>{m}</td><td class=num>{a} of {n}</td>" + ''.join(f"<td class=num>{p[q]} of 10</td>" for q in Q5) + "</tr>" for m, a, n, p in pilot())
unread = sum(1 for v in texts.values() if v[2] is None)
page('method.html', 'Method', f"""
<h2>Which texts</h2>
<p>The <a href='https://atlas.lari-island.ai/research/names/method.html'>names and roles set</a> lists, for every text of release 15, each name or role the text gives an inhabitant.
A text is taken here when one of those labels holds one of the twelve words as a whole word: {', '.join(STEMS)}. {n_asked:,} texts.</p>
<h2>The question</h2>
<p>One request per text to one reader model (anthropic/claude-sonnet-5.5). The sentences of the text are numbered by script; the reader answers with sentence numbers, so every line on this site is the text's own sentence. The instruction, in full:</p>
<pre>{esc(open(os.path.join(HERE, 'prompt_v1.md')).read().strip())}</pre>
<p>{unread} answers could not be read. In {sum(1 for v in texts.values() if v[2] == 0)} texts the reader found the word only mentioned.</p>
<h2>What it was checked against</h2>
<p>Ten care texts drawn at random were read whole and marked by hand before any request (<code>pilot_hand.json</code>); three models then got the same instruction.
The table counts, of 50 answers (ten texts, five questions), how often the model and the hand marking agree on whether the text answers the question at all, and the same per question.</p>
<table class=kv><tr><th>reader</th><th>agree</th>{''.join(f'<th>{q}</th>' for q in Q5)}</tr>{prow}</table>
<p>Thirty more random texts were then read by the chosen reader, and the sentences it put under cost and origin were read by eye. Under cost they were mostly a cost
(a limb given up, memories let go, "a loneliness of total recollection", no bed and no hearth); in two or three of thirty they were not (a hot metabolism in thin air).
Under origin the range is wide, and a tradition handed down counts as an origin here.</p>
<h2>Where it is thin</h2>
<ul>
<li>The hand marking is by the same model family as the reader, so their agreement is partly a shared view.</li>
<li>"The text answers the question" means the reader put at least one sentence there. It is a reading, not a measurement; the error on thirty texts was a few sentences too many, not too few, and it was not measured on more.</li>
<li>Relation is answered for nearly every being and the sentences chosen for it vary most between readers. It is for reading, not for counting.</li>
<li>Longer texts answer more questions. By length of text, eight equal groups of beings:
<table class=kv><tr><th>sentences in text</th><th>cost</th><th>origin</th><th>fate</th></tr>{lenrows}</table></li>
<li>A care role in a sentence that neither the who-quotes nor the patterns of the names study touched is not in the names set, and so not here.</li>
<li>Denials ("she is not a keeper of anything") and comparisons ("like a gardener") are not collected.</li>
<li>There is no comparison group: nothing here says whether builders or hunters are written with a cost more or less often.</li>
</ul>
<h2>Files</h2>
<p><code>care/common.py</code> (the words, sentence numbering), <code>ask.py</code>, <code>batch_care.py</code>, <code>build.py</code> (answers to <code>data/care.db</code>), <code>build_site.py</code>, <code>what_is_kept.py</code>.</p>
""")
exec(open(os.path.join(HERE, 'site_more.py')).read())
print('site built:', n_beings, 'beings;', {f: os.path.getsize(os.path.join(SITE, f)) // 1024 for f in sorted(os.listdir(SITE)) if f.endswith('.json') and not f.startswith('b_')}, 'KB')
