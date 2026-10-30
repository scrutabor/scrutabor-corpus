"""Short contextual predicates retain their arguments and legitimate state controls."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from english_register_successor_fixture import before_english_register_text_layer
from possessive_sweep_b3_successor_fixture import before_possessive_b3_layer

from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs, prose

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads(
    (ROOT / "tests/fixtures/seven-deponent-constructions.json").read_text(encoding="utf-8")
)
CASES = DATA["cases"]
DECISIONS = DATA["decisions"]
CONTROLS = DATA["controls"]
TOPOLOGY = ("split", "residual", "duplicate", "anchor", "order", "too-wide")
SEMANTIC = [(case, wrong) for case in CASES for wrong in case["wrong"]]
NOTES = [case for case in CASES if "note" in case]
POLISH = DATA["polish_controls"]
CORE_BRIDGE = DATA["core_metadata_bridge"]


def path_of(text, language=None):
    base = ROOT if language is None else ROOT / "languages" / language
    return base / "texts" / (text.replace(".", "/", 1) + ".json")


def load(row):
    return (
        json.loads(path_of(row["text"]).read_bytes()),
        json.loads(path_of(row["text"], row["language"]).read_bytes()),
    )


def unit(case, layer):
    touching = [
        group
        for group in layer["segments"]["s01"].get("alignments", [])
        if set(group["words"]) & set(case["words"])
    ]
    assert touching == [case["group"]], "one short contextual predicate"
    assert all("gloss" not in layer["words"][wid] for wid in case["words"]), (
        "one source realization"
    )
    return touching[0]


def decision(row, layer):
    groups = [
        group
        for group in layer["segments"]["s01"].get("alignments", [])
        if row["word"] in group["words"]
    ]
    if row["group"] is None:
        assert groups == [], "retained direct state or boundary"
        assert layer["words"][row["word"]]["gloss"] == row["gloss"]
    else:
        assert groups == [row["group"]], "retained contextual group"
        assert "gloss" not in layer["words"][row["word"]]


def historical_core_identity(text, core, saved):
    raw = path_of(text).read_bytes()
    assert json.loads(raw) == core
    if text != CORE_BRIDGE["text"]:
        assert hashlib.sha256(raw).hexdigest() == saved["core_sha256"]
        return
    assert saved["core_sha256"] == CORE_BRIDGE["before_sha256"]
    comparison = deepcopy(core)
    assert comparison["localization"] == CORE_BRIDGE["after_localization"]
    comparison["localization"] = deepcopy(CORE_BRIDGE["before_localization"])
    historical = json.dumps(
        comparison, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    assert hashlib.sha256(historical).hexdigest() == CORE_BRIDGE["before_canonical_sha256"]


def historical_healthy(row, core, layer):
    text, language = row["text"], row["language"]
    saved = DATA["layers"][text][language]
    assert core["id"] == layer["text"] == text and layer["language"] == language
    indexed = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    for item in DECISIONS:
        if (item["text"], item["language"]) == (text, language):
            assert indexed[item["word"]] == item["source_word"]
            decision(item, layer)
    for case in CASES:
        if (case["text"], case["language"]) == (text, language):
            unit(case, layer)
            for wid, target in case["external"].items():
                assert layer["words"][wid] == target
    assert layer["about"] == saved["about"]
    assert {
        sid: {k: v for k, v in segment.items() if k != "alignments"}
        for sid, segment in layer["segments"].items()
    } == saved["segment_fields"]
    assert {
        sid: segment["alignments"]
        for sid, segment in layer["segments"].items()
        if "alignments" in segment
    } == saved["alignments"]
    assert {
        wid: {k: v for k, v in word.items() if k != "gloss"}
        for wid, word in layer["words"].items()
        if set(word) - {"gloss"}
    } == saved["word_help"], "contextual help unchanged or explicitly supplied"
    assert language_packs.check_core(core) == []
    assert language_packs.check_layer(core, layer, path_of(text, language)) == []
    assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
    assert prose.check(layer) == []
    historical_core_identity(text, core, saved)


def fourth_passive_comparison(layer, language):
    fixture = json.loads(
        (ROOT / "tests/fixtures/proper-fourth-twelve-passive-captions.json").read_text()
    )
    layer = before_possessive_b3_layer(layer)
    text = "proprium.dominica-xiii-post-pentecosten-evangelium"
    case = next(
        row for row in fixture["layers"] if row["text"] == text and row["language"] == language
    )
    comparison = deepcopy(layer)
    for wid, change in case["word_changes"].items():
        assert comparison["words"][wid] == change["after"], "later passive predicate"
        comparison["words"][wid] = deepcopy(change["before"])
    change = case["alignment_changes"]["s01"]
    assert comparison["segments"]["s01"]["alignments"] == change["after"], "later passive predicate"
    comparison["segments"]["s01"]["alignments"] = deepcopy(change["before"])
    return comparison


def fifth_passive_comparison(layer, language):
    layer = before_possessive_b3_layer(layer)
    layer = before_english_register_text_layer(layer, "fifth passive predicate")
    fixture = json.loads(
        (ROOT / "tests/fixtures/proper-fifth-twelve-passive-captions.json").read_text()
    )
    text = "proprium.dominica-xix-post-pentecosten-evangelium"
    case = next(
        row for row in fixture["layers"] if row["text"] == text and row["language"] == language
    )
    comparison = deepcopy(layer)
    for wid, change in case["word_changes"].items():
        assert comparison["words"][wid] == change["after"], "fifth passive predicate"
        comparison["words"][wid] = deepcopy(change["before"])
    change = case["alignment_changes"]["s01"]
    assert comparison["segments"]["s01"]["alignments"] == change["after"], "fifth passive predicate"
    comparison["segments"]["s01"]["alignments"] = deepcopy(change["before"])
    historical = json.dumps(
        comparison, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    assert hashlib.sha256(historical).hexdigest() == case["before_sha256"], (
        "fifth passive unchanged remainder"
    )
    return comparison


def sixth_passive_comparison(layer, language):
    fixture = json.loads(
        (ROOT / "tests/fixtures/proper-sixth-twelve-passive-captions.json").read_text()
    )
    layer = before_possessive_b3_layer(layer)
    text = "proprium.dominica-xxiii-post-pentecosten-evangelium"
    case = next(
        row for row in fixture["layers"] if row["text"] == text and row["language"] == language
    )
    comparison = deepcopy(layer)
    for wid, change in case["word_changes"].items():
        assert comparison["words"][wid] == change["after"], "later healing predicate"
        comparison["words"][wid] = deepcopy(change["before"])
    for sid, change in case["alignment_changes"].items():
        assert comparison["segments"][sid]["alignments"] == change["after"]
        comparison["segments"][sid]["alignments"] = deepcopy(change["before"])
    historical = json.dumps(
        comparison, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    assert hashlib.sha256(historical).hexdigest() == case["before_sha256"]
    return comparison


def healthy(row, core, layer):
    if row["text"] == "proprium.dominica-xix-post-pentecosten-evangelium":
        assert language_packs.check_core(core) == []
        assert language_packs.check_layer(core, layer, path_of(row["text"], row["language"])) == []
        assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
        assert prose.check(layer) == []
        historical_healthy(row, core, fifth_passive_comparison(layer, row["language"]))
        return
    if row["text"] == "proprium.dominica-xxiii-post-pentecosten-evangelium":
        assert language_packs.check_core(core) == []
        assert language_packs.check_layer(core, layer, path_of(row["text"], row["language"])) == []
        assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
        assert prose.check(layer) == []
        historical_healthy(row, core, sixth_passive_comparison(layer, row["language"]))
        return
    if row["text"] != "proprium.dominica-xiii-post-pentecosten-evangelium":
        # A later exact English register successor is undone on a copy first; the
        # current layer itself must still pass the product validators.
        previous = before_english_register_text_layer(before_possessive_b3_layer(layer))
        if previous is not layer:
            assert language_packs.check_core(core) == []
            path = path_of(row["text"], row["language"])
            assert language_packs.check_layer(core, layer, path) == []
            assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
            assert prose.check(layer) == []
        historical_healthy(row, core, previous)
        return
    assert language_packs.check_core(core) == []
    assert language_packs.check_layer(core, layer, path_of(row["text"], row["language"])) == []
    assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
    assert prose.check(layer) == []
    historical_healthy(row, core, fourth_passive_comparison(layer, row["language"]))


@pytest.mark.parametrize("row", DECISIONS, ids=[row["id"] for row in DECISIONS])
def test_all_thirty_contextual_decisions_and_complete_layer_contract(row):
    healthy(row, *load(row))


@pytest.mark.parametrize(
    "case,fault",
    [(case, fault) for case in CASES for fault in TOPOLOGY],
    ids=[f"{case['id']}-{fault}" for case in CASES for fault in TOPOLOGY],
)
def test_short_group_accountability_rejects_then_restores(case, fault):
    core, layer = load(case)
    healthy(case, core, layer)
    saved = deepcopy(layer)
    group = unit(case, layer)
    groups = layer["segments"]["s01"]["alignments"]
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
            group["anchor"] = case["words"][1]
        elif fault == "order":
            group["words"].reverse()
        else:
            group["words"].append(case["next_word"])
        assert layer != saved
        if fault in {"residual", "duplicate", "order", "too-wide"}:
            assert interlinear.check(expand_core(core), enrich_layer(core, layer))
        with pytest.raises(
            AssertionError,
            match=r"^one (?:short contextual predicate|source realization)(?:\n|$)",
        ):
            unit(case, layer)
    finally:
        layer.clear()
        layer.update(saved)
        assert layer == saved
        healthy(case, core, layer)


@pytest.mark.parametrize(
    "case,wrong", SEMANTIC, ids=[f"{case['id']}-{i}" for i, (case, _) in enumerate(SEMANTIC)]
)
def test_active_meaning_agreement_and_external_arguments_reject_then_restore(case, wrong):
    core, layer = load(case)
    healthy(case, core, layer)
    saved = deepcopy(layer)
    group = unit(case, layer)
    try:
        group["gloss"] = wrong
        assert layer != saved and wrong != case["group"]["gloss"]
        with pytest.raises(AssertionError, match=r"^one short contextual predicate(?:\n|$)"):
            unit(case, layer)
    finally:
        group["gloss"] = case["group"]["gloss"]
        assert layer == saved
        healthy(case, core, layer)


@pytest.mark.parametrize("control", CONTROLS, ids=[row["id"] for row in CONTROLS])
def test_existing_return_boundary_and_direct_dead_state_reject_false_joins(control):
    core, layer = load(control)
    healthy(control, core, layer)
    saved = deepcopy(layer)
    try:
        groups = layer["segments"]["s01"].setdefault("alignments", [])
        if control["kind"] == "return-boundary":
            group = next(group for group in groups if group["words"] == ["w061", "w062"])
            group["words"] = ["w060", "w061"]
            assert interlinear.check(expand_core(core), enrich_layer(core, layer))
        else:
            groups.append(control["wrong_group"])
            for wid in control["wrong_group"]["words"]:
                del layer["words"][wid]["gloss"]
        assert layer != saved
        with pytest.raises(AssertionError):
            healthy(control, core, layer)
    finally:
        layer.clear()
        layer.update(saved)
        assert layer == saved
        healthy(control, core, layer)


@pytest.mark.parametrize(
    "case,fault",
    [(case, fault) for case in NOTES for fault in ("missing", "semicolon")],
    ids=[f"{case['id']}-{fault}" for case in NOTES for fault in ("missing", "semicolon")],
)
def test_state_explanation_is_present_and_uses_valid_reader_prose(case, fault):
    core, layer = load(case)
    healthy(case, core, layer)
    saved = deepcopy(layer)
    try:
        if fault == "missing":
            del layer["words"]["w032"]["explanation"]
        else:
            layer["words"]["w032"]["explanation"] = case["note"].replace(". ", "; ", 1)
            assert any("uses a semicolon" in error for error in prose.check(layer))
        assert layer != saved
        with pytest.raises(AssertionError):
            healthy(case, core, layer)
    finally:
        layer.clear()
        layer.update(saved)
        assert layer == saved
        healthy(case, core, layer)


@pytest.mark.parametrize("control", POLISH, ids=[row["id"] for row in POLISH])
def test_existing_polish_active_predicates_do_not_become_passive(control):
    core, layer = load(control)
    healthy(control, core, layer)
    saved = deepcopy(layer)
    group = next(
        group
        for group in layer["segments"]["s01"]["alignments"]
        if group["words"] == control["words"]
    )
    try:
        group["gloss"] = control["wrong"]
        assert layer != saved
        with pytest.raises(AssertionError):
            healthy(control, core, layer)
    finally:
        group["gloss"] = control["group"]["gloss"]
        assert layer == saved
        healthy(control, core, layer)


@pytest.mark.parametrize(
    "language,fault",
    [
        (language, fault)
        for language in ("pl", "en")
        for fault in ("missing", "wrong-token", "narrowed")
    ],
    ids=[
        f"{language}-{fault}"
        for language in ("pl", "en")
        for fault in ("missing", "wrong-token", "narrowed")
    ],
)
def test_real_explanation_declaration_rejects_then_restores(language, fault):
    case = next(case for case in NOTES if case["language"] == language)
    core, layer = load(case)
    healthy(case, core, layer)
    saved_core, saved_layer = deepcopy(core), deepcopy(layer)
    localization = core["localization"]
    saved = deepcopy(localization)
    try:
        if fault == "missing":
            del localization["explanations"]
        elif fault == "wrong-token":
            localization["explanations"] = {"w033": {}}
        else:
            other = "en" if language == "pl" else "pl"
            localization["explanations"]["w032"] = {"languages": [other]}
        assert core != saved_core and layer == saved_layer
        assert language_packs.check_core(core) == []
        missing = ["w033"] if fault == "wrong-token" else []
        assert language_packs.check_layer(core, layer, path_of(case["text"], language)) == [
            f"{language}:{case['text']}: explanation topology differs — "
            f"missing={missing} extra=['w032']"
        ]
        with pytest.raises(AssertionError):
            healthy(case, core, layer)
    finally:
        localization.clear()
        localization.update(saved)
        assert core["localization"] is localization
        assert core == saved_core and layer == saved_layer
        healthy(case, core, layer)


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("fault", ["missing", "wrong", "extra"])
def test_later_passive_inverse_rejects_unaccounted_changes_then_recovers(language, fault):
    row = next(
        row
        for row in DECISIONS
        if row["text"] == "proprium.dominica-xiii-post-pentecosten-evangelium"
        and row["language"] == language
    )
    core, layer = load(row)
    healthy(row, core, layer)
    saved = deepcopy(layer)
    groups = layer["segments"]["s01"]["alignments"]
    group = next(group for group in groups if group["words"] == ["w059", "w060"])
    try:
        if fault == "missing":
            groups.remove(group)
        elif fault == "wrong":
            group["gloss"] = "control"
        else:
            layer["words"]["w060"]["gloss"] = "control"
        assert layer != saved
        with pytest.raises(AssertionError, match=r"^later passive predicate(?:\n|$)"):
            fourth_passive_comparison(layer, language)
    finally:
        layer.clear()
        layer.update(saved)
    assert layer == saved
    healthy(row, core, layer)
