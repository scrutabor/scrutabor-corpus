"""A full-rendering label belongs to one language and survives compression."""

import copy
import json
from pathlib import Path

import pytest

from build_reader.emit import Table, core_artifact, expand, language_artifact
from build_reader.layers import enrich_layer, expand_core
from checks.language_packs import check_core, check_layer

ROOT = Path(__file__).resolve().parent.parent
LABEL = "Przekład hymniczny ks. Tadeusza Karyłowskiego"


def subject(language="pl"):
    core = json.loads((ROOT / "texts/orationes/te-deum.json").read_text())
    path = ROOT / f"languages/{language}/texts/orationes/te-deum.json"
    return core, json.loads(path.read_text()), path


def test_actual_label_is_language_owned_and_uses_the_approved_rendering():
    core, pl, path = subject()
    _, en, _ = subject("en")
    assert pl["translation_label"] == LABEL
    assert "translation_label" not in core
    assert "translation_label" not in en
    assert check_core(core) == []
    assert check_layer(core, pl, path) == []


@pytest.mark.parametrize("invalid", [None, False, 7, [], {}, "", "  "])
def test_label_rejects_non_strings_and_empty_values(invalid):
    core, layer, path = subject()
    layer["translation_label"] = invalid
    assert any(
        "translation_label must be a nonempty string" in e for e in check_layer(core, layer, path)
    )


def test_label_is_optional_but_cannot_move_into_the_neutral_core():
    core, layer, path = subject()
    del layer["translation_label"]
    assert check_layer(core, layer, path) == []
    core["translation_label"] = LABEL
    assert any("localized document fields" in e for e in check_core(core))


def test_label_requires_an_actual_verse_rendering():
    core = {
        "id": "orationes.test",
        "category": "orationes",
        "schema_version": "0.21.0",
        "segments": [],
    }
    layer = {
        "text": core["id"],
        "language": "pl",
        "schema_version": "0.21.0",
        "about": "Test.",
        "translation_label": LABEL,
        "segments": {},
        "words": {},
    }
    assert any(
        "translation_label requires a verse translation" in e
        for e in check_layer(core, layer, Path("orationes/test.json"))
    )


def test_label_round_trips_without_altering_verses_or_interlinear_data():
    core, raw_layer, _ = subject()
    doc = expand_core(core)
    layer = enrich_layer(core, raw_layer)
    before = copy.deepcopy(layer)
    parses, analyses, shared, localized = Table(), Table(), Table(), Table()
    base = core_artifact(doc, core, parses, analyses, shared)
    language = language_artifact(doc, layer, localized)
    assert language["translation_label"] == LABEL
    assert "translation_label" not in base
    _, restored = expand(
        base, language, parses.order, analyses.order, shared.order, localized.order
    )
    assert restored["translation_label"] == LABEL
    assert restored["segments"] == layer["segments"]
    assert restored["words"] == layer["words"]
    assert layer == before
    del layer["translation_label"]
    assert "translation_label" not in language_artifact(doc, layer, Table())
