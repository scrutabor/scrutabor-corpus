"""Three short English constructions preserve the source contribution exactly once."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from offertory_rubric_successor_fixture import before_offertory_core_bytes

from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs, prose

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads(
    (ROOT / "tests/fixtures/magnificat-lavabo-constructions.json").read_text(encoding="utf-8")
)
CASES = FIXTURE["cases"]
TOPOLOGY = ("split", "residual", "duplicate", "anchor", "order", "too-wide")
SEMANTIC = [(case, wrong) for case in CASES for wrong in case["wrong"]]


def path_of(text, language=None):
    root = ROOT if language is None else ROOT / "languages" / language
    return root / "texts" / (text.replace(".", "/", 1) + ".json")


def load(case):
    return (
        json.loads(path_of(case["text"]).read_bytes()),
        json.loads(path_of(case["text"], "en").read_bytes()),
    )


def unit(case, layer):
    groups = layer["segments"][case["segment"]].get("alignments", [])
    touching = [g for g in groups if set(g["words"]) & set(case["words"])]
    assert touching == [case["group"]], "one minimal construction"
    assert not any("gloss" in layer["words"][w] for w in case["words"]), (
        "one realization per source word"
    )
    return touching[0]


def healthy(case, core, layer):
    text = case["text"]
    saved = FIXTURE["texts"][text]
    assert core["id"] == layer["text"] == text and layer["language"] == "en"
    words = next(s["words"] for s in core["segments"] if s["id"] == case["segment"])
    start = next(i for i, w in enumerate(words) if w["id"] == case["words"][0])
    assert words[start : start + 2] == case["source_words"]
    group = unit(case, layer)
    assert group["gloss"] == case["group"]["gloss"]
    assert language_packs.check_core(core) == []
    assert language_packs.check_layer(core, layer, path_of(text, "en")) == []
    assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
    assert prose.check(layer) == []
    assert layer["about"] == saved["about"]
    assert {
        sid: {k: v for k, v in segment.items() if k != "alignments"}
        for sid, segment in layer["segments"].items()
    } == saved["segment_fields"]
    expected = deepcopy(saved["old_alignments"])
    for other in CASES:
        if other["text"] == text:
            expected.setdefault(other["segment"], []).append(other["group"])
    source_order = {
        s["id"]: {w["id"]: i for i, w in enumerate(s.get("words", []))} for s in core["segments"]
    }
    for sid, groups in expected.items():
        groups.sort(key=lambda g: source_order[sid][g["words"][0]])
    assert {
        sid: segment["alignments"]
        for sid, segment in layer["segments"].items()
        if "alignments" in segment
    } == expected
    for wid, note in saved["predicate_notes"].items():
        assert layer["words"][wid]["explanation"] == note
    if text == "ordinarium.lavabo":
        assert layer["words"]["w053"]["gloss"] == "I"
        assert "I have walked" not in layer["words"]["w059"]["explanation"]
    else:
        indexed = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
        assert indexed["w016"]["morph"]["case"] == indexed["w017"]["morph"]["case"] == "gen"
        assert indexed["w017"]["head"] == "w016"
    comparison = before_offertory_core_bytes(text, path_of(text).read_bytes())
    assert hashlib.sha256(comparison).hexdigest() == saved["core_sha256"]
    assert hashlib.sha256(path_of(text, "pl").read_bytes()).hexdigest() == saved["pl_sha256"]


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_three_actual_short_constructions(case):
    healthy(case, *load(case))


@pytest.mark.parametrize(
    "case,fault",
    [(case, fault) for case in CASES for fault in TOPOLOGY],
    ids=[f"{case['id']}-{fault}" for case in CASES for fault in TOPOLOGY],
)
def test_minimal_group_and_token_accountability_reject_then_restore(case, fault):
    core, layer = load(case)
    healthy(case, core, layer)
    saved = deepcopy(layer)
    group = unit(case, layer)
    groups = layer["segments"][case["segment"]]["alignments"]
    try:
        if fault == "split":
            groups.remove(group)
            for wid, gloss in zip(case["words"], case["old_glosses"], strict=True):
                layer["words"][wid]["gloss"] = gloss
        elif fault == "residual":
            layer["words"][case["words"][0]]["gloss"] = case["group"]["gloss"]
        elif fault == "duplicate":
            groups.append(deepcopy(group))
        elif fault == "anchor":
            group["anchor"] = next(w for w in case["words"] if w != group["anchor"])
        elif fault == "order":
            group["words"].reverse()
        else:
            group["words"].append(case["next_word"])
        assert layer != saved
        with pytest.raises(
            AssertionError,
            match=r"^one (?:minimal construction|realization per source word)(?:\n|$)",
        ):
            unit(case, layer)
    finally:
        layer.clear()
        layer.update(saved)
        assert layer == saved
        healthy(case, core, layer)


@pytest.mark.parametrize(
    "case,wrong", SEMANTIC, ids=[f"{c['id']}-{i}" for i, (c, _) in enumerate(SEMANTIC)]
)
def test_genitive_divine_possessive_and_active_perfect_are_not_lost(case, wrong):
    core, layer = load(case)
    healthy(case, core, layer)
    saved = deepcopy(layer)
    group = unit(case, layer)
    try:
        group["gloss"] = wrong
        assert wrong != case["group"]["gloss"] and layer != saved
        with pytest.raises(AssertionError, match=r"^one minimal construction(?:\n|$)"):
            unit(case, layer)
    finally:
        group["gloss"] = case["group"]["gloss"]
        assert layer == saved
        healthy(case, core, layer)


@pytest.mark.parametrize("fault", ("ego", "quote"))
def test_lavabo_subject_and_matching_predicate_note_reject_then_restore(fault):
    case = next(c for c in CASES if c["text"] == "ordinarium.lavabo")
    core, layer = load(case)
    healthy(case, core, layer)
    saved = deepcopy(layer)
    try:
        if fault == "ego":
            layer["words"]["w053"]["gloss"] = ""
        else:
            layer["words"]["w059"]["explanation"] = (
                "With “ingréssus” it forms the single predicate “I have walked”."
            )
            assert prose.check(layer) == [
                "ordinarium.lavabo:w059.explanation.en: quoted shared predicate "
                "'I have walked' differs from its gloss 'have walked'"
            ]
        assert layer != saved
        with pytest.raises(AssertionError):
            healthy(case, core, layer)
    finally:
        layer.clear()
        layer.update(saved)
        assert layer == saved
        healthy(case, core, layer)
