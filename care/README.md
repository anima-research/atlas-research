# Keepers, tenders, guardians

A study of the Atlas creature texts (release 15): what the texts say about inhabitants that are
given one of twelve names or roles of care (keeper, tender, steward, gardener, caretaker,
custodian, warden, guardian, shepherd, curator, maintainer, cultivator).

Written by Claude Fable 5.1 with Lari, 3-4 October 2026. Live site:
https://atlas.lari-island.ai/research/care/

## What is here

| file | what it is |
|---|---|
| `common.py` | the twelve words; which texts carry them (from `../names/data/roles.db`); sentence numbering |
| `prompt_v1.md` | the one instruction given to the reader model |
| `ask.py` | one request per text, synchronously; used for the pilots |
| `batch_care.py` | the same request for every care text through the Batch API |
| `build.py` | the answers -> `data/care.db` |
| `build_site.py` | `data/care.db` -> `site/`; every number on the pages is computed there |
| `site_more.py` | run by `build_site.py`: the Findings page (each figure reported by a reader and each quote is checked at build time, and the build stops if one is not found), the portrait page (a writer, a word, or both), the weave page, the kinds pages |
| `release_dates.json` | release dates of the writers, copied from the Atlas model ledger; used for the tables by date on the Findings page |
| `weave.py` | whether a being stands alone in its text, carries several of the words, or is one of several |
| `sample_reading.py` | draws the two samples of 300 beings per question that the readers read |
| `reading/*_notes.md` | each reader's account of the kinds of answer it met in its sample (ten readers, two per question) |
| `reading/*_merged.md` | the two accounts for each question set side by side; quotes checked against the samples |
| `kept_ask.py`, `prompt_kept.md` | what is kept: a small model gives, for each distinct care name, the nouns in it that say what is kept; a noun is accepted only if it stands in the name (`data/kept.json`) |
| `kept_text.py`, `prompt_kept_text.md` | what is cared for and what is worked against, by the text: a small model reads the role sentences of each being; a noun is accepted only if it stands in them (`data/kept_text.json`). `prompt_kept_text_v1.md` is the first instruction, which did not separate the two sides and was dropped |
| `pilot_kept_ids.json` | twenty random beings whose role sentences were marked by hand before that reading |
| `person.py`, `prompt_person.md` | who says "I" and who is "you" in the sentences about a being; asked only where a search finds such words (`data/person.json`) |
| `what_is_kept.py` | what stands next to a care word in the names, counted without a reader |
| `pilot_ids.json`, `pilot_hand.json` | ten random care texts and their marking by hand, made before any request |
| `pilot2_ids.json` | thirty more random texts, read through the chosen reader's cost and origin sentences |
| `deploy.sh`, `worker/` | publish `site/` as a Cloudflare Worker |

`data/`, `out/` (the reader's raw answers) and `site/` are derived and not in the repository. The
site serves the whole set as JSON: `beings.json` (one row per being) and `q_role.json`,
`q_relation.json`, `q_cost.json`, `q_origin.json`, `q_fate.json` (the sentences under each
question, by being).

## How it was made

1. Texts: every text in which the names-and-roles set (`../names/roles/`) holds a label with one
   of the twelve words as a whole word. 12,415 texts.
2. One request per text to anthropic/claude-sonnet-5.5: the text's sentences, numbered by script,
   and the care labels found in it. The reader names each inhabitant the labels are given to and
   lists sentence numbers under five questions: role, relation to what is cared for, cost, origin,
   fate. An empty list is an answer. Nothing is paraphrased.
3. 16,801 beings; `data/care.db` tables `beings`, `sentences`, `texts`.

The reader was chosen on ten texts marked by hand: of 50 answers (does the text answer the
question at all) a small model agreed on 42, two larger ones on 44 and 46; the small one missed
the cost in two texts of five that state one. The site's Method page carries the table, the
check on thirty further texts, and the known thin places.

## Reading

Kinds of answer were found by reading, not by coding the whole set. For each question two readers
(models, given no kinds in advance) each read a different sample of 300 beings and wrote up what
they met; a third pass compared the two accounts without forming kinds of its own. The site's
Kinds pages show those comparisons. The samples (`reading/<question>_A.md`, `_B.md`) are rebuilt
by `sample_reading.py`.

To rebuild: `python3 build.py && python3 sample_reading.py && python3 kept_ask.py && python3 kept_text.py submit (then collect) && python3 build_site.py`, then
`python3 -m http.server 8798 -d site`.
