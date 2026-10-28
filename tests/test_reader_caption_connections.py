"""Recipients, complements and government survive the reader projection."""

from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import store
from build_reader.emit import Table, core_artifact, expand, language_artifact
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs

ROOT = Path(__file__).resolve().parents[1]
HAEC = "ordinarium.haec-commixtio"
GOSPEL = "proprium.commemoratio-omnium-fidelium-defunctorum-missa-i-evangelium"
SECRET = "proprium.commemoratio-omnium-fidelium-defunctorum-missa-i-secreta"
CASES = ("recipient", "grant-complement", "wonder-dative", "regard-object")
SUBJECTS = {
    "recipient": (HAEC, "en", "s02"),
    "grant-complement": (GOSPEL, "pl", "s01"),
    "wonder-dative": (GOSPEL, "pl", "s01"),
    "regard-object": (SECRET, "pl", "s01"),
}
SCALARS = {
    "grant-complement": ("w039", "by miał", "miał", "by będzie miał"),
    "wonder-dative": ("w055", "temu", "to", "tego"),
    "regard-object": ("w001", "Na ofiary", "Ofiary", "Na ofiarom"),
}


def load(case):
    text, language, _ = SUBJECTS[case]
    return store.core(ROOT, text), store.raw_layer(ROOT, language, text)


def reader(core, layer):
    doc, target = expand_core(core), enrich_layer(core, layer)
    assert language_packs.check_core(core) == [], "native core"
    path = ROOT / "languages" / layer["language"] / "texts"
    path = path / (core["id"].replace(".", "/", 1) + ".json")
    assert language_packs.check_layer(core, layer, path) == [], "native language"
    assert interlinear.check(doc, target) == [], "native realization"
    parses, analyses, shared, local = Table(), Table(), Table(), Table()
    neutral = core_artifact(doc, core, parses, analyses, shared)
    localized = language_artifact(doc, target, local)
    back, received = expand(
        neutral, localized, parses.order, analyses.order, shared.order, local.order
    )
    assert back["segments"] == doc["segments"]
    assert received["words"] == target["words"]
    for segment in core["segments"]:
        name = segment["id"]
        assert received["segments"].get(name, {}).get("alignments") == target["segments"].get(
            name, {}
        ).get("alignments")
    return received, localized


def meaning(case, core, layer):
    received, artifact = reader(core, layer)
    words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    segment = SUBJECTS[case][2]
    emitted = next(row for row in artifact["seg"] if row["id"] == segment)
    if case == "recipient":
        assert words["w013"]["morph"]["case"] == words["w014"]["morph"]["case"] == "dat"
        assert words["w013"]["morph"]["number"] == "pl"
        assert words["w013"]["morph"]["voice"] == "act"
        assert words["w013"]["morph"]["tense"] == "pres"
        assert words["w013"]["head"] == "w014"
        groups = [
            g
            for g in received["segments"][segment].get("alignments", [])
            if set(g["words"]) & {"w013", "w014"}
        ]
        assert groups == [
            {"words": ["w013", "w014"], "anchor": "w014", "gloss": "for us who receive"}
        ], "human recipient"
        assert interlinear.effective_gloss(received, "w013") == ""
        assert interlinear.effective_gloss(received, "w014") == "for us who receive"
        assert emitted["g"][12:14] == [None, None]
        assert [a for a in emitted["a"] if a["s"] == 12] == [
            {"s": 12, "n": 2, "a": 1, "g": "for us who receive"}
        ]
    else:
        word, expected, _, _ = SCALARS[case]
        assert interlinear.effective_gloss(received, word) == expected, case
        assert not any(
            word in g["words"] for g in received["segments"][segment].get("alignments", [])
        )
        if case == "grant-complement":
            assert words[word]["morph"]["mood"] == "inf"
            assert words["w038"]["morph"]["case"] == "dat"
            assert layer["words"]["w036"]["gloss"] == "dał"
            assert layer["words"]["w038"]["gloss"] == "Synowi"
        elif case == "wonder-dative":
            assert words[word]["morph"]["case"] == "acc"
            assert layer["words"]["w053"]["gloss"] == "nie"
            assert layer["words"]["w054"]["gloss"] == "dziwcie się"
        else:
            assert words[word]["morph"]["case"] == "acc"
            assert words["w013"]["morph"]["mood"] == "imp"
            assert layer["words"]["w013"]["gloss"] == "wejrzyj"
            assert layer["words"]["w004"]["gloss"] == "które"


@pytest.mark.parametrize("case", CASES)
def test_current_connections_reach_the_real_reader(case):
    meaning(case, *load(case))


@pytest.mark.parametrize("case", CASES)
def test_predecessor_and_wrong_relationship_fail_then_restore(case):
    core, layer = load(case)
    saved = deepcopy(layer)
    meaning(case, core, layer)
    faults = ("old", "recipient", "duplicate", "anchor", "missing-member")
    if case != "recipient":
        faults = ("old", "wrong-government")
    for fault in faults:
        try:
            if case == "recipient":
                group = layer["segments"]["s02"]["alignments"][0]
                if fault == "old":
                    del layer["segments"]["s02"]["alignments"]
                    layer["words"]["w013"]["gloss"] = "receiving"
                    layer["words"]["w014"]["gloss"] = "to us"
                elif fault == "recipient":
                    group["gloss"] = "for the mingling which receives"
                elif fault == "duplicate":
                    layer["words"]["w013"]["gloss"] = "receiving"
                elif fault == "anchor":
                    group["anchor"] = "w012"
                else:
                    group["words"].pop()
            else:
                word, _, old, wrong = SCALARS[case]
                layer["words"][word]["gloss"] = old if fault == "old" else wrong
            assert layer != saved
            if fault in ("duplicate", "anchor", "missing-member"):
                errors = interlinear.check(expand_core(core), enrich_layer(core, layer))
                diagnostic = "anchor" if fault == "anchor" else "exactly one"
                assert any(diagnostic in error for error in errors)
            with pytest.raises(AssertionError):
                meaning(case, core, layer)
        finally:
            layer.clear()
            layer.update(deepcopy(saved))
        assert layer == saved
        meaning(case, core, layer)


def test_neighboring_valid_infinitives_cases_and_recipients_are_retained():
    controls = [
        (HAEC, "pl", {"w013": "przyjmującym", "w014": "nam", "w015": "ku"}),
        (GOSPEL, "pl", {"w031": "ma", "w048": "czynić"}),
        (GOSPEL, "en", {"w039": "to have", "w048": "to render", "w055": "this"}),
        (SECRET, "pl", {"w004": "które", "w005": "Tobie", "w012": "przebłagany"}),
        (SECRET, "en", {"w001": "Sacrificial offerings", "w004": "which"}),
    ]
    for text, language, expected in controls:
        core, layer = store.core(ROOT, text), store.raw_layer(ROOT, language, text)
        received, _ = reader(core, layer)
        assert {word: interlinear.effective_gloss(received, word) for word in expected} == expected
