"""English glosses, checked where English can be checked exactly.

The Polish line has Morfeusz behind it and can be held to agreement. English
has no such analyzer here, and its prepositions answer to the English verb
rather than to the Latin case — *believe IN one God* renders an accusative,
*have mercy ON us* a dative, and neither is a mistake. So this module asserts
only what is decidable without English morphology, and says nothing else.

Two things are decidable:

- **A preposition rendered twice.** When *de* is glossed *from* and its own
  object *cælis* is glossed *of heaven*, the gloss line reads *Father from of
  heaven*. Exact, because the Latin `head` says which word is the object.
- **A two-case preposition against the case it governs.** *in* with the
  ablative is *in*, with the accusative *into*; the corpus records the case.
  Where English idiom overrides — *in memoriam*, *at the hour*, *believe in* —
  the site is declared below rather than guessed at.
"""

from __future__ import annotations

import re

LEADING_PREPOSITION = re.compile(
    r"^\s*(of|to|unto|for|with|by|in|from|at|on|into|through|upon)\b", re.IGNORECASE
)

# What a two-case preposition may be glossed with, per case it governs.
BY_CASE: dict[tuple[str, str], set[str]] = {
    ("in", "abl"): {"in", "on", "among", "within"},
    ("in", "acc"): {"into", "to", "unto", "on", "upon", "for"},
    ("sub", "abl"): {"under", "beneath"},
    ("sub", "acc"): {"under", "beneath"},
    ("super", "abl"): {"over", "above", "concerning"},
    ("super", "acc"): {"over", "above", "upon"},
    ("subter", "abl"): {"under", "beneath"},
    ("subter", "acc"): {"under", "beneath"},
}

# English idiom that overrides the Latin case, declared site by site so the
# check above can be a gate. Each is right English and would be wrong to
# "correct": one does not believe INTO God, and the hour of death is AT.
IDIOM_RULINGS: dict[tuple[str, str], str] = {
    ("orationes.angelus-domini", "w036"): "in hora mortis: at the hour",
    ("orationes.angelus-domini", "w075"): "in hora mortis: at the hour",
    ("orationes.angelus-domini", "w115"): "in hora mortis: at the hour",
    ("orationes.ave-maria", "w027"): "in hora mortis: at the hour",
    ("ordinarium.communicantes", "w005"): "in primis: the phrase reads first of all",
    ("ordinarium.credo", "w002"): "credo in: one believes IN God, not into",
    ("ordinarium.credo", "w016"): "credo in: one believes IN God, not into",
    ("ordinarium.credo", "w117"): "credo in: one believes IN the Spirit, not into",
    ("ordinarium.simili-modo", "w057"): "in memoriam: in memory of",
    ("ordinarium.suscipe-sancta-trinitas", "w020"): "in honorem: in honour of",
    ("ordinarium.te-igitur", "w029"): "in primis: the phrase reads first of all",
    ("psalmi.118-he", "w022"): "in toto corde meo: with my whole heart",
}


def _index(doc: dict) -> dict[str, dict]:
    return {w["id"]: w for s in doc.get("segments", []) for w in (s.get("words") or [])}


def check_doubled_preposition(doc: dict, gloss: dict) -> list[str]:
    """A preposition glossed once by itself and again inside its object."""
    errors: list[str] = []
    words = gloss.get("words", {})
    index = _index(doc)
    for w in index.values():
        if w["morph"].get("pos") != "prep":
            continue
        head_id = w.get("head")
        if head_id is None or head_id not in index:
            continue
        own = (words.get(w["id"]) or {}).get("gloss") or ""
        obj = (words.get(head_id) or {}).get("gloss") or ""
        if LEADING_PREPOSITION.match(own) and LEADING_PREPOSITION.match(obj):
            errors.append(
                f"{doc['id']}:{w['id']} ({w['form']}): glossed {own.strip()!r} over "
                f"{index[head_id]['form']!r} glossed {obj.strip()!r} — the gloss line "
                f"renders the preposition twice"
            )
    return errors


def check_two_case_prepositions(doc: dict, gloss: dict) -> list[str]:
    """in with the ablative is `in`; with the accusative it is `into`."""
    errors: list[str] = []
    words = gloss.get("words", {})
    index = _index(doc)
    for w in index.values():
        if w["morph"].get("pos") != "prep":
            continue
        head_id = w.get("head")
        if head_id is None or head_id not in index:
            continue
        if (doc["id"], w["id"]) in IDIOM_RULINGS:
            continue
        allowed = BY_CASE.get((w["lemma"], index[head_id]["morph"].get("case")))
        if not allowed:
            continue
        text = ((words.get(w["id"]) or {}).get("gloss") or "").strip().lower()
        if not text or text in allowed:
            continue
        errors.append(
            f"{doc['id']}:{w['id']} ({w['form']}): governs {index[head_id]['form']!r} in "
            f"the {index[head_id]['morph'].get('case')}, but is glossed {text!r} — "
            f"expected one of {'/'.join(sorted(allowed))}"
        )
    return errors


def check(doc: dict, gloss: dict) -> list[str]:
    if gloss.get("lang") != "en":
        return []
    return check_doubled_preposition(doc, gloss) + check_two_case_prepositions(doc, gloss)


# A Latin plural the edition renders with an English singular, declared site by
# site so the check below can be a gate. Each is an editorial decision: the
# ecclesiastical *caeli* names one heaven, *sanguinibus* in the Last Gospel is a
# Hebraism for one substance, and *in cælis et in terris* is the same idiom.
ENGLISH_NUMBER_RULINGS: dict[str, str] = {
    "caelum": "the ecclesiastical plural caeli names one heaven",
    "dies": "the distributive per singulos dies is rendered every day",
    "sanguis": "sanguinibus is a Hebraism for one substance",
    "terra": "in caelis et in terris: English says earth",
}


def check_number(docs: list[tuple[dict, dict]]) -> list[str]:
    """One English gloss may not serve both numbers of one Latin noun.

    English has no analyzer here, so number is checked against the CORPUS
    itself: if *caelo* and *caelis* are both glossed 'heaven', either one of
    them is wrong or the collapse is an editorial decision — and the corpus
    says which by declaring it. Adjectives and pronouns are exempt because
    English does not inflect them for number, which is why this reads nouns
    alone.
    """
    seen: dict[tuple[str, str], set[str]] = {}
    where: dict[tuple[str, str], str] = {}
    for doc, gloss in docs:
        words = gloss.get("words") or {}
        for segment in doc.get("segments", []):
            for w in segment.get("words") or []:
                m = w["morph"]
                if m.get("pos") != "noun" or not m.get("number"):
                    continue
                text = (words.get(w["id"]) or {}).get("gloss")
                if not text:
                    continue
                key = (w["lemma"], text.lower())
                seen.setdefault(key, set()).add(m["number"])
                where.setdefault(key, f"{doc['id']}:{w['id']} ({w['form']})")
    return [
        f"{where[key]}: gloss {key[1]!r} serves both the singular and the plural "
        f"of {key[0]!r} — declare the collapse or distinguish the numbers"
        for key, nums in sorted(seen.items())
        if len(nums) > 1 and key[0] not in ENGLISH_NUMBER_RULINGS
    ]
