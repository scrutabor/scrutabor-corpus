"""Short Matthew constructions, contextual genders and retained source facts."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from michael_gospel_fixture import (
    FIXTURE,
    TEXT,
    predecessor_core,
    predecessor_layer,
    predecessor_row,
)

from build_reader import emit, store
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs, prose
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
GROUPS = [pytest.param(row, id=row["id"]) for row in FIXTURE["groups"]]
DIRECT = [pytest.param(row, id=row["id"]) for row in FIXTURE["direct"]]
GENDERS = [pytest.param(row, id=row["word"]) for row in FIXTURE["genders"]]
PROSE = [
    pytest.param(language, before, after, id=identity)
    for identity, language, before, after in (
        ("pl-name", "pl", "w moje imię", "w Moje imię"),
        ("pl-receives", "pl", "mnie przyjmuje", "Mnie przyjmuje"),
        ("pl-believe", "pl", "we mnie wierzą", "we Mnie wierzą"),
        ("pl-Father", "pl", "mojego Ojca", "Mojego Ojca"),
        ("pl-angels", "pl", "ich Aniołowie", "ich aniołowie"),
        ("pl-millstone", "pl", "ośli kamień młyński", "kamień młyński obracany przez osła"),
        ("pl-offender", "pl", "i zatopiono go", "i zatopiono tego człowieka"),
        ("en-name", "en", "in my name", "in My name"),
        ("en-receives", "en", "welcomes me.", "welcomes Me."),
        ("en-believe", "en", "in me into sin", "in Me into sin"),
        ("en-Father", "en", "my Father", "My Father"),
    )
]


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
    touching = [
        group for group in layer["segments"]["s01"]["alignments"] if members & set(group["words"])
    ]
    assert touching == [case["group"]], "Gospel short construction"
    assert all("gloss" not in layer["words"][wid] for wid in members), "Gospel short construction"


def group_in(layer, case):
    return next(
        group
        for group in layer["segments"]["s01"]["alignments"]
        if group["words"] == case["group"]["words"]
    )


def actual_row(language):
    rows = json.loads((ROOT / f"languages/{language}/translation-provenance.json").read_text())
    matches = [row for row in rows["sites"] if row["text"] == TEXT]
    assert len(matches) == 1
    return matches[0]


def exact_row(core, layer, row):
    language = layer["language"]
    assert row == FIXTURE["ledger"][language]["after"], "Gospel complete provenance row"
    assert row["source_sha256"] == canonical_hash(source_payload(core["segments"][0]))
    assert row["target_sha256"] == canonical_hash(layer["segments"]["s01"]["translation"])


def compact(core, layer):
    doc, localized = expand_core(core), enrich_layer(core, layer)
    tables = [emit.Table() for _ in range(4)]
    base = emit.core_artifact(doc, core, *tables[:3])
    target = emit.language_artifact(doc, localized, tables[3])
    return base, target, [table.order for table in tables]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_all196_realizations_context_genders_prose_and_reader(language):
    core, layer = load(language)
    snapshot = deepcopy((core, layer))
    shape(core, layer)
    predecessor_core(core)
    assert layer == FIXTURE["after_layers"][language]
    predecessor_layer(layer)
    exact_row(core, layer, actual_row(language))
    base, target, tables = compact(core, layer)
    want_core, want_layers = emit._strip(expand_core(core), {language: enrich_layer(core, layer)})
    assert emit.expand(base, target, *tables) == (want_core, want_layers[language])
    assert (core, layer) == snapshot


@pytest.mark.parametrize("case", GROUPS)
@pytest.mark.parametrize("fault", ["residual", "duplicate", "reverse", "anchor"])
def test_actual_alignment_rejection_and_same_container_recovery(case, fault):
    core, layer = load(case["language"])
    snapshot = deepcopy(layer)
    shape(core, layer)
    exact_group(layer, case)
    group = group_in(layer, case)
    groups = layer["segments"]["s01"]["alignments"]
    if fault == "residual":
        layer["words"][group["words"][0]]["gloss"] = "duplicate"
        diagnostic = "expected exactly one direct gloss or alignment"
    elif fault == "duplicate":
        position = next(i for i, row in enumerate(groups) if row is group)
        groups.insert(position + 1, deepcopy(group))
        diagnostic = "belongs to more than one alignment"
    elif fault == "reverse":
        group["words"].reverse()
        diagnostic = "contiguous and in source order"
    else:
        assert "w001" not in group["words"]
        group["anchor"] = "w001"
        diagnostic = "anchor must name the source word carrying the gloss"
    try:
        assert layer != snapshot
        assert any(diagnostic in error for error in interlinear.check(core, layer))
        assert any(
            diagnostic in error
            for error in language_packs.check_layer(
                core, layer, store.layer_path(ROOT, case["language"], TEXT)
            )
        )
    finally:
        layer.clear()
        layer.update(snapshot)
    assert layer == snapshot
    shape(core, layer)
    exact_group(layer, case)


@pytest.mark.parametrize("case", GROUPS)
def test_wrong_contextual_wording_is_not_approved_by_valid_shape(case):
    core, layer = load(case["language"])
    snapshot = deepcopy(layer)
    shape(core, layer)
    exact_group(layer, case)
    group_in(layer, case)["gloss"] = case["wrong_gloss"]
    try:
        assert layer != snapshot
        shape(core, layer)
        with pytest.raises(AssertionError, match=r"^Gospel short construction(?:\n|$)"):
            exact_group(layer, case)
    finally:
        layer.clear()
        layer.update(snapshot)
    shape(core, layer)
    exact_group(layer, case)


@pytest.mark.parametrize("case", DIRECT)
def test_direct_choice_rejects_exact_predecessor_and_recovers(case):
    core, layer = load(case["language"])
    snapshot = deepcopy(layer)
    shape(core, layer)
    predecessor_layer(layer)
    assert layer["words"][case["word"]]["gloss"] == case["after"]
    layer["words"][case["word"]]["gloss"] = case["before"]
    try:
        assert layer != snapshot
        shape(core, layer)
        with pytest.raises(AssertionError, match=r"^Gospel complete target layer$"):
            predecessor_layer(layer)
    finally:
        layer.clear()
        layer.update(snapshot)
    shape(core, layer)
    predecessor_layer(layer)


@pytest.mark.parametrize("case", GENDERS)
@pytest.mark.parametrize("fault", ["missing", "wrong"])
def test_contextual_gender_identity_rejects_then_restores(case, fault):
    core, layer = load("en")
    snapshot = deepcopy(core)
    shape(core, layer)
    predecessor_core(core)
    morph = core["segments"][0]["words"][case["index"]]["morph"]
    assert morph["gender"] == case["gender"]
    if fault == "missing":
        del morph["gender"]
    else:
        morph["gender"] = "n"
    try:
        assert core != snapshot
        # The contextual literal, not a claimed universal gender inference API.
        with pytest.raises(AssertionError, match=r"^Gospel contextual core$"):
            predecessor_core(core)
    finally:
        core.clear()
        core.update(snapshot)
    shape(core, layer)
    predecessor_core(core)


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("fault", ["gloss", "anchor"])
def test_actual_compact_fields_cannot_change_owned_construction(language, fault):
    core, layer = load(language)
    shape(core, layer)
    case = next(row for row in FIXTURE["groups"] if row["language"] == language)
    base, target, tables = compact(core, layer)
    snapshot = deepcopy(target)
    _, recovered = emit.expand(base, target, *tables)
    exact_group(recovered, case)
    start = int(case["group"]["words"][0][1:]) - 1
    cell = next(row for row in target["seg"][0]["a"] if row["s"] == start)
    if fault == "gloss":
        cell["g"] += " also"
    else:
        cell["a"] = 1 - cell["a"]
    try:
        assert target != snapshot
        _, changed = emit.expand(base, target, *tables)
        assert interlinear.check(core, changed) == []
        with pytest.raises(AssertionError, match=r"^Gospel short construction(?:\n|$)"):
            exact_group(changed, case)
    finally:
        target.clear()
        target.update(snapshot)
    assert target == snapshot
    _, recovered = emit.expand(base, target, *tables)
    exact_group(recovered, case)


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("field", ["source_sha256", "target_sha256", "origin", "review"])
def test_exact_provenance_rejects_stale_or_promoted_row_then_recovers(language, field):
    core, layer = load(language)
    row = actual_row(language)
    snapshot = deepcopy(row)
    exact_row(core, layer, row)
    row[field] = "0" * 64 if field.endswith("sha256") else "approved"
    try:
        assert row != snapshot
        with pytest.raises(AssertionError, match=r"^Gospel complete provenance row(?:\n|$)"):
            exact_row(core, layer, row)
        with pytest.raises(AssertionError, match=r"^Gospel complete provenance row$"):
            predecessor_row(row)
    finally:
        row.clear()
        row.update(snapshot)
    exact_row(core, layer, row)
    assert predecessor_row(row) == FIXTURE["ledger"][language]["before"]


@pytest.mark.parametrize("subject", ["core", "layer", "row"])
def test_historical_comparison_cannot_hide_an_unrelated_change(subject):
    core, layer = load("pl")
    shape(core, layer)
    row = actual_row("pl")
    if subject == "core":
        value, inverse = core, predecessor_core
        diagnostic = "Gospel contextual core"
    elif subject == "layer":
        value, inverse = layer, predecessor_layer
        diagnostic = "Gospel complete target layer"
    else:
        value, inverse = row, predecessor_row
        diagnostic = "Gospel complete provenance row"
    snapshot = deepcopy(value)
    inverse(value)
    if subject == "core":
        value["segments"][0]["words"][0]["form"] = "Sub"
    elif subject == "layer":
        value["words"]["w001"]["gloss"] = "Pod"
    else:
        value["familiar_core"] = True
    try:
        assert value != snapshot
        with pytest.raises(AssertionError, match="^" + diagnostic + "$"):
            inverse(value)
    finally:
        value.clear()
        value.update(deepcopy(snapshot))
    assert value == snapshot
    inverse(value)
    if subject == "core":
        shape(core, layer)
        try:
            value["editorial"]["source"]["method"] += " Altered."
            assert value != snapshot
            with pytest.raises(AssertionError, match=r"^Gospel contextual core$"):
                inverse(value)
        finally:
            value.clear()
            value.update(deepcopy(snapshot))
            assert value == snapshot
            shape(core, layer)
            inverse(value)


@pytest.mark.parametrize("language,before,after", PROSE)
def test_each_finite_prose_choice_rejects_its_predecessor_then_recovers(language, before, after):
    core, layer = load(language)
    snapshot = deepcopy(layer)
    shape(core, layer)
    predecessor_layer(layer)
    text = layer["segments"]["s01"]["translation"]
    assert text.count(after) == 1 and before not in text
    layer["segments"]["s01"]["translation"] = text.replace(after, before)
    try:
        assert layer != snapshot
        shape(core, layer)
        with pytest.raises(AssertionError, match=r"^Gospel complete target layer$"):
            predecessor_layer(layer)
    finally:
        layer.clear()
        layer.update(snapshot)
    assert layer == snapshot
    shape(core, layer)
    predecessor_layer(layer)
