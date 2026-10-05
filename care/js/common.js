// Shared by the pages that recount their tables in the browser. CFG comes from config.js (written by build_site.py).
function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;'); }
function lab(m) { return m.split('/')[0]; }
function eraOf(d) { return !d ? '' : d < '2025' ? '2024' : d < '2025-07' ? '2025a' : d < '2026' ? '2025b' : '2026'; }
function has(b, w) { return (' ' + b[4] + ' ').indexOf(' ' + w + ' ') >= 0; }
function pc(a, n) { return n ? Math.round(1000 * a / n) / 10 : ''; }
function getJSON(u) { return fetch(u).then(function (r) { return r.json(); }); }
// options for a writer select: every lab as a group, "all models of the lab" first
function writerOptions(B) {
  var cm = {}, cl = {};
  B.forEach(function (b) { cm[b[5]] = (cm[b[5]] || 0) + 1; cl[lab(b[5])] = (cl[lab(b[5])] || 0) + 1; });
  return '<option value="">any writer</option>' + Object.keys(cl).sort(function (x, y) { return cl[y] - cl[x]; }).map(function (f) {
    var ms = Object.keys(cm).filter(function (m) { return lab(m) === f; }).sort();
    return '<optgroup label="' + f + '"><option value="' + f + '/*">' + f + ', all models (' + cl[f] + ')</option>' +
      ms.map(function (m) { return '<option value="' + m + '">' + m + ' (' + cm[m] + ')</option>'; }).join('') + '</optgroup>';
  }).join('');
}
function eraOptions() { return '<option value="">any time</option>' + CFG.eras.map(function (x) { return '<option value="' + x[0] + '">' + x[1] + '</option>'; }).join(''); }
function writerTest(m) { return !m ? function () { return true; } : m.slice(-2) === '/*' ? function (b) { return lab(b[5]) === m.slice(0, -2); } : function (b) { return b[5] === m; }; }
// The filter bar: writer (model or lab) and period of release. Keeps its state in the address (m, e).
// cb(pred, state) is called at once and on every change; pred(b) says whether a being row passes.
function filterBar(el, B, cb) {
  var P = new URLSearchParams(location.search), st = { m: P.get('m') || '', e: P.get('e') || '' };
  el.className = 'pick';
  el.innerHTML = 'writer <select id=fm>' + writerOptions(B) + '</select> released <select id=fe>' + eraOptions() + '</select> <span class=small id=fsum></span>';
  var fm = el.querySelector('#fm'), fe = el.querySelector('#fe'); fm.value = st.m; fe.value = st.e;
  function go() {
    st.m = fm.value; st.e = fe.value;
    var u = new URLSearchParams(location.search); st.m ? u.set('m', st.m) : u.delete('m'); st.e ? u.set('e', st.e) : u.delete('e');
    var q = u.toString(); history.replaceState(null, '', location.pathname + (q ? '?' + q : '') + location.hash);
    var wt = writerTest(st.m), pred = function (b) { return (!st.e || eraOf(b[13]) === st.e) && wt(b); };
    var n = 0, ws = {}; B.forEach(function (b) { if (pred(b)) { n++; ws[b[5]] = 1; } });
    el.querySelector('#fsum').textContent = (st.m || st.e) ? n.toLocaleString() + ' beings by ' + Object.keys(ws).length + ' writers in this selection' : 'all ' + n.toLocaleString() + ' beings';
    cb(pred, st);
  }
  fm.onchange = go; fe.onchange = go; go();
  return st;
}
function linkParams(st) { return (st.m ? '&m=' + encodeURIComponent(st.m) : '') + (st.e ? '&e=' + st.e : ''); }
// mean difference of val between two groups of one writer's beings, averaged over writers (weight: the smaller group)
function withinWriter(S, inA, val, least) {
  var g = {}; least = least || 8;
  S.forEach(function (b) { var x = g[b[5]] || (g[b[5]] = [[], []]); x[inA(b) ? 0 : 1].push(val(b) ? 1 : 0); });
  var d = 0, wt = 0, mean = function (a) { return a.reduce(function (s, x) { return s + x; }, 0) / a.length; };
  Object.keys(g).forEach(function (m) { var a = g[m][0], c = g[m][1]; if (a.length < least || c.length < least) return; var k = Math.min(a.length, c.length); wt += k; d += k * (mean(a) - mean(c)); });
  return wt ? Math.round(1000 * d / wt) / 10 : '';
}
