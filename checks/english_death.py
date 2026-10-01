"""A bounded English double-death regression, not a general tense validator."""

from __future__ import annotations

import re
import unicodedata
from itertools import pairwise

FINITE_DIE = re.compile(
    r"(?:(?:i|you|he|she|it|we|they) )?"
    r"(?:die|dies|died|(?:have|has|had) died|(?:will|shall) die)"
)


def check_death_auxiliaries(doc: dict, layer: dict) -> list[str]:
    """Reject adjacent direct dead + dies glosses for mortuus/morior + sum.

    Correct dead/is or was/dead state readings are deliberately accepted.
    Shared/zero providers, nonadjacent constructions, other dying synonyms
    and arbitrary compound-tense semantics need their own contextual review.
    """
    if (layer.get("language") or layer.get("lang")) != "en":
        return []
    errors: list[str] = []
    localized = layer.get("segments") or {}
    glosses = layer.get("words") or {}

    def text(word: dict) -> str:
        value = (glosses.get(word["id"]) or {}).get("gloss")
        if not isinstance(value, str):
            return ""
        normalized = unicodedata.normalize("NFKC", value).casefold()
        return " ".join(normalized.split()).strip(' .,:;!?"“”‘’()[]')

    for segment in doc.get("segments") or []:
        members = {
            wid
            for group in (localized.get(segment.get("id")) or {}).get("alignments") or []
            for wid in group.get("words") or []
        }
        for left, right in pairwise(segment.get("words") or []):
            if (
                left["id"] in members
                or right["id"] in members
                or left.get("post", "").strip()
                or right.get("pre", "").strip()
            ):
                continue
            for dead, auxiliary in ((left, right), (right, left)):
                morph = dead.get("morph") or {}
                finite = auxiliary.get("morph") or {}
                death_form = (dead.get("lemma") == "mortuus" and morph.get("pos") == "adj") or (
                    dead.get("lemma") == "morior"
                    and morph.get("pos") == "verb"
                    and morph.get("mood") == "part"
                    and morph.get("tense") == "perf"
                )
                if (
                    death_form
                    and morph.get("case") == "nom"
                    and auxiliary.get("lemma") == "sum"
                    and finite.get("pos") == "verb"
                    and finite.get("mood") in {"ind", "subj"}
                    and text(dead) == "dead"
                    and FINITE_DIE.fullmatch(text(auxiliary))
                ):
                    errors.append(
                        f"{doc['id']}:{left['id']}–{right['id']}: English glosses "
                        "duplicate the death predicate as 'dead' plus a finite form of 'die'; "
                        "render the compound once or retain a coherent state construction"
                    )
    return errors
