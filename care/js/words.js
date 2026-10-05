// The twelve words side by side, recounted for the chosen writers and period.
var W = CFG.words, QI = [7, 8, 9, 10, 11];
getJSON('beings.json').then(function (B) {
  filterBar(document.getElementById('bar'), B, function (pred, st) {
    var S = B.filter(pred), rows = [], many = {}; S.forEach(function (b) { many[b[5]] = 1; }); many = Object.keys(many).length > 1;
    W.forEach(function (w) {
      var g = S.filter(function (b) { return has(b, w); }), o = S.filter(function (b) { return !has(b, w); }); if (!g.length) return;
      var t = {}, m = {}; g.forEach(function (b) { t[b[1]] = 1; m[b[5]] = 1; });
      var band = g.filter(function (b) { return b[6] >= 30 && b[6] <= 60; }), cost = function (b) { return b[9] > 0; };
      rows.push(['<a href="portrait.html?w=' + w + linkParams(st) + '">' + w + '</a>', g.length, Object.keys(t).length, Object.keys(m).length]
        .concat(QI.map(function (i) { return pc(g.filter(function (b) { return b[i] > 0; }).length, g.length); }),
          [band.length >= 20 ? pc(band.filter(cost).length, band.length) : '', o.length ? Math.round(10 * (pc(g.filter(cost).length, g.length) - pc(o.filter(cost).length, o.length))) / 10 : '',
           many ? withinWriter(S, function (b) { return has(b, w); }, cost) : '']));
    });
    var el = document.getElementById('t'); el.innerHTML = '';
    makeTable(el, { pageSize: 50, sort: [1, -1], rows: rows, columns: [{ title: 'word', type: 'html' }, { title: 'beings', type: 'num' }, { title: 'texts', type: 'num' }, { title: 'writers', type: 'num' },
      { title: 'role %', type: 'num' }, { title: 'relation %', type: 'num' }, { title: 'cost %', type: 'num' }, { title: 'origin %', type: 'num' }, { title: 'fate %', type: 'num' },
      { title: 'cost %, texts of 30 to 60 sentences', type: 'num' }, { title: 'cost, against other words', type: 'num' }, { title: 'cost, inside one writer', type: 'num' }] });
    var c = {}, n = 0; S.forEach(function (b) { if (b[4].indexOf(' ') > 0) { c[b[4]] = (c[b[4]] || 0) + 1; n++; } });
    document.getElementById('combo').innerHTML = n.toLocaleString() + ' beings carry more than one of the words. Most frequent sets: ' +
      Object.keys(c).sort(function (x, y) { return c[y] - c[x]; }).slice(0, 14).map(function (k) { return k.replace(/ /g, ' + ') + ' (' + c[k] + ')'; }).join('; ') + '.';
  });
});
