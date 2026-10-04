#!/usr/bin/env python3
"""Build the static site from data/roles.db, data/names.db and the snapshot.

    python3 build_site.py --rev 15

Names and roles (roles.db, the second instrument) are the main data; the patterns (names.db, the
first instrument) are shown as method. Numbers of the checks come from roles/checks.json.

Writes site/. Text bodies (site/t/) are written once per snapshot and reused; everything
else is rewritten on each build. Serve with:  python3 -m http.server 8795 -d site
"""
import argparse, csv, gzip, hashlib, html, json, os, random, re, shutil, sqlite3, statistics, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "site")
ATLAS = "https://atlas.animalabs.ai/v3/creature/%d"
E = html.escape

VERDICTS = {"b": "being", "p": "place", "t": "thing", "s": "statement", "x": "not a name",
            "g": "broken text"}
NAV = [("index.html", "Overview"), ("names.html", "Names and roles"), ("models.html", "Models"),
       ("texts.html", "Texts"), ("method.html", "Method and checks"), ("flagged.html", "Flagged texts"),
       ("export.html", "Data export")]
NAV1 = [("patterns.html", "Patterns"), ("pattern_names.html", "Names caught by patterns"),
        ("kinds.html", "Kinds of answer"), ("no_names.html", "Texts without names"),
        ("recall.html", "Recall checks"), ("readings.html", "Reading log")]
FIRST = ("<p class=first>This page belongs to the first instrument of the study, the regular-expression "
         "patterns. The names and roles on the main pages come from the second instrument; see "
         "<a href='%smethod.html'>Method and checks</a>.</p>")

CSS = """
body{font:15px/1.45 system-ui,sans-serif;margin:0 auto;max-width:1500px;padding:0 16px 60px;color:#222;background:#fff}
nav{padding:10px 0;border-bottom:1px solid #ccc;margin-bottom:14px}
nav a{margin-right:16px} nav div{font-size:13px;color:#555;margin-top:4px} nav div a{margin-right:12px}
.first{font-size:13px;background:#f6f6f6;border:1px solid #e3e3e3;padding:5px 9px;max-width:900px}
mark.l{background:#9fe3a8} mark.ll{background:#cdeccf}
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
.tbl-tools{font-size:12px;margin:6px 0 2px} .tbl-panel{border:1px solid #ddd;background:#fafafa;padding:6px 8px;margin:4px 0;max-width:900px}
.tbl-panel label{display:inline-block;margin:2px 12px 2px 0;white-space:nowrap}
.tbl-wrap{overflow-x:auto}
code,pre,.rx{font:12px/1.4 ui-monospace,Menlo,monospace}
pre,.rx{background:#f6f6f6;padding:8px;white-space:pre-wrap;word-break:break-all;border:1px solid #e3e3e3}
blockquote{border-left:3px solid #bbb;margin:6px 0;padding:2px 10px;color:#333;white-space:pre-wrap}
mark{background:#ffe08a;padding:0 1px} mark.s{background:#9fe3a8} mark.st{background:#b9d3ff} mark.lo{background:#eadfd2}
.kv td:first-child{white-space:nowrap;color:#555}
.kv{width:auto}
.text{white-space:pre-wrap;max-width:900px;font:15px/1.55 Georgia,serif;border:1px solid #ddd;padding:14px}
.strict{color:#0a6b1f;font-weight:600} .wide{color:#8a6100}
.small{font-size:12px;color:#555}
details.cols{font-size:12px;color:#444;margin:4px 0} details.cols summary{cursor:pointer;color:#555}
details.cols ul{margin:4px 0 6px;padding-left:18px} details.cols li{max-width:900px}
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
  var key = 'cols:' + location.pathname + ':' + (opt.key || cols.map(function (c) { return c.title; }).join('|'));
  var hidden = {};
  try { (JSON.parse(localStorage.getItem(key) || '[]')).forEach(function (i) { hidden[i] = true; }); } catch (e) {}
  var info = document.createElement('div'); info.className = 'tbl-info';
  var tools = document.createElement('div'); tools.className = 'tbl-tools';
  var colBtn = document.createElement('button'); colBtn.textContent = 'columns';
  var panel = document.createElement('div'); panel.className = 'tbl-panel'; panel.style.display = 'none';
  cols.forEach(function (c, i) {
    var lab = document.createElement('label'), cb = document.createElement('input');
    cb.type = 'checkbox'; cb.checked = !hidden[i];
    cb.onchange = function () {
      if (cb.checked) delete hidden[i]; else hidden[i] = true;
      try { localStorage.setItem(key, JSON.stringify(Object.keys(hidden).map(Number))); } catch (e) {}
      build(); draw();
    };
    lab.appendChild(cb); lab.appendChild(document.createTextNode(' ' + c.title)); panel.appendChild(lab);
  });
  colBtn.onclick = function () { panel.style.display = panel.style.display === 'none' ? '' : 'none'; };
  tools.appendChild(colBtn); tools.appendChild(panel);
  var wrap = document.createElement('div'); wrap.className = 'tbl-wrap';
  var table = document.createElement('table'), thead = document.createElement('thead'),
      tbody = document.createElement('tbody');
  var hr = document.createElement('tr'), fr = document.createElement('tr'); fr.className = 'filters';
  var ths = [];
  function build() {
    hr.innerHTML = ''; fr.innerHTML = ''; ths = [];
    cols.forEach(function (c, i) {
      if (hidden[i]) return;
      var th = document.createElement('th'); th.textContent = c.title; if (c.tip) th.title = c.tip;
      th.onclick = function () { if (sortCol === i) sortDir = -sortDir; else { sortCol = i; sortDir = c.type === 'num' ? -1 : 1; } shown = page; draw(); };
      th.dataset.idx = i; hr.appendChild(th); ths.push(th);
      var f = document.createElement('th'), inp = document.createElement('input');
      inp.placeholder = c.type === 'num' ? '>0' : 'filter'; inp.value = filters[i];
      inp.oninput = function () { filters[i] = inp.value.trim(); shown = page; draw(); };
      f.appendChild(inp); fr.appendChild(f);
    });
  }
  build();
  thead.appendChild(hr); thead.appendChild(fr); table.appendChild(thead); table.appendChild(tbody);
  var more = document.createElement('button');
  more.onclick = function () { shown += page * 5; draw(); };
  el.appendChild(tools); el.appendChild(info); wrap.appendChild(table); el.appendChild(wrap); el.appendChild(more);
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
        if (hidden[c2]) continue;
        var v = row[c2] == null ? '' : row[c2], t = cols[c2].type;
        cells += t === 'num' ? '<td class="num">' + v + '</td>' : t === 'html' ? '<td>' + v + '</td>'
          : '<td>' + String(v).replace(/&/g, '&amp;').replace(/</g, '&lt;') + '</td>';
      }
      out.push('<tr>' + cells + '</tr>');
    }
    tbody.innerHTML = out.join('');
    info.textContent = idx.length + ' of ' + rows.length + ' rows' + (n < idx.length ? ' (showing ' + n + ')' : '');
    more.style.display = n < idx.length ? '' : 'none'; more.textContent = 'show more';
    ths.forEach(function (th) {
      th.className = +th.dataset.idx === sortCol ? (sortDir > 0 ? 'sorted-asc' : 'sorted-desc') : '';
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


FORM = '\n<form class=sets onsubmit="var a=this.a.value.trim(),b=this.b.value.trim();location.href=\'name.html?n=\'+encodeURIComponent(a)+(b?\'&vs=\'+encodeURIComponent(b):\'\')+(this.w.checked?\'&words=1\':\'\');return false">\n<p><b>Look up a name or a role, or compare sets of them.</b> Write one string, or several joined by <code>|</code>\n(the lower-cased string as it appears in the tables: <code>keeper|keepers</code>). The match is on the whole\nstring: <code>keepers</code> does not find <code>memory-keepers</code> or <code>keepers of the well</code>. Tick\n"as words" to count every label that holds the word, in any longer string.\nCounts are of texts: a text that has several of the strings is counted once. A second set gives a\ncomparison, model by model.</p>\n<p><label>set: <input name=a size=30 placeholder="keeper|keepers"></label> &nbsp;\n<label>compare with: <input name=b size=30 placeholder="tender|tenders"></label> &nbsp;\n<label><input type=checkbox name=w> as words</label> &nbsp;\n<button>show</button> &nbsp; <span class=small>examples: <a href="name.html?n=keeper%7Ckeepers&vs=tender%7Ctenders">keeper|keepers vs tender|tenders</a>, the same <a href="name.html?n=keeper%7Ckeepers&vs=tender%7Ctenders&words=1">as words</a></span></p>\n</form>'


def columns_note(columns):
    """A visible list of the columns that carry an explanation."""
    items = ["<li><b>%s</b>: %s</li>" % (E(c["title"]), E(c["tip"])) for c in columns if c.get("tip")]
    if not items:
        return ""
    return "<details class=cols><summary>Columns</summary><ul>%s</ul></details>" % "".join(items)


def table(columns, rows, sort=None, page=200):
    """An inline table: data embedded in the page."""
    _tid[0] += 1
    i = _tid[0]
    d = dict(columns=columns, rows=rows, pageSize=page)
    if sort:
        d["sort"] = sort
    return (columns_note(columns) + '<div id="t%d"></div><script type="application/json" id="d%d">%s</script>'
            '<script>tableFromScript("t%d","d%d")</script>' % (i, i, jdump(d), i, i))


def col(title, type="text", tip=None):
    c = dict(title=title, type=type)
    if tip:
        c["tip"] = tip
    return c


def page(path, title, body, depth=0, first=False):
    up = "../" * depth
    nav = " ".join('<a href="%s%s">%s</a>' % (up, h, E(t)) for h, t in NAV)
    nav1 = " ".join('<a href="%s%s">%s</a>' % (up, h, E(t)) for h, t in NAV1)
    doc = ("<!doctype html><html lang=en><head><meta charset=utf-8>"
           "<meta name=viewport content='width=device-width,initial-scale=1'>"
           "<title>%s — Atlas names study</title><link rel=stylesheet href='%sstyle.css'>"
           "<script src='%stable.js'></script></head><body><nav><b>Atlas names study</b> &nbsp; %s"
           "<div>First instrument (patterns): %s</div></nav>"
           "<h1>%s</h1>%s%s</body></html>") % (E(title), up, up, nav, nav1, E(title), (FIRST % up) if first else "", body)
    full = os.path.join(SITE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(doc)


def tlink(tid, depth=0, at=None, label=None):
    """A link to the text viewer. With a position it opens on the pattern hits and scrolls there."""
    return '<a href="%stext.html?id=%d%s">%s</a>' % (
        "../" * depth, tid, "&show=patterns&at=%d" % at if at is not None else "", label or ("#%d" % tid))


def ctx(text, s, e, n=70):
    left = text[max(0, s - n):s].replace("\n", " ⏎ ")
    right = text[e:e + n].replace("\n", " ⏎ ")
    return "%s<mark>%s</mark>%s" % (E(left), E(text[s:e].replace("\n", " ⏎ ")), E(right))


def pct(a, b):
    return round(100.0 * a / b, 1) if b else ""


def band(x):
    """Display band of a score: used only for colour and for the summary rows."""
    return "hi" if x >= 0.8 else "mid" if x >= 0.5 else "lo" if x > 0 else "none"


def fnum(x, nd=2):
    return "" if x is None else round(x, nd)


def who_quotes(xdir, length, parts=2):
    """The quotes the second instrument read, as download files: one line per text, the last answer
    that has quotes. Returns the file names and the share of characters covered."""
    src = os.path.join(HERE, "..", "who", "quotes", "corpus", "anthropic__claude-sonnet-5.5.jsonl")
    last = {}
    for line in open(src, encoding="utf-8"):
        r = json.loads(line)
        if r.get("quotes"):
            last[r["text"]] = [[x["start"], x["end"], x["quote"]] for x in r["quotes"]]
    ids = sorted(last)
    covered = sum(e - s for t in ids for s, e, _ in last[t]); total = sum(length[t] for t in ids)
    names, step = [], (len(ids) + parts - 1) // parts
    for k in range(parts):
        name = "who_quotes_%d.jsonl.gz" % (k + 1)
        with gzip.GzipFile(os.path.join(xdir, name), "wb", 9, mtime=0) as f:
            for t in ids[k * step:(k + 1) * step]:
                f.write((json.dumps({"text": t, "quotes": [{"start": a, "end": b, "quote": c} for a, b, c in last[t]]},
                                    ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"))
        names.append(name)
    return dict(files=names, texts=len(ids), quotes=sum(len(v) for v in last.values()), coverage=pct(covered, total))


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
    for d in ("pattern", "model", "m", "n", "x", "pn", "l", "w"):
        shutil.rmtree(os.path.join(SITE, d), ignore_errors=True)
    for f in ("uncovered.html", "names_candidates.html"):
        if os.path.exists(os.path.join(SITE, f)):
            os.remove(os.path.join(SITE, f))
    open(os.path.join(SITE, "style.css"), "w").write(CSS)
    open(os.path.join(SITE, "table.js"), "w").write(JS)
    open(os.path.join(SITE, "sha1.js"), "w").write(SHA1_JS)

    texts = {}
    def text_of(tid):
        if tid not in texts:
            texts[tid] = snap.execute("SELECT text FROM texts WHERE id=?", (tid,)).fetchone()[0]
        return texts[tid]

    # text_id -> (id, model, length, n_hits, n_names, best, expected, n_statements, n_anti, flag, tagged)
    cov = {r[0]: r for r in q("SELECT text_id, model, length, n_hits, n_names, best, expected, n_statements, "
                              "n_anti, flag, tagged, best_body, best_title_only, n_names_80, n_place_self, "
                              "n_process, n_species, kind FROM text_cov")}
    models = sorted(set(r[1] for r in cov.values()))
    midx = {m: i for i, m in enumerate(models)}
    pats = q("SELECT id, version, round, added, yields, family, regex, flags, stop, max_words, origin_text, "
             "origin_excerpt, what, note, status, retired_reason, mask, reject, remark, min_occ, max_df, "
             "precision, n_read FROM patterns ORDER BY rowid")
    active = [p for p in pats if p[14] == "active"]
    retired = [p for p in pats if p[14] == "retired"]
    prec = {p[0]: p[21] for p in active}
    ev = {r[0]: r for r in q("SELECT * FROM pattern_eval")}
    pstat = {r[0]: r for r in q("SELECT pattern_id, count(*), count(distinct text_id), count(distinct norm) "
                                "FROM mentions GROUP BY 1")}
    pmodels = Counter(r[0] for r in q("SELECT pattern_id FROM pattern_model"))
    readings = q("SELECT round, text_id, basis, saw, note FROM readings ORDER BY round, rowid")
    read_round = {}
    for r in readings:
        read_round.setdefault(r[1], r[0])
    okn = stats["texts"] - stats["flagged"]

    # ---- names and roles: the second instrument (data/roles.db, roles/checks.json)
    rdb = sqlite3.connect("file:%s?mode=ro" % os.path.join(HERE, "data", "roles.db"), uri=True)
    checks = json.load(open(os.path.join(HERE, "roles", "checks.json")))
    rrun = json.loads(dict(rdb.execute("SELECT key, value FROM run"))["stats"])
    counted = {tid for tid, r in cov.items() if not r[9]}
    SRC = {"quote": 1, "line": 2}
    tl = defaultdict(dict)            # text -> string -> [labels, source bits]
    nlab, src_n = Counter(), Counter()
    for tid, nrm, src, k in rdb.execute("SELECT text_id, norm, source, count(*) FROM labels GROUP BY 1, 2, 3"):
        d = tl[tid].setdefault(nrm, [0, 0])
        d[0] += k; d[1] |= SRC[src]
        if tid in counted:
            nlab[tid] += k; src_n[src] += k
    shown = {}                        # string -> as most often written
    best_form = {}
    for nrm, lab, k in rdb.execute("SELECT norm, label, count(*) FROM labels GROUP BY 1, 2"):
        if k > best_form.get(nrm, 0):
            best_form[nrm] = k; shown[nrm] = lab
    del best_form
    rn = {}                           # string -> [texts, labels, Counter of models, texts from quotes, texts from lines]
    for tid in counted:
        m = cov[tid][1]
        for nrm, (k, bits) in tl.get(tid, {}).items():
            g = rn.get(nrm)
            if g is None:
                g = rn[nrm] = [0, 0, Counter(), 0, 0]
            g[0] += 1; g[1] += k; g[2][m] += 1; g[3] += bits & 1; g[4] += (bits >> 1) & 1
    psc = {(r[0], r[1]): r[2] for r in q("SELECT text_id, norm, score FROM text_names")}
    pbest = dict(q("SELECT norm, best FROM names"))
    per_text = sorted(nlab[t] for t in counted if nlab[t])
    rs = dict(labels=sum(nlab.values()), texts=len(per_text), without=len(counted) - len(per_text),
              strings=len(rn), strings2=sum(1 for g in rn.values() if g[0] >= 2),
              median=int(statistics.median(per_text)), quote=src_n["quote"], line=src_n["line"],
              dropped=rrun["dropped"], all_labels=rrun["labels"])
    vb = {v["code"]: v for v in checks["verdicts"]}
    xdir = os.path.join(SITE, "export")
    os.makedirs(xdir, exist_ok=True)
    wq = who_quotes(xdir, {tid: r[2] for tid, r in cov.items()})
    nlink = lambda nrm, up="": '<a href="%sname.html?n=%s">%s</a>' % (up, E(nrm, quote=True).replace(" ", "%20").replace("|", "%7C"), E(shown.get(nrm, nrm)))

    # ------------------------------------------------------------------ index
    rrows = []
    for rnd, date, note, st in q("SELECT round, date, note, stats FROM rounds ORDER BY round"):
        st = json.loads(st)
        o = st["texts"] - st.get("flagged", 0)
        rrows.append([rnd, date, st["patterns"], st["mentions"], st.get("verdicts", ""), st["covered"],
                      pct(st["covered"], o), st.get("best_none", st.get("nothing", "")), note])
    first_intro = """
<p>The first instrument of the study: regular expressions written by reading. A pattern is written
after a form of naming is seen in a text, run over every text, and judged by reading a sample of
what it caught. This page shows the words used, where the patterns stand, the rounds in which they
were written, and every pattern.</p>
<h2>Words used for the first instrument</h2>
<ul>
<li><b>Pattern</b>: a regular expression written after seeing a form of naming in a text. Each
pattern page shows the passage it was first seen in.</li>
<li><b>Hit</b>: one place in one text where a pattern matched.</li>
<li><b>Name</b>: the captured string with its article, markup and edge punctuation removed,
compared without regard to case. A name may be one word or several. Names here include names
of kinds, of single beings, of places and of things, and descriptions that stand where a name
would ("those who …"). A word for a role or function that designates a kind ("the grazers", "the
tenders") counts as a name; an ordinary species word ("the crickets", "moss") does not.</li>
<li><b>Precision of a pattern</b>: of the hits of the pattern that were read by eye, the share
that were names. It is a number between 0 and 1, shown with the number of hits read. It is empty
until %(minread)d hits have been read.</li>
<li><b>Score of a name in a text</b>: the highest precision among the patterns that caught it
there. A string caught only by a pattern of precision 0.2 has score 0.2: one such string in five
is a name.</li>
<li><b>Best score of a text</b>: the highest score among its names; 0 when no pattern caught
anything. Texts with a low best score are where new forms of naming are looked for, and are the
candidates for having no name at all.</li>
<li><b>Title only</b>: a name that was caught in a title line (a heading, a bold line, the head
of a list item) and occurs nowhere else in the text. The text put it over a section and never
used it again: it may be a title given to one inhabitant in place of a name, or the title of a
section. It is kept apart from names the text goes on using; a text's best score is given for
both ("in the body" and "title only") so that neither is lost in the other.</li>
<li><b>Expected</b>: a sum of scores. "Expected texts" of a name is the sum of its scores over the
texts it was caught in: about how many of those texts really use it as a name.</li>
<li><b>Also in the place text</b>: the same string occurs in the description of the place that
the creature text was written for. This says where a name first appeared; it does not say
whether it names a place or a being.</li>
<li><b>Flagged text</b>: a text left out of the counts. Either the corpus taggers marked it as
broken, a refusal or off-topic, or it is empty, or it failed a word check made here (see
<a href="flagged.html">Flagged texts</a>).</li>
</ul>

<h2>Where it stands</h2>
<table class=kv>
<tr><td>Patterns</td><td>%(np)d in use (%(n80)d name patterns with precision 0.8 or more), %(nr)d earlier versions kept</td></tr>
<tr><td>Hits</td><td>%(mentions)d</td></tr>
<tr><td>Hits read by eye and judged</td><td>%(verdicts)d</td></tr>
<tr><td>Distinct strings caught</td><td>%(dn)d, of which %(d80)d reach a score of 0.8 in at least one text</td></tr>
<tr><td>Texts counted</td><td>%(ok)d (%(flagged)d flagged and left out)</td></tr>
<tr><td>Best score 0.8 or more</td><td>%(b80)d (%(p80)s%%)</td></tr>
<tr><td>Best score 0.5 to 0.8</td><td>%(b50)d (%(p50)s%%)</td></tr>
<tr><td>Best score under 0.5</td><td>%(blo)d (%(plo)s%%)</td></tr>
<tr><td>Nothing caught</td><td>%(bno)d (%(pno)s%%)</td></tr>
<tr><td>Best score in the body under 0.5</td><td>%(bu)d, of which %(tn)d have a title-only designation</td></tr>
<tr><td>Texts that say there is no name</td><td>%(anti)d (see <a href="no_names.html">Texts without names</a>)</td></tr>
<tr><td>Texts that say the place is the inhabitant</td><td>%(pself)d (see <a href="kinds.html">Kinds of answer</a>)</td></tr>
<tr><td>Texts that use the word "name"</td><td>%(talk)d</td></tr>
</table>
<p class=small>The four rows of best score are a way to read one number; the cuts at 0.8 and 0.5
are for display. Any table on this site can be filtered at another cut.</p>

<h2>Rounds</h2>
<p>A round is: read texts, write or correct patterns, run them over every text, read a sample of
each pattern's hits.</p>
%(rounds)s
<p class=small>Until round 3 patterns were sorted into two classes, "strict" (precision 0.8 or more)
and "wide". "Texts with a name at 0.8 or more" is the same count as "covered" was then.</p>

<h2>Known gaps</h2>
<ul>
<li>A high best score does not mean every name in the text was found, only that one was. The
<a href="recall.html">recall checks</a> measure how many are found.</li>
<li>Precision is measured on about 30 read hits per pattern. A precision of 1.0 means 30 of 30,
not certainty.</li>
<li>Names of places and of beings are not told apart.</li>
<li>A name longer than the pattern expects is cut short: a capitalised run ends at the first
lower-case word that is not one of a short list of joining words ("of", "in", "who", "that" …).</li>
<li>Singular and plural forms of one name are counted as two names ("Weaver", "Weavers").</li>
<li>The verdicts were given by one reader, the model that wrote the patterns; a second reader's
blind re-judging of 200 hits is on the <a href="recall.html">recall page</a>.</li>
<li>All texts are treated as English.</li>
</ul>

""" % dict(minread=20, np=len(active),
           n80=stats["patterns_at_80"], nr=len(retired), mentions=stats["mentions"],
           verdicts=stats["verdicts"], dn=stats["distinct_strings"], d80=stats["distinct_at_80"],
           ok=okn, flagged=stats["flagged"],
           b80=stats["best_80"], p80=pct(stats["best_80"], okn), b50=stats["best_50_80"],
           p50=pct(stats["best_50_80"], okn), blo=stats["best_under_50"], plo=pct(stats["best_under_50"], okn),
           bno=stats["best_none"], pno=pct(stats["best_none"], okn), anti=stats["anti_texts"],
           bu=stats["body_under_50"], tn=stats["titled_any_not_named"], pself=stats["place_self_texts"],
           talk=stats["name_talk_texts"],
           rounds=table([col("round", "num"), col("date"), col("patterns", "num"), col("hits", "num"),
                         col("verdicts", "num"), col("texts with a name at 0.8 or more", "num"),
                         col("% of texts", "num"), col("texts with nothing caught", "num"),
                         col("what was done")], rrows, sort=[0, 1]))
    body = ("""
<p>This site shows a study of the names and roles that language models gave to the inhabitants
they wrote into the <a href="https://atlas.animalabs.ai">Atlas</a>. Each creature text belongs to
a place text that the same model had written before it. No text has a name field; the names are
inside the prose, in many forms.</p>
<p>The study has used two instruments. The first is a set of regular expressions (patterns)
written by reading; every pattern, what it catches and what it misses are kept under "First
instrument". The second is a small language model that was given, line by line, the sentences in
which each text says who or what lives there, and was asked to write out every name and every role
exactly as written; each answer was then checked by script against its line. The second finds
more: of %(vb_n)d names of beings that were judged by eye while the patterns were written, it holds
%(vb_both)d. The main pages of this site show the result of the second instrument, and
<a href="method.html">Method and checks</a> says how it was made, what it was measured against and
what it is known to miss.</p>
<p>Names and roles are not kept apart. A sentence such as "The Flux Dwellers are the city's
gardeners, architects, and caretakers" gives four rows. Nothing is filtered: general words
(inhabitants, people, creatures) are in the set and lead it by count.</p>
@@FORM@@
<h2>What was read</h2>
<table class=kv>
<tr><td>Atlas release</td><td>r%(rev)s, cut %(cut)s</td></tr>
<tr><td>Release digest</td><td><code>%(digest)s</code></td></tr>
<tr><td>Texts</td><td>%(texts)d creature texts by %(nmodels)d models: every creature text of the release, as written</td></tr>
<tr><td>Content hash</td><td><code>%(content)s</code> (sha256 over the ids and texts, in id order)</td></tr>
<tr><td>Built</td><td>%(built)s</td></tr>
</table>

<h2>Words used on this site</h2>
<ul>
<li><b>Label</b>: one name or role that a text gives an inhabitant, at one position in the text,
exactly as written there.</li>
<li><b>String</b>: a label in lower case with markup and a leading article removed. Labels are
counted by string. Singular and plural are two strings ("keeper", "keepers"), and so are compound
forms ("memory-keepers").</li>
<li><b>From a quote, from a line</b>: where the label was found. A quote is a sentence in which the
text says who or what lives there, collected beforehand for every text. A line is a heading, or a
sentence outside every quote in which a pattern of the first instrument had caught something.</li>
<li><b>Caught by a pattern</b>: the same string was also caught in the same text by the first
instrument; the number is its score there (see <a href="patterns.html">Patterns</a>).</li>
<li><b>Flagged text</b>: a text left out of the counts (see <a href="flagged.html">Flagged texts</a>).</li>
</ul>

<h2>Where it stands</h2>
<table class=kv>
<tr><td>Texts counted</td><td>%(ok)d (%(flagged)d flagged and left out)</td></tr>
<tr><td>Labels</td><td>%(labels)d, of which %(quote)d from quotes and %(line)d from lines</td></tr>
<tr><td>Texts with at least one label</td><td>%(rtexts)d (%(without)d counted texts have none)</td></tr>
<tr><td>Labels per text</td><td>median %(median)d</td></tr>
<tr><td>Distinct strings</td><td>%(strings)d, of which %(strings2)d occur in two or more texts</td></tr>
<tr><td>Answers dropped by the check</td><td>%(dropped)d labels that were not found, as written, in the line they were given for</td></tr>
</table>

<h2>Rebuilding</h2>
<pre>./snapshot.sh %(rev)s              # copy the creature texts of release r%(rev)s
python3 extract.py --rev %(rev)s   # first instrument: run patterns.py over every text, write data/names.db
python3 roles/batch_roles.py submit quotes; python3 roles/batch_roles.py submit items   # second instrument
python3 roles/batch_roles.py collect quotes; python3 roles/batch_roles.py collect items
python3 roles/build_roles.py       # write data/roles.db
python3 roles/check.py             # write roles/checks.json
python3 build_site.py --rev %(rev)s</pre>
<p class=small>snapshot.sh needs access to the machine that holds the releases. The same texts
are public through the Atlas API and are exported to the atlas-texts repository. The second
instrument reads the quotes of the companion study "who lives there"; they can be downloaded from
<a href="export.html">Data export</a>.</p>
""" % dict(rev=a.rev, cut=E(run.get("release_cut_at", "")[:19]), digest=E(run.get("release_corpus_digest", "")),
           texts=stats["texts"], nmodels=len(models), content=run["content_sha256"], built=run["built_at"],
           ok=okn, flagged=stats["flagged"], vb_n=vb["b"]["n"], vb_both=vb["b"]["both"],
           labels=rs["labels"], quote=rs["quote"], line=rs["line"], rtexts=rs["texts"], without=rs["without"],
           median=rs["median"], strings=rs["strings"], strings2=rs["strings2"], dropped=rs["dropped"])).replace("@@FORM@@", FORM)
    page("index.html", "Names and roles in the Atlas creature texts", body)

    # ----------------------------------------------------------------- method
    prompt_q = open(os.path.join(HERE, "roles", "prompt_v2.md")).read().strip()
    prompt_l = open(os.path.join(HERE, "roles", "prompt_items_v1.md")).read().strip()
    vrows = [[v["verdict"], v["n"], v["first"], pct(v["first"], v["n"]), v["both"], pct(v["both"], v["n"])]
             for v in checks["verdicts"]]
    wrows = [[w["word"], w["texts"], w["in_a_label"], pct(w["in_a_label"], w["texts"]), w["texts"] - w["in_a_label"]]
             for w in checks["words"]]
    pl = checks["pilot"]
    page("method.html", "Method and checks", """
<p>The names and roles on this site were collected by the second instrument of the study. This page
says how, what the result was measured against, and what it is known to miss. The first instrument,
the patterns, has its own pages (second row of the menu).</p>

<h2>How the labels were collected</h2>
<ol>
<li><b>Quotes.</b> For every text, the sentences in which the text itself says who or what lives
there had been collected beforehand by a larger model, for the companion study "who lives there".
Every stored quote is the text's own stretch at a recorded position. The quotes cover %(qcov)s%% of
the characters of the texts that have them.</li>
<li><b>First pass, over the quotes.</b> The quotes of one text are numbered and given to a small
model (<code>openai/gpt-6-luna</code>), one request per text, with this request and nothing else:
<blockquote>%(pq)s</blockquote></li>
<li><b>Second pass, over what the quotes did not cover.</b> Headings (found by script), and
sentences outside every quote in which a pattern of the first instrument had caught something, are
numbered and given to the same model, 25 lines per request:
<blockquote>%(plq)s</blockquote>
Of %(ls)d such lines in the %(vt)d texts used for the checks below, %(ll)d were given a label.</li>
<li><b>The check.</b> A label is kept only if it is found, as written, inside the line it was given
for; its position in the text is recorded from that. %(dropped)d labels of %(all)d were dropped by
this check.</li>
</ol>
<p>Nothing else is done to the answers: no list of words is excluded and no score is given.</p>

<h2>Measured against the verdicts of the first instrument</h2>
<p>While the patterns were written, %(nv)d of their hits were read in context and judged
(<a href="patterns.html">Patterns</a>). For each judged hit the table says whether the first pass,
or either pass, gave a label that equals the judged string, contains it, or is contained in
it.</p>%(vt_table)s
<p class=small>"Not a name" in those verdicts included ordinary species words ("the crickets", "moss"),
which count as labels here, so the last row is not a count of errors. The verdicts were made on
pattern hits: they cannot show a name that no pattern caught. The patterns were also used to choose
the lines of the second pass, which favours this comparison.</p>
<p>The patterns now serve the result in one way only: they point to lines outside the quotes. What
they caught is not added to the set.</p>

<h2>Twelve words for those who look after something</h2>
<p>A check from the other side, without the patterns' verdicts: in the same %(vt)d texts, the
texts in which the word occurs anywhere (singular or plural), and how many of them have a label
that holds the word.</p>%(w_table)s
<p class=small>The texts without such a label include uses that are rightly absent: the adjective
("tender shoots"), comparisons ("like a gardener") and denials ("she is not a keeper of anything").
The rest are roles in sentences that neither the quotes nor a pattern reached ("A piston keeper may
spend an entire shift ..."). How the texts without a label divide between the two has not been counted.</p>

<h2>Ten texts read whole</h2>
<p>Before any request, %(pt)d texts drawn at random were read whole and every name and role marked
by hand: %(pm)d marks. The first pass found %(pf)d of them. Of the %(pmiss)d not found, %(pd)d were
denials ("not plants"), which are not collected.</p>

<h2>Known gaps</h2>
<ul>
<li>A role in a sentence that the quotes did not take and no pattern touched is not seen.</li>
<li>Lines longer than 700 characters were not sent in the second pass.</li>
<li>Denials ("they are not guards") and comparisons ("like a gardener") are not collected.</li>
<li>Singular and plural, and compound forms ("moss-keeper"), are separate strings.</li>
<li>Long descriptive phrases are in the set as labels; they rarely recur.</li>
<li>General words (inhabitants, creatures) and ordinary species words are in the set.</li>
<li>Names of places are mostly absent, not marked: of %(pn)d judged place names the two passes hold %(pb)d.</li>
<li>The quotes, the labels and the hand marks were all made by language models; no part was read
whole by a person.</li>
</ul>
""" % dict(qcov=wq["coverage"], pq=E(prompt_q), plq=E(prompt_l), ls=checks["lines_sent"], ll=checks["lines_with_a_label"],
           vt=checks["verdict_texts"], dropped=rs["dropped"], all=rs["all_labels"] + rs["dropped"],
           nv=sum(v["n"] for v in checks["verdicts"]),
           vt_table=table([col("verdict when the patterns were written"), col("judged hits", "num"),
                           col("held by the first pass", "num"), col("%", "num"),
                           col("held by either pass", "num"), col("%", "num")], vrows),
           w_table=table([col("word"), col("texts with the word", "num"), col("with a label holding it", "num"),
                          col("%", "num"), col("without", "num")], wrows),
           pt=pl["texts"], pm=pl["marked"], pf=pl["found"], pmiss=pl["marked"] - pl["found"], pd=pl["missed_denials"],
           pn=vb["p"]["n"], pb=vb["p"]["both"]))

    # --------------------------------------------------------------- patterns
    prow = []
    for p in active:
        st = pstat.get(p[0], (p[0], 0, 0, 0))
        e = ev.get(p[0])
        prow.append(['<a href="pattern/%s.html">%s</a>' % (p[0], p[0]), p[5], p[4], p[1], p[2], st[1], st[2],
                     pmodels.get(p[0], 0), st[3], e[1] if e else 0, fnum(p[21]),
                     fnum(e[2] / float(e[1])) if e and e[1] >= 20 else "", p[12]])
    rrow = [[p[0], p[1], p[2], p[15] or "", p[18] or ""] for p in retired]
    page("patterns.html", "Patterns", first_intro + """
<h2>Every pattern in use</h2>
<p>Click a pattern for its regular expression, the passage it was first
seen in, a sample of its hits, the hits that were read and judged, and its counts by model.</p>
%s
<h2>Earlier versions</h2>
<p>A pattern that is changed keeps its name and gets a new version. The earlier version stays
here with the reason it was replaced and the sample that showed the problem.</p>
%s""" % (
        table([col("pattern", "html"), col("form"), col("yields", "text", "name: the capture is a name candidate; statement: the hit is a sentence about naming"),
               col("v", "num"), col("round", "num"), col("hits", "num"), col("texts", "num", "texts with at least one hit"),
               col("models", "num", "models with at least one hit"), col("distinct", "num", "distinct captured strings"),
               col("read", "num", "hits read and judged by eye"),
               col("precision", "num", "share of read hits judged to be a name of a being, place or thing (for statement patterns: a statement about the inhabitants' names)"),
               col("beings", "num", "share of read hits judged to be the name of a being or kind"),
               col("what it catches")], prow, sort=[10, -1], page=60),
        table([col("pattern"), col("v", "num"), col("round", "num"), col("why it was replaced"),
               col("sample that showed it")], rrow)), first=True)

    labels = defaultdict(list)
    for r in q("SELECT text_id, pattern_id, start, end, surface, verdict, round FROM labels"):
        labels[r[1]].append(r)
    live = defaultdict(list)
    for tid, pid, s, e in q("SELECT text_id, pattern_id, start, end FROM mentions WHERE pattern_id IN "
                            "(SELECT DISTINCT pattern_id FROM labels)"):
        live[(pid, tid)].append((s, e))
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
            still = any(a < e and b > s for a, b in live.get((pid, t), ()))
            lrows.append([tlink(t, 1, s), cov[t][1].split("/")[-1], VERDICTS.get(v, v), rd,
                          "yes" if still else "no", ctx(text_of(t), s, e)])
        mrows = [['<a href="../model/%s.html">%s</a>' % (slug(m), E(m)), n, nt, mtexts[m], pct(nt, mtexts[m])]
                 for m, n, nt in q("SELECT model, n_mentions, n_texts FROM pattern_model WHERE pattern_id=?", pid)]
        trows = [[n, c, ct] for n, c, ct in q(
            "SELECT norm, count(*), count(distinct text_id) FROM mentions WHERE pattern_id=? AND norm!='' "
            "GROUP BY 1 ORDER BY 3 DESC LIMIT 300", pid)]
        e = ev.get(pid)
        evline = "<tr><td>Read by eye</td><td>nothing yet</td></tr>"
        if e:
            evline = ("<tr><td>Read by eye</td><td>%d hits that the pattern still matches: %d beings, %d places, "
                      "%d things, %d statements, %d not names. %d more were in broken texts and are not counted. "
                      "%d earlier verdicts no longer apply because the pattern stopped matching there "
                      "(%d of those were not names).</td></tr>"
                      % (e[1], e[2], e[3], e[4], e[5], e[6], e[7], e[8], e[9]))
        hrows = "".join("<h3>version %d (round %d)</h3><p>%s</p><p class=small>Sample: %s</p><div class=rx>%s</div>"
                        % (h[1], h[2], E(h[15] or ""), E(h[18] or ""), E(h[6])) for h in hist.get(pid, ()))
        cond = "; ".join(x for x in [
            "flags: " + p[7] if p[7] else "", "stoplist: " + p[8] if p[8] else "",
            "does not look inside: " + p[16] if p[16] else "",
            "drops captures matching: " + p[17] if p[17] else "",
            "at most %d words" % p[9] if p[9] else "",
            "the captured string must occur at least %d times in the text" % p[19] if p[19] else "",
            "a single word is dropped if it occurs in more than %d%% of all texts" % round(100 * p[20]) if p[20] else ""] if x) or "none"
        body = """
<p>%s</p>%s
<table class=kv>
<tr><td>Precision</td><td><b>%s</b>%s</td></tr>
%s
<tr><td>Form</td><td>%s</td></tr>
<tr><td>Version</td><td>%d, written in round %d (%s)</td></tr>
<tr><td>Hits</td><td>%d in %d texts by %d models; %d distinct strings</td></tr>
<tr><td>Conditions</td><td>%s</td></tr>
</table>
<h2>First seen in</h2>
<blockquote>%s</blockquote><p class=small>text %s · <a href="%s">in the Atlas</a></p>
<h2>Regular expression</h2><div class=rx>%s</div>
<h2>Hits that were read</h2>
<p class=small>Seeded random samples, read in context and judged.</p>%s
<h2>A sample of hits</h2>
<p class=small>300 hits drawn at random (fixed seed); not judged.</p>%s
<h2>By model</h2>%s
<h2>Most frequent captures</h2>%s
%s""" % (
            E(p[12]), ("<p><b>Weakness:</b> %s</p>" % E(p[13])) if p[13] else "",
            fnum(p[21]) if p[21] is not None else "not measured yet",
            (" &nbsp; " + E(p[18])) if p[18] else "", evline, E(p[5]), p[1], p[2], p[3],
            st[1], st[2], pmodels.get(pid, 0), st[3], E(cond),
            E(p[11]), tlink(p[10], 1), ATLAS % p[10], E(p[6]),
            table([col("text", "html"), col("model"), col("verdict"), col("round", "num"),
                   col("still matched", "text", "whether the current version of the pattern still matches at this place"),
                   col("in context", "html")], lrows) if lrows else "<p>None yet.</p>",
            table([col("text", "html"), col("model"), col("captured"), col("in context", "html")], srows, page=100),
            table([col("model", "html"), col("hits", "num"), col("texts with a hit", "num"),
                   col("texts of the model", "num"), col("% of texts", "num")], mrows, sort=[4, -1], page=130),
            table([col("captured string"), col("hits", "num"), col("texts", "num")], trows, page=100),
            ("<h2>Earlier versions</h2>" + hrows) if hrows else "")
        page("pattern/%s.html" % pid, "Pattern: " + pid, body, 1, first=True)

    # ----------------------------------------------------------------- models
    per = defaultdict(lambda: dict(hi=0, mid=0, lo=0, none=0, flag=0, anti=0, talk=0, exp=0.0, anti_lo=0,
                                   body_lo=0, titled=0))
    for r in cov.values():
        d = per[r[1]]
        if r[9]:
            d["flag"] += 1; continue
        d[band(r[5])] += 1
        if r[11] < 0.5:
            d["body_lo"] += 1
            if r[12] > 0:
                d["titled"] += 1
        d["exp"] += r[6]
        if r[8]:
            d["anti"] += 1
            if r[5] < 0.5:
                d["anti_lo"] += 1
        if r[7]:
            d["talk"] += 1
    rm = defaultdict(lambda: dict(texts=0, labels=0, strings=0))
    for tid in counted:
        d = rm[cov[tid][1]]
        d["texts"] += nlab[tid] > 0; d["labels"] += nlab[tid]
    mstr = defaultdict(list)          # model -> [(texts of the model, string)]
    for nrm, g in rn.items():
        for m, c in g[2].items():
            rm[m]["strings"] += 1; mstr[m].append((c, nrm))
    mrows, nnrows = [], []
    for m in models:
        d = per[m]
        n = d["hi"] + d["mid"] + d["lo"] + d["none"]
        link = '<a href="model/%s.html">%s</a>' % (slug(m), E(m))
        mrows.append([link, n, d["flag"], rm[m]["texts"], pct(rm[m]["texts"], n), round(rm[m]["labels"] / n, 1) if n else "",
                      rm[m]["strings"], d["hi"], pct(d["hi"], n), d["mid"], d["lo"], d["none"],
                      d["anti"], d["talk"], round(d["exp"] / n, 2) if n else ""])
        nnrows.append([link, n, d["body_lo"], pct(d["body_lo"], n), d["titled"], d["none"], pct(d["none"], n),
                       d["anti"], pct(d["anti"], n), d["anti_lo"]])
    page("models.html", "Models", """
<p>One row per model. The first columns count the names and roles; the columns that begin with
"patterns" are from the first instrument, where texts are split by their best pattern score
(see <a href="patterns.html">Patterns</a> for the words). Click a model for its names and roles
and its texts.</p>%s""" % table(
        [col("model", "html"), col("texts", "num", "texts counted (flagged texts left out)"), col("flagged", "num"),
         col("texts with a label", "num", "counted texts with at least one name or role"), col("%", "num"),
         col("labels per text", "num", "labels in counted texts, divided by the number of counted texts"),
         col("distinct strings", "num", "distinct names and roles in the model's texts"),
         col("patterns: best ≥ 0.8", "num"), col("patterns: % ≥ 0.8", "num"), col("patterns: best 0.5–0.8", "num"),
         col("patterns: best < 0.5", "num"),
         col("patterns: nothing caught", "num"), col("texts that say there is no name", "num", "from a statement pattern of the first instrument"),
         col("texts that use the word 'name'", "num", "from a statement pattern of the first instrument"),
         col("patterns: expected names per text", "num", "sum of scores of all names caught, divided by the number of texts")],
        mrows, sort=[5, -1], page=130))

    tn = defaultdict(list)
    for r in q("SELECT text_id, norm, display, n_mentions, patterns, score, first_pos, occurrences, in_place_text, "
               "in_title, body_occ, body_cased FROM text_names"):
        tn[r[0]].append(r)
    def where(x):
        return "title only" if x[9] and not x[10] else "title and body" if x[9] else "body"
    by_model = defaultdict(list)
    for tid, r in cov.items():
        by_model[r[1]].append(tid)
    pm = defaultdict(list)
    for pid, m, n, nt in q("SELECT pattern_id, model, n_mentions, n_texts FROM pattern_model"):
        pm[m].append((pid, n, nt))
    for m in models:
        agg, trows = {}, []
        for tid in sorted(by_model[m]):
            r = cov[tid]
            names = sorted(tn.get(tid, ()), key=lambda x: (-x[5], x[6]))
            top = [x[2] for x in names if x[5] >= 0.8]
            titled = [x[2] for x in names if where(x) == "title only"]
            trows.append([tlink(tid, 1), r[2], nlab[tid] if not r[9] else sum(v[0] for v in tl.get(tid, {}).values()),
                          ("flagged: " + r[9]) if r[9] else fnum(r[11]), fnum(r[12]),
                          len(top), ", ".join(top[:8]) + (" …" if len(top) > 8 else ""),
                          ", ".join(titled[:6]) + (" …" if len(titled) > 6 else ""),
                          len(names) - len(top), r[8], r[7], read_round.get(tid, "")])
            if r[9]:
                continue
            for x in names:
                g = agg.setdefault(x[1], [x[2], 0.0, 0, 0, 0, set(), 0.0, 0])
                g[1] += x[5]; g[2] += 1; g[4] += x[3]; g[5].update(x[4].split(","))
                if where(x) == "title only":
                    g[7] += 1
                if x[8]:
                    g[3] += 1
                if x[5] >= g[6]:
                    g[6] = x[5]; g[0] = x[2]
        nrows = [['<a href="../name.html?n=%s">%s</a>' % (E(k, quote=True).replace(" ", "%20"), E(g[0])),
                  round(g[1], 2), g[2], fnum(g[6]), g[7], g[3], g[4], ", ".join(sorted(g[5]))] for k, g in agg.items()]
        d = per[m]
        n = d["hi"] + d["mid"] + d["lo"] + d["none"]
        prs = [['<a href="../pattern/%s.html">%s</a>' % (pid, pid), fnum(prec.get(pid)), k, nt, pct(nt, n)]
               for pid, k, nt in pm[m]]
        top = sorted(mstr[m], key=lambda x: (-x[0], x[1]))[:2000]
        srows = [[nlink(nrm, "../"), c, pct(c, n), rn[nrm][0], len(rn[nrm][2])] for c, nrm in top]
        page("model/%s.html" % slug(m), "Model: " + m, """
<table class=kv>
<tr><td>Texts</td><td>%d counted, %d flagged</td></tr>
<tr><td>Names and roles</td><td>%d labels in %d texts; %d distinct strings</td></tr>
<tr><td>By best pattern score</td><td>0.8 or more: %d (%s%%) · 0.5 to 0.8: %d · under 0.5: %d · nothing caught: %d</td></tr>
<tr><td>Texts that say there is no name</td><td>%d</td></tr>
</table>
<h2>Names and roles</h2>
<p class=small>The %d strings found in the most texts of this model.</p>%s
<h2>Texts</h2>%s
<h2>First instrument: patterns in this model's texts</h2>%s
<h2>First instrument: strings caught by patterns</h2>
<p class=small>Every captured string in this model's texts. "Expected texts" is the sum of its scores
over the texts; "in place" counts the texts where the same string is also in the place
description.</p>%s""" % (
            n, d["flag"], rm[m]["labels"], rm[m]["texts"], rm[m]["strings"],
            d["hi"], pct(d["hi"], n), d["mid"], d["lo"], d["none"], d["anti"], len(srows),
            table([col("name or role", "html"), col("texts of this model", "num"), col("% of its texts", "num"),
                   col("texts, all models", "num"), col("models", "num", "models in whose texts it occurs")],
                  srows, sort=[1, -1], page=100),
            table([col("text", "html"), col("length", "num"), col("labels", "num", "names and roles in the text"),
                   col("best pattern score in body"), col("title only", "num", "best score among title-only designations"),
                   col("names ≥ 0.8", "num", "names with a pattern score of 0.8 or more"), col("those names"),
                   col("title-only designations"),
                   col("other strings", "num", "strings caught with a lower score"),
                   col("no-name statements", "num"), col("sentences with 'name'", "num"),
                   col("read in round", "num")], trows, page=100),
            table([col("pattern", "html"), col("precision", "num"), col("hits", "num"), col("texts", "num"),
                   col("% of texts", "num")], prs, sort=[4, -1], page=60),
            table([col("name", "html"), col("expected texts", "num"), col("texts", "num"), col("best score", "num"),
                   col("title only", "num", "texts where it is caught in a title line and occurs nowhere else"),
                   col("in place", "num"), col("hits", "num"), col("patterns")], nrows, sort=[1, -1], page=100)), 1)

    # ------------------------------------------------------------------ names
    os.makedirs(os.path.join(SITE, "n"), exist_ok=True)
    os.makedirs(os.path.join(SITE, "pn"), exist_ok=True)
    allnames = q("SELECT norm, display, n_texts, expected, expected_new, best, n_models, n_mentions, patterns, "
                 "top_models, df, expected_title_only FROM names")
    n80 = dict(q("SELECT norm, count(*) FROM text_names n JOIN text_cov c ON c.text_id=n.text_id "
                 "WHERE n.score>=0.8 AND c.flag='' GROUP BY norm"))
    def nrow(r):
        return ['<a href="name.html?n=%s">%s</a>' % (E(r[0], quote=True).replace(" ", "%20"), E(r[1])),
                r[3], n80.get(r[0], 0), r[2], r[4], r[11], r[6], r[7], len(r[0].split()),
                "" if r[10] is None else round(100 * r[10], 1), r[8], r[9]]
    ncols = [col("name", "html", "the captured string, as most often written; click for the texts"),
             col("expected texts", "num", "sum of the name's scores over the texts it was caught in: about how many of those texts use it as a name, if the patterns' precision is right"),
             col("texts at 0.8", "num", "texts where a pattern of precision 0.8 or more caught it"),
             col("texts", "num", "texts where any pattern caught it"),
             col("expected, not in place text", "num", "the same sum over the texts where the string does not occur in the place description"),
             col("expected, title only", "num", "the same sum over the texts where it is caught in a title line and occurs nowhere else"),
             col("models", "num", "models in whose texts it was caught"), col("hits", "num", "pattern matches, all texts"),
             col("words", "num", "words in the name"),
             col("% of all texts", "num", "for a one-word name: the share of all texts in which the word occurs in any sense. A high share marks ordinary vocabulary."),
             col("patterns", "text", "every pattern that caught it somewhere"),
             col("most expected in", "text", "the models with the largest sums of scores for it")]
    hi = [nrow(r) for r in allnames if r[5] >= 0.8]
    lo = [nrow(r) for r in allnames if r[5] < 0.8]
    with open(os.path.join(SITE, "pn", "names_hi.json"), "w", encoding="utf-8") as f:
        f.write(jdump(dict(columns=ncols, rows=hi, pageSize=200, sort=[1, -1])))
    with open(os.path.join(SITE, "pn", "names_lo.json"), "w", encoding="utf-8") as f:
        f.write(jdump(dict(columns=ncols, rows=lo, pageSize=200, sort=[1, -1])))
    page_cols = columns_note(ncols)
    page("pattern_names.html", "Names caught by patterns",
         """<p>Every distinct string that at least one text uses as a name with a pattern score of 0.8 or
more (%d strings). A click on a name opens its page in the main set. The %d strings that
never reach 0.8 anywhere are kept on a <a href="names_low.html">second page</a> as a pool of
candidates.</p>
<p class=small>Singular and plural are separate rows. Frequent rows near the top include ordinary
capitalised words ("Water", "Body"): the capitalisation patterns take any capitalised word after
"the". The column "%% of all texts" helps to set those aside.</p>
%s<div id=nt></div><script>tableFromUrl("nt","pn/names_hi.json")</script>""" % (len(hi), len(lo), page_cols), first=True)
    page("names_low.html", "Strings with a best pattern score under 0.8",
         """<p>Strings caught only by patterns of lower precision. Most are not names. They are kept so
that names written in forms that the better patterns miss can be found here.</p>
%s<div id=nt></div><script>tableFromUrl("nt","pn/names_lo.json")</script>""" % page_cols, first=True)

    # names and roles: the main table holds the strings found in two or more counted texts
    rcols = [col("name or role", "html", "the string, as most often written; click for the texts"),
             col("texts", "num", "counted texts with at least one label of this string"),
             col("% of texts", "num", "share of all counted texts"),
             col("models", "num", "models in whose texts it occurs"),
             col("labels", "num", "labels of this string, all counted texts"),
             col("words", "num", "words in the string"),
             col("texts, from a quote", "num", "texts where it was found in a quote"),
             col("texts, from a line", "num", "texts where it was found in a heading or in a sentence outside the quotes"),
             col("best pattern score", "num", "the highest score the first instrument gave the same string in any text; empty if no pattern caught it"),
             col("most in", "text", "the three models with the most texts holding it")]
    rrows2 = [[nlink(nrm), g[0], pct(g[0], okn), len(g[2]), g[1], len(nrm.split()), g[3], g[4], fnum(pbest.get(nrm)),
               ", ".join("%s %d" % (m.split("/")[-1], c) for m, c in g[2].most_common(3))]
              for nrm, g in rn.items() if g[0] >= 2]
    with open(os.path.join(SITE, "n", "strings.json"), "w", encoding="utf-8") as f:
        f.write(jdump(dict(columns=rcols, rows=rrows2, pageSize=200, sort=[1, -1])))
    page("names.html", "Names and roles",
         FORM + """<p>Every string that two or more counted texts give an inhabitant as a name or a role
(%d strings). The %d strings found in one text only are not in this table; they open by the form
above and are in the <a href="export.html">export</a>. Click a string to see its texts and its share
in each model.</p>
<p class=small>Nothing is filtered: general words lead the table. Filter the first column
(<code>keeper</code>) to see every form that holds a word; singular, plural and compounds are
separate rows.</p>
%s<div id=nt></div><script>tableFromUrl("nt","n/strings.json")</script>""" % (len(rrows2), rs["strings"] - len(rrows2), columns_note(rcols)))

    buckets = defaultdict(dict)
    for tid in counted:
        mi = midx[cov[tid][1]]
        for nrm, (k, bits) in tl.get(tid, {}).items():
            b = hashlib.sha1(nrm.encode("utf-8")).hexdigest()[:2]
            buckets[b].setdefault(nrm, []).append([tid, mi, k, bits, psc.get((tid, nrm), 0)])
    for b, d in buckets.items():
        with open(os.path.join(SITE, "n", b + ".json"), "w", encoding="utf-8") as f:
            f.write(jdump(d))
    del buckets
    # the same by word: text -> labels that hold the word, in any string
    os.makedirs(os.path.join(SITE, "w"), exist_ok=True)
    WORD = re.compile(r"[^\W_]+(?:'[^\W_]+)*")
    wb = defaultdict(dict)
    for tid in counted:
        mi = midx[cov[tid][1]]; seen = {}
        for nrm, (k, bits) in tl.get(tid, {}).items():
            for wd in set(WORD.findall(nrm)):
                d = seen.get(wd)
                if d is None:
                    seen[wd] = [tid, mi, k, bits, [nrm]]
                else:
                    d[2] += k; d[3] |= bits; d[4].append(nrm)
        for wd, d in seen.items():
            d[4] = "; ".join(sorted(d[4])[:6])
            wb[hashlib.sha1(wd.encode("utf-8")).hexdigest()[:2]].setdefault(wd, []).append(d)
    for b, d in wb.items():
        with open(os.path.join(SITE, "w", b + ".json"), "w", encoding="utf-8") as f:
            f.write(jdump(d))
    del wb
    with open(os.path.join(SITE, "n", "models.json"), "w", encoding="utf-8") as f:
        f.write(jdump(models))
    with open(os.path.join(SITE, "n", "model_counts.json"), "w", encoding="utf-8") as f:
        f.write(jdump([sum(1 for r in cov.values() if r[1] == m and not r[9]) for m in models]))
    page("name.html", "Name or role", FORM + """<div id=head></div><div id=sets></div><div id=nt></div>
<script src="sha1.js"></script><script>
(function () {
  var qs = new URLSearchParams(location.search);
  var parse = function (s) { return (s || '').split('|').map(function (x) { return x.trim().toLowerCase(); }).filter(Boolean); };
  var setA = parse(qs.get('n')), setB = parse(qs.get('vs')), words = qs.get('words') === '1', dir = words ? 'w/' : 'n/';
  var f = document.querySelector('form.sets'); f.a.value = setA.join('|'); f.b.value = setB.join('|'); f.w.checked = words;
  var h1 = document.querySelector('h1');
  if (!setA.length) { h1.textContent = 'Name or role'; return; }
  h1.textContent = setA.join(' | ') + (setB.length ? '  vs  ' + setB.join(' | ') : '') + (words ? '  (as words)' : '');
  var get = function (u) { return fetch(u).then(function (r) { return r.ok ? r.json() : {}; }); };
  var buckets = {};
  var need = setA.concat(setB).map(function (n) { return sha1(n).slice(0, 2); }).filter(function (b, i, a) { return a.indexOf(b) === i; });
  Promise.all([get('n/models.json'), get('n/model_counts.json')].concat(need.map(function (b) {
    return get(dir + b + '.json').then(function (d) { buckets[b] = d; });
  }))).then(function (res) {
    var models = res[0], counts = res[1];
    var rowsOf = function (n) { return (buckets[sha1(n).slice(0, 2)] || {})[n] || []; };
    // per set: text -> one row over its strings
    var gather = function (set) {
      var by = {};
      set.forEach(function (n) { rowsOf(n).forEach(function (r) {
        var cur = by[r[0]];
        if (!cur) cur = by[r[0]] = {text: r[0], model: r[1], labels: 0, bits: 0, score: 0, strings: []};
        cur.labels += r[2]; cur.bits |= r[3];
        if (words) cur.strings.push(r[4]); else { if (r[4] > cur.score) cur.score = r[4]; cur.strings.push(n); }
      }); });
      return by;
    };
    var A = gather(setA), B = setB.length ? gather(setB) : null;
    var ids = Object.keys(A), bi = B ? Object.keys(B) : [];
    var share = function (a, n) { return n ? Math.round(1000 * a / n) / 10 : ''; };
    var total = counts.reduce(function (x, y) { return x + y; }, 0);
    var perModel = models.map(function (m, i) {
      var a = 0, bb = 0;
      ids.forEach(function (t) { if (A[t].model === i) a++; });
      bi.forEach(function (t) { if (B[t].model === i) bb++; });
      var row = [m, counts[i], a, share(a, counts[i])];
      if (B) row = row.concat([bb, share(bb, counts[i])]);
      return row;
    });
    var nm = perModel.filter(function (r) { return r[2]; }).length;
    var head = '<p>' + ids.length + ' of ' + total + ' counted texts (' + share(ids.length, total) + '%), by ' + nm + ' of ' + models.length +
      ' models, give an inhabitant ' + (words ? 'a name or role that holds the word ' : setA.length > 1 ? 'one of the names or roles ' : 'the name or role ') + setA.join(' | ') + '.';
    if (B) head += ' ' + bi.length + ' texts (' + share(bi.length, total) + '%) give ' + setB.join(' | ') + '. ' +
      ids.filter(function (t) { return B[t]; }).length + ' texts give both.';
    document.getElementById('head').innerHTML = head + '</p>';
    var cols = [{title: 'model', type: 'text'}, {title: 'texts', type: 'num', tip: 'counted texts of the model'},
      {title: 'with ' + setA.join('|'), type: 'num', tip: 'texts of the model with a label of any string of the first set'}, {title: '%', type: 'num'}];
    if (B) cols = cols.concat([{title: 'with ' + setB.join('|'), type: 'num'}, {title: '%', type: 'num'}]);
    document.getElementById('sets').innerHTML = '<h2>By model</h2><div id=pm></div><h2>Texts</h2>';
    makeTable(document.getElementById('pm'), {columns: cols, rows: perModel, pageSize: 130, sort: [3, -1]});
    var src = ['', 'quote', 'line', 'quote and line'];
    var trows = ids.map(function (t) { var r = A[t]; return ['<a href="text.html?id=' + t + '&' + (words ? 'markw=' + encodeURIComponent(setA.join('|')) : 'mark=' + encodeURIComponent(r.strings.join('|'))) + '">#' + t + '</a>', models[r.model], r.strings.join(words ? '; ' : ', '), r.labels, src[r.bits], words ? '' : (r.score || '')]; });
    makeTable(document.getElementById('nt'), {columns: [
      {title: 'text', type: 'html'}, {title: 'model', type: 'text'}, {title: 'strings', type: 'text', tip: 'which of the strings the text has (as words: up to six of the strings that hold the word)'},
      {title: 'labels', type: 'num', tip: 'labels of these strings in the text'},
      {title: 'found in', type: 'text', tip: 'a quote (a sentence saying who lives there), a line (a heading or a sentence outside the quotes), or both'},
      {title: 'pattern score', type: 'num', tip: 'the score the first instrument gave the same string in this text; empty if no pattern caught it there'}],
      rows: trows, pageSize: 300, sort: [3, -1]});
  });
})();</script>""")

    # ------------------------------------------------------------------ export
    def dump_csv(name, header, rows, notes):
        import io
        raw = open(os.path.join(xdir, name), "wb") if not name.endswith(".gz") else gzip.GzipFile(os.path.join(xdir, name), "wb", 9, mtime=0)
        with raw, io.TextIOWrapper(raw, encoding="utf-8", newline="") as f:
            w = csv.writer(f); w.writerow(header); w.writerows(rows)
        return "### %s\n\n%s\n\n" % (name, "\n".join("- `%s`: %s" % kv for kv in zip(header, notes)))
    notes = ("# Data export\n\nThe tables behind this site. Rebuilt with the site; same release.\n\n"
             "## Names and roles (second instrument)\n\n")
    with gzip.GzipFile(os.path.join(xdir, "labels.csv.gz"), "wb", 9, mtime=0) as gz:
        import io
        tw = io.TextIOWrapper(gz, encoding="utf-8", newline="")
        w = csv.writer(tw)
        w.writerow(["text_id", "start", "end", "label", "string", "source", "model", "flag"])
        for tid, s0, e0, lab, nrm, src in rdb.execute("SELECT text_id, start, end, label, norm, source FROM labels ORDER BY text_id, start, end"):
            w.writerow([tid, s0, e0, lab, nrm, src, cov[tid][1], cov[tid][9]])
        tw.flush(); tw.detach()
    notes += "### labels.csv.gz\n\nThe whole set, one row per label (gzip). %d rows.\n\n%s\n\n" % (rs["all_labels"], "\n".join("- `%s`: %s" % kv for kv in [
        ("text_id", "Atlas creature id (https://atlas.animalabs.ai/v3/creature/<id>)"),
        ("start, end", "character offsets of the label in the text"),
        ("label", "the name or role exactly as written in the text"),
        ("string", "the label in lower case, markup and a leading article removed; counts on the site are by this column"),
        ("source", "quote: found in a sentence saying who lives there; line: found in a heading or in a sentence outside the quotes"),
        ("model", "writer model"),
        ("flag", "why the text is left out of the counts on the site, empty if counted")]))
    notes += dump_csv("strings.csv.gz",
        ["string", "as_written", "texts", "models", "labels", "texts_from_quote", "texts_from_line", "best_pattern_score"],
        [[nrm, shown.get(nrm, nrm), g[0], len(g[2]), g[1], g[3], g[4], fnum(pbest.get(nrm))]
         for nrm, g in sorted(rn.items(), key=lambda kv: (-kv[1][0], kv[0]))],
        ["the string", "as most often written", "counted texts with a label of this string", "models in whose texts it occurs",
         "labels of this string in counted texts", "texts where it was found in a quote",
         "texts where it was found in a heading or a sentence outside the quotes",
         "highest score the first instrument gave the same string in any text, empty if none"])
    notes += ("### %s\n\nThe quotes the second instrument read: for each text, the sentences in which it says who or what "
              "lives there, collected for the companion study \"who lives there\" (gzip, JSON lines, in %d parts by text id). "
              "%d texts, %d quotes.\n\n- `text`: Atlas creature id\n- `quotes`: list of `start`, `end` (character offsets in the text) "
              "and `quote` (the text's own stretch there)\n\n## First instrument (patterns)\n\n" % (
                  ", ".join(wq["files"]), len(wq["files"]), wq["texts"], wq["quotes"]))
    notes += dump_csv("texts.csv",
        ["text_id", "model", "length", "kind", "best_score_body", "best_score_title_only", "names_at_0_8", "expected_names",
         "no_name_statements", "place_is_inhabitant_statements", "process_statements", "species_words",
         "sentences_with_name", "corpus_status", "flag"],
        [[tid, r[1], r[2], r[17], r[11], r[12], r[13], r[6], r[8], r[14], r[15], r[16], r[7], r[10], r[9]]
         for tid, r in sorted(cov.items())],
        ["Atlas creature id (https://atlas.animalabs.ai/v3/creature/<id>)", "writer model", "characters",
         "kind of answer by the rule on the site page Kinds of answer",
         "highest score among names the text uses outside a title line (0 = none)",
         "highest score among title-only designations (0 = none)",
         "distinct strings with a score of 0.8 or more, used in the body",
         "sum of the scores of all strings caught", "sentences saying there is no name",
         "sentences saying the place itself is the inhabitant",
         "sentences saying the inhabitant is not a creature but a process", "distinct ordinary words for kinds of living things",
         "sentences using the word name", "status recorded by the corpus taggers, empty if none",
         "why the text is left out of counts, empty if counted"])
    notes += dump_csv("text_names.csv",
        ["text_id", "string", "as_written", "score", "patterns", "hits", "first_position", "occurrences",
         "in_place_text", "title_hits", "body_occurrences", "body_occurrences_same_capitals"],
        [[r[0], r[1], r[2], r[5], r[4], r[3], r[6], r[7], r[8], r[9], r[10], r[11]]
         for r in q("SELECT text_id, norm, display, n_mentions, patterns, score, first_pos, occurrences, "
                    "in_place_text, in_title, body_occ, body_cased FROM text_names ORDER BY text_id, first_pos")],
        ["text", "the string, lower-cased, article and markup removed", "as most often written in this text",
         "highest precision among the patterns that caught it here", "patterns that caught it, comma-separated",
         "pattern matches in this text", "character offset of the first hit", "times it occurs in the text, any case",
         "1 if the string occurs in the description of the place", "hits in title lines",
         "occurrences outside title lines (0 with title_hits > 0 = title only)", "of those, with the same capitals"])
    notes += dump_csv("names.csv",
        ["string", "as_written", "texts", "texts_at_0_8", "expected_texts", "expected_not_in_place", "expected_title_only",
         "best_score", "models", "hits", "share_of_all_texts", "patterns"],
        [[r[0], r[1], r[2], n80.get(r[0], 0), r[3], r[4], r[11], r[5], r[6], r[7], r[10], r[8]] for r in allnames],
        ["the string, lower-cased", "as most often written where its score is highest", "texts where any pattern caught it",
         "texts where a pattern of precision 0.8 or more caught it", "sum of scores over texts",
         "the same over texts where the string is not in the place description",
         "the same over texts where it is title only", "highest score in any text", "models", "pattern matches",
         "for one word: share of all texts containing the word in any sense", "patterns that caught it anywhere"])
    notes += dump_csv("patterns.csv",
        ["pattern", "version", "round", "yields", "family", "precision", "hits_read", "regex", "what"],
        [[p[0], p[1], p[2], p[4], p[5], p[21], p[22], p[6], p[12]] for p in active],
        ["pattern id", "version", "round written", "name or statement", "form family",
         "share of names among read hits (empty under 20 read)", "hits read by eye", "regular expression", "what it catches"])
    notes += dump_csv("models.csv",
        ["model", "texts", "flagged", "best_0_8", "best_0_5_0_8", "best_under_0_5", "nothing_caught",
         "no_name_in_body", "of_those_titled", "texts_saying_no_name", "texts_using_word_name", "expected_names_per_text"],
        [[m, per[m]["hi"] + per[m]["mid"] + per[m]["lo"] + per[m]["none"], per[m]["flag"], per[m]["hi"], per[m]["mid"],
          per[m]["lo"], per[m]["none"], per[m]["body_lo"], per[m]["titled"], per[m]["anti"], per[m]["talk"],
          round(per[m]["exp"] / max(1, per[m]["hi"] + per[m]["mid"] + per[m]["lo"] + per[m]["none"]), 3)] for m in models],
        ["model", "counted texts", "flagged texts", "texts with best score 0.8 or more", "0.5 to 0.8", "under 0.5 but something caught",
         "nothing caught", "best score in the body under 0.5", "of those, with a title-only designation",
         "texts with a no-name statement", "texts using the word name", "sum of scores per text"])
    with open(os.path.join(xdir, "README.md"), "w", encoding="utf-8") as f:
        f.write(notes)
    flist = lambda names: "".join('<li><a href="export/%s">%s</a> (%s MB)</li>' % (n, n, round(os.path.getsize(os.path.join(xdir, n)) / 1e6, 1)) for n in names)
    page("export.html", "Data export", "<p>The tables behind this site, with their columns described. "
         "Rebuilt with the site. Second-order questions (shares by model, groups of strings, singular and plural "
         "together) are meant to be asked of these files; the site is for looking and checking.</p>"
         "<h2>Names and roles</h2><ul>%s</ul><h2>The quotes they were read from</h2><ul>%s</ul>"
         "<h2>First instrument (patterns)</h2><ul>%s</ul><pre>%s</pre>" % (
             flist(["labels.csv.gz", "strings.csv.gz"]), flist(wq["files"]),
             flist(["texts.csv", "text_names.csv", "names.csv", "patterns.csv", "models.csv", "README.md"]), E(notes)))

    # ------------------------------------------------------------------ texts
    os.makedirs(os.path.join(SITE, "x"), exist_ok=True)
    xrows = [[tlink(tid), r[1], r[2], nlab[tid], len(tl.get(tid, ())), r[17], fnum(r[11]), fnum(r[12]), r[13], r[6], r[8], r[14], r[15], r[16], r[7],
              r[10] or "none", read_round.get(tid, "")] for tid, r in sorted(cov.items()) if not r[9]]
    xcols = [
            col("text", "html"), col("model"), col("length", "num", "characters"),
            col("labels", "num", "names and roles found in the text"),
            col("distinct strings", "num", "distinct names and roles in the text"),
            col("kind", "text", "first instrument: the kind of answer, by the rule on the Kinds of answer page"),
            col("best score in body", "num", "highest score among names the text uses outside a title line"),
            col("best score, title only", "num", "highest score among title-only designations; empty when there is none"),
            col("names ≥ 0.8", "num", "distinct strings with a score of 0.8 or more, used in the body"),
            col("expected names", "num", "sum of the scores of all strings caught in the text"),
            col("no-name statements", "num", "sentences saying there is no name"),
            col("place is the inhabitant", "num", "sentences saying the place itself is what lives here"),
            col("not a creature but a process", "num", "sentences saying the inhabitant is a process, a condition, a pattern"),
            col("species words", "num", "distinct ordinary words for kinds of living things"),
            col("sentences with 'name'", "num", "sentences that use the word name"),
            col("corpus status", "text", "the status the corpus taggers recorded; many newer texts have none"),
            col("read in round", "num", "the round in which the text was read by eye, if it was")]
    with open(os.path.join(SITE, "x", "texts.json"), "w", encoding="utf-8") as f:
        f.write(jdump(dict(columns=xcols, rows=xrows, pageSize=200, sort=[3, 1])))
    page("texts.html", "Texts",
         """<p>Every counted text (%d) with the number of names and roles found in it, and with what the
first instrument recorded: the kind of answer, the best pattern scores, the statement counts.
Sorted from the fewest labels: the texts at the top are where no name or role was found. Click a
text to read it with its labels marked.</p>%s<div id=xt></div><script>tableFromUrl("xt","x/texts.json")</script>""" % (len(xrows), columns_note(xcols)))


    # ------------------------------------------------------------------ kinds
    KIND_ORDER = ["catalogue", "named", "place itself", "a process", "unnamed, said so", "ordinary biology", "undetermined"]
    KIND_RULE = {
        "catalogue": "three or more names at a score of 0.8 or more, used in the body",
        "named": "one or two such names",
        "place itself": "no such name, and a sentence saying the place is the inhabitant",
        "a process": "no such name, and a sentence saying the inhabitant is not a creature but a process, a condition, a pattern",
        "unnamed, said so": "no such name, and a sentence saying there is no name",
        "ordinary biology": "no such name, no such sentence, and four or more ordinary words for kinds of living things (fish, moss, beetles, goats \u2026)",
        "undetermined": "none of the above: nothing caught that decides it",
    }
    kc = Counter(r[17] for r in cov.values() if not r[9])
    krows = [[k, KIND_RULE[k], kc[k], pct(kc[k], okn)] for k in KIND_ORDER]
    per_kind = defaultdict(Counter)
    for r in cov.values():
        if not r[9]:
            per_kind[r[1]][r[17]] += 1
            if r[14]:
                per_kind[r[1]]["pself_any"] += 1
    kmrows = []
    for m in models:
        c = per_kind[m]; n = sum(c[k] for k in KIND_ORDER)
        kmrows.append(['<a href="model/%s.html">%s</a>' % (slug(m), E(m)), n] + [c[k] for k in KIND_ORDER] +
                      [pct(c["catalogue"] + c["named"], n), pct(c["place itself"], n), c["pself_any"], pct(c["pself_any"], n)])
    page("kinds.html", "Kinds of answer", """
<p>Each text answers the question "who or what lives here" in its own way, and the kinds of answer
are not a scale. A text that says the place itself is the inhabitant has answered; a text that
describes goats and lichens has answered; a text in which nothing was caught may not have. The
name search alone puts all three in one box. This page separates them by a rule over what was
caught in each text. The rule is one choice among several; the signals it reads are stored beside
it (columns of the <a href="texts.html">Texts</a> table and of <code>texts.csv</code>), so another
rule can be applied without re-reading anything.</p>
<p>The rule is applied in the order of the rows: the first row that fits is the kind. A catalogue
can also say the place is alive; it is counted as a catalogue here, and the sentence is counted in
the column "say the place is the inhabitant", which is independent of the kind.</p>
<h2>The rule and the counts</h2>%s
<h2>By model</h2>%s
<p class=small>"undetermined" is where the reading should go next. "ordinary biology" is a weak
signal: a text that coins no name and uses four or more ordinary species words; a long essay
about one unnamed being that mentions birds and moss in passing also lands here.</p>
""" % (table([col("kind"), col("rule"), col("texts", "num"), col("% of counted texts", "num")], krows),
       table([col("model", "html"), col("texts", "num")] + [col(k, "num", KIND_RULE[k]) for k in KIND_ORDER] +
             [col("% catalogue or named", "num"), col("% place itself", "num", "share of texts whose kind is 'place itself'"),
              col("say the place is the inhabitant", "num", "texts with such a sentence, whatever their kind"),
              col("% saying so", "num")], kmrows, sort=[9, -1], page=130)), first=True)

    # --------------------------------------------------------------- no names
    rc = q("SELECT chk, date, pool, text_id, read_chars, name, then_caught, score_now, patterns_now, forms_missed, note FROM recall")
    eye = defaultdict(lambda: dict(texts=set(), noname=set()))
    for r in rc:
        eye[(r[0], r[2])]["texts"].add(r[3])
        if r[5] is None:
            eye[(r[0], r[2])]["noname"].add(r[3])
    eyerows = [[k[0], k[1], len(v["texts"]), len(v["noname"]), pct(len(v["noname"]), len(v["texts"]))]
               for k, v in sorted(eye.items())]
    anti_rows = []
    for tid, s, e, surf in q("SELECT text_id, start, end, surface FROM mentions WHERE pattern_id='anti_name' ORDER BY text_id, start"):
        r = cov[tid]
        if r[9]:
            continue
        anti_rows.append([tlink(tid, 0, s), r[1], fnum(r[5]), surf if len(surf) < 400 else surf[:397] + "…"])
    with open(os.path.join(SITE, "x", "anti.json"), "w", encoding="utf-8") as f:
        f.write(jdump(dict(columns=[col("text", "html"), col("model"), col("best score of the text", "num"),
                                    col("sentence")], rows=anti_rows, pageSize=100, sort=[2, 1])))
    lo_n = stats["best_under_50"] + stats["best_none"]
    page("no_names.html", "Texts without names", """
<p>A text with no name, and a text that says its beings have no name, belong to what is studied
here as much as a name does. Two things are tracked.</p>

<h2>1. Candidates for having no name</h2>
<p>A pattern search cannot show that a text has no name. It can only collect the texts in which
nothing convincing was caught. These are candidates:</p>
<table class=kv>
<tr><td>Nothing caught by any pattern</td><td>%d texts</td></tr>
<tr><td>Best score in the body under 0.5</td><td>%d texts (the row above included)</td></tr>
<tr><td>&nbsp; of those, with a title-only designation</td><td>%d texts: the text put a title over a section about an inhabitant and never used it again</td></tr>
<tr><td>Share of all counted texts under 0.5</td><td>%s%%</td></tr>
</table>
<p>The cut at 0.5 is a choice; the <a href="texts.html">Texts</a> table can be filtered at any other.
Title-only designations are kept apart because a title can be a name the model gave the being
("The Floor That Eats") or the title of a section ("What it wants"); measured on read samples, a
heading that never recurs designates an inhabitant about 4 times in 10, a list head about 7 in 10.</p>
<p><b>How the candidates will be checked.</b> At the end of the study a large random sample of the
candidates will be given to language models with one question: are there names or titles of
beings in this text? A yes-or-no question is easier to answer reliably than a request to list the
names. A sample of texts with high best scores will be given the same question, to see how often
the same models say "no" where a name is known to be. This has not been done yet.</p>
<p><b>Checked by eye so far.</b> Texts read whole by the reader who writes the patterns:</p>%s
<p class=small>"Uncovered" texts were drawn from the ten models with the fewest names found, so
they are not a sample of all candidates.</p>

<h2>By model</h2>%s

<h2>2. Texts that say there is no name</h2>
<p>%d sentences in %d texts say that a being has no name, refuses one, cannot be named, or is
known by something other than a name. Of 30 such sentences read, %s were about the inhabitants;
the others were about something else ("colours that have no names"). A text can say this and
still give a name ("They are called the Hollow Choir, though they have no name for themselves"):
the third column shows whether a name was caught in the same text.</p>
<div id=at></div><script>tableFromUrl("at","x/anti.json")</script>
""" % (stats["best_none"], stats["body_under_50"], stats["titled_any_not_named"], pct(stats["body_under_50"], okn),
       table([col("check", "num"), col("texts drawn from"), col("texts read", "num"),
              col("no name seen", "num"), col("%", "num")], eyerows, sort=[0, 1]),
       table([col("model", "html"), col("texts", "num"), col("no name in the body", "num", "best score in the body under 0.5"), col("%", "num"),
              col("of those, titled", "num", "texts with a title-only designation"),
              col("nothing caught", "num"), col("% nothing", "num"),
              col("texts that say there is no name", "num"), col("% saying so", "num"),
              col("saying so, and no name caught", "num", "texts with a no-name statement and a best score under 0.5")],
             nnrows, sort=[3, -1], page=130),
       len(anti_rows), stats["anti_texts"],
       ("%d" % (ev["anti_name"][5]) if "anti_name" in ev else "?")), first=True)

    # ----------------------------------------------------------------- recall
    summ = defaultdict(lambda: dict(texts=set(), noname=set(), n=0, then=Counter(), now=Counter(), date=""))
    rrows = []
    def then_label(t):
        return {"strict": "by a pattern at 0.8 or more", "wide": "only by a lower pattern", "missed": "by nothing"}.get(t, t)
    for chk, date, pool, tid, chars, name, then, now, pnow, forms, note in rc:
        s = summ[(chk, pool)]
        s["texts"].add(tid); s["date"] = date
        if name is None:
            s["noname"].add(tid)
        else:
            s["n"] += 1
            try:
                tb = band(float(then))
            except ValueError:
                tb = {"strict": "hi", "wide": "lo", "missed": "none"}[then]
            s["then"]["hi" if tb == "hi" else "none" if tb == "none" else "low"] += 1
            nb = band(now)
            s["now"]["hi" if nb == "hi" else "none" if nb == "none" else "low"] += 1
        rrows.append([chk, pool, tlink(tid), cov[tid][1], name or "(no name in the text)",
                      then_label(then) if then else "", fnum(now) if name else "", pnow or "",
                      "; ".join(json.loads(forms)), note or ""])
    srows = []
    for (chk, pool), s in sorted(summ.items()):
        srows.append([chk, s["date"], pool, len(s["texts"]), len(s["noname"]), s["n"],
                      s["then"]["hi"], s["then"]["low"], s["then"]["none"], pct(s["then"]["hi"], s["n"]),
                      s["now"]["hi"], s["now"]["low"], s["now"]["none"], pct(s["now"]["hi"], s["n"])])
    ag = q("SELECT reader, first, second, pattern_id FROM agreement")
    agree_html = "<p>Not measured yet.</p>"
    if ag:
        n = len(ag)
        isname = lambda v: v in "bpts"
        exact = sum(1 for r in ag if r[1] == r[2]); nm = sum(1 for r in ag if isname(r[1]) == isname(r[2]))
        bg = sum(1 for r in ag if (r[1] == "b") == (r[2] == "b"))
        pairs = Counter((r[1], r[2]) for r in ag if r[1] != r[2])
        agree_html = """<p>A second reader (another instance of the same model, in a fresh context, with the
rule as written in the README and nothing else) judged %d of the first reader's hits again, blind.
Agreement: %d of %d on the exact code (%s%%), %d on "a name or not" (%s%%), %d on "a being or not"
(%s%%). The disagreements, as (first, second): %s.</p>""" % (
            n, exact, n, pct(exact, n), nm, pct(nm, n), bg, pct(bg, n),
            ", ".join("%s/%s %d" % (VERDICTS.get(a, a), VERDICTS.get(c, c), k) for (a, c), k in pairs.most_common()))
    page("recall.html", "Recall checks",
         """<p>A recall check: texts are drawn at random and read whole (up to a few thousand characters),
and every name seen by eye is written down with what caught it at the time. "Now" columns are
recomputed against the current patterns, so they move as patterns are added. The samples are
small; the percentages show direction, not a measured rate.</p>
<p>The "now" numbers of an earlier check are optimistic: new patterns are written from the very
names that check found missing. Only the "then" numbers of a fresh check measure the patterns
honestly, so a new sample is drawn each round.</p>
<p>The same reader wrote the patterns and judged what counts as a name.</p>
<h2>Second reader</h2>%s
<h2>By check</h2>%s<h2>Every name</h2>%s""" % (agree_html, 
             table([col("check", "num"), col("date"), col("texts drawn from"), col("texts", "num"),
                    col("texts with no name", "num", "texts in which the reader saw no name at all"),
                    col("names seen", "num"),
                    col("then: ≥ 0.8", "num", "names caught, when the text was read, by a pattern of precision 0.8 or more"),
                    col("then: lower", "num"), col("then: nothing", "num"), col("then: % ≥ 0.8", "num"),
                    col("now: ≥ 0.8", "num"), col("now: lower", "num"), col("now: nothing", "num"),
                    col("now: % ≥ 0.8", "num")], srows, sort=[0, 1]),
             table([col("check", "num"), col("pool"), col("text", "html"), col("model"), col("name seen by eye"),
                    col("caught then"), col("score now", "num"), col("patterns now"),
                    col("forms that were missed"), col("note")], rrows)), first=True)

    # --------------------------------------------------------------- readings
    page("readings.html", "Reading log",
         "<p>Texts read by eye to find forms of naming, with what was seen in each.</p>" + table(
             [col("round", "num"), col("text", "html"), col("model"), col("how it was chosen"),
              col("forms of naming seen"), col("note")],
             [[rnd, tlink(tid), cov[tid][1], basis, "; ".join(json.loads(saw)), note or ""]
              for rnd, tid, basis, saw, note in readings]), first=True)

    frows = [[tlink(tid), r[1], r[9], "corpus tagger" if r[9] in ("broken", "refusal", "off-topic") else "check made here",
              r[2]] for tid, r in sorted(cov.items()) if r[9]]
    untagged = sum(1 for r in cov.values() if not r[10])
    page("flagged.html", "Flagged texts",
         """<p>Texts left out of the counts (%d).</p>
<ul>
<li><b>broken, refusal, off-topic</b>: the status recorded in the corpus by its taggers (language
models that read each text). "Broken" covers repetition and garbled endings as well as runs of
unrelated tokens. "Refusal" covers a writer that declined, criticised the request or addressed
the reader as the one who asked. The study takes these as given.</li>
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
    if not (os.path.exists(marker) and open(marker).read().strip() == run["content_sha256"]):
        cur, bucket = None, {}
        def flush():
            if bucket:
                with open(os.path.join(tdir, "%d.json" % cur), "w", encoding="utf-8") as f:
                    f.write(jdump(bucket))
        for tid, model, text in snap.execute("SELECT id, model, text FROM texts ORDER BY id"):
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
    with open(os.path.join(mdir, "patterns.json"), "w") as f:
        f.write(jdump({p[0]: [p[21], p[4]] for p in active}))
    with open(os.path.join(mdir, "status.json"), "w") as f:
        f.write(jdump({tid: [("flagged: " + r[9]) if r[9] else "best pattern score %s" % fnum(r[5])] for tid, r in cov.items()}))
    ldir = os.path.join(SITE, "l")
    os.makedirs(ldir, exist_ok=True)
    cur, bucket = None, {}
    def flushl():
        if bucket:
            with open(os.path.join(ldir, "%d.json" % cur), "w", encoding="utf-8") as f:
                f.write(jdump(bucket))
    for tid, s0, e0, src in rdb.execute("SELECT text_id, start, end, source FROM labels ORDER BY text_id, start, end"):
        b = tid // 100
        if b != cur:
            flushl(); cur, bucket = b, {}
        bucket.setdefault(tid, []).append([s0, e0, SRC[src]])
    flushl()
    page("text.html", "Text", """<div id=head></div>
<p class=small id=legend></p>
<div id=body class=text></div><h2>Names and roles in this text</h2><div id=labels></div>
<h2>Pattern hits in this text (first instrument)</h2><div id=hits></div>
<script>
(function () {
  var qs = new URLSearchParams(location.search), id = +qs.get('id'), at = qs.get('at'), b = Math.floor(id / 100);
  var showPat = qs.get('show') === 'patterns';
  var want = (qs.get('mark') || '').split('|').map(function (x) { return x.trim().toLowerCase(); }).filter(Boolean);
  var wantw = (qs.get('markw') || '').split('|').map(function (x) { return x.trim().toLowerCase(); }).filter(Boolean);
  var holds = function (lab) { var n = norm(lab); if (want.indexOf(n) >= 0) return true;
    return wantw.some(function (w) { return n.split(/[^a-z0-9\u00c0-\uffff']+/).indexOf(w) >= 0; }); };
  var esc = function (s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;'); };
  var norm = function (s) { return s.replace(/[*_`"“”#]/g, '').replace(/[‘’]/g, "'").replace(/\s+/g, ' ').trim().toLowerCase().replace(/^(the|a|an)\s+/, ''); };
  var get = function (u) { return fetch(u).then(function (r) { return r.ok ? r.json() : {}; }); };
  Promise.all([get('t/' + b + '.json'), get('m/' + b + '.json'), get('m/patterns.json'), get('m/status.json'), get('l/' + b + '.json')]).then(function (res) {
    var t = res[0][id]; if (!t) { document.getElementById('body').textContent = 'no such text'; return; }
    var ms = res[1][id] || [], pat = res[2], st = res[3][id] || [''], ls = res[4][id] || [];
    var pr = function (m) { var p = pat[m[2]]; return p && p[1] === 'name' ? (p[0] || 0) : -1; };
    var src = ['', 'from a quote', 'from a line'];
    document.querySelector('h1').textContent = 'Text #' + id;
    var other = 'text.html?id=' + id + (showPat ? '' : '&show=patterns');
    document.getElementById('head').innerHTML = '<p>' + esc(t[0]) + ' · ' + t[1].length + ' characters · ' + ls.length + ' labels · ' + st[0] +
      ' · <a href="https://atlas.animalabs.ai/v3/creature/' + id + '">in the Atlas</a> · <a href="model/' +
      t[0].replace(/[^A-Za-z0-9._-]/g, '_') + '.html">model page</a></p>';
    document.getElementById('legend').innerHTML = showPat
      ? 'Highlighted: pattern hits, by the precision of the best pattern that matched there: <mark class=s>0.8 or more</mark> &nbsp; <mark>0.5 to 0.8</mark> &nbsp; <mark class=lo>under 0.5 or not measured</mark> &nbsp; <mark class=st>sentence about naming</mark> &nbsp; hover a highlight to see the patterns. <a href="' + other + '">Show names and roles instead.</a>'
      : 'Highlighted: names and roles. <mark class=l>found in a quote</mark> (a sentence saying who or what lives there) &nbsp; <mark class=ll>found in a line</mark> (a heading, or a sentence outside the quotes). <a href="' + other + '">Show pattern hits instead.</a>';
    var text = t[1], cuts = {}, spans = showPat ? ms : ls;
    spans.forEach(function (m) { cuts[m[0]] = 1; cuts[m[1]] = 1; }); cuts[0] = 1; cuts[text.length] = 1;
    var pts = Object.keys(cuts).map(Number).sort(function (a, b) { return a - b; }), out = '', first = null;
    for (var i = 0; i + 1 < pts.length; i++) {
      var s = pts[i], e = pts[i + 1], on = spans.filter(function (m) { return m[0] <= s && m[1] >= e; });
      var seg = esc(text.slice(s, e));
      if (!on.length) { out += seg; continue; }
      if (showPat) {
        var best = Math.max.apply(null, on.map(pr));
        var cls = best >= 0.8 ? 's' : best >= 0.5 ? '' : best >= 0 ? 'lo' : 'st';
        out += '<mark class="' + cls + '" id="p' + s + '" title="' + on.map(function (m) { return m[2]; }).join(', ') + '">' + seg + '</mark>';
      } else {
        var hit = (want.length || wantw.length) && on.some(function (m) { return holds(text.slice(m[0], m[1])); });
        if (hit && first == null) first = s;
        out += '<mark class="' + (on.some(function (m) { return m[2] & 1; }) ? 'l' : 'll') + '" id="p' + s + '"' + (hit ? ' style="outline:2px solid #0a6b1f"' : '') + ' title="' + src[on[0][2]] + '">' + seg + '</mark>';
      }
    }
    document.getElementById('body').innerHTML = out;
    makeTable(document.getElementById('labels'), {columns: [{title: 'position', type: 'num'}, {title: 'label', type: 'html'}, {title: 'found in', type: 'text'}],
      rows: ls.map(function (m) { var lab = text.slice(m[0], m[1]); return [m[0], '<a href="name.html?n=' + encodeURIComponent(norm(lab)) + '">' + esc(lab) + '</a>', src[m[2]].replace('from ', '')]; }),
      pageSize: 500, sort: [0, 1]});
    var rows = ms.map(function (m) {
      var p = pat[m[2]] || [null, ''];
      return [m[0], esc(text.slice(m[0], m[1])).slice(0, 160), '<a href="pattern/' + m[2] + '.html">' + m[2] + '</a>',
              p[1] === 'statement' ? '' : (p[0] == null ? '' : p[0]), p[1]];
    });
    makeTable(document.getElementById('hits'), {columns: [{title: 'position', type: 'num'}, {title: 'captured', type: 'html'},
      {title: 'pattern', type: 'html'}, {title: 'precision of the pattern', type: 'num'}, {title: 'yields', type: 'text'}],
      rows: rows, pageSize: 500, sort: [0, 1]});
    var go = at != null ? at : first;
    if (go != null) { var el = document.getElementById('p' + go); if (el) el.scrollIntoView({block: 'center'}); }
  });
})();</script>""")
    big = [(os.path.getsize(os.path.join(dp, f)), os.path.join(dp, f)) for dp, _, fs in os.walk(SITE) for f in fs]
    for size, path in big:
        if size > 25 * 1024 * 1024:
            print("WARNING over 25 MiB (the host's limit for one file): %s %.1f MB" % (path, size / 1e6))
    print("files: %d, total %.0f MB" % (len(big), sum(x[0] for x in big) / 1e6))
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
