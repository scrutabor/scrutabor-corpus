"""Regression checks for reader-visible interlinear gloss corruption."""

from __future__ import annotations

import re

CORRUPT_EXACT = {"Ń", "NIEROZSTRZYGNIĘTE", "UNRESOLVED"}
ENGLISH_CHOICE_LIST = re.compile(r"[,;/]")
CORRUPT_ENGLISH_PLURAL = re.compile(r"\b(?:ageses|taxeses)\b", re.IGNORECASE)


def check(doc: dict, gloss: dict) -> list[str]:
    """Reject known damage and dictionary alternatives exposed as a gloss.

    A word gloss is one contextual editorial choice.  Comma-, semicolon- or
    slash-separated English headwords are dictionary output, not a decision,
    and have no place in the reader layer.
    """
    errors: list[str] = []
    language = gloss.get("lang")
    for word_id, entry in (gloss.get("words") or {}).items():
        text = (entry or {}).get("gloss") or ""
        stripped = text.strip()
        if stripped in CORRUPT_EXACT:
            errors.append(
                f"{doc['id']}:{word_id}: {language} gloss {stripped!r} is a corruption marker"
            )
        if language != "en":
            continue
        if ENGLISH_CHOICE_LIST.search(stripped):
            errors.append(
                f"{doc['id']}:{word_id}: English gloss {stripped!r} reads as a "
                "dictionary choice list; select one contextual rendering"
            )
        if CORRUPT_ENGLISH_PLURAL.search(stripped):
            errors.append(
                f"{doc['id']}:{word_id}: English gloss {stripped!r} contains a "
                "duplicated plural suffix"
            )
    return errors
