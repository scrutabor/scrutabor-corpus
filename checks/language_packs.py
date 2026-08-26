"""Shape and coverage checks for independently publishable language packs."""

from __future__ import annotations

import re
from pathlib import Path

from build_reader import store
from checks.lint import lint_citations

LANGUAGE_RE = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
CORE_LOCALIZATION_KEYS = {
    "about",
    "about_citations",
    "functions",
    "notes",
    "narrative_citations",
}
LAYER_KEYS = {"schema_version", "language", "text", "about", "segments", "words"}


def check_manifests(corpus: Path) -> list[str]:
    errors: list[str] = []
    all_texts = store.text_ids(corpus)
    known = set(all_texts)
    languages = store.language_ids(corpus)
    if not languages:
        return ["languages: no manifests found — refusing to pass on zero"]

    for language in languages:
        manifest = store.language_manifest(corpus, language)
        where = f"languages/{language}/manifest.json"
        if manifest.get("language") != language:
            errors.append(f"{where}: language does not match its directory")
        if not LANGUAGE_RE.fullmatch(language):
            errors.append(f"{where}: {language!r} is not a BCP 47 language tag")
        if manifest.get("direction") not in ("ltr", "rtl"):
            errors.append(f"{where}: direction must be ltr or rtl")
        texts = manifest.get("texts")
        if not isinstance(texts, list) or not texts:
            errors.append(f"{where}: texts must be a nonempty list")
            continue
        if len(texts) != len(set(texts)):
            errors.append(f"{where}: text ids must be unique")
        unknown = sorted(set(texts) - known)
        if unknown:
            errors.append(f"{where}: unknown text ids {unknown}")
        expected_order = [text_id for text_id in all_texts if text_id in set(texts)]
        if texts != expected_order:
            errors.append(f"{where}: texts must follow the neutral manifest order")

        actual = {
            f"{path.parent.name}.{path.stem}"
            for path in (corpus / "languages" / language / "texts").glob("*/*.json")
        }
        if set(texts) != actual:
            errors.append(
                f"{where}: manifest/file coverage differs — "
                f"missing={sorted(set(texts) - actual)} orphaned={sorted(actual - set(texts))}"
            )
        for required in ("lexicon.json", "translation-provenance.json"):
            if not (corpus / "languages" / language / required).exists():
                errors.append(f"languages/{language}/{required} is missing")
    return errors


def check_core(core: dict) -> list[str]:
    errors: list[str] = []
    text_id = core.get("id", "?")
    localization = core.get("localization")
    if not isinstance(localization, dict):
        return [f"{text_id}: localization must be an object"]
    unknown = set(localization) - CORE_LOCALIZATION_KEYS
    if unknown:
        errors.append(f"{text_id}: localization has unknown keys {sorted(unknown)}")
    if localization.get("about") is not True:
        errors.append(f"{text_id}: localization.about must be true")
    if citations := localization.get("about_citations"):
        errors += lint_citations(citations, f"{text_id}:localization.about")

    segment_ids = {segment["id"] for segment in core.get("segments") or []}
    rubric_ids = {
        segment["id"] for segment in core.get("segments") or [] if segment.get("type") == "rubric"
    }
    word_ids = {
        word["id"] for segment in core.get("segments") or [] for word in segment.get("words") or []
    }
    functions = localization.get("functions") or {}
    if not isinstance(functions, dict):
        errors.append(f"{text_id}: localization.functions must be an object")
        functions = {}
    for word_id, requirement in functions.items():
        if word_id not in word_ids:
            errors.append(f"{text_id}: function requirement for unknown word {word_id}")
        if not isinstance(requirement, dict) or set(requirement) - {"citations"}:
            errors.append(f"{text_id}:{word_id}: function requirement has unknown shape")
            continue
        if citations := requirement.get("citations"):
            errors += lint_citations(citations, f"{text_id}:{word_id}:function")

    notes = localization.get("notes") or []
    if not isinstance(notes, list) or len(notes) != len(set(notes)):
        errors.append(f"{text_id}: localization.notes must be a unique list")
    else:
        unknown_notes = sorted(set(notes) - word_ids)
        if unknown_notes:
            errors.append(f"{text_id}: note requirements for unknown words {unknown_notes}")

    narrative = localization.get("narrative_citations") or {}
    if not isinstance(narrative, dict):
        errors.append(f"{text_id}: localization.narrative_citations must be an object")
        narrative = {}
    for segment_id, citations in narrative.items():
        if segment_id not in segment_ids:
            errors.append(f"{text_id}: narrative citations for unknown segment {segment_id}")
        elif segment_id not in rubric_ids:
            errors.append(f"{text_id}:{segment_id}: narrative citations on a verse")
        errors += lint_citations(citations, f"{text_id}:{segment_id}:narrative")

    forbidden_doc = set(core) & {"about", "about_citations"}
    if forbidden_doc:
        errors.append(
            f"{text_id}: localized document fields in neutral core {sorted(forbidden_doc)}"
        )
    for segment in core.get("segments") or []:
        forbidden = set(segment) & {
            "translation",
            "translation_citations",
            "narrative",
            "narrative_citations",
        }
        if forbidden:
            errors.append(
                f"{text_id}:{segment['id']}: localized fields in neutral core {sorted(forbidden)}"
            )
        for word in segment.get("words") or []:
            forbidden = set(word) & {"gloss", "function", "function_citations", "note"}
            if forbidden:
                errors.append(
                    f"{text_id}:{word['id']}: localized fields in neutral core {sorted(forbidden)}"
                )
    return errors


def check_layer(core: dict, layer: dict, path: Path) -> list[str]:
    errors: list[str] = []
    text_id = core["id"]
    language = layer.get("language", "?")
    where = f"{language}:{text_id}"
    if layer.get("text") != text_id:
        errors.append(f"{where}: text id does not match the neutral core")
    if path.parent.name != core["category"] or path.stem != text_id.split(".", 1)[1]:
        errors.append(f"{where}: path does not match text id")
    unknown = set(layer) - LAYER_KEYS
    if unknown:
        errors.append(f"{where}: unknown document keys {sorted(unknown)}")
    if layer.get("schema_version") != core.get("schema_version"):
        errors.append(f"{where}: schema version differs from the neutral core")
    if not isinstance(layer.get("about"), str) or not layer["about"].strip():
        errors.append(f"{where}: about is required and must be nonempty")

    core_segments = core.get("segments") or []
    segments = layer.get("segments") or {}
    expected_segment_ids = [segment["id"] for segment in core_segments]
    if list(segments) != expected_segment_ids:
        errors.append(f"{where}: segment coverage or order differs from the neutral core")
    for segment in core_segments:
        segment_id = segment["id"]
        entry = segments.get(segment_id) or {}
        if segment["type"] == "verse":
            allowed, required = {"translation", "translation_citations"}, "translation"
        else:
            allowed, required = {"narrative"}, "narrative"
        unknown = set(entry) - allowed
        if unknown:
            errors.append(f"{where}:{segment_id}: unknown keys {sorted(unknown)}")
        if not isinstance(entry.get(required), str) or not entry[required].strip():
            errors.append(f"{where}:{segment_id}: {required} is required and must be nonempty")
        if citations := entry.get("translation_citations"):
            errors += lint_citations(citations, f"{where}:{segment_id}:translation")

    words = layer.get("words") or {}
    core_word_ids = [word["id"] for segment in core_segments for word in segment.get("words") or []]
    if list(words) != core_word_ids:
        errors.append(f"{where}: word coverage or order differs from the neutral core")
    expected_functions = set((core.get("localization") or {}).get("functions") or {})
    expected_notes = set((core.get("localization") or {}).get("notes") or [])
    actual_functions: set[str] = set()
    actual_notes: set[str] = set()
    for word_id in core_word_ids:
        entry = words.get(word_id) or {}
        unknown = set(entry) - {"gloss", "function", "note"}
        if unknown:
            errors.append(f"{where}:{word_id}: unknown keys {sorted(unknown)}")
        if not isinstance(entry.get("gloss"), str) or not entry["gloss"].strip():
            errors.append(f"{where}:{word_id}: gloss is required and must be nonempty")
        if "function" in entry:
            actual_functions.add(word_id)
        if "note" in entry:
            actual_notes.add(word_id)
    if actual_functions != expected_functions:
        errors.append(
            f"{where}: function topology differs — "
            f"missing={sorted(expected_functions - actual_functions)} "
            f"extra={sorted(actual_functions - expected_functions)}"
        )
    if actual_notes != expected_notes:
        errors.append(
            f"{where}: note topology differs — missing={sorted(expected_notes - actual_notes)} "
            f"extra={sorted(actual_notes - expected_notes)}"
        )
    return errors
