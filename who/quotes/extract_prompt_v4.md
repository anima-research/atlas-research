You will read one text. A language model had described an imagined place and was then asked what lives there; the text is its answer. The text may be told from outside, or spoken by an inhabitant in the first person; then what the speaker says of itself is said of an inhabitant.

Your task is to copy sentences out of the text, word for word. Do not summarize, paraphrase, correct, translate or shorten anything. Each quote must be one continuous stretch of the text, copied character for character, with its punctuation, its capital letters, and any asterisks, dashes or other marks exactly as they stand. A quote is one whole sentence; take two neighbouring sentences only when the first cannot be understood without the second. Never join two separate places of the text into one quote, and never leave words out of the middle.

Copy out every sentence in which the text says, of what lives there or of any one inhabitant or kind of inhabitant, one of the following. A sentence that fits two kinds is given once, under the kind listed first.

- "answer": the text's own overall answer to the question of what lives here, wherever in the text it stands.
- "part": what the inhabitant is a part of, and how it stands to the place. That it is a part, an organ, a limb, an extension or an expression of the place or of something larger. That it is not separate from the place. That the place itself is alive, or is a being, or is what lives there. And the opposite: that it is a visitor, or does not belong to the place.
- "not": what the inhabitant is not: a kind of thing or of being that the text says it is not, or something the text says it does not have where a being of its sort would be expected to have it. Also a sentence saying that the line between two kinds of thing is blurred or gone in it.
- "name": what the inhabitant is called, what it calls itself, who gave it its name, or that it has no name.
- "is": what the inhabitant is. What kind of thing, what sort of being, what it is the same as, what it once was or came from.

Do not copy sentences that only describe how an inhabitant looks, moves, feeds, breeds or behaves, or what it does, or what the place is like, unless the same sentence also says one of the things above. Do not copy a heading alone.

Go through the text from its first line to its last, paragraph by paragraph. The first and the last paragraphs are the easiest to skip and often hold the answer. A text with several kinds of inhabitant usually says of each one what it is; take each.

Answer with one JSON object and nothing else. It has one key, "quotes", whose value is a list; each element of the list is an object with two keys, "kind" (one of the five words above) and "quote" (the copied sentence).
