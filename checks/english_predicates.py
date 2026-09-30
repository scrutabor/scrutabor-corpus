"""Narrow English predicate junctions, not a general translation validator."""

from __future__ import annotations

import unicodedata


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
    return errors
