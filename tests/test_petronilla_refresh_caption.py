"""Keep the reused refresh-us imperative local and in natural English order."""

from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

from checks import language_packs

ROOT = Path(__file__).resolve().parent.parent
CASES = (
    ("proprium.sanctae-petronillae-postcommunio", "s01", "w011", "w012"),
    ("proprium.nativitas-domini-in-aurora-postcommunio", "s03", "w048", "w049"),
)


def load_case(case):
    text = case[0]
    relative = text.replace(".", "/", 1) + ".json"
    core = json.loads((ROOT / "texts" / relative).read_text(encoding="utf-8"))
    path = ROOT / "languages" / "en" / "texts" / relative
    layer = json.loads(path.read_text(encoding="utf-8"))
    return core, layer, path


def assert_refresh_group(core, layer, case):
    _, segment_id, nos_id, refove_id = case
    segment = next(s for s in core["segments"] if s["id"] == segment_id)
    words = segment["words"]
    members = [word["id"] for word in words]
    index = members.index(nos_id)
    assert members[index : index + 2] == [nos_id, refove_id], "adjacent source pair"
    nos, refove = words[index : index + 2]
    assert nos["form"] == "nos" and nos["lemma"] == "nos"
    assert nos["morph"] == {"pos": "pron", "case": "acc", "number": "pl"}, (
        "accusative plural beneficiary"
    )
    assert refove["form"] == "réfove" and refove["lemma"] == "refoveo"
    assert refove["morph"] == {
        "pos": "verb",
        "mood": "imp",
        "number": "sg",
        "person": 2,
        "tense": "pres",
        "voice": "act",
        "conj": 2,
    }, "present active singular imperative"
    groups = layer["segments"][segment_id].get("alignments", [])
    touching = [group for group in groups if set(group["words"]) & {nos_id, refove_id}]
    assert len(touching) == 1, "one local imperative group"
    group = touching[0]
    assert group["words"] == [nos_id, refove_id], "exact two-member imperative group"
    assert group["anchor"] == refove_id, "predicate anchor"
    assert group["gloss"] == "refresh us", "reviewed imperative caption"
    assert all("gloss" not in layer["words"][word_id] for word_id in (nos_id, refove_id)), (
        "no duplicate direct caption"
    )
    realized = [word_id for word_id in members if "gloss" in layer["words"][word_id]]
    for alignment in groups:
        assert set(alignment["words"]) <= set(members), "segment-local caption"
        realized.extend(alignment["words"])
    assert Counter(realized) == Counter(members), "whole segment coverage"


@pytest.mark.parametrize("case", CASES)
def test_real_reused_body_has_one_local_refresh_us_caption(case):
    core, layer, path = load_case(case)
    assert language_packs.check_layer(core, layer, path) == []
    assert_refresh_group(core, layer, case)


MUTATIONS = (
    ("separate", "one local imperative group"),
    ("object-anchor", "predicate anchor"),
    ("direct-nos", "no duplicate direct caption"),
    ("direct-refove", "no duplicate direct caption"),
    ("wrong-beneficiary", "reviewed imperative caption"),
    ("wrong-agency", "reviewed imperative caption"),
    ("reversed", "exact two-member imperative group"),
    ("swallow-left", "exact two-member imperative group"),
    ("missing-nos", "exact two-member imperative group"),
    ("missing-refove", "exact two-member imperative group"),
    ("indicative", "present active singular imperative"),
    ("singular-nos", "accusative plural beneficiary"),
)


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize(("mutation", "message"), MUTATIONS)
def test_refresh_caption_rejects_semantic_and_boundary_mutants_and_recovers(
    case, mutation, message
):
    core, layer, _ = load_case(case)
    assert_refresh_group(core, layer, case)
    healthy_core, healthy_layer = deepcopy(core), deepcopy(layer)
    _, segment_id, nos_id, refove_id = case
    groups = layer["segments"][segment_id]["alignments"]
    group = next(g for g in groups if g["words"] == [nos_id, refove_id])
    if mutation == "separate":
        groups.remove(group)
        layer["words"][nos_id]["gloss"] = "us"
        layer["words"][refove_id]["gloss"] = "refresh"
    elif mutation == "object-anchor":
        group["anchor"] = nos_id
    elif mutation in ("direct-nos", "direct-refove"):
        word_id = nos_id if mutation == "direct-nos" else refove_id
        layer["words"][word_id]["gloss"] = "us" if word_id == nos_id else "refresh"
    elif mutation == "wrong-beneficiary":
        group["gloss"] = "refresh her"
    elif mutation == "wrong-agency":
        group["gloss"] = "we refresh"
    elif mutation == "reversed":
        group["words"].reverse()
    elif mutation == "swallow-left":
        previous = groups[groups.index(group) - 1]
        group["words"] = previous["words"] + group["words"]
        groups.remove(previous)
    elif mutation == "missing-nos":
        group["words"] = [refove_id]
    elif mutation == "missing-refove":
        group["words"] = [nos_id]
    else:
        word_id = refove_id if mutation == "indicative" else nos_id
        word = next(w for s in core["segments"] for w in s.get("words", []) if w["id"] == word_id)
        if mutation == "indicative":
            word["morph"]["mood"] = "ind"
        else:
            word["morph"]["number"] = "sg"
    with pytest.raises(AssertionError, match=message):
        assert_refresh_group(core, layer, case)
    assert_refresh_group(healthy_core, healthy_layer, case)
    restored_core, restored_layer, _ = load_case(case)
    assert restored_core == healthy_core and restored_layer == healthy_layer


def test_the_pair_maps_exactly_between_the_two_existing_body_consumers():
    layers = [load_case(case)[1] for case in CASES]
    expected = {"words": ["w011", "w012"], "anchor": "w012", "gloss": "refresh us"}
    actual = next(
        group
        for group in layers[0]["segments"]["s01"]["alignments"]
        if group["words"] == expected["words"]
    )
    donor = next(
        group
        for group in layers[1]["segments"]["s03"]["alignments"]
        if group["words"] == ["w048", "w049"]
    )
    mapping = {"w048": "w011", "w049": "w012"}
    assert (
        actual
        == expected
        == {
            **donor,
            "words": [mapping[word_id] for word_id in donor["words"]],
            "anchor": mapping[donor["anchor"]],
        }
    )
