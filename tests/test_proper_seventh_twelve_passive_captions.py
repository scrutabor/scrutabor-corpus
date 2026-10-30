"""Finite reviewed relations, not an automatic passive or translation analyzer.

Literal semantic rejection is separate from actual native/reader API rejection.
"""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from english_register_successor_fixture import before_english_register_text_layer
from negative_government_fixture import predecessor_layer, predecessor_rows

from build_reader import emit, store
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs, prose
from checks.translation_provenance import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads(
    (ROOT / "tests/fixtures/proper-seventh-twelve-passive-captions.json").read_text()
)
GROUPS = [pytest.param(row, id=row["id"]) for row in FIXTURE["groups"]]
LAYERS = [pytest.param(row, id=row["id"]) for row in FIXTURE["layers"]]
SCALARS = [pytest.param(row, id=row["id"]) for row in FIXTURE["scalars"]]
CONTROLS = [pytest.param(row, id=row["id"]) for row in FIXTURE["controls"]]
FRAMES = [
    pytest.param(frame, fault, id=f"{frame['id']}-{index}")
    for frame in FIXTURE["frames"]
    for index, fault in enumerate(frame["faults"])
]


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
    assert touching(layer, case["group"]["words"]) == [case["group"]], "reviewed seventh group"
    assert all("gloss" not in layer["words"][wid] for wid in case["group"]["words"]), (
        "reviewed seventh group"
    )


def group_in(layer, case):
    (group,) = touching(layer, case["group"]["words"])
    return group


def reviewed_control(layer, case):
    assert touching(layer, case["members"]) == case["groups"], "retained seventh relation"
    assert {wid: layer["words"][wid] for wid in case["members"]} == case["words"], (
        "retained seventh relation"
    )


def contribution(layer, wid):
    groups = touching(layer, [wid])
    assert len(groups) <= 1, "one contextual contribution"
    if groups:
        assert "gloss" not in layer["words"][wid], "one contextual contribution"
        return groups[0].get("gloss") if groups[0].get("anchor") == wid else None
    return layer["words"][wid].get("gloss")


def frame_readback(core, layer, frame):
    assert [
        word
        for segment in core["segments"]
        for word in segment.get("words", [])
        if word["id"] in frame["members"]
    ] == frame["source_words"], "unchanged contextual Latin frame"
    assert [contribution(layer, wid) for wid in frame["members"]] == frame["readback"], (
        "reviewed contextual readback"
    )


def preserved(layer, case):
    layer = before_english_register_text_layer(layer, "unchanged seventh remainder")
    comparison = predecessor_layer(layer, "unchanged seventh remainder")
    for group in FIXTURE["groups"]:
        if (group["text"], group["language"]) == (case["text"], case["language"]):
            reviewed_group(comparison, group)
    for wid, change in case["word_changes"].items():
        assert comparison["words"][wid] == change["after"], "reviewed seventh word fields"
        comparison["words"][wid] = deepcopy(change["before"])
    for sid, change in case["alignment_changes"].items():
        assert comparison["segments"][sid]["alignments"] == change["after"]
        if change["before_present"]:
            comparison["segments"][sid]["alignments"] = deepcopy(change["before"])
        else:
            del comparison["segments"][sid]["alignments"]
    for sid, change in case["translation_changes"].items():
        assert comparison["segments"][sid]["translation"] == change["after"], (
            "unchanged seventh remainder"
        )
        comparison["segments"][sid]["translation"] = change["before"]
    assert canonical_hash(comparison) == case["before_sha256"], "unchanged seventh remainder"


def compact(core, layer):
    tables = [emit.Table() for _ in range(4)]
    doc, target = expand_core(core), enrich_layer(core, layer)
    return (
        emit.core_artifact(doc, core, *tables[:3]),
        emit.language_artifact(doc, target, tables[3]),
        [table.order for table in tables],
    )


@pytest.mark.parametrize("case", LAYERS)
def test_complete_real_layer_native_reader_and_predecessor_identity(case):
    core, layer = load(case)
    saved = deepcopy((core, layer, FIXTURE))
    assert canonical_hash(core) == case["core_sha256"]
    shape(core, layer)
    preserved(layer, case)
    assert {
        sid: segment.get("translation")
        for sid, segment in predecessor_layer(layer)["segments"].items()
    } == case["prose"]
    ledger = json.loads(
        (ROOT / "languages" / case["language"] / "translation-provenance.json").read_text()
    )
    assert (
        predecessor_rows([row for row in ledger["sites"] if row["text"] == case["text"]])
        == case["provenance"]
    )
    base, target, tables = compact(core, layer)
    expected_core, expected_layers = emit._strip(
        expand_core(core), {case["language"]: enrich_layer(core, layer)}
    )
    assert emit.expand(base, target, *tables) == (expected_core, expected_layers[case["language"]])
    assert (core, layer, FIXTURE) == saved


@pytest.mark.parametrize("case", GROUPS)
def test_exact_short_group_and_selected_source_contributions(case):
    core, layer = load(case)
    shape(core, layer)
    assert [
        word
        for segment in core["segments"]
        for word in segment.get("words", [])
        if word["id"] in case["group"]["words"]
    ] == case["source_words"]
    reviewed_group(layer, case)
    if case["id"] in {"72-pl", "72-en", "73-pl", "73-en"}:
        assert len(case["group"]["words"]) == 4
    else:
        assert 2 <= len(case["group"]["words"]) <= 3


@pytest.mark.parametrize("case", GROUPS)
@pytest.mark.parametrize("fault", ["residual", "duplicate", "reversed", "outside-anchor"])
def test_real_native_topology_fault_rejects_and_same_layer_recovers(case, fault):
    core, layer = load(case)
    saved = deepcopy(layer)
    shape(core, layer)
    reviewed_group(layer, case)
    group = group_in(layer, case)
    groups = layer["segments"][case["segment"]]["alignments"]
    try:
        if fault == "residual":
            layer["words"][case["group"]["words"][0]]["gloss"] = case["old_glosses"][0]
            diagnostic = "expected exactly one direct gloss or alignment"
        elif fault == "duplicate":
            position = next(i for i, item in enumerate(groups) if item is group)
            groups.insert(position + 1, deepcopy(group))
            diagnostic = "belongs to more than one alignment"
        elif fault == "reversed":
            group["words"].reverse()
            diagnostic = "contiguous and in source order"
        else:
            group["anchor"] = case["outside_word"]
            diagnostic = "anchor must name the source word carrying the gloss"
        assert layer != saved
        assert any(diagnostic in error for error in interlinear.check(core, layer))
        assert any(
            diagnostic in error
            for error in language_packs.check_layer(
                core, layer, store.layer_path(ROOT, case["language"], case["text"])
            )
        )
    finally:
        layer.clear()
        layer.update(saved)
        assert layer == saved
        shape(core, layer)
        reviewed_group(layer, case)


@pytest.mark.parametrize("case", GROUPS)
@pytest.mark.parametrize("fault", ["wrong-predicate", "lost-contribution"])
def test_selected_agency_agreement_person_and_contribution_reject_then_recover(case, fault):
    core, layer = load(case)
    saved = deepcopy(layer)
    shape(core, layer)
    reviewed_group(layer, case)
    try:
        group_in(layer, case)["gloss"] = case[fault]
        assert layer != saved
        shape(core, layer)
        with pytest.raises(AssertionError, match=r"^reviewed seventh group(?:\n|$)"):
            reviewed_group(layer, case)
    finally:
        layer.clear()
        layer.update(saved)
        assert layer == saved
        shape(core, layer)
        reviewed_group(layer, case)


@pytest.mark.parametrize("case", GROUPS)
@pytest.mark.parametrize("fault", ["compact-gloss", "compact-anchor"])
def test_real_reader_group_fields_reject_then_restore(case, fault):
    core, layer = load(case)
    shape(core, layer)
    base, target, tables = compact(core, layer)
    saved = deepcopy(target)
    _, decoded = emit.expand(base, target, *tables)
    reviewed_group(decoded, case)
    segment = next(row for row in target["seg"] if row["id"] == case["segment"])
    source = next(row for row in core["segments"] if row["id"] == case["segment"])["words"]
    start = [word["id"] for word in source].index(case["group"]["words"][0])
    cell = next(row for row in segment["a"] if row["s"] == start)
    try:
        if fault == "compact-gloss":
            cell["g"] = case["wrong-predicate"]
        else:
            expected = case["group"]["words"].index(case["group"]["anchor"])
            assert cell["a"] == expected
            cell["a"] = (expected + 1) % len(case["group"]["words"])
        assert target != saved
        _, decoded = emit.expand(base, target, *tables)
        assert interlinear.check(core, decoded) == []
        with pytest.raises(AssertionError, match=r"^reviewed seventh group(?:\n|$)"):
            reviewed_group(decoded, case)
    finally:
        target.clear()
        target.update(saved)
        assert target == saved
        _, decoded = emit.expand(base, target, *tables)
        reviewed_group(decoded, case)
        shape(core, layer)


@pytest.mark.parametrize("case", SCALARS)
def test_companion_scalar_rejects_predecessor_then_same_layer_recovers(case):
    core, layer = load(case)
    saved = deepcopy(layer)
    shape(core, layer)
    assert layer["words"][case["word"]] == case["after"]
    try:
        layer["words"][case["word"]] = deepcopy(case["before"])
        assert layer != saved
        with pytest.raises(AssertionError, match=r"^reviewed companion(?:\n|$)"):
            assert layer["words"][case["word"]] == case["after"], "reviewed companion"
    finally:
        layer.clear()
        layer.update(saved)
        assert layer == saved
        shape(core, layer)


@pytest.mark.parametrize("frame,fault", FRAMES)
def test_atomic_condition_coordination_government_and_readback_reject_then_recover(frame, fault):
    core, layer = load(frame)
    saved = deepcopy(layer)
    shape(core, layer)
    frame_readback(core, layer, frame)
    kind, wid, wrong = fault
    try:
        if kind == "word":
            layer["words"][wid]["gloss"] = wrong
        else:
            (group,) = touching(layer, [wid])
            group["gloss"] = wrong
        assert layer != saved
        with pytest.raises(AssertionError, match=r"^reviewed contextual readback(?:\n|$)"):
            frame_readback(core, layer, frame)
    finally:
        layer.clear()
        layer.update(saved)
        assert layer == saved
        shape(core, layer)
        frame_readback(core, layer, frame)


@pytest.mark.parametrize("case", CONTROLS)
def test_cross_colon_nonrelation_preserves_separate_true_groups(case):
    core, layer = load(case)
    saved = deepcopy(layer)
    shape(core, layer)
    reviewed_control(layer, case)
    try:
        if case["groups"]:
            touching(layer, case["members"])[0]["gloss"] = "changed retained relation"
        else:
            layer["words"][case["members"][0]]["gloss"] = "changed retained relation"
        assert layer != saved
        with pytest.raises(AssertionError, match=r"^retained seventh relation(?:\n|$)"):
            reviewed_control(layer, case)
    finally:
        layer.clear()
        layer.update(saved)
        assert layer == saved
        shape(core, layer)
        reviewed_control(layer, case)


@pytest.mark.parametrize("case", LAYERS)
def test_whole_predecessor_inverse_does_not_hide_unselected_prose(case):
    core, layer = load(case)
    saved = deepcopy(layer)
    shape(core, layer)
    preserved(layer, case)
    try:
        layer["segments"]["s01"]["translation"] += " Added."
        assert layer != saved
        with pytest.raises(AssertionError, match=r"^unchanged seventh remainder(?:\n|$)"):
            preserved(layer, case)
    finally:
        layer.clear()
        layer.update(saved)
        assert layer == saved
        shape(core, layer)
        preserved(layer, case)


PROSE = [pytest.param(row, id=row["id"]) for row in FIXTURE["prose_changes"]]


def divine_prose_and_target(layer, rows, case):
    layer = predecessor_layer(layer, "divine initial in complete prose")
    rows = predecessor_rows(rows, "only matching prose target digest")
    assert layer["segments"][case["segment"]]["translation"] == case["after"], (
        "divine initial in complete prose"
    )
    assert next(row for row in rows if row["segment"] == case["segment"]) == case["after_row"], (
        "only matching prose target digest"
    )
    assert case["after_row"]["target_sha256"] == canonical_hash(case["after"])


@pytest.mark.parametrize("case", PROSE)
@pytest.mark.parametrize("fault", ["prose-initial", "target-digest", "origin"])
def test_divine_prose_initial_and_exact_matching_provenance_reject_then_recover(case, fault):
    core, layer = load(case)
    ledger = json.loads(
        (ROOT / "languages" / case["language"] / "translation-provenance.json").read_text()
    )
    rows = [row for row in ledger["sites"] if row["text"] == case["text"]]
    saved_layer, saved_ledger = deepcopy(layer), deepcopy(ledger)
    shape(core, layer)
    divine_prose_and_target(layer, rows, case)
    selected = next(row for row in rows if row["segment"] == case["segment"])
    try:
        if fault == "prose-initial":
            layer["segments"][case["segment"]]["translation"] = case["before"]
        elif fault == "target-digest":
            selected["target_sha256"] = "0" * 64
        else:
            selected["origin"] = "own" if selected["origin"] != "own" else "working-unsettled"
        assert (layer, ledger) != (saved_layer, saved_ledger)
        with pytest.raises(
            AssertionError,
            match=r"^(?:divine initial in complete prose|only matching prose target digest)"
            r"(?:\n|$)",
        ):
            divine_prose_and_target(layer, rows, case)
    finally:
        layer.clear()
        layer.update(saved_layer)
        ledger.clear()
        ledger.update(saved_ledger)
        rows = [row for row in ledger["sites"] if row["text"] == case["text"]]
        assert (layer, ledger) == (saved_layer, saved_ledger)
        shape(core, layer)
        divine_prose_and_target(layer, rows, case)
