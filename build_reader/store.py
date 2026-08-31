"""Read neutral text cores and independently publishable language packs."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

from build_reader.layers import enrich_layer, expand_core


def text_ids(corpus: Path) -> list[str]:
    return [f"{p.parent.name}.{p.stem}" for p in sorted(corpus.glob("texts/*/*.json"))]


def path_of(corpus: Path, text_id: str) -> Path:
    category, name = text_id.split(".", 1)
    return corpus / "texts" / category / f"{name}.json"


def core(corpus: Path, text_id: str) -> dict:
    """The neutral document exactly as it is stored."""
    return json.loads(path_of(corpus, text_id).read_text(encoding="utf-8"))


def language_ids(corpus: Path) -> list[str]:
    return [path.parent.name for path in sorted((corpus / "languages").glob("*/manifest.json"))]


@cache
def _manifest(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def language_manifest(corpus: Path, language: str) -> dict:
    return _manifest(str(corpus / "languages" / language / "manifest.json"))


@cache
def _translation_relationships(corpus_path: str, language: str) -> dict[str, str]:
    """Expand the compact public relationship groups to stable site keys."""
    corpus = Path(corpus_path)
    path = corpus / "languages" / language / "translation-basis.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for record in doc.get("records") or []:
        for text_id in record["texts"]:
            core_doc = core(corpus, text_id)
            segments = record.get("segments") or [
                segment["id"]
                for segment in core_doc.get("segments") or []
                if segment.get("type") == "verse"
            ]
            for segment_id in segments:
                out[f"{text_id}.{segment_id}.{language}"] = record["relationship"]
    return out


def translation_relationships(corpus: Path, language: str) -> dict[str, str]:
    return _translation_relationships(str(corpus), language)


def layer_path(corpus: Path, language: str, text_id: str) -> Path:
    category, name = text_id.split(".", 1)
    return corpus / "languages" / language / "texts" / category / f"{name}.json"


def raw_layer(corpus: Path, language: str, text_id: str) -> dict:
    return json.loads(layer_path(corpus, language, text_id).read_text(encoding="utf-8"))


def languages_for(corpus: Path, text_id: str) -> list[str]:
    return [
        language
        for language in language_ids(corpus)
        if text_id in language_manifest(corpus, language).get("texts", [])
    ]


def load(corpus: Path, text_id: str) -> tuple[dict, dict[str, dict]]:
    """A neutral checking document and every published layer for this text."""
    stored = core(corpus, text_id)
    return expand_core(stored), {
        language: enrich_layer(stored, raw_layer(corpus, language, text_id))
        for language in languages_for(corpus, text_id)
    }


def all_texts(corpus: Path) -> list[tuple[dict, dict[str, dict]]]:
    return [load(corpus, text_id) for text_id in text_ids(corpus)]


def formularies(corpus: Path) -> list[dict]:
    """Return the authored Mass assemblies in stable collection/id order."""
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(corpus.glob("formularies/*/*.json"))
    ]


def language_formularies(corpus: Path, language: str) -> list[dict]:
    """Return one language package's localized formulary metadata."""
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((corpus / "languages" / language).glob("formularies/*/*.json"))
    ]
