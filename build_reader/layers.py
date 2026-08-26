"""Join neutral text cores to one language layer in memory.

The authored corpus stores facts at the boundary where they change: Latin,
ritual structure and editorial analysis in ``texts/``; reader-facing prose in
``languages/<language>/``.  Checks written before that storage split still ask
for a text document and one gloss document.  This module reconstructs those
two views without coupling the files on disk again.
"""

from __future__ import annotations

import copy

SCHEMA = "0.17.0"


def expand_core(core: dict) -> dict:
    """Return the language-neutral checking view of one stored core."""
    editorial = core.get("editorial") or {}
    text = {
        key: copy.deepcopy(value)
        for key, value in core.items()
        if key not in ("editorial", "localization")
    }
    for key in ("status", "notes", "source", "analysis_defaults", "analysis_defaults_words"):
        if key in editorial:
            text[key] = copy.deepcopy(editorial[key])

    segments = []
    for stored_segment in core["segments"]:
        segment = copy.deepcopy(stored_segment)
        segment_editorial = (editorial.get("segments") or {}).get(segment["id"]) or {}
        if "analysis" in segment_editorial:
            segment["analysis"] = copy.deepcopy(segment_editorial["analysis"])
        for word in segment.get("words") or []:
            word_editorial = (editorial.get("words") or {}).get(word["id"]) or {}
            if "analysis" in word_editorial:
                word["analysis"] = copy.deepcopy(word_editorial["analysis"])
        segments.append(segment)
    text["segments"] = segments
    return text


def enrich_layer(core: dict, layer: dict) -> dict:
    """Attach shared source notes and compatibility metadata to one language."""
    editorial = core.get("editorial") or {}
    localization = core.get("localization") or {}
    out = copy.deepcopy(layer)
    out["lang"] = out.pop("language")
    out["status"] = editorial.get("status", "working-edition")
    out["analysis_defaults"] = copy.deepcopy(editorial.get("analysis_defaults") or {})

    if citations := localization.get("about_citations"):
        out["about_citations"] = copy.deepcopy(citations)
    for word_id, requirement in (localization.get("explanations") or {}).items():
        if citations := requirement.get("citations"):
            out["words"][word_id]["explanation_citations"] = copy.deepcopy(citations)
    for segment_id, citations in (localization.get("narrative_citations") or {}).items():
        out["segments"][segment_id]["narrative_citations"] = copy.deepcopy(citations)
    return out
