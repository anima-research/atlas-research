// What is kept: by the name (texts), by the text (beings), and over time. Recounted for the chosen writers and period.
var W = CFG.words, B, KT, KN, pred, fst, view;
function nounLink(side, x) { return '<a href="read.html?q=role&' + side + '=' + encodeURIComponent(x) + linkParams(fst) + '">' + esc(x) + '</a>'; }
var wcols = W.map(function (w) { return { title: w, type: 'num' }; });
function byName() {
  var tw = {}; B.forEach(function (b) { if (!tw[b[1]]) tw[b[1]] = b; });
  var A = {}, any = !(fst.m || fst.e);
  Object.keys(KN).forEach(function (t) {
    var b = tw[t]; if (b ? !pred(b) : !any) return;
    KN[t].forEach(function (e) { e[0].forEach(function (x) { var a = A[x] || (A[x] = { t: {}, w: {} }); a.t[t] = 1; e[1].forEach(function (w) { (a.w[w] || (a.w[w] = {}))[t] = 1; }); }); });
  });
  var rows = []; Object.keys(A).forEach(function (x) { var n = Object.keys(A[x].t).length; if (n < 2) return;
    rows.push([esc(x), n, Object.keys(A[x].w).length].concat(W.map(function (w) { return A[x].w[w] ? Object.keys(A[x].w[w]).length : ''; }))); });
  return { cols: [{ title: 'kept', type: 'html' }, { title: 'texts', type: 'num', tip: 'distinct texts' }, { title: 'care words', type: 'num', tip: 'how many of the twelve keep it' }].concat(wcols), rows: rows, sort: [1, -1] };
}
function bySide(side) {
  var A = {}, i = side === 'for' ? 0 : 1;
  B.forEach(function (b) { if (!pred(b)) return; var k = KT[b[0]]; if (!k) return; var ws = b[4] ? b[4].split(' ') : [];
    k[i].forEach(function (x) { var a = A[x] || (A[x] = { n: 0, w: {} }); a.n++; ws.forEach(function (w) { a.w[w] = (a.w[w] || 0) + 1; }); }); });
  var least = (fst.m || fst.e) ? 2 : 3, rows = [];
  Object.keys(A).forEach(function (x) { if (A[x].n < least) return; rows.push([nounLink(side, x), A[x].n, Object.keys(A[x].w).length].concat(W.map(function (w) { return A[x].w[w] || ''; }))); });
  return { cols: [{ title: side === 'for' ? 'cared for' : 'worked against', type: 'html', tip: 'opens the sentences' }, { title: 'beings', type: 'num' }, { title: 'care words', type: 'num' }].concat(wcols), rows: rows, sort: [1, -1] };
}
function overTime(side) {
  var A = {}, i = side === 'for' ? 0 : 1, en = {}, tot = 0;
  B.forEach(function (b) { if (!pred(b)) return; var k = KT[b[0]], e = eraOf(b[13]); if (!k || !e) return; en[e] = (en[e] || 0) + 1; tot++;
    k[i].forEach(function (x) { var a = A[x] || (A[x] = { n: 0 }); a.n++; a[e] = (a[e] || 0) + 1; }); });
  var least = Math.max(4, Math.round(25 * tot / 16400)), rows = [], sh = function (a, e) { return en[e] ? Math.round(10000 * (a[e] || 0) / en[e]) / 100 : ''; };
  Object.keys(A).forEach(function (x) { var a = A[x]; if (a.n < least) return; var s = CFG.eras.map(function (e) { return sh(a, e[0]); });
    rows.push([nounLink(side, x), a.n].concat(s, [s[0] === '' || s[3] === '' ? '' : Math.round(100 * (s[3] - s[0])) / 100, s[0] ? Math.round(10 * s[3] / s[0]) / 10 : ''])); });
  var cols = [{ title: side === 'for' ? 'cared for' : 'worked against', type: 'html', tip: 'opens the sentences' }, { title: 'beings', type: 'num' }]
    .concat(CFG.eras.map(function (e) { return { title: e[1] + ', %', type: 'num', tip: 'share of the beings by writers of that period (' + (en[e[0]] || 0).toLocaleString() + ' beings)' }; }),
      [{ title: 'change, points', type: 'num', tip: '2026 minus 2024 and before' }, { title: 'times', type: 'num', tip: '2026 share divided by the share of 2024 and before' }]);
  return { cols: cols, rows: rows, sort: side === 'for' ? [6, 1] : [6, -1] };
}
var VIEWS = {
  noun: ['kept, by the name', byName, 'What the name itself says is kept. A small model was given each distinct care name and asked for the main noun of each thing kept, as written in the name: <i>keepers of the ancient knowledge etched into the stone</i> gives <b>knowledge</b>; <i>silent curators</i> gives nothing. Counted by distinct texts; nouns of one text only are left out.'],
  text: ['cared for, by the text', function () { return bySide('for'); }, 'What the sentences about the being\'s work say it cares for. A small model read those sentences and listed what the being cares for and, apart from that, what it works against, as the main noun of each, exactly as written. Counted by beings. A noun opens the sentences it comes from.'],
  against: ['worked against, by the text', function () { return bySide('against'); }, 'From the same reading: what the sentences say the being holds off, removes, prevents, or protects what it keeps from. The same noun can stand on both sides in different texts.'],
  period: ['cared for, over time', function () { return overTime('for'); }, 'What is cared for, by the release date of the writer. Each cell is the share, in percent, of the beings written by models of that period that care for the thing. Sort by <b>change</b> to see what came and what went. The periods are different sets of writers and later texts are longer, so a few tenths of a point mean little.'],
  againstperiod: ['worked against, over time', function () { return overTime('against'); }, 'What is worked against, by the release date of the writer; read as the table before.']
};
function show() {
  view = VIEWS[location.hash.slice(1)] ? location.hash.slice(1) : 'noun';
  document.getElementById('views').innerHTML = Object.keys(VIEWS).map(function (k) { return '<a href="#' + k + '"' + (k === view ? ' class=on' : '') + '>' + VIEWS[k][0] + '</a>'; }).join('');
  document.getElementById('note').innerHTML = VIEWS[view][2];
  var t = VIEWS[view][1](), el = document.getElementById('t'); el.innerHTML = '';
  if (!t.rows.length) { el.innerHTML = '<p class=none>Nothing in this selection.</p>'; return; }
  makeTable(el, { key: view, pageSize: 200, sort: t.sort, columns: t.cols, rows: t.rows });
}
Promise.all([getJSON('beings.json'), getJSON('kt.json'), getJSON('kn.json')]).then(function (a) {
  B = a[0]; KT = a[1]; KN = a[2];
  filterBar(document.getElementById('bar'), B, function (p, st) { pred = p; fst = st; show(); });
  window.onhashchange = show;
});
