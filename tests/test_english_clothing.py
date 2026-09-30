"""English clothing distinguishes the person from the garment."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.layers import enrich_layer, expand_core
from checks import english

ROOT = Path(__file__).resolve().parents[1]
NAME = "dominica-v-post-epiphaniam-epistola"


def example():
    core = json.loads((ROOT / f"texts/proprium/{NAME}.json").read_text())
    layer = json.loads((ROOT / f"languages/en/texts/proprium/{NAME}.json").read_text())
    doc, gloss = expand_core(core), enrich_layer(core, layer)
    gloss["words"]["w002"]["gloss"] = "Put on"
    gloss["words"]["w003"]["gloss"] = "yourselves"
    return doc, gloss


def matches(doc, gloss):
    return [
        error for error in english.check(doc, gloss) if "treat the person as a garment" in error
    ]


def test_real_formulary_has_positive_control_and_dispatch(monkeypatch):
    doc, gloss = example()
    errors = matches(doc, gloss)
    assert len(errors) == 1 and "w002–w003" in errors[0]
    monkeypatch.setattr(english, "check_reflexive_clothing", lambda *_: [])
    assert matches(doc, gloss) == []


@pytest.mark.parametrize(
    "left,right",
    [
        ("Put on", "yourselves"),
        (" PUT  ON\t", " YOURSELVES "),
        ("put\u00a0on", "yourselves"),
    ],
)
def test_spacing_and_case_do_not_hide_the_junction(left, right):
    doc, gloss = example()
    gloss["words"]["w002"]["gloss"] = left
    gloss["words"]["w003"]["gloss"] = right
    assert len(matches(doc, gloss)) == 1


@pytest.mark.parametrize(
    "left,right",
    [
        ("Clothe", "yourselves"),
        ("Put", "on yourselves"),
        ("Put on", "armor"),
        (None, "yourselves"),
        ("Put on", None),
    ],
)
def test_other_realizations_are_not_judged(left, right):
    doc, gloss = example()
    gloss["words"]["w002"]["gloss"] = left
    gloss["words"]["w003"]["gloss"] = right
    assert matches(doc, gloss) == []


@pytest.mark.parametrize(
    "index,key,value",
    [
        (1, "lemma", "pono"),
        (2, "lemma", "ego"),
        (1, "pos", "noun"),
        (1, "mood", "ind"),
        (1, "person", 1),
        (1, "number", "sg"),
        (2, "pos", "noun"),
        (2, "case", "nom"),
        (2, "number", "sg"),
    ],
)
def test_only_the_declared_morphology_is_matched(index, key, value):
    doc, gloss = example()
    word = doc["segments"][0]["words"][index]
    (word if key == "lemma" else word["morph"])[key] = value
    assert matches(doc, gloss) == []


@pytest.mark.parametrize("index,key", [(1, "post"), (2, "pre")])
def test_punctuation_boundaries_are_not_crossed(index, key):
    doc, gloss = example()
    doc["segments"][0]["words"][index][key] = ";"
    assert matches(doc, gloss) == []


def test_segment_boundary_is_not_crossed():
    doc, gloss = example()
    segment = doc["segments"][0]
    tail = deepcopy(segment)
    tail["id"] = "s02"
    tail["words"] = segment["words"][2:]
    segment["words"] = segment["words"][:2]
    doc["segments"].append(tail)
    gloss["segments"]["s02"] = {}
    assert matches(doc, gloss) == []


@pytest.mark.parametrize(
    "alignment",
    [
        {"words": ["w002", "w003"], "anchor": "w002", "gloss": "Clothe yourselves"},
        {"words": ["w003"], "zero": "inflection"},
    ],
)
def test_grouped_and_zero_members_belong_to_provider_checks(alignment):
    doc, gloss = example()
    gloss["segments"]["s01"].setdefault("alignments", []).append(alignment)
    assert matches(doc, gloss) == []


def test_missing_direct_provider_is_not_an_english_junction():
    doc, gloss = example()
    del gloss["words"]["w003"]
    assert matches(doc, gloss) == []


def test_language_dispatch_and_empty_segments():
    doc, gloss = example()
    gloss["lang"] = "pl"
    assert english.check(doc, gloss) == []
    assert english.check_reflexive_clothing({"segments": []}, {}) == []


def test_complete_corpus_has_no_clothing_junction_errors():
    count = 0
    for path in sorted((ROOT / "texts").glob("*/*.json")):
        core = json.loads(path.read_text())
        layer = json.loads(
            (ROOT / "languages/en/texts" / path.relative_to(ROOT / "texts")).read_text()
        )
        assert not english.check_reflexive_clothing(expand_core(core), enrich_layer(core, layer)), (
            core["id"]
        )
        count += 1
    assert count >= 1105
