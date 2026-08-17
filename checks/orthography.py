"""One edition, one spelling — American, for a United States and Canada
audience (PLAYBOOK, owner 2026-08-17).

The question was first settled the wrong way, by counting forms inside the
corpus, which says nothing about who reads it. Having been settled properly it
should not drift back, and it drifts easily: a British form arrived in the
lexicon under `centrum` and another under `formo` after the whole English layer
had supposedly been swept, because the first sweep's word list was short.

WHAT IS QUOTED IS NOT SWEPT. A verse carrying a `translation_citation` is a
claim about what a source says, and five of them quote the Thesaurus Precum
Latinarum with its own spelling. A reader meets *Vessel of honour* in a verse
above a gloss reading *honor*, which is the same rule as *thee* standing in a
Douay verse above a modern gloss.
"""

from __future__ import annotations

import re

# British spelling against the American form this edition uses. Kept as data so
# that the next form somebody meets is one line, not a new condition.
BRITISH = {
    "honour": "honor",
    "favour": "favor",
    "armour": "armor",
    "saviour": "savior",
    "splendour": "splendor",
    "colour": "color",
    "neighbour": "neighbor",
    "labour": "labor",
    "vigour": "vigor",
    "succour": "succor",
    "odour": "odor",
    "valour": "valor",
    "ardour": "ardor",
    "clamour": "clamor",
    "fervour": "fervor",
    "marvellous": "marvelous",
    "counsellor": "counselor",
    "traveller": "traveler",
    "offence": "offense",
    "defence": "defense",
    "pretence": "pretense",
    "centre": "center",
    "theatre": "theater",
    "metre": "meter",
    "fibre": "fiber",
    "sombre": "somber",
    "spectre": "specter",
    "sceptre": "scepter",
    "catalogue": "catalog",
    "dialogue": "dialog",
    "analyse": "analyze",
    "organise": "organize",
    "realise": "realize",
    "recognise": "recognize",
    "enrol": "enroll",
    "instil": "instill",
    "skilful": "skillful",
    "wilful": "willful",
    "fulfil": "fulfill",
    "judgement": "judgment",
    "mould": "mold",
    "smoulder": "smolder",
    "grey": "gray",
    "plough": "plow",
    "licence": "license",
    "practise": "practice",
    "programme": "program",
}
PATTERN = re.compile("|".join(rf"\b{b}\w*\b" for b in sorted(BRITISH)), re.I)


AMERICAN = {v for v in BRITISH.values()}


def _hits(text: str) -> list[str]:
    """British forms in this text.

    A British form can be a prefix of its own American replacement — *enrol*
    inside *enroll*, *instil* inside *instill*, *fulfil* inside *fulfill* — so
    a match is only a hit when it does not itself begin with the American form
    it would be corrected to. Without that test the check fails on the very
    spelling it asks for, which it did on the first run.
    """
    out = []
    for match in PATTERN.finditer(text or ""):
        word = match.group(0)
        low = word.lower()
        if any(low.startswith(a) for a in AMERICAN):
            continue
        out.append(word)
    return out


def check(doc: dict, gloss: dict) -> list[str]:
    """One message per British spelling in the edition's own English."""
    if gloss.get("lang") != "en":
        return []
    errors: list[str] = []

    def report(where: str, text: str) -> None:
        for hit in _hits(text):
            base = hit.lower()
            while base and base not in BRITISH:
                base = base[:-1]
            errors.append(
                f"{doc['id']}:{where}: {hit!r} is British, and this edition writes "
                f"American — {BRITISH.get(base, '?')!r} (PLAYBOOK, orthography)"
            )

    report("about", gloss.get("about") or "")
    for wid, entry in (gloss.get("words") or {}).items():
        report(wid, entry.get("gloss") or "")
        report(f"{wid} note", entry.get("function") or "")
    for sid, segment in (gloss.get("segments") or {}).items():
        report(f"{sid} rubric", segment.get("narrative") or "")
        # a cited verse quotes its source, spelling and all
        if not segment.get("translation_citations"):
            report(f"{sid} verse", segment.get("translation") or "")
    return errors


def check_lexicon(entries: dict) -> list[str]:
    """The same rule over the English lexicon, which has no citations."""
    errors: list[str] = []
    for name, entry in sorted(entries.items()):
        blob = " ".join(
            (entry.get("senses") or [])
            + [entry.get("note") or ""]
            + (entry.get("derivatives") or [])
        )
        for hit in _hits(blob):
            base = hit.lower()
            while base and base not in BRITISH:
                base = base[:-1]
            errors.append(
                f"lexicon:{name}: {hit!r} is British, and this edition writes American "
                f"— {BRITISH.get(base, '?')!r} (PLAYBOOK, orthography)"
            )
    return errors
