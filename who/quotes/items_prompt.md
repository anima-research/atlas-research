Below are passages copied, word for word, out of several texts. Each text was written by a language model that had described an imagined place and was then asked what lives there. You do not see the texts, only passages from them: the ones that say who or what the inhabitants are, what they are not, how they stand to the place, what they do, and how a visitor is treated. Each item is one text. The passages are in the order they stand in the text; the number before each passage says how far into the text it begins, in percent.

Answer for each item separately, from its passages alone. Do not let one item colour another: they come from different texts by different writers. Do not judge the quality of the writing.

For each item give one JSON object with these keys.

**item** — the item's number.

**relation** — how the text places what lives there relative to the place. One of four levels; give the highest level the passages reach.

- `"in"`: the inhabitants are beings living in the place as in a habitat. They may be shaped by it, adapted to it, or look after it; the passages do not say that they are the place or parts of its body, and do not say that the place is alive.
- `"part"`: the passages say that the inhabitants are parts, organs, cells, extensions or expressions of the place (or of one larger organism or system that the place is), or that they are not separate from it. Being adapted to the place or caring for it is not enough.
- `"alive"`: the passages say that the place itself is alive, aware, or a being, and mean it: the claim is stated outright or carried through more than one sentence. The inhabitants are still mainly other beings; the place is one more living thing beside or around them. A single passing figure of speech ("the cavern was pleased", "the city listens") is not enough.
- `"is"`: the text's own answer to "what lives here" is the place itself, or its mind, or its process, or the whole system taken as one being. Other creatures may appear, but the place (or the whole) is presented as the main inhabitant.

**relation_quote** — for "part", "alive" and "is": the one sentence among the passages that says it most directly, copied exactly. Empty string for "in".

**main_kind** — the kind of inhabitant the text gives most weight to. One of: `"animals"` (including invented fauna), `"plants_fungi"`, `"microbes"`, `"people"` (persons with culture, speech, crafts or names; human or not), `"machines"` (mechanical beings, or beings part organism and part machine), `"spirits"` (ghosts, gods, bodiless presences, beings of light, sound or energy), `"place_mind"` (the place or the system itself as a being or a mind), `"process"` (a process, condition or pattern said to be what lives there), `"other"`.

**number** — `"one"` (a single being), `"one_kind"` (one kind, people or species with many members), `"several"` (several kinds).

**tending** — do the inhabitants maintain, repair, tend, regulate or keep the place or its workings? `"yes"` or `"no"`.

**predation** — `"present"` (something hunts, is hunted, or is eaten alive), `"denied"` (the passages say there are no predators or that nothing hunts), `"absent"` (not mentioned).

**visitor** — `"you"` (the reader is addressed as someone present in the place), `"outsider"` (a traveller, observer or stranger is mentioned in the third person), `"none"`.

**unsure** — a list of the keys above on which you hesitated between two answers, or on which the passages do not let you answer; empty list if none.

Answer with one JSON array holding one such object per item, in the order of the items, and nothing else.
