"""Merge a text and its gloss layers into one document, and split it back.

The corpus keeps a text and its two gloss layers in three files keyed by word
id. Nothing has gone wrong, because the checks enforce the agreement, but the
coupling is invisible in the file layout and every structural edit touches all
three. The measured cost is in review: a one-word correction spans two files
today, and the reviewer cannot see the Latin beside the gloss being changed.
Merged, the same correction is a four-line diff with the form, the parse and
both languages in one hunk.

Two shapes change beyond the join:

- **The editorial block.** `status`, `notes`, `source`, the analysis defaults
  and every per-word `analysis` move under one `editorial` key. A reader never
  sees any of it and the coming review interface wants exactly that layer
  foregrounded, which one document cannot do while the two are interleaved.
  It also means an analyzer re-run touches `editorial` alone, so a human's
  seal over the reading does not go stale because a dictionary was upgraded.
- **Per-language values instead of per-language files.** `gloss`, `about`,
  `translation` and the rest become objects keyed by language, so the Latin
  and both renderings sit on adjacent lines.

`split()` is the inverse and exists so the merge is reversible under test: a
document that cannot be taken apart again is a migration nobody can undo.
"""

from __future__ import annotations

import json
from pathlib import Path

LANGS = ("pl", "en")
SCHEMA = "0.14.0"

# Document keys that describe the edition's working rather than its content.
EDITORIAL = ("status", "notes", "source", "analysis_defaults", "analysis_defaults_words")
# Per-language gloss values that hang off a segment or a word.
SEGMENT_LANG = ("translation", "translation_citations", "narrative", "narrative_citations")
WORD_LANG = ("gloss", "function", "function_citations", "note")


def merge(text: dict, glosses: dict[str, dict]) -> dict:
    """One document from three."""
    out: dict = {"schema_version": SCHEMA}
    for key, value in text.items():
        if key in ("schema_version", "segments") or key in EDITORIAL:
            continue
        out[key] = value

    for key in ("about", "about_citations"):
        by_lang = {lang: glosses[lang][key] for lang in LANGS if key in glosses[lang]}
        if by_lang:
            out[key] = by_lang

    segments = []
    editorial_words: dict[str, dict] = {}
    for segment in text["segments"]:
        row: dict = {}
        for key, value in segment.items():
            if key in ("words", "analysis"):
                continue
            row[key] = value
        for key in SEGMENT_LANG:
            by_lang = {
                lang: (glosses[lang].get("segments") or {}).get(segment["id"], {})[key]
                for lang in LANGS
                if key in ((glosses[lang].get("segments") or {}).get(segment["id"]) or {})
            }
            if by_lang:
                row[key] = by_lang
        if segment.get("analysis"):
            row.setdefault("_editorial", {})["analysis"] = segment["analysis"]

        words = []
        for word in segment.get("words") or []:
            cell: dict = {}
            for key, value in word.items():
                if key == "analysis":
                    editorial_words.setdefault(word["id"], {})["analysis"] = value
                    continue
                cell[key] = value
            for key in WORD_LANG:
                by_lang = {
                    lang: (glosses[lang].get("words") or {}).get(word["id"], {})[key]
                    for lang in LANGS
                    if key in ((glosses[lang].get("words") or {}).get(word["id"]) or {})
                }
                if by_lang:
                    cell[key] = by_lang
            words.append(cell)
        if words:
            row["words"] = words
        segments.append(row)

    out["segments"] = segments
    editorial = {key: text[key] for key in EDITORIAL if key in text}
    for segment, row in zip(text["segments"], segments, strict=True):
        if "_editorial" in row:
            editorial.setdefault("segments", {})[segment["id"]] = row.pop("_editorial")
    if editorial_words:
        editorial["words"] = editorial_words
    out["editorial"] = editorial
    return out


def split(doc: dict) -> tuple[dict, dict[str, dict]]:
    """Three documents from one. The inverse, so the merge is reversible."""
    editorial = doc.get("editorial") or {}
    text: dict = {"schema_version": "0.13.0"}
    for key, value in doc.items():
        if key in ("schema_version", "segments", "editorial", "about", "about_citations"):
            continue
        text[key] = value
        if key == "status":
            pass
    for key in EDITORIAL:
        if key in editorial:
            text[key] = editorial[key]

    glosses: dict[str, dict] = {
        lang: {
            "schema_version": "0.13.0",
            "text": doc["id"],
            "lang": lang,
            "status": editorial.get("status", "working-edition"),
            "analysis_defaults": editorial.get("analysis_defaults", {}),
            "segments": {},
            "words": {},
        }
        for lang in LANGS
    }
    for key in ("about", "about_citations"):
        for lang in LANGS:
            if key in doc and lang in doc[key]:
                glosses[lang][key] = doc[key][lang]

    segments = []
    for row in doc["segments"]:
        segment: dict = {}
        for key, value in row.items():
            if key in SEGMENT_LANG or key == "words":
                continue
            segment[key] = value
        if (editorial.get("segments") or {}).get(row["id"], {}).get("analysis"):
            segment["analysis"] = editorial["segments"][row["id"]]["analysis"]
        for key in SEGMENT_LANG:
            for lang, value in (row.get(key) or {}).items():
                glosses[lang]["segments"].setdefault(row["id"], {})[key] = value

        words = []
        for cell in row.get("words") or []:
            word = {k: v for k, v in cell.items() if k not in WORD_LANG}
            if (editorial.get("words") or {}).get(cell["id"], {}).get("analysis"):
                word["analysis"] = editorial["words"][cell["id"]]["analysis"]
            words.append(word)
            for key in WORD_LANG:
                for lang, value in (cell.get(key) or {}).items():
                    glosses[lang]["words"].setdefault(cell["id"], {})[key] = value
        if words:
            segment["words"] = words
        segments.append(segment)
    text["segments"] = segments
    return text, glosses


def load(corpus: Path, text_id: str) -> tuple[dict, dict[str, dict]]:
    category, name = text_id.split(".", 1)
    text = json.loads((corpus / "texts" / category / f"{name}.json").read_text(encoding="utf-8"))
    glosses = {
        lang: json.loads(
            (corpus / "glosses" / lang / f"{text_id}.json").read_text(encoding="utf-8")
        )
        for lang in LANGS
    }
    return text, glosses
