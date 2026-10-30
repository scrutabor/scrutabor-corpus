"""Contextual spiritual worship preserves the offering and its objective petition."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
import test_main_ordo_registrations as registrations
from canon_consecration_successor_fixture import (
    before_canon_bytes,
    before_canon_core_frame,
    before_canon_layer_frame,
    before_canon_object,
)
from communicantes_prose_successor_fixture import before_communicantes_ledger
from lent_easter_successor_fixture import RULE as LENT
from lent_easter_successor_fixture import before_lent_easter_ledger
from perceptio_purpose_successor_fixture import before_perceptio_bytes, before_perceptio_object
from quam_rationabilem_successor_fixture import (
    DATA,
    before_quam_bytes,
    before_quam_core_bytes,
    before_quam_ledger,
    before_quam_object,
)

from build_reader import bibliography, emit, store
from build_reader.bibliography_bindings import digest, selected_text
from build_reader.layers import enrich_layer, expand_core
from checks import english, interlinear, language_packs, prose, translation_provenance
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
NOTE_FAULTS = ("exclusive-sense", "Holy-Spirit-agent", "merely-symbolic")
LEDGER_FAULTS = ("target", "source", "origin", "review", "familiar", "order")


def native(core, layer):
    assert language_packs.check_core(core) == []
    assert language_packs.check_layer(core, layer, ROOT / DATA["layer_relative"]) == []
    assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
    assert english.check(expand_core(core), enrich_layer(core, layer)) == []
    assert prose.check(layer) == []


def visible(entry):
    return {key: entry[key] for key in ("gloss", "explanation", "note") if key in entry}


def assert_adopted(core, layer):
    core, layer = before_canon_core_frame(core), before_canon_layer_frame(layer)
    segments = {s["id"]: s for s in core["segments"]}
    words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    assert core["id"] == DATA["text"] and len(words) == 27
    for rule in DATA["source_segments"]:
        assert canonical_hash(source_payload(segments[rule["segment"]])) == rule["sha256"], (
            "Quam unchanged Latin source"
        )
    assert words["w003"]["lemma"] == "tu" and words["w004"]["morph"]["case"] == "voc"
    assert words["w014"]["morph"]["person"] == 2
    assert words["w020"]["morph"]["person"] == 3 and words["w020"]["morph"]["number"] == "sg"
    assert words["w016"]["lemma"] == "nos" and words["w016"]["morph"]["case"] == "dat"
    assert words["w017"]["lemma"] == "corpus" and words["w019"]["lemma"] == "sanguis"
    assert visible(layer["words"]["w011"]) == DATA["entry"], "Quam adopted interpretation"
    assert layer["segments"]["s03"]["translation"] == DATA["prose"]["s03"], (
        "Quam adopted interpretation"
    )
    assert not any(
        "w011" in group["words"]
        for segment in layer["segments"].values()
        for group in segment.get("alignments", [])
    ), "Quam adopted direct provider"
    for row in DATA["five_predicates"]:
        assert {key: words[row["word"]][key] for key in row["source"]} == row["source"]
        assert words[row["word"]]["head"] == "w002"
        assert layer["words"][row["word"]]["gloss"] == row["gloss"]
    for sid, expected in DATA["prose"].items():
        assert layer["segments"][sid]["translation"] == expected, "Quam retained full petition"
    for sid, expected in DATA["narratives"].items():
        assert layer["segments"][sid]["narrative"] == expected
    assert {wid: visible(entry) for wid, entry in layer["words"].items() if wid != "w011"} == (
        DATA["other_word_entries"]
    ), "Quam unrelated word help"


def current():
    core = store.core(ROOT, DATA["text"])
    layer = store.raw_layer(ROOT, "en", DATA["text"])
    assert core["localization"]["explanations"]["w011"] == {"languages": ["en"]}
    native(core, layer)
    assert_adopted(core, layer)
    return core, layer


def restore(value, saved):
    value.clear()
    value.update(deepcopy(saved))


def test_actual_five_predicates_context_and_literal_countercontrol():
    core, actual = current()
    saved, same_input = deepcopy(actual), actual
    try:
        actual["words"]["w011"]["gloss"] = DATA["literal_gloss"]
        actual["segments"]["s03"]["translation"] = DATA["literal_prose"]
        # The explained literal interpretation is not a shape or general grammar error.
        native(core, actual)
        with pytest.raises(AssertionError, match=r"^Quam adopted interpretation(?:\n|$)"):
            assert_adopted(core, actual)
    finally:
        restore(actual, saved)
    assert actual is same_input and actual == saved
    assert_adopted(core, actual)
    try:
        actual["segments"]["s03"]["alignments"] = [
            {"words": ["w010", "w011"], "anchor": "w011", "gloss": "ratified and spiritual"}
        ]
        assert any(
            "w011:en: expected exactly one direct gloss or alignment" in message
            for message in interlinear.check(core, actual)
        )
    finally:
        restore(actual, saved)
    assert actual is same_input and actual == saved
    native(core, actual)
    assert_adopted(core, actual)


@pytest.mark.parametrize("fault", NOTE_FAULTS)
def test_contextual_note_faults_reject_and_restore(fault):
    core, actual = current()
    saved, same_input = deepcopy(actual), actual
    notes = {
        "exclusive-sense": "The adjective can only mean spiritual. It has no rational sense.",
        "Holy-Spirit-agent": "The Holy Spirit makes the offering spiritual.",
        "merely-symbolic": "The following petition asks only for a symbolic Body and Blood.",
    }
    try:
        actual["words"]["w011"]["explanation"] = notes[fault]
        assert actual != saved
        native(core, actual)
        with pytest.raises(AssertionError, match=r"^Quam adopted interpretation(?:\n|$)"):
            assert_adopted(core, actual)
    finally:
        restore(actual, saved)
    assert actual is same_input and actual == saved
    native(core, actual)
    assert_adopted(core, actual)


@pytest.mark.parametrize("fault", ["undeclared", "PL-leak"])
def test_EN_only_note_scope_rejects_and_restores(fault):
    core, layer = current()
    saved, same_input = deepcopy(core), core
    path = store.layer_path(ROOT, "pl", DATA["text"])
    pl_raw = path.read_bytes()
    polish = store.raw_layer(ROOT, "pl", DATA["text"])
    polish_saved = deepcopy(polish)
    assert language_packs.check_layer(core, polish, path) == []
    try:
        if fault == "undeclared":
            del core["localization"]["explanations"]["w011"]
            errors = language_packs.check_layer(core, layer, ROOT / DATA["layer_relative"])
            assert any(
                "explanation topology differs" in e and "extra=['w011']" in e for e in errors
            )
        else:
            core["localization"]["explanations"]["w011"]["languages"] = ["en", "pl"]
            errors = language_packs.check_layer(core, polish, path)
            assert any(
                "explanation topology differs" in e and "missing=['w011']" in e for e in errors
            )
        assert language_packs.check_core(core) == []
        assert core != saved and polish == polish_saved and path.read_bytes() == pl_raw
    finally:
        restore(core, saved)
    assert core is same_input and core == saved
    assert polish == polish_saved and path.read_bytes() == pl_raw
    assert language_packs.check_layer(core, polish, path) == []
    native(core, layer)


@pytest.mark.parametrize("fault", LEDGER_FAULTS)
def test_one_row_actual_input_and_whole_frame_inverse(fault, monkeypatch):
    current()
    relative = DATA["ledger_relative"]
    raw = (ROOT / relative).read_bytes()
    actual = json.loads(raw)
    saved, same_input = deepcopy(actual), actual
    rows = actual["sites"]
    original_order = list(rows)
    rule = DATA["ledger_change"]
    row = rows[rule["index"]]
    row_saved = deepcopy(row)
    assert row == rule["after"]
    recorded, errors = translation_provenance.load(ROOT)
    assert errors == []
    polish = {site: entry for site, entry in recorded.items() if entry["language"] == "pl"}
    polish_saved = deepcopy(polish)
    assert polish
    for entry in rows:
        assert recorded[entry["site"]] == entry
        recorded[entry["site"]] = entry
    site = row["site"]
    calls = []

    def actual_recorded_input(corpus):
        assert corpus == ROOT
        calls.append(recorded)
        return recorded, []

    monkeypatch.setattr(translation_provenance, "load", actual_recorded_input)
    assert translation_provenance.check(ROOT)[0] == []
    assert translation_provenance.corpus_sites(ROOT)[site]["has_wording_citations"] is False
    damaged = bytearray(raw)
    same_bytes = damaged
    expected = before_quam_ledger(relative, actual)
    try:
        if fault in ("target", "source"):
            row[f"{fault}_sha256"] = "0" * 64
            diagnostic = f"{site}: stale {fault}_sha256"
        elif fault == "origin":
            row["origin"] = "public-domain"
            diagnostic = f"{site}: origin=public-domain requires a wording citation"
        elif fault == "review":
            row["review"] = "internally-reviewed"
            diagnostic = f"{site}: unsettled origin cannot claim review=internally-reviewed"
        elif fault == "familiar":
            row["familiar_core"] = True
            diagnostic = f"{site}: stale or incorrect familiar_core"
        else:
            assert fault == "order"
            index = rule["index"]
            rows[index], rows[index + 1] = rows[index + 1], rows[index]
            diagnostic = None
        messages, _ = translation_provenance.check(ROOT)
        if diagnostic:
            assert diagnostic in messages
        else:
            # Site-map validation does not claim to validate list serialization order.
            assert messages == []
        assert calls[-1] is recorded and recorded[site] is row and actual != saved
        assert all(recorded[key] is entry for key, entry in polish.items())
        assert {key: recorded[key] for key in polish} == polish_saved
        damaged[:] = json.dumps(actual, ensure_ascii=False).encode()
        with pytest.raises(AssertionError, match=r"^Quam current ledger$"):
            before_quam_ledger(relative, actual)
        with pytest.raises(AssertionError, match=r"^exact Quam comparison bytes$"):
            before_quam_bytes(relative, bytes(damaged))
    finally:
        restore(row, row_saved)
        rows[:] = original_order
        damaged[:] = raw
    assert actual is same_input and actual["sites"] is rows and actual == saved
    assert recorded[site] is row and row == row_saved
    assert all(recorded[key] is entry for key, entry in polish.items())
    assert {key: recorded[key] for key in polish} == polish_saved
    assert damaged is same_bytes and bytes(damaged) == raw
    assert translation_provenance.check(ROOT)[0] == []
    assert before_quam_ledger(relative, actual) == expected
    assert before_quam_bytes(relative, bytes(damaged)) == before_quam_bytes(relative, raw)


def test_neutral_metadata_source_registration_inverse(monkeypatch):
    core, layer = current()
    relative = DATA["core_relative"]
    raw = (ROOT / relative).read_bytes()
    comparison = before_quam_core_bytes(DATA["text"], raw)
    old = before_quam_object(relative, core)
    assert json.loads(comparison) == old
    assert selected_text(before_canon_object(relative, core)) == selected_text(old)
    row = next(r for r in registrations.ROWS if r["text"] == DATA["text"])
    assert hashlib.sha256(comparison).hexdigest() == row["core_sha256"]
    graph, _ = bibliography.load(ROOT)
    real = registrations.witness_subject
    calls = []

    def observed(root, witness, evidence, doc):
        assert doc == core and doc["localization"]["explanations"]["w011"] == {"languages": ["en"]}
        calls.append(doc)
        return real(root, witness, evidence, doc)

    monkeypatch.setattr(registrations, "witness_subject", observed)
    registrations.assert_registered_payload(ROOT, graph, row)
    assert calls
    actual, saved = deepcopy(core), deepcopy(core)
    same_input = actual
    for fault in ("Latin", "declaration", "unrelated-editorial"):
        try:
            if fault == "Latin":
                actual["segments"][0]["words"][1]["form"] += "x"
                assert selected_text(actual) != selected_text(core)
            elif fault == "declaration":
                actual["localization"]["explanations"]["w011"]["languages"] = ["pl"]
            else:
                actual["editorial"]["notes"] += " Extra."
            assert actual != saved
            with pytest.raises(AssertionError, match=r"^Quam current comparison$"):
                before_quam_object(relative, actual)
            with pytest.raises(AssertionError, match=r"^exact Quam core metadata$"):
                before_quam_core_bytes(DATA["text"], json.dumps(actual).encode())
        finally:
            restore(actual, saved)
        assert actual is same_input and actual == saved
        assert before_quam_object(relative, actual) == old
        native(actual, layer)


def test_real_complete_reader_faults_restore_same_bytes(reader_copy):
    core, layer = current()
    assert emit.verify(ROOT, reader_copy) == []
    path = reader_copy / DATA["layer_relative"]
    original = path.read_bytes()
    source = json.loads((reader_copy / DATA["core_relative"]).read_bytes())
    tables = [
        json.loads((reader_copy / p).read_bytes())
        for p in (
            "tables/morphology.json",
            "tables/analysis.json",
            "tables/citations.json",
            "languages/en/citations.json",
        )
    ]
    segment = next(s for s in core["segments"] if s["id"] == "s03")
    index = [w["id"] for w in segment["words"]].index("w011")
    for fault in ("translation", "gloss", "explanation"):
        artifact = json.loads(original)
        row = next(r for r in artifact["seg"] if r["id"] == "s03")
        if fault == "translation":
            assert row["tr"] == DATA["prose"]["s03"]
            row["tr"] = DATA["literal_prose"]
            where = "en.segments.s03.translation:"
        elif fault == "gloss":
            assert row["g"][index] == "spiritual"
            row["g"][index] = DATA["literal_gloss"]
            where = "en.words.w011.gloss:"
        else:
            assert row["ex"]["w011"] == DATA["entry"]["explanation"]
            row["ex"]["w011"] = "The Holy Spirit makes the offering spiritual."
            where = "en.words.w011.explanation:"
        try:
            path.write_text(json.dumps(artifact, ensure_ascii=False), encoding="utf-8")
            assert path.read_bytes() != original
            assert any(
                f"{DATA['text']}: {where}" in error for error in emit.verify(ROOT, reader_copy)
            )
        finally:
            path.write_bytes(original)
        assert path.read_bytes() == original
        assert emit.verify(ROOT, reader_copy) == []
        assert_adopted(*emit.expand(source, json.loads(original), *tables))
    native(core, layer)


def test_all_three_raw_and_object_inverses_keep_every_unselected_field():
    current()
    for relative, rule in DATA["objects"].items():
        raw = (ROOT / relative).read_bytes()
        actual = json.loads(raw)
        saved = deepcopy(actual)
        comparison = before_quam_object(relative, actual)
        before_raw = before_quam_bytes(relative, raw)
        assert (
            digest(before_perceptio_object(relative, before_canon_object(relative, actual)))
            == rule["after_canonical_sha256"]
        )
        assert digest(comparison) == rule["before_canonical_sha256"]
        assert (
            hashlib.sha256(
                before_perceptio_bytes(relative, before_canon_bytes(relative, raw))
            ).hexdigest()
            == (rule["after_raw_sha256"])
        )
        assert hashlib.sha256(before_raw).hexdigest() == rule["before_raw_sha256"]
        assert json.loads(before_raw) == comparison and actual == saved and comparison is not actual
        with pytest.raises(AssertionError, match=r"^Quam current comparison$"):
            before_quam_object(relative, comparison)
    relative = DATA["ledger_relative"]
    actual = json.loads((ROOT / relative).read_bytes())
    assert digest(before_communicantes_ledger(relative, actual)) == LENT["after_canonical_sha256"]
    assert digest(before_lent_easter_ledger(relative, actual)) == LENT["before_canonical_sha256"]
    fixture = ROOT / "tests/fixtures/communicantes-prose-successor.json"
    assert hashlib.sha256(fixture.read_bytes()).hexdigest() == DATA["communicantes_fixture_sha256"]
    unrelated = {"unchanged": True}
    path = "languages/pl/translation-provenance.json"
    assert before_quam_object(path, unrelated) is unrelated
    assert before_quam_bytes(path, b"unchanged") == b"unchanged"
