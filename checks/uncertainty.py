"""What the edition does not know, measured and kept honest.

This edition is bound to state its uncertainty plainly and to flag it for
review: an edition must know what it does not know. Until 2026-08-16 this
corpus stored NO uncertainty whatever: 4,773 of 4,926 words carried no analysis
block at all and inherited `confidence: high`, and the 153 that carried one were
all `high`. Every verdict line printed `disputed=0/0 forms`, which reads as
"checked, nothing disputed" and meant "nothing was ever marked".

Two numbers keep that honest, and they answer different questions.

EXPOSURE is how many tokens the corpus's own evidence does not settle: the form
is attested in this corpus with more than one reading, and neither an agreement
head nor a preposition's government forces the choice. It is large — about a
sixth of the corpus — and it is NOT a defect count. *Deus* in *Deus meus* is
nominative-or-vocative by form and beyond doubt in context. Exposure names the
population an expert would have to read to close the question, not the errors.

STORED DOUBT is how many tokens the edition has actually marked `medium`/`low`
confidence or `review: disputed`. That number reaches the list an expert reads.

The rule this file enforces is narrow and hard to game: a corpus with real
exposure and ZERO stored doubt is asserting certainty it has not earned, and
fails the build.
"""

from __future__ import annotations

FORCED_BY = "an agreement head or a preposition's government"


def _signature(morph: dict) -> tuple:
    return (
        morph.get("pos"),
        morph.get("case"),
        morph.get("number"),
        morph.get("gender"),
        morph.get("tense"),
        morph.get("mood"),
        morph.get("voice"),
        morph.get("person"),
    )


def readings(docs: list[dict]) -> dict[str, set]:
    """form -> every (lemma, morph) reading this corpus attests for it."""
    out: dict[str, set] = {}
    for doc in docs:
        for segment in doc.get("segments", []):
            for word in segment.get("words") or []:
                out.setdefault(word["form"].lower(), set()).add(
                    (word["lemma"], _signature(word["morph"]))
                )
    return out


def exposure(doc: dict, attested: dict[str, set]) -> int:
    """Tokens this text does not settle: ambiguous form, nothing forcing it.

    A FLOOR, not a measure. `attested` holds only the readings THIS corpus
    happens to carry, so a form that is syncretic in Latin at large but occurs
    here once, or always in one reading, is not counted at all. The real
    exposure is larger by an unknown amount, and the printed figure is written
    `>=` for that reason.
    """
    words = {w["id"]: w for s in doc.get("segments", []) for w in (s.get("words") or [])}
    governed = {
        w["head"] for w in words.values() if w["morph"].get("pos") == "prep" and w.get("head")
    }
    return sum(
        1
        for wid, w in words.items()
        if len(attested.get(w["form"].lower(), ())) > 1
        and not w.get("head")
        and wid not in governed
    )


def stored(doc: dict) -> int:
    """Tokens this text marks as doubted, by confidence or by review.

    Reads BOTH document shapes: the joined 0.14.0 document, where the
    analysis lives under `editorial`, and the split shape the store hands
    the suite. Until 2026-08-19 it read only the split shape and was right
    by luck — everything flowed through `build_reader/store.py` — while the
    same lookup, pointed at a file on disk, returned zero and would have
    failed the build. That one-seam dependence is exactly how the agreement
    machine's own provenance reader went silent, so this reader takes no
    seam for granted.
    """
    editorial = doc.get("editorial") or {}
    base = editorial.get("analysis_defaults") or doc.get("analysis_defaults") or {}
    words_base = (
        editorial.get("analysis_defaults_words") or doc.get("analysis_defaults_words") or base
    )
    overrides = editorial.get("words") or {}
    total = 0
    for segment in doc.get("segments", []):
        for word in segment.get("words") or []:
            a = (
                (overrides.get(word.get("id"), {}) or {}).get("analysis")
                or word.get("analysis")
                or words_base
            )
            if a.get("confidence") in ("medium", "low") or a.get("review") == "disputed":
                total += 1
    return total


def check(docs: list[dict]) -> list[str]:
    """A corpus with exposure and no stored doubt fails.

    This is asserted ACROSS the corpus, not per text: most texts are short
    enough that having nothing to doubt in one of them is ordinary. Having
    nothing to doubt in eighty-one of them is not.
    """
    attested = readings(docs)
    total_exposure = sum(exposure(doc, attested) for doc in docs)
    total_stored = sum(stored(doc) for doc in docs)
    if total_exposure and not total_stored:
        return [
            f"the corpus leaves {total_exposure} tokens unsettled by {FORCED_BY} "
            f"and marks NONE of them doubted: an edition that admits no "
            f"uncertainty anywhere is asserting certainty it has not earned"
        ]
    return []
