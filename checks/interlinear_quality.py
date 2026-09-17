"""Regression checks for reader-visible interlinear gloss corruption."""

from __future__ import annotations

import re

CORRUPT_EXACT = {"Ń", "NIEROZSTRZYGNIĘTE", "UNRESOLVED"}
NONCANONICAL_POLISH_AUXILIARY_MARKERS = {
    "[auxiliary]",
    "[czas posiłkowy]",
    "[pomocnicze]",
}
ENGLISH_CHOICE_LIST = re.compile(r"[,;/]")
CORRUPT_ENGLISH_PLURAL = re.compile(r"\b(?:ageses|taxeses)\b", re.IGNORECASE)
DUPLICATED_FUTURE_AUXILIARY = {
    "pl": re.compile(r"\b(?:jest|są)\s+(?:będzie|będą)\b", re.IGNORECASE),
    "en": re.compile(r"\b(?:is|are)\s+(?:shall|will)\b", re.IGNORECASE),
}


def check(doc: dict, gloss: dict) -> list[str]:
    """Reject known damage and dictionary alternatives exposed as a gloss.

    A word gloss is one contextual editorial choice.  Comma-, semicolon- or
    slash-separated English headwords are dictionary output, not a decision,
    and have no place in the reader layer.
    """
    errors: list[str] = []
    # Authored language layers use ``language``; the in-memory checking view
    # produced by build_reader.layers uses the compatibility key ``lang``.
    # Accept both so the repository gate checks the same bytes as direct unit
    # tests and reader builds.
    language = gloss.get("language") or gloss.get("lang")
    for word_id, entry in (gloss.get("words") or {}).items():
        text = (entry or {}).get("gloss") or ""
        stripped = text.strip()
        if stripped in CORRUPT_EXACT:
            errors.append(
                f"{doc['id']}:{word_id}: {language} gloss {stripped!r} is a corruption marker"
            )
        if language == "pl" and stripped in NONCANONICAL_POLISH_AUXILIARY_MARKERS:
            errors.append(
                f"{doc['id']}:{word_id}: Polish auxiliary marker {stripped!r} is not "
                "canonical; use '[czasownik posiłkowy]'"
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
    words = gloss.get("words") or {}
    pattern = DUPLICATED_FUTURE_AUXILIARY.get(language)
    if pattern:
        for segment in doc.get("segments") or []:
            latin_words = segment.get("words") or []
            for first, second in zip(latin_words, latin_words[1:]):
                morphs = (first.get("morph") or {}, second.get("morph") or {})
                is_future_periphrastic = any(
                    word.get("lemma") == "sum"
                    and morph.get("mood") in {"ind", "subj"}
                    and other_morph.get("mood") == "part"
                    and other_morph.get("tense") == "fut"
                    for word, morph, other_morph in (
                        (first, morphs[0], morphs[1]),
                        (second, morphs[1], morphs[0]),
                    )
                )
                if not is_future_periphrastic:
                    continue
                line = " ".join(
                    str((words.get(word["id"]) or {}).get("gloss") or "").strip()
                    for word in (first, second)
                )
                if pattern.search(line):
                    errors.append(
                        f"{doc['id']}:{first['id']}-{second['id']}: {language} "
                        f"glosses {line!r} duplicate the auxiliary of a Latin future "
                        "periphrastic; assign the tense once and mark or fuse the helper"
                    )
    return errors
