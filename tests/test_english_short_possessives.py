"""Six short possessives retain actual sources, scope and historical comparisons."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from english_possessive_successor_fixture import (
    DATA,
    before_short_possessive_bytes,
    before_short_possessive_caption_frame,
    before_short_possessive_layer,
)
from test_prayer_prose_successors import healthy as native_healthy
from test_prayer_prose_successors import meaning as native_prose_meaning

from build_reader import emit, store
from build_reader.bibliography_bindings import digest
from build_reader.layers import enrich_layer, expand_core
from checks import english, interlinear, interlinear_quality, prose
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
CASES = DATA["cases"]
LAYERS = DATA["layers"]


def read(relative, root=ROOT):
    return json.loads((root / relative).read_bytes())


def subject(rule):
    return store.core(ROOT, rule["text"]), store.raw_layer(ROOT, "en", rule["text"])


def cases_for(rule):
    return [case for case in CASES if case["text"] == rule["text"]]


def native(core, layer):
    native_healthy(core, layer)
    assert prose.check(layer) == []
    doc, target = expand_core(core), enrich_layer(core, layer)
    assert english.check(doc, target) == []
    assert interlinear_quality.check(doc, target) == []


def assert_case(case, core, layer):
    source = next(segment for segment in core["segments"] if segment["id"] == case["segment"])
    assert canonical_hash(source_payload(source)) == case["source_sha256"], "possessive source"
    words = {word["id"]: word for word in source["words"]}
    assert [{key: words[w["id"]][key] for key in w} for w in case["source_words"]] == (
        case["source_words"]
    )
    assert layer["segments"][case["segment"]]["translation"] == case["translation"], (
        "short possessive full prose"
    )
    touching = [
        group
        for group in interlinear.alignments_for(layer, case["segment"])
        if set(group["words"]) & set(case["group"]["words"])
    ]
    assert touching == [case["group"]], "short possessive caption"
    for word, expected in case["after_entries"].items():
        entry = layer["words"][word]
        assert "gloss" not in entry
        # Expansion may attach genuine projected citations to the retained word help.
        assert {key: entry[key] for key in expected} == expected


def expanded(out, text):
    relative = text.replace(".", "/", 1)
    return emit.expand(
        read(f"texts/{relative}.json", out),
        read(f"languages/en/texts/{relative}.json", out),
        read("tables/morphology.json", out),
        read("tables/analysis.json", out),
        read("tables/citations.json", out),
        read("languages/en/citations.json", out),
    )


@pytest.fixture(scope="module")
def complete_reader(emitted_book):
    """Full real emission owns the global citation-coverage check."""
    assert emit.verify(ROOT, emitted_book[0]) == []
    return emitted_book[0]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_adopted_short_group_has_real_source_and_one_provider(case):
    core, layer = subject(case)
    native(core, layer)
    assert_case(case, core, layer)
    expected = next(
        row
        for row in DATA["provenance_rows"]
        if (row["text"], row["segment"]) == (case["text"], case["segment"])
    )
    recorded = read("languages/en/translation-provenance.json")["sites"]
    row = next(row for row in recorded if row["site"] == expected["site"])
    assert row == expected
    assert row["source_sha256"] == case["source_sha256"]
    assert row["target_sha256"] == canonical_hash(layer["segments"][case["segment"]]["translation"])
    for word, entry in case["after_entries"].items():
        assert layer["words"][word] == entry
    if case["id"] == "consecration-body":
        control = DATA["controls"]["consecration_connective"]
        assert interlinear.alignments_for(layer, "s11") == [control["group"], case["group"]]
        assert case["group"]["gloss"] == "My Body"
        assert layer["segments"]["s11"]["translation"] == "For this is My Body."


@pytest.mark.parametrize("rule", LAYERS, ids=lambda rule: rule["text"])
@pytest.mark.usefixtures("complete_reader")
def test_actual_reader_caption_damage_and_same_artifact_recovery(reader_copy, rule):
    core, layer = subject(rule)
    native(core, layer)
    got_core, got_layer = expanded(reader_copy, rule["text"])
    for case in cases_for(rule):
        assert_case(case, got_core, got_layer)
    case = cases_for(rule)[0]
    path = reader_copy / rule["relative"]
    original = path.read_bytes()
    artifact = json.loads(original)
    row = next(row for row in artifact["seg"] if row["id"] == case["segment"])
    index = layer["segments"][case["segment"]]["alignments"].index(case["group"])
    assert row["a"][index]["g"] == case["group"]["gloss"]
    try:
        row["a"][index]["g"] = case["wrong"]
        path.write_text(json.dumps(artifact, ensure_ascii=False), encoding="utf-8")
        assert path.read_bytes() != original
        where = f"en.segments.{case['segment']}.alignments[{index}].gloss:"
        assert any(f"{rule['text']}: {where}" in error for error in emit.verify(ROOT, reader_copy))
    finally:
        path.write_bytes(original)
    assert path.read_bytes() == original
    assert emit.verify(ROOT, reader_copy) == []
    for case in cases_for(rule):
        assert_case(case, *expanded(reader_copy, rule["text"]))


@pytest.mark.parametrize("rule", LAYERS, ids=lambda rule: rule["text"])
def test_complete_successor_inverses_reject_drift_and_recover_same_input(rule):
    core, actual = subject(rule)
    native(core, actual)
    raw = (ROOT / rule["relative"]).read_bytes()
    saved, same_input = deepcopy(actual), actual
    comparison = before_short_possessive_layer(rule["relative"], actual)
    old_raw = before_short_possessive_bytes(rule["relative"], raw)
    assert comparison is not actual and actual == saved
    assert digest(comparison) == rule["before_canonical_sha256"]
    assert hashlib.sha256(old_raw).hexdigest() == rule["before_raw_sha256"]
    assert json.loads(old_raw) == comparison
    with pytest.raises(AssertionError, match=r"^short possessive current layer$"):
        before_short_possessive_layer(rule["relative"], comparison)
    with pytest.raises(AssertionError, match=r"^short possessive current bytes$"):
        before_short_possessive_bytes(rule["relative"], old_raw)
    for case in cases_for(rule):
        assert_case(case, core, actual)
        group = next(
            group
            for group in interlinear.alignments_for(actual, case["segment"])
            if group == case["group"]
        )
        original, same_group = deepcopy(group), group
        try:
            group["gloss"] = case["wrong"]
            assert interlinear.check(core, actual) == []
            with pytest.raises(AssertionError, match=r"^short possessive caption(?:\n|$)"):
                assert_case(case, core, actual)
            with pytest.raises(AssertionError, match=r"^short possessive current layer$"):
                before_short_possessive_layer(rule["relative"], actual)
            with pytest.raises(AssertionError, match=r"^short possessive current caption frame$"):
                before_short_possessive_caption_frame(rule["relative"], actual)
            assert actual is same_input and actual != saved
        finally:
            group.clear()
            group.update(deepcopy(original))
        assert group is same_group and actual == saved
        assert_case(case, core, actual)
    case = cases_for(rule)[0]
    segment = actual["segments"][case["segment"]]
    original, same_segment = deepcopy(segment), segment
    try:
        segment["translation"] += " Extra."
        with pytest.raises(AssertionError, match=r"^short possessive current layer$"):
            before_short_possessive_layer(rule["relative"], actual)
        captions_only = before_short_possessive_caption_frame(rule["relative"], actual)
        assert captions_only["segments"][case["segment"]]["translation"] == segment["translation"]
        assert actual != saved
    finally:
        segment.clear()
        segment.update(deepcopy(original))
    assert segment is same_segment and actual == saved
    word = case["group"]["words"][0]
    entry = actual["words"][word]
    original, same_entry = deepcopy(entry), entry
    try:
        entry["note"] = "Extra."
        with pytest.raises(AssertionError, match=r"^short possessive current layer$"):
            before_short_possessive_layer(rule["relative"], actual)
        with pytest.raises(AssertionError, match=r"^short possessive current caption frame$"):
            before_short_possessive_caption_frame(rule["relative"], actual)
    finally:
        entry.clear()
        entry.update(deepcopy(original))
    assert entry is same_entry and actual is same_input and actual == saved
    damaged = bytearray(raw)
    same_bytes = damaged
    try:
        damaged.extend(b" ")
        with pytest.raises(AssertionError, match=r"^short possessive current bytes$"):
            before_short_possessive_bytes(rule["relative"], bytes(damaged))
    finally:
        damaged[:] = raw
    assert damaged is same_bytes and bytes(damaged) == raw
    assert before_short_possessive_bytes(rule["relative"], bytes(damaged)) == old_raw
    assert before_short_possessive_layer(rule["relative"], actual) == comparison
    assert before_short_possessive_caption_frame(rule["relative"], actual) == comparison
    native(core, actual)
    assert (ROOT / rule["relative"]).read_bytes() == raw


def test_anima_caption_comparison_keeps_actual_bad_prose_for_original_oracle():
    rule = next(rule for rule in LAYERS if rule["text"] == "orationes.anima-christi")
    core, actual = subject(rule)
    native(core, actual)
    native_prose_meaning(core, actual)
    saved, same_input = deepcopy(actual), actual
    segment = actual["segments"]["s12"]
    original, same_segment = deepcopy(segment), segment
    try:
        tokens = segment["translation"].split()
        assert tokens[6] == "Your"
        tokens[6] = "your"
        segment["translation"] = " ".join(tokens)
        native(core, actual)
        comparison = before_short_possessive_caption_frame(rule["relative"], actual)
        assert comparison["segments"]["s12"]["translation"] == segment["translation"]
        assert comparison["words"]["w058"]["gloss"] == "Your"
        assert "gloss" not in actual["words"]["w058"]
        with pytest.raises(AssertionError, match=r"^direct divine case w058(?:\n|$)"):
            native_prose_meaning(core, actual)
    finally:
        segment.clear()
        segment.update(deepcopy(original))
    assert segment is same_segment and actual is same_input and actual == saved
    native(core, actual)
    native_prose_meaning(core, actual)


def test_healthy_reply_and_preposed_possessive_keep_their_existing_realizations():
    control = DATA["controls"]["reply"]
    core, actual = subject(control)
    native(core, actual)
    assert interlinear.alignments_for(actual, control["segment"]) == [control["group"]]
    assert control["group"]["gloss"] == "your spirit"
    assert actual["segments"][control["segment"]]["translation"] == control["translation"]
    control = DATA["controls"]["preposed"]
    core, actual = subject(control)
    native(core, actual)
    assert actual["segments"][control["segment"]]["translation"] == control["translation"]
    assert {word: actual["words"][word] for word in control["words"]} == control["entries"]
    assert not any(
        set(group["words"]) & set(control["words"])
        for group in interlinear.alignments_for(actual, control["segment"])
    )
