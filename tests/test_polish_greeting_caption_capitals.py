"""Seven Polish response openings preserve full prayers and local case boundaries."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from english_contract_successor_fixture import before_english_contract_layer
from foot_communion_successor_fixture import (
    before_foot_communion_core_bytes,
    before_foot_communion_core_object,
)
from pater_agnus_successor_fixture import (
    before_pater_agnus_core_bytes,
    before_pater_agnus_core_object,
)

from build_reader import store
from build_reader.emit import Table, core_artifact, expand, language_artifact
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs
from checks.translation_provenance import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "tests/fixtures/polish-greeting-caption-capitals.json").read_bytes())
CASES = DATA["cases"]


def require(condition, label):
    if not condition:
        raise AssertionError(label)


def prose_scope(layer):
    return {
        "about": layer.get("about"),
        "segments": {
            sid: {
                key: value for key, value in segment.items() if key in ("translation", "narrative")
            }
            for sid, segment in layer["segments"].items()
        },
    }


def native(core, raw):
    doc, layer = expand_core(core), enrich_layer(core, raw)
    assert language_packs.check_core(core) == []
    path = ROOT / "languages/pl/texts" / (core["id"].replace(".", "/", 1) + ".json")
    assert language_packs.check_layer(core, raw, path) == []
    assert interlinear.check(doc, layer) == []
    parses, analyses, shared, local = Table(), Table(), Table(), Table()
    neutral = core_artifact(doc, core, parses, analyses, shared)
    localized = language_artifact(doc, layer, local)
    back, received = expand(
        neutral, localized, parses.order, analyses.order, shared.order, local.order
    )
    assert back["id"] == core["id"]
    assert received["words"] == layer["words"]
    assert received["segments"] == layer["segments"]
    assert received.get("about") == layer.get("about")
    return back, received


def response(case, core, raw):
    assert core["id"] == raw["text"] == case["text"]
    assert (
        canonical_hash(
            before_foot_communion_core_object(
                case["text"], before_pater_agnus_core_object(case["text"], core)
            )
        )
        == case["source_canonical_sha256"]
    )
    source = next(segment for segment in core["segments"] if segment["id"] == case["segment"])
    assert [word["id"] for word in source["words"]] == case["words"]
    assert [word["form"] for word in source["words"]] == ["Et", "cum", "spíritu", "tuo"]
    assert source["words"][0]["lemma"] == "et"
    assert source["words"][0]["morph"]["pos"] == "conj"
    assert source["words"][-1]["post"] == "."
    assert raw["segments"][case["segment"]]["translation"] == "I z duchem twoim."
    back, received = native(core, raw)
    realized = [interlinear.effective_gloss(received, word) for word in case["words"]]
    require(realized[0] == "I", "Polish response sentence initial")
    assert realized[1:] == ["z", "duchem", "twoim"]
    assert canonical_hash(prose_scope(raw)) == case["prose_sha256"]
    assert prose_scope(received) == prose_scope(raw)
    recovered = next(segment for segment in back["segments"] if segment["id"] == case["segment"])
    assert [(word["id"], word["form"]) for word in recovered["words"]] == list(
        zip(case["words"], case["forms"], strict=True)
    )


@pytest.mark.parametrize("case", CASES, ids=[row["text"] for row in CASES])
def test_actual_complete_response_reaches_native_reader(case):
    response(case, store.core(ROOT, case["text"]), store.raw_layer(ROOT, "pl", case["text"]))


@pytest.mark.parametrize("case", CASES, ids=[row["text"] for row in CASES])
def test_old_lowercase_is_structurally_valid_but_local_boundary_rejects_and_recovers(case):
    core = store.core(ROOT, case["text"])
    layer = store.raw_layer(ROOT, "pl", case["text"])
    record = layer["words"][case["word"]]
    saved, whole = deepcopy(record), deepcopy(layer)
    response(case, core, layer)
    try:
        record["gloss"] = "i"
        assert layer != whole
        native(core, layer)
        with pytest.raises(AssertionError, match=r"^Polish response sentence initial$"):
            response(case, core, layer)
    finally:
        record.clear()
        record.update(deepcopy(saved))
    assert layer["words"][case["word"]] is record
    assert layer == whole
    response(case, core, layer)


def test_exact_seven_byte_inverses_keep_every_other_field_and_language():
    assert len(CASES) == 7
    for case in CASES:
        raw = (ROOT / case["path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == case["after_sha256"]
        before = bytearray(raw)
        assert before[case["byte_offset"]] == ord("I")
        before[case["byte_offset"]] = ord("i")
        assert hashlib.sha256(before).hexdigest() == case["before_sha256"]
        comparison = json.loads(before)
        comparison["words"][case["word"]]["gloss"] = "I"
        assert comparison == json.loads(raw)
        source = ROOT / "texts" / (case["text"].replace(".", "/", 1) + ".json")
        source_raw = before_pater_agnus_core_bytes(case["text"], source.read_bytes())
        source_raw = before_foot_communion_core_bytes(case["text"], source_raw)
        assert hashlib.sha256(source_raw).hexdigest() == case["source_sha256"]
        english = ROOT / "languages/en/texts" / (case["text"].replace(".", "/", 1) + ".json")
        # English caption groups have their own controls; the complete prayers stay intact
        # once a later exact English successor is undone on a copy.
        previous = before_english_contract_layer(
            str(english.relative_to(ROOT)), json.loads(english.read_bytes())
        )
        assert canonical_hash(prose_scope(previous)) == case["english_prose_sha256"]


@pytest.mark.parametrize("text", ["ordinarium.confiteor", "ordinarium.confiteor-sacerdotis"])
def test_existing_noninitial_polish_conjunction_stays_lowercase(text):
    core, layer = store.core(ROOT, text), store.raw_layer(ROOT, "pl", text)
    native(core, layer)
    word = next(
        word
        for segment in core["segments"]
        for word in segment.get("words", [])
        if word["id"] == "w057"
    )
    assert word["form"] == "et" and word["lemma"] == "et"
    assert interlinear.effective_gloss(layer, "w057") == "i"
