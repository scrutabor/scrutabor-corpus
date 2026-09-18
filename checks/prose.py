"""The edition's prose rule, held where the prose is written.

This edition writes no semicolons in its own voice, and it does not hedge. Both
rules were applied by hand across every reader-facing string and then guarded
in the READER APP — which vendors this corpus, so a sweep there runs against a
copy, and only after somebody re-vendors it. A census of unguarded mutations
(2026-08-19) walked the gap: a semicolon planted in an `about` paragraph passed
every check this repository has, and the hedges the rule names reached corpus
prose in neither repository, because the app's sweep never read the words the
corpus writes about a word.

So the rule is checked at the source. What it covers is the prose this edition
writes in its own voice — the introduction, the altar narrative, the note under
a word, and the dictionary's derivatives — in both languages, since a rule
about the edition's register is not a rule about English.

Three things are deliberately out of scope, and each for a reason:

  * **`translation`.** The punctuation belongs to the text being translated.
    Thirty-one verses carry a semicolon, most of them psalm verses whose two
    halves the Latin itself divides, and De profundis is not going to be
    repunctuated to suit a house rule about our own sentences.
  * **`editorial`.** Notes to a reviewer, dropped from the reader edition. The
    rule is about what a reader meets.
  * **Citations.** A title and a locator are bibliographic data, transcribed
    from the work they name, not prose we chose the words of.

The lexicon's `senses` and `note` are already swept for semicolons by
checks/lexicon.py (`check_note_prose`), which also holds a rule of its own
about how a note ends. They are not swept twice here — one defect, one message
— so this module adds what that one does not read: the derivatives, and the
hedges in both.
"""

from __future__ import annotations

import re

# Prose the edition does not write. The two phrases are the ones the rule
# names, and both say "it depends" where a prayer book has to say what happens.
HEDGES = {
    "pl": (r"zależnie od zwyczaju",),
    "en": (r"as the custom is",),
}
# Checked in every language, because a Polish paragraph can carry an English
# hedge translated word for word and the reverse is likelier still.
ALL_HEDGES = tuple(pattern for patterns in HEDGES.values() for pattern in patterns)

# Word help explains the text and names its evidence, not the authority of
# the reader's own editorial decisions. This is a narrow wording check, not
# a semantic contradiction detector. Named source editions remain valid.
EDITORIAL_SELF_REFERENCE = re.compile(
    r"\b(?:this|our) edition(?:['’]s)?\b|"
    r"\bthe edition (?:parses|takes|reads|adopts|interprets|analy[sz]es)\b|"
    r"\b(?:ta|to|nasza|nasze) (?:edycja|wydanie)\b|"
    r"\bwydanie (?:analizuje|czyta|odczytuje|przyjmuje|interpretuje|wiąże)\b",
    re.IGNORECASE,
)
WORD_ID = re.compile(r"\bw\d{3,}\b")


def _word_help(where: str, prose: str, *, plain_note: bool = False) -> list[str]:
    errors = []
    if not isinstance(prose, str):
        return errors
    if match := EDITORIAL_SELF_REFERENCE.search(prose):
        errors.append(
            f"{where}: self-authorizing word help ({match.group()!r}) — "
            "explain the context or name the source, and retain genuine uncertainty"
        )
    # Explanations support linked quoted-form references, validated by lint.py.
    # Notes are plain prose in the reader, so even a quoted id leaks here.
    if plain_note and (match := WORD_ID.search(prose)):
        errors.append(f"{where}: bare word-id {match.group()!r} in plain reader note")
    return errors


def _duplicate_help(where: str, explanation: str, note: str) -> list[str]:
    if (
        isinstance(explanation, str)
        and isinstance(note, str)
        and explanation.strip()
        and " ".join(explanation.casefold().split()) == " ".join(note.casefold().split())
    ):
        return [f"{where}: explanation and note repeat the same text"]
    return []


def _sweep(where: str, prose: str) -> list[str]:
    errors = []
    if not isinstance(prose, str):
        return errors
    if ";" in prose:
        errors.append(
            f"{where}: uses a semicolon — this edition's own prose has none. Use a full "
            f"stop, or an 'and'"
        )
    for hedge in ALL_HEDGES:
        if re.search(hedge, prose, re.IGNORECASE):
            errors.append(
                f"{where}: hedges ({hedge!r}) — say what the book does, or say who decides and when"
            )
    return errors


def check(doc: dict) -> list[str]:
    """One independently stored language layer."""
    errors: list[str] = []
    if isinstance(doc.get("segments"), list):
        # The joined shape remains useful in small unit-test fixtures and for
        # reading old revisions. Current authored files take the branch below.
        tid = doc.get("id", "?")
        for language, about in (doc.get("about") or {}).items():
            errors += _sweep(f"{tid}:about.{language}", about)
        for segment in doc.get("segments") or []:
            segment_id = segment.get("id", "?")
            for language, narrative in (segment.get("narrative") or {}).items():
                errors += _sweep(f"{tid}:{segment_id}.narrative.{language}", narrative)
            for word in segment.get("words") or []:
                for key in ("explanation", "note"):
                    for language, prose in (word.get(key) or {}).items():
                        where = f"{tid}:{word.get('id', '?')}.{key}.{language}"
                        errors += _sweep(where, prose)
                        errors += _word_help(where, prose, plain_note=key == "note")
                for language, explanation in (word.get("explanation") or {}).items():
                    errors += _duplicate_help(
                        f"{tid}:{word.get('id', '?')}.{language}",
                        explanation,
                        (word.get("note") or {}).get(language, ""),
                    )
        return errors
    tid = doc.get("text", "?")
    lang = doc.get("lang") or doc.get("language") or "?"
    errors += _sweep(f"{tid}:about.{lang}", doc.get("about", ""))
    for sid, segment in (doc.get("segments") or {}).items():
        if narrative := segment.get("narrative"):
            errors += _sweep(f"{tid}:{sid}.narrative.{lang}", narrative)
    for wid, word in (doc.get("words") or {}).items():
        for key in ("explanation", "note"):
            if prose := word.get(key):
                where = f"{tid}:{wid}.{key}.{lang}"
                errors += _sweep(where, prose)
                errors += _word_help(where, prose, plain_note=key == "note")
        errors += _duplicate_help(
            f"{tid}:{wid}.{lang}", word.get("explanation", ""), word.get("note", "")
        )
    return errors


def check_lexicon(lex: dict) -> list[str]:
    """One lexicon language file. Semicolons in `senses` and `note` belong to
    checks/lexicon.py and are not repeated here — what is added is the
    derivatives, which no sweep had read, and the hedges."""
    errors: list[str] = []
    lang = lex.get("lang") or lex.get("language") or "?"
    for lemma, entry in sorted((lex.get("entries") or {}).items()):
        for derivative in entry.get("derivatives") or []:
            errors += _sweep(f"lexicon:{lang}:{lemma}: derivative {derivative!r}", derivative)
        for sense in entry.get("senses") or []:
            for hedge in ALL_HEDGES:
                if re.search(hedge, sense, re.IGNORECASE):
                    errors.append(f"lexicon:{lang}:{lemma}: sense hedges ({hedge!r})")
        note = entry.get("note") or ""
        errors += _word_help(f"lexicon:{lang}:{lemma}: note", note, plain_note=True)
        for hedge in ALL_HEDGES:
            if re.search(hedge, note, re.IGNORECASE):
                errors.append(f"lexicon:{lang}:{lemma}: note hedges ({hedge!r})")
    return errors
