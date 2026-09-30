"""Polish negative predicates in explicitly bounded Latin constructions.

This checks local realizations, not general Polish grammar. A nominal
predicate such as niczym + sum can be affirmative. Elliptical shared copulas,
ad nihilum, nihil non and non nihil require their own contextual reading.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator
from itertools import pairwise


def _tokens(value: str) -> list[str]:
    return re.findall(r"[^\W\d_]+", unicodedata.normalize("NFKC", value).casefold())


def _finite(word: dict) -> bool:
    morph = word.get("morph", {})
    return morph.get("pos") == "verb" and morph.get("mood") in {"ind", "subj", "imp"}


def _patterns(words: list[dict]) -> Iterator[tuple[list[dict], bool]]:
    """Yield explicit local predicates and whether sum permits nominal niczym."""
    for i, word in enumerate(words):
        if word.get("lemma") != "nihil":
            continue
        if i and words[i - 1].get("lemma") == "non":
            continue
        rest = words[i:]
        if i >= 2:
            part, aux = words[i - 2 : i]
            morph = part.get("morph", {})
            if (
                part.get("lemma") == "facio"
                and morph.get("mood") == "part"
                and morph.get("tense") == "perf"
                and morph.get("voice") == "pass"
                and morph.get("case") == "nom"
                and morph.get("gender") == "n"
                and aux.get("lemma") == "sum"
                and _finite(aux)
            ):
                yield words[i - 2 : i + 1], False
        if len(rest) > 1 and _finite(rest[1]):
            yield rest[:2], rest[1].get("lemma") == "sum"
        if len(rest) > 1:
            morph = rest[1].get("morph", {})
            if (
                rest[1].get("lemma") == "habeo"
                and morph.get("pos") == "verb"
                and morph.get("mood") == "part"
            ):
                yield rest[:2], False
        if len(rest) > 2:
            middle = rest[1]
            morph = middle.get("morph", {})
            if (
                middle.get("lemma") in {"ego", "vos", "hic"}
                and morph.get("pos") == "pron"
                and morph.get("case") in {"dat", "gen"}
                and _finite(rest[2])
                and rest[2].get("lemma") != "sum"
            ):
                yield rest[:3], False
            if (
                [v.get("lemma") for v in rest[:3]] == ["nihil", "sollicitus", "sum"]
                and middle.get("morph", {}).get("pos") == "adj"
                and _finite(rest[2])
            ):
                yield rest[:3], False
        if (
            len(rest) >= 5
            and [v.get("lemma") for v in rest[:5]] == ["nihil", "enim", "ego", "conscius", "sum"]
            and rest[2].get("morph", {}).get("case") == "dat"
            and _finite(rest[4])
        ):
            yield rest[:5], False


def _realizations(span: list[dict], members: dict, entries: dict) -> list[str] | None:
    ids = {word["id"] for word in span}
    pieces: list[str] = []
    seen: set[tuple[str, ...]] = set()
    for word in span:
        wid = word["id"]
        group = members.get(wid)
        if group:
            key = tuple(group["words"])
            gloss = group.get("gloss")
            if not set(key) <= ids or not isinstance(gloss, str) or not gloss.strip():
                return None
            if key not in seen:
                pieces.append(gloss)
                seen.add(key)
        else:
            gloss = (entries.get(wid) or {}).get("gloss")
            if not isinstance(gloss, str) or not gloss.strip():
                return None
            pieces.append(gloss)
    return pieces


def check_negative_predicates(doc: dict, layer: dict) -> list[str]:
    """Flag a suspect nihil predicate without prescribing extra negation.

    Complete shared realizations are examined once. Missing, zero and wider
    providers are not a semantic pass; the interlinear contract checks their
    structure separately. Tense, lexical meaning and remote scope need review.
    """
    if layer.get("lang") != "pl":
        return []
    errors: list[str] = []
    entries = layer.get("words", {})
    for segment in doc.get("segments", []):
        words = segment.get("words") or []
        groups = (layer.get("segments", {}).get(segment["id"]) or {}).get("alignments", [])
        members = {wid: group for group in groups for wid in group["words"]}
        for span, copula in _patterns(words):
            if any(
                a.get("post", "").strip() or b.get("pre", "").strip() for a, b in pairwise(span)
            ):
                continue
            pieces = _realizations(span, members, entries)
            if pieces is None:
                continue
            tokens = _tokens(" ".join(pieces))
            negatives = set(tokens) & {"nic", "niczego", "niczym"}
            if not negatives or (copula and negatives == {"niczym"}):
                continue
            denied = "nie" in tokens or any(
                token in {"niemający", "niemając", "niemające", "niemająca"} for token in tokens
            )
            if not denied:
                errors.append(
                    f"{doc['id']}:{span[0]['id']}–{span[-1]['id']}: "
                    f"suspect Polish nihil predicate {' / '.join(pieces)!r}; "
                    "verify predicate case, negative concord and local scope"
                )
    return errors
