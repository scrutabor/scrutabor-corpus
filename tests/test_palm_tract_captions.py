"""Finite Psalm tract realizations, current validation and exact historical copies."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from palm_tract_fixture import (
    DATA,
    TEXT,
    predecessor_palm_layer,
    predecessor_palm_rows,
    reviewed_palm_group,
    reviewed_palm_layer,
)

from build_reader import emit, store
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs, prose
from checks.lint import lint_text
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
GROUPS = [pytest.param(row, id=row["id"]) for row in DATA["groups"]]
SCALARS = [pytest.param(row, id=row["id"]) for row in DATA["scalars"]]
KEEPS = [pytest.param(row, id=row["id"]) for row in DATA["keeps"]]


def load(language):
    return store.core(ROOT, TEXT), store.raw_layer(ROOT, language, TEXT)


def healthy(core, layer):
    assert language_packs.check_core(core) == []
    assert lint_text(core) == ([], 147)
    assert (
        language_packs.check_layer(core, layer, store.layer_path(ROOT, layer["language"], TEXT))
        == []
    )
    assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
    assert prose.check(layer) == []


def group_in(layer, case):
    matches = [
        row
        for row in layer["segments"]["s01"]["alignments"]
        if set(row["words"]) & set(case["group"]["words"])
    ]
    assert matches == [case["group"]]
    return matches[0]


def compact(core, layer):
    doc, localized = expand_core(core), enrich_layer(core, layer)
    tables = [emit.Table() for _ in range(4)]
    base = emit.core_artifact(doc, core, *tables[:3])
    target = emit.language_artifact(doc, localized, tables[3])
    return base, target, [table.order for table in tables]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_all147_realizations_and_current_reader_are_exact_before_comparison(language):
    core, layer = load(language)
    snapshot = deepcopy((core, layer, DATA))
    healthy(core, layer)
    reviewed_palm_layer(layer)
    case = DATA["layers"][language]
    assert canonical_hash(core) == DATA["core_sha256"]
    assert list(layer["words"]) == [f"w{i:03}" for i in range(1, 148)]
    assert layer["words"] == case["words"]
    assert layer["segments"]["s01"]["alignments"] == case["alignments"]
    for word in core["segments"][0]["words"]:
        wid = word["id"]
        groups = [g for g in case["alignments"] if wid in g["words"]]
        assert ("gloss" in layer["words"][wid]) + len(groups) == 1
    changed = {(row["language"], wid) for row in DATA["groups"] for wid in row["group"]["words"]}
    changed |= {(row["language"], row["word"]) for row in DATA["scalars"]}
    assert len(changed) == 19 and 294 - len(changed) == 275
    assert [row["id"] for row in DATA["groups"]] == [
        "pl-038-039",
        "pl-054-055",
        "pl-086-087",
        "pl-051-053",
        "en-051-053",
        "en-138-139",
        "en-146-147",
    ]
    old = predecessor_palm_layer(layer)
    assert canonical_hash(old) == case["before_sha256"]
    ledger = json.loads((ROOT / "languages" / language / "translation-provenance.json").read_text())
    rows = [row for row in ledger["sites"] if row["text"] == TEXT]
    assert rows == [case["row_after"]]
    assert canonical_hash(source_payload(core["segments"][0])) == rows[0]["source_sha256"]
    assert canonical_hash(layer["segments"]["s01"]["translation"]) == rows[0]["target_sha256"]
    assert predecessor_palm_rows(rows, TEXT, language) == [case["row_before"]]
    base, target, tables = compact(core, layer)
    want_core, want_layers = emit._strip(expand_core(core), {language: enrich_layer(core, layer)})
    assert emit.expand(base, target, *tables) == (want_core, want_layers[language])
    assert (core, layer, DATA) == snapshot


@pytest.mark.parametrize("case", GROUPS)
@pytest.mark.parametrize("fault", ["residual", "duplicate", "reversed", "outside-anchor"])
def test_native_alignment_defects_reject_and_restore_the_same_layer(case, fault):
    core, layer = load(case["language"])
    healthy(core, layer)
    reviewed_palm_group(layer, case)
    snapshot = deepcopy(layer)
    group = group_in(layer, case)
    groups = layer["segments"]["s01"]["alignments"]
    if fault == "residual":
        layer["words"][group["words"][0]]["gloss"] = "control"
        diagnostic = "expected exactly one direct gloss or alignment"
    elif fault == "duplicate":
        index = next(i for i, value in enumerate(groups) if value is group)
        groups.insert(index + 1, deepcopy(group))
        diagnostic = "belongs to more than one alignment"
    elif fault == "reversed":
        group["words"].reverse()
        diagnostic = "contiguous and in source order"
    else:
        group["anchor"] = case["outside"]
        diagnostic = "anchor must name the source word carrying the gloss"
    try:
        assert layer != snapshot
        assert any(diagnostic in e for e in interlinear.check(core, layer))
        errors = language_packs.check_layer(
            core, layer, store.layer_path(ROOT, case["language"], TEXT)
        )
        assert any(diagnostic in error for error in errors)
    finally:
        layer.clear()
        layer.update(snapshot)
    healthy(core, layer)
    reviewed_palm_group(layer, case)


@pytest.mark.parametrize("case", GROUPS)
def test_structurally_valid_wrong_context_is_not_a_semantic_pass(case):
    core, layer = load(case["language"])
    healthy(core, layer)
    reviewed_palm_group(layer, case)
    snapshot = deepcopy(layer)
    group_in(layer, case)["gloss"] = case["wrong"]
    try:
        assert layer != snapshot
        healthy(core, layer)
        with pytest.raises(AssertionError, match=r"^reviewed Palm group(?:\n|$)"):
            reviewed_palm_group(layer, case)
    finally:
        layer.clear()
        layer.update(snapshot)
    healthy(core, layer)
    reviewed_palm_layer(layer)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_conjunction_cannot_be_stolen_by_the_rescue_group(language):
    core, layer = load(language)
    case = next(row for row in DATA["groups"] if row["id"] == f"{language}-051-053")
    healthy(core, layer)
    snapshot = deepcopy(layer)
    group = group_in(layer, case)
    layer["words"]["w050"].pop("gloss")
    group["words"].insert(0, "w050")
    try:
        assert layer != snapshot
        healthy(core, layer)
        with pytest.raises(AssertionError, match=r"^reviewed Palm group(?:\n|$)"):
            reviewed_palm_group(layer, case)
    finally:
        layer.clear()
        layer.update(snapshot)
    healthy(core, layer)
    reviewed_palm_layer(layer)


@pytest.mark.parametrize("case", GROUPS)
@pytest.mark.parametrize("fault", ["gloss", "anchor"])
def test_real_compact_alignment_corruption_rejects_then_recovers(case, fault):
    core, layer = load(case["language"])
    healthy(core, layer)
    base, target, tables = compact(core, layer)
    _, decoded = emit.expand(base, target, *tables)
    reviewed_palm_group(decoded, case)
    snapshot = deepcopy(target)
    segment = next(row for row in target["seg"] if row["id"] == "s01")
    ids = [w["id"] for w in core["segments"][0]["words"]]
    cell = next(row for row in segment["a"] if row["s"] == ids.index(case["group"]["words"][0]))
    if fault == "gloss":
        cell["g"] = case["wrong"]
    else:
        expected = case["group"]["words"].index(case["group"]["anchor"])
        assert cell["a"] == expected
        cell["a"] = (expected + 1) % len(case["group"]["words"])
    try:
        assert target != snapshot
        _, decoded = emit.expand(base, target, *tables)
        assert interlinear.check(core, decoded) == []
        with pytest.raises(AssertionError, match=r"^reviewed Palm group(?:\n|$)"):
            reviewed_palm_group(decoded, case)
    finally:
        target.clear()
        target.update(snapshot)
    assert target == snapshot
    _, decoded = emit.expand(base, target, *tables)
    reviewed_palm_group(decoded, case)


@pytest.mark.parametrize("case", SCALARS)
def test_superseded_scalar_rejects_without_claiming_structural_invalidity(case):
    core, layer = load(case["language"])
    healthy(core, layer)
    snapshot = deepcopy(layer)
    layer["words"][case["word"]]["gloss"] = case["before"]
    try:
        assert layer != snapshot
        healthy(core, layer)
        with pytest.raises(AssertionError, match=r"^unchanged contextual remainder(?:\n|$)"):
            reviewed_palm_layer(layer)
    finally:
        layer.clear()
        layer.update(snapshot)
    healthy(core, layer)
    reviewed_palm_layer(layer)


@pytest.mark.parametrize("case", KEEPS)
def test_valid_contrary_constructions_are_not_automatically_rewritten(case):
    core, layer = load(case["language"])
    healthy(core, layer)
    reviewed_palm_layer(layer)
    expected = DATA["layers"][case["language"]]
    assert {wid: layer["words"][wid] for wid in case["words"]} == {
        wid: expected["words"][wid] for wid in case["words"]
    }
    snapshot = deepcopy(layer)
    wid = case["words"][0]
    if "gloss" in layer["words"][wid]:
        layer["words"][wid]["gloss"] = "control"
    else:
        group = next(g for g in layer["segments"]["s01"]["alignments"] if wid in g["words"])
        group["gloss"] = "control"
    try:
        assert layer != snapshot
        healthy(core, layer)
        with pytest.raises(AssertionError, match=r"^unchanged contextual remainder(?:\n|$)"):
            reviewed_palm_layer(layer)
    finally:
        layer.clear()
        layer.update(snapshot)
    healthy(core, layer)
    reviewed_palm_layer(layer)


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("fault", ["old-prose", "added-prose"])
def test_prose_inverse_never_hides_unreviewed_words(language, fault):
    core, layer = load(language)
    healthy(core, layer)
    reviewed_palm_layer(layer)
    snapshot = deepcopy(layer)
    layer["segments"]["s01"]["translation"] = (
        DATA["layers"][language]["before_translation"]
        if fault == "old-prose"
        else layer["segments"]["s01"]["translation"] + " Added."
    )
    try:
        assert layer != snapshot
        healthy(core, layer)
        with pytest.raises(AssertionError, match=r"^unchanged contextual remainder(?:\n|$)"):
            predecessor_palm_layer(layer)
    finally:
        layer.clear()
        layer.update(snapshot)
    assert layer == snapshot
    reviewed_palm_layer(layer)


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("fault", ["missing", "wrong", "extra"])
def test_complete_provenance_row_guard_rejects_then_restores_same_object(language, fault):
    ledger = json.loads((ROOT / "languages" / language / "translation-provenance.json").read_text())
    rows = [row for row in ledger["sites"] if row["text"] == TEXT]
    assert predecessor_palm_rows(rows, TEXT, language) == [DATA["layers"][language]["row_before"]]
    row = rows[0]
    snapshot = deepcopy(row)
    try:
        if fault == "missing":
            row.pop("target_sha256")
        elif fault == "wrong":
            row["target_sha256"] = "0" * 64
        else:
            row["unreviewed_change"] = True
        assert row != snapshot
        with pytest.raises(AssertionError, match=r"^reviewed Palm provenance row(?:\n|$)"):
            predecessor_palm_rows(rows, TEXT, language)
    finally:
        row.clear()
        row.update(snapshot)
    assert rows[0] is row and row == snapshot
    assert predecessor_palm_rows(rows, TEXT, language) == [DATA["layers"][language]["row_before"]]
