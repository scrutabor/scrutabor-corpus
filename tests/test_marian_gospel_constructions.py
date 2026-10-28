"""Short Marian Gospel constructions and exact surrounding wording.

Literal choices are contextual expectations, not a universal grouping rule.
Compact transport is checked here, not rendered or oral presentation.
"""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from marian_gospel_fixture import (
    FIXTURE,
    current_expected_row,
    predecessor_core,
    predecessor_layer,
    predecessor_row,
)

from build_reader import emit, store
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs, prose
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
LAYERS = [pytest.param(row, id=row["id"]) for row in FIXTURE["layers"]]
NOTED = [pytest.param(row, id=row["id"]) for row in FIXTURE["layers"] if row["notes"]]
CORES = [pytest.param(row, id=row["id"]) for row in FIXTURE["cores"] if row["notes"]]
SCOPES = [pytest.param(row, id=row["id"]) for row in FIXTURE["scope_controls"]]


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


def group_in(layer, expected):
    found = [
        group
        for group in layer["segments"]["s01"]["alignments"]
        if set(group["words"]) & set(expected["words"])
    ]
    assert found == [expected], "Marian Gospel construction"
    return found[0]


def fields(layer, case):
    assert layer["segments"]["s01"]["alignments"] == case["alignments_after"], (
        "Marian Gospel construction"
    )
    for wid, change in case["word_changes"].items():
        assert layer["words"][wid] == change["after"], "Marian Gospel word field"
    assert canonical_hash(layer["segments"]["s01"]["translation"]) == case["prose_after_sha256"], (
        "Marian Gospel prose"
    )


def compact(core, layer):
    doc, target = expand_core(core), enrich_layer(core, layer)
    tables = [emit.Table() for _ in range(4)]
    base = emit.core_artifact(doc, core, *tables[:3])
    localized = emit.language_artifact(doc, target, tables[3])
    return base, localized, [table.order for table in tables]


def restore(actual, saved):
    actual.clear()
    actual.update(deepcopy(saved))


@pytest.mark.parametrize("case", LAYERS)
def test_complete_context_and_transport(case):
    core, layer = load(case)
    saved = deepcopy((core, layer))
    shape(core, layer)
    fields(layer, case)
    assert canonical_hash(predecessor_layer(layer)) == case["before_sha256"]
    core_case = next(row for row in FIXTURE["cores"] if row["text"] == case["text"])
    assert canonical_hash(predecessor_core(core)) == core_case["before_sha256"]
    ledger = json.loads(
        (ROOT / "languages" / case["language"] / "translation-provenance.json").read_text()
    )
    rows = [row for row in ledger["sites"] if row["site"] == case["after_row"]["site"]]
    assert rows == [current_expected_row(case["before_row"])]
    assert predecessor_row(rows[0]) == case["before_row"]
    row = rows[0]
    saved_row = deepcopy(row)
    for field in ("source_sha256", "target_sha256", "review", "extra"):
        try:
            row[field] = "unadmitted"
            assert row != saved_row
            with pytest.raises(AssertionError, match=r"^Marian Gospel provenance row(?:\n|$)"):
                predecessor_row(row)
        finally:
            row.clear()
            row.update(saved_row)
        assert rows[0] is row and row == saved_row
        assert predecessor_row(row) == case["before_row"]
    assert rows[0]["source_sha256"] == canonical_hash(
        source_payload(expand_core(core)["segments"][0])
    )
    assert rows[0]["target_sha256"] == canonical_hash(layer["segments"]["s01"]["translation"])
    base, target, tables = compact(core, layer)
    want_core, want_layers = emit._strip(
        expand_core(core), {case["language"]: enrich_layer(core, layer)}
    )
    got = emit.expand(base, target, *tables)
    assert got == (want_core, want_layers[case["language"]])
    fields(got[1], case)
    assert (core, layer) == saved


@pytest.mark.parametrize("case", LAYERS)
@pytest.mark.parametrize("fault", ["residual", "duplicate", "reversed", "outside-anchor"])
def test_native_group_faults_reject_and_recover(case, fault):
    core, layer = load(case)
    shape(core, layer)
    for expected in case["groups"]:
        saved = deepcopy(layer)
        group = group_in(layer, expected)
        groups = layer["segments"]["s01"]["alignments"]
        if fault == "residual":
            layer["words"][group["words"][0]]["gloss"] = "residual"
            diagnostic = "expected exactly one direct gloss or alignment"
        elif fault == "duplicate":
            index = next(i for i, value in enumerate(groups) if value is group)
            groups.insert(index + 1, deepcopy(group))
            diagnostic = "belongs to more than one alignment"
        elif fault == "reversed":
            group["words"].reverse()
            diagnostic = "contiguous and in source order"
        else:
            assert "w001" not in group["words"]
            group["anchor"] = "w001"
            diagnostic = "anchor must name the source word carrying the gloss"
        try:
            assert layer != saved
            assert any(diagnostic in error for error in interlinear.check(core, layer))
            assert any(
                diagnostic in error
                for error in language_packs.check_layer(
                    core, layer, store.layer_path(ROOT, case["language"], case["text"])
                )
            )
        finally:
            restore(layer, saved)
        assert layer == saved
        shape(core, layer)
        fields(layer, case)


@pytest.mark.parametrize("case", LAYERS)
def test_literal_group_wording_rejects_and_recovers(case):
    core, layer = load(case)
    shape(core, layer)
    for expected in case["groups"]:
        saved = deepcopy(layer)
        group_in(layer, expected)["gloss"] += " not"
        try:
            assert layer != saved
            # This is valid structural data. The contextual oracle rejects it.
            shape(core, layer)
            with pytest.raises(AssertionError, match=r"^Marian Gospel construction(?:\n|$)"):
                fields(layer, case)
        finally:
            restore(layer, saved)
        fields(layer, case)
        shape(core, layer)


@pytest.mark.parametrize("case", LAYERS)
@pytest.mark.parametrize("fault", ["gloss", "anchor"])
def test_compact_group_fields_reject_and_recover(case, fault):
    core, layer = load(case)
    shape(core, layer)
    base, target, tables = compact(core, layer)
    _, decoded = emit.expand(base, target, *tables)
    fields(decoded, case)
    order = [word["id"] for word in core["segments"][0]["words"]]
    for expected in case["groups"]:
        saved = deepcopy(target)
        segment = next(row for row in target["seg"] if row["id"] == "s01")
        group = next(row for row in segment["a"] if row["s"] == order.index(expected["words"][0]))
        if fault == "gloss":
            group["g"] += " not"
        else:
            group["a"] = 1 if group["a"] == 0 else 0
        try:
            assert target != saved
            _, changed = emit.expand(base, target, *tables)
            assert interlinear.check(core, changed) == []
            with pytest.raises(AssertionError, match=r"^Marian Gospel construction(?:\n|$)"):
                fields(changed, case)
        finally:
            restore(target, saved)
        assert target == saved
        _, recovered = emit.expand(base, target, *tables)
        fields(recovered, case)


@pytest.mark.parametrize("case", LAYERS)
def test_literal_scalar_wording_rejects_and_recovers(case):
    core, layer = load(case)
    shape(core, layer)
    assert case["scalars"]
    for scalar in case["scalars"]:
        saved = deepcopy(layer)
        assert layer["words"][scalar["word"]]["gloss"] == scalar["after"]
        layer["words"][scalar["word"]]["gloss"] = scalar["before"]
        try:
            assert layer != saved
            shape(core, layer)
            with pytest.raises(AssertionError, match=r"^Marian Gospel word field(?:\n|$)"):
                fields(layer, case)
        finally:
            restore(layer, saved)
        fields(layer, case)


@pytest.mark.parametrize("case", NOTED)
@pytest.mark.parametrize("fault", ["missing", "semicolon"])
def test_reader_note_guards_reject_and_recover(case, fault):
    core, layer = load(case)
    shape(core, layer)
    for wid in case["notes"]:
        saved = deepcopy(layer)
        if fault == "missing":
            del layer["words"][wid]["note"]
        else:
            layer["words"][wid]["note"] += ";"
        try:
            assert layer != saved
            if fault == "missing":
                errors = language_packs.check_layer(
                    core, layer, store.layer_path(ROOT, case["language"], case["text"])
                )
                assert any("note topology differs" in error and wid in error for error in errors)
            else:
                assert any("uses a semicolon" in error for error in prose.check(layer))
        finally:
            restore(layer, saved)
        assert layer == saved
        shape(core, layer)
        fields(layer, case)


@pytest.mark.parametrize("case", CORES)
@pytest.mark.parametrize("fault", ["missing", "extra"])
def test_neutral_note_topology_rejects_and_recovers(case, fault):
    core = store.core(ROOT, case["text"])
    layer = store.raw_layer(ROOT, "en", case["text"])
    shape(core, layer)
    saved = deepcopy(core)
    if fault == "missing":
        core["localization"]["notes"].remove("w124")
    else:
        core["localization"]["notes"].insert(0, "w001")
    try:
        assert core != saved
        errors = language_packs.check_layer(core, layer, store.layer_path(ROOT, "en", case["text"]))
        assert any("note topology differs" in error for error in errors)
        with pytest.raises(AssertionError, match=r"^Marian Gospel core remainder(?:\n|$)"):
            predecessor_core(core)
    finally:
        restore(core, saved)
    assert core == saved
    shape(core, layer)
    predecessor_core(core)


@pytest.mark.parametrize("case", LAYERS)
def test_unselected_prose_is_not_hidden_by_the_inverse(case):
    core, layer = load(case)
    shape(core, layer)
    predecessor_layer(layer)
    saved = deepcopy(layer)
    layer["segments"]["s01"]["translation"] += " Added."
    try:
        shape(core, layer)
        with pytest.raises(AssertionError, match=r"^unchanged passive-layer remainder(?:\n|$)"):
            predecessor_layer(layer)
    finally:
        restore(layer, saved)
    assert layer == saved
    fields(layer, case)
    predecessor_layer(layer)


@pytest.mark.parametrize("case", SCOPES)
def test_boundary_extension_is_not_an_admitted_short_group(case):
    core, layer = load(case)
    shape(core, layer)
    expected = case["group"]
    saved = deepcopy(layer)
    group = group_in(layer, expected)
    group["words"].append(case["next"])
    del layer["words"][case["next"]]["gloss"]
    try:
        assert layer != saved
        # The extension is structural data, not an approved contextual scope.
        shape(core, layer)
        with pytest.raises(AssertionError, match=r"^Marian Gospel construction(?:\n|$)"):
            group_in(layer, expected)
    finally:
        restore(layer, saved)
    assert layer == saved
    shape(core, layer)
    group_in(layer, expected)
