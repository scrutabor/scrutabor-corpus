"""Agreement and government, checked against the edition's own syntax.

The defect this file exists for is a reading the FORM permits and the SENTENCE
forbids. Neither analyzer can see it: they answer whether a
reading is among the candidates, and 59% of tokens admit several. What settles
such a reading is what the word attaches to, and until schema 0.13.0 the corpus
did not record that.

It does now. Every adjective, numeral and participle carries either

    "head": "wNNN"        the word it must agree with, or
    "substantive": true   it heads its own phrase and agrees with nothing

and every preposition carries a `head` naming the word it governs. Both are
CLAIMS, checked here on every build:

- a modifier matches its head in case, number and gender;
- a preposition's object stands in a case that preposition governs;
- a nominative relative pronoun matches its head verb in number.

`substantive` is data, not a default, because "this adjective is really a noun"
is exactly the kind of quiet assumption that hid *omnibus* = all people among
131 false agreement failures when the sweep was first tried without heads.
"""

from __future__ import annotations

# What each preposition may govern. Two-case prepositions list both; the check
# speaks only when the object stands in neither.
PREP_CASE: dict[str, set[str]] = {
    "ab": {"abl"},
    "de": {"abl"},
    "ex": {"abl"},
    "cum": {"abl"},
    "pro": {"abl"},
    "sine": {"abl"},
    "prae": {"abl"},
    "coram": {"abl"},
    "absque": {"abl"},
    "ad": {"acc"},
    "per": {"acc"},
    "propter": {"acc"},
    "ante": {"acc"},
    "post": {"acc"},
    "apud": {"acc"},
    "inter": {"acc"},
    "supra": {"acc"},
    "circa": {"acc"},
    "contra": {"acc"},
    "secundum": {"acc"},
    "trans": {"acc"},
    "ultra": {"acc"},
    "intra": {"acc"},
    "extra": {"acc"},
    "erga": {"acc"},
    "usque": {"acc"},
    "in": {"abl", "acc"},
    "sub": {"abl", "acc"},
    "super": {"abl", "acc"},
    "subter": {"abl", "acc"},
}

NOMINAL = {"noun", "pron", "adj", "num"}
# Genders that a two- or three-termination form may share with its head. Latin
# adjectives of the third declension are one form for masculine and feminine,
# but the corpus records the head's gender, so no slack is needed here.
MODIFIER_POS = {"adj", "num"}


def is_modifier(word: dict) -> bool:
    m = word["morph"]
    if m.get("pos") in MODIFIER_POS:
        return True
    return m.get("pos") == "verb" and m.get("mood") == "part"


def is_nominal(word: dict) -> bool:
    """Anything a preposition can govern.

    Participles decline, so a preposition may govern one. So may a GERUND,
    which is a verbal noun and takes a case for exactly that reason — *in
    credéndo*, the first in this corpus, arrived with the Advent II epistle
    and was reported as something a preposition could not govern.
    """
    m = word["morph"]
    return m.get("pos") in NOMINAL or (
        m.get("pos") == "verb" and m.get("mood") in ("part", "ger")
    )


def _index(doc: dict) -> dict[str, dict]:
    return {w["id"]: w for s in doc.get("segments", []) for w in (s.get("words") or [])}


def _same_segment(doc: dict) -> dict[str, str]:
    out = {}
    for s in doc.get("segments", []):
        for w in s.get("words") or []:
            out[w["id"]] = s["id"]
    return out


def candidates(segment: dict, word: dict) -> list[dict]:
    """Nominals in this segment that agree with `word` in case, number, gender."""
    m = word["morph"]
    return [
        n
        for n in segment.get("words") or []
        if n["id"] != word["id"]
        and is_nominal(n)
        and n["morph"].get("case") == m.get("case")
        and n["morph"].get("number") == m.get("number")
        and n["morph"].get("gender") == m.get("gender")
    ]


def check(doc: dict) -> list[str]:
    """Return one message per broken claim. Empty means the syntax holds."""
    tid = doc["id"]
    words = _index(doc)
    seg_of = _same_segment(doc)
    errors: list[str] = []

    def fail(word: dict, msg: str) -> None:
        errors.append(f"{tid}:{word['id']} ({word['form']}): {msg}")

    for segment in doc.get("segments", []):
        for word in segment.get("words") or []:
            m = word["morph"]
            head_id = word.get("head")
            substantive = word.get("substantive")

            if head_id is not None:
                if head_id not in words:
                    fail(word, f"head={head_id!r} is not a word of this text")
                    continue
                # A head may stand in another segment. The Canon's sentences
                # run across four and five of them — *Et ex Patre natum* takes
                # its head from the segment before, and *plenum grátiæ* from
                # two before that — because a segment is a unit of LAYOUT, set
                # by how the book breaks lines, and not a unit of syntax.
                if seg_of[head_id] != segment["id"]:
                    pass
                if head_id == word["id"]:
                    fail(word, "head is the word itself")
                    continue
                # Two coordinate modifiers agree with each other BY CONSTRUCTION
                # (*dignum et iustum*, *omnibus Sanctis*), so a pair pointing at
                # each other passes every agreement test and still records
                # nothing: neither word names what the phrase attaches to. 33
                # such pairs had accumulated. A modifier resolves to a nominal
                # that is not itself a dependent modifier, or to a finite verb,
                # or it is `substantive` — never to a sibling.
                if words[head_id].get("head") == word["id"]:
                    other = words[head_id]["form"]
                    fail(word, f"and {other!r} name each other: neither has a head")
                    continue
                if is_modifier(words[head_id]) and words[head_id].get("head") is not None:
                    fail(
                        word,
                        f"modifies {words[head_id]['form']!r}, which is itself a "
                        f"modifier of something else: name that word instead",
                    )
                    continue

            head = words.get(head_id) if head_id else None

            # --- prepositions govern a case -------------------------------
            if m.get("pos") == "prep":
                if substantive:
                    fail(word, "a preposition cannot be substantive")
                if head is None:
                    fail(word, "preposition carries no head naming what it governs")
                    continue
                allowed = PREP_CASE.get(word["lemma"])
                if allowed is None:
                    continue  # a preposition whose government we do not assert
                if not is_nominal(head):
                    fail(word, f"governs {head['form']!r}, which is not a nominal")
                    continue
                # A preposition may DECLARE the case it governs. When it does,
                # that declaration and the object it names must agree — one
                # `in` read `governs: abl` over a `sǽcula` tagged accusative,
                # and nothing compared the two.
                declared = m.get("governs")
                if declared and head["morph"].get("case") != declared:
                    fail(
                        word,
                        f"declares governs={declared!r} but heads {head['form']!r}, "
                        f"which is {head['morph'].get('case')!r}",
                    )
                    continue
                if head["morph"].get("case") not in allowed:
                    fail(
                        word,
                        f"governs {head['form']!r} in the {head['morph'].get('case')}, "
                        f"but takes the {'/'.join(sorted(allowed))}",
                    )
                continue

            # --- agreement with a verb's subject, which is not written -----
            # A predicate complement (Propítius esto, digni efficiámur,
            # súpplices deprecámur) and a nominative relative (qui tollis)
            # agree with a subject the Latin leaves unexpressed. Their head is
            # the finite verb, and the only feature it can settle is number —
            # a verb has no gender to lend.
            # A PARTICIPLE is not a finite verb: used substantively it is a
            # noun (*ómnium circumstántium*, of all those standing round) and
            # takes agreement like one, so it falls through to the rule below.
            if (
                head is not None
                and head["morph"].get("pos") == "verb"
                and head["morph"].get("mood") != "part"
            ):
                if head["morph"].get("number") != m.get("number"):
                    fail(
                        word,
                        f"is {m.get('number')} but agrees with the subject of "
                        f"{head['form']!r}, which is {head['morph'].get('number')}",
                    )
                continue

            # --- modifiers agree with their head --------------------------
            if not is_modifier(word):
                if substantive:
                    fail(word, "only a modifier may be marked substantive")
                if head is not None and word["lemma"] != "qui":
                    fail(word, "carries a head but is not a modifier or a preposition")
                continue

            if substantive and head is not None:
                fail(word, "is marked substantive and also carries a head")
                continue
            if not substantive and head is None:
                # The annotation is COMPLETE as of 2026-08-16: every modifier in
                # the corpus declares what it modifies, or declares that it
                # modifies nothing. A new one that declares neither is a gap in
                # the edition's syntax and fails the build.
                fail(word, "carries neither a head nor substantive: what does it modify?")
                continue
            if substantive or head is None:
                continue
            if not is_nominal(head):
                fail(word, f"modifies {head['form']!r}, which is not a nominal")
                continue
            # A personal pronoun has no grammatical gender in this corpus —
            # `nos`, `tu`, `mihi` carry none — so an adjective agreeing with
            # one (omnes nos, benedícta tu, nobis peténtibus) is checked on
            # case and number alone. Its gender answers to the person meant,
            # which is not a fact about the Latin.
            features: tuple[str, ...] = ("case", "number", "gender")
            # The same slack runs both ways. The corpus records no gender on a
            # modifier whose own form shows none — *meis* over *peccátis et
            # offensiónibus et negligéntiis*, three coordinate nouns of mixed
            # gender — and without this it had been marked `substantive` to
            # dodge the check, which claimed it modified nothing. Binding on
            # case and number states exactly what the two forms state.
            if m.get("gender") is None or (
                head["morph"].get("pos") == "pron" and head["morph"].get("gender") is None
            ):
                features = ("case", "number")
            for feature in features:
                mine, theirs = m.get(feature), head["morph"].get(feature)
                if mine != theirs:
                    fail(
                        word,
                        f"is {feature}={mine!r} but modifies {head['form']!r}, "
                        f"which is {feature}={theirs!r}",
                    )
    return errors


def coverage(doc: dict) -> tuple[int, int]:
    """(declared, total) — how much of this text's syntax is stated as data.

    DECLARED, not verified. A head that names the wrong word counts here
    exactly as a right one does: this measures whether the question was
    answered, never whether the answer is true. It read 1289/1289 on the day
    165 heads were found pointing at a word in another sentence. Anything
    quoting this number owes the word `declared` beside it.
    """
    declared = total = 0
    for segment in doc.get("segments", []):
        for word in segment.get("words") or []:
            m = word["morph"]
            if m.get("pos") == "prep" or is_modifier(word):
                total += 1
                if word.get("head") is not None or word.get("substantive"):
                    declared += 1
    return declared, total
