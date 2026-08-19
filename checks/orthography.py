"""One edition, one spelling — American, for a United States and Canada
audience (owner, 2026-08-17).

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
    # Found missing by the census of 2026-08-19, which read the table against
    # the words this edition actually writes.
    "worshipper": "worshiper",
    "acknowledgement": "acknowledgment",
    "towards": "toward",
}

# A word, for this purpose, is a run of letters. The declared forms are all
# ASCII, but the prose around them is not — a Latin incipit inside an English
# note has to end a word rather than split one.
WORD = re.compile(r"[^\W\d_]+")

# Longest first, so the most specific declared form is the one that answers.
DECLARED = sorted(BRITISH, key=len, reverse=True)


def _hits(text: str) -> list[tuple[str, str]]:
    """(the word as written, the declared British form it is built on).

    A British form can be a prefix of its own American replacement — *enrol*
    inside *enroll*, *instil* inside *instill*, *fulfil* inside *fulfill* — and
    a word that begins with the American form is then the spelling this edition
    asks for, not a hit. Written as "skip anything beginning with any American
    form", that test silently exempted three of the table's own entries, the
    ones whose American twin is their own PREFIX: `_hits('dialogue')` came back
    empty, and so did catalogue and programme, for as long as they had been
    declared (census, 2026-08-19).

    So the exemption is now the narrow thing it was always meant to be — it
    applies to ONE pair, the pair being tested, and only where that pair's
    American form is the longer of the two. *towards* is caught and *toward*
    is not, from the same rule read the other way round.
    """
    out = []
    for match in WORD.finditer(text or ""):
        word = match.group(0)
        low = word.lower()
        for british in DECLARED:
            if not low.startswith(british):
                continue
            american = BRITISH[british]
            if not (len(american) > len(british) and low.startswith(american)):
                out.append((word, british))
            break
    return out


def check(doc: dict, gloss: dict) -> list[str]:
    """One message per British spelling in the edition's own English."""
    if gloss.get("lang") != "en":
        return []
    errors: list[str] = []

    def report(where: str, text: str) -> None:
        for hit, british in _hits(text):
            errors.append(
                f"{doc['id']}:{where}: {hit!r} is British, and this edition writes "
                f"American — {BRITISH[british]!r}"
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
        for hit, british in _hits(blob):
            errors.append(
                f"lexicon:{name}: {hit!r} is British, and this edition writes American "
                f"— {BRITISH[british]!r}"
            )
    return errors
