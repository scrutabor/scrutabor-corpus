"""The Proper's celebrant/schola delivery changes with the Mass form."""

import json
from pathlib import Path

from checks.delivery import check_doc, derive

CORPUS = Path(__file__).resolve().parent.parent


def text(text_id: str) -> dict:
    category, name = text_id.split(".", 1)
    path = CORPUS / "texts" / category / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_a_proper_chant_has_a_sung_mass_override():
    doc = text("proprium.dominica-iv-adventus-communio")
    assert derive(doc, doc["segments"][0]) == {"cantu": {"speaker": "schola", "voice": "cantus"}}


def test_a_proper_oration_keeps_the_celebrants_base_delivery():
    doc = text("proprium.dominica-iv-adventus-collecta")
    assert derive(doc, doc["segments"][0]) == {}


def test_the_rule_does_not_depend_on_one_advent_formulary():
    for sunday in ("i", "ii", "iii", "iv"):
        doc = text(f"proprium.dominica-{sunday}-adventus-offertorium")
        assert derive(doc, doc["segments"][0])["cantu"]["speaker"] == "schola"


def test_a_stale_or_extra_override_is_rejected():
    doc = text("proprium.dominica-i-adventus-collecta")
    doc["segments"][0]["delivery"] = {"cantu": {"speaker": "schola"}}
    errors, _ = check_doc(doc)
    assert any("Mass forms require none" in error for error in errors)


def test_every_text_carries_the_derived_delivery():
    problems = []
    for path in sorted(CORPUS.glob("texts/*/*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        errors, _ = check_doc(doc)
        problems += [f"{doc['id']} {error}" for error in errors]
    assert problems == []
