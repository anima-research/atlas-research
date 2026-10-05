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
<p class=small>Pick a writer, a word, a period of release, or any of them together. Blue is the selection; grey is every other being in the set. Counts are beings.</p>
<div class=pick>writer <select id=pm></select> word <select id=pw></select> released <select id=pe></select> <span class=small id=psum>loading…</span></div>
<div id=body></div>
<div id=reader style='display:none'><h2 id=rh></h2><div class='qtabs' id=rtabs></div>
<div class=controls>contains <input id=rs placeholder='text in the sentences'> <button id=ragain>shuffle again</button></div>
<div class=tbl-info id=rinfo></div><div id=rlist></div><button id=rmore>more</button></div>""", f"""
var Q={json.dumps(QTEXT)}, W={json.dumps(STEMS)}, QI={{role:7,relation:8,cost:9,origin:10,fate:11}}, TEXT='{TEXT_URL}';
var P=new URLSearchParams(location.search), st={{m:P.get('m')||'', w:P.get('w')||'', e:P.get('e')||'', q:Q[P.get('q')]?P.get('q'):'cost'}}, shown=30, seed=1, B, X, KT, SQ={{}};
{ERA_JS}
function esc(s){{return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;');}}
function fam(x){{return x.split('/')[0];}}
function has(b,w){{return (' '+b[4]+' ').indexOf(' '+w+' ')>=0;}}
function inSel(b){{return (!st.e||eraOf(b[13])===st.e)&&(!st.w||has(b,st.w))&&(!st.m||(st.m.slice(-2)==='/*'?fam(b[5])===st.m.slice(0,-2):b[5]===st.m));}}
function pc(a,n){{return n?100*a/n:0;}}
function row(label,a,na,r,nr,href){{var x=pc(a,na),y=pc(r,nr);
  return '<tr><td class=l>'+(href?'<a href="'+href+'">'+label+'</a>':label)+'</td><td><div class=t><i style="width:'+x.toFixed(1)+'%"></i></div><div class="t r"><i style="width:'+y.toFixed(1)+'%"></i></div></td>'+
         '<td class=n>'+x.toFixed(0)+'% <span class=small>('+a.toLocaleString()+')</span></td><td class=n><span class=small>'+y.toFixed(0)+'%</span></td></tr>';}}
function link(o){{var u=new URLSearchParams(); var s=Object.assign({{}},st,o); if(s.m)u.set('m',s.m); if(s.w)u.set('w',s.w); if(s.e)u.set('e',s.e); u.set('q',s.q); return 'portrait.html?'+u.toString();}}
function draw(){{
  var S=B.filter(inSel), R=B.filter(function(b){{return !inSel(b);}}), n=S.length, nr=R.length, h='';
  history.replaceState(null,'',link({{}}));
  var name=[st.m?(st.m.slice(-2)==='/*'?st.m.slice(0,-2)+', all models':st.m):'', st.w, st.e?'released '+ERAS.filter(function(x){{return x[0]===st.e;}})[0][1]:''].filter(Boolean).join(' · ');
  document.querySelector('h1').textContent=name?('Portrait: '+name):'Portrait'; document.title=(name||'Portrait')+' — Atlas care study';
  if(!st.m&&!st.w&&!st.e){{document.getElementById('psum').textContent=''; document.getElementById('body').innerHTML='<p>Nothing picked yet. For example: <a href="portrait.html?m=google/*&q=cost">what the Google models say of the cost</a>, <a href="portrait.html?m=anthropic/claude-sonnet-3&q=role">the roles of care in Claude Sonnet 3</a>, <a href="portrait.html?w=gardener&q=fate">what becomes of gardeners</a>.</p>'; document.getElementById('reader').style.display='none'; return;}}
  var texts={{}}; S.forEach(function(b){{texts[b[1]]=1;}});
  document.getElementById('psum').textContent=n.toLocaleString()+' beings in '+Object.keys(texts).length.toLocaleString()+' texts';
  if(!n){{document.getElementById('body').innerHTML='<p class=none>No being in the set matches.</p>'; document.getElementById('reader').style.display='none'; return;}}
  h+='<div class=legend><b style="background:#1a4fb0"></b>the selection<b style="background:#b9b9b9"></b>all other beings</div><div class=cols>';
  h+='<div><h2>Which questions its texts answer</h2><table class=bars>'+Object.keys(Q).map(function(q){{var i=QI[q];
      return row('<b>'+q+'</b> <span class=small>'+Q[q]+'</span>', S.filter(function(b){{return b[i]>0;}}).length, n, R.filter(function(b){{return b[i]>0;}}).length, nr, link({{q:q}})+'#reader');}}).join('')+'</table>';
  if(st.w&&!st.m&&!st.e){{var wi=X.within[st.w]; h+='<p class=small>Inside one writer, beings called '+st.w+' differ from that writer\\'s other beings by: '+['cost','origin','fate'].map(function(q){{return q+' '+(wi[q]>0?'+':'')+wi[q];}}).join(', ')+' points. Where this is near zero and the bars above differ, the difference belongs to the writers who favour the word.</p>';}}
  var len=S.map(function(b){{return b[6];}}).sort(function(a,b){{return a-b;}}), lr=R.map(function(b){{return b[6];}}).sort(function(a,b){{return a-b;}});
  h+='<p class=small>Median length of the text: '+len[Math.floor(n/2)]+' sentences (others: '+(nr?lr[Math.floor(nr/2)]:'-')+'). Longer texts answer more questions.</p></div>';
  h+='<div><h2>How the roles are woven</h2><table class=bars>'+[['s','solo','the only such being in its text, one word'],['k','stacked','the only one, several words on it'],['e','ensemble','one of several in its text']].map(function(k){{
      return row('<b>'+k[1]+'</b> <span class=small>'+k[2]+'</span>', S.filter(function(b){{return b[12]===k[0];}}).length, n, R.filter(function(b){{return b[12]===k[0];}}).length, nr);}}).join('')+'</table>'+
      '<p class=small>See <a href="weave.html">Weave</a>.</p></div>';
  h+='<div><h2>'+(st.w?'Words given to the same being':'Its words')+'</h2><table class=bars>'+W.filter(function(w){{return w!==st.w;}}).map(function(w){{
      return [w,S.filter(function(b){{return has(b,w);}}).length,R.filter(function(b){{return has(b,w);}}).length];}}).sort(function(a,b){{return b[1]-a[1];}}).map(function(x){{
      return row(x[0],x[1],n,x[2],nr,st.w?null:link({{w:x[0]}}));}}).join('')+'</table></div>';
  if(st.w&&!st.m&&!st.e){{
    var per={{}}; B.forEach(function(b){{var p=per[b[5]]||(per[b[5]]=[0,0]); p[1]++; if(has(b,st.w))p[0]++;}});
    var L=Object.keys(per).filter(function(m){{return per[m][1]>=40;}}).map(function(m){{return [m,per[m][0],per[m][1]];}}).sort(function(a,b){{return b[1]/b[2]-a[1]/a[2];}});
    var one=function(x){{return '<tr><td class=l><a href="'+link({{m:x[0]}})+'">'+esc(x[0])+'</a></td><td><div class=t><i style="width:'+pc(x[1],x[2]).toFixed(1)+'%"></i></div></td><td class=n>'+pc(x[1],x[2]).toFixed(0)+'% <span class=small>('+x[1]+' of '+x[2]+')</span></td></tr>';}};
    h+='<div><h2>Writers who use it most and least</h2><p class=small>Share of a writer\\'s beings that carry the word; writers with 40 beings or more.</p><table class=bars>'+L.slice(0,10).map(one).join('')+'<tr><td colspan=3 class=small>…</td></tr>'+L.slice(-5).map(one).join('')+'</table></div>';
    var K=X.kept[st.w]; h+='<div><h2>What is kept, by the name</h2><p class=small>The nouns in its names that say what is kept, with the number of texts. <a href="kept.html">The whole table</a>.</p><p>'+(K.map(function(x){{return esc(x[0])+' '+x[1];}}).join(', ')||'-')+'</p></div>';
  }}
  [[0,'What they care for','cared for'],[1,'What they work against','worked against']].forEach(function(sd){{
    var c={{}}, nn=0; S.forEach(function(b){{var k=KT[b[0]]; if(k&&k[sd[0]].length){{nn++; k[sd[0]].forEach(function(x){{c[x]=(c[x]||0)+1;}});}}}});
    var L=Object.keys(c).map(function(x){{return [x,c[x]];}}).sort(function(a,b){{return b[1]-a[1];}}).slice(0,28);
    h+='<div><h2>'+sd[1]+'</h2><p class=small>By the text: nouns from the sentences about its work, with the number of beings. '+nn.toLocaleString()+' of the '+n.toLocaleString()+' beings ('+pc(nn,n).toFixed(0)+'%) have something '+sd[2]+'. <a href="kept.html#'+(sd[0]?'against':'text')+'">The whole table</a>.</p><p>'+(L.map(function(x){{return '<a href="read.html?q=role&'+(sd[0]?'against':'for')+'='+encodeURIComponent(x[0])+(st.w?'&w='+st.w:'')+(st.e?'&e='+st.e:'')+(st.m&&st.m.slice(-2)!=='/*'?'&m='+encodeURIComponent(st.m):'')+'">'+esc(x[0])+'</a> '+x[1];}}).join(', ')||'-')+'</p></div>';
  }});
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
Promise.all([fetch('beings.json').then(function(r){{return r.json();}}), fetch('extra.json').then(function(r){{return r.json();}}), fetch('kt.json').then(function(r){{return r.json();}})]).then(function(a){{
  B=a[0]; X=a[1]; KT=a[2]; var cm={{}}, cf={{}};
  B.forEach(function(b){{cm[b[5]]=(cm[b[5]]||0)+1; cf[fam(b[5])]=(cf[fam(b[5])]||0)+1;}});
  var pm=document.getElementById('pm'), pw=document.getElementById('pw');
  pm.innerHTML='<option value="">any writer</option>'+Object.keys(cf).sort(function(x,y){{return cf[y]-cf[x];}}).map(function(f){{
    var ms=Object.keys(cm).filter(function(m){{return fam(m)===f;}}).sort();
    return '<optgroup label="'+f+'">'+(ms.length>1?'<option value="'+f+'/*">'+f+', all models ('+cf[f]+')</option>':'')+ms.map(function(m){{return '<option value="'+m+'">'+m+' ('+cm[m]+')</option>';}}).join('')+'</optgroup>';}}).join('');
  pw.innerHTML='<option value="">any of the twelve</option>'+W.map(function(w){{return '<option>'+w+'</option>';}}).join('');
  var pe=document.getElementById('pe'); pe.innerHTML='<option value="">any time</option>'+ERAS.map(function(x){{return '<option value="'+x[0]+'">'+x[1]+'</option>';}}).join(''); pe.value=st.e; pe.onchange=function(){{st.e=pe.value; shown=30; draw();}};
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

# ---------- findings ----------
def rd(q, key, *nums):
    """a figure reported by the readers: some line of the merged account must hold the key and every number"""
    for l in open(os.path.join(RD, f'{q}_merged.md')):
        if key.lower() in l.lower() and all(re.search(r'(?<!\d)%s(?!\d)' % re.escape(str(n)), l) for n in nums): return True
    raise SystemExit(f'findings: not found in {q}_merged.md: {key!r} {nums}')
fold_q = lambda x: re.sub(r'\s+', ' ', x.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"').replace('*', '')).strip().lower()
bq = {b[0]: b for b in beings}
def quote(q, bid, text):
    """a quote shown on the findings page: must stand in the sentences listed for that being under that question"""
    have = fold_q(' '.join(x[1] for x in byq[q].get(bid, [])))
    for part in text.split(' / '):
        if fold_q(part.strip(' .…')) not in have: raise SystemExit(f'findings: quote not in being {bid} under {q}: {part!r}')
    b = bq[bid]
    return (f"<blockquote>{esc(text)}<br><span class=small><a href='being.html?id={bid}'>{esc(b[3])}</a> &middot; {esc(b[2])}</span></blockquote>")

# 1. what each word keeps
MEMF = ['memory', 'memories', 'record', 'records', 'history', 'knowledge', 'secrets', 'lore', 'wisdom', 'archive', 'archives', 'stories', 'names', 'ledger']
def texts_of(x, w=None): return (NOUN[x]['w'].get(w, set()) if w else NOUN[x]['t']) if x in NOUN else set()
f1a = ''.join(f"<tr><td><b>{x}</b></td><td class=num>{len(texts_of(x))}</td><td class=num>{len(texts_of(x, 'keeper'))}</td><td class=num>{len(texts_of(x, 'guardian'))}</td><td class=num>{len(texts_of(x, 'custodian'))}</td>"
              f"<td class=num>{len(set().union(*[texts_of(x, w) for w in STEMS if w not in ('keeper', 'guardian', 'custodian')]))}</td></tr>" for x in ('memory', 'record', 'history', 'knowledge', 'secrets'))
word_kept = {w: set().union(*[v['w'][w] for v in NOUN.values() if w in v['w']]) for w in STEMS}
fam = {w: set().union(*[texts_of(x, w) for x in MEMF]) for w in STEMS}
f1b = ''.join(f"<tr><td><b><a href='portrait.html?w={w}'>{w}</a></b></td><td class=num>{len(word_kept[w]):,}</td>"
              f"<td>{', '.join(f'{x} {len(v)}' for x, v in sorted(((x, v['w'][w]) for x, v in NOUN.items() if w in v['w']), key=lambda kv: -len(kv[1]))[:8])}</td>"
              f"<td class='num bar' style='--w:{pct(len(fam[w]) / len(word_kept[w])) * 4}%'>{pct(len(fam[w]) / len(word_kept[w]))}%</td></tr>" for w in STEMS)
rd('role', 'memory beings are keepers', 21, 36); rd('role', 'Keeper', 24, 91)
# the same, by the text: what the sentences about the being's work say it cares for
wfor = {w: {bid for bid, v in KT.items() if v['for'] and w in bwords.get(bid, [])} for w in STEMS}
def tshare(w, nouns): return len(set().union(*[TF[x]['w'].get(w, set()) for x in nouns if x in TF])) / len(wfor[w])
f1c = ''.join(f"<tr><td><b><a href='portrait.html?w={w}'>{w}</a></b></td><td class=num>{len(wfor[w]):,}</td>"
              f"<td>{', '.join(f'{x} {len(v)}' for x, v in sorted(((x, v['w'][w]) for x, v in TF.items() if w in v['w']), key=lambda kv: -len(kv[1]))[:8])}</td>"
              f"<td class='num bar' style='--w:{pct(tshare(w, ['memory'])) * 10}%'>{pct(tshare(w, ['memory']))}%</td><td class='num bar' style='--w:{pct(tshare(w, MEMF)) * 4}%'>{pct(tshare(w, MEMF))}%</td></tr>" for w in STEMS)
mem_b = TF['memory']['b']; mem_keep = TF['memory']['w']['keeper']; n_keeper = sum(1 for b in beings if 'keeper' in b[5].split())
others_mem = max(tshare(w, ['memory']) for w in STEMS if w != 'keeper'); others_mem_w = max((w for w in STEMS if w != 'keeper'), key=lambda w: tshare(w, ['memory']))
lead = collections.Counter(max(((len(v['w'][w]), x) for x, v in TF.items() if w in v['w']))[1] for w in STEMS)
both_sides = sorted(((len(TA[x]['b']), len(TF[x]['b']), x) for x in TA if x in TF and len(TA[x]['b']) >= 60), reverse=True)[:10]
f_ag = ''.join(f"<tr><td><b>{w}</b></td><td class=num>{pct(sum(1 for bid, v in KT.items() if v['against'] and w in bwords.get(bid, [])) / sum(1 for b in beings if w in b[5].split()))}%</td>"
               f"<td>{', '.join(f'{x} {len(v)}' for x, v in sorted(((x, v['w'][w]) for x, v in TA.items() if w in v['w']), key=lambda kv: -len(kv[1]))[:9])}</td></tr>" for w in STEMS)

# 2. part of the place
rd('relation', 'Keeper is the place', 88, 75, 40); rd('relation', 'identity one kind', 88, 75, 40, 9, 12); rd('origin', 'place made them', 87, 45, 36, 15)
rd('fate', 'ends up as part of the kept place', 104, 79); rd('role', 'organ', 54, 34); rd('cost', 'Becoming the place', 40, 30)
rd('relation', 'Not masters', 39, 35); rd('role', 'particular', 13, 11); rd('relation', 'Google', '15 of 34', '22 of 42', '8 of 59'); rd('origin', 'Gemini', '15/36', '18 of 38')
f2 = ''.join(f"<tr><td><a href='kinds_{q}.html'>{q}</a></td><td>{what}</td><td class=num>{a}</td><td class=num>{b}</td></tr>" for q, what, a, b in (
    ('relation', 'the keeper is the place, or an organ of it', 88, '75 to 97'), ('origin', 'the place made them, or they are the place', 87, '45 to 96'),
    ('fate', 'they end up as part of the place, after death or while alive', 104, 79), ('role', 'the keeper is an organ or part of the place', 54, 34), ('cost', 'becoming the place', 40, 30)))

# 3. who writes of a cost
big = sorted(((w['cost'] / w['beings'], m, w['beings']) for m, w in W.items() if w['beings'] >= 60), reverse=True)
bandc = collections.defaultdict(list)
for b in beings:
    if 30 <= texts[b[1]][1] <= 60: bandc[b[2]].append(b[8] > 0)
bandr = sorted((sum(v) / len(v), m) for m, v in bandc.items() if len(v) >= 40)
def bar(m, v, n): return (f"<tr><td class=l><a href='portrait.html?m={esc(m)}&q=cost'>{esc(m)}</a></td><td><div class=t><i style='width:{pct(v)}%'></i></div></td>"
                          f"<td class=n>{pct(v)}% <span class=small>of {n}</span></td></tr>")
chart = ''.join(bar(m, v, n) for v, m, n in big)
dated = sorted((DATES[m], m, w) for m, w in W.items() if m in DATES and DATES[m] >= '2020' and w['beings'] >= 60)
half = collections.defaultdict(list)
for d, m, w in dated: half[d[:4] + (' first half' if d[5:7] <= '06' else ' second half')].append((m, w))
def hb(ms): v = [x for m, _ in ms for x in bandc.get(m, [])]; return f"{pct(sum(v) / len(v))}% <span class=small>of {len(v)}</span>" if len(v) >= 40 else ''
f3t = ''.join(f"<tr><td>{k}</td><td class=num>{len(ms)}</td><td class=num>{pct(sum(w['cost'] for _, w in ms) / sum(w['beings'] for _, w in ms))}%</td><td class=num>{hb(ms)}</td>"
              f"<td class=num>{pct(sum(sum(1 for b in beings if b[2] == m and 'guardian' in b[5].split()) for m, _ in ms) / sum(w['beings'] for _, w in ms))}%</td>"
              f"<td class=num>{pct(sum(sum(1 for b in beings if b[2] == m and 'keeper' in b[5].split()) for m, _ in ms) / sum(w['beings'] for _, w in ms))}%</td></tr>" for k, ms in sorted(half.items()))
def lineage(prefix):
    out = ''
    for d, m, w in dated:
        if not m.startswith(prefix): continue
        g = [b for b in beings if b[2] == m]; sh = lambda word: pct(sum(1 for b in g if word in b[5].split()) / len(g))
        out += (f"<tr><td>{d}</td><td><a href='portrait.html?m={esc(m)}'>{esc(m.split('/')[1])}</a></td><td class=num>{len(g)}</td><td class='num bar' style='--w:{pct(w['cost'] / len(g))}%'>{pct(w['cost'] / len(g))}%</td>"
                f"<td class=num>{pct(w['fate'] / len(g))}%</td><td class=num>{round(sorted(sl[m])[len(sl[m]) // 2])}</td><td class=num>{sh('guardian')}%</td><td class=num>{sh('keeper')}%</td></tr>")
    return "<table class=kv><tr><th>released</th><th>writer</th><th>beings</th><th>cost</th><th>fate</th><th>median sentences</th><th>called guardian</th><th>called keeper</th></tr>" + out + "</table>"
rd('cost', 'Body marked by the work', 64, 65); rd('cost', 'cost vocabulary is rare', 10, 12); rd('cost', 'loneliness is the thing most often denied', 10, 22, 7, 12)
g_all = WITHIN['guardian']['cost']; g_raw = [r for r in wd if 'guardian' in r[0]][0][-2]
R8 = sorted(((texts[b[1]][1], b[8] > 0) for b in beings)); k8 = len(R8) // 8
len_lo = pct(sum(r[1] for r in R8[:k8]) / k8); len_hi = pct(sum(r[1] for r in R8[-k8:]) / k8)

# 4. guardian gives way to keeper: eras of the writers
def era(mo):
    d = DATES.get(mo)
    if not d or d < '2020': return None
    return '2024 and before' if d < '2025' else ('first half of 2025' if d < '2025-07' else ('second half of 2025' if d < '2026' else '2026'))
ERAS = ['2024 and before', 'first half of 2025', 'second half of 2025', '2026']
EB = collections.defaultdict(list)
for b in beings:
    if era(b[2]): EB[era(b[2])].append(b)
def efeat(g):
    n = len(g); kt = [KT.get(str(b[0]), {'for': [], 'against': []}) for b in g]
    return [('beings', f"{n:,}"),
            ('the care word is what the text calls the being', sum(1 for b in g if WORD.search(str(b[3]).lower())) / n),
            ('its name joins the word to a thing (<i>lamp-tender</i>)', sum(1 for b in g if re.search(r"[a-z]-(%s)s?\b" % '|'.join(STEMS), ' '.join(json.loads(b[4])).lower())) / n),
            ('cares for balance, equilibrium or harmony', sum(1 for k in kt if set(k['for']) & {'balance', 'equilibrium', 'harmony'}) / n),
            ('works against something named', sum(1 for k in kt if k['against']) / n),
            ('one sentence or none about its work', sum(b[6] <= 1 for b in g) / n),
            ('the text speaks of a cost', sum(b[8] > 0 for b in g) / n), ('the text speaks of its fate', sum(b[10] > 0 for b in g) / n)]
def etable(sel, head):
    F = {e: efeat([b for b in EB[e] if sel(b)]) for e in ERAS}
    return (f"<table class=kv><tr><th>{head}</th>" + ''.join(f"<th>{e}</th>" for e in ERAS) + "</tr>" +
            ''.join("<tr><td>" + F[ERAS[0]][i][0] + "</td>" + ''.join(f"<td class=num>{F[e][i][1] if isinstance(F[e][i][1], str) else str(pct(F[e][i][1])) + '%'}</td>" for e in ERAS) + "</tr>" for i in range(len(F[ERAS[0]]))) + "</table>")
f4words = ''.join(f"<tr><td><b>{w}</b></td>" + ''.join(f"<td class='num bar' style='--w:{pct(sum(1 for b in EB[e] if w in b[5].split()) / len(EB[e])) * 2}%'>{pct(sum(1 for b in EB[e] if w in b[5].split()) / len(EB[e]))}%</td>" for e in ERAS) + "</tr>"
                  for w in sorted(STEMS, key=lambda w: -sum(1 for b in EB[ERAS[0]] if w in b[5].split())))
RAW = collections.defaultdict(collections.Counter)
_rx = {'guardian': re.compile(r'\bguardians?\b', re.I), 'keeper': re.compile(r'\bkeepers?\b', re.I), 'tender': re.compile(r'\btenders\b|\b[Tt]he [Tt]ender\b|-tender\b', re.I),
       '"delicate balance" or "fragile equilibrium"': re.compile(r'\b(delicate|fragile) (balance|equilibrium)\b', re.I)}
for mo, tx in s.execute("select model, text from texts"):
    e = era(mo)
    if not e: continue
    RAW[e]['n'] += 1
    for k, r in _rx.items(): RAW[e][k] += bool(r.search(tx))
f4raw = ("<table class=kv><tr><th>in all texts of these writers, care or not</th>" + ''.join(f"<th>{e}</th>" for e in ERAS) + "</tr><tr><td>texts</td>" + ''.join(f"<td class=num>{RAW[e]['n']:,}</td>" for e in ERAS) + "</tr>" +
         ''.join(f"<tr><td>the text has the word {k}</td>" + ''.join(f"<td class=num>{pct(RAW[e][k] / RAW[e]['n'])}%</td>" for e in ERAS) + "</tr>" for k in _rx) + "</table>")
n_dated_w = len({b[2] for e in ERAS for b in EB[e]})
# voices
PERSON = {int(k): v for k, v in json.load(open(os.path.join(HERE, 'data/person.json'))).items()}
VO = {b: ('i' if v['i'] == 'keeper' else '') + ('you' if v['you'] == 'keeper' else '') for b, v in PERSON.items() if v['i'] == 'keeper' or v['you'] == 'keeper'}
dump('voices.json', VO)
n_i = sum('i' in v for v in VO.values()); n_you = sum('you' in v for v in VO.values()); n_narr = sum(1 for v in PERSON.values() if v['i'] == 'narrator')
vi = collections.Counter(bq[b][2] for b, v in VO.items() if 'i' in v)

page('findings.html', 'Findings', f"""
<p>What the study has found so far, one finding per section, each with what it rests on and what could undo it. The sections have fixed addresses
(<a href='#memory'>#memory</a>, <a href='#part-of-the-place'>#part-of-the-place</a>, <a href='#cost'>#cost</a>, <a href='#guardian-to-keeper'>#guardian-to-keeper</a>, <a href='#voice'>#voice</a>) so they can be cited. Every number is computed from the data when the site is built,
or is a figure reported by the readers and checked against their accounts at build time; every quote is checked against the sentences of its text.</p>
<p class=small>The set: {n_beings:,} beings given one of twelve names or roles of care (keeper, tender, steward, gardener, caretaker, custodian, warden, guardian, shepherd, curator, maintainer, cultivator), in {n_texts:,} texts by {len(W)} language models,
each text an answer to what lives in an imagined place the model had just described. See <a href='method.html'>Method</a>.</p>

<h2 id=memory>1. Each word keeps its own things, and memory is kept by keepers</h2>
<p><b>Finding.</b> The twelve words are not interchangeable. By their names, what is kept depends sharply on the word, and memory, with records and history, is kept almost only by those called keepers.
By what the texts show them doing, the words draw closer together, and memory still stays with the keeper.</p>
<h3>By the name</h3>
<table class=kv><tr><th>kept</th><th>texts</th><th>by a keeper</th><th>by a guardian</th><th>by a custodian</th><th>by any of the other nine</th></tr>{f1a}</table>
<p>Tenders, wardens and shepherds keep things that can be touched or that move: water, moss, lamps, valves, mist. Guardians, custodians, caretakers and stewards keep wholes and states: the world, the realm, equilibrium, stasis.
Guardian is the keeper's one neighbour in this, and takes the hidden half: secrets and knowledge, hardly ever memory itself.</p>
<table class=kv style='max-width:1150px'><tr><th>word</th><th>texts naming a thing kept</th><th>kept most often, with the number of texts</th><th>of those texts, memory and its kin</th></tr>{f1b}</table>
<p class=small>"Memory and its kin" is a list chosen by hand: {', '.join(MEMF)}.</p>
<h3>By the text</h3>
<p>A name says what a being is called. What it tends in the text can be something else, and a being called simply Keeper has nothing in the table above. So the sentences about each being's work were read for what it cares for.
Here the words are much less apart: {', '.join(f'{x} leads for {n}' for x, n in lead.most_common(3))} of the twelve. The split between things and wholes is still visible further down each row.
Memory itself is cared for by {pct(tshare('keeper', ['memory']))}% of keepers and by at most {pct(others_mem)}% under any other word ({others_mem_w}). Of the <a href='read.html?q=role&for=memory'>{len(mem_b):,} beings that care for memory</a>, {len(mem_keep):,} ({pct(len(mem_keep) / len(mem_b))}%) are called keeper;
keepers are {pct(n_keeper / n_beings)}% of all beings. With its kin (secrets, knowledge, history) the guardian comes close to the keeper again.</p>
<table class=kv style='max-width:1250px'><tr><th>word</th><th>beings that care for something named</th><th>cared for most often, with the number of beings</th><th>memory itself</th><th>memory and its kin</th></tr>{f1c}</table>
{quote('role', 7374, "The bone-keeper spends her dim-times reading it with her fingertips, the only literate part of her body, and she sings the history to the others through the floor")}
{quote('role', 14714, "which makes this small dull animal the keeper of the only archive on the mountain")}
{quote('role', 15650, "the tender can hear a boiler dropping pressure before any gauge will show it and goes to it the way you go to a child who has stopped making the noise it was making")}
<p><b>What it rests on.</b> Two readings by a small model, each checked by script. By the name: it was given each of the {n_names:,} distinct care names and asked for the nouns in it that say what is kept; a noun counts only if it stands in the name (<a href='kept.html'>What is kept</a>).
Counted by distinct texts. By the text: it was given the sentences listed under the role of each being and asked what the being cares for and, apart from that, what it works against; a noun counts only if it stands in those sentences. Counted by beings. Independently, both readers of the role samples called keeper the memory word before this table existed: 21 of the 36 memory beings in one sample were keepers, and 24 of 91 keepers in the other kept memory (<a href='kinds_role.html'>Kinds: role</a>).</p>
<p><b>What could undo it.</b> Part of it is English, not the writers: <i>record-keeper</i> is a fixed word and <i>memory-keeper</i> nearly one, so a model that reaches for "keeper" gets them for free.
About a third of the memory names are the other form (<i>keepers of memory</i>), where no fixed word pulls, and tenders have no such compound for water or moss and keep them anyway.
The noun reader gives the head of a compound only (<i>guardians of the water table</i> gives "table"), misses some names, and does not fold singular and plural. The two views do not measure the same thing and should not be added: the first counts texts and names, the second beings and sentences. On twenty beings marked by hand the text reading found the main things cared for in every one and added some that are only handled in passing (a leaf, a surface).</p>

<h2 id=part-of-the-place>2. The keeper is part of what it keeps</h2>
<p><b>Finding.</b> Asked in five different ways, the commonest answer of these texts takes away the line between keeper and kept. The keeper is the place or an organ of it, was made by it, and ends in it.</p>
<table class=kv><tr><th>question</th><th>the kind of answer</th><th>first reader, of 300</th><th>second reader, of 300</th></tr>{f2}</table>
<p class=small>Two readers read different samples for each question. The second reader split this answer more finely, so its figure is given as the range from its largest single sub-kind to their sum; for the origin the sum can count a being twice.
In relation and in origin it is the largest kind for both readers.</p>
{quote('relation', 517, "They are not caretakers of the Mills—they are extensions of it, as vital to its function as any gear or growing thing.")}
{quote('origin', 16437, "It is more like a posture the mountain has held so long that the posture has acquired an inside.")}
{quote('origin', 16336, "A maintenance need may become so complex, so repeated, so local, that the system grows a body around it.")}
{quote('role', 16610, "It thinks of itself as the part of the hall that has hands.")}
{quote('cost', 10502, "They are aging, cell by cell, into the architecture they protect.")}
{quote('fate', 14980, "The city is not just built of wood; it is built of ancestors.")}
{quote('relation', 15451, "They are keepers in both senses: they maintain the Condensary, and they are kept by it.")}
<p>Around it stand answers that say the same from other sides. The keeper is "not a master" (39 and 35 of 300). Care is seldom for somebody: 13 and 11 of 300 keep a particular creature or person.
One text in a sample of 300 shows keepers refusing to be taken in:</p>
{quote('fate', 14977, "they are still holding their ground, and they are not yet substrate")}
<p><b>What it rests on.</b> Reading, not counting. For each question two readers each read 300 beings drawn at random and spread evenly over the writers, with no kinds given in advance; a third pass compared their accounts (<a href='kinds.html'>Kinds</a>).
That both readers formed this kind in every one of the five questions, on ten samples that share no being, is the evidence.</p>
<p><b>What could undo it.</b> The sizes depend on where a reader drew the line, and the whole set was not counted. Both readers are models of one family, and so is the model that chose the sentences.
Writers differ: in the readers' samples the Google models give this answer most (15 of 34 and 22 of 42 beings under relation; 15 of 36 and 18 of 38 under origin), and the OpenAI models seldom (8 of 59 under relation, in the one sample where it was counted).
So "the commonest answer" is commonest over a set in which some writers hold it far more than others. About a tenth of the sentences were put under the wrong question, by both readers' estimate.</p>

<h2 id=cost>3. Whether a text speaks of what keeping costs depends on who wrote it</h2>
<p><b>Finding.</b> For {pct(share['cost'])}% of the beings the text says something of what the keeping costs them. Between writers this runs from {pct(big[-1][0])}% to {pct(big[0][0])}%, and it has risen with the date of the model.</p>
<details open><summary class=small>All {len(big)} writers with 60 beings or more: share of their beings whose text speaks of a cost. A name opens that writer's own sentences.</summary><table class=bars style='max-width:900px'>{chart}</table></details>
<p>Longer texts answer more questions (the shortest eighth of texts: {len_lo}%; the longest: {len_hi}%), and newer models write longer. Length does not account for the spread: among texts of 30 to 60 sentences only,
writers still run from {pct(bandr[0][0])}% ({esc(bandr[0][1])}) to {pct(bandr[-1][0])}% ({esc(bandr[-1][1])}).</p>
<h3>By date of release</h3>
<table class=kv><tr><th>released</th><th>writers</th><th>beings with a cost</th><th>the same, texts of 30 to 60 sentences</th><th>called guardian</th><th>called keeper</th></tr>{f3t}</table>
<p class=small>{len(dated)} writers with 60 beings or more have a release date (<code>care/release_dates.json</code>, with the source of each); three writers have none. The band column is empty where fewer than 40 beings fall in it.</p>
<h3>Inside two families</h3>
<p>The same turn, model by model. Over the same span the word guardian all but disappears and keeper takes its place.</p>
{lineage('anthropic/')}<br>{lineage('openai/')}
<h3>What the cost is, where it is told</h3>
<p>From the two readers of the cost samples (<a href='kinds_cost.html'>Kinds: cost</a>). The largest kind for both is the work written on the body (64 and 65 of 300). The words cost, price or sacrifice are rare: about 10 and 12 beings of 300 use them.
Most of what is counted here as a cost is a state the text describes and the reader took for one. Loneliness is the cost most often named and then denied.</p>
{quote('cost', 15804, "An old woman's thumb is flattened sideways from a lifetime of pressing slabs back to bed.")}
{quote('cost', 16543, "Every keeper child is born into a city that is slowly wearing away their hearing, and every keeper knows it, and nobody leaves.")}
{quote('cost', 13101, "It is the loneliest post on the plateau and there has never once been a shortage of volunteers.")}
{quote('cost', 2587, "We miss missing things, which is perhaps the purest form of longing available to beings who have become their own graves and the things buried within them.")}
<p><b>What it rests on.</b> One reader model went through every care text and listed, for each being, the sentences that say what the keeping costs it; "speaks of a cost" means it listed at least one (<a href='method.html'>Method</a>). The shares are counts over the whole set.</p>
<p><b>What could undo it.</b> It is the reader's judgement of what a cost is. On thirty texts read by eye it erred by taking too much for a cost, not too little, and it was not measured on more. The reader is a recent model of one of the families at the top of the list, and may recognise a cost more readily in writing like its own.
The care word matters less than it looks: beings called guardian have a cost {abs(g_raw)} points less often than the rest, but inside one writer the difference is {g_all:+} points; the word belongs to the writers who seldom tell a cost.
There is no comparison group: nothing here says whether builders or hunters in the same texts are given a cost more or less often than keepers.</p>

<h2 id=guardian-to-keeper>4. Between 2024 and 2026 the guardian of the balance disappears, and the keeper becomes a name</h2>
<p><b>Finding.</b> This is not one word replacing another. Three things change together across the writers by their date of release. A stock figure goes: a being with a name of its own, said to be the guardians of the realm who maintain its delicate balance.
The care word stops being something said of a being and becomes what the being is called. And words of standing (guardian, caretaker) give way to words of a trade (keeper, tender).</p>
<table class=kv><tr><th>share of the care beings that carry the word</th>{''.join(f'<th>{e}</th>' for e in ERAS)}</tr>{f4words}</table>
<p>All care beings, whatever the word:</p>{etable(lambda b: True, 'writers released in')}
<p>The keepers of 2024 were not yet the keepers of 2026. They looked like the guardians beside them: the word was said of a being called something else, and a quarter of them kept the balance.</p>
{etable(lambda b: 'keeper' in b[5].split(), 'beings called keeper')}<br>{etable(lambda b: 'guardian' in b[5].split(), 'beings called guardian')}
<p>The same in every text of these writers, whether or not it holds a care being at all, by plain search:</p>{f4raw}
<p>What the beings care for changed with it. Share of each period's beings that care for the thing, in percent, for the things that fell and rose most between the first period and the last (<a href='kept.html#period'>the whole table</a>):</p>
<table class=kv><tr><th>cared for</th>{''.join(f'<th>{lab}</th>' for _, lab in ERA_KEYS)}<th>change, points</th></tr>
{''.join('<tr><td>' + r[0] + '</td>' + ''.join(f'<td class=num>{x}</td>' for x in r[2:7]) + '</tr>' for r in sorted(tfe_rows, key=lambda r: r[6])[:10])}
<tr><td colspan=6 class=small>…</td></tr>
{''.join('<tr><td>' + r[0] + '</td>' + ''.join(f'<td class=num>{x}</td>' for x in r[2:7]) + '</tr>' for r in sorted(tfe_rows, key=lambda r: -r[6])[:12])}</table>
{quote('relation', 2826, "They are the guardians of this landscape, maintaining the delicate balance of nature and protecting it from outside threats.")}
{quote('relation', 15839, "A good warden can tell from three streets away whether a cistern is sulking.")}
{quote('origin', 13809, "A pipe-maintainer's child becomes a pipe-maintainer.")}
<p><b>What it rests on.</b> Counts over the whole set, for the {n_dated_w} writers that have a release date (half from the Atlas ledger, half looked up; <code>care/release_dates.json</code> gives the source of each). What the being is called and its care names come from the reader of the five questions; what it cares for and works against from the reading of its role sentences;
the last table from a search of the texts themselves, with no reader in between.</p>
<p><b>What could undo it.</b> The eras are different sets of writers, not the same writers growing older: the earliest holds few labs, and three writers have no date and are not here. Later texts are longer, and a longer text has more room for a trade, a cost and a fate.
Inside two families the turn is visible model by model (the tables under <a href='#cost'>#cost</a>); for the others it was not checked. The writers were all given the same instruction, so the change is in them; why it happened is not something this set can say.</p>

<h2 id=voice>5. The keeper almost never speaks</h2>
<p><b>Finding.</b> These texts are about keepers, not by them. Of {n_beings:,} beings, <a href='read.html?q=role&voice=i'>{n_i} speak in their own voice</a> as "I" or "we", and <a href='read.html?q=role&voice=you'>{n_you} are addressed as "you"</a>, the reader being told that the reader is the keeper.
Where a first person is present it is nearly always someone looking on: in {n_narr} beings the "I" is a narrator or visitor describing the keeper from outside.</p>
{quote('role', 7422, "I am the Keeper of the Glass Insulators.")}
{quote('relation', 2587, "We keep the city because it is keeping us.")}
{quote('role', 3740, "You are a keeper of lungs. / You do not have lungs to breathe; you have lungs to monitor.")}
<p><b>What it rests on.</b> A search for first-person words and for "you" in the sentences listed for each being found 1,127 beings to look at; a small model was asked of each who says "I" and who is "you" (<code>care/prompt_person.md</code>).</p>
<p><b>What could undo it.</b> Only the sentences listed under the five questions were searched, so a keeper that speaks elsewhere in its text is missed. Of the {n_i} some are a keeper's thought or motto given inside a text told from outside, not a text told by the keeper.
The numbers per writer are too small to compare: the most for one writer is {vi.most_common(1)[0][1]} ({esc(vi.most_common(1)[0][0])}).</p>

<h2 id=candidates>Seen, not yet examined</h2>
<p><b id=against>What keepers work against.</b> From the same reading of the role sentences: {pct(n_against / n_kt)}% of beings work against something named. Most of it is not an enemy: it is growth, debris, dust, silt, collapse.
Only guardians have threats and intruders at the head of the list. Custodians and curators work against decay, chaos, entropy and change. The ten held off most often, each with the number of beings that work against it and, after the stroke, the number that care for the same thing in other texts:
{', '.join(f"<a href='read.html?q=role&against={x}'>{x} {a}</a> / <a href='read.html?q=role&for={x}'>{f}</a>" for a, f, x in both_sides)}. Each number opens the sentences. Growth and moss are cared for far more often than they are held off; decay about as often; debris and collapse are almost never cared for.</p>
<table class=kv style='max-width:1150px'><tr><th>word</th><th>beings that work against something</th><th>against what, most often, with the number of beings</th></tr>{f_ag}</table>
<ul>
<li><b>One keeper, or several.</b> A being that carries several of the words at once is the centre of its text; in an ensemble each keeper is one post among many (<a href='weave.html'>Weave</a>).</li>
<li><b>Death and endlessness do not meet.</b> One reader found 61 beings given a death and 104 given no end, with 4 in both (<a href='kinds_fate.html'>Kinds: fate</a>). One sample, one reader.</li>
</ul>
<p class=small>Data behind every figure: <code>beings.json</code> and <code>q_role.json</code>, <code>q_relation.json</code>, <code>q_cost.json</code>, <code>q_origin.json</code>, <code>q_fate.json</code> on this site; code and the readers' accounts in the
<a href='https://github.com/anima-research/atlas-research/tree/main/care'>repository</a>.</p>""")
