"""Passion actors must match the source-bound delivery rule, not stored labels."""

import json
from pathlib import Path

import pytest

from checks.delivery import check_doc

CORPUS = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("actor", ["christus", "synagoga", "sacerdos", "schola"])
def test_the_first_passion_narrator_cannot_be_a_different_legal_actor(actor):
    path = CORPUS / "texts/proprium/dominica-ii-passionis-evangelium.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    errors, _ = check_doc(doc)
    assert errors == [], errors
    first = next(s for s in doc["segments"] if s["id"] == "s01")
    assert first["delivery"]["cantu"]["speaker"] == "chronista"
    first["delivery"]["cantu"]["speaker"] = actor
    errors, _ = check_doc(doc)
    assert any("s01:" in error and "chronista" in error for error in errors), errors
