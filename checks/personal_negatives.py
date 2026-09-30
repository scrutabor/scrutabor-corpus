"""Local personal-negative concord and duplicated English subjects.

These checks cover the explicit constructions below, not general grammar.
Missing, zero and wider providers are unmeasured; their structural validity
is checked separately. A predicate in an intervening relative clause cannot
provide the main clause's negation. Predicative nikim is not negative existence.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator
from itertools import pairwise


def _tokens(value: object) -> list[str]:
    if not isinstance(value, str):
        return []
    return re.findall(r"[^\W\d_]+", unicodedata.normalize("NFKC", value).casefold())


def _finite(word: dict) -> bool:
    morph = word.get("morph", {})
    return morph.get("pos") == "verb" and morph.get("mood") in {"ind", "subj", "imp"}


def _matches(word: dict, lemma: str, **features: str) -> bool:
    return word.get("lemma") == lemma and all(
        word.get("morph", {}).get(key) == value for key, value in features.items()
    )


def _patterns(words: list[dict]) -> Iterator[tuple[list[dict], list[dict]]]:
    for i, word in enumerate(words):
        rest = words[i:]
        if word.get("lemma") not in {"nemo", "quis"}:
            continue
        if i and words[i - 1].get("lemma") == "non":
            continue
        if len(rest) > 1 and _finite(rest[1]):
            yield rest[:2], rest[:2]
        if word.get("lemma") != "nemo":
            continue
        if len(rest) > 2 and _finite(rest[2]):
            middle = rest[1]
            if _matches(word, "nemo", case="nom") and (
                _matches(middle, "alius", pos="adj", case="nom")
                or (
                    middle.get("lemma") in {"ego", "vos"}
                    and middle.get("morph", {}).get("pos") == "pron"
                    and middle.get("morph", {}).get("case") == "acc"
                )
            ):
                yield rest[:3], rest[:3]
        if (
            len(rest) > 1
            and _matches(word, "nemo", case="dat")
            and _matches(rest[1], "do", pos="verb", mood="part", tense="pres", voice="act")
        ):
            yield rest[:2], rest[:2]
        # This explicit relative clause is not the main negative predicate.
        if (
            len(rest) >= 7
            and [w.get("lemma") for w in rest[:7]]
            == ["nemo", "vir", "ille", "qui", "voco", "sum", "gusto"]
            and _matches(word, "nemo", case="nom")
            and _matches(rest[1], "vir", case="gen", number="pl")
            and _matches(rest[2], "ille", case="gen", number="pl")
            and _matches(rest[3], "qui", case="nom", number="pl")
            and _matches(
                rest[4],
                "voco",
                mood="part",
                tense="perf",
                voice="pass",
                case="nom",
                number="pl",
            )
            and rest[4].get("head") == rest[3]["id"]
            and _matches(rest[5], "sum", mood="ind", tense="pres", number="pl")
            and _matches(rest[6], "gusto", mood="ind", tense="fut", number="sg")
        ):
            yield rest[:7], [rest[0], rest[6]]


def _unpunctuated(words: list[dict]) -> bool:
    return not any(
        left.get("post", "").strip() or right.get("pre", "").strip()
        for left, right in pairwise(words)
    )


def _bounded(window: list[dict], scope: list[dict]) -> bool:
    if len(window) == 7 and len(scope) == 2:
        for i, (left, right) in enumerate(pairwise(window)):
            if right.get("pre", "").strip():
                return False
            punctuation = left.get("post", "").strip()
            if punctuation and not (i in {2, 5} and punctuation == ","):
                return False
        return True
    return _unpunctuated(window)


def _realizations(scope: list[dict], members: dict, entries: dict) -> list[str] | None:
    ids = {word["id"] for word in scope}
    seen: set[tuple[str, ...]] = set()
    pieces: list[str] = []
    for word in scope:
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


def _polish(doc_id: str, words: list[dict], members: dict, entries: dict) -> list[str]:
    errors: list[str] = []
    for window, scope in _patterns(words):
        if not _bounded(window, scope):
            continue
        pieces = _realizations(scope, members, entries)
        if pieces is None:
            continue
        tokens = set(_tokens(" ".join(pieces)))
        negative = tokens & {
            "nikt",
            "nikogo",
            "nikomu",
            "nikim",
            "żaden",
            "żadna",
            "żadne",
        }
        if scope[-1].get("lemma") == "sum" and negative == {"nikim"}:
            continue
        if negative and "nie" not in tokens:
            errors.append(
                f"{doc_id}:{window[0]['id']}–{window[-1]['id']}: "
                "suspect Polish personal-negative predicate; verify local concord and scope"
            )
    return errors


def _english(doc_id: str, words: list[dict], members: dict, entries: dict) -> list[str]:
    errors: list[str] = []
    for i in range(len(words) - 3):
        first, verb, adjective, noun = window = words[i : i + 4]
        if (
            _matches(first, "nemo", case="dat")
            and _matches(verb, "do", pos="verb", mood="part", tense="pres", voice="act")
            and _matches(adjective, "ullus", case="acc")
            and _matches(noun, "offensio", case="acc")
            and _unpunctuated(window)
            and not any(w["id"] in members for w in window)
        ):
            glosses = [_tokens((entries.get(w["id"]) or {}).get("gloss")) for w in window]
            if glosses == [["to", "no", "one"], ["giving", "no"], ["any"], ["offense"]]:
                errors.append(
                    f"{doc_id}:{first['id']}–{noun['id']}: "
                    "duplicated English negative in the giving-of-offense construction"
                )
    for first, second in pairwise(words):
        if not (
            _matches(first, "ne", pos="conj")
            and _matches(second, "quis", pos="pron", case="nom")
            and _unpunctuated([first, second])
            and not {first["id"], second["id"]} & members.keys()
        ):
            continue
        left, right = [_tokens((entries.get(w["id"]) or {}).get("gloss")) for w in (first, second)]
        if right not in (
            ["no", "one"],
            ["no", "man"],
            ["nobody"],
            ["anyone"],
            ["anybody"],
        ):
            continue
        if any(left == prefix + right for prefix in (["that"], ["lest"], ["so", "that"])):
            errors.append(
                f"{doc_id}:{first['id']}–{second['id']}: adjacent direct glosses "
                "repeat the indefinite subject of ne; verify one coherent realization"
            )
    return errors


def check_personal_negatives(doc: dict, layer: dict) -> list[str]:
    """Examine only explicitly bounded, completely realized constructions."""
    language = layer.get("lang")
    if language not in {"pl", "en"}:
        return []
    errors: list[str] = []
    entries = layer.get("words", {})
    checker = _polish if language == "pl" else _english
    for segment in doc.get("segments", []):
        words = segment.get("words") or []
        groups = (layer.get("segments", {}).get(segment["id"]) or {}).get("alignments", [])
        members = {wid: group for group in groups for wid in group["words"]}
        errors.extend(checker(doc["id"], words, members, entries))
    return errors
