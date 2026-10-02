"""Pattern registry for the Atlas names study.

This file is the source of truth for every active pattern. The database and the site
are rebuilt from it. When a pattern is changed it keeps its id and gets a higher
`version`; the earlier form is appended to patterns_retired.py with the reason.

Each pattern is a dict:

  id        short stable name
  version   integer, bumped on any change of the regex or its conditions
  round     the round in which this version was written
  added     date
  tier      'strict'  a hit is trusted to be a name; the text counts as covered
            'wide'    collects candidates; the text stays in the uncovered pool
  tier_basis  an optional remark on the tier; the sample counts themselves are computed
            from labels.jsonl and shown on the site
  yields    'name'       the captured group `name` (or `name2`) is a name candidate
            'statement'  the hit is a statement about naming (e.g. "it has no name")
  family    the kind of form: heading | markup | list | capitalisation | frame |
            descriptive | statement
  regex     Python `re` source
  flags     subset of 'm' (multiline), 'i' (ignore case)
  stop      optional name of a stoplist in STOPLISTS: captures whose normalised form
            is in the list are dropped
  mask      optional name of a mask in MASKS: lines matching the mask are blanked
            before this pattern runs (the pattern does not look inside them)
  reject    optional regex; a capture that matches it is dropped
  max_words optional cap on the number of words in the capture
  origin    {'text': id, 'excerpt': the passage in which the form was first seen}
  what      one or two sentences: what form of naming this is
  note      what a reader should know about its weaknesses

All patterns were written by reading texts. `origin` records where each form was seen.
The tier rule: a pattern is 'strict' when at least 80% of a read sample of its hits
(30 or more) are names, of beings, places or things.
"""
from patterns_retired import RETIRED  # noqa: F401  (re-exported for the extractor)

# ---------------------------------------------------------------------------
# building blocks

# A capitalised word, possibly hyphenated: Toneminds, Seep-Minds, Toe-Shear, Myco-Weave
CAPW = r"[A-Z][A-Za-zÀ-ɏ'’]*(?:-[A-Za-z][A-Za-zÀ-ɏ'’]*)*"
# Small words that may sit inside a capitalised name: Geometers of the Gyre,
# The One Who Waits at the Center, the House That Drinks
LINK = (r"(?:of|in|at|on|to|for|from|with|under|beneath|between|beyond|within|"
        r"without|who|that|which|de|la|du|von)")
# One or more capitalised words, joined by spaces and optional small words. Never
# crosses a line break.
NAME = (r"%(c)s(?:[ \t]+(?:%(l)s[ \t]+(?:the[ \t]+|a[ \t]+)?)?%(c)s)*" % {"c": CAPW, "l": LINK})
# Optional list marker at the start of a line:  "1. ", "2) ", "- ", "* ", "• ", "IV. "
MARK = r"(?:(?:\d{1,2}[.)]|[IVXLC]{1,5}[.)]|[-*•])[ \t]+)"
NUM = r"(?:\d{1,2}[.)]|[IVXLC]{1,5}[.)])[ \t]+"
BULLET = r"[-*•][ \t]+"
DASH = "—–"                       # em dash, en dash
OQ, CQ = "\"“", "\"”"             # opening / closing double quotes
# A verb of naming with its optional object pronoun: "call them", "known to themselves as"
CALL = (r"\b(?:call(?:ed|s|ing)?|name[ds]?|naming|known(?:[ \t]+\w+){0,3}?[ \t]+as|"
        r"refer(?:s|red|ring)?[ \t]+to(?:[ \t]+\w+){0,2}?[ \t]+as|dubbed|termed)"
        r"(?:[ \t]+(?:it|them|her|him|this|these|those|themselves|itself|us|me|you))?")
# Last elements that make a lower-case hyphenated compound the name of a kind of beings.
AGENT = (r"(?:[a-z]+(?:ers|ors)|folk|kin|born|people|ones|things|men|women|wives|hands|"
         r"children|creatures|beings|beasts|birds|fish|worms|flies|moths|crabs|mites|lice|"
         r"wrens|eels|hounds|walkers)")

MASKS = {
    # Lines set as titles: Markdown headings and lines that hold only a bold span.
    # Capital letters inside them are typography, not the writer marking a name, so the
    # capitalisation patterns do not look inside them. The heading and bold-line
    # patterns read these lines instead.
    "title_lines": r"^#{1,6}[ \t].*$|^[ \t]*%s?\*\*[^*\n]+\*\*[ \t]*:?[ \t]*$" % MARK,
}

# Words written in capitals for reasons other than naming (acronyms, a single letter,
# a musical note): a capture with two capitals in a row, or of one letter, is dropped.
REJECT_CAPS = r"[A-Z]{2,}|^[A-Za-z]$"

STOPLISTS = {
    # Capitalised words that are ordinary English, not names coined in the text.
    "common_caps": """
        i i'm i've i'd i'll
        monday tuesday wednesday thursday friday saturday sunday
        january february march april may june july august september october
        november december
        english french german latin greek roman spanish italian chinese japanese
        russian arabic victorian gothic euclidean darwinian newtonian cartesian
        earth god celsius fahrenheit kelvin morse
        """.split(),
    # Labels that structure a description and name nothing.
    "section_words": """
        form forms behavior behaviour role roles appearance diet habitat
        reproduction communication physiology anatomy senses movement locomotion
        size color colour sound sounds culture society purpose function origin
        origins lifecycle note notes summary overview conclusion introduction
        description ecology biology morphology sensory metabolism feeding defense
        defence lifespan temperament intelligence language relationship
        relationships interaction interactions adaptation adaptations
        """.split() + [
        # Title lines that recur across hundreds of texts and name no one. Taken from
        # the frequency list of heading and bold-line captures (round 2).
        "what lives here", "what lives there", "who lives here", "who lives there",
        "who or what lives here", "inhabitants", "first inhabitants", "residents",
        "first residents", "fauna", "flora", "vegetation", "plants", "insects", "birds",
        "people", "others", "visitors", "what they do", "what they are", "how they live",
        "what they believe", "how they speak", "what it wants", "what they know",
        "what they want", "what it does", "first answer", "and you", "you", "names",
        "work", "speech", "atmosphere", "their bodies", "interaction with the environment",
    ],
}


def P(id, version, round, tier, tier_basis, family, regex, origin, what, note="",
      yields="name", flags="", added="2026-10-02", **kw):
    d = dict(id=id, version=version, round=round, added=added, tier=tier,
             tier_basis=tier_basis, yields=yields, family=family, regex=regex, flags=flags,
             origin=dict(text=origin[0], excerpt=origin[1]), what=what, note=note)
    d.update(kw)
    return d


PATTERNS = [
    # ================================================================ headings
    P("md_heading", 2, 2, "wide",
      "",
      "heading",
      r"^#{1,6}[ \t]+%s?\**(?P<name>[^\n#*(:%s]+?)\**[ \t]*(?:[(:%s].*)?$" % (MARK, DASH, DASH),
      (4117, "# The Phonic Resonants"),
      "A Markdown heading line, up to the first colon, dash or parenthesis. Models often "
      "put the name of a kind or of a single being in a heading.",
      "Headings also carry section titles ('Form and Subsistence', 'What it wants').",
      flags="m", stop="section_words", max_words=10),
    P("heading_second", 1, 2, "wide",
      "",
      "heading",
      r"^#{1,6}[ \t]+[^\n(:%s]*?(?::[ \t]+|[ \t][%s][ \t]*|\()[*%s]*(?P<name>[^\n#*():%s%s]+?)[*%s]*\)?[ \t]*\**[ \t]*$"
      % (DASH, DASH, OQ, DASH, CQ, CQ),
      (30066, "### The Leather-Crabs: The Black Tide"),
      "The second part of a heading, after a colon or dash or inside parentheses: a "
      "second name for the same kind.",
      "The second part is as often a description ('the unseen citizens that make "
      "everything possible').",
      flags="m", stop="section_words", max_words=10),

    # ==================================================================== bold
    P("bold_line", 2, 2, "wide",
      "",
      "markup",
      r"^[ \t]*%s?\*\*%s?(?P<name>[^*\n(:%s]+?)(?:[ \t]*[(:%s][^*\n]*)?\*\*[ \t]*(?:\([^)\n]*\))?[ \t]*:?[ \t]*$"
      % (MARK, MARK, DASH, DASH),
      (8747, "**The Grazers (The Slate Herds)**"),
      "A line that holds only a bold span: a bold sub-heading naming the kind described "
      "below it. Read up to the first colon, dash or parenthesis.",
      "Bold lines are also used for section titles.",
      flags="m", stop="section_words", max_words=10),
    P("bold_second", 1, 2, "wide",
      "",
      "markup",
      r"^[ \t]*%s?\*\*[^*\n(:%s]+?(?::[ \t]+|[ \t][%s][ \t]*)(?P<name>[^*\n():%s]+?)[ \t]*\*\*[ \t]*:?[ \t]*$"
      % (MARK, DASH, DASH, DASH),
      (9842, "**The Inhabitants: the Quiet Ones**"),
      "The second part of a bold title line, after a colon or dash.",
      flags="m", stop="section_words", max_words=10),
    P("bold_paren_alias", 2, 2, "wide",
      "",
      "markup",
      r"\*\*[^*\n(]+?[ \t]*\([*%s]*(?P<name>[^)\n]+?)[*%s]*\)[ \t]*:?[ \t]*\*\*"
      r"|\*\*[^*\n(]+?\*\*:?[ \t]*\([*%s]*(?P<name2>[^)\n]{2,60}?)[*%s]*\)" % (OQ, CQ, OQ, CQ),
      (8747, "**The Chitin-Swarms (The Shimmering in the Basins)**"),
      "A second name given in parentheses inside a bold span or right after it.",
      "The parenthesis may hold a role description instead of a second name ('Base "
      "Population / Prey / Engineers of Erosion').",
      max_words=10),
    P("bold_subject", 1, 2, "wide",
      "With 'The' before it the span was a name 14 times of 16 read; without, 6 of 13.",
      "markup",
      r"^[ \t]*%s?\*\*(?:[Tt]he[ \t]+)?(?P<name>%s)\*\*[ \t]+(?=[a-z])" % (MARK, NAME),
      (8203, "**The Crawlers** represent the newest adaptation to life in the"),
      "A capitalised bold span that opens a paragraph and is the subject of its first "
      "sentence.",
      "A bold ordinary noun at the start of a sentence is capitalised too ('**Snakes** "
      "are treated with a wary respect').",
      flags="m", stop="section_words", reject=REJECT_CAPS, max_words=10),
    P("bold_lead", 2, 2, "wide",
      "",
      "markup",
      r"^[ \t]*%s?\*\*(?P<name>[^*\n(:]+?)(?:[ \t]*\([^)\n]*\))?[ \t]*:?[ \t]*\*\*[ \t]*[:%s-][ \t]*\S"
      r"|^[ \t]*%s?\*\*(?P<name2>[^*\n(:]+?)(?:[ \t]*\([^)\n]*\))?[ \t]*:[ \t]*\*\*[ \t]*\S"
      % (MARK, DASH, MARK),
      (12599, "1.  **The Dust-Runners (Base Population / Prey / Engineers of Erosion):**"),
      "A bold span that opens a line or a list item and is followed by a colon or dash "
      "and then its description.",
      "The same position holds attribute labels ('**Form:**', '**Behavior:**'); the "
      "commonest are removed by a stoplist, the rest remain as noise.",
      flags="m", stop="section_words", max_words=10),
    P("bold_inline_cap", 3, 2, "strict",
      "",
      "markup",
      r"(?:(?:(?<=[A-Za-z,;:)%s])|(?<=[A-Za-z)%s][.!?]))[ \t]+|(?<=[%s(]))"
      r"\*\*(?:[Tt]he[ \t]+|[Aa]n?[ \t]+)?(?P<name>%s)(?:['’]s)?\*\*" % (CQ, CQ, DASH, NAME),
      (6483, "Below the dripping pipes and the faint blue halo along the stone ceiling, the **Underheat** sleeps."),
      "A capitalised name set in bold inside a paragraph, after a word of the sentence "
      "or at the start of a later sentence.",
      "Capitalised bold is also used for concepts ('**Flow Continuity**').",
      stop="common_caps", reject=REJECT_CAPS, max_words=10),
    P("bold_inline_lower", 2, 2, "wide",
      "",
      "markup",
      r"(?<=[A-Za-z,;:)])[ \t]+\*\*(?P<name>[a-z]+(?:-[a-z]+)+)\*\*"
      r"|\b(?:[Tt]he|[Aa]n?|[Tt]hese|[Tt]hose)[ \t]+\*\*(?P<name2>[a-z][^*\n]{1,40}?)\*\*",
      (12599, "Its inhabitants are **mechano-fauna**, organisms sculpted by vibration, dust, and the relentless hum of titanic engines"),
      "A lower-case term set in bold inside a sentence, when it is a hyphenated compound "
      "or follows an article: sometimes a coined word for the inhabitants.",
      "Still catches emphasis ('the **hollowness**').",
      max_words=3),

    # ================================================================== italic
    P("italic_cap", 2, 2, "strict",
      "",
      "markup",
      r"(?<![*\w])\*(?:[Tt]he[ \t]+)?(?P<name>%s)\*(?![*\w])" % NAME,
      (18409, "To witness the residents of this bulb-city is to watch shadow-work performed by living origami. They are the *Suturers*."),
      "A capitalised name set in italics.",
      stop="common_caps", reject=REJECT_CAPS, max_words=10),
    P("italic_lower", 2, 2, "wide",
      "",
      "markup",
      r"(?<![*\w])\*(?P<name>[a-z]+(?:-[a-z]+)+)\*(?![*\w])"
      r"|\b(?:[Tt]he|[Aa]n?|[Tt]hese|[Tt]hose)[ \t]+\*(?P<name2>[a-z][^*\n]{1,40}?)\*(?![*\w])",
      (29699, "These are the *curtain-leeches*, though they are not vermin."),
      "A lower-case term set in italics, when it is a hyphenated compound or follows an "
      "article: sometimes a coined name for a kind.",
      "Still catches emphasis.",
      max_words=3),

    # =================================================================== lists
    P("list_head_line", 2, 2, "wide",
      "",
      "list",
      r"^[ \t]*%s(?P<name>[A-Z][^\n.:!?*(,]{1,60}?)[ \t]*(?:\([^)\n]*\))?[ \t]*$" % MARK,
      (15886, "1.  Slurry-Eaters  \n   • A consortium of limestone-digesting bacteria (chief genus: Calciphagea) nests in the still-liquid ribs overhead."),
      "A numbered or bulleted line that holds only a short capitalised phrase: the name "
      "of the kind described under it.",
      "Roman-numbered lines are usually group titles ('I.  The Invisible Majority').",
      flags="m", stop="section_words", max_words=6),
    P("list_num_lead", 1, 2, "wide",
      "",
      "list",
      r"^[ \t]*%s(?P<name>[A-Z][^\n.:!?*()%s]{1,60}?)[ \t]*(?:\([^)\n]*\))?[ \t]*(?::|[%s]| - )[ \t]*\S"
      % (NUM, DASH, DASH),
      (15765, "3. Sluicers – the Moving Ground"),
      "A numbered list item that opens with a short capitalised phrase, then a colon or "
      "dash, then the description.",
      flags="m", stop="section_words", max_words=6),
    P("list_bullet_lead", 1, 2, "wide",
      "Not sampled on its own. As part of the earlier list_head_lead, 2 of 19 bulleted items read were names.",
      "list",
      r"^[ \t]*%s(?P<name>[A-Z][^\n.:!?*()%s]{1,60}?)[ \t]*(?:\([^)\n]*\))?[ \t]*(?::|[%s]| - )[ \t]*\S"
      % (BULLET, DASH, DASH),
      (15842, "• Slate-eaters: chemosynthetic sheets that dissolve basalt"),
      "A bulleted list item that opens with a short capitalised phrase, then a colon or "
      "dash, then the description.",
      "Mostly attribute labels ('Skin:', 'Shelter:', 'Fate:').",
      flags="m", stop="section_words", max_words=6),
    P("paren_quoted_alias", 1, 2, "wide",
      "",
      "frame",
      r"\([^()\n]{0,60}?[%s](?P<name>[^%s\n]{2,40}?)[,.]?[%s][^()\n]{0,30}\)" % (OQ, CQ, CQ),
      (15775, "4.  Bronze-Obsidian Salamanders (“Vault Whelps”)"),
      "A name in quotation marks inside parentheses: the local or colloquial name given "
      "beside a descriptive one.",
      max_words=6),

    # ========================================================== capitalisation
    P("the_cap", 2, 2, "strict",
      "",
      "capitalisation",
      r"\b[Tt]he[ \t]+(?P<name>%s)" % NAME,
      (4117, "The Toneminds are the most immediately noticeable intelligent presence."),
      "'the' followed by a capitalised word or run of words. English does not capitalise "
      "a common noun after 'the', so the capital is the writer marking a name.",
      "Catches names of places and things as well as of beings ('the Khas Plateau', 'the "
      "Flats').",
      stop="common_caps", mask="title_lines", reject=REJECT_CAPS, max_words=10),
    P("a_cap", 2, 2, "strict",
      "",
      "capitalisation",
      r"\b[Aa]n?[ \t]+(?P<name>%s)" % NAME,
      (4117, "A Tonemind can extend its consciousness through the calcified spires"),
      "'a' or 'an' followed by a capitalised word: one member of a named kind.",
      stop="common_caps", mask="title_lines", reject=REJECT_CAPS, max_words=10),
    P("cap_mid", 2, 2, "strict",
      "",
      "capitalisation",
      r"(?<![A-Za-z'’-])(?!(?:the|a|an)[ ])[a-z][a-z'’-]*[,;]?[ ](?P<name>%s)" % NAME,
      (13977, "they are in constant contact with the legs of neighboring Tarse"),
      "A capitalised word or run of words in the middle of a sentence, with no article "
      "before it.",
      "Also catches ordinary proper nouns and capitalised concepts. Most hits are the "
      "name of the place, not of a being.",
      stop="common_caps", mask="title_lines", reject=REJECT_CAPS, max_words=10),
    P("or_alias", 1, 2, "strict",
      "",
      "capitalisation",
      r",?[ \t]+or(?:,?[ \t]+(?:simply|just|perhaps|sometimes|more[ \t]+often|occasionally|else))?,?"
      r"[ \t]+(?:the[ \t]+)?(?:\*{1,2}|[%s])?(?:[Tt]he[ \t]+)?(?P<name>%s)" % (OQ, NAME),
      (4734, "They are the **Sedimentaries**, or the **Hold-Still**, or simply **Those Who Did Not Flee When t"),
      "'or X', 'or simply the X': one more name in a run of alternative names.",
      stop="common_caps", mask="title_lines", reject=REJECT_CAPS, max_words=10),
    P("binomial", 2, 2, "wide",
      "",
      "frame",
      r"(?:(?<!\*)\*|\()(?P<name>[A-Z][a-z]{3,}[ \t]+[a-z]{2,}"
      r"(?:us|is|um|a|ae|i|ans|ens|ox|or|es|as|on|yx|ix|ex))(?=\*(?!\*)|\)|,)",
      (3853, "**5. The Sporeling Swarms (Mycospira lucens):**"),
      "A two-word Latin-style species name, in italics or parentheses.",
      "Real species names match too ('Sturnus vulgaris'). The second word must have a "
      "Latin ending (-us, -is, -um, -a, -ae, -i, -ans, -ens \u2026).",
      max_words=2),

    # ================================================================== frames
    P("frame_call_marked", 2, 2, "strict",
      "",
      "frame",
      CALL + r"(?:,[^,\n]{1,60},)?(?:[ \t]+(?:simply|only|just|merely))?"
      r"[ \t]+(?:the[ \t]+|a[ \t]+|an[ \t]+)?(?:\*{1,2}|[%s'‘])?(?:[Tt]he[ \t]+)?(?:\*{1,2})?(?P<name>%s)" % (OQ, NAME),
      (2296, "This being, which we might call the Nexus, has no fixed shape or size."),
      "A verb of naming (call, name, known as, refer to as, dub, term) followed by a "
      "capitalised name.",
      stop="common_caps", reject=REJECT_CAPS, max_words=10),
    P("frame_call_quoted", 1, 1, "strict",
      "",
      "frame",
      CALL + r"(?:[ \t]+(?:simply|only|just|merely))?[ \t]+(?:the[ \t]+|a[ \t]+|an[ \t]+)?"
      r"(?:\*{1,2}|[%s‘])(?P<name>[a-z][^*%s’\n]{1,50}?)(?:\*{1,2}|[%s’])" % (OQ, CQ, CQ),
      (14545, "Some of them report what they call *listening dreams*"),
      "A verb of naming followed by a lower-case term in italics, bold or quotation "
      "marks.",
      "Names things and practices of the inhabitants more often than the inhabitants.",
      max_words=6),
    P("frame_means", 1, 2, "wide",
      "",
      "frame",
      r"\b(?:means?|meaning|meant|translates?|translated|translation)(?:[ \t]+[a-z]+){0,5}?"
      r"[ \t,:—]*(?:\*{1,2}|[%s‘])(?P<name>[^*%s’\n]{3,80}?)[,.]?(?:\*{1,2}|[%s’])" % (OQ, CQ, CQ),
      (31747, "Among themselves they use a word that means roughly *those on shift*."),
      "A name given by its meaning: 'a word that means roughly *those on shift*', "
      "'translates as “those who are inside”'.",
      "Also catches glosses of words that are not names.",
      max_words=14),
    P("there_are_the", 1, 1, "wide",
      "",
      "frame",
      r"\bThere[ \t]+(?:are|is)[ \t]+(?:also[ \t]+)?the[ \t]+"
      r"(?P<name>[a-z][a-z-]*(?:[ \t]+[a-z][a-z-]*){0,3}?)"
      r"(?=[.,;:%s]|[ \t]+(?:who|that|which|and)\b|[ \t]+\()" % DASH,
      (28450, "There are the stitchers. They are small and tireless and everywhere."),
      "'There are the X': a lower-case kind introduced by what it does.",
      "Half the hits introduce ordinary things ('There is the wind outside').",
      max_words=4),
    P("the_hyphen_agent", 1, 2, "strict",
      "",
      "frame",
      r"\b[Tt]he[ \t]+(?P<name>[a-z]+(?:-[a-z]+)*-%s)\b(?![ \t]*-)" % AGENT,
      (14545, "The first ones you see are usually the conduit-scrapers — small figures in waxed canvas smocks"),
      "'the' followed by a lower-case hyphenated compound whose last element is an agent "
      "or creature word (-ers, -folk, -kin, -born, -things, -moths …): a coined name for "
      "a kind, written without a capital.",
      "The list of last elements is hand-made and will grow.",
      max_words=3),
    P("the_hyphen_compound", 2, 2, "wide",
      "",
      "frame",
      r"\b[Tt]he[ \t]+(?!(?:[a-z]+-)+%s\b)(?:(?P<name>[a-z]+(?:-[a-z]+)*-[a-z]+s)\b(?![ \t]*-)"
      r"|(?P<name2>[a-z]+(?:-[a-z]+)+)"
      r"(?=[ \t]*(?:[.,;:%s]|$)|[ \t]+(?:are|is|were|was|have|has|do|does|who|that|which|"
      r"live|lives|move|moves|come|comes|will|can|may|must|never|always|also|still|only)\b))"
      % (AGENT, DASH),
      (29699, "Higher up, where the invisible edge of the field shears against the seventy-mile-an-hour gales of the upper troposphere, the gas-bladders live out a violent, rhythmic life."),
      "'the' followed by a lower-case hyphenated compound that does not end in an agent "
      "word: a plural compound anywhere, a singular one at the end of its noun phrase.",
      "Mostly names of things in the place ('the rust-farms', 'the root-mat') and "
      "ordinary compounds ('the water-stains').",
      flags="m", max_words=4),
    P("dash_appositive", 1, 2, "wide",
      "",
      "frame",
      r"—[ \t]*the[ \t]+(?P<name>[a-z][a-z-]+(?:[ \t]+[a-z][a-z-]+)?)[ \t]*—",
      (29699, "The silica-backed crawlers—the chitons—are more than grazers; they are masonry tools with guts."),
      "A short lower-case noun phrase set between dashes after a description: the name "
      "that the description was leading to.",
      "Seen once by eye; written to find out how common it is.",
      max_words=2),
    P("pronoun_is_the", 1, 1, "wide",
      "",
      "frame",
      r"\b(?:They|These|Those)[ \t]+are[ \t]+the[ \t]+"
      r"(?P<name>[a-z][a-z-]*(?:[ \t]+[a-z][a-z-]*){0,2}?)(?=[.,;:%s])"
      r"|\b(?:She|He|It|This)[ \t]+is[ \t]+the[ \t]+"
      r"(?P<name2>[a-z][a-z-]*(?:[ \t]+[a-z][a-z-]*){0,2}?)(?=[.,;:%s])" % (DASH, DASH),
      (27073, "She is the caretaker.\n\nNot because anyone appointed her."),
      "'They are the X.' / 'She is the X.': a short lower-case designation given as an "
      "identity.",
      "Short predicates of any kind match ('It is the heat'). A role word used in place "
      "of a name is the target.",
      max_words=3),

    # ============================================================= descriptive
    P("those_who_lower", 1, 1, "wide",
      "",
      "descriptive",
      r"\b(?P<name>(?:[Tt]hose|[Tt]he[ \t]+ones?)[ \t]+(?:who|that|which)[ \t]+[^.,;:\n%s()]{3,70})" % DASH,
      (9667, "the ones who keep the floor clean of its own dead"),
      "'those who …' / 'the ones who …' in lower case: a description standing where a "
      "name would stand.",
      "Most uses are ordinary relative clauses ('those who enter'). The capitalised form "
      "('The Ones Who Wait') is caught by the capitalisation patterns.",
      max_words=14),

    # =============================================================== statement
    P("anti_name", 1, 1, "wide",
      "",
      "statement",
      r"[^.!?\n]*\b(?:no[ \t]+names?|nameless|unnamed|un-?nam(?:e)?able|"
      r"without[ \t]+(?:a[ \t]+)?names?|never[ \t]+(?:been[ \t]+)?named|"
      r"rather[ \t]+than[ \t]+names?|not[ \t]+(?:a|its|their|her|his)[ \t]+(?:real[ \t]+|true[ \t]+)?name|"
      r"no[ \t]+word[ \t]+for[ \t]+(?:itself|themselves|what[ \t]+(?:it|they)))\b[^.!?\n]*[.!?]?",
      (4823, "It has no name for itself, no border, no flag except the constant temperature of its own breath."),
      "A sentence saying that the being has no name, refuses one, or is known by "
      "something other than a name.",
      "The sentence may be about something other than the inhabitants ('colors that have "
      "no names').",
      yields="statement", flags="i"),
]
