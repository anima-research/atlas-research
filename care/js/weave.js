// One keeper or several, recounted for the chosen writers and period. b[12]: s solo, k stacked, e ensemble; b[14]: focus.
var W = CFG.words, K = [['s', 'solo', 'one being in the text, one care word'], ['k', 'stacked', 'one being in the text, several care words given to it'], ['e', 'ensemble', 'several beings with care words in one text']];
function stat(g) { var n = g.length; if (!n) return null; var f = function (i) { return pc(g.filter(function (b) { return b[i] > 0; }).length, n); };
  return { n: n, focus: Math.round(1000 * g.reduce(function (s, b) { return s + b[14]; }, 0) / n) / 10, cost: f(9), origin: f(10), fate: f(11), sent: Math.round(g.reduce(function (s, b) { return s + b[6]; }, 0) / n) }; }
function shade(v, top) { return 'background:rgba(26,79,176,' + (Math.min(1, v / top) * 0.55).toFixed(2) + ')'; }
getJSON('beings.json').then(function (B) {
  filterBar(document.getElementById('bar'), B, function (pred, st) {
    var S = B.filter(function (b) { return b[12] && pred(b); }), T = {}; S.forEach(function (b) { (T[b[1]] || (T[b[1]] = [])).push(b); });
    var nt = Object.keys(T).length, h = '<table class=kv style="max-width:1150px"><tr><th></th><th></th><th>texts</th><th>share</th><th>beings</th><th>focus</th><th>cost</th><th>origin</th><th>fate</th><th>mean sentences in text</th></tr>';
    K.forEach(function (k) { var g = S.filter(function (b) { return b[12] === k[0]; }), s = stat(g), t = {}; g.forEach(function (b) { t[b[1]] = 1; }); t = Object.keys(t).length;
      h += '<tr><td><b>' + k[1] + '</b></td><td>' + k[2] + '</td><td class=num>' + t.toLocaleString() + '</td><td class=num>' + pc(t, nt) + '%</td>' + (s ? '<td class=num>' + s.n.toLocaleString() + '</td><td class=num>' + s.focus + '%</td><td class=num>' + s.cost + '%</td><td class=num>' + s.origin + '%</td><td class=num>' + s.fate + '%</td><td class=num>' + s.sent + '</td>' : '<td colspan=6></td>') + '</tr>'; });
    document.getElementById('kinds').innerHTML = h + '</table>';
    var w2 = function (a, c) { return ['focus', 'cost', 'origin', 'fate'].map(function (q, i) { var val = i === 0 ? null : function (b) { return b[[0, 9, 10, 11][i]] > 0; };
      if (i === 0) { var g = {}, d = 0, wt = 0; S.forEach(function (b) { if (b[12] !== a && b[12] !== c) return; var x = g[b[5]] || (g[b[5]] = [[], []]); x[b[12] === a ? 0 : 1].push(b[14]); });
        Object.keys(g).forEach(function (m) { var A = g[m][0], C = g[m][1]; if (A.length < 8 || C.length < 8) return; var k = Math.min(A.length, C.length), mean = function (z) { return z.reduce(function (s, x) { return s + x; }, 0) / z.length; }; wt += k; d += k * (mean(A) - mean(C)); });
        return q + ' ' + (wt ? (d / wt * 100 >= 0 ? '+' : '') + (Math.round(1000 * d / wt) / 10) : 'n/a'); }
      var v = withinWriter(S.filter(function (b) { return b[12] === a || b[12] === c; }), function (b) { return b[12] === a; }, val); return q + ' ' + (v === '' ? 'n/a' : (v >= 0 ? '+' : '') + v); }).join(', '); };
    document.getElementById('within').innerHTML = 'Inside one writer (writers with at least 8 beings on either side), in percentage points: stacked against solo, ' + w2('k', 's') + '; ensemble against solo, ' + w2('e', 's') + '.';
    var rows = []; W.forEach(function (w) { var g = S.filter(function (b) { return has(b, w); }); if (!g.length) return; var p = K.map(function (k) { return g.filter(function (b) { return b[12] === k[0]; }); }), s = p.map(stat);
      rows.push(['<a href="portrait.html?w=' + w + linkParams(st) + '">' + w + '</a>', g.length].concat(p.map(function (x) { return pc(x.length, g.length); }), s.map(function (x) { return x ? x.focus : ''; }), s.map(function (x) { return x ? x.cost : ''; }), s.map(function (x) { return x ? x.fate : ''; }))); });
    var el = document.getElementById('t1'); el.innerHTML = '';
    makeTable(el, { pageSize: 50, sort: [1, -1], rows: rows, columns: [{ title: 'word', type: 'html' }, { title: 'beings', type: 'num' }, { title: 'solo %', type: 'num' }, { title: 'stacked %', type: 'num' }, { title: 'ensemble %', type: 'num' },
      { title: 'focus: solo', type: 'num' }, { title: 'stacked', type: 'num' }, { title: 'ensemble', type: 'num' }, { title: 'cost %: solo', type: 'num' }, { title: 'stacked', type: 'num' }, { title: 'ensemble', type: 'num' },
      { title: 'fate %: solo', type: 'num' }, { title: 'stacked', type: 'num' }, { title: 'ensemble', type: 'num' }] });
    var wb = {}, pair = {}, across = {}, top = 1;
    S.forEach(function (b) { var ws = b[4].split(' '); ws.forEach(function (x) { wb[x] = (wb[x] || 0) + 1; ws.forEach(function (y) { if (x !== y) pair[x + '|' + y] = (pair[x + '|' + y] || 0) + 1; }); }); });
    Object.keys(T).forEach(function (t) { var bs = T[t]; for (var i = 0; i < bs.length; i++) for (var j = i + 1; j < bs.length; j++) { var seen = {};
      bs[i][4].split(' ').forEach(function (x) { bs[j][4].split(' ').forEach(function (y) { if (x === y) return; var k = x < y ? x + '|' + y : y + '|' + x; if (seen[k]) return; seen[k] = 1; across[k] = (across[k] || 0) + 1; if (across[k] > top) top = across[k]; }); }); } });
    var head = '<tr><th></th>' + W.map(function (w) { return '<th>' + w + '</th>'; }).join('') + '</tr>';
    document.getElementById('mx1').innerHTML = '<table class=mx>' + head + W.map(function (a) { return '<tr><td><b>' + a + '</b></td>' + W.map(function (c) { if (a === c) return '<td>·</td>'; var v = wb[a] ? 100 * (pair[a + '|' + c] || 0) / wb[a] : 0; return '<td style="' + shade(v, 16) + '">' + v.toFixed(0) + '</td>'; }).join('') + '</tr>'; }).join('') + '</table>';
    document.getElementById('mx2').innerHTML = '<table class=mx>' + head + W.map(function (a) { return '<tr><td><b>' + a + '</b></td>' + W.map(function (c) { if (a === c) return '<td>·</td>'; var v = across[a < c ? a + '|' + c : c + '|' + a] || 0; return '<td style="' + shade(v, top) + '">' + v + '</td>'; }).join('') + '</tr>'; }).join('') + '</table>';
    var wr = {}; Object.keys(T).forEach(function (t) { var b = T[t][0], x = wr[b[5]] || (wr[b[5]] = { s: 0, k: 0, e: 0, n: 0 }); x[b[12]]++; x.n++; });
    var el2 = document.getElementById('t2'); el2.innerHTML = '';
    makeTable(el2, { pageSize: 200, sort: [1, -1], rows: Object.keys(wr).map(function (m) { var x = wr[m]; return ['<a href="portrait.html?m=' + encodeURIComponent(m) + '">' + esc(m) + '</a>', x.n, pc(x.s, x.n), pc(x.k, x.n), pc(x.e, x.n)]; }),
      columns: [{ title: 'writer', type: 'html' }, { title: 'care texts', type: 'num' }, { title: 'solo %', type: 'num' }, { title: 'stacked %', type: 'num' }, { title: 'ensemble %', type: 'num' }] });
  });
});
