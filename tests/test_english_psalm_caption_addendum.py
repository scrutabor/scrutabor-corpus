"""The Psalm refrain retains its human possessives and real sentence onset."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from english_possessive_successor_fixture import (
    DATA as SIX,
)
from english_possessive_successor_fixture import (
    before_short_possessive_bytes,
    before_short_possessive_caption_frame,
    before_short_possessive_layer,
)
from english_psalm_caption_addendum import DATA
from test_english_short_possessives import assert_case, expanded, native, subject

from build_reader import emit
from build_reader.bibliography_bindings import digest
from checks import interlinear

ROOT = Path(__file__).resolve().parents[1]
CASES = DATA["cases"]


def assert_onset(core, layer):
    rule = DATA["onset"]
    segment = next(s for s in core["segments"] if s["id"] == rule["segment"])
    previous = next(s for s in core["segments"] if s["id"] == rule["previous_segment"])
    assert {key: segment["words"][0][key] for key in rule["source_word"]} == rule["source_word"], (
        "Psalm onset source"
    )
    assert {key: previous["words"][-1][key] for key in rule["previous_terminal"]} == rule[
        "previous_terminal"
    ], "Psalm sentence boundary"
    assert layer["words"][rule["source_word"]["id"]]["gloss"] == rule["gloss"], (
        "Psalm real sentence onset"
    )


def current():
    core, layer = subject(DATA)
    native(core, layer)
    assert_onset(core, layer)
    for case in CASES:
        assert_case(case, core, layer)
    return core, layer


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_refrain_pair_keeps_exact_source_full_prose_and_provider(case):
    core, layer = current()
    assert_case(case, core, layer)
    assert DATA["provenance"]["source_sha256"] == case["source_sha256"]
    ledger = json.loads((ROOT / "languages/en/translation-provenance.json").read_bytes())
    (row,) = [r for r in ledger["sites"] if r["site"] == DATA["provenance"]["site"]]
    assert row == DATA["provenance"]


def test_real_onset_lowercase_regression_fails_then_same_input_recovers():
    core, original = current()
    changed = deepcopy(original)
    same_input = changed
    try:
        changed["words"]["w082"]["gloss"] = "hope"
        assert interlinear.check(core, changed) == []
        with pytest.raises(AssertionError, match=r"^Psalm real sentence onset(?:\n|$)"):
            assert_onset(core, changed)
    finally:
        changed.clear()
        changed.update(deepcopy(original))
    assert changed is same_input and changed == original
    native(core, changed)
    assert_onset(core, changed)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_wrong_possessor_is_structurally_valid_but_rejected_then_same_input_recovers(case):
    core, original = current()
    changed = deepcopy(original)
    same_input = changed
    try:
        group = next(g for g in changed["segments"]["s08"]["alignments"] if g == case["group"])
        group["gloss"] = case["wrong"]
        assert interlinear.check(core, changed) == []
        with pytest.raises(AssertionError, match=r"^short possessive caption(?:\n|$)"):
            assert_case(case, core, changed)
    finally:
        changed.clear()
        changed.update(deepcopy(original))
    assert changed is same_input and changed == original
    native(core, changed)
    assert_case(case, core, changed)


@pytest.mark.parametrize("fault", ["duplicate-direct", "missing-group"])
def test_actual_alignment_fault_rejects_then_same_input_recovers(fault):
    core, original = current()
    changed = deepcopy(original)
    same_input = changed
    try:
        if fault == "duplicate-direct":
            changed["words"]["w090"]["gloss"] = "of my countenance"
        else:
            changed["segments"]["s08"]["alignments"].remove(CASES[0]["group"])
        assert f"{DATA['text']}:w090:en: expected exactly one direct gloss or alignment" in (
            interlinear.check(core, changed)
        )
    finally:
        changed.clear()
        changed.update(deepcopy(original))
    assert changed is same_input and changed == original
    native(core, changed)
    for case in CASES:
        assert_case(case, core, changed)


def test_complete_extended_inverse_reaches_unchanged_six_group_predecessor():
    core, layer = current()
    saved = deepcopy(layer)
    old_rule = next(rule for rule in SIX["layers"] if rule["relative"] == DATA["relative"])
    comparison = before_short_possessive_layer(DATA["relative"], layer)
    raw = (ROOT / DATA["relative"]).read_bytes()
    old_raw = before_short_possessive_bytes(DATA["relative"], raw)
    assert digest(comparison) == old_rule["before_canonical_sha256"]
    assert hashlib.sha256(old_raw).hexdigest() == old_rule["before_raw_sha256"]
    assert json.loads(old_raw) == comparison
    assert comparison is not layer and layer == saved
    assert before_short_possessive_caption_frame(DATA["relative"], layer) == comparison
    fixture = ROOT / "tests/fixtures/english-short-possessive-successors.json"
    assert hashlib.sha256(fixture.read_bytes()).hexdigest() == DATA["six_fixture_sha256"]
    native(core, layer)


@pytest.mark.parametrize("fault", ["unrelated-caption", "word-help", "extra-field"])
def test_exact_frame_drift_is_rejected_then_same_input_recovers(fault):
    core, original = current()
    changed = deepcopy(original)
    same_input = changed
    try:
        if fault == "unrelated-caption":
            changed["words"]["w084"]["gloss"] += " extra"
        elif fault == "word-help":
            changed["words"]["w088"]["explanation"] += " Extra."
        else:
            changed["words"]["w090"]["unexpected"] = "extra"
        for inverse in (before_short_possessive_layer, before_short_possessive_caption_frame):
            with pytest.raises(AssertionError, match=r"^short possessive current"):
                inverse(DATA["relative"], changed)
    finally:
        changed.clear()
        changed.update(deepcopy(original))
    assert changed is same_input and changed == original
    native(core, changed)
    before_short_possessive_layer(DATA["relative"], changed)


def test_caption_comparison_keeps_actual_prose_damage_for_its_original_oracle():
    core, original = current()
    changed = deepcopy(original)
    same_input = changed
    try:
        changed["segments"]["s08"]["translation"] += " Extra."
        with pytest.raises(AssertionError, match=r"^short possessive current layer$"):
            before_short_possessive_layer(DATA["relative"], changed)
        comparison = before_short_possessive_caption_frame(DATA["relative"], changed)
        assert (
            comparison["segments"]["s08"]["translation"]
            == (changed["segments"]["s08"]["translation"])
        )
        with pytest.raises(AssertionError, match=r"^short possessive full prose(?:\n|$)"):
            assert_case(CASES[0], core, comparison)
    finally:
        changed.clear()
        changed.update(deepcopy(original))
    assert changed is same_input and changed == original
    native(core, changed)
    assert_case(CASES[0], core, changed)


def test_real_complete_reader_rejects_both_pairs_and_onset_then_exact_bytes_recover(reader_copy):
    core, layer = current()
    assert emit.verify(ROOT, reader_copy) == []
    path = reader_copy / DATA["relative"]
    original = path.read_bytes()
    for kind in ("countenance", "my-god", "onset"):
        artifact = json.loads(original)
        row = next(r for r in artifact["seg"] if r["id"] == "s08")
        if kind == "onset":
            row["g"][0] = "hope"
            diagnostic = f"{DATA['text']}: en.words.w082.gloss:"
        else:
            index = 0 if kind == "countenance" else 1
            row["a"][index]["g"] = CASES[index]["wrong"]
            diagnostic = f"{DATA['text']}: en.segments.s08.alignments[{index}].gloss:"
        try:
            path.write_text(json.dumps(artifact, ensure_ascii=False), encoding="utf-8")
            assert path.read_bytes() != original
            assert any(diagnostic in error for error in emit.verify(ROOT, reader_copy))
        finally:
            path.write_bytes(original)
        assert path.read_bytes() == original
        assert emit.verify(ROOT, reader_copy) == []
        got_core, got_layer = expanded(reader_copy, DATA["text"])
        assert_onset(got_core, got_layer)
        for case in CASES:
            assert_case(case, got_core, got_layer)
    native(core, layer)
