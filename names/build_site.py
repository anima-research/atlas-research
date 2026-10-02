#!/usr/bin/env python3
"""Build the static site from data/names.db and the snapshot.

    python3 build_site.py --rev 15

Writes site/. Text bodies (site/t/) are written once per snapshot and reused; everything
else is rewritten on each build. Serve with:  python3 -m http.server 8795 -d site
"""
import argparse, hashlib, html, json, os, random, re, shutil, sqlite3, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "site")
ATLAS = "https://atlas.animalabs.ai/v3/creature/%d"
E = html.escape

VERDICTS = {"b": "being", "p": "place", "t": "thing", "s": "statement", "x": "not a name",
            "g": "broken text"}
STATUS = {0: "covered", 2: "candidates only", 3: "nothing found",
          4: "flagged"}

NAV = [("index.html", "Overview"), ("patterns.html", "Patterns"), ("models.html", "Models"),
       ("names.html", "Names"), ("uncovered.html", "Uncovered texts"), ("recall.html", "Recall checks"),
       ("readings.html", "Reading log"), ("flagged.html", "Flagged texts")]

CSS = """
body{font:15px/1.45 system-ui,sans-serif;margin:0 auto;max-width:1500px;padding:0 16px 60px;color:#222;background:#fff}
nav{padding:10px 0;border-bottom:1px solid #ccc;margin-bottom:14px}
nav a{margin-right:16px}
h1{font-size:22px;margin:.6em 0 .3em} h2{font-size:17px;margin:1.6em 0 .4em}
p,li{max-width:900px}
table{border-collapse:collapse;font-size:13px;width:100%}
th,td{border:1px solid #ddd;padding:3px 6px;vertical-align:top;text-align:left}
th{background:#f3f3f3;cursor:pointer;white-space:nowrap;user-select:none}
th.sorted-asc:after{content:" \\25B2"} th.sorted-desc:after{content:" \\25BC"}
td.num{text-align:right;font-variant-numeric:tabular-nums}
tr.filters th{cursor:default;padding:2px}
tr.filters input{width:100%;box-sizing:border-box;font-size:12px;min-width:40px}
.tbl-info{font-size:12px;color:#555;margin:4px 0}
.tbl-wrap{overflow-x:auto}
code,pre,.rx{font:12px/1.4 ui-monospace,Menlo,monospace}
pre,.rx{background:#f6f6f6;padding:8px;white-space:pre-wrap;word-break:break-all;border:1px solid #e3e3e3}
blockquote{border-left:3px solid #bbb;margin:6px 0;padding:2px 10px;color:#333;white-space:pre-wrap}
mark{background:#ffe08a;padding:0 1px} mark.s{background:#9fe3a8} mark.st{background:#b9d3ff}
.kv td:first-child{white-space:nowrap;color:#555}
.kv{width:auto}
.text{white-space:pre-wrap;max-width:900px;font:15px/1.55 Georgia,serif;border:1px solid #ddd;padding:14px}
.strict{color:#0a6b1f;font-weight:600} .wide{color:#8a6100}
.small{font-size:12px;color:#555}
button{font-size:12px}
"""

JS = r"""
// Sortable, filterable table.  makeTable(element, {columns, rows, pageSize, sort})
// columns: [{title, type: 'num' | 'text' | 'html', tip}]   rows: array of arrays
// Filters: text columns match a substring (case-insensitive; prefix with ! to exclude,
// with = for an exact match). Number columns accept 5, >5, >=5, <5, <=5, 2..9.
function makeTable(el, opt) {
  var cols = opt.columns, rows = opt.rows, page = opt.pageSize || 200, shown = page;
  var sortCol = opt.sort ? opt.sort[0] : -1, sortDir = opt.sort ? opt.sort[1] : 1;
  var strip = function (s) { return String(s == null ? '' : s).replace(/<[^>]*>/g, ''); };
  var keyed = rows.map(function (r) {
    return r.map(function (v, i) {
      return cols[i].type === 'num' ? (v === '' || v == null ? null : +v) : strip(v).toLowerCase();
    });
  });
  var filters = cols.map(function () { return ''; });
  var info = document.createElement('div'); info.className = 'tbl-info';
  var wrap = document.createElement('div'); wrap.className = 'tbl-wrap';
  var table = document.createElement('table'), thead = document.createElement('thead'),
      tbody = document.createElement('tbody');
  var hr = document.createElement('tr'), fr = document.createElement('tr'); fr.className = 'filters';
  cols.forEach(function (c, i) {
    var th = document.createElement('th'); th.textContent = c.title; if (c.tip) th.title = c.tip;
    th.onclick = function () { if (sortCol === i) sortDir = -sortDir; else { sortCol = i; sortDir = c.type === 'num' ? -1 : 1; } shown = page; draw(); };
    hr.appendChild(th);
    var f = document.createElement('th'), inp = document.createElement('input');
    inp.placeholder = c.type === 'num' ? '>0' : 'filter';
    inp.oninput = function () { filters[i] = inp.value.trim(); shown = page; draw(); };
    f.appendChild(inp); fr.appendChild(f);
  });
  thead.appendChild(hr); thead.appendChild(fr); table.appendChild(thead); table.appendChild(tbody);
  var more = document.createElement('button');
  more.onclick = function () { shown += page * 5; draw(); };
  el.appendChild(info); wrap.appendChild(table); el.appendChild(wrap); el.appendChild(more);
  function numTest(f) {
    var m;
    if ((m = /^(-?[\d.]+)\.\.(-?[\d.]+)$/.exec(f))) return function (v) { return v != null && v >= +m[1] && v <= +m[2]; };
    if ((m = /^(>=|<=|>|<|=)?\s*(-?[\d.]+)$/.exec(f))) {
      var n = +m[2], op = m[1] || '=';
      return function (v) { if (v == null) return false; return op === '>' ? v > n : op === '<' ? v < n : op === '>=' ? v >= n : op === '<=' ? v <= n : v === n; };
    }
    return function () { return true; };
  }
  function draw() {
    var tests = filters.map(function (f, i) {
      if (!f) return null;
      if (cols[i].type === 'num') return numTest(f);
      var neg = f[0] === '!', exact = f[0] === '=', q = (neg || exact ? f.slice(1) : f).toLowerCase();
      if (!q) return null;
      return function (v) { var hit = exact ? v === q : v.indexOf(q) >= 0; return neg ? !hit : hit; };
    });
    var idx = [];
    for (var r = 0; r < rows.length; r++) {
      var ok = true;
      for (var c = 0; c < cols.length; c++) if (tests[c] && !tests[c](keyed[r][c])) { ok = false; break; }
      if (ok) idx.push(r);
    }
    if (sortCol >= 0) idx.sort(function (a, b) {
      var x = keyed[a][sortCol], y = keyed[b][sortCol];
      if (x == null && y == null) return 0; if (x == null) return 1; if (y == null) return -1;
      return x < y ? -sortDir : x > y ? sortDir : 0;
    });
    var out = [], n = Math.min(shown, idx.length);
    for (var k = 0; k < n; k++) {
      var row = rows[idx[k]], cells = '';
      for (var c2 = 0; c2 < cols.length; c2++) {
        var v = row[c2] == null ? '' : row[c2], t = cols[c2].type;
        cells += t === 'num' ? '<td class="num">' + v + '</td>' : t === 'html' ? '<td>' + v + '</td>'
          : '<td>' + String(v).replace(/&/g, '&amp;').replace(/</g, '&lt;') + '</td>';
      }
      out.push('<tr>' + cells + '</tr>');
    }
    tbody.innerHTML = out.join('');
    info.textContent = idx.length + ' of ' + rows.length + ' rows' + (n < idx.length ? ' (showing ' + n + ')' : '');
    more.style.display = n < idx.length ? '' : 'none'; more.textContent = 'show more';
    Array.prototype.forEach.call(hr.children, function (th, i) {
      th.className = i === sortCol ? (sortDir > 0 ? 'sorted-asc' : 'sorted-desc') : '';
    });
  }
  draw();
}
function tableFromScript(elId, dataId) {
  var d = JSON.parse(document.getElementById(dataId).textContent);
  makeTable(document.getElementById(elId), d);
}
function tableFromUrl(elId, url) {
  var el = document.getElementById(elId); el.textContent = 'loading…';
  fetch(url).then(function (r) { return r.json(); }).then(function (d) { el.textContent = ''; makeTable(el, d); })
    .catch(function (e) { el.textContent = 'could not load ' + url + ': ' + e; });
}
"""

_tid = [0]


def slug(model):
    return re.sub(r"[^A-Za-z0-9._-]", "_", model)


def jdump(o):
    return json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def table(columns, rows, sort=None, page=200):
    """An inline table: data embedded in the page."""
    _tid[0] += 1
    i = _tid[0]
    d = dict(columns=columns, rows=rows, pageSize=page)
    if sort:
        d["sort"] = sort
    return ('<div id="t%d"></div><script type="application/json" id="d%d">%s</script>'
            '<script>tableFromScript("t%d","d%d")</script>' % (i, i, jdump(d), i, i))


def col(title, type="text", tip=None):
    c = dict(title=title, type=type)
    if tip:
        c["tip"] = tip
    return c


def page(path, title, body, depth=0):
    up = "../" * depth
    nav = " ".join('<a href="%s%s">%s</a>' % (up, h, E(t)) for h, t in NAV)
    doc = ("<!doctype html><html lang=en><head><meta charset=utf-8>"
           "<meta name=viewport content='width=device-width,initial-scale=1'>"
           "<title>%s — Atlas names study</title><link rel=stylesheet href='%sstyle.css'>"
           "<script src='%stable.js'></script></head><body><nav><b>Atlas names study</b> &nbsp; %s</nav>"
           "<h1>%s</h1>%s</body></html>") % (E(title), up, up, nav, E(title), body)
    full = os.path.join(SITE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(doc)


def tlink(tid, depth=0, at=None, label=None):
    return '<a href="%stext.html?id=%d%s">%s</a>' % (
        "../" * depth, tid, "&at=%d" % at if at is not None else "", label or ("#%d" % tid))


def ctx(text, s, e, n=70):
    left = text[max(0, s - n):s].replace("\n", " ⏎ ")
    right = text[e:e + n].replace("\n", " ⏎ ")
    return "%s<mark>%s</mark>%s" % (E(left), E(text[s:e].replace("\n", " ⏎ ")), E(right))


def pct(a, b):
    return round(100.0 * a / b, 1) if b else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rev", required=True)
    a = ap.parse_args()
    db = sqlite3.connect("file:%s?mode=ro" % os.path.join(HERE, "data", "names.db"), uri=True)
    snap = sqlite3.connect("file:%s?mode=ro" % os.path.join(HERE, "data", "snapshot_r%s.sqlite" % a.rev), uri=True)
    q = lambda s, *p: db.execute(s, p).fetchall()
    run = dict(q("SELECT key, value FROM run"))
    stats = json.loads(run["stats"])
    os.makedirs(SITE, exist_ok=True)
    for d in ("pattern", "model", "m", "n"):
        shutil.rmtree(os.path.join(SITE, d), ignore_errors=True)
    open(os.path.join(SITE, "style.css"), "w").write(CSS)
    open(os.path.join(SITE, "table.js"), "w").write(JS)

    texts = {}
    def text_of(tid):
        if tid not in texts:
            texts[tid] = snap.execute("SELECT text FROM texts WHERE id=?", (tid,)).fetchone()[0]
        return texts[tid]

    cov = {r[0]: r for r in q("SELECT text_id, model, length, n_strict, n_wide, n_names_strict, "
                              "n_names_wide, n_statements, covered, flag, all_in_place, tagged "
                              "FROM text_cov")}
    def status(r):
        if r[9]:
            return 4
        if r[8]:
            return 0
        if r[6]:
            return 2
        return 3
    models = sorted(set(r[1] for r in cov.values()))
    midx = {m: i for i, m in enumerate(models)}
    pats = q("SELECT id, version, round, added, tier, yields, family, regex, flags, stop, max_words, "
             "origin_text, origin_excerpt, what, note, status, retired_reason, mask, reject, tier_basis, "
             "min_occ, max_df FROM patterns ORDER BY rowid")
    active = [p for p in pats if p[15] == "active"]
    retired = [p for p in pats if p[15] == "retired"]
    ev = {r[0]: r for r in q("SELECT * FROM pattern_eval")}
    pstat = {r[0]: r for r in q("SELECT pattern_id, count(*), count(distinct text_id), count(distinct norm) "
                                "FROM mentions GROUP BY 1")}
    pmodels = Counter(r[0] for r in q("SELECT pattern_id FROM pattern_model"))
    readings = q("SELECT round, text_id, basis, saw, note FROM readings ORDER BY round, rowid")
    read_round = {}
    for r in readings:
        read_round.setdefault(r[1], r[0])

    # ------------------------------------------------------------------ index
    rounds = q("SELECT round, date, note, stats FROM rounds ORDER BY round")
    rrows = []
    for rnd, date, note, st in rounds:
        st = json.loads(st)
        ok = st["texts"] - st.get("flagged", 0)
        rrows.append([rnd, date, st["patterns"], st["strict_patterns"], st["mentions"],
                      st["covered"], pct(st["covered"], ok), st["wide_only"], st["nothing"], note])
    ok = stats["texts"] - stats["flagged"]
    receipt = json.loads(run.get("release_receipt", "{}"))
    body = """
<p>This site shows a study in progress: finding the names that language models gave to the
beings they wrote into the <a href="https://atlas.animalabs.ai">Atlas</a>. The Atlas asks each
model to describe who or what lives in a place the same model described earlier. No text has a
name field; the names are inside the prose, in many forms. The study collects them with regular
expressions, and this site shows every pattern, what it catches, and what is still missed.</p>

<h2>What was read</h2>
<table class=kv>
<tr><td>Atlas release</td><td>r%(rev)s, cut %(cut)s</td></tr>
<tr><td>Release digest</td><td><code>%(digest)s</code></td></tr>
<tr><td>Texts</td><td>%(texts)d creature texts by %(nmodels)d models: every creature text of the release, as written</td></tr>
<tr><td>Content hash</td><td><code>%(content)s</code> (sha256 over the ids and texts, in id order)</td></tr>
<tr><td>Patterns file hash</td><td><code>%(phash)s</code></td></tr>
<tr><td>Built</td><td>%(built)s</td></tr>
</table>

<h2>Words used on this site</h2>
<ul>
<li><b>Pattern</b>: a regular expression written after seeing a form of naming in a text. Each
pattern page shows the passage it was first seen in.</li>
<li><b>Hit</b>: one place in one text where a pattern matched.</li>
<li><b>Name</b>: the captured string with its article, markup and edge punctuation removed,
compared without regard to case. A name may be one word or several. Names here include names
of kinds, of single beings, of places and of things, and descriptions that stand where a name
would ("those who …"). A word for a role or function that designates a kind ("the grazers", "the
tenders") counts as a name; an ordinary species word ("the crickets", "moss") does not.</li>
<li><b>Strict pattern</b>: at least 80%% of a read sample of its hits were names. A
<b>wide pattern</b> collects candidates and has not met that bar.</li>
<li><b>Covered text</b>: a text with at least one name from a strict pattern. New forms of
naming are looked for by reading the texts that are not covered.</li>
<li><b>Also in the place text</b>: the same string occurs in the description of the place that
the creature text was written for. The name was already there when the creature text was
written. This says where a name first appeared; it does not say whether it names a place or a
being.</li>
<li><b>Flagged text</b>: a text left out of the counts. Either the corpus taggers marked it as
broken, a refusal or off-topic, or it is empty, or it failed a word check made here (see
<a href="flagged.html">Flagged texts</a>).</li>
</ul>

<h2>Where it stands</h2>
<table class=kv>
<tr><td>Patterns</td><td>%(np)d active (%(ns)d strict, %(nw)d wide), %(nr)d earlier versions kept</td></tr>
<tr><td>Hits</td><td>%(mentions)d</td></tr>
<tr><td>Distinct names from strict patterns</td><td>%(dns)d</td></tr>
<tr><td>Distinct strings from any pattern</td><td>%(dn)d</td></tr>
<tr><td>Texts counted</td><td>%(ok)d (%(flagged)d flagged and left out)</td></tr>
<tr><td>Covered</td><td>%(covered)d (%(cp)s%%)</td></tr>
<tr><td>&nbsp; of those, every name is also in the place text</td><td>%(place)d</td></tr>
<tr><td>Only candidates from wide patterns</td><td>%(wide)d</td></tr>
<tr><td>Nothing found</td><td>%(nothing)d</td></tr>
<tr><td>Statements about having no name</td><td>%(st)d hits</td></tr>
</table>

<h2>Rounds</h2>
<p>A round is: read texts, write or correct patterns, run them over every text, read a sample of
each pattern's hits.</p>
%(rounds)s

<h2>Known gaps</h2>
<ul>
<li>"Covered" does not mean every name in the text was found, only that one was. The
<a href="recall.html">recall checks</a> measure how many are found.</li>
<li>Names of places and of beings are not told apart.</li>
<li>A name longer than the pattern expects is cut short: a capitalised run ends at the first
lower-case word that is not one of a short list of joining words ("of", "in", "who", "that" …).</li>
<li>Singular and plural forms of one name are counted as two names ("Weaver", "Weavers").</li>
<li>The sample verdicts were given by one reader, the model that wrote the patterns.</li>
<li>All texts are treated as English.</li>
</ul>

<h2>Rebuilding</h2>
<pre>./snapshot.sh %(rev)s              # copy the creature texts of release r%(rev)s
python3 extract.py --rev %(rev)s   # run patterns.py over every text, write data/names.db
python3 build_site.py --rev %(rev)s</pre>
<p class=small>snapshot.sh needs access to the machine that holds the releases. The same texts
are public through the Atlas API and are exported to the atlas-texts repository.</p>
""" % dict(rev=a.rev, cut=E(run.get("release_cut_at", "")[:19]), digest=E(run.get("release_corpus_digest", "")),
           texts=stats["texts"], nmodels=len(models), content=run["content_sha256"],
           phash=run["patterns_sha256"], built=run["built_at"], np=len(active),
           ns=sum(1 for p in active if p[4] == "strict"), nw=sum(1 for p in active if p[4] == "wide"),
           nr=len(retired), mentions=stats["mentions"], dns=stats["distinct_names_strict"],
           dn=stats["distinct_names"], ok=ok, flagged=stats["flagged"], covered=stats["covered"],
           cp=pct(stats["covered"], ok), place=stats["covered_all_in_place"], wide=stats["wide_only"],
           nothing=stats["nothing"], st=stats["statements"],
           rounds=table([col("round", "num"), col("date"), col("patterns", "num"), col("strict", "num"),
                         col("hits", "num"), col("covered texts", "num"), col("covered %", "num"),
                         col("candidates only", "num"),
                         col("nothing", "num"), col("what was done")], rrows, sort=[0, 1]))
    page("index.html", "Names in the Atlas creature texts", body)

    # --------------------------------------------------------------- patterns
    def evcells(pid):
        e = ev.get(pid)
        if not e:
            return ["", "", ""]
        n = e[1]
        names = e[2] + e[3] + e[4] + e[5]
        return [n, pct(names, n), pct(e[2], n)]
    prow = []
    for p in active:
        st = pstat.get(p[0], (p[0], 0, 0, 0))
        prow.append(['<a href="pattern/%s.html">%s</a>' % (p[0], p[0]), p[6],
                     '<span class="%s">%s</span>' % (p[4], p[4]), p[1], p[2], st[1], st[2],
                     pmodels.get(p[0], 0), st[3]] + evcells(p[0]) + [p[13]])
    rrow = [[p[0], p[1], p[2], p[16] or "", p[19] or ""] for p in retired]
    body = """
<p>Every pattern in use. Click a pattern for its regular expression, the passage it was first
seen in, a sample of its hits, the hits that were read and judged, and its counts by model.</p>
%s
<h2>Earlier versions</h2>
<p>A pattern that is changed keeps its name and gets a new version. The earlier version stays
here with the reason it was replaced and the sample that showed the problem.</p>
%s""" % (
        table([col("pattern", "html"), col("form"), col("tier", "html"), col("v", "num"),
               col("round", "num"), col("hits", "num"), col("texts", "num", "texts with at least one hit"),
               col("models", "num", "models with at least one hit"), col("distinct", "num", "distinct captured strings"),
               col("read", "num", "hits read and judged by eye"),
               col("names %", "num", "share of read hits judged to be a name of a being, place or thing (or, for statement patterns, a statement about the inhabitants)"),
               col("beings %", "num", "share of read hits judged to be the name of a being or kind"),
               col("what it catches")], prow, sort=[5, -1]),
        table([col("pattern"), col("v", "num"), col("round", "num"), col("why it was replaced"),
               col("sample that showed it")], rrow))
    page("patterns.html", "Patterns", body)

    labels = defaultdict(list)
    for r in q("SELECT text_id, pattern_id, start, end, surface, verdict, round FROM labels"):
        labels[r[1]].append(r)
    hist = defaultdict(list)
    for p in retired:
        hist[p[0]].append(p)
    mtexts = Counter(r[1] for r in cov.values() if not r[9])
    for p in active:
        pid = p[0]
        st = pstat.get(pid, (pid, 0, 0, 0))
        rows_all = q("SELECT text_id, start, end, surface FROM mentions WHERE pattern_id=? ORDER BY text_id, start", pid)
        rnd = random.Random("site:" + pid)
        samp = rnd.sample(rows_all, min(300, len(rows_all)))
        srows = [[tlink(t, 1, s), cov[t][1].split("/")[-1], (surf if len(surf) < 90 else surf[:87] + "…"),
                  ctx(text_of(t), s, e)] for t, s, e, surf in samp]
        lrows = []
        for t, _pid, s, e, surf, v, rd in labels.get(pid, ()):
            lrows.append([tlink(t, 1, s), cov[t][1].split("/")[-1], VERDICTS.get(v, v), rd,
                          ctx(text_of(t), s, e)])
        mrows = [[ '<a href="../model/%s.html">%s</a>' % (slug(m), E(m)), n, nt, mtexts[m], pct(nt, mtexts[m])]
                 for m, n, nt in q("SELECT model, n_mentions, n_texts FROM pattern_model WHERE pattern_id=?", pid)]
        top = q("SELECT norm, count(*), count(distinct text_id) FROM mentions WHERE pattern_id=? AND norm!='' "
                "GROUP BY 1 ORDER BY 3 DESC LIMIT 300", pid)
        trows = [[n, c, ct] for n, c, ct in top]
        e = ev.get(pid)
        evline = ""
        if e:
            evline = ("<tr><td>Read by eye</td><td>%d hits: %d beings, %d places, %d things, %d statements, "
                      "%d not names, %d in broken texts. %d earlier verdicts no longer apply because the "
                      "pattern stopped matching there (%d of those were not names).</td></tr>"
                      % (e[1], e[2], e[3], e[4], e[5], e[6], e[7], e[8], e[9]))
        hrows = "".join("<h3>version %d (round %d)</h3><p>%s</p><p class=small>Sample: %s</p><div class=rx>%s</div>"
                        % (h[1], h[2], E(h[16] or ""), E(h[19] or ""), E(h[7])) for h in hist.get(pid, ()))
        body = """
<p>%s</p>%s
<table class=kv>
<tr><td>Tier</td><td><span class="%s">%s</span> %s</td></tr>
<tr><td>Form</td><td>%s</td></tr>
<tr><td>Version</td><td>%d, written in round %d (%s)</td></tr>
<tr><td>Hits</td><td>%d in %d texts by %d models; %d distinct strings</td></tr>
%s
<tr><td>Conditions</td><td>%s</td></tr>
</table>
<h2>First seen in</h2>
<blockquote>%s</blockquote><p class=small>text %s · <a href="%s">in the Atlas</a></p>
<h2>Regular expression</h2><div class=rx>%s</div>
<h2>Hits that were read</h2>
<p class=small>A seeded random sample, read in context and judged.</p>%s
<h2>A sample of hits</h2>
<p class=small>300 hits drawn at random (fixed seed); not judged.</p>%s
<h2>By model</h2>%s
<h2>Most frequent captures</h2>%s
%s""" % (
            E(p[13]), ("<p><b>Weakness:</b> %s</p>" % E(p[14])) if p[14] else "",
            p[4], p[4], E(p[19] or ""), E(p[6]), p[1], p[2], p[3], st[1], st[2], pmodels.get(pid, 0), st[3],
            evline,
            E("; ".join(x for x in [
                "flags: " + p[8] if p[8] else "", "stoplist: " + p[9] if p[9] else "",
                "does not look inside: " + p[17] if p[17] else "",
                "drops captures matching: " + p[18] if p[18] else "",
                "at most %d words" % p[10] if p[10] else "",
                "the captured string must occur at least %d times in the text" % p[20] if p[20] else "",
                "a single word is dropped if it occurs in more than %d%% of all texts" % round(100 * p[21]) if p[21] else ""] if x) or "none"),
            E(p[12]), tlink(p[11], 1), ATLAS % p[11], E(p[7]),
            table([col("text", "html"), col("model"), col("verdict"), col("round", "num"), col("in context", "html")], lrows) if lrows else "<p>None yet.</p>",
            table([col("text", "html"), col("model"), col("captured"), col("in context", "html")], srows, page=100),
            table([col("model", "html"), col("hits", "num"), col("texts with a hit", "num"),
                   col("texts of the model", "num"), col("% of texts", "num")], mrows, sort=[4, -1], page=130),
            table([col("captured string"), col("hits", "num"), col("texts", "num")], trows, page=100),
            ("<h2>Earlier versions</h2>" + hrows) if hrows else "")
        page("pattern/%s.html" % pid, "Pattern: " + pid, body, 1)

    # ----------------------------------------------------------------- models
    per = defaultdict(lambda: [0, 0, 0, 0, 0])
    for r in cov.values():
        per[r[1]][status(r)] += 1
        if status(r) == 0 and r[10]:
            per[r[1]][1] += 1          # covered, and every name is also in the place text
    stm = Counter(r[1] for r in cov.values() if r[7] and not r[9])
    mnames = {r[0]: r for r in q(
        "SELECT c.model, count(distinct n.norm), count(*) FROM text_names n JOIN text_cov c ON c.text_id=n.text_id "
        "WHERE n.tier='strict' AND c.flag='' GROUP BY 1")}
    mrows = []
    for m in models:
        c = per[m]
        okm = c[0] + c[2] + c[3]
        mn = mnames.get(m, (m, 0, 0))
        mrows.append(['<a href="model/%s.html">%s</a>' % (slug(m), E(m)), okm, c[4], c[0], pct(c[0], okm),
                      c[1], c[2], c[3], stm[m], mn[1], round(mn[2] / float(okm), 2) if okm else ""])
    body = """
<p>One row per model. "Covered" and the other columns are defined on the overview page. The last
two columns count names from strict patterns.</p>%s""" % table(
        [col("model", "html"), col("texts", "num", "texts counted (flagged texts left out)"), col("flagged", "num"),
         col("covered", "num"), col("covered %", "num"),
         col("all names also in place text", "num", "covered texts in which every name from a strict pattern also occurs in the place description"),
         col("candidates only", "num"), col("nothing", "num"),
         col("texts with a no-name statement", "num"), col("distinct names", "num"),
         col("names per text", "num")], mrows, sort=[4, 1], page=130)
    page("models.html", "Models", body)

    tn = defaultdict(list)
    for r in q("SELECT text_id, norm, display, n_mentions, patterns, tier, first_pos, occurrences, in_place_text "
               "FROM text_names"):
        tn[r[0]].append(r)
    by_model = defaultdict(list)
    for tid, r in cov.items():
        by_model[r[1]].append(tid)
    pm = defaultdict(list)
    for pid, m, n, nt in q("SELECT pattern_id, model, n_mentions, n_texts FROM pattern_model"):
        pm[m].append((pid, n, nt))
    tier_of = {p[0]: p[4] for p in active}
    for m in models:
        tids = sorted(by_model[m])
        agg = {}
        trows = []
        for tid in tids:
            r = cov[tid]
            names = sorted(tn.get(tid, ()), key=lambda x: x[6])
            strict = [x for x in names if x[5] == "strict"]
            new = [x[2] for x in strict if not x[8]]
            shown = [x[2] for x in strict]
            trows.append([tlink(tid, 1), r[2], STATUS[status(r)] if not r[9] else "flagged: " + r[9],
                          len(strict), ", ".join(shown[:8]) + (" …" if len(shown) > 8 else ""),
                          len(strict) - len(new), r[6], r[7], read_round.get(tid, "")])
            if r[9]:
                continue
            for x in names:
                g = agg.setdefault(x[1], [x[2], 0, 0, 0, 0, set()])
                g[2] += 1; g[4] += x[3]; g[5].update(x[4].split(","))
                if x[5] == "strict":
                    g[1] += 1; g[0] = x[2]
                if x[8]:
                    g[3] += 1
        nrows = [['<a href="../name.html?n=%s">%s</a>' % (E(k, quote=True).replace(" ", "%20"), E(g[0])),
                  g[1], g[2], g[3], g[4], ", ".join(sorted(g[5]))] for k, g in agg.items()]
        c = per[m]
        okm = c[0] + c[2] + c[3]
        prs = [['<a href="../pattern/%s.html">%s</a>' % (pid, pid),
                '<span class="%s">%s</span>' % (tier_of.get(pid, ""), tier_of.get(pid, "")), n, nt, pct(nt, okm)]
               for pid, n, nt in pm[m]]
        body = """
<table class=kv>
<tr><td>Texts</td><td>%d counted, %d flagged</td></tr>
<tr><td>Covered</td><td>%d (%s%%); in %d of them every name is also in the place text</td></tr>
<tr><td>Candidates only / nothing</td><td>%d / %d</td></tr>
</table>
<h2>Patterns in this model's texts</h2>%s
<h2>Names</h2>
<p class=small>Every captured string in this model's texts. "Strict texts" counts the texts where a
strict pattern caught it; "in place" counts the texts where the same string is also in the place
description.</p>%s
<h2>Texts</h2>%s""" % (
            okm, c[4], c[0], pct(c[0], okm), c[1], c[2], c[3],
            table([col("pattern", "html"), col("tier", "html"), col("hits", "num"), col("texts", "num"),
                   col("% of texts", "num")], prs, sort=[4, -1], page=50),
            table([col("name", "html"), col("strict texts", "num"), col("texts", "num"), col("in place", "num"),
                   col("hits", "num"), col("patterns")], nrows, sort=[1, -1], page=100),
            table([col("text", "html"), col("length", "num"), col("status"), col("names", "num", "names from strict patterns"),
                   col("names found"), col("also in place text", "num", "of those names, how many also occur in the place description"), col("candidates", "num"),
                   col("no-name statements", "num"), col("read in round", "num")], trows, page=100))
        page("model/%s.html" % slug(m), "Model: " + m, body, 1)

    # ------------------------------------------------------------------ names
    os.makedirs(os.path.join(SITE, "n"), exist_ok=True)
    allnames = q("SELECT norm, display, n_texts, n_texts_strict, n_texts_new, n_models, n_models_strict, "
                 "n_mentions, patterns, top_models FROM names")
    def nrow(r):
        return ['<a href="name.html?n=%s">%s</a>' % (E(r[0], quote=True).replace(" ", "%20"), E(r[1])),
                r[3], r[4], r[6], r[2], r[5], r[7], len(r[0].split()), r[8], r[9]]
    ncols = [col("name", "html"), col("strict texts", "num", "texts where a strict pattern caught it"),
             col("not in place text", "num", "of those, texts where the string does not occur in the place description: the name first appears in the creature text"),
             col("strict models", "num", "models with at least one such text"),
             col("texts", "num", "texts where any pattern caught it"),
             col("models", "num"), col("hits", "num"), col("words", "num"), col("patterns"),
             col("most frequent in")]
    with open(os.path.join(SITE, "n", "strict.json"), "w", encoding="utf-8") as f:
        f.write(jdump(dict(columns=ncols, rows=[nrow(r) for r in allnames if r[3] > 0], pageSize=200, sort=[1, -1])))
    with open(os.path.join(SITE, "n", "candidates.json"), "w", encoding="utf-8") as f:
        f.write(jdump(dict(columns=ncols, rows=[nrow(r) for r in allnames if r[3] == 0], pageSize=200, sort=[4, -1])))
    page("names.html", "Names",
         """<p>Every distinct string caught by a strict pattern in at least one text (%d). Click a name to
see the texts it occurs in. Strings caught only by wide patterns are on a
<a href="names_candidates.html">separate page</a> (%d).</p>
<p class=small>Singular and plural are separate rows. Frequent rows near the top include ordinary
capitalised words ("Water", "Body"): the capitalisation patterns take any capitalised word after
"the".</p><div id=nt></div><script>tableFromUrl("nt","n/strict.json")</script>"""
         % (sum(1 for r in allnames if r[3] > 0), sum(1 for r in allnames if r[3] == 0)))
    page("names_candidates.html", "Candidate strings",
         """<p>Strings caught only by wide patterns. Most are not names. They are kept so that names
written in forms that the strict patterns miss can be found here.</p>
<div id=nt></div><script>tableFromUrl("nt","n/candidates.json")</script>""")

    buckets = defaultdict(dict)
    for tid, names in tn.items():
        if cov[tid][9]:
            continue
        for x in names:
            b = hashlib.sha1(x[1].encode("utf-8")).hexdigest()[:2]
            buckets[b].setdefault(x[1], []).append([tid, midx[cov[tid][1]], 1 if x[5] == "strict" else 0,
                                                     x[3], x[7], x[8], x[4]])
    for b, d in buckets.items():
        with open(os.path.join(SITE, "n", b + ".json"), "w", encoding="utf-8") as f:
            f.write(jdump(d))
    with open(os.path.join(SITE, "n", "models.json"), "w", encoding="utf-8") as f:
        f.write(jdump(models))
    page("name.html", "Name", """<div id=head></div><div id=nt></div>
<script src="sha1.js"></script><script>
(function () {
  var n = new URLSearchParams(location.search).get('n') || '';
  document.querySelector('h1').textContent = 'Name: ' + n;
  var b = sha1(n).slice(0, 2);
  Promise.all([fetch('n/' + b + '.json').then(function (r) { return r.json(); }),
               fetch('n/models.json').then(function (r) { return r.json(); })]).then(function (res) {
    var rows = (res[0][n] || []).map(function (r) {
      return ['<a href="text.html?id=' + r[0] + '">#' + r[0] + '</a>', res[1][r[1]], r[2] ? 'strict' : 'wide',
              r[3], r[4], r[5] ? 'yes' : '', r[6]];
    });
    document.getElementById('head').innerHTML = '<p>' + rows.length + ' texts.</p>';
    makeTable(document.getElementById('nt'), {columns: [
      {title: 'text', type: 'html'}, {title: 'model', type: 'text'}, {title: 'tier', type: 'text'},
      {title: 'hits', type: 'num'}, {title: 'occurrences in text', type: 'num', tip: 'times the string occurs in the text, any case'},
      {title: 'in place description', type: 'text'}, {title: 'patterns', type: 'text'}], rows: rows, pageSize: 300, sort: [1, 1]});
  });
})();</script>""")
    open(os.path.join(SITE, "sha1.js"), "w").write(SHA1_JS)


    # ----------------------------------------------------------------- recall
    rc = q("SELECT chk, date, pool, text_id, read_chars, name, caught, caught_now, forms_missed, note FROM recall")
    summ = defaultdict(lambda: dict(texts=set(), noname=set(), n=0, then=Counter(), now=Counter(), date=""))
    rrows = []
    for chk, date, pool, tid, chars, name, caught, now, forms, note in rc:
        s = summ[(chk, pool)]
        s["texts"].add(tid); s["date"] = date
        if name is None:
            s["noname"].add(tid)
        else:
            s["n"] += 1; s["then"][caught] += 1; s["now"][now] += 1
        rrows.append([chk, pool, tlink(tid), cov[tid][1], name or "(no name in the text)", caught or "", now or "",
                      "; ".join(json.loads(forms)), note or ""])
    srows = []
    for (chk, pool), s in sorted(summ.items()):
        srows.append([chk, s["date"], pool, len(s["texts"]), len(s["noname"]), s["n"],
                      s["then"]["strict"], s["then"]["wide"], s["then"]["missed"],
                      s["now"]["strict"], s["now"]["wide"], s["now"]["missed"],
                      pct(s["now"]["strict"], s["n"])])
    page("recall.html", "Recall checks",
         """<p>A recall check: texts are drawn at random and read whole (up to a few thousand characters),
and every name seen by eye is written down with what caught it at the time: a strict pattern, only
a wide one, or nothing. "Now" columns are recomputed against the current patterns, so they move as
patterns are added. The samples are small; the percentages show direction, not a measured rate.</p>
<p>The "now" numbers of an earlier check are optimistic: new patterns are written from the very
names that check found missing. Only the "then" numbers of a fresh check measure the patterns
honestly, so a new sample is drawn each round.</p>
<p>The same reader wrote the patterns and judged what counts as a name.</p>
<h2>By check</h2>%s<h2>Every name</h2>%s""" % (
             table([col("check", "num"), col("date"), col("texts drawn from"), col("texts", "num"),
                    col("texts with no name", "num", "texts in which the reader saw no name at all"),
                    col("names seen", "num"), col("strict then", "num"), col("wide then", "num"),
                    col("missed then", "num"), col("strict now", "num"), col("wide now", "num"),
                    col("missed now", "num"), col("strict now %", "num")], srows, sort=[0, 1]),
             table([col("check", "num"), col("pool"), col("text", "html"), col("model"), col("name seen by eye"),
                    col("caught then"), col("caught now"), col("forms that were missed"), col("note")], rrows)))

    # -------------------------------------------------------------- uncovered
    urows = []
    for tid, r in sorted(cov.items()):
        s = status(r)
        if s in (2, 3):
            urows.append([tlink(tid), r[1], r[2], STATUS[s], r[6], r[7], r[11] or "untagged", read_round.get(tid, "")])
    page("uncovered.html", "Uncovered texts",
         """<p>Texts in which no strict pattern found a name (%d). New forms of naming are looked for
here: a sample is read each round, and the round in which a text was read is in the last column.</p>%s"""
         % (len(urows), table(
             [col("text", "html"), col("model"), col("length", "num"), col("status"),
              col("candidates", "num", "strings from wide patterns"), col("no-name statements", "num"),
              col("corpus status", "text", "the status the corpus taggers recorded for the text; many newer texts have none"),
              col("read in round", "num")], urows)))

    # --------------------------------------------------------------- readings
    rrows = []
    for rnd, tid, basis, saw, note in readings:
        rrows.append([rnd, tlink(tid), cov[tid][1], basis, "; ".join(json.loads(saw)), note or ""])
    page("readings.html", "Reading log",
         "<p>Texts read by eye to find forms of naming, with what was seen in each.</p>" + table(
             [col("round", "num"), col("text", "html"), col("model"), col("how it was chosen"),
              col("forms of naming seen"), col("note")], rrows))

    frows = [[tlink(tid), r[1], r[9], "corpus tagger" if r[9] in ("broken", "refusal", "off-topic") else "check made here",
              r[2]] for tid, r in sorted(cov.items()) if r[9]]
    untagged = sum(1 for r in cov.values() if not r[11])
    page("flagged.html", "Flagged texts",
         """<p>Texts left out of the counts (%d).</p>
<ul>
<li><b>broken, refusal, off-topic</b>: the status recorded in the corpus by its taggers (language
models that read each text). "Broken" covers repetition and garbled endings as well as runs of
unrelated tokens. The study takes these as given.</li>
<li><b>empty</b>: under 50 characters.</li>
<li><b>not prose (word check)</b>: under 15%% of the words are common English function words. This
check is made here and is crude. It is the only one applied to the %d texts that have no status
in the corpus; a text among those that is broken in a subtler way is not flagged.</li>
</ul>""" % (len(frows), untagged) + table(
             [col("text", "html"), col("model"), col("flag"), col("source"), col("length", "num")], frows, sort=[1, 1]))

    # ------------------------------------------------------- text viewer data
    tdir = os.path.join(SITE, "t")
    os.makedirs(tdir, exist_ok=True)
    marker = os.path.join(tdir, "content.sha256")
    have = os.path.exists(marker) and open(marker).read().strip() == run["content_sha256"]
    if not have:
        cur, bucket = None, {}
        def flush():
            if bucket:
                with open(os.path.join(tdir, "%d.json" % cur), "w", encoding="utf-8") as f:
                    f.write(jdump(bucket))
        for tid, model, text, place_id in snap.execute("SELECT id, model, text, place_id FROM texts ORDER BY id"):
            b = tid // 100
            if b != cur:
                flush(); cur, bucket = b, {}
            bucket[tid] = [model, text]
        flush()
        open(marker, "w").write(run["content_sha256"])
    mdir = os.path.join(SITE, "m")
    os.makedirs(mdir, exist_ok=True)
    cur, bucket = None, {}
    def flushm():
        if bucket:
            with open(os.path.join(mdir, "%d.json" % cur), "w", encoding="utf-8") as f:
                f.write(jdump(bucket))
    for tid, pid, s, e in db.execute("SELECT text_id, pattern_id, start, end FROM mentions ORDER BY text_id, start"):
        b = tid // 100
        if b != cur:
            flushm(); cur, bucket = b, {}
        bucket.setdefault(tid, []).append([s, e, pid])
    flushm()
    with open(os.path.join(SITE, "m", "tiers.json"), "w") as f:
        f.write(jdump({p[0]: ("st" if p[5] == "statement" else "s" if p[4] == "strict" else "w") for p in active}))
    with open(os.path.join(SITE, "m", "status.json"), "w") as f:
        f.write(jdump({tid: [STATUS[status(r)], r[9]] for tid, r in cov.items()}))
    page("text.html", "Text", """<div id=head></div>
<p class=small><mark class=s>strict pattern</mark> &nbsp; <mark>wide pattern</mark> &nbsp;
<mark class=st>statement about naming</mark> &nbsp; hover a highlight to see which patterns matched.</p>
<div id=body class=text></div><h2>Hits in this text</h2><div id=hits></div>
<script>
(function () {
  var qs = new URLSearchParams(location.search), id = +qs.get('id'), at = qs.get('at'), b = Math.floor(id / 100);
  var esc = function (s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;'); };
  var get = function (u) { return fetch(u).then(function (r) { return r.ok ? r.json() : {}; }); };
  Promise.all([get('t/' + b + '.json'), get('m/' + b + '.json'), get('m/tiers.json'), get('m/status.json')]).then(function (res) {
    var t = res[0][id]; if (!t) { document.getElementById('body').textContent = 'no such text'; return; }
    var ms = res[1][id] || [], tiers = res[2], st = res[3][id] || ['', ''];
    document.querySelector('h1').textContent = 'Text #' + id;
    document.getElementById('head').innerHTML = '<p>' + esc(t[0]) + ' · ' + t[1].length + ' characters · ' + st[0] +
      ' · <a href="https://atlas.animalabs.ai/v3/creature/' + id + '">in the Atlas</a> · <a href="model/' +
      t[0].replace(/[^A-Za-z0-9._-]/g, '_') + '.html">model page</a></p>';
    var text = t[1], cuts = {};
    ms.forEach(function (m) { cuts[m[0]] = 1; cuts[m[1]] = 1; }); cuts[0] = 1; cuts[text.length] = 1;
    var pts = Object.keys(cuts).map(Number).sort(function (a, b) { return a - b; }), out = '';
    for (var i = 0; i + 1 < pts.length; i++) {
      var s = pts[i], e = pts[i + 1], on = ms.filter(function (m) { return m[0] <= s && m[1] >= e; });
      var seg = esc(text.slice(s, e));
      if (!on.length) { out += seg; continue; }
      var cls = on.some(function (m) { return tiers[m[2]] === 's'; }) ? 's' : on.some(function (m) { return tiers[m[2]] === 'w'; }) ? '' : 'st';
      out += '<mark class="' + cls + '" id="p' + s + '" title="' + on.map(function (m) { return m[2]; }).join(', ') + '">' + seg + '</mark>';
    }
    document.getElementById('body').innerHTML = out;
    var rows = ms.map(function (m) {
      return [m[0], esc(text.slice(m[0], m[1])).slice(0, 160), '<a href="pattern/' + m[2] + '.html">' + m[2] + '</a>',
              tiers[m[2]] === 's' ? 'strict' : tiers[m[2]] === 'st' ? 'statement' : 'wide'];
    });
    makeTable(document.getElementById('hits'), {columns: [{title: 'position', type: 'num'}, {title: 'captured', type: 'html'},
      {title: 'pattern', type: 'html'}, {title: 'tier', type: 'text'}], rows: rows, pageSize: 500, sort: [0, 1]});
    if (at) { var el = document.getElementById('p' + at); if (el) el.scrollIntoView({block: 'center'}); }
  });
})();</script>""")
    print("site built: %s" % SITE)


SHA1_JS = r"""
// Minimal SHA-1 of a UTF-8 string, hex output (used only to find a name's data file).
function sha1(str) {
  var msg = unescape(encodeURIComponent(str)), i, j, w = [], H = [0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0];
  var ml = msg.length, words = [];
  for (i = 0; i < ml; i++) words[i >> 2] |= msg.charCodeAt(i) << (24 - (i % 4) * 8);
  words[ml >> 2] |= 0x80 << (24 - (ml % 4) * 8);
  words[(((ml + 8) >> 6) << 4) + 15] = ml * 8;
  var rotl = function (n, s) { return (n << s) | (n >>> (32 - s)); };
  for (i = 0; i < words.length; i += 16) {
    var a = H[0], b = H[1], c = H[2], d = H[3], e = H[4];
    for (j = 0; j < 80; j++) {
      w[j] = j < 16 ? (words[i + j] | 0) : rotl(w[j - 3] ^ w[j - 8] ^ w[j - 14] ^ w[j - 16], 1);
      var f = j < 20 ? ((b & c) | (~b & d)) + 0x5A827999 : j < 40 ? (b ^ c ^ d) + 0x6ED9EBA1
        : j < 60 ? ((b & c) | (b & d) | (c & d)) + 0x8F1BBCDC : (b ^ c ^ d) + 0xCA62C1D6;
      var t = (rotl(a, 5) + f + e + w[j]) | 0;
      e = d; d = c; c = rotl(b, 30); b = a; a = t;
    }
    H[0] = (H[0] + a) | 0; H[1] = (H[1] + b) | 0; H[2] = (H[2] + c) | 0; H[3] = (H[3] + d) | 0; H[4] = (H[4] + e) | 0;
  }
  return H.map(function (h) { return ('00000000' + (h >>> 0).toString(16)).slice(-8); }).join('');
}
"""

if __name__ == "__main__":
    main()
