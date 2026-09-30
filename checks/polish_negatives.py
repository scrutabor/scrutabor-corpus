"""Polish negative predicates in explicitly bounded Latin constructions.

This checks bounded nihil, numquam and nullus realizations, not general Polish grammar. A nominal
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


# Appended to checks/polish_negatives.py; reuses its finite/provider helpers.


def _agrees(modifier: dict, noun: dict, case: str) -> bool:
    left, right = modifier.get("morph", {}), noun.get("morph", {})
    return (
        left.get("pos") == "adj"
        and right.get("pos") == "noun"
        and left.get("case") == right.get("case") == case
        and modifier.get("head") == noun.get("id")
        and all(
            left.get(key) is not None and left[key] == right.get(key)
            for key in ("number", "gender")
        )
    )


def _quantifier_scopes(words: list[dict]) -> Iterator[tuple[list[dict], list[dict], bool]]:
    """Yield only explicit adverb/predicate and agreeing quantifier shapes.

    The scope excludes intervening complements: their negation cannot stand in
    for the governed predicate's negation. An encompassing group is unmeasured.
    Nullius possessives, elliptical copulas and double Latin negatives are not
    interpreted by these patterns.
    """
    for i, word in enumerate(words):
        rest = words[i:]
        if word.get("lemma") not in {"numquam", "nullus"}:
            continue
        if i and words[i - 1].get("lemma") == "non":
            continue
        if word.get("lemma") == "numquam" and word.get("morph", {}).get("pos") == "adv":
            if len(rest) > 1 and _finite(rest[1]):
                yield rest[:2], rest[:2], False
            if len(rest) > 2 and _finite(rest[2]):
                middle = rest[1].get("morph", {})
                if (middle.get("pos") == "noun" and middle.get("case") == "abl") or (
                    middle.get("pos") == "verb"
                    and middle.get("mood") == "inf"
                    and rest[2].get("lemma") == "permitto"
                ):
                    yield rest[:3], [word, rest[2]], False
            if (
                len(rest) > 3
                and rest[1].get("lemma") in {"tuus", "noster"}
                and _agrees(rest[1], rest[2], "abl")
                and _finite(rest[3])
            ):
                yield rest[:4], [word, rest[3]], False
        if word.get("lemma") != "nullus":
            continue
        for verb_index, noun_index in ((1, 2), (2, 3)):
            if len(rest) <= noun_index:
                continue
            if verb_index == 2 and not (
                rest[1].get("morph", {}).get("pos") == "noun"
                and rest[1].get("morph", {}).get("case") == "gen"
            ):
                continue
            if (
                _agrees(word, rest[noun_index], "nom")
                and _finite(rest[verb_index])
                and rest[verb_index].get("lemma") != "sum"
            ):
                yield rest[: noun_index + 1], [word, rest[verb_index]], False
        if (
            len(rest) > 3
            and rest[1].get("lemma") in {"tuus", "noster"}
            and _agrees(word, rest[2], "abl")
            and _agrees(rest[1], rest[2], "abl")
            and _finite(rest[3])
            and rest[3].get("lemma") != "sum"
        ):
            yield rest[:4], [word, rest[3]], False
        # A dative recipient and a present participle, not a genitive possessor
        # or a negative predicate borrowed from the next participial clause.
        if (
            len(rest) >= 5
            and [w.get("lemma") for w in rest[:5]] == ["nullus", "malum", "pro", "malum", "reddo"]
            and word.get("morph", {}).get("case") == "dat"
            and word.get("substantive") is True
            and rest[1].get("morph", {}).get("pos") == "noun"
            and rest[1].get("morph", {}).get("case") == "acc"
            and rest[2].get("morph", {}).get("pos") == "prep"
            and rest[2].get("morph", {}).get("governs") == "abl"
            and rest[2].get("head") == rest[3]["id"]
            and rest[3].get("morph", {}).get("pos") == "noun"
            and rest[3].get("morph", {}).get("case") == "abl"
            and all(
                rest[4].get("morph", {}).get(k) == v
                for k, v in {
                    "pos": "verb",
                    "mood": "part",
                    "tense": "pres",
                    "voice": "act",
                    "case": "nom",
                    "number": "pl",
                    "gender": "m",
                }.items()
            )
        ):
            yield rest[:5], [word, rest[4]], True


def check_quantifier_predicates(doc: dict, layer: dict) -> list[str]:
    """Check bounded numquam/nullus concord, not all negation or government."""
    if layer.get("lang") != "pl":
        return []
    errors: list[str] = []
    entries = layer.get("words", {})
    negative_forms = {
        "nigdy",
        "nikomu",
        "żaden",
        "żadna",
        "żadne",
        "żadni",
        "żadnego",
        "żadnej",
        "żadnemu",
        "żadną",
        "żadnym",
        "żadnymi",
        "żadnych",
    }
    for segment in doc.get("segments", []):
        words = segment.get("words") or []
        groups = (layer.get("segments", {}).get(segment["id"]) or {}).get("alignments", [])
        members = {wid: group for group in groups for wid in group["words"]}
        for window, scope, participle in _quantifier_scopes(words):
            if any(
                a.get("post", "").strip() or b.get("pre", "").strip() for a, b in pairwise(window)
            ):
                continue
            pieces = _realizations(scope, members, entries)
            if pieces is None:
                continue
            tokens = set(_tokens(" ".join(pieces)))
            denied = "nie" in tokens or (participle and "nieodpłacający" in tokens)
            if tokens & negative_forms and not denied:
                errors.append(
                    f"{doc['id']}:{window[0]['id']}–{window[-1]['id']}: "
                    "suspect Polish negative-quantifier predicate; "
                    "verify concord, scope and government"
                )
    return errors
