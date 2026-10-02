# Atlas names study

Finding the names that models gave to the beings in the Atlas creature texts, with regular
expressions, reproducibly. The site is static: `python3 -m http.server 8795 -d site`.

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
5. Set `tier` from the verdicts (strict = at least 80% names in 30 or more read hits).
6. `python3 extract.py --rev 15 --record "what was done"` and `python3 build_site.py --rev 15`

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
- A wide pattern never removes a text from the uncovered pool. Only a strict pattern does.
- "Also in the place text" says where a name first appeared. It is not a test of whether the
  name is of a place or of a being: of the hits read so far that were in the place text, more
  were beings than places.
- Sample counts shown on the site are computed from `labels.jsonl`, never typed by hand.

## Not done yet

- Places and beings are not told apart.
- Singular and plural are separate names.
- No model-specific exceptions.
- The read-hits table on a pattern page also lists verdicts on hits the pattern no longer matches.
- Not yet sampled to 30: `binomial` (13 read), `list_bullet_lead` (none), `as_known` (4 hits in all).
- Forms seen and not yet written as patterns: a bare capitalised plural opening a sentence
  ("Wanderers, conversely, roam"); a compound with an adjective between "the" and it ("the oldest
  shell-builders"); frames that say who gives the name ("they call themselves", "the keepers call
  them"), to be read off the hits of the naming-verb patterns.
- `live_the` is mostly wrong on verbs that take an object (roam the, work the); "live the" alone
  was right 6 times in 10.
- Recall check 3 (fresh sample of covered texts) is due at the start of round 4.
