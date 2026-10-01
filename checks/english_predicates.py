"""Narrow English predicate junctions, not a general translation validator."""

from __future__ import annotations

import re
import unicodedata
from itertools import pairwise


def check_predicate_junctions(doc: dict, gloss: dict) -> list[str]:
    """Reject direct like/is and let sound/voice/your in bounded Latin syntax.

    Compare complete glosses only, inside a single unpunctuated Latin window.
    Shared and zero providers remain the interlinear validator's responsibility.
    Other tenses, comparisons, jussives and result-state readings need review.
    """
    if gloss.get("lang") != "en":
        return []
    errors: list[str] = []
    localized = gloss.get("segments") or {}
    glosses = gloss.get("words") or {}

    def normalized(value: object) -> str:
        if not isinstance(value, str):
            return ""
        return " ".join(unicodedata.normalize("NFKC", value).casefold().split())

    def has(word: dict, expected: dict) -> bool:
        return all(word.get("morph", {}).get(k) == v for k, v in expected.items())

    for segment in doc.get("segments", []):
        words = segment.get("words") or []
        members = {
            wid
            for group in (localized.get(segment.get("id")) or {}).get("alignments", [])
            for wid in group["words"]
        }

        def direct(
            window: list[dict], grouped: frozenset[str] = frozenset(members)
        ) -> tuple[str, ...] | None:
            if (
                any(w["id"] in grouped for w in window)
                or any(w.get("post", "").strip() for w in window[:-1])
                or any(w.get("pre", "").strip() for w in window[1:])
            ):
                return None
            return tuple(normalized((glosses.get(w["id"]) or {}).get("gloss")) for w in window)

        for i in range(len(words) - 1):
            a, b = words[i : i + 2]
            if (
                a.get("lemma") == "similis"
                and b.get("lemma") == "sum"
                and has(a, {"pos": "adj", "case": "nom", "number": "sg"})
                and has(
                    b,
                    {
                        "pos": "verb",
                        "mood": "ind",
                        "tense": "pres",
                        "voice": "act",
                        "person": 3,
                        "number": "sg",
                    },
                )
                and direct([a, b]) == ("like", "is")
            ):
                errors.append(
                    f"{doc['id']}:{a['id']}–{b['id']}: comparison glosses produce "
                    "'like is' — use a coherent English predicate and complement"
                )
        for i in range(len(words) - 2):
            a, b, c = words[i : i + 3]
            if (
                (a.get("lemma"), b.get("lemma"), c.get("lemma")) == ("sono", "vox", "tuus")
                and has(
                    a,
                    {
                        "pos": "verb",
                        "mood": "subj",
                        "tense": "pres",
                        "voice": "act",
                        "person": 3,
                        "number": "sg",
                    },
                )
                and has(b, {"pos": "noun", "case": "nom", "gender": "f", "number": "sg"})
                and has(c, {"pos": "adj", "case": "nom", "gender": "f", "number": "sg"})
                and c.get("head") == b["id"]
                and direct([a, b, c]) == ("let sound", "voice", "your")
            ):
                errors.append(
                    f"{doc['id']}:{a['id']}–{c['id']}: jussive glosses produce "
                    "'let sound voice your' — preserve the subject in a coherent English clause"
                )
    return errors + check_dependent_jussive(doc, gloss)


def check_dependent_jussive(doc: dict, gloss: dict) -> list[str]:
    """Reject the direct dependent/imperative hybrid 'that / let them rest'.

    Only adjacent ut plus a present active third-person subjunctive is examined.
    Do not infer a junction across punctuation, segments, or shared/zero providers.
    This does not choose a translation for ut or reject free quoted imperatives.
    Other persons, tenses, voices, longer connectives and quoted glosses need review.
    """
    if gloss.get("lang") != "en":
        return []
    errors: list[str] = []
    entries = gloss.get("words") or {}
    localized = gloss.get("segments") or {}

    def normalized(value: object) -> str:
        if not isinstance(value, str):
            return ""
        return " ".join(unicodedata.normalize("NFKC", value).casefold().split())

    for segment in doc.get("segments", []):
        words = segment.get("words") or []
        members = {
            wid
            for group in (localized.get(segment.get("id")) or {}).get("alignments", [])
            for wid in group["words"]
        }
        for conjunction, verb in pairwise(words):
            morph = verb.get("morph") or {}
            if (
                conjunction.get("lemma") != "ut"
                or conjunction.get("morph", {}).get("pos") != "conj"
                or morph.get("pos") != "verb"
                or morph.get("mood") != "subj"
                or morph.get("tense") != "pres"
                or morph.get("voice") != "act"
                or morph.get("person") != 3
                or morph.get("number") not in {"sg", "pl"}
                or conjunction.get("post", "").strip()
                or verb.get("pre", "").strip()
                or conjunction["id"] in members
                or verb["id"] in members
            ):
                continue
            left = normalized((entries.get(conjunction["id"]) or {}).get("gloss"))
            right = normalized((entries.get(verb["id"]) or {}).get("gloss"))
            if left in {"that", "so that"} and re.match(r"let (?:him|her|it|them) [^\W\d_]", right):
                errors.append(
                    f"{doc['id']}:{conjunction['id']}–{verb['id']}: dependent glosses "
                    f"produce {left!r} + {right!r} — use one coherent dependent clause "
                    "rather than appending an independent let-imperative"
                )
    return errors
