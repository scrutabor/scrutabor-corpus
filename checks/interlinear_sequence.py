"""Interlinear glosses read as one line.

A gloss can be right for its own word and still break the line it is read in.
These checks reject the patterns that are decidable from the Latin analysis and
the glosses alone: the name Holy Spirit split into two English words, English
*not* placed before an auxiliary (a direct gloss of the verb, or the caption of
a group that begins with the verb; *Not* at a sentence start and the archaic
auxiliaries included), and Polish *bowiem* opening a clause. Whether a whole
line reads as grammatical Polish or English otherwise remains editorial review:
*not* before a group whose caption is a bare finite verb, for one, is not
decidable from the glosses.
"""

from __future__ import annotations

import re
from itertools import pairwise

from checks.interlinear import alignment_by_word

ENGLISH_AUXILIARY = re.compile(
    r"^(?:(?:i|you|he|she|it|we|they|there|thou|ye)\s+)?"
    r"(?:will|shall|is|are|was|were|am|have|has|had|do|does|did|can|could|may|might|must|should|would"
    r"|shalt|wilt|canst|couldst|shouldst|wouldst|mayest|mightest|hast|hath|art|wast|wert|dost|doth|didst)\b",
    re.IGNORECASE,
)
CLAUSE_PUNCTUATION = re.compile(r"[.:;?!,]")


def _direct(layer: dict, aligned: dict[str, dict], word_id: str) -> str | None:
    """The word's own gloss; None when an alignment realizes the word."""
    if word_id in aligned:
        return None
    return ((layer.get("words") or {}).get(word_id) or {}).get("gloss")


def check(doc: dict, layer: dict) -> list[str]:
    errors: list[str] = []
    language = layer.get("language") or layer.get("lang") or ""
    aligned = alignment_by_word(layer)
    for segment in doc.get("segments") or []:
        words = segment.get("words") or []
        if language == "en":
            for first, second in pairwise(words):
                one = _direct(layer, aligned, first["id"])
                two = _direct(layer, aligned, second["id"])
                if not one or not two:
                    continue
                if {first.get("lemma"), second.get("lemma")} == {"spiritus", "sanctus"}:
                    spirit, holy = (one, two) if first.get("lemma") == "spiritus" else (two, one)
                    if spirit.endswith("Spirit") and holy == "Holy":
                        errors.append(
                            f"{doc['id']}:{first['id']}-{second['id']}: English glosses "
                            f"{one!r} {two!r} split the name; give Spiritus Sanctus one "
                            "shared gloss such as 'of the Holy Spirit'"
                        )
                if (
                    first.get("lemma") == "non"
                    and one.lower() == "not"
                    and (second.get("morph") or {}).get("pos") == "verb"
                    and ENGLISH_AUXILIARY.match(two)
                ):
                    errors.append(
                        f"{doc['id']}:{first['id']}-{second['id']}: English glosses {one!r} "
                        f"{two!r} put the negation before the auxiliary; align non with "
                        "its verb ('will not be', 'is not')"
                    )
            for first, second in pairwise(words):
                one = _direct(layer, aligned, first["id"])
                group = aligned.get(second["id"])
                if (
                    first.get("lemma") == "non"
                    and one
                    and one.lower() == "not"
                    and group is not None
                    and group["words"][0] == second["id"]
                    and isinstance(group.get("gloss"), str)
                    and ENGLISH_AUXILIARY.match(group["gloss"])
                ):
                    errors.append(
                        f"{doc['id']}:{first['id']}-{second['id']}: English gloss {one!r} stands "
                        f"before the group [{group['gloss']}], which begins with an auxiliary; "
                        "include non in the group ('has not forgotten')"
                    )
        if language == "pl":
            for index, word in enumerate(words):
                gloss = _direct(layer, aligned, word["id"])
                if not gloss or gloss.split()[0].lower() != "bowiem":
                    continue
                previous = words[index - 1] if index else None
                if previous is None or CLAUSE_PUNCTUATION.search(previous.get("post") or ""):
                    errors.append(
                        f"{doc['id']}:{word['id']}: Polish gloss {gloss!r} opens a clause; "
                        "bowiem cannot begin one (albowiem can)"
                    )
    return errors
