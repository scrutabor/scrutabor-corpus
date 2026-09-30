"""Bounded duplicated demonstratives, connectors and absolute subjects.

These diagnostics require local direct providers and explicit grammatical
evidence. Missing dependencies, other scopes, shared and zero providers are
unmeasured here, not semantically approved. Structural validation is separate.
"""

from __future__ import annotations

import re
import unicodedata
from itertools import pairwise


def _tokens(value: object) -> list[str]:
    if not isinstance(value, str):
        return []
    return re.findall(
        r"[^\W\d_]+(?:['’][^\W\d_]+)*",
        unicodedata.normalize("NFKC", value).casefold().replace("’", "'"),
    )


def _bounded(words: list[dict]) -> bool:
    return not any(
        a.get("post", "").strip() or b.get("pre", "").strip() for a, b in pairwise(words)
    )


def _direct(word: dict, entries: dict, grouped: set[str]) -> list[str]:
    if word["id"] in grouped:
        return []
    return _tokens(entries.get(word["id"], {}).get("gloss"))


def check_contextual_repetitions(doc: dict, layer: dict) -> list[str]:
    """Flag only the duplicated local argument/connector shapes described above."""
    if layer.get("lang") != "en":
        return []
    errors: list[str] = []
    for segment in doc.get("segments", []):
        words = segment.get("words") or []
        entries = layer.get("words", {})
        groups = (layer.get("segments", {}).get(segment["id"]) or {}).get("alignments", [])
        grouped = {wid for group in groups for wid in group["words"]}

        def report(span: list[dict], reason: str) -> None:
            errors.append(
                f"{doc['id']}:{span[0]['id']}–{span[-1]['id']}: {reason}; "
                "verify one coherent realization of the construction"
            )

        for i, first in enumerate(words):
            fm = first.get("morph", {})
            if i + 1 < len(words):
                second = words[i + 1]
                sm = second.get("morph", {})
                left, right = _direct(first, entries, grouped), _direct(second, entries, grouped)
                if left and right and _bounded([first, second]):
                    if (
                        fm.get("pos") == "noun"
                        and sm.get("pos") == "pron"
                        and second.get("lemma") in {"hic", "ille", "iste"}
                        and second.get("head") == first["id"]
                        and all(
                            fm.get(k) is not None and fm[k] == sm.get(k)
                            for k in ("case", "number", "gender")
                        )
                        and right in [["this"], ["that"], ["these"], ["those"]]
                        and right[0] in left
                    ):
                        report([first, second], "adjacent direct glosses repeat the demonstrative")
                    connector = {"enim": "for", "autem": "but"}.get(second.get("lemma"))
                    if (
                        fm.get("pos") == "verb"
                        and fm.get("mood") in {"ind", "subj"}
                        and connector
                        and right == [connector]
                        and len(left) > 1
                        and left[0] == connector
                    ):
                        report([first, second], "adjacent direct glosses repeat the connector")
                    if (
                        first.get("lemma") == "ager"
                        and fm.get("pos") == "noun"
                        and second.get("lemma") == "figulus"
                        and sm.get("pos") == "noun"
                        and second.get("head") == first["id"]
                        and sm.get("case") == "gen"
                        and right == ["potter's"]
                        and "potter's" in left
                    ):
                        report(
                            [first, second],
                            "the direct field gloss already includes the potter genitive",
                        )
            for distance in (1, 2):
                if i + distance >= len(words):
                    continue
                span = words[i : i + distance + 1]
                pron = span[-1]
                pm = pron.get("morph", {})
                if distance == 2 and span[1].get("lemma") not in {"autem", "ergo", "igitur"}:
                    continue
                if (
                    not _bounded(span)
                    or fm.get("pos") != "verb"
                    or fm.get("mood") != "part"
                    or fm.get("case") != "abl"
                    or pm.get("pos") != "pron"
                    or pm.get("case") != "abl"
                    or first.get("head") != pron["id"]
                    or any(fm.get(k) is None or fm[k] != pm.get(k) for k in ("number", "gender"))
                    or any(word["id"] in grouped for word in span)
                ):
                    continue
                left, right = _direct(first, entries, grouped), _direct(pron, entries, grouped)
                if len(left) < 2 or not right:
                    continue
                subject = (
                    left[1]
                    if left[0] in {"as", "when", "while"}
                    else left[0]
                    if left[1] == "being"
                    else None
                )
                object_form = {"he": "him", "she": "her", "they": "them", "it": "it"}.get(
                    subject or ""
                )
                if object_form and (right == [subject] or right == ["to", object_form]):
                    report(
                        span,
                        "the absolute's direct participle already realizes its pronoun subject",
                    )
    return errors
