"""The eighth Sunday asks sanctification, not the preceding Sunday's petition."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REL = Path("proprium/dominica-viii-post-pentecosten-secreta.json")


def test_mysteries_are_the_subject_and_eternal_qualifies_joys():
    doc = json.loads((ROOT / "texts" / REL).read_text())
    words = {w["id"]: w for s in doc["segments"] for w in s["words"]}
    assert words["w014"]["morph"]["case"] == "nom"
    assert words["w013"]["head"] == "w014"
    assert words["w028"]["morph"] == {"pos": "adj", "case": "acc", "number": "pl", "gender": "n"}
    assert words["w028"]["head"] == "w027"
    assert "substantive" not in words["w028"]
    assert words["w032"]["head"] == "w031"


@pytest.mark.parametrize("language", ["pl", "en"])
def test_translation_keeps_grace_present_life_and_eternal_joy(language):
    text = json.loads((ROOT / "languages" / language / "texts" / REL).read_text())
    translation = text["segments"]["s01"]["translation"]
    markers = (
        ["dary", "łaski", "obecnym życiu", "wiecznych radości"]
        if language == "pl"
        else ["gifts", "grace", "present life"]
    )
    for marker in markers:
        assert marker in translation
    if language == "en":
        assert any(marker in translation for marker in ("eternal joy", "everlasting joy"))
    assert "Abl" not in translation and "Abel" not in translation
    assert text["segments"]["s03"]["translation"] == "Amen."


def test_english_lexical_cards_include_the_ordinary_liturgical_senses():
    entries = json.loads((ROOT / "languages/en/lexicon.json").read_text())["entries"]
    assert "to bring" in entries["defero"]["senses"]
    assert "to offer" in entries["defero"]["senses"]
    assert "conduct" in entries["conversatio"]["senses"]
    assert "way of life" in entries["conversatio"]["senses"]
