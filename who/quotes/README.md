# Quotes: who or what lives there

For every creature text of Atlas release r15, the sentences in which the text itself says who or
what lives there: what the inhabitants are, are not, are called, are part of. Collected by Claude
Fable 5.1 on 3 October 2026 as part of a study that is still in progress ("who lives there"); this
directory and `../gold/` are the parts of it that other work already reads. The names-and-roles
set of the names study (`../../names/roles/`) was read from these quotes.

## What is here

| file | what it is |
|---|---|
| `extract_prompt.md` | the instruction given to the extracting model: three sentences, no example phrases, no categories |
| `extract_prompt_v1.md` ... `v7.md` | earlier versions, kept as they were |
| `extract.py` | one request per text; every returned quote is looked for in the text, exactly, then loosely, and what is stored is the text's own stretch with its position; a quote that cannot be found is dropped |
| `batch.py` | the same through a batch interface |
| `headings.py` | the heading a quote stands under, found by script |
| `recall.py`, `pilot*_reference.json`, `pilot*_ids.json` | phrases marked by reading whole texts, and the measure of what an extractor misses against them; only `pilot3` was marked before extraction and with the instruction fixed, the other two were used while the instruction was being changed and are not fair tests |
| `items.py`, `items_prompt.md` | an early trial of sorting quotes as anonymous numbered items; not used for any result |
| `corpus_ids.json` | the ids of the texts sent |
| `corpus/unanswered.json` | the three texts the provider's content filter refused |

The quotes themselves (`corpus/`, 134 MB) are not in the repository. They can be downloaded from
the names study's site, page Data export: `who_quotes_1.jsonl.gz`, `who_quotes_2.jsonl.gz`
(one line per text: `text`, and `quotes` as a list of `start`, `end`, `quote`).

The run: Claude Sonnet 5.5 over the whole corpus; 32,000 of 32,003 texts answered. A text may
have more than one row in the raw answers file (retries); the last row with quotes is the one used.

## What has and has not been checked

- Every stored quote is the text's own stretch at its position (by construction).
- Against `pilot3_reference.json` (102 phrases marked in ten texts read whole), the corpus
  extractor catches 95.
- How many quotes are beside the point has not been measured for the corpus run.

## The gold set (`../gold/`)

180 texts read whole on a four-level scale of how the inhabitants stand to the place (in / part /
alive / is), with the questions in `reader_codebook.md`; 60 of them read twice by independent
readers, and the 14 disagreements ruled on in `adjudicated.jsonl`. The readers were instances of
the model that wrote the study, so agreement with it is partly a shared view. The sample
(`sample.json`) was drawn in three cells by how two earlier model judges had answered a question
about the place (both yes, split, both no); those judges are not published. The copies of the
texts that the readers were given are not in the repository; the ids are in `batches.json`.
