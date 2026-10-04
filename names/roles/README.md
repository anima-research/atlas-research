# Names and roles

Built 3 October 2026 by Claude Fable 5.1 with Lari, on the frozen snapshot of release 15.
Result: `../data/roles.db`, table `labels(text_id, start, end, label, norm, source)`.
One row is one name or role the text gives an inhabitant, at one position in the text.
Names and roles are not kept apart: "The Flux Dwellers are the city's gardeners, architects, and
caretakers" gives four rows. Nothing is filtered and there are no stoplists; general words
(inhabitants, people, creatures) are in the set and lead it by count.

986,691 labels in 31,533 texts; 382,366 distinct strings; median 25 labels per text.

## How it was made

Two passes of one small model (openai/gpt-6-luna), each answer checked by script: a label is kept
only if it is found, as written, inside the line it was given for (1.3% dropped).

1. `prompt_v2.md` over the numbered who-quotes of each text (`../../who/quotes/corpus/`),
   one request per text. `source = 'quote'`, 814,018 labels.
2. `prompt_items_v1.md` over what the quotes did not cover: headings, and sentences in which a
   pattern of the names study caught something outside every quote (`items.py`), 25 lines per
   request. `source = 'line'`, 172,672 labels.

`luna.py`, `luna_items.py` run synchronously; `batch_roles.py` sends the same requests through the
Batch API; `build_roles.py` merges; `check.py` measures the result against what was read by eye
and writes `checks.json`, from which the site takes its numbers. Cost of the whole corpus: about $23.

## Inputs

- `../data/snapshot_r15.sqlite` and `../data/names.db`: the texts and the pattern hits of the names
  study (`../snapshot.sh`, `../extract.py`).
- `../../who/quotes/corpus/`: the who-quotes. They are not in the repository; download
  `who_quotes_1.jsonl.gz` and `who_quotes_2.jsonl.gz` from the site's Data export page
  (https://atlas.lari-island.ai/research/names/export.html). `luna.py` reads the raw answers file
  of the extraction run, which has the same fields per quote.
- `out/` (the model's raw answers, 135 MB) is not in the repository; `roles.db` is exported whole
  as `labels.csv.gz` on the same page.

## What it was measured against

The 1,983 hand verdicts of the names study (`../labels.jsonl`), on their 1,815 texts:

| verdict | n | pass 1 | both passes |
|---|---|---|---|
| name of a being | 929 | 767 | 911 (98%) |
| name of a place | 40 | 13 | 14 |
| thing or phenomenon | 104 | 29 | 33 |
| not a name | 777 | 266 | 326 |

"Not a name" in those verdicts included ordinary species words, which count here.
The verdicts were made on pattern hits, so they cannot show names no pattern caught.

Ten texts read whole before any request (`pilot_hand.json`): of 139 labels marked by hand the
first pass found 118; 10 of the 21 missed were denials ("not plants"), which are not collected.

## Known gaps

- A role in a sentence that the who-quotes did not take and no pattern touched is not seen.
  Texts where the word occurs and no label holds it, on the 1,815 texts: keeper 25 of 332,
  gardener 37 of 181, tender 72 of 251, shepherd 24 of 72 (these include adjectives,
  comparisons and denials, which are rightly absent; for keeper about 5% are real misses).
- Lines longer than 700 characters were not sent in pass 2.
- Denials and comparisons are not collected.
- Singular and plural, and compound forms (moss-keeper), are not folded.
- Long descriptive phrases are in the set as labels.
