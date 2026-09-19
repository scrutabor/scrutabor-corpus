"""The prayer invokes Mary's companions, not an abstract fellowship."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REL = Path("proprium/septem-dolorum-beatae-mariae-virginis-secreta.json")


def test_personal_companions_and_their_intercession():
    text = json.loads((ROOT / "texts" / REL).read_text())
    words = {w["id"]: w for s in text["segments"] for w in s["words"]}
    assert len(words) == 54
    assert words["w027"]["lemma"] == "consors"
    assert words["w027"]["morph"]["case"] == "gen"
    assert words["w027"]["morph"]["number"] == "pl"
    assert words["w022"]["head"] == "w030"
    assert words["w028"]["head"] == "w030"
    assert words["w023"]["head"] == "w027"
    assert words["w026"]["head"] == "w027"
    assert words["w012"]["morph"]["number"] == "pl"
    assert words["w014"]["head"] == "w015"
    assert words["w014"]["morph"]["gender"] == "m"
    assert "decl" not in words["w007"]["morph"]
    assert text["editorial"]["words"]["w049"]["analysis"]["confidence"] == "medium"


@pytest.mark.parametrize("language", ["pl", "en"])
def test_delayed_intercession_is_realized_once(language):
    layer = json.loads((ROOT / "languages" / language / "texts" / REL).read_text())
    expected = [f"w{n:03}" for n in range(22, 31)]
    matches = [a for a in layer["segments"]["s01"]["alignments"] if a["words"] == expected]
    assert len(matches) == 1
    assert matches[0]["anchor"] == "w030"
    assert all("gloss" not in layer["words"][wid] for wid in expected)
    translation = layer["segments"]["s01"]["translation"]
    markers = (
        ["duszy", "jej świętych towarzyszy", "zasługi Twojej śmierci", "nagrody"]
        if language == "pl"
        else ["soul", "her holy companions", "merits of Your death", "reward"]
    )
    for marker in markers:
        assert marker in translation
    assert layer["segments"]["s03"]["translation"] == "Amen."


@pytest.mark.parametrize("language", ["pl", "en"])
def test_lexicon_explains_intercession_and_reward(language):
    entries = json.loads((ROOT / "languages" / language / "lexicon.json").read_text())["entries"]
    assert ("wstawiennictwo" if language == "pl" else "intercession") in entries["interventus"][
        "senses"
    ]
    assert ("nagroda" if language == "pl" else "reward") in entries["meritum"]["senses"]


def test_dictionary_heads_preserve_conjugation_stress():
    entries = json.loads((ROOT / "lexicon/lemmata.json").read_text())["entries"]
    assert "supplicáre" in entries["supplico"]["head"]
    assert "multiplicáre" in entries["multiplico"]["head"]
    assert "recensére" in entries["recenseo"]["head"]
    assert entries["interventus"]["head"] == "intervéntus, -us"
