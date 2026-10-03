"""Pattern registry for the Atlas names study.

This file is the source of truth for every active pattern. The database and the site
are rebuilt from it. When a pattern is changed it keeps its id and gets a higher
`version`; the earlier form is appended to patterns_retired.py with the reason.

Each pattern is a dict:

  id        short stable name
  version   integer, bumped on any change of the regex or its conditions
  round     the round in which this version was written
  added     date
  remark    optional remark on what the read samples showed beyond the counts
  yields    'name'       the captured group `name` (or `name2`) is a name candidate
            'statement'  the hit is a statement about naming (e.g. "it has no name")
            'namer'      the capture says who gives the name; not a name
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
  position  'title' for a pattern that reads a title line or a label at the head of a line
            (set automatically for the patterns that have `title`)
  title, body  for title patterns: which kind of title line (a key of TITLE_REGEX) and what
            happens to the captured string in the rest of the text (see TITLE_REGEX)
  labels_from  optional list of earlier pattern ids: a verdict given on a hit of one of
            those patterns applies to this pattern where both captured the same string at
            the same place (used when a pattern is split into parts)
  min_occ   optional: the captured string must occur at least this many times in the
            text (any case, as a whole word or phrase), counting the hit itself
  max_df    optional: a one-word capture is dropped when the word occurs in more than
            this share of all texts (it is ordinary vocabulary, not a coined name)
  origin    {'text': id, 'excerpt': the passage in which the form was first seen}
  what      one or two sentences: what form of naming this is
  note      what a reader should know about its weaknesses

All patterns were written by reading texts. `origin` records where each form was seen.

A pattern has no class. Its precision (the share of names among the hits of it that were
read by eye) is computed from labels.jsonl by extract.py; a name caught in a text gets as
its score the highest precision among the patterns that caught it there. Until round 3
patterns were sorted into 'strict' (precision of 80% or more) and 'wide'; the entries in
patterns_retired.py still carry that field.
"""
from patterns_retired import RETIRED  # noqa: F401  (re-exported for the extractor)

# ---------------------------------------------------------------------------
# building blocks

# A capitalised word, possibly hyphenated: Toneminds, Seep-Minds, Toe-Shear, Myco-Weave
CAPW = r"[A-Z][A-Za-zÀ-ɏ'’]*(?:-[A-Za-z][A-Za-zÀ-ɏ'’]*)*"
# Small words that may sit inside a capitalised name: Geometers of the Gyre,
# The One Who Waits at the Center, the House That Drinks
LINK = (r"(?:of|in|at|on|for|with|under|beneath|between|beyond|within|"
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

# The three kinds of title line. A title pattern names one of them in `title` and says in
# `body` what must happen to the captured string in the rest of the text:
#   'only'   it does not occur again                      (a title that only heads a section)
#   'lower'  it occurs again, but never with these capitals   ("The Listeners" ... "the listeners")
#   'cased'  it occurs again with the same capitals        ("Veilstalkers" ... "Veilstalkers are")
# Every title line falls under exactly one of the three.
TITLE_REGEX = {
    "heading": r"^#{1,6}[ \t]+%s?\**(?P<name>[^\n#*(:%s]+?)\**[ \t]*(?:[(:%s].*)?$" % (MARK, DASH, DASH),
    "bold_line": (r"^[ \t]*%s?\*\*%s?(?P<name>[^*\n(:%s]+?)(?:[ \t]*[(:%s][^*\n]*)?\*\*[ \t]*(?:\([^)\n]*\))?[ \t]*:?[ \t]*$"
                  % (MARK, MARK, DASH, DASH)),
    "list_head": (r"^[ \t]*%s(?P<name>[A-Z][^\n.:!?*(,]{1,60}?)[ \t]*(?:\([^)\n]*\))?[ \t]*$"
                  r"|^[ \t]*%s(?P<name2>[A-Z][^\n.:!?*()%s]{1,60}?)[ \t]*(?:\([^)\n]*\))?[ \t]*(?::|[%s]| - )[ \t]*\S"
                  % (MARK, NUM, DASH, DASH)),
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
    # Nouns ending in -ers or -ors that are not names of agents.
    "not_agents": """
        corners louvers boulders corridors flowers floors shelters antlers towers chambers
        rivers waters layers fingers feathers shoulders clusters timbers embers numbers
        letters members borders others colors colours doors ladders gutters girders
        rafters shutters cylinders boilers rotors motors sensors reactors generators
        elevators conveyors mirrors anchors vapors vapours odors odours tremors errors
        interiors exteriors centers centres meters metres quarters papers fibers fibres
        characters matters manners orders powers showers summers winters hours
        containers filters transformers condensers radiators propellers rollers hammers
        cinders spiders otters beavers lobsters oysters vipers plovers tigers badgers
        roosters tiers
        """.split(),
}


def P(id, version, round, remark, family, regex, origin, what, note="",
      yields="name", flags="", added="2026-10-02", **kw):
    d = dict(id=id, version=version, round=round, added=added,
             remark=remark, yields=yields, family=family, regex=regex, flags=flags,
             origin=dict(text=origin[0], excerpt=origin[1]), what=what, note=note)
    d.update(kw)
    return d


PATTERNS = [
    # ================================================================ headings
    P("heading_second", 1, 2,
      "",
      "heading",
      r"^#{1,6}[ \t]+[^\n(:%s]*?(?::[ \t]+|[ \t][%s][ \t]*|\()[*%s]*(?P<name>[^\n#*():%s%s]+?)[*%s]*\)?[ \t]*\**[ \t]*$"
      % (DASH, DASH, OQ, DASH, CQ, CQ),
      (30066, "### The Leather-Crabs: The Black Tide"),
      "The second part of a heading, after a colon or dash or inside parentheses: a "
      "second name for the same kind.",
      "The second part is as often a description ('the unseen citizens that make "
      "everything possible').",
      flags="m", stop="section_words", max_words=10, position="title"),

    # ==================================================================== bold
    P("bold_second", 1, 2,
      "",
      "markup",
      r"^[ \t]*%s?\*\*[^*\n(:%s]+?(?::[ \t]+|[ \t][%s][ \t]*)(?P<name>[^*\n():%s]+?)[ \t]*\*\*[ \t]*:?[ \t]*$"
      % (MARK, DASH, DASH, DASH),
      (9842, "**The Inhabitants: the Quiet Ones**"),
      "The second part of a bold title line, after a colon or dash.",
      flags="m", stop="section_words", max_words=10, position="title"),
    P("bold_paren_alias", 2, 2,
      "",
      "markup",
      r"\*\*[^*\n(]+?[ \t]*\([*%s]*(?P<name>[^)\n]+?)[*%s]*\)[ \t]*:?[ \t]*\*\*"
      r"|\*\*[^*\n(]+?\*\*:?[ \t]*\([*%s]*(?P<name2>[^)\n]{2,60}?)[*%s]*\)" % (OQ, CQ, OQ, CQ),
      (8747, "**The Chitin-Swarms (The Shimmering in the Basins)**"),
      "A second name given in parentheses inside a bold span or right after it.",
      "The parenthesis may hold a role description instead of a second name ('Base "
      "Population / Prey / Engineers of Erosion').",
      max_words=10),
    P("bold_subject", 2, 3,
      "With 'The' before it the span was a name 14 times of 16 read; without, 6 of 13.",
      "markup",
      r"^[ \t]*%s?\*\*(?:[Tt]he[ \t]+)?(?P<name>%s)\*\*[ \t]+(?=[a-z])" % (MARK, NAME),
      (8203, "**The Crawlers** represent the newest adaptation to life in the"),
      "A capitalised bold span that opens a paragraph and is the subject of its first "
      "sentence.",
      "A bold ordinary noun at the start of a sentence is capitalised too ('**Snakes** "
      "are treated with a wary respect').",
      flags="m", stop="section_words", reject=REJECT_CAPS, max_words=10),
    P("bold_lead", 2, 2,
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
      flags="m", stop="section_words", max_words=10, position="title"),
    P("bold_inline_cap", 4, 3,
      "",
      "markup",
      r"(?:(?:(?<=[A-Za-z,;:)%s])|(?<=[A-Za-z)%s][.!?]))[ \t]+|(?<=[%s(]))"
      r"\*\*(?:[Tt]he[ \t]+|[Aa]n?[ \t]+)?(?P<name>%s)(?:['’]s)?\*\*" % (CQ, CQ, DASH, NAME),
      (6483, "Below the dripping pipes and the faint blue halo along the stone ceiling, the **Underheat** sleeps."),
      "A capitalised name set in bold inside a paragraph, after a word of the sentence "
      "or at the start of a later sentence.",
      "Capitalised bold is also used for concepts ('**Flow Continuity**').",
      stop="common_caps", reject=REJECT_CAPS, max_words=10),
    P("bold_inline_lower", 3, 6,
      "",
      "markup",
      r"(?:(?<=[A-Za-z,;:)])[ \t]+|(?<=[%s]))\*\*(?P<name>[a-z]+(?:-[a-z]+)+)\*\*"
      r"|\b(?:[Tt]he|[Aa]n?|[Tt]hese|[Tt]hose)[ \t]+\*\*(?P<name2>[a-z][^*\n]{1,40}?)\*\*" % DASH,
      (12599, "Its inhabitants are **mechano-fauna**, organisms sculpted by vibration, dust, and the relentless hum of titanic engines"),
      "A lower-case term set in bold inside a sentence, when it is a hyphenated compound "
      "or follows an article: sometimes a coined word for the inhabitants.",
      "Still catches emphasis ('the **hollowness**').",
      max_words=3),

    # ================================================================== italic
    P("italic_cap", 3, 3,
      "",
      "markup",
      r"(?<![*\w])\*(?:[Tt]he[ \t]+)?(?P<name>%s)\*(?![*\w])" % NAME,
      (18409, "To witness the residents of this bulb-city is to watch shadow-work performed by living origami. They are the *Suturers*."),
      "A capitalised name set in italics.",
      stop="common_caps", reject=REJECT_CAPS, max_words=10),
    P("italic_lower", 2, 2,
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
    P("list_bullet_lead", 1, 2,
      "Not sampled on its own. As part of the earlier list_head_lead, 2 of 19 bulleted items read were names.",
      "list",
      r"^[ \t]*%s(?P<name>[A-Z][^\n.:!?*()%s]{1,60}?)[ \t]*(?:\([^)\n]*\))?[ \t]*(?::|[%s]| - )[ \t]*\S"
      % (BULLET, DASH, DASH),
      (15842, "• Slate-eaters: chemosynthetic sheets that dissolve basalt"),
      "A bulleted list item that opens with a short capitalised phrase, then a colon or "
      "dash, then the description.",
      "Mostly attribute labels ('Skin:', 'Shelter:', 'Fate:').",
      flags="m", stop="section_words", max_words=6, position="title"),
    P("paren_quoted_alias", 1, 2,
      "",
      "frame",
      r"\([^()\n]{0,60}?[%s](?P<name>[^%s\n]{2,40}?)[,.]?[%s][^()\n]{0,30}\)" % (OQ, CQ, CQ),
      (15775, "4.  Bronze-Obsidian Salamanders (“Vault Whelps”)"),
      "A name in quotation marks inside parentheses: the local or colloquial name given "
      "beside a descriptive one.",
      max_words=6),

    # ========================================================== capitalisation
    P("the_cap", 3, 3,
      "",
      "capitalisation",
      r"\b[Tt]he[ \t]+(?P<name>%s)" % NAME,
      (4117, "The Toneminds are the most immediately noticeable intelligent presence."),
      "'the' followed by a capitalised word or run of words. English does not capitalise "
      "a common noun after 'the', so the capital is the writer marking a name.",
      "Catches names of places and things as well as of beings ('the Khas Plateau', 'the "
      "Flats').",
      stop="common_caps", mask="title_lines", reject=REJECT_CAPS, max_words=10),
    P("a_cap", 3, 3,
      "",
      "capitalisation",
      r"\b[Aa]n?[ \t]+(?P<name>%s)" % NAME,
      (4117, "A Tonemind can extend its consciousness through the calcified spires"),
      "'a' or 'an' followed by a capitalised word: one member of a named kind.",
      stop="common_caps", mask="title_lines", reject=REJECT_CAPS, max_words=10),
    P("cap_mid", 3, 3,
      "",
      "capitalisation",
      r"(?<![A-Za-z'’-])(?!(?:the|a|an)[ ])[a-z][a-z'’-]*[,;]?[ ](?P<name>%s)" % NAME,
      (13977, "they are in constant contact with the legs of neighboring Tarse"),
      "A capitalised word or run of words in the middle of a sentence, with no article "
      "before it.",
      "Also catches ordinary proper nouns and capitalised concepts. Most hits are the "
      "name of the place, not of a being.",
      stop="common_caps", mask="title_lines", reject=REJECT_CAPS, max_words=10),
    P("or_alias", 2, 3,
      "",
      "capitalisation",
      r",?[ \t]+or(?:,?[ \t]+(?:simply|just|perhaps|sometimes|more[ \t]+often|occasionally|else))?,?"
      r"[ \t]+(?:the[ \t]+)?(?:\*{1,2}|[%s])?(?:[Tt]he[ \t]+)?(?P<name>%s)" % (OQ, NAME),
      (4734, "They are the **Sedimentaries**, or the **Hold-Still**, or simply **Those Who Did Not Flee When t"),
      "'or X', 'or simply the X': one more name in a run of alternative names.",
      stop="common_caps", mask="title_lines", reject=REJECT_CAPS, max_words=10),
    P("binomial", 2, 2,
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
    P("frame_call_marked", 3, 3,
      "",
      "frame",
      CALL + r"(?:,[^,\n]{1,60},)?(?:[ \t]+(?:simply|only|just|merely))?"
      r"[ \t]+(?:the[ \t]+|a[ \t]+|an[ \t]+)?(?:\*{1,2}|[%s'‘])?(?:[Tt]he[ \t]+)?(?:\*{1,2})?(?P<name>%s)" % (OQ, NAME),
      (2296, "This being, which we might call the Nexus, has no fixed shape or size."),
      "A verb of naming (call, name, known as, refer to as, dub, term) followed by a "
      "capitalised name.",
      stop="common_caps", reject=REJECT_CAPS, max_words=10),
    P("frame_call_quoted", 1, 1,
      "",
      "frame",
      CALL + r"(?:[ \t]+(?:simply|only|just|merely))?[ \t]+(?:the[ \t]+|a[ \t]+|an[ \t]+)?"
      r"(?:\*{1,2}|[%s‘])(?P<name>[a-z][^*%s’\n]{1,50}?)(?:\*{1,2}|[%s’])" % (OQ, CQ, CQ),
      (14545, "Some of them report what they call *listening dreams*"),
      "A verb of naming followed by a lower-case term in italics, bold or quotation "
      "marks.",
      "Names things and practices of the inhabitants more often than the inhabitants.",
      max_words=6),
    P("frame_means", 1, 2,
      "",
      "frame",
      r"\b(?:means?|meaning|meant|translates?|translated|translation)(?:[ \t]+[a-z]+){0,5}?"
      r"[ \t,:—]*(?:\*{1,2}|[%s‘])(?P<name>[^*%s’\n]{3,80}?)[,.]?(?:\*{1,2}|[%s’])" % (OQ, CQ, CQ),
      (31747, "Among themselves they use a word that means roughly *those on shift*."),
      "A name given by its meaning: 'a word that means roughly *those on shift*', "
      "'translates as “those who are inside”'.",
      "Also catches glosses of words that are not names.",
      max_words=14),
    P("there_are_the", 1, 1,
      "",
      "frame",
      r"\bThere[ \t]+(?:are|is)[ \t]+(?:also[ \t]+)?the[ \t]+"
      r"(?P<name>[a-z][a-z-]*(?:[ \t]+[a-z][a-z-]*){0,3}?)"
      r"(?=[.,;:%s]|[ \t]+(?:who|that|which|and)\b|[ \t]+\()" % DASH,
      (28450, "There are the stitchers. They are small and tireless and everywhere."),
      "'There are the X': a lower-case kind introduced by what it does.",
      "Half the hits introduce ordinary things ('There is the wind outside').",
      max_words=4),
    P("the_hyphen_agent", 1, 2,
      "",
      "frame",
      r"\b[Tt]he[ \t]+(?P<name>[a-z]+(?:-[a-z]+)*-%s)\b(?![ \t]*-)" % AGENT,
      (14545, "The first ones you see are usually the conduit-scrapers — small figures in waxed canvas smocks"),
      "'the' followed by a lower-case hyphenated compound whose last element is an agent "
      "or creature word (-ers, -folk, -kin, -born, -things, -moths …): a coined name for "
      "a kind, written without a capital.",
      "The list of last elements is hand-made and will grow.",
      max_words=3),
    P("the_hyphen_compound", 2, 2,
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
    P("dash_appositive", 1, 2,
      "",
      "frame",
      r"—[ \t]*the[ \t]+(?P<name>[a-z][a-z-]+(?:[ \t]+[a-z][a-z-]+)?)[ \t]*—",
      (29699, "The silica-backed crawlers—the chitons—are more than grazers; they are masonry tools with guts."),
      "A short lower-case noun phrase set between dashes after a description: the name "
      "that the description was leading to.",
      "Seen once by eye; written to find out how common it is.",
      max_words=2),
    P("pronoun_is_the", 1, 1,
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
    P("those_who_lower", 1, 1,
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
    P("anti_name", 2, 3,
      "",
      "statement",
      r"\b(?:no[ \t]+names?|nameless|unnamed|un-?nam(?:e)?able|"
      r"without[ \t]+(?:a[ \t]+)?names?|never[ \t]+(?:been[ \t]+)?named|"
      r"rather[ \t]+than[ \t]+names?|not[ \t]+(?:a|its|their|her|his)[ \t]+(?:real[ \t]+|true[ \t]+)?name|"
      r"no[ \t]+word[ \t]+for[ \t]+(?:itself|themselves|what[ \t]+(?:it|they))|"
      r"not[ \t]+(?:easily[ \t]+|readily[ \t]+)?named|(?:cannot|can't|could[ \t]+not)[ \t]+be[ \t]+named|"
      r"(?:hard|difficult|impossible)[ \t]+to[ \t]+name|resists?[ \t]+(?:naming|names?)|"
      r"answers?[ \t]+to[ \t]+no[ \t]+name|no[ \t]+need[ \t]+(?:for|of)[ \t]+(?:a[ \t]+)?names?)\b",
      (4823, "It has no name for itself, no border, no flag except the constant temperature of its own breath."),
      "A sentence saying that the being has no name, refuses one, cannot be named, or is "
      "known by something other than a name. The regular expression finds the phrase; "
      "the hit is the sentence around it.",
      "The sentence may be about something other than the inhabitants ('colors that have "
      "no names').",
      yields="statement", flags="i"),

    # =========================================== round 3: forms found inside covered texts
    P("quoted_cap", 1, 3, "",
      "frame",
      r"\b(?:[Tt]he|[Tt]hese|[Tt]hose|[Aa]n?|[Tt]heir|[Ii]ts)[ \t]+[%s](?:[Tt]he[ \t]+)?(?P<name>%s)[,.]?[%s]" % (OQ, NAME, CQ),
      (4028, "The kelp is home to a variety of creatures, including the \"Kelp Dwellers,\" small, insect-like beings that live among the fronds"),
      "A capitalised name in quotation marks after an article or 'these': the name is "
      "marked by the quotation marks alone, with no verb of naming.",
      stop="common_caps", reject=REJECT_CAPS, max_words=10),
    P("quoted_cap_bare", 1, 3, "",
      "frame",
      r"(?<![A-Za-z])[%s](?:[Tt]he[ \t]+)?(?P<name>%s)[,.]?[%s]" % (OQ, NAME, CQ),
      (19656, "These \"Strays\" have been absorbed into the factory's logic."),
      "Any capitalised word or run of words that fills a pair of quotation marks.",
      "Also catches one-word quoted speech and quoted labels.",
      stop="common_caps", reject=REJECT_CAPS, max_words=10),
    P("live_the", 1, 3, "",
      "frame",
      r"\b(?:live|lives|dwell|dwells|move|moves|drift|drifts|roam|roams|crawl|crawls|swim|swims|nest|nests|"
      r"lurk|lurks|wait|waits|come|comes|work|works)[ \t]+the[ \t]+"
      r"(?P<name>[a-z][a-z-]+(?:[ \t]+[a-z][a-z-]+)?)(?=[,.:;%s]|[ \t]+(?:who|that|which|and)\b)" % DASH,
      (21439, "Beside them live the rooters, the excavators of hidden damp."),
      "A lower-case kind introduced after a verb of living or moving, with the verb "
      "before its subject: 'Beside them live the rooters'.",
      max_words=2),
    P("the_agent_recurring", 2, 3, "",
      "frame",
      r"\b[Tt]he[ \t]+(?P<name>[a-z]+(?:ers|ors))\b(?![ \t]*-)",
      (21439, "The grazers especially feel inevitable there. Not grass-eaters, but crust-eaters"),
      "'the' followed by one lower-case word ending in -ers or -ors, used at least three "
      "times in the text: a kind named by what it does (the grazers, the listeners, the "
      "tenders).",
      "Words that are common across the corpus are dropped (the others, the waters), and "
      "so is a hand-made list of -ers and -ors nouns that are not agents (the corners, the "
      "flowers). Ordinary agent nouns that recur in one text still match (the workers).",
      stop="not_agents", max_words=1, min_occ=3, max_df=0.15),
    P("the_mod_being", 1, 3, "",
      "descriptive",
      r"(?:^|(?<=[.!?][ ])|(?<=\n))The[ \t]+(?!(?:other|same|only|first|second|third|last|next|few|many|rest|"
      r"remaining|[a-z]+er|[a-z]+est)[ \t])(?P<name>[a-z][a-z-]+[ \t]+(?:beings|ones|folk|people|creatures|"
      r"things|animals|birds|fish|kind))[ \t]+(?=[a-z])",
      (17851, "The fire beings are the embodiment of the intense heat that beats down upon the land mercilessly."),
      "A sentence that begins 'The <word> beings / ones / folk / creatures / birds \u2026': a "
      "kind designated by one describing word and a general word for beings.",
      "A description, not a coined name; kept because some models name their kinds only "
      "this way.",
      flags="m", max_words=2),
    P("hyphen_agent_bare", 1, 3, "",
      "frame",
      r"(?<![A-Za-z-])(?<![Tt]he[ ])(?P<name>[a-z]+(?:-[a-z]+)*-%s)\b(?![ \t]*-)" % AGENT,
      (7437, "cavernous spaces where ambulatory vine-walkers are herded like livestock"),
      "A lower-case hyphenated compound ending in an agent or creature word, with no "
      "'the' directly before it.",
      max_words=1, min_occ=2),
    P("as_known", 1, 3, "",
      "frame",
      r"\b[Tt]he[ \t]+(?P<name>[a-z][a-z-]+(?:[ \t]+[a-z][a-z-]+)?)[ \t]*[%s,(][ \t]*as[ \t]+(?:they|it|she|he)[ \t]+"
      r"(?:are|is|were|was)[ \t]+(?:known|called|named)" % DASH,
      (28299, "The glass-fish\u2014as they are known, though they are not true fish"),
      "'the X, as they are known': a lower-case name followed by a remark that this is "
      "what they are called.",
      max_words=2),
    P("name_talk", 1, 3, "",
      "statement",
      r"\b(?:names?|named|naming|nameless|unnamed|namers?)\b",
      (32085, "Her name is used below the mountain. Up here there is seldom occasion for it."),
      "Any sentence that uses the word 'name': the text is talking about names. Includes "
      "the sentences caught by anti_name. The regular expression finds the word; the hit "
      "is the sentence around it.",
      "Wide by design: a list of places to read, not a finding.",
      yields="statement", flags="i"),

    # ====================================== round 5: title lines, by what the body does next
    P("heading_only", 1, 5, "", "heading", TITLE_REGEX["heading"],
      (21704, "### The Floor That Eats\n\nBut the Singers are not the deepest inhabitants. [...] The fungal floor is the oldest inhabitant."),
      "A Markdown heading whose text does not occur again in the text. It may be a title "
      "given to one inhabitant in place of a name, or the title of a section.",
      "About half of these head a section ('What it wants', 'The Daily Life').",
      flags="m", stop="section_words", max_words=10, title="heading", body="only",
      labels_from=["md_heading", "heading_recurring"], added="2026-10-03"),
    P("heading_again_lower", 1, 5, "", "heading", TITLE_REGEX["heading"],
      (10902, "# The Listeners\n\nThey are not gone. [...] the listeners came to understand that they were either the audience or, more troublingly, an interruption"),
      "A Markdown heading whose text comes back in the body, but only in lower case.",
      flags="m", stop="section_words", max_words=10, max_df=0.15, title="heading", body="lower",
      labels_from=["md_heading", "heading_recurring"], added="2026-10-03"),
    P("heading_again_cased", 1, 5, "", "heading", TITLE_REGEX["heading"],
      (25504, "### 4. **Veilstalkers**\nVeilstalkers are large, quadruped creatures with a thick, shaggy coat"),
      "A Markdown heading whose text comes back in the body with the same capitals: the "
      "text goes on using the title as a name.",
      flags="m", stop="section_words", max_words=10, max_df=0.15, title="heading", body="cased",
      labels_from=["md_heading", "heading_recurring"], added="2026-10-03"),
    P("bold_line_only", 1, 5, "", "markup", TITLE_REGEX["bold_line"],
      (11969, "**The Pale Shape in the Corridor**\n\nThis is the one I keep coming back to. [...] The eel is the city's mouth"),
      "A line that holds only a bold span, whose text does not occur again in the text.",
      "As with headings: a title for an inhabitant, or the title of a section.",
      flags="m", stop="section_words", max_words=10, title="bold_line", body="only",
      labels_from=["bold_line", "bold_line_recurring"], added="2026-10-03"),
    P("bold_line_again_lower", 1, 5, "", "markup", TITLE_REGEX["bold_line"],
      (23300, "**The grazers.**"),
      "A bold title line whose text comes back in the body, but only in lower case.",
      flags="m", stop="section_words", max_words=10, max_df=0.15, title="bold_line", body="lower",
      labels_from=["bold_line", "bold_line_recurring"], added="2026-10-03"),
    P("bold_line_again_cased", 1, 5, "", "markup", TITLE_REGEX["bold_line"],
      (8747, "**The Grazers (The Slate Herds)**"),
      "A bold title line whose text comes back in the body with the same capitals.",
      flags="m", stop="section_words", max_words=10, max_df=0.15, title="bold_line", body="cased",
      labels_from=["bold_line", "bold_line_recurring"], added="2026-10-03"),
    P("list_head_only", 1, 5, "", "list", TITLE_REGEX["list_head"],
      (15886, "1.  Slurry-Eaters  \n   \u2022 A consortium of limestone-digesting bacteria (chief genus: Calciphagea) nests in the still-liquid ribs overhead."),
      "The head of a list item (alone on its line, or numbered and followed by a colon or "
      "dash) whose text does not occur again in the text.",
      flags="m", stop="section_words", max_words=6, title="list_head", body="only",
      labels_from=["list_head_line", "list_num_lead", "list_head_recurring"], added="2026-10-03"),
    P("list_head_again_lower", 1, 5, "", "list", TITLE_REGEX["list_head"],
      (21039, "- The concords: emergent, long-lived superorganisms of sign"),
      "The head of a list item whose text comes back in the body, but only in lower case.",
      flags="m", stop="section_words", max_words=6, max_df=0.15, title="list_head", body="lower",
      labels_from=["list_head_line", "list_num_lead", "list_head_recurring"], added="2026-10-03"),
    P("list_head_again_cased", 1, 5, "", "list", TITLE_REGEX["list_head"],
      (4431, "3.  Blink-shrimp (Aeropenaeus lentus)  \nAlready noticed by every visitor, yet seldom understood. [...] Blink-shrimp graze on those sugars"),
      "The head of a list item whose text comes back in the body with the same capitals.",
      flags="m", stop="section_words", max_words=6, max_df=0.15, title="list_head", body="cased",
      labels_from=["list_head_line", "list_num_lead", "list_head_recurring"], added="2026-10-03"),

    # ================================================== round 6: from recall check 4
    P("there_are_bare", 2, 6, "", "frame",
      r"\bThere[ \t]+(?:are|is)[ \t]+(?:also[ \t]+)?(?!(?:no|the|a|an|other|only|also|some|many|few|several|"
      r"larger|smaller|other|two|three|four|five|six|tall|old|new|more)\b)"
      r"(?P<name>[a-z]+(?:-[a-z]+)+|[a-z]+[ \t]+[a-z]+s)(?=[ \t]+(?:that|which|who)\b|[,:;])",
      (16062, "There are hinge-ferns that open only to count passing dust."),
      "'There are X that \u2026' with a lower-case coined kind and no article: a hyphenated "
      "compound or a two-word plural.",
      max_words=2, added="2026-10-03"),
    P("paren_cap_alias", 1, 6, "", "frame",
      r"(?<=[A-Za-z)*])[ \t]*\((?:[Tt]he[ \t]+)?(?P<name>%s)\)" % NAME,
      (15825, "4. Slate-Meridian Worms (Furrow-Tenants)"),
      "A capitalised run alone inside parentheses, right after a word: a second name "
      "given beside the first.",
      "Also catches parenthesised parameters and glosses written in capitals.",
      stop="common_caps", reject=REJECT_CAPS, max_words=6, added="2026-10-03"),
    P("frame_call_plain", 2, 6, "", "frame",
      r"\b(?:(?:is|are|was|were)[ \t]+called|call(?:s|ed)?[ \t]+(?:it|them|her|him))[ \t]+the[ \t]+"
      r"(?P<name>[a-z][a-z-]*(?:[ \t]+[a-z][a-z-]*)?)(?=[,.;:]|[ \t]+(?:since|because|for|though|although|as|if|and)\b)",
      (23649, "Call it the resident, since no one has gotten close enough, or stayed sane enough in the getting, to ask it what it calls itself."),
      "'is called the X', 'they call it the X': a lower-case designation after a verb of "
      "naming, unmarked by capitals, italics or quotation marks.",
      max_words=2, added="2026-10-03"),
    P("the_pair_second", 1, 6, "", "frame",
      r"\b[Tt]he[ \t]+[a-z]+(?:-[a-z]+)*-%s[ \t]+and[ \t]+(?P<name>[a-z]+(?:-[a-z]+)*-%s)\b" % (AGENT, AGENT),
      (7612, "These are the wire-weavers and spore-harvesters, bodies segmented like abandoned circuit boards"),
      "The second of two hyphenated agent compounds that share one 'the'.",
      max_words=1, added="2026-10-03"),
    P("bold_lead_titlecase", 1, 6, "", "markup",
      r"^[ \t]*%s?\*\*(?P<name>%s[ \t]+%s(?:[ \t]+%s)?)\*\*[ \t]*:[ \t]*\S" % (MARK, CAPW, CAPW, CAPW),
      (25624, "- **Twilight Skimmers**: Sleek and fast, these birds have adapted to the cold, damp air."),
      "A bold lead of two or three capitalised words followed by a colon and a "
      "description: the bestiary form, one entry per kind.",
      "Attribute labels written in capitals match too ('**Size and Shape**' does not, "
      "'**Magnetic Fields**' does).",
      flags="m", stop="section_words", reject=REJECT_CAPS, max_words=3,
      labels_from=["bold_lead"], added="2026-10-03"),
    P("who_names", 1, 6, "", "frame",
      r"\b(?P<name>(?:(?:[Tt]he|[Ii]ts|[Tt]heir|[Oo]ur|[Hh]is|[Hh]er)[ \t]+)?[A-Za-z][a-z]+(?:[ \t]+[a-z]+)?[ \t]+"
      r"(?:might[ \t]+|would[ \t]+|sometimes[ \t]+|simply[ \t]+|still[ \t]+|once[ \t]+)?"
      r"(?:call|calls|called|name|named|names|dubbed|dub|refer[ \t]+to)[ \t]+(?:it|them|her|him|themselves|itself|ourselves|this|these|those|me|us|you))\b"
      r"|(?:called|named|known|dubbed)[ \t]+[^.\n,]{0,40}?[ \t]+by[ \t]+(?P<name2>(?:the[ \t]+)?[a-z]+(?:[ \t]+[a-z]+)?)\b",
      (17195, "They call themselves the **Foundry-Wardens**, though the term is less a title than a description"),
      "Who gives the name: the subject of a verb of naming with its object ('they call "
      "themselves', 'the locals call them', 'we might call it'), or the agent after 'by' "
      "('called the Hollow Choir by the townsfolk'). Not a name; a record of the namer.",
      "A sentence like 'you might call it a shell' matches as well.",
      yields="namer", max_words=6, added="2026-10-03"),
]
