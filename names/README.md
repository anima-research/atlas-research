# Atlas names study

Written by Claude Fable 5.1 on Lari's laptop, 2 October 2026, in one session: the snapshot, the
patterns, the verdicts, the extractor, the site and this file. Two more instances of the same
model read for it (recall check 5, the thirty undetermined texts) and a third re-judged two
hundred verdicts blind. Lari set the question, the rulings in the reading log, and the
perimeter. Live site: https://atlas.lari-island.ai/research/names/

Finding the names that models gave to the beings in the Atlas creature texts, with regular
expressions, reproducibly. The site is static: `python3 -m http.server 8795 -d site`;
`deploy.sh` publishes it.

## Files

| file | what it is | source of truth? |
|---|---|---|
| `snapshot.sh`, `export_on_box.py` | copy the creature texts of one finalized release from the corpus box (read-only; needs `ATLAS_BOX` and `ATLAS_RELEASES`) | yes |
| `patterns.py` | every active pattern, with the passage it was first seen in | yes |
| `patterns_retired.py` | earlier versions of patterns and why each was replaced; append-only | yes |
| `labels.jsonl` | verdicts on sampled hits, keyed by text id and character span | yes |
| `readings.jsonl` | which texts were read by eye, how they were chosen, what was seen | yes |
| `rounds.jsonl` | one line of counts per round | yes |
| `recall.jsonl` | covered texts read whole: every name seen by eye, and whether a strict pattern, only a wide one, or nothing caught it | yes |
| `extract.py` | snapshot + the files above -> `data/names.db` | |
| `sample.py`, `label.py` | draw a seeded sample of a pattern's hits; record verdicts on it | |
| `recall_add.py` | append a recall check to `recall.jsonl`, stamping each name with its score at that moment | |
| `retire.py` | copy a pattern's current version to `patterns_retired.py` before changing it | |
| `show.py` | print texts with the current hits marked inline, for reading | |
| `build_site.py` | `data/names.db` -> `site/` | |
| `data/`, `site/` | derived; rebuilt by the commands below | no |

## A round

1. Read texts: a sample from the uncovered pool, and a fresh random sample of covered texts read
   whole (`python3 show.py <ids>` marks the current hits). Log each in `readings.jsonl`; write every
   name seen in the covered sample to `recall.jsonl`.
2. Write or correct patterns in `patterns.py`. A changed pattern gets a new `version`; the old
   dict goes to `patterns_retired.py` with `retired_reason`.
3. `python3 extract.py --rev 15`
4. `python3 sample.py <pattern> --n 30`, read, then `python3 label.py <pattern> <verdicts> --round N`
   (before changing a pattern: `python3 retire.py --reason "..." <pattern>`)
5. `python3 extract.py --rev 15 --round N --record "what was done"` and `python3 build_site.py --rev 15`

## What counts as a name (for the verdicts)

- The name of a kind, of a single being, of a place, or of a thing or practice of the inhabitants.
- A word for a role or function that designates a kind counts: "the grazers", "the tenders",
  "the rooters". Models often name by role, and a role word and a name are not kept apart here.
- An ordinary species word does not count: "the crickets", "moss", "the humans".
- A description that stands where a name would stand counts when it is used as a fixed label
  ("the low ones", "Those Who Wait"), not when it is a passing description ("the small birds").

## Rules of the study

- The snapshot does not carry `creatures.name` or the tagger's attributes in `item_tags` (names
  assigned by an earlier LLM tagger). The study does not read them while patterns are being
  written. One comparison at the end, reported as such. The only column taken from `item_tags`
  is the text status (ok / broken / refusal / off-topic).
- The wording of the instruction the models were given is not public and is not quoted on the
  site or in this directory.
- Everything here is in English: the site is meant to become part of a publication.
- A pattern has no class. Its precision is the share of names among its hits that were read
  (computed from `labels.jsonl`, empty under 20 read). A name in a text scores the highest
  precision among the patterns that caught it; a text's best score is the highest score among
  its names. Cuts such as 0.8 or 0.5 appear only as display choices.
- "Also in the place text" says where a name first appeared. It is not a test of whether the
  name is of a place or of a being: of the hits read so far that were in the place text, more
  were beings than places.
- Sample counts shown on the site are computed from `labels.jsonl`, never typed by hand.

## Second-order questions

The site answers one class of them directly: the share of each model's texts that contain any
string of a set, counted by texts (`name.html?n=keeper|keepers`, with `&vs=tender|tenders` for a
second set). Everything else is meant to be asked of the exported tables (site page Data export:
`texts.csv`, `text_names.csv`, `names.csv`, `patterns.csv`, `models.csv`, each with its columns
described in `export/README.md`). Singular and plural are not folded in the data; a lemma, if
ever added, goes in a column of its own beside the string.

## Title only: the third state

A string caught in a title line (heading, bold line, head of a list item) that occurs nowhere
else in the text is kept apart as "title only". It may be a title the model gave one inhabitant
in place of a name ("The Floor That Eats") or the title of a section ("What it wants"); the two
are not told apart, and the text is not forced into "named" or "not named". Each name in a text
records it (`in_title`, `body_occ`, `body_cased` in `text_names`); each text has a best score in
the body and a best score among title-only designations (`text_cov`).

Title lines are read by nine patterns: three kinds of line, each split by what the body does
with the title (never again / again in lower case / again with the same capitals). The split was
made because the precision differs: a heading that never recurs designates an inhabitant 0.38 of
the time, one that recurs with the same capitals 0.94. A pattern split out of earlier ones
inherits their verdicts where it captures the same place (`labels_from`).

## Kinds of answer

The unit of the study was the name; the text was only where names lie. That put "the canyon is
a being" and "diverse marine life" in the same box (nothing caught). Since round 7 every text
has a kind of answer, by a stated rule over what was caught: catalogue / named / place itself /
a process / unnamed, said so / ordinary biology / undetermined. The signals the rule reads
(names at 0.8 used in the body, place-is-inhabitant sentences, process sentences, no-name
sentences, species words) are stored beside the kind in `text_cov` and `texts.csv`, so another
rule can be applied without re-reading. Two statement patterns feed it: `place_is_inhabitant`
and `being_is_process`.

## Texts without names

A text with no name, and a text that says its beings have no name, are part of what is studied.

- Said outright: the `anti_name` pattern collects the sentences ("it has no name for itself").
- Not said: a pattern search cannot show absence. It collects candidates: texts whose best score
  is low. Site page: Texts without names.
- The candidate set is not the set of nameless texts. In recall check 3 (20 texts drawn from all
  texts) 6 had no name of a being; 3 of the 6 had a best score under 0.5, the other 3 had a high
  best score from the name of the place or from a wrong capture.
- Final check, not done yet: give language models a large random sample with one question, "are
  there names or titles of beings in this text?" (yes or no). Because of the point above, the
  sample should be drawn across all best scores (more densely where the score is low), not only
  from the candidates, and should include texts where names are known, to measure how often the
  judges say "no" wrongly.

## Who gives the name

`who_names` records the subject of a verb of naming with its object ("they call themselves",
"the locals call them", "one researcher called it") and the agent after "by". It yields a
namer, not a name; its captures are listed on its pattern page. First counts (r15): "they call
themselves" 685 hits, "do not call themselves" 153, "do not name themselves" 66; names given by
others ("people call them", "outsiders refer to them") are rarer.

## Not done yet

- Places and beings are not told apart.
- Singular and plural are separate names.
- No model-specific exceptions.
- The read-hits table on a pattern page also lists verdicts on hits the pattern no longer matches.
- `as_known` has 4 hits in all and no precision.
- Forms seen and not yet written as patterns: a bare capitalised plural opening a sentence
  ("Wanderers, conversely, roam"); a compound with an adjective between "the" and it ("the oldest
  shell-builders"); frames that say who gives the name ("they call themselves", "the keepers call
  them"), to be read off the hits of the naming-verb patterns.
- `live_the` is mostly wrong on verbs that take an object (roam the, work the); "live the" alone
  was right 6 times in 10.
- Forms seen in recall check 3 and not yet written as patterns: the second compound of a pair
  sharing one "the" ("the wire-weavers and spore-harvesters"); a bold lower-case compound after
  a dash. (The title forms seen there are now covered by the title states.)
- A fresh recall check is due at the start of each round (`recall_add.py`).
