"""The human Canon subject retains every saint and the God-directed petition."""

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
from communicantes_prose_successor_fixture import (
    DATA,
    before_communicantes_bytes,
    before_communicantes_layer,
    before_communicantes_ledger,
)
from lent_easter_successor_fixture import RULE as LENT
from lent_easter_successor_fixture import before_lent_easter_bytes, before_lent_easter_ledger
from quam_rationabilem_successor_fixture import before_quam_bytes, before_quam_object

from build_reader import emit, store
from build_reader.bibliography_bindings import digest
from build_reader.layers import enrich_layer, expand_core
from checks import english, interlinear, language_packs, translation_provenance
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
SEMANTIC_FAULTS = (
    "suspended",
    "divine-controller",
    "lost-name",
    "lost-title",
    "petition-agent",
    "intercession-agent",
)
LEDGER_FAULTS = (
    "unexpected-field",
    "other-row",
    "missing-row",
    "duplicate-row",
    "source-digest",
    "review",
    "origin",
)
LAYER_FAULTS = ("other-prose", "caption", "word-help", "about", "unexpected-field")


def native(core, layer):
    assert language_packs.check_layer(core, layer, ROOT / DATA["layer"]["relative"]) == []
    doc, localized = expand_core(core), enrich_layer(core, layer)
    assert interlinear.check(doc, localized) == []
    assert english.check(doc, localized) == []


def caption_frame(layer):
    """Visible wording; source-added citations retain their normal reader projection."""
    return {
        "words": {
            word: {key: entry[key] for key in ("gloss", "explanation", "note") if key in entry}
            for word, entry in layer["words"].items()
        },
        "segments": {
            sid: {"alignments": row["alignments"]} if "alignments" in row else {}
            for sid, row in layer["segments"].items()
        },
    }


def assert_context(core, layer):
    segments = {s["id"]: s for s in core["segments"]}
    words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    assert len(words) == 79 and list(segments) == [f"s{i:02}" for i in range(1, 8)]
    for rule in DATA["source_segments"]:
        source = segments[rule["segment"]]
        assert canonical_hash(source_payload(source)) == rule["source_sha256"], (
            "Communicantes source signature"
        )
        assert source["speaker"] == "sacerdos" and source["voice"] == "secreto"
    for identity in ("w001", "w004"):
        word = words[identity]
        assert word["morph"]["mood"] == "part" and word["morph"]["case"] == "nom"
        assert word["morph"]["number"] == "pl" and word["ellipsis"] == "subject"
    assert words["w066"]["morph"]["person"] == 2
    assert words["w066"]["morph"]["mood"] == "subj"
    assert words["w072"]["morph"]["person"] == 1
    assert words["w072"]["morph"]["number"] == "pl"
    assert words["w072"]["morph"]["voice"] == "pass"
    opening = layer["segments"]["s01"]["translation"]
    assert opening.startswith("We are joined in communion and venerate the memory,"), (
        "Communicantes human controller"
    )
    names = [row["name"] for row in DATA["saints"]]
    assert len(names) == 26
    for row in DATA["saints"]:
        assert words[row["word"]]["lemma"] == row["lemma"]
        assert words[row["word"]]["morph"]["case"] == "gen"
        assert layer["words"][row["word"]]["gloss"] == row["name"]
    prayer = " ".join(layer["segments"][f"s{i:02}"]["translation"] for i in range(1, 6))
    pattern = (
        r"\b(?:"
        + "|".join(re.escape(n) for n in sorted(set(names), key=len, reverse=True))
        + r")\b"
    )
    assert re.findall(pattern, prayer) == names, "Communicantes saint list"
    for sid, expected in DATA["prose"].items():
        assert layer["segments"][sid]["translation"] == expected, "Communicantes retained prose"
    for sid, expected in DATA["narrative"].items():
        assert layer["segments"][sid]["narrative"] == expected
    assert segments["s06"]["text"] == "Iungit manus."
    assert caption_frame(layer) == DATA["captions"], "Communicantes retained captions"


def current():
    core = store.core(ROOT, DATA["text"])
    layer = store.raw_layer(ROOT, "en", DATA["text"])
    native(core, layer)
    assert_context(core, layer)
    return core, layer


def restore(actual, saved):
    actual.clear()
    actual.update(deepcopy(saved))


def test_current_full_context_keeps_human_controller_and_all_source_roles():
    core, layer = current()
    rule = DATA["ledger"]
    ledger = json.loads((ROOT / rule["relative"]).read_bytes())
    assert ledger["sites"][rule["index"]] == rule["after"]
    assert canonical_hash(layer["segments"]["s01"]["translation"]) == rule["after"]["target_sha256"]
    assert rule["before"]["source_sha256"] == rule["after"]["source_sha256"]
    assert (rule["after"]["origin"], rule["after"]["review"]) == ("working-unsettled", "working")
    native(core, layer)


@pytest.mark.parametrize("fault", SEMANTIC_FAULTS)
def test_actual_context_fault_fails_then_same_layer_recovers(fault):
    core, actual = current()
    saved, same_input = deepcopy(actual), actual
    try:
        if fault == "suspended":
            actual["segments"]["s01"]["translation"] = DATA["layer"]["before"]
        elif fault == "divine-controller":
            text = actual["segments"]["s01"]["translation"]
            assert text.startswith("We are")
            actual["segments"]["s01"]["translation"] = text.replace("We are", "You are", 1)
        elif fault == "lost-name":
            text = actual["segments"]["s03"]["translation"]
            assert text.count("Thomas, James, Philip") == 1
            actual["segments"]["s03"]["translation"] = text.replace(
                "Thomas, James, Philip", "Thomas, Philip", 1
            )
        elif fault == "lost-title":
            text = actual["segments"]["s01"]["translation"]
            assert text.count("Mother of God and our Lord Jesus Christ") == 1
            actual["segments"]["s01"]["translation"] = text.replace(
                "Mother of God and our Lord Jesus Christ", "Mother of our Lord Jesus Christ", 1
            )
        else:
            text = actual["segments"]["s05"]["translation"]
            before, after = (
                ("grant,", "we grant,")
                if fault == "petition-agent"
                else ("their merits and prayers", "our merits and prayers")
            )
            assert text.count(before) == 1
            actual["segments"]["s05"]["translation"] = text.replace(before, after, 1)
        assert actual != saved
        native(core, actual)
        with pytest.raises(
            AssertionError,
            match=r"^Communicantes (human controller|saint list|retained prose)(?:\n|$)",
        ):
            assert_context(core, actual)
        assert actual is same_input and actual != saved
    finally:
        restore(actual, saved)
    assert actual is same_input and actual == saved
    native(core, actual)
    assert_context(core, actual)


def test_short_participles_and_real_long_range_subject_sharing_remain_healthy():
    core, layer = current()
    assert layer["words"]["w001"]["gloss"] == "remaining in communion"
    assert "unexpressed subject" in layer["words"]["w001"]["explanation"]
    assert {"words": ["w003", "w004"], "anchor": "w004", "gloss": "venerating the memory"} in (
        layer["segments"]["s01"]["alignments"]
    )
    rule = DATA["long_range_control"]
    source = store.core(ROOT, rule["text"])
    target = store.raw_layer(ROOT, "en", rule["text"])
    words = {w["id"]: w for s in source["segments"] for w in s.get("words", [])}
    assert words["w005"] == rule["source_subject"]
    assert words["w034"] == rule["source_predicate"]
    assert words["w005"]["morph"]["case"] == "nom"
    assert words["w034"]["morph"]["person"] == 1
    for sid, prose in rule["prose"].items():
        assert target["segments"][sid]["translation"] == prose
    assert "we, Your servants" in target["segments"]["s02"]["translation"]
    assert target["segments"]["s03"]["translation"].startswith("offer ")
    assert (
        language_packs.check_layer(source, target, store.layer_path(ROOT, "en", rule["text"])) == []
    )
    assert interlinear.check(expand_core(source), enrich_layer(source, target)) == []
    native(core, layer)


def test_exact_layer_ledger_and_raw_inverses_keep_actual_native_inputs():
    core, layer = current()
    for key, inverse in (
        ("layer", before_communicantes_layer),
        ("ledger", before_communicantes_ledger),
    ):
        rule = DATA[key]
        raw = (ROOT / rule["relative"]).read_bytes()
        actual = json.loads(raw)
        saved = deepcopy(actual)
        current_comparison = before_quam_object(rule["relative"], actual)
        current_raw_comparison = before_quam_bytes(rule["relative"], raw)
        comparison = inverse(rule["relative"], actual)
        before_raw = before_communicantes_bytes(rule["relative"], raw)
        assert digest(current_comparison) == rule["after_canonical_sha256"]
        assert hashlib.sha256(current_raw_comparison).hexdigest() == rule["after_raw_sha256"]
        assert digest(comparison) == rule["before_canonical_sha256"]
        assert hashlib.sha256(before_raw).hexdigest() == rule["before_raw_sha256"]
        assert json.loads(before_raw) == comparison
        assert actual == saved and comparison is not actual
        assert (ROOT / rule["relative"]).read_bytes() == raw
        with pytest.raises(AssertionError, match=r"^Communicantes current"):
            inverse(rule["relative"], comparison)
        with pytest.raises(AssertionError, match=r"^exact Communicantes comparison bytes$"):
            before_communicantes_bytes(rule["relative"], before_raw)
    rule = DATA["ledger"]
    actual_raw = (ROOT / rule["relative"]).read_bytes()
    actual = json.loads(actual_raw)
    old = before_communicantes_ledger(rule["relative"], actual)
    assert digest(old) == LENT["after_canonical_sha256"]
    assert before_lent_easter_ledger(rule["relative"], actual) != old
    assert before_lent_easter_bytes(rule["relative"], actual_raw) != actual_raw
    fixture = ROOT / "tests/fixtures/lent-easter-english-successors.json"
    assert hashlib.sha256(fixture.read_bytes()).hexdigest() == DATA["lent_fixture_sha256"]
    unrelated = {"preserved": True}
    other = "languages/pl/translation-provenance.json"
    assert before_communicantes_ledger(other, unrelated) is unrelated
    assert before_communicantes_layer(other, unrelated) is unrelated
    assert before_communicantes_bytes(other, b"preserved") == b"preserved"
    native(core, layer)


@pytest.mark.parametrize("fault", LEDGER_FAULTS)
def test_ledger_drift_is_rejected_and_same_object_and_bytes_recover(fault):
    rule = DATA["ledger"]
    raw = (ROOT / rule["relative"]).read_bytes()
    actual = json.loads(raw)
    saved, same_input = deepcopy(actual), actual
    damaged = bytearray(raw)
    same_bytes = damaged
    expected = before_communicantes_ledger(rule["relative"], actual)
    expected_raw = before_communicantes_bytes(rule["relative"], raw)
    try:
        row = actual["sites"][rule["index"]]
        if fault == "unexpected-field":
            actual["unexpected"] = True
        elif fault == "other-row":
            assert rule["index"] != 0
            actual["sites"][0]["unexpected"] = True
        elif fault == "missing-row":
            actual["sites"].pop(rule["index"])
        elif fault == "duplicate-row":
            actual["sites"].append(deepcopy(row))
        elif fault == "source-digest":
            row["source_sha256"] = "0" * 64
        elif fault == "review":
            row["review"] = "internally-reviewed"
        else:
            assert fault == "origin"
            row["origin"] = "own"
        damaged[:] = json.dumps(actual, ensure_ascii=False).encode()
        assert actual != saved and json.loads(damaged) == actual
        with pytest.raises(AssertionError, match=r"^Communicantes current ledger$"):
            before_communicantes_ledger(rule["relative"], actual)
        with pytest.raises(AssertionError, match=r"^exact Communicantes comparison bytes$"):
            before_communicantes_bytes(rule["relative"], bytes(damaged))
        with pytest.raises(AssertionError, match=r"^Lent/Easter current ledger(?:\n|$)"):
            before_lent_easter_ledger(rule["relative"], actual)
    finally:
        restore(actual, saved)
        damaged[:] = raw
    assert actual is same_input and actual == saved
    assert damaged is same_bytes and bytes(damaged) == raw
    assert before_communicantes_ledger(rule["relative"], actual) == expected
    assert before_communicantes_bytes(rule["relative"], bytes(damaged)) == expected_raw


@pytest.mark.parametrize("fault", LAYER_FAULTS)
def test_unrelated_layer_drift_cannot_hide_in_comparison_and_recovers(fault):
    core, actual = current()
    saved, same_input = deepcopy(actual), actual
    rule = DATA["layer"]
    raw = (ROOT / rule["relative"]).read_bytes()
    damaged = bytearray(raw)
    same_bytes = damaged
    expected_raw = before_communicantes_bytes(rule["relative"], raw)
    try:
        if fault == "other-prose":
            actual["segments"]["s05"]["translation"] += " Extra."
        elif fault == "caption":
            actual["words"]["w001"]["gloss"] += " extra"
        elif fault == "word-help":
            actual["words"]["w001"]["explanation"] += " Extra."
        elif fault == "about":
            actual["about"] += " Extra."
        else:
            assert fault == "unexpected-field"
            actual["unexpected"] = True
        assert actual != saved
        damaged[:] = json.dumps(actual, ensure_ascii=False).encode()
        with pytest.raises(AssertionError, match=r"^Communicantes current layer$"):
            before_communicantes_layer(rule["relative"], actual)
        with pytest.raises(AssertionError, match=r"^exact Communicantes comparison bytes$"):
            before_communicantes_bytes(rule["relative"], bytes(damaged))
    finally:
        restore(actual, saved)
        damaged[:] = raw
    assert actual is same_input and actual == saved
    assert damaged is same_bytes and bytes(damaged) == raw
    assert before_communicantes_bytes(rule["relative"], bytes(damaged)) == expected_raw
    native(core, actual)
    assert_context(core, actual)


def test_native_provenance_receives_the_original_bad_row_then_recovers(monkeypatch):
    recorded, errors = translation_provenance.load(ROOT)
    assert errors == []
    saved = deepcopy(recorded)
    rule = DATA["ledger"]
    site = rule["after"]["site"]
    row = recorded[site]
    original = deepcopy(row)
    assert row == rule["after"]
    calls = []

    def actual_recorded_input(corpus):
        assert corpus == ROOT
        calls.append(recorded)
        return recorded, []

    monkeypatch.setattr(translation_provenance, "load", actual_recorded_input)
    assert translation_provenance.check(ROOT)[0] == []
    try:
        row["target_sha256"] = "0" * 64
        messages, _ = translation_provenance.check(ROOT)
        assert f"{site}: stale target_sha256" in messages
        assert calls[-1] is recorded and recorded[site] is row and row != original
    finally:
        restore(row, original)
    assert recorded[site] is row and row == original and recorded == saved
    assert translation_provenance.check(ROOT)[0] == []


def test_real_complete_reader_context_damage_rejects_and_exact_bytes_recover(reader_copy):
    core, layer = current()
    assert emit.verify(ROOT, reader_copy) == []
    relative = DATA["layer"]["relative"]
    path = reader_copy / relative
    original = path.read_bytes()
    source = json.loads((reader_copy / "texts/ordinarium/communicantes.json").read_bytes())
    tables = [
        json.loads((reader_copy / p).read_bytes())
        for p in (
            "tables/morphology.json",
            "tables/analysis.json",
            "tables/citations.json",
            "languages/en/citations.json",
        )
    ]
    for identity, fault in (("s01", "human-controller"), ("s05", "petition")):
        artifact = json.loads(original)
        row = next(r for r in artifact["seg"] if r["id"] == identity)
        assert row["tr"] == DATA["prose"][identity]
        row["tr"] = row["tr"].replace("We are", "You are", 1) if identity == "s01" else "We grant."
        try:
            path.write_text(json.dumps(artifact, ensure_ascii=False), encoding="utf-8")
            assert path.read_bytes() != original, fault
            diagnostic = f"{DATA['text']}: en.segments.{identity}.translation:"
            assert any(diagnostic in error for error in emit.verify(ROOT, reader_copy))
        finally:
            path.write_bytes(original)
        assert path.read_bytes() == original
        assert emit.verify(ROOT, reader_copy) == []
        assert_context(*emit.expand(source, json.loads(original), *tables))
    native(core, layer)
