"""The target-language alignment carried by an interlinear layer.

Most Latin words have one ordinary ``words.<id>.gloss``.  A target language
may instead render a contiguous Latin construction with one expression, or
render a particle only through syntax.  Those exceptional realizations live
on the segment as explicit alignments; visible gloss strings never carry
editorial placeholders.
"""

from __future__ import annotations

import re

ZERO_REASONS = {"idiom", "inflection", "punctuation", "word-order"}
TECHNICAL_GLOSS = re.compile(r"^\s*(?:\[[^\]]+\]|[—–-])\s*$")


def alignments_for(layer: dict, segment_id: str) -> list[dict]:
    return list(((layer.get("segments") or {}).get(segment_id) or {}).get("alignments") or [])


def alignment_by_word(layer: dict) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for segment in (layer.get("segments") or {}).values():
        for alignment in segment.get("alignments") or []:
            for word_id in alignment.get("words") or []:
                found[word_id] = alignment
    return found


def effective_gloss(layer: dict, word_id: str) -> str:
    """The gloss used by linguistic checks: a shared gloss belongs to its anchor."""
    direct = ((layer.get("words") or {}).get(word_id) or {}).get("gloss")
    if direct:
        return direct
    alignment = alignment_by_word(layer).get(word_id)
    if alignment and alignment.get("anchor") == word_id:
        return alignment.get("gloss") or ""
    return ""


def check(doc: dict, layer: dict) -> list[str]:
    """Every Latin token has exactly one real target-language realization."""
    errors: list[str] = []
    language = layer.get("language") or layer.get("lang") or "?"
    entries = layer.get("words") or {}
    aligned: dict[str, tuple[str, int]] = {}

    for segment in doc.get("segments") or []:
        segment_id = segment["id"]
        words = segment.get("words") or []
        positions = {word["id"]: index for index, word in enumerate(words)}
        previous_end = -1
        for number, alignment in enumerate(alignments_for(layer, segment_id), 1):
            where = f"{doc['id']}:{segment_id}:alignment-{number}:{language}"
            unknown_keys = set(alignment) - {"words", "anchor", "gloss", "reason"}
            if unknown_keys:
                errors.append(f"{where}: unknown keys {sorted(unknown_keys)}")
            ids = alignment.get("words")
            if not isinstance(ids, list) or not ids or any(not isinstance(i, str) for i in ids):
                errors.append(f"{where}: words must be a nonempty list of word ids")
                continue
            if len(ids) != len(set(ids)):
                errors.append(f"{where}: words must be unique")
                continue
            if any(i not in positions for i in ids):
                errors.append(f"{where}: alignment names a word outside this segment")
                continue
            indices = [positions[i] for i in ids]
            if indices != list(range(indices[0], indices[0] + len(indices))):
                errors.append(f"{where}: aligned words must be contiguous and in source order")
            if indices[0] <= previous_end:
                errors.append(f"{where}: alignments must be ordered and may not overlap")
            previous_end = max(indices)
            for word_id in ids:
                if word_id in aligned:
                    errors.append(f"{where}: {word_id} belongs to more than one alignment")
                aligned[word_id] = (segment_id, number)

            gloss = alignment.get("gloss")
            reason = alignment.get("reason")
            anchor = alignment.get("anchor")
            if gloss is not None:
                if not isinstance(gloss, str) or not gloss.strip():
                    errors.append(f"{where}: gloss must be a nonempty string")
                elif TECHNICAL_GLOSS.fullmatch(gloss):
                    errors.append(f"{where}: gloss must be target-language wording, not {gloss!r}")
                if len(ids) < 2:
                    errors.append(f"{where}: a one-word realization belongs in words.<id>.gloss")
                if anchor not in ids:
                    errors.append(f"{where}: anchor must name the source word carrying the gloss")
                if reason is not None:
                    errors.append(f"{where}: a realized alignment may not also have a zero reason")
            else:
                if anchor is not None:
                    errors.append(f"{where}: an unrealized alignment may not have an anchor")
                if reason not in ZERO_REASONS:
                    errors.append(
                        f"{where}: an unrealized alignment needs reason in {sorted(ZERO_REASONS)}"
                    )

    word_ids = [
        word["id"] for segment in doc.get("segments") or [] for word in segment.get("words") or []
    ]
    for word_id in word_ids:
        entry = entries.get(word_id) or {}
        direct = entry.get("gloss")
        in_alignment = word_id in aligned
        if direct is not None:
            if not isinstance(direct, str) or not direct.strip():
                errors.append(f"{doc['id']}:{word_id}:{language}: gloss must be nonempty")
            elif TECHNICAL_GLOSS.fullmatch(direct):
                errors.append(
                    f"{doc['id']}:{word_id}:{language}: visible gloss {direct!r} "
                    "is a technical marker"
                )
        if bool(direct) == in_alignment:
            errors.append(
                f"{doc['id']}:{word_id}:{language}: expected exactly one direct gloss or alignment"
            )
    return errors
