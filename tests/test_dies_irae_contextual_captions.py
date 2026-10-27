"""Selected future, petition and absolute captions retain distinct contextual force."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from dies_irae_caption_fixture import DATA, canonical, parent_at, restore_dies_irae_layer

from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs, prose

ROOT = Path(__file__).resolve().parents[1]
CASES = DATA["cases"]
GROUPS = [case for case in CASES if "group" in case]
MUTANTS = [(case, wrong) for case in CASES for wrong in case["wrong"]]
CONTROLS = DATA["controls"]
FAULTS = ("split", "residual", "duplicate", "anchor", "order", "too-wide")


def path_of(language=None):
    base = ROOT if language is None else ROOT / "languages" / language
    return base / DATA["core_path"]


def load(language):
    raw = path_of().read_bytes()
    assert hashlib.sha256(raw).hexdigest() == DATA["core_sha256"]
    return json.loads(raw), json.loads(path_of(language).read_bytes())


def reviewed(case, layer):
    groups = layer["segments"][case["segment"]].get("alignments", [])
    touching = [group for group in groups if set(group["words"]) & set(case["words"])]
    if "group" in case:
        assert touching == [case["group"]], "selected contextual reading"
        assert all("gloss" not in layer["words"][wid] for wid in case["words"]), (
            "selected contextual reading"
        )
        return touching[0]
    assert touching == [], "selected contextual reading"
    assert layer["words"][case["words"][0]]["gloss"] == case["gloss"], "selected contextual reading"
    return layer["words"][case["words"][0]]


def retained(control, layer):
    touching = [
        group
        for group in layer["segments"][control["segment"]].get("alignments", [])
        if set(group["words"]) & set(control["words"])
    ]
    assert touching == control["groups"], "retained contextual force"
    assert {wid: layer["words"][wid] for wid in control["words"]} == control["entries"], (
        "retained contextual force"
    )


def healthy(core, layer):
    language = layer["language"]
    assert core["id"] == layer["text"] == DATA["text"]
    indexed = {word["id"]: word for segment in core["segments"] for word in segment["words"]}
    for case in CASES:
        if case["language"] == language:
            assert [indexed[wid] for wid in case["words"]] == case["source_words"]
            reviewed(case, layer)
    for control in CONTROLS:
        if control["language"] == language:
            assert [indexed[wid] for wid in control["words"]] == control["source_words"]
            retained(control, layer)
    assert layer["about"] == DATA["unchanged"][language]["about"]
    assert {
        sid: {key: value for key, value in segment.items() if key != "alignments"}
        for sid, segment in layer["segments"].items()
    } == DATA["unchanged"][language]["segment_fields"], "full prose remains unchanged"
    assert {
        wid: {key: value for key, value in entry.items() if key != "gloss"}
        for wid, entry in layer["words"].items()
        if set(entry) - {"gloss"}
    } == DATA["unchanged"][language]["word_help"], "word help remains unchanged"
    restore_dies_irae_layer(layer)
    assert language_packs.check_core(core) == []
    assert language_packs.check_layer(core, layer, path_of(language)) == []
    assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
    assert prose.check(layer) == []


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_selected_captions_and_actual_language_contract(case):
    healthy(*load(case["language"]))


@pytest.mark.parametrize(
    "case,wrong", MUTANTS, ids=[f"{case['id']}-{i}" for i, (case, _) in enumerate(MUTANTS)]
)
def test_selected_previous_or_damaged_wording_rejects_then_restores(case, wrong):
    core, layer = load(case["language"])
    healthy(core, layer)
    saved = deepcopy(layer)
    target = reviewed(case, layer)
    old = target["gloss"]
    try:
        target["gloss"] = wrong
        assert layer != saved and wrong != old
        with pytest.raises(AssertionError, match=r"^selected contextual reading(?:\n|$)"):
            reviewed(case, layer)
    finally:
        target["gloss"] = old
        assert layer == saved
        healthy(core, layer)


@pytest.mark.parametrize(
    "case,fault",
    [(case, fault) for case in GROUPS for fault in FAULTS],
    ids=[f"{case['id']}-{fault}" for case in GROUPS for fault in FAULTS],
)
def test_exact_short_group_accountability_rejects_then_restores(case, fault):
    core, layer = load(case["language"])
    healthy(core, layer)
    saved = deepcopy(layer)
    group = reviewed(case, layer)
    groups = layer["segments"][case["segment"]]["alignments"]
    try:
        if fault == "split":
            groups.remove(group)
            if not groups:
                del layer["segments"][case["segment"]]["alignments"]
            for wid, gloss in zip(case["words"], case["split_glosses"], strict=True):
                layer["words"][wid]["gloss"] = gloss
        elif fault == "residual":
            layer["words"][case["words"][0]]["gloss"] = case["group"]["gloss"]
        elif fault == "duplicate":
            groups.append(deepcopy(group))
        elif fault == "anchor":
            group["anchor"] = next(wid for wid in case["words"] if wid != group["anchor"])
        elif fault == "order":
            group["words"].reverse()
        else:
            group["words"].append(case["next_word"])
            del layer["words"][case["next_word"]]["gloss"]
        assert layer != saved
        errors = interlinear.check(expand_core(core), enrich_layer(core, layer))
        if fault == "residual":
            assert any(
                "expected exactly one direct gloss or alignment" in error for error in errors
            )
        elif fault == "duplicate":
            assert any("belongs to more than one alignment" in error for error in errors)
        elif fault == "order":
            assert any("contiguous and in source order" in error for error in errors)
        with pytest.raises(AssertionError, match=r"^selected contextual reading(?:\n|$)"):
            reviewed(case, layer)
    finally:
        layer.clear()
        layer.update(saved)
        assert layer == saved
        healthy(core, layer)


def test_structurally_valid_zero_cannot_erase_confutatis_then_recovers():
    case = next(case for case in GROUPS if case["words"] == ["w169", "w170"])
    core, layer = load("en")
    healthy(core, layer)
    saved = deepcopy(layer)
    try:
        layer["segments"]["s16"]["alignments"] = [{"words": ["w169"], "reason": "word-order"}]
        layer["words"]["w170"]["gloss"] = "the accursed"
        assert layer != saved
        assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
        with pytest.raises(AssertionError, match=r"^selected contextual reading(?:\n|$)"):
            reviewed(case, layer)
    finally:
        layer.clear()
        layer.update(saved)
        assert layer == saved
        healthy(core, layer)


@pytest.mark.parametrize("control", CONTROLS, ids=[row["id"] for row in CONTROLS])
def test_retained_questions_petitions_and_passive_controls(control):
    healthy(*load(control["language"]))


@pytest.mark.parametrize("control", CONTROLS, ids=[row["id"] for row in CONTROLS])
def test_retained_control_rejects_then_restores(control):
    core, layer = load(control["language"])
    healthy(core, layer)
    saved = deepcopy(layer)
    entry = layer["words"][control["mutate_word"]]
    old = entry["gloss"]
    try:
        entry["gloss"] = control["wrong"]
        assert layer != saved
        with pytest.raises(AssertionError, match=r"^retained contextual force(?:\n|$)"):
            retained(control, layer)
    finally:
        entry["gloss"] = old
        assert layer == saved
        healthy(core, layer)


@pytest.mark.parametrize(
    "language,fault",
    [(language, fault) for language in ("pl", "en") for fault in ("prose", "help", "outside")],
)
def test_complete_target_preservation_rejects_then_restores(language, fault):
    core, layer = load(language)
    healthy(core, layer)
    saved = deepcopy(layer)
    try:
        if fault == "prose":
            layer["segments"]["s08"]["translation"] += " Amen."
        elif fault == "help":
            layer["words"]["w071"]["explanation"] += " Extra."
        else:
            layer["words"]["w171"]["gloss"] += " extra"
        assert layer != saved
        with pytest.raises(AssertionError):
            healthy(core, layer)
    finally:
        layer.clear()
        layer.update(saved)
        assert layer == saved
        healthy(core, layer)


def provenance_rows(language):
    ledger = json.loads(
        (ROOT / "languages" / language / "translation-provenance.json").read_bytes()
    )
    return [row for row in ledger["sites"] if row["text"] == DATA["text"]]


def provenance_contract(language, rows):
    assert rows == DATA["provenance"][language], "unchanged working provenance and protection"


@pytest.mark.parametrize("language", ["pl", "en"])
def test_prose_origin_review_and_protection_are_not_promoted(language):
    provenance_contract(language, provenance_rows(language))


@pytest.mark.parametrize(
    "language,field",
    [
        (language, field)
        for language in ("pl", "en")
        for field in ("origin", "review", "familiar_core", "target_sha256")
    ],
)
def test_provenance_control_rejects_then_restores(language, field):
    rows = provenance_rows(language)
    provenance_contract(language, rows)
    saved = deepcopy(rows)
    target = next(row for row in rows if row["segment"] == "s08")
    old = target[field]
    try:
        target[field] = {
            "origin": "own",
            "review": "expert-reviewed",
            "familiar_core": True,
            "target_sha256": "0" * 64,
        }[field]
        assert rows != saved
        with pytest.raises(
            AssertionError, match=r"^unchanged working provenance and protection(?:\n|$)"
        ):
            provenance_contract(language, rows)
    finally:
        target[field] = old
        assert rows == saved
        provenance_contract(language, rows)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_exact_comparison_copy_restores_whole_predecessor(language):
    _core, layer = load(language)
    saved = deepcopy(layer)
    restored = restore_dies_irae_layer(layer)
    assert restored is not layer and canonical(restored) == DATA["before_canonical"][language]
    assert layer == saved


@pytest.mark.parametrize(
    "language,fault",
    [(language, fault) for language in ("pl", "en") for fault in ("missing", "old-value", "extra")],
)
def test_exact_inverse_rejects_missing_stale_or_extra_then_restores(language, fault):
    core, layer = load(language)
    healthy(core, layer)
    saved = deepcopy(layer)
    operation = next(op for op in DATA["operations"] if op["language"] == language)
    parent, key = parent_at(layer, operation["pointer"])
    try:
        if fault == "missing":
            del parent[key]
        elif fault == "old-value":
            parent[key] = operation["before"]
        else:
            layer["about"] += " Extra."
        assert layer != saved
        with pytest.raises(AssertionError, match="reviewed Dies irae"):
            restore_dies_irae_layer(layer)
    finally:
        layer.clear()
        layer.update(saved)
        assert layer == saved
        healthy(core, layer)
