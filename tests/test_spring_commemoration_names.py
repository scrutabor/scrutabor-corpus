"""Exact named-prayer membership, predecessor rejection and healthy recovery."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from checks import lint

ROOT = Path(__file__).resolve().parents[1]
JOINT = "proprium.sanctorum-alexandri-eventii-theoduli-et-iuvenalis-collecta"
CASES = (
    ("Athanasius", "proprium.sancti-athanasii-collecta", "w009", 51),
    ("Augustinus", "proprium.sanctae-monicae-collecta", "w018", 54),
    ("Eventius", JOINT, "w010", 44),
    ("Iuvenalis", JOINT, "w013", 44),
    ("Monica", "proprium.sanctae-monicae-collecta", "w011", 54),
    ("Theodulus", JOINT, "w011", 44),
)


def core(text):
    return json.loads((ROOT / "texts" / (text.replace(".", "/", 1) + ".json")).read_text())


def token(doc, word):
    return next(w for s in doc["segments"] for w in s.get("words", []) if w["id"] == word)


def healthy(doc, count):
    errors, observed = lint.lint_text(doc)
    assert errors == []
    assert observed == count


@pytest.mark.parametrize(("lemma", "text", "word", "count"), CASES)
def test_six_source_names_need_their_explicit_membership_and_recover(
    monkeypatch, lemma, text, word, count
):
    doc = core(text)
    saved = deepcopy(doc)
    assert token(doc, word)["lemma"] == lemma
    healthy(doc, count)
    diagnostic = f"{word}: lemma {lemma!r} capitalized but not in proper-name list (SCHEMA.md)"
    with monkeypatch.context() as limited:
        limited.setattr(lint, "PROPER_LEMMAS", lint.PROPER_LEMMAS - {lemma})
        errors, observed = lint.lint_text(doc)
        assert diagnostic in errors
        assert observed == count
    assert doc == saved
    healthy(doc, count)


def test_existing_alexander_remains_explicit_and_healthy():
    doc = core(JOINT)
    assert token(doc, "w009")["lemma"] == "Alexander"
    assert "Alexander" in lint.PROPER_LEMMAS
    healthy(doc, 44)


def test_unrelated_unknown_name_is_still_rejected_and_healthy_source_recovers():
    doc = core("proprium.sancti-athanasii-collecta")
    saved = deepcopy(doc)
    healthy(doc, 51)
    unknown = "Ficticius"
    assert unknown not in lint.PROPER_LEMMAS
    bad = deepcopy(doc)
    token(bad, "w009")["lemma"] = unknown
    errors, observed = lint.lint_text(bad)
    assert "w009: lemma 'Ficticius' capitalized but not in proper-name list (SCHEMA.md)" in errors
    assert observed == 51
    assert doc == saved
    healthy(doc, 51)
