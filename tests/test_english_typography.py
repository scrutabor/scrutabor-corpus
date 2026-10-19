"""Typography checks cover every current English reader layer."""

import json
from pathlib import Path

import pytest

from checks.english import check_apostrophes

ROOT = Path(__file__).resolve().parents[1]


def test_all_english_reader_layers_use_typographic_apostrophes():
    neutral_root = ROOT / "texts"
    english_root = ROOT / "languages/en/texts"
    neutral = {p.relative_to(neutral_root) for p in neutral_root.glob("*/*.json")}
    english = {p.relative_to(english_root) for p in english_root.glob("*/*.json")}
    assert neutral, "The current corpus must not be empty"
    assert english == neutral, "Every current text needs an English reader layer"
    errors = []
    for relative in sorted(english):
        layer = json.loads((english_root / relative).read_text(encoding="utf-8"))
        assert layer["language"] == "en"
        assert layer["text"] == f"{relative.parent.name}.{relative.stem}"
        errors.extend(check_apostrophes(layer))
    assert errors == []


@pytest.mark.parametrize(
    "field",
    [
        ("about",),
        ("segments", "s01", "translation"),
        ("segments", "s01", "narrative"),
        ("segments", "s01", "alignments", 0, "gloss"),
        ("words", "w001", "gloss"),
        ("words", "w001", "explanation"),
        ("words", "w001", "note"),
    ],
)
def test_apostrophe_check_covers_each_reader_field(field):
    layer = {
        "text": "test.prayer",
        "segments": {"s01": {"alignments": [{"words": ["w001", "w002"]}]}},
        "words": {"w001": {}},
    }
    parent = layer
    for key in field[:-1]:
        parent = parent[key]
    parent[field[-1]] = "the Lord’s right hand"
    assert check_apostrophes(layer) == []
    parent[field[-1]] = "the Lord's right hand"
    errors = check_apostrophes(layer)
    assert len(errors) == 1
    assert "straight apostrophe" in errors[0]
    parent[field[-1]] = "the Lord’s right hand"
    assert check_apostrophes(layer) == []
