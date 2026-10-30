"""Finite contextual predicates; literal assertions are not a semantic analyzer.

Compact transport is not a rendered, spoken, or whole-prayer review.
"""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from english_register_successor_fixture import before_english_register_text_layer

from build_reader import emit, store
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs, prose
from checks.translation_provenance import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads(
    (
        Path(__file__).with_name("fixtures") / "proper-fourth-twelve-passive-captions.json"
    ).read_text()
)
GROUPS = [pytest.param(row, id=row["id"]) for row in FIXTURE["groups"]]
LAYERS = [pytest.param(row, id=row["id"]) for row in FIXTURE["layers"]]
SCALARS = [pytest.param(row, id=row["id"]) for row in FIXTURE["scalars"]]
CONTROLS = [pytest.param(row, id=row["id"]) for row in FIXTURE["controls"]]


def load(case):
    return store.core(ROOT, case["text"]), store.raw_layer(ROOT, case["language"], case["text"])


def shape(core, layer):
    assert language_packs.check_core(core) == []
    assert (
        language_packs.check_layer(
            core, layer, store.layer_path(ROOT, layer["language"], core["id"])
        )
        == []
    )
    assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
    assert prose.check(layer) == []


def touching(layer, members):
    return [
        group
        for segment in layer["segments"].values()
        for group in segment.get("alignments", [])
        if set(group["words"]) & set(members)
    ]


def reviewed_group(layer, case):
    assert touching(layer, case["group"]["words"]) == [case["group"]], "reviewed contextual group"
    assert all("gloss" not in layer["words"][wid] for wid in case["group"]["words"]), (
        "reviewed contextual group"
    )


def group_in(layer, case):
    matches = touching(layer, case["group"]["words"])
    assert len(matches) == 1
    return matches[0]


def reviewed_scalar(layer, case):
    assert layer["words"][case["word"]] == case["after"], "reviewed companion caption"


def reviewed_control(layer, case):
    assert touching(layer, case["members"]) == case["groups"], "reviewed unchanged context"
    assert {wid: layer["words"][wid] for wid in case["members"]} == case["words"], (
        "reviewed unchanged context"
    )


def preserved(layer, case):
    layer = before_english_register_text_layer(layer, "unchanged contextual remainder")
    restored = deepcopy(layer)
    for row in FIXTURE["groups"]:
        if (row["text"], row["language"]) == (case["text"], case["language"]):
            reviewed_group(restored, row)
    for wid, change in case["word_changes"].items():
        assert restored["words"][wid] == change["after"], "reviewed contextual word fields"
        restored["words"][wid] = deepcopy(change["before"])
    for sid, change in case["alignment_changes"].items():
        assert restored["segments"][sid]["alignments"] == change["after"]
        if change["before_present"]:
            restored["segments"][sid]["alignments"] = deepcopy(change["before"])
        else:
            del restored["segments"][sid]["alignments"]
    assert canonical_hash(restored) == case["before_sha256"], "unchanged contextual remainder"


def compact(core, layer):
    doc, localized = expand_core(core), enrich_layer(core, layer)
    tables = [emit.Table() for _ in range(4)]
    base = emit.core_artifact(doc, core, *tables[:3])
    target = emit.language_artifact(doc, localized, tables[3])
    return base, target, [table.order for table in tables]


def decoded(base, target, tables):
    return emit.expand(base, target, *tables)


@pytest.mark.parametrize("case", LAYERS)
def test_complete_layers_preserve_context_and_reader_roundtrip(case):
    core, layer = load(case)
    snapshot = deepcopy((core, layer, FIXTURE))
    assert canonical_hash(core) == case["core_sha256"]
    shape(core, layer)
    preserved(layer, case)
    ledger = json.loads(
        (ROOT / "languages" / case["language"] / "translation-provenance.json").read_text()
    )
    assert [row for row in ledger["sites"] if row["text"] == case["text"]] == case["provenance"]
    base, target, tables = compact(core, layer)
    want_core, want_layers = emit._strip(
        expand_core(core), {case["language"]: enrich_layer(core, layer)}
    )
    assert decoded(base, target, tables) == (want_core, want_layers[case["language"]])
    assert (core, layer, FIXTURE) == snapshot


@pytest.mark.parametrize("case", GROUPS)
@pytest.mark.parametrize("fault", ["residual", "duplicate", "reversed", "outside-anchor"])
def test_native_alignment_rejection_and_same_copy_recovery(case, fault):
    core, layer = load(case)
    snapshot = deepcopy(layer)
    shape(core, layer)
    reviewed_group(layer, case)
    group = group_in(layer, case)
    groups = layer["segments"][case["segment"]]["alignments"]
    if fault == "residual":
        layer["words"][case["residual_word"]]["gloss"] = case["residual_gloss"]
        diagnostic = "expected exactly one direct gloss or alignment"
    elif fault == "duplicate":
        position = next(i for i, value in enumerate(groups) if value is group)
        groups.insert(position + 1, deepcopy(group))
        diagnostic = "belongs to more than one alignment"
    elif fault == "reversed":
        group["words"].reverse()
        diagnostic = "contiguous and in source order"
    else:
        group["anchor"] = case["outside_word"]
        diagnostic = "anchor must name the source word carrying the gloss"
    assert layer != snapshot
    try:
        assert any(diagnostic in error for error in interlinear.check(core, layer))
        assert any(
            diagnostic in error
            for error in language_packs.check_layer(
                core, layer, store.layer_path(ROOT, case["language"], case["text"])
            )
        )
    finally:
        layer.clear()
        layer.update(snapshot)
    assert layer == snapshot
    shape(core, layer)
    reviewed_group(layer, case)


@pytest.mark.parametrize("case", GROUPS)
@pytest.mark.parametrize("fault", ["wrong-predicate", "lost-contribution"])
def test_person_aspect_and_contributions_reject_then_recover(case, fault):
    core, layer = load(case)
    snapshot = deepcopy(layer)
    shape(core, layer)
    reviewed_group(layer, case)
    group_in(layer, case)["gloss"] = case[fault]
    try:
        assert layer != snapshot
        shape(core, layer)
        with pytest.raises(AssertionError, match=r"^reviewed contextual group(?:\n|$)"):
            reviewed_group(layer, case)
    finally:
        layer.clear()
        layer.update(snapshot)
    assert layer == snapshot
    shape(core, layer)
    reviewed_group(layer, case)


@pytest.mark.parametrize("case", GROUPS)
def test_neighbor_scope_is_not_approved_by_structural_validity(case):
    core, layer = load(case)
    snapshot = deepcopy(layer)
    shape(core, layer)
    reviewed_group(layer, case)
    group = group_in(layer, case)
    extension = case["extension"]
    groups = layer["segments"][case["segment"]]["alignments"]
    for old_group in extension["remove_groups"]:
        groups.remove(old_group)
    for wid in extension["direct_members"]:
        del layer["words"][wid]["gloss"]
    group["words"] = extension["combined_members"]
    try:
        assert layer != snapshot
        shape(core, layer)
        with pytest.raises(AssertionError, match=r"^reviewed contextual group(?:\n|$)"):
            reviewed_group(layer, case)
    finally:
        layer.clear()
        layer.update(snapshot)
    assert layer == snapshot
    shape(core, layer)
    reviewed_group(layer, case)


@pytest.mark.parametrize("case", GROUPS)
@pytest.mark.parametrize("fault", ["compact-gloss", "compact-anchor"])
def test_real_compact_reader_fields_reject_then_restore(case, fault):
    core, layer = load(case)
    shape(core, layer)
    base, target, tables = compact(core, layer)
    snapshot = deepcopy(target)
    _, restored = decoded(base, target, tables)
    reviewed_group(restored, case)
    segment = next(row for row in target["seg"] if row["id"] == case["segment"])
    words = next(row for row in core["segments"] if row["id"] == case["segment"])["words"]
    start = [word["id"] for word in words].index(case["group"]["words"][0])
    cell = next(row for row in segment["a"] if row["s"] == start)
    if fault == "compact-gloss":
        cell["g"] = case["wrong-predicate"]
    else:
        expected = case["group"]["words"].index(case["group"]["anchor"])
        assert cell["a"] == expected
        cell["a"] = (expected + 1) % len(case["group"]["words"])
    try:
        assert target != snapshot
        _, changed = decoded(base, target, tables)
        assert interlinear.check(core, changed) == []
        with pytest.raises(AssertionError, match=r"^reviewed contextual group(?:\n|$)"):
            reviewed_group(changed, case)
    finally:
        target.clear()
        target.update(snapshot)
    assert target == snapshot
    _, recovered = decoded(base, target, tables)
    reviewed_group(recovered, case)
    assert interlinear.check(core, recovered) == []


@pytest.mark.parametrize("case", SCALARS)
def test_relative_and_answer_initial_reject_then_recover(case):
    core, layer = load(case)
    snapshot = deepcopy(layer)
    shape(core, layer)
    reviewed_scalar(layer, case)
    layer["words"][case["word"]] = deepcopy(case["before"])
    try:
        assert layer != snapshot
        shape(core, layer)
        with pytest.raises(AssertionError, match=r"^reviewed companion caption(?:\n|$)"):
            reviewed_scalar(layer, case)
    finally:
        layer.clear()
        layer.update(snapshot)
    assert layer == snapshot
    shape(core, layer)
    reviewed_scalar(layer, case)


@pytest.mark.parametrize("case", CONTROLS)
def test_neighbor_deponent_question_and_case_controls_reject_then_recover(case):
    core, layer = load(case)
    snapshot = deepcopy(layer)
    shape(core, layer)
    reviewed_control(layer, case)
    if case["groups"]:
        touching(layer, case["members"])[0]["gloss"] = "control"
    else:
        layer["words"][case["members"][0]]["gloss"] = "control"
    try:
        assert layer != snapshot
        shape(core, layer)
        with pytest.raises(AssertionError, match=r"^reviewed unchanged context(?:\n|$)"):
            reviewed_control(layer, case)
    finally:
        layer.clear()
        layer.update(snapshot)
    assert layer == snapshot
    shape(core, layer)
    reviewed_control(layer, case)


@pytest.mark.parametrize("case", LAYERS)
def test_unselected_prose_is_not_hidden_by_the_inverse(case):
    core, layer = load(case)
    snapshot = deepcopy(layer)
    shape(core, layer)
    preserved(layer, case)
    layer["segments"]["s01"]["translation"] += " Added."
    try:
        assert layer != snapshot
        with pytest.raises(AssertionError, match=r"^unchanged contextual remainder(?:\n|$)"):
            preserved(layer, case)
    finally:
        layer.clear()
        layer.update(snapshot)
    assert layer == snapshot
    shape(core, layer)
    preserved(layer, case)
