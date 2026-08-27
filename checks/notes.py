"""A contextual explanation and the structured parse must not disagree.

Most explanations no longer narrate routine grammar. A genuinely useful
explanation may still name a formal ambiguity or a relation to another word,
however, and the text files record the adopted relation as data in `head`.

Nothing compared them, and they had drifted apart in both directions: *ipsa*
tagged feminine under a note reading "neuter plural", *clamántem* headed at
*te* under notes naming *pópulum*, *ímpiis* headed at *viris* under notes
calling it substantival. A reader meets both layers on the same panel.

The claim is only extracted where the prose makes it unambiguously — an
agreement phrase or a government phrase, immediately followed by an id. Explanations
that merely mention another word ("It joins X to Y") assert no relation this
file can check, and are left alone.
"""

from __future__ import annotations

import re

# "agrees with X (wNNN)" — the explanation claims W's head is wNNN.
# An explanation's opening clause can state the parse: "Ablativus po „in"",
# "Nominative plural". That is a claim about THIS word, and the tag beneath it
# is the same claim as data. Three things make a case word NOT such a claim,
# and all three occur: the note may name a case the word GOVERNS ("It governs
# three genitives"), it may name another word first and describe THAT ("
# Viscéribus is read as a plural dative"), or it may name two cases because the
# form is syncretic and then choose ("Spíritus can be nominative or genitive").
# Each of those produced false positives before it was excluded.
CASE_WORDS = {
    "pl": {
        "mianownik": "nom",
        "dopełniacz": "gen",
        "celownik": "dat",
        "biernik": "acc",
        "ablativus": "abl",
        "ablatiwie": "abl",
        "ablatiwem": "abl",
        "wołacz": "voc",
    },
    "en": {
        "nominative": "nom",
        "genitive": "gen",
        "dative": "dat",
        "accusative": "acc",
        "ablative": "abl",
        "vocative": "voc",
    },
}
NUMBER_WORDS = {
    "pl": {
        "liczby mnogiej": "pl",
        "liczbie mnogiej": "pl",
        "liczba mnoga": "pl",
        "liczby pojedynczej": "sg",
        "liczbie pojedynczej": "sg",
        "liczba pojedyncza": "sg",
    },
    "en": {"plural": "pl", "singular": "sg"},
}
MOOD_WORDS = {
    "pl": {
        "tryb rozkazujący": "imp",
        "trybie rozkazującym": "imp",
        "rozkaźnik": "imp",
        "tryb łączący": "subj",
        "trybie łączącym": "subj",
        "bezokolicznik": "inf",
        "imiesłów": "part",
    },
    "en": {"imperative": "imp", "subjunctive": "subj", "infinitive": "inf", "participle": "part"},
}
GOVERNED = re.compile(
    r"rządz\w+|łącz\w+ się z|wymaga|govern\w*|takes? a|takes? the|forma\b|the form\b|"
    r"zarazem|at once|both\b|odczytujemy|is read as",
    re.I,
)
QUOTED = re.compile(r"[„“\"«]([^”\"»]{2,})[”\"»]")
SCRIPTURE = re.compile(r"\b\d+\s*,\s*\d+|\b[A-Z][a-z]{1,3}\s+\d+[:,]\d+")
OPENING = re.compile(r"^([^.;:—]{0,60})")


def _parse_claim(explanation: str, form: str, table: dict) -> str | None:
    """The morphological value the prose claims about its own word, if any."""
    match = OPENING.match(explanation)
    if match is None:
        return None
    opening = match.group(1)
    if GOVERNED.search(opening) or SCRIPTURE.search(opening):
        return None
    low = opening.lower()
    found = [(low.find(k), v) for k, v in table.items() if k in low]
    if not found:
        return None
    at, value = min(found)
    if len({v for pos, v in found if pos == at}) != 1:
        return None
    if len({v for _pos, v in found}) > 1:
        return None  # names two values: a syncretism note, which then chooses
    if any(m.start() < at and m.group(1).lower() != form.lower() for m in QUOTED.finditer(opening)):
        return None  # names another word first, and is describing that one
    return value


AGREES = [
    re.compile(r"[Zz]gadza(?:ją)?\s+się\s+z(?P<rest>[^.]{0,90})"),
    re.compile(r"zgadzając[ye]?\w*\s+się\s+z(?P<rest>[^.]{0,90})"),
    re.compile(r"[Aa]gree(?:s|ing)\s+with(?P<rest>[^.]{0,90})"),
]
ID = re.compile(r"\((w\d{3,})\)")


def _claims(text: str, patterns: list[re.Pattern]) -> list[set[str]]:
    """One set per agreement clause: every word id that clause names.

    A note may name more than one, and truthfully — *sperántibus* agrees with
    `Nobis` AND `fámulis`, which stand in apposition. The data records one of
    them, so the check asks only that the recorded head be among those named.
    """
    out = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            named = {m.group(1) for m in ID.finditer(match.group("rest"))}
            if named:
                out.append(named)
    return out


def check(doc: dict, gloss: dict) -> list[str]:
    """One message per place where the prose and the data disagree."""
    from checks.syntax import is_modifier

    words = {w["id"]: w for s in doc.get("segments", []) for w in (s.get("words") or [])}
    lang = gloss.get("lang", "?")
    errors: list[str] = []
    for wid, entry in (gloss.get("words") or {}).items():
        explanation = entry.get("explanation")
        word = words.get(wid)
        if not explanation or word is None or not is_modifier(word):
            continue

        for named in _claims(explanation, AGREES):
            named = {c for c in named if c in words}
            if not named or word.get("head") in named:
                continue
            shown = " / ".join(f"{words[c]['form']!r} ({c})" for c in sorted(named))
            if word.get("substantive"):
                errors.append(
                    f"{doc['id']}:{wid} ({word['form']}): the {lang} explanation says it agrees "
                    f"with {shown}, but the word is marked `substantive`, which claims "
                    f"it agrees with nothing expressed"
                )
            else:
                errors.append(
                    f"{doc['id']}:{wid} ({word['form']}): the {lang} explanation says it agrees "
                    f"with {shown}, but head={word.get('head')!r}"
                )

    # The parse an explanation states about its own word, against the tag beneath it.
    # This reads every word, not only modifiers: a noun's prose states its case
    # as readily as an adjective's.
    for wid, entry in (gloss.get("words") or {}).items():
        explanation = entry.get("explanation")
        word = words.get(wid)
        if not explanation or word is None:
            continue
        for label, table, field in (
            ("case", CASE_WORDS, "case"),
            ("number", NUMBER_WORDS, "number"),
            ("mood", MOOD_WORDS, "mood"),
        ):
            claimed = _parse_claim(explanation, word["form"], table.get(lang, {}))
            actual = word["morph"].get(field)
            if claimed and actual and claimed != actual:
                errors.append(
                    f"{doc['id']}:{wid} ({word['form']}): the {lang} explanation calls it "
                    f"{label}={claimed!r}, but the tag says {actual!r}"
                )

    return errors
