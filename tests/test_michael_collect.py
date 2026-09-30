"""Saint Michael's Collect: agency, service and the complete petition."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.layers import expand_core
from checks import interlinear
from checks.raw_binding import resolve_binding
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
NAME = "dedicatio-sancti-michaelis-archangeli-collecta"
TEXT = "proprium." + NAME
AGENTS = [f"w{i:03}" for i in range(12, 22)]
GLOSSES = {
    "pl": "przez tych, którzy służąc, zawsze stoją przy Tobie w niebie",
    "en": "by those who always stand in heaven ministering to You",
}


def core():
    return json.loads((ROOT / "texts/proprium" / f"{NAME}.json").read_text())


def layer(language):
    return json.loads((ROOT / f"languages/{language}/texts/proprium/{NAME}.json").read_text())


def test_complete_prayer_keeps_its_impersonal_passive_and_response():
    doc = core()
    assert [s["id"] for s in doc["segments"]] == ["s01", "s02"]
    assert [len(s["words"]) for s in doc["segments"]] == [47, 1]
    words = {w["id"]: w for s in doc["segments"] for w in s["words"]}
    assert words["w019"] == {
        "id": "w019",
        "form": "assístitur",
        "lemma": "assisto",
        "morph": {
            "pos": "verb",
            "mood": "ind",
            "number": "sg",
            "person": 3,
            "tense": "pres",
            "voice": "pass",
            "conj": 3,
        },
        "post": ",",
    }
    assert words["w026"]["morph"]["voice"] == "pass"
    assert words["w048"]["form"] == "Amen"
    assert [(s["speaker"], s["voice"]) for s in doc["segments"]] == [
        ("sacerdos", "clara"),
        ("minister", "clara"),
    ]


@pytest.mark.parametrize("wid", ["w013", "w021"])
def test_same_angelic_agents_have_contextual_gender_without_inherited_approval(wid):
    doc = core()
    word = next(w for w in expand_core(doc)["segments"][0]["words"] if w["id"] == wid)
    assert word["morph"]["gender"] == "m"
    assert word["morph"]["case"] == "abl"
    assert word["analysis"] == {
        "confidence": "high",
        "sources": ["editorial", "whitakers", "collatinus"],
        "review": "pending",
    }


@pytest.mark.parametrize("language", ["pl", "en"])
def test_one_relative_agent_group_preserves_service_attendance_and_place(language):
    doc, data = core(), layer(language)
    group = next(g for g in data["segments"]["s01"]["alignments"] if g["words"] == AGENTS)
    assert group == {"words": AGENTS, "anchor": "w013", "gloss": GLOSSES[language]}
    assert interlinear.check(doc, data) == []
    for wid in AGENTS:
        assert "gloss" not in data["words"][wid]
        duplicate = deepcopy(data)
        duplicate["words"][wid]["gloss"] = "extra"
        assert interlinear.check(doc, duplicate)
        missing = deepcopy(data)
        next(g for g in missing["segments"]["s01"]["alignments"] if g["words"] == AGENTS)[
            "words"
        ].remove(wid)
        assert interlinear.check(doc, missing)


def test_polish_keeps_coordination_earth_surface_and_familiar_conclusion():
    data = layer("pl")
    assert data["words"]["w007"]["gloss"] == "i ludzi"
    assert data["words"]["w022"]["gloss"] == "na"
    assert data["words"]["w026"]["gloss"] == "było strzeżone"
    conclusion = "Przez Pana" + data["segments"]["s01"]["translation"].split("Przez Pana", 1)[1]
    assert (
        hashlib.sha256(conclusion.encode()).hexdigest()
        == "41f118623434bf92b3a063601d66a4d5bdd66cfb5bd7647af63c2ea3b6d42503"
    )
    assert data["about"].startswith("Kolekta formularza")


def test_english_keeps_manner_and_both_coordinated_possessors():
    data = layer("en")
    assert data["segments"]["s01"]["alignments"][0] == {
        "words": ["w003", "w004"],
        "anchor": "w004",
        "gloss": "in wondrous order",
    }
    assert [data["words"][w]["gloss"] for w in ["w005", "w006", "w007"]] == [
        "angels’",
        "duties",
        "and men’s",
    ]
    assert data["words"]["w022"]["gloss"] == "on"


def test_english_conclusion_uses_one_contemporary_register():
    data = layer("en")
    assert {
        w: data["words"][w]["gloss"]
        for w in ["w008", "w027", "w033", "w034", "w035", "w036", "w038"]
    } == {
        "w008": "assign",
        "w027": "Through",
        "w033": "Your",
        "w034": "who",
        "w035": "with You",
        "w036": "lives",
        "w038": "reigns",
    }
    assert data["segments"]["s01"]["translation"].endswith(
        "Through our Lord Jesus Christ, Your Son, who lives and reigns with You "
        "in the unity of the Holy Spirit, God, for ever and ever."
    )
    assert data["segments"]["s02"]["translation"] == "Amen."
    assert data["about"].startswith("The Collect of")


@pytest.mark.parametrize("language", ["pl", "en"])
def test_current_provenance_remains_working_and_bound_to_both_payloads(language):
    data = layer(language)
    sites = json.loads((ROOT / f"languages/{language}/translation-provenance.json").read_text())[
        "sites"
    ]
    site = next(s for s in sites if s["site"] == f"{TEXT}.s01.{language}")
    assert site["source_sha256"] == canonical_hash(source_payload(core()["segments"][0]))
    assert site["target_sha256"] == canonical_hash(data["segments"]["s01"]["translation"])
    assert (site["origin"], site["review"], site["familiar_core"]) == (
        "working-unsettled",
        "working",
        False,
    )


def test_digital_binding_resolves_the_body_conclusion_and_response():
    bound = resolve_binding(ROOT / "witnesses" / TEXT / "do.txt", ROOT)
    assert bound is not None
    assert len(bound.text.split()) == 48
    assert bound.text.split()[:2] == ["Deus,", "qui,"]
    assert bound.text.split()[-1] == "Amen."
