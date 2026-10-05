# Run inside build_site.py after site_more.py: the pages whose tables are recounted in the browser
# for a chosen writer (a model, or all models of a lab) and period of release.
for f in ('common.js', 'kept.js', 'words.js', 'weave.js'): shutil.copy(os.path.join(HERE, 'js', f), os.path.join(SITE, f))
open(os.path.join(SITE, 'config.js'), 'w').write('var CFG=' + json.dumps({'words': STEMS, 'eras': ERA_KEYS, 'q': QTEXT, 'textUrl': TEXT_URL}) + ';')
# what the names say is kept, per text: [[nouns], [care words in that name]] for every name with a noun
KN = collections.defaultdict(list)
for n, nouns in KEPT.items():
    if not nouns: continue
    ws = sorted({m_.group(1) for m_ in WORD.finditer(n)})
    for t_ in name_texts[n]: KN[t_].append([nouns, ws])
dump('kn.json', KN)
BAR = "<div id=bar></div>"
page('kept.html', 'What is kept', f"""
<p>What the keepers keep, seen two ways. <b>By the name</b>: what the name itself says is kept (<i>moss-tenders</i>, <i>keepers of the threshold</i>). <b>By the text</b>: what the sentences about the being's work say it cares for,
and, apart from that, what they say it works against. A keeper of chaos and a keeper who holds chaos off are on different sides.</p>
{BAR}<p class=qtabs id=views></p><p class=small id=note></p><div id=t><span class=small>loading…</span></div>
<p class=small>Every table here is recounted for the writer and period chosen above. Singular and plural are folded into one row by rule: a form in -s, -es, -ies or -ves is counted under its base
(<i>channels</i> under <i>channel</i>, <i>memories</i> under <i>memory</i>, <i>leaves</i> under <i>leaf</i>) when the base itself occurs in the data; {n_folded:,} forms were folded.
The readings are by a small model (openai/gpt-6-luna), each noun accepted only if it stands in the name or in the sentences; the instructions are <code>care/prompt_kept.md</code> and <code>care/prompt_kept_text.md</code>.</p>
<script src='kept.js'></script>""")
page('words.html', 'The twelve words', f"""
<p>A being is counted under a word when the word stands in one of the care names the text gives it. A being with several of the words is counted under each. The table is recounted for the writer and period chosen.</p>
{BAR}<div id=t><span class=small>loading…</span></div>
<p class=small>"cost %, texts of 30 to 60 sentences" repeats the cost column inside one band of length, since longer texts answer more questions (empty under 20 beings).
The last two columns separate the word from the writers who favour it. "Cost, against other words" is the plain difference in percentage points between beings with the word and the beings without it.
"Inside one writer" takes each writer with at least 8 beings on either side, compares that writer's beings with the word to its beings without, and averages. Where the first is large and the second near zero, the difference belongs to the writers, not to the word; guardian is the clear case. A word opens its portrait.</p>
<h2>Words given together</h2><p id=combo></p><script src='words.js'></script>""")
page('weave.html', 'Weave: one keeper, or several', f"""
<p>A text about one gardener is a different thing from a text in which a keeper stands beside a gardener and a tender. Three arrangements, by text; everything below is recounted for the writer and period chosen.</p>
{BAR}<div id=kinds><span class=small>loading…</span></div>
<p class=small><b>Focus</b> is the share of the text's sentences that the reader listed for the being under any of the five questions. Cost, origin and fate are the share of beings whose text answers the question.</p>
<p>Over the whole set, a being that carries several of the words at once is the centre of its text: more of the text is about it, and its origin and fate are told more often. In an ensemble each keeper is one post among several.
<span id=within></span></p>
<p class=small>The arrangements follow how the reader divided the text into beings. Where it took two keepers for one, an ensemble became a stack; how often that happened was not measured.</p>
<h2>The twelve words</h2><p>Where the beings of each word stand, and what they get there.</p><div id=t1></div>
<h2>Words on one being</h2><p>Of the beings that carry the word in the row, the percentage that also carry the word in the column.</p><div id=mx1></div>
<h2>Words on different beings of one text</h2><p>Pairs of beings in one text, one carrying the row word and the other the column word.</p><div id=mx2></div>
<h2>Writers</h2><p>Share of each writer's care texts in each arrangement. Filter <code>care texts</code> with <code>&gt;=60</code> before comparing.</p><div id=t2></div>
<script src='weave.js'></script>""")
