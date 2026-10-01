"""Narrow Polish gloss junctions that need an explicit relational realization.

These diagnostics match complete, attested broken phrases and specific Latin
features, not all absolutes, genitives or perception complements. They do not
prescribe a particular replacement. Shared/zero providers and punctuation
boundaries are excluded. Other constructions require contextual review.
"""

from __future__ import annotations

import unicodedata

# Lemma, required contextual features. Extra features are immaterial.
Token = tuple[str, dict[str, str | int]]
Rule = tuple[str, tuple[Token, ...], tuple[str, ...], tuple[tuple[int, int], ...]]
RULES: tuple[Rule, ...] = (
    (
        "medial relation",
        (
            ("in", {"pos": "prep", "governs": "abl"}),
            ("medius", {"pos": "adj", "case": "abl", "number": "sg", "gender": "n"}),
        ),
        ("w", "pośrodku"),
        ((0, 1),),
    ),
    (
        "medial relation",
        (
            ("in", {"pos": "prep", "governs": "abl"}),
            ("medius", {"pos": "adj", "case": "abl", "number": "sg", "gender": "n"}),
        ),
        ("w", "pośród"),
        ((0, 1),),
    ),
    (
        "medial separation",
        (
            ("de", {"pos": "prep", "governs": "abl"}),
            ("medius", {"pos": "adj", "case": "abl", "number": "sg", "gender": "n"}),
        ),
        ("spośród", "środka"),
        ((0, 1),),
    ),
    (
        "noise genitive",
        (
            ("confusio", {"pos": "noun", "case": "abl", "number": "sg"}),
            ("sonitus", {"pos": "noun", "case": "gen", "number": "sg"}),
        ),
        ("zamętu", "szumu"),
        (),
    ),
    (
        "human absolute",
        (
            (
                "aresco",
                {
                    "pos": "verb",
                    "mood": "part",
                    "tense": "pres",
                    "voice": "act",
                    "case": "abl",
                    "number": "pl",
                    "gender": "m",
                },
            ),
            ("homo", {"pos": "noun", "case": "abl", "number": "pl", "gender": "m"}),
        ),
        ("mdlejącymi", "ludźmi"),
        ((0, 1),),
    ),
    (
        "beginning absolute",
        (
            ("hic", {"pos": "pron", "case": "abl", "number": "pl", "gender": "n"}),
            ("autem", {"pos": "conj"}),
            ("fio", {"pos": "verb", "mood": "inf", "tense": "pres", "voice": "act"}),
            (
                "incipio",
                {
                    "pos": "verb",
                    "mood": "part",
                    "tense": "pres",
                    "voice": "act",
                    "case": "abl",
                    "number": "pl",
                    "gender": "n",
                },
            ),
        ),
        ("gdy te", "zaś", "dziać się", "zaczną"),
        ((3, 0),),
    ),
    (
        "perception complement",
        (
            (
                "video",
                {
                    "pos": "verb",
                    "mood": "ind",
                    "tense": "futperf",
                    "voice": "act",
                    "person": 2,
                    "number": "pl",
                },
            ),
            ("hic", {"pos": "pron", "case": "acc", "number": "pl", "gender": "n"}),
            ("fio", {"pos": "verb", "mood": "inf", "tense": "pres", "voice": "act"}),
        ),
        ("zobaczycie", "to", "dziać się"),
        (),
    ),
)


def _normalized(value: object) -> str:
    if not isinstance(value, str):
        return ""
    text = " ".join(unicodedata.normalize("NFKC", value).casefold().split())
    return text.rstrip(".,;:!?…").rstrip()


def check_clause_junctions(doc: dict, gloss: dict) -> list[str]:
    """Match attested direct-gloss phrases within source/provider bounds."""
    if gloss.get("lang") != "pl":
        return []
    errors: list[str] = []
    localized = gloss.get("segments") or {}
    glosses = gloss.get("words") or {}
    for segment in doc.get("segments", []):
        words = segment.get("words") or []
        grouped = {
            wid
            for group in (localized.get(segment.get("id")) or {}).get("alignments", [])
            for wid in group["words"]
        }
        for label, tokens, target, heads in RULES:
            size = len(tokens)
            for start in range(len(words) - size + 1):
                window = words[start : start + size]
                if (
                    any(w["id"] in grouped for w in window)
                    or any(w.get("post", "").strip() for w in window[:-1])
                    or any(w.get("pre", "").strip() for w in window[1:])
                ):
                    continue
                if any(
                    word.get("lemma") != lemma
                    or any(word.get("morph", {}).get(k) != v for k, v in morph.items())
                    for word, (lemma, morph) in zip(window, tokens, strict=True)
                ):
                    continue
                if any(window[a].get("head") != window[b]["id"] for a, b in heads):
                    continue
                actual = tuple(
                    _normalized((glosses.get(w["id"]) or {}).get("gloss")) for w in window
                )
                if actual == target:
                    errors.append(
                        f"{doc['id']}:{window[0]['id']}–{window[-1]['id']}: Polish "
                        f"{label} glosses produce {' '.join(target)!r} — "
                        "preserve the construction as a coherent Polish expression"
                    )
    return errors
