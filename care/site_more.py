# Run inside build_site.py (shares its names): portraits, weave, kinds.
import itertools

# ---------- extra.json: what the portrait page needs beyond beings.json ----------
kept_top = {}
for w in STEMS:
    a_ = sorted(((len(v['w'][w]), x) for x, v in NOUN.items() if len(v['w'].get(w, ())) >= 2), reverse=True)[:30]
    kept_top[w] = [[x, n] for n, x in a_]
dump('extra.json', {'within': WITHIN, 'kept': kept_top, 'corpus': corpus_by_model, 'care_texts': {m: len(v) for m, v in tm.items()}})

open(os.path.join(SITE, 'style.css'), 'a').write("""
.pick{font-size:14px;margin:8px 0 4px;max-width:980px} .pick select{font-size:14px;margin-right:14px;max-width:330px}
.cols{display:flex;flex-wrap:wrap;gap:8px 34px;max-width:1150px} .cols>div{flex:1 1 430px;min-width:300px;max-width:560px}
.bars{border-collapse:collapse;width:100%;font-size:13px} .bars td{border:0;padding:2px 6px 2px 0;vertical-align:middle}
.bars td.l{white-space:nowrap;width:1%} .bars td.n{white-space:nowrap;width:1%;text-align:right;font-variant-numeric:tabular-nums;color:#333}
.bars .t{background:#f0f0f0;height:9px;margin:1px 0} .bars .t i{display:block;height:9px;background:#1a4fb0} .bars .t.r i{background:#b9b9b9}
.bars a{cursor:pointer} .legend{font-size:12px;color:#555;margin:2px 0 6px} .legend b{display:inline-block;width:10px;height:10px;margin:0 4px 0 10px;vertical-align:-1px}
table.mx td,table.mx th{text-align:right;padding:2px 5px;font-size:12px} table.mx th:first-child,table.mx td:first-child{text-align:left}
.md table{width:auto;max-width:1400px;margin:8px 0} .md td,.md th{font-size:13px} .md blockquote{font:15px/1.5 Georgia,serif}
.md li{margin:3px 0}
""")

# ---------- portrait ----------
page('portrait.html', 'Portrait', """
<p class=small>Pick a writer, a word, or both. Blue is the selection; grey is every other being in the set. Counts are beings.</p>
<div class=pick>writer <select id=pm></select> word <select id=pw></select> <span class=small id=psum>loading…</span></div>
<div id=body></div>
<div id=reader style='display:none'><h2 id=rh></h2><div class='qtabs' id=rtabs></div>
<div class=controls>contains <input id=rs placeholder='text in the sentences'> <button id=ragain>shuffle again</button></div>
<div class=tbl-info id=rinfo></div><div id=rlist></div><button id=rmore>more</button></div>""", f"""
var Q={json.dumps(QTEXT)}, W={json.dumps(STEMS)}, QI={{role:7,relation:8,cost:9,origin:10,fate:11}}, TEXT='{TEXT_URL}';
var P=new URLSearchParams(location.search), st={{m:P.get('m')||'', w:P.get('w')||'', q:Q[P.get('q')]?P.get('q'):'cost'}}, shown=30, seed=1, B, X, SQ={{}};
function esc(s){{return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;');}}
function fam(x){{return x.split('/')[0];}}
function has(b,w){{return (' '+b[4]+' ').indexOf(' '+w+' ')>=0;}}
function inSel(b){{return (!st.w||has(b,st.w))&&(!st.m||(st.m.slice(-2)==='/*'?fam(b[5])===st.m.slice(0,-2):b[5]===st.m));}}
function pc(a,n){{return n?100*a/n:0;}}
function row(label,a,na,r,nr,href){{var x=pc(a,na),y=pc(r,nr);
  return '<tr><td class=l>'+(href?'<a href="'+href+'">'+label+'</a>':label)+'</td><td><div class=t><i style="width:'+x.toFixed(1)+'%"></i></div><div class="t r"><i style="width:'+y.toFixed(1)+'%"></i></div></td>'+
         '<td class=n>'+x.toFixed(0)+'% <span class=small>('+a.toLocaleString()+')</span></td><td class=n><span class=small>'+y.toFixed(0)+'%</span></td></tr>';}}
function link(o){{var u=new URLSearchParams(); var s=Object.assign({{}},st,o); if(s.m)u.set('m',s.m); if(s.w)u.set('w',s.w); u.set('q',s.q); return 'portrait.html?'+u.toString();}}
function draw(){{
  var S=B.filter(inSel), R=B.filter(function(b){{return !inSel(b);}}), n=S.length, nr=R.length, h='';
  history.replaceState(null,'',link({{}}));
  var name=[st.m?(st.m.slice(-2)==='/*'?st.m.slice(0,-2)+', all models':st.m):'', st.w].filter(Boolean).join(' · ');
  document.querySelector('h1').textContent=name?('Portrait: '+name):'Portrait'; document.title=(name||'Portrait')+' — Atlas care study';
  if(!st.m&&!st.w){{document.getElementById('psum').textContent=''; document.getElementById('body').innerHTML='<p>Nothing picked yet. For example: <a href="portrait.html?m=google/*&q=cost">what the Google models say of the cost</a>, <a href="portrait.html?m=anthropic/claude-sonnet-3&q=role">the roles of care in Claude Sonnet 3</a>, <a href="portrait.html?w=gardener&q=fate">what becomes of gardeners</a>.</p>'; document.getElementById('reader').style.display='none'; return;}}
  var texts={{}}; S.forEach(function(b){{texts[b[1]]=1;}});
  document.getElementById('psum').textContent=n.toLocaleString()+' beings in '+Object.keys(texts).length.toLocaleString()+' texts';
  if(!n){{document.getElementById('body').innerHTML='<p class=none>No being in the set matches.</p>'; document.getElementById('reader').style.display='none'; return;}}
  h+='<div class=legend><b style="background:#1a4fb0"></b>the selection<b style="background:#b9b9b9"></b>all other beings</div><div class=cols>';
  h+='<div><h2>Which questions its texts answer</h2><table class=bars>'+Object.keys(Q).map(function(q){{var i=QI[q];
      return row('<b>'+q+'</b> <span class=small>'+Q[q]+'</span>', S.filter(function(b){{return b[i]>0;}}).length, n, R.filter(function(b){{return b[i]>0;}}).length, nr, link({{q:q}})+'#reader');}}).join('')+'</table>';
  if(st.w&&!st.m){{var wi=X.within[st.w]; h+='<p class=small>Inside one writer, beings called '+st.w+' differ from that writer\\'s other beings by: '+['cost','origin','fate'].map(function(q){{return q+' '+(wi[q]>0?'+':'')+wi[q];}}).join(', ')+' points. Where this is near zero and the bars above differ, the difference belongs to the writers who favour the word.</p>';}}
  var len=S.map(function(b){{return b[6];}}).sort(function(a,b){{return a-b;}}), lr=R.map(function(b){{return b[6];}}).sort(function(a,b){{return a-b;}});
  h+='<p class=small>Median length of the text: '+len[Math.floor(n/2)]+' sentences (others: '+(nr?lr[Math.floor(nr/2)]:'-')+'). Longer texts answer more questions.</p></div>';
  h+='<div><h2>How the roles are woven</h2><table class=bars>'+[['s','solo','the only such being in its text, one word'],['k','stacked','the only one, several words on it'],['e','ensemble','one of several in its text']].map(function(k){{
      return row('<b>'+k[1]+'</b> <span class=small>'+k[2]+'</span>', S.filter(function(b){{return b[12]===k[0];}}).length, n, R.filter(function(b){{return b[12]===k[0];}}).length, nr);}}).join('')+'</table>'+
      '<p class=small>See <a href="weave.html">Weave</a>.</p></div>';
  h+='<div><h2>'+(st.w?'Words given to the same being':'Its words')+'</h2><table class=bars>'+W.filter(function(w){{return w!==st.w;}}).map(function(w){{
      return [w,S.filter(function(b){{return has(b,w);}}).length,R.filter(function(b){{return has(b,w);}}).length];}}).sort(function(a,b){{return b[1]-a[1];}}).map(function(x){{
      return row(x[0],x[1],n,x[2],nr,st.w?null:link({{w:x[0]}}));}}).join('')+'</table></div>';
  if(st.w&&!st.m){{
    var per={{}}; B.forEach(function(b){{var p=per[b[5]]||(per[b[5]]=[0,0]); p[1]++; if(has(b,st.w))p[0]++;}});
    var L=Object.keys(per).filter(function(m){{return per[m][1]>=40;}}).map(function(m){{return [m,per[m][0],per[m][1]];}}).sort(function(a,b){{return b[1]/b[2]-a[1]/a[2];}});
    var one=function(x){{return '<tr><td class=l><a href="'+link({{m:x[0]}})+'">'+esc(x[0])+'</a></td><td><div class=t><i style="width:'+pc(x[1],x[2]).toFixed(1)+'%"></i></div></td><td class=n>'+pc(x[1],x[2]).toFixed(0)+'% <span class=small>('+x[1]+' of '+x[2]+')</span></td></tr>';}};
    h+='<div><h2>Writers who use it most and least</h2><p class=small>Share of a writer\\'s beings that carry the word; writers with 40 beings or more.</p><table class=bars>'+L.slice(0,10).map(one).join('')+'<tr><td colspan=3 class=small>…</td></tr>'+L.slice(-5).map(one).join('')+'</table></div>';
    var K=X.kept[st.w]; h+='<div><h2>What is kept</h2><p class=small>The nouns in its names that say what is kept, with the number of texts. <a href="kept.html">The whole table</a>.</p><p>'+(K.map(function(x){{return esc(x[0])+' '+x[1];}}).join(', ')||'-')+'</p></div>';
  }}
  if(st.m&&st.m.slice(-2)!=='/*'&&X.corpus[st.m]){{h+='<div><h2>How often it writes them</h2><p>'+X.care_texts[st.m]+' of its '+X.corpus[st.m]+' texts in the corpus ('+pc(X.care_texts[st.m],X.corpus[st.m]).toFixed(0)+'%) have a being with one of the twelve words.</p></div>';}}
  h+='</div>'; document.getElementById('body').innerHTML=h; reader(S);
}}
function reader(S){{
  var q=st.q; document.getElementById('reader').style.display=''; document.getElementById('reader').id='reader';
  document.getElementById('rh').innerHTML='In its own words: '+q+' <span class=small>'+Q[q]+'</span>';
  document.getElementById('rtabs').innerHTML=Object.keys(Q).map(function(k){{return '<a href="'+link({{q:k}})+'" data-q="'+k+'"'+(k===q?' class=on':'')+'>'+k+'</a>';}}).join('');
  Array.prototype.forEach.call(document.querySelectorAll('#rtabs a'),function(a){{a.onclick=function(e){{e.preventDefault(); st.q=a.dataset.q; shown=30; draw();}};}});
  document.getElementById('rinfo').textContent='loading the sentences…'; document.getElementById('rlist').innerHTML='';
  (SQ[q]?Promise.resolve(SQ[q]):fetch('q_'+q+'.json').then(function(r){{return r.json();}}).then(function(j){{SQ[q]=j; return j;}})).then(function(J){{
    if(st.q!==q) return;
    var fs=document.getElementById('rs').value.trim().toLowerCase();
    var L=S.filter(function(b){{return J[b[0]]&&(!fs||J[b[0]].map(function(x){{return x[1];}}).join(' ').toLowerCase().indexOf(fs)>=0);}});
    var rnd=function(i){{var x=Math.sin(i*9301+seed*49297)*233280; return x-Math.floor(x);}}; L.sort(function(x,y){{return rnd(x[0])-rnd(y[0]);}});
    document.getElementById('rinfo').textContent=L.length.toLocaleString()+' of its '+S.length.toLocaleString()+' beings have sentences here; showing '+Math.min(shown,L.length);
    document.getElementById('rlist').innerHTML=L.slice(0,shown).map(function(b){{
      return '<div class=card><h3><a href="being.html?id='+b[0]+'">'+esc(b[2])+'</a></h3><div class=meta>'+esc(b[3])+' &middot; '+esc(b[5])+' &middot; text <a href="'+TEXT+b[1]+'">'+b[1]+'</a></div>'+
        J[b[0]].map(function(x){{return '<blockquote><sup>'+x[0]+'</sup> '+esc(x[1])+'</blockquote>';}}).join('')+'</div>';}}).join('')||'<p class=none>Its texts say nothing the reader put under this question.</p>';
    document.getElementById('rmore').style.display=shown<L.length?'':'none';
    document.getElementById('rmore').onclick=function(){{shown+=60; reader(S);}};
    document.getElementById('ragain').onclick=function(){{seed++; shown=30; reader(S);}};
    document.getElementById('rs').oninput=function(){{shown=30; reader(S);}};
  }});
}}
Promise.all([fetch('beings.json').then(function(r){{return r.json();}}), fetch('extra.json').then(function(r){{return r.json();}})]).then(function(a){{
  B=a[0]; X=a[1]; var cm={{}}, cf={{}};
  B.forEach(function(b){{cm[b[5]]=(cm[b[5]]||0)+1; cf[fam(b[5])]=(cf[fam(b[5])]||0)+1;}});
  var pm=document.getElementById('pm'), pw=document.getElementById('pw');
  pm.innerHTML='<option value="">any writer</option>'+Object.keys(cf).sort(function(x,y){{return cf[y]-cf[x];}}).map(function(f){{
    var ms=Object.keys(cm).filter(function(m){{return fam(m)===f;}}).sort();
    return '<optgroup label="'+f+'">'+(ms.length>1?'<option value="'+f+'/*">'+f+', all models ('+cf[f]+')</option>':'')+ms.map(function(m){{return '<option value="'+m+'">'+m+' ('+cm[m]+')</option>';}}).join('')+'</optgroup>';}}).join('');
  pw.innerHTML='<option value="">any of the twelve</option>'+W.map(function(w){{return '<option>'+w+'</option>';}}).join('');
  pm.value=st.m; pw.value=st.w; pm.onchange=function(){{st.m=pm.value; shown=30; draw();}}; pw.onchange=function(){{st.w=pw.value; shown=30; draw();}};
  draw();
}});""")

# ---------- weave ----------
KN = ('solo', 'stacked', 'ensemble')
wB = [b for b in weave.B]
def wstats(rs): return weave.stats(rs) if rs else None
ck = collections.Counter(weave.kind.values()); NT = len(weave.T)
srow = ''
for k, what in (('solo', 'one being in the text, one care word'), ('stacked', 'one being in the text, several care words given to it'), ('ensemble', 'several beings with care words in one text')):
    stt = wstats([b for b in wB if weave.kind[b[1]] == k])
    srow += (f"<tr><td><b>{k}</b></td><td>{what}</td><td class=num>{ck[k]:,}</td><td class=num>{pct(ck[k] / NT)}%</td><td class=num>{stt['n']:,}</td><td class=num>{pct(stt['focus'])}%</td>"
             f"<td class=num>{pct(stt['cost'])}%</td><td class=num>{pct(stt['origin'])}%</td><td class=num>{pct(stt['fate'])}%</td><td class=num>{round(stt['sent'])}</td></tr>")
def within_kind(a, c):
    d = collections.Counter(); wt = 0; g = collections.defaultdict(lambda: collections.defaultdict(list))
    for b in wB: g[b[2]][weave.kind[b[1]]].append(b)
    for m, v in g.items():
        if len(v[a]) < 8 or len(v[c]) < 8: continue
        k = min(len(v[a]), len(v[c])); wt += k; sa, sc = weave.stats(v[a]), weave.stats(v[c])
        for q in ('cost', 'origin', 'fate', 'focus'): d[q] += k * (sa[q] - sc[q])
    return ', '.join(f"{q} {100 * d[q] / wt:+.1f}" for q in ('focus', 'cost', 'origin', 'fate'))
ww_rows = []
for w in STEMS:
    g = [b for b in wB if w in b[3].split()]; parts = {k: [b for b in g if weave.kind[b[1]] == k] for k in KN}; stt = {k: wstats(v) for k, v in parts.items()}
    ww_rows.append([f"<a href='portrait.html?w={w}'>{w}</a>", len(g), *[pct(len(parts[k]) / len(g)) for k in KN], *[pct(stt[k]['focus']) for k in KN], *[pct(stt[k]['cost']) for k in KN], *[pct(stt[k]['fate']) for k in KN]])
wbc = collections.Counter(); pair = collections.Counter(); across = collections.Counter()
for b in wB:
    ws = set(b[3].split()); wbc.update(ws)
    for x, y in itertools.permutations(ws, 2): pair[(x, y)] += 1
for t, bs in weave.T.items():
    for i, j in itertools.combinations(range(len(bs)), 2):
        for p in {tuple(sorted((a, c))) for a in bs[i][3].split() for c in bs[j][3].split() if a != c}: across[p] += 1
def shade(v, top): return f"background:rgba(26,79,176,{min(1, v / top) * 0.55:.2f})"
mx = "<table class=mx><tr><th></th>" + ''.join(f"<th>{w}</th>" for w in STEMS) + "</tr>" + ''.join(
    f"<tr><td><b>{a}</b></td>" + ''.join("<td>·</td>" if a == c else f"<td style='{shade(100 * pair[(a, c)] / wbc[a], 16)}'>{100 * pair[(a, c)] / wbc[a]:.0f}</td>" for c in STEMS) + "</tr>" for a in STEMS) + "</table>"
topa = max(across.values())
mx2 = "<table class=mx><tr><th></th>" + ''.join(f"<th>{w}</th>" for w in STEMS) + "</tr>" + ''.join(
    f"<tr><td><b>{a}</b></td>" + ''.join("<td>·</td>" if a == c else f"<td style='{shade(across[tuple(sorted((a, c)))], topa)}'>{across[tuple(sorted((a, c)))]}</td>" for c in STEMS) + "</tr>" for a in STEMS) + "</table>"
same_words = sum(1 for t, bs in weave.T.items() if weave.kind[t] == 'ensemble' and len({b[3] for b in bs}) == 1)
wr_rows = [[f"<a href='portrait.html?m={esc(m)}'>{esc(m)}</a>", sum(c.values()), *[pct(c[k] / sum(c.values())) for k in KN]] for m, c in wk.items()]
page('weave.html', 'Weave: one keeper, or several', f"""
<p>A text about one gardener is a different thing from a text in which a keeper stands beside a gardener and a tender. Three arrangements, by text:</p>
<table class=kv style='max-width:1150px'><tr><th></th><th></th><th>texts</th><th>share</th><th>beings</th><th>focus</th><th>cost</th><th>origin</th><th>fate</th><th>mean sentences in text</th></tr>{srow}</table>
<p class=small><b>Focus</b> is the share of the text's sentences that the reader listed for the being under any of the five questions. Cost, origin and fate are the share of beings whose text answers the question.</p>
<p>A being that carries several of the words at once is the centre of its text: more of the text is about it, and its origin and fate are told more often. In an ensemble each keeper is one post among several: a tenth of the text, and its fate is told for about a quarter.
This is not an effect of who writes. Inside one writer (writers with at least 8 beings on either side), in percentage points: stacked against solo, {within_kind('stacked', 'solo')}; ensemble against solo, {within_kind('ensemble', 'solo')}.</p>
<p class=small>The arrangements follow how the reader divided the text into beings. Where it took two keepers for one, an ensemble became a stack; how often that happened was not measured. In {same_words:,} of the {ck['ensemble']:,} ensemble texts every being carries the same word or words.</p>
<h2>The twelve words</h2>
<p>Where the beings of each word stand, and what they get there. Keeper, tender and warden are words of trades, found half the time among other keepers; curator, custodian and gardener are more often the one being of the place.</p><div id=t1></div>
<h2>Words on one being</h2>
<p>Of the beings that carry the word in the row, the percentage that also carry the word in the column.</p>{mx}
<h2>Words on different beings of one text</h2>
<p>Pairs of beings in one text, one carrying the row word and the other the column word.</p>{mx2}
<h2>Writers</h2><p>Share of each writer's care texts in each arrangement. Filter <code>care texts</code> with <code>&gt;=60</code> before comparing.</p><div id=t2></div>""",
     "makeTable(document.getElementById('t1'),{pageSize:50,sort:[1,-1],columns:[{title:'word',type:'html'},{title:'beings',type:'num'},{title:'solo %',type:'num'},{title:'stacked %',type:'num'},{title:'ensemble %',type:'num'},"
     "{title:'focus: solo',type:'num'},{title:'stacked',type:'num'},{title:'ensemble',type:'num'},{title:'cost %: solo',type:'num'},{title:'stacked',type:'num'},{title:'ensemble',type:'num'},"
     "{title:'fate %: solo',type:'num'},{title:'stacked',type:'num'},{title:'ensemble',type:'num'}],rows:" + json.dumps(ww_rows) + "});"
     "makeTable(document.getElementById('t2'),{pageSize:200,sort:[1,-1],columns:[{title:'writer',type:'html'},{title:'care texts',type:'num'},{title:'solo %',type:'num'},{title:'stacked %',type:'num'},{title:'ensemble %',type:'num'}],rows:" + json.dumps(wr_rows) + "});")

# ---------- kinds: the two readers' merged accounts ----------
def inline(x):
    x = esc(x, quote=False)
    x = re.sub(r'`([^`]+)`', r'<code>\1</code>', x)
    x = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', x)
    x = re.sub(r'(?<![\w*])\*([^*\n]+)\*(?![\w*])', r'<i>\1</i>', x)
    return x
def md(text, link):
    out = []; lines = text.split('\n'); i = 0; mode = None
    def close():
        nonlocal mode
        if mode: out.append('</%s>' % mode); mode = None
    while i < len(lines):
        l = lines[i]
        if l.startswith('|') and i + 1 < len(lines) and re.match(r'^\|[\s:|-]+\|\s*$', lines[i + 1]):
            close(); cells = lambda r: [c.strip() for c in r.strip().strip('|').split('|')]
            out.append('<div class=tbl-wrap><table><tr>' + ''.join(f'<th style="cursor:default">{inline(c)}</th>' for c in cells(l)) + '</tr>'); i += 2
            while i < len(lines) and lines[i].startswith('|'):
                out.append('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in cells(lines[i])) + '</tr>'); i += 1
            out.append('</table></div>'); continue
        m = re.match(r'^(#{1,4})\s+(.*)', l)
        if m: close(); n = min(4, len(m.group(1)) + 1); out.append(f'<h{n}>{inline(m.group(2))}</h{n}>')
        elif re.match(r'^\s*---+\s*$', l): close()
        elif re.match(r'^\s*([-*]|\d+\.)\s+', l):
            kind_ = 'ol' if re.match(r'^\s*\d+\.', l) else 'ul'
            if mode != kind_: close(); out.append('<%s>' % kind_); mode = kind_
            out.append('<li>' + link(inline(re.sub(r'^\s*([-*]|\d+\.)\s+', '', l))) + '</li>')
        elif not l.strip(): close()
        else:
            if mode in ('ul', 'ol') and l.startswith('  '): out[-1] = out[-1][:-5] + ' ' + link(inline(l.strip())) + '</li>'
            else: close(); out.append('<p>' + link(inline(l)) + '</p>')
        i += 1
    close(); return '\n'.join(out)
RD = os.path.join(HERE, 'reading'); kinds_idx = ''
for q in Q5:
    f = os.path.join(RD, f'{q}_merged.md')
    if not os.path.exists(f): continue
    ids = {tag: {int(x) for x in re.findall(r'^## being (\d+)', open(os.path.join(RD, f'{q}_{tag}.md')).read(), re.M)} for tag in 'AB'}
    def link(x, ids=ids):
        return re.sub(r'\b([AB]) (\d{1,5})\b', lambda m: f"<a href='being.html?id={m.group(2)}'>{m.group(0)}</a>" if int(m.group(2)) in ids[m.group(1)] else m.group(0), x)
    body = open(f).read(); body = body[body.index('\n## 1.'):]
    table = body[:body.index('\n## 2.')]; nkinds = len(re.findall(r'^\|\s*\**\d', table, re.M))
    page(f'kinds_{q}.html', f'Kinds of answer: {q}', f"""
<p class=qtabs>{''.join(f"<a href='kinds_{k}.html'{' class=on' if k == q else ''}>{k}</a>" for k in Q5)}</p>
<p>The question: <b>{QTEXT[q]}</b>. Two readers each read a different random sample of 300 beings, spread evenly over the writers, and wrote down the kinds of answer they met, without being given any kinds in advance.
A third pass set the two accounts side by side; it formed no kinds of its own and checked every quote against the texts. What follows is that comparison. All counts are out of 300 and a being can sit in several kinds.</p>
<p class=small>A kind that both readers formed on different samples is likelier to be in the texts than in a reader. The sizes depend on where each reader drew the line and should be read as rough. Both readers are models of one family.
<b>A 13101</b> means being 13101 in the first reader's sample; the number opens the being. <a href='read.html?q={q}'>Read the sentences yourself</a>.</p>
<div class=md>{md(body, link)}</div>""")
    kinds_idx += f"<li><a href='kinds_{q}.html'><b>{q}</b></a>: {QTEXT[q]} &middot; {nkinds} kinds listed</li>"
page('kinds.html', 'Kinds of answer', f"""
<p>What kinds of answer the texts give to each of the five questions, found by reading. Ten readers took part: two per question, each with its own random sample of 300 beings, and no kinds given in advance; then the two accounts for each question were set side by side.</p>
<ul>{kinds_idx}</ul>
<p class=small>These are readings of samples, not counts over the whole set. The pages keep the two readers' numbers apart and say where they disagree.</p>""")
