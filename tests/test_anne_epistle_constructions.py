"""Owned contextual choices, not a general translation or gender classifier."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from anne_epistle_fixture import (
    FIXTURE,
    TEXT,
    current_row,
    opening_case,
    opening_tuple,
    predecessor_core,
    predecessor_layer,
    predecessor_row,
)

from build_reader import emit, store
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs, prose

ROOT = Path(__file__).resolve().parents[1]
GROUPS = [pytest.param(row, id=row["id"]) for row in FIXTURE["groups"]]
DIRECT = [pytest.param(row, id=row["id"]) for row in FIXTURE["direct"]]
NOTES = [pytest.param(row, id=row["id"]) for row in FIXTURE["notes"]]
PROSE = [pytest.param(row, id=row["id"]) for row in FIXTURE["prose"]]


def load(language):
    return store.core(ROOT, TEXT), store.raw_layer(ROOT, language, TEXT)


def shape(core, layer):
    assert language_packs.check_core(core) == []
    assert (
        language_packs.check_layer(core, layer, store.layer_path(ROOT, layer["language"], TEXT))
        == []
    )
    assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
    assert prose.check(layer) == []


def exact_group(layer, case):
    members = set(case["group"]["words"])
    touching = [g for g in layer["segments"]["s01"]["alignments"] if members & set(g["words"])]
    assert touching == [case["group"]], "Anne short construction"
    assert all("gloss" not in layer["words"][wid] for wid in members), "Anne short construction"


def group_in(layer, case):
    return next(
        g for g in layer["segments"]["s01"]["alignments"] if g["words"] == case["group"]["words"]
    )


def actual_row(language):
    ledger = json.loads((ROOT / f"languages/{language}/translation-provenance.json").read_text())
    (row,) = [row for row in ledger["sites"] if row["text"] == TEXT]
    return row


def compact(core, layer):
    tables = [emit.Table() for _ in range(4)]
    doc, localized = expand_core(core), enrich_layer(core, layer)
    return (
        emit.core_artifact(doc, core, *tables[:3]),
        emit.language_artifact(doc, localized, tables[3]),
        [table.order for table in tables],
    )


@pytest.mark.parametrize("language", ["pl", "en"])
def test_all229_realizations_current_native_prose_and_reader(language):
    core, layer = load(language)
    saved = deepcopy((core, layer))
    shape(core, layer)
    predecessor_core(core)
    predecessor_layer(layer)
    assert layer == FIXTURE["after_layers"][language]
    assert len(layer["words"]) == 229
    current_row(core, layer, actual_row(language))
    base, target, tables = compact(core, layer)
    expected_core, expected_layers = emit._strip(
        expand_core(core), {language: enrich_layer(core, layer)}
    )
    assert emit.expand(base, target, *tables) == (expected_core, expected_layers[language])
    assert (core, layer) == saved


@pytest.mark.parametrize("case", GROUPS)
@pytest.mark.parametrize("fault", ["residual", "duplicate", "reverse", "anchor"])
def test_real_topology_rejects_and_same_layer_recovers(case, fault):
    core, layer = load(case["language"])
    saved = deepcopy(layer)
    shape(core, layer)
    exact_group(layer, case)
    group = group_in(layer, case)
    groups = layer["segments"]["s01"]["alignments"]
    try:
        if fault == "residual":
            layer["words"][group["words"][0]]["gloss"] = "duplicate"
            diagnostic = "expected exactly one direct gloss or alignment"
        elif fault == "duplicate":
            groups.insert(groups.index(group) + 1, deepcopy(group))
            diagnostic = "belongs to more than one alignment"
        elif fault == "reverse":
            group["words"].reverse()
            diagnostic = "contiguous and in source order"
        else:
            group["anchor"] = case["outside_word"]
            diagnostic = "anchor must name the source word carrying the gloss"
        assert layer != saved
        assert any(diagnostic in e for e in interlinear.check(core, layer))
        assert any(
            diagnostic in e
            for e in language_packs.check_layer(
                core, layer, store.layer_path(ROOT, case["language"], TEXT)
            )
        )
    finally:
        layer.clear()
        layer.update(saved)
    shape(core, layer)
    exact_group(layer, case)


@pytest.mark.parametrize("case", GROUPS)
def test_valid_shape_cannot_approve_predecessor_context_wording(case):
    core, layer = load(case["language"])
    saved = deepcopy(layer)
    shape(core, layer)
    exact_group(layer, case)
    try:
        group_in(layer, case)["gloss"] = case["wrong_gloss"]
        assert layer != saved
        shape(core, layer)
        with pytest.raises(AssertionError, match=r"^Anne short construction(?:\n|$)"):
            exact_group(layer, case)
    finally:
        layer.clear()
        layer.update(saved)
    shape(core, layer)
    exact_group(layer, case)


@pytest.mark.parametrize("case", DIRECT)
def test_direct_predecessor_is_rejected_then_restored(case):
    core, layer = load(case["language"])
    saved = deepcopy(layer)
    shape(core, layer)
    predecessor_layer(layer)
    try:
        layer["words"][case["word"]]["gloss"] = case["before"]
        assert layer != saved
        shape(core, layer)
        with pytest.raises(AssertionError, match=r"^Anne complete target layer$"):
            predecessor_layer(layer)
    finally:
        layer.clear()
        layer.update(saved)
    shape(core, layer)
    predecessor_layer(layer)


@pytest.mark.parametrize("fault", ["missing", "wrong"])
def test_contextual_feminine_completion_is_literal_not_provider_inference(fault):
    core, layer = load("en")
    saved = deepcopy(core)
    shape(core, layer)
    predecessor_core(core)
    morph = core["segments"][0]["words"][13]["morph"]
    assert morph["gender"] == "f"
    try:
        if fault == "missing":
            del morph["gender"]
        else:
            morph["gender"] = "n"
        assert core != saved
        with pytest.raises(AssertionError, match=r"^Anne contextual core$"):
            predecessor_core(core)
    finally:
        core.clear()
        core.update(saved)
    shape(core, layer)
    predecessor_core(core)


@pytest.mark.parametrize("case", NOTES)
@pytest.mark.parametrize("fault", ["core", "layer"])
def test_actual_explanation_topology_rejects_one_sided_removal(case, fault):
    core, layer = load(case["language"])
    saved_core, saved_layer = deepcopy(core), deepcopy(layer)
    shape(core, layer)
    try:
        if fault == "core":
            del core["localization"]["explanations"][case["word"]]
        else:
            del layer["words"][case["word"]]["explanation"]
        assert (core, layer) != (saved_core, saved_layer)
        assert any(
            "explanation topology differs" in e
            for e in language_packs.check_layer(
                core, layer, store.layer_path(ROOT, case["language"], TEXT)
            )
        )
    finally:
        core.clear()
        core.update(saved_core)
        layer.clear()
        layer.update(saved_layer)
    shape(core, layer)
    predecessor_layer(layer)


@pytest.mark.parametrize("case", NOTES)
def test_each_new_explanation_rejects_semicolon_and_restores(case):
    core, layer = load(case["language"])
    saved = deepcopy(layer)
    shape(core, layer)
    try:
        layer["words"][case["word"]]["explanation"] += ";"
        assert layer != saved
        assert any("uses a semicolon" in e for e in prose.check(layer))
    finally:
        layer.clear()
        layer.update(saved)
    shape(core, layer)
    predecessor_layer(layer)


@pytest.mark.parametrize("case", PROSE)
def test_each_finite_prose_reversion_is_rejected_then_recovers(case):
    core, layer = load(case["language"])
    saved = deepcopy(layer)
    shape(core, layer)
    predecessor_layer(layer)
    actual = layer["segments"]["s01"]["translation"]
    assert actual.count(case["after"]) == 1
    try:
        layer["segments"]["s01"]["translation"] = actual.replace(case["after"], case["before"])
        assert layer != saved
        shape(core, layer)
        with pytest.raises(AssertionError, match=r"^Anne complete target layer$"):
            predecessor_layer(layer)
    finally:
        layer.clear()
        layer.update(saved)
    shape(core, layer)
    predecessor_layer(layer)


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("field", ["source_sha256", "target_sha256", "origin", "review"])
def test_complete_current_provenance_rejects_forgery_then_restores(language, field):
    core, layer = load(language)
    row = actual_row(language)
    saved = deepcopy(row)
    shape(core, layer)
    current_row(core, layer, row)
    try:
        row[field] = "0" * 64 if field.endswith("sha256") else "approved"
        assert row != saved
        with pytest.raises(AssertionError, match=r"^Anne complete provenance row$"):
            current_row(core, layer, row)
        with pytest.raises(AssertionError, match=r"^Anne complete provenance row$"):
            predecessor_row(row)
    finally:
        row.clear()
        row.update(saved)
    current_row(core, layer, row)
    assert predecessor_row(row) == FIXTURE["ledger"][language]["before"]


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("fault", ["gloss", "anchor"])
def test_real_compact_fields_reject_context_change_then_restore(language, fault):
    core, layer = load(language)
    shape(core, layer)
    case = next(row for row in FIXTURE["groups"] if row["language"] == language)
    base, target, tables = compact(core, layer)
    saved = deepcopy(target)
    start = int(case["group"]["words"][0][1:]) - 1
    cell = next(row for row in target["seg"][0]["a"] if row["s"] == start)
    try:
        if fault == "gloss":
            cell["g"] = case["wrong_gloss"]
        else:
            cell["a"] = 1 - cell["a"]
        assert target != saved
        _, changed = emit.expand(base, target, *tables)
        assert interlinear.check(core, changed) == []
        with pytest.raises(AssertionError, match=r"^Anne short construction(?:\n|$)"):
            exact_group(changed, case)
    finally:
        target.clear()
        target.update(saved)
    _, restored = emit.expand(base, target, *tables)
    exact_group(restored, case)


@pytest.mark.parametrize("subject", ["core", "layer", "row"])
def test_comparison_inverse_cannot_hide_an_unrelated_change(subject):
    core, layer = load("pl")
    row = actual_row("pl")
    shape(core, layer)
    values = {
        "core": (core, predecessor_core, "Anne contextual core"),
        "layer": (layer, predecessor_layer, "Anne complete target layer"),
        "row": (row, predecessor_row, "Anne complete provenance row"),
    }
    value, check, diagnostic = values[subject]
    saved = deepcopy(value)
    check(value)
    try:
        if subject == "core":
            value["segments"][0]["words"][0]["form"] = "Virum"
        elif subject == "layer":
            value["words"]["w001"]["gloss"] = "Mężczyznę"
        else:
            value["familiar_core"] = True
        assert value != saved
        with pytest.raises(AssertionError, match="^" + diagnostic + "$"):
            check(value)
    finally:
        value.clear()
        value.update(saved)
    assert value == saved
    shape(core, layer)
    check(value)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_first_opening_mapping_preserves_control_and_real_group_recovery(language):
    core, layer = load(language)
    shape(core, layer)
    row = opening_tuple(FIXTURE["opening_before" if language == "en" else "opening_control"])
    selected = opening_case(row, core, layer)
    if language == "pl":
        assert selected == row
        return
    assert selected == opening_tuple(FIXTURE["opening_after"])
    assert row[7][0] in selected[7] and "a valiant woman" in selected[7]
    case = next(c for c in FIXTURE["groups"] if c["id"] == "en-w001-w002")
    group = group_in(layer, case)
    saved, identity = deepcopy(layer), id(group)
    for wrong in selected[7]:
        try:
            group["gloss"] = wrong
            assert layer != saved
            shape(core, layer)
            with pytest.raises(AssertionError, match=r"^Anne short construction(?:\n|$)"):
                exact_group(layer, case)
        finally:
            group["gloss"] = case["group"]["gloss"]
        assert id(group_in(layer, case)) == identity and layer == saved
        shape(core, layer)
        exact_group(layer, case)


@pytest.mark.parametrize("field", ["expected", "span", "mutant"])
def test_first_opening_mapping_rejects_wrong_predecessor_row_and_restores(field):
    core, layer = load("en")
    shape(core, layer)
    row = list(opening_tuple(FIXTURE["opening_before"]))
    saved = deepcopy(row)
    try:
        index = {"expected": 5, "span": 3, "mutant": 7}[field]
        row[index] = {"expected": "Another", "span": ("w001", "w002"), "mutant": ("other",)}[field]
        assert row != saved
        with pytest.raises(AssertionError, match=r"^Anne first-opening predecessor$"):
            opening_case(tuple(row), core, layer)
    finally:
        row[:] = saved
    assert opening_case(tuple(row), core, layer) == opening_tuple(FIXTURE["opening_after"])
