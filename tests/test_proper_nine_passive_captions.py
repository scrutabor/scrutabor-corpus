"""Finite compound captions and retained auxiliary-first readings.

These exact contextual choices are not a universal passive-translation rule.
Compact-reader checks cover transport, not a rendered or oral review.
"""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import emit, store
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs, prose
from checks.translation_provenance import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads(
    (Path(__file__).with_name("fixtures") / "proper-nine-passive-captions.json").read_text()
)
GROUPS = [pytest.param(row, id=row["id"]) for row in FIXTURE["groups"]]
LAYERS = [pytest.param(row, id=row["id"]) for row in FIXTURE["layers"]]
SUM_FIRST = [pytest.param(row, id=row["id"]) for row in FIXTURE["sum_first"]]
FUTURES = [pytest.param(row, id=row["id"]) for row in FIXTURE["futures"]]
EXPLICIT = [pytest.param(row, id=row["id"]) for row in FIXTURE["explicit_words"]]


def load(case):
    return store.core(ROOT, case["text"]), store.raw_layer(ROOT, case["language"], case["text"])


def shape(core, layer):
    assert language_packs.check_core(core) == []
    path = store.layer_path(ROOT, layer["language"], core["id"])
    assert language_packs.check_layer(core, layer, path) == []
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
    assert touching(layer, case["group"]["words"]) == [case["group"]], "reviewed passive group"
    assert all("gloss" not in layer["words"][wid] for wid in case["group"]["words"]), (
        "reviewed passive group"
    )


def group_in(layer, case):
    matches = touching(layer, case["group"]["words"])
    assert len(matches) == 1
    return matches[0]


def preserved(layer, case):
    restored = deepcopy(layer)
    for group_case in FIXTURE["groups"]:
        if (group_case["text"], group_case["language"]) == (case["text"], case["language"]):
            reviewed_group(restored, group_case)
    for wid, change in case["word_changes"].items():
        assert restored["words"][wid] == change["after"], "reviewed passive word fields"
        restored["words"][wid] = deepcopy(change["before"])
    for sid, change in case["alignment_changes"].items():
        assert restored["segments"][sid]["alignments"] == change["after"]
        if change["before_present"]:
            restored["segments"][sid]["alignments"] = deepcopy(change["before"])
        else:
            del restored["segments"][sid]["alignments"]
    assert canonical_hash(restored) == case["before_sha256"], "unchanged passive-layer remainder"


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
def test_native_provider_faults_reject_then_restore_same_layer(case, fault):
    core, layer = load(case)
    snapshot = deepcopy(layer)
    shape(core, layer)
    reviewed_group(layer, case)
    group = group_in(layer, case)
    groups = layer["segments"][case["segment"]]["alignments"]
    if fault == "residual":
        layer["words"][group["words"][0]]["gloss"] = case["before_direct"][group["words"][0]]
        diagnostic = "expected exactly one direct gloss or alignment"
    elif fault == "duplicate":
        position = next(i for i, value in enumerate(groups) if value is group)
        groups.insert(position + 1, deepcopy(group))
        diagnostic = "belongs to more than one alignment"
    elif fault == "reversed":
        group["words"].reverse()
        diagnostic = "contiguous and in source order"
    else:
        group["anchor"] = case["neighbor"]
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
@pytest.mark.parametrize("fault", ["wrong-predicate", "extra-dependent"])
def test_exact_context_and_minimality_reject_then_restore(case, fault):
    core, layer = load(case)
    snapshot = deepcopy(layer)
    shape(core, layer)
    reviewed_group(layer, case)
    group = group_in(layer, case)
    if fault == "wrong-predicate":
        group["gloss"] = case["wrong_predicate"]
    else:
        group["words"].append(case["neighbor"])
        del layer["words"][case["neighbor"]]["gloss"]
    assert layer != snapshot
    try:
        # Shape alone cannot adjudicate this grammatical but unapproved wording/scope.
        shape(core, layer)
        with pytest.raises(AssertionError, match=r"^reviewed passive group(?:\n|$)"):
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
    group = next(row for row in segment["a"] if row["s"] == start)
    if fault == "compact-gloss":
        group["g"] = case["wrong_predicate"]
    else:
        assert group["a"] == 0
        group["a"] = 1
    assert target != snapshot
    try:
        _, changed = decoded(base, target, tables)
        assert interlinear.check(core, changed) == []
        with pytest.raises(AssertionError, match=r"^reviewed passive group(?:\n|$)"):
            reviewed_group(changed, case)
    finally:
        target.clear()
        target.update(snapshot)
    assert target == snapshot
    _, recovered = decoded(base, target, tables)
    reviewed_group(recovered, case)
    assert interlinear.check(core, recovered) == []


@pytest.mark.parametrize("case", SUM_FIRST)
def test_sum_first_controls_remain_separate_and_natural(case):
    core, layer = load(case)
    shape(core, layer)
    assert touching(layer, case["members"]) == []
    assert {wid: layer["words"][wid]["gloss"] for wid in case["members"]} == case["direct"]


def reviewed_future(layer, case):
    assert layer["words"][case["word"]]["gloss"] == "will be", "reviewed ordinary future"


@pytest.mark.parametrize("case", FUTURES)
def test_old_future_register_rejects_then_restores(case):
    core, layer = load(case)
    snapshot = deepcopy(layer)
    shape(core, layer)
    reviewed_future(layer, case)
    layer["words"][case["word"]]["gloss"] = "shall be"
    try:
        assert layer != snapshot
        shape(core, layer)
        with pytest.raises(AssertionError, match=r"^reviewed ordinary future(?:\n|$)"):
            reviewed_future(layer, case)
    finally:
        layer.clear()
        layer.update(snapshot)
    assert layer == snapshot
    shape(core, layer)
    reviewed_future(layer, case)


def reviewed_explicit(layer, case):
    assert layer["words"][case["word"]] == case["fields"], "explicit Wisdom subject and time"


@pytest.mark.parametrize("case", EXPLICIT)
def test_explicit_wisdom_subject_and_already_reject_then_restore(case):
    core, layer = load(case)
    snapshot = deepcopy(layer)
    shape(core, layer)
    reviewed_explicit(layer, case)
    layer["words"][case["word"]]["gloss"] = case["wrong"]
    try:
        assert layer != snapshot
        shape(core, layer)
        with pytest.raises(AssertionError, match=r"^explicit Wisdom subject and time(?:\n|$)"):
            reviewed_explicit(layer, case)
    finally:
        layer.clear()
        layer.update(snapshot)
    assert layer == snapshot
    reviewed_explicit(layer, case)
    shape(core, layer)


@pytest.mark.parametrize("case", LAYERS)
def test_unselected_prose_is_not_hidden_by_the_comparison_inverse(case):
    core, layer = load(case)
    snapshot = deepcopy(layer)
    shape(core, layer)
    preserved(layer, case)
    layer["segments"]["s01"]["translation"] += " Added."
    try:
        assert layer != snapshot
        with pytest.raises(AssertionError, match=r"^unchanged passive-layer remainder(?:\n|$)"):
            preserved(layer, case)
    finally:
        layer.clear()
        layer.update(snapshot)
    assert layer == snapshot
    shape(core, layer)
    preserved(layer, case)
