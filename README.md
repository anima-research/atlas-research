# atlas-research

Studies built on the corpus of the [Atlas](https://atlas.animalabs.ai): texts in which language
models describe places and the beings that live in them.

Each study has its own directory, with the code, the hand-made inputs (patterns, verdicts, reading
logs) and a README. Derived data and built sites are not in the repository; each README says how
to rebuild them.

| directory | study |
|---|---|
| `names/` | The names and roles that models gave to the beings in the creature texts: first retrieved with regular expressions, then written out by a small model from the sentences that say who lives there (`names/roles/`). |
| `who/` | In progress. Published so far: the quotes in which each text says who or what lives there (`who/quotes/`), which the names study reads, and a set of 180 texts read whole (`who/gold/`). |
| `care/` | Keepers, tenders, guardians: what the texts say about inhabitants given a name or role of care - their role, how they stand to what they care for, what it costs them, where they came from, what becomes of them. |
