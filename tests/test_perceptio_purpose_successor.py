"""Reception benefits its speaker through protection and the receipt of healing."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
import test_main_ordo_registrations as registrations
from perceptio_purpose_successor_fixture import (
    DATA,
    before_perceptio_bytes,
    before_perceptio_core_bytes,
    before_perceptio_ledger,
    before_perceptio_object,
)
from quam_rationabilem_successor_fixture import before_quam_ledger

from build_reader import bibliography, emit, store
from build_reader.bibliography_bindings import digest
from build_reader.layers import enrich_layer, expand_core
from checks import english, interlinear, language_packs, prose, translation_provenance
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
MEANING_FAULTS = ("receiver", "healing-agent", "promised-cure", "lost-body")
GROUP_FAULTS = (
    ("body", "duplicate-direct"),
    ("body", "foreign-anchor"),
    ("body", "missing-group"),
    ("purpose", "duplicate-direct"),
    ("purpose", "foreign-anchor"),
    ("purpose", "missing-group"),
)
HELP_FAULTS = ("undeclared", "PL-required", "missing-note", "semicolon", "duplicate-language")
LEDGER_FAULTS = ("target", "source", "origin", "review", "familiar", "order")
DRIFT_FAULTS = ("Latin", "other-prose", "declaration")


def restore(actual, saved):
    actual.clear()
    actual.update(deepcopy(saved))


def native(core, layer):
    assert language_packs.check_core(core) == [], "Perceptio native core"
    assert language_packs.check_layer(core, layer, ROOT / DATA["files"]["layer"]["relative"]) == []
    doc, localized = expand_core(core), enrich_layer(core, layer)
    assert interlinear.check(doc, localized) == [], "Perceptio native interlinear"
    assert english.check(doc, localized) == [], "Perceptio native English"
    assert prose.check(layer) == [], "Perceptio native prose"


def assert_purpose_help(layer):
    assert layer["words"]["w033"]["explanation"] == DATA["explanation"], "Perceptio purpose help"


def assert_context(core, layer):
    segments = {row["id"]: row for row in core["segments"]}
    words = {word["id"]: word for row in core["segments"] for word in row["words"]}
    assert list(segments) == ["s01", "s02", "s03", "s04"] and len(words) == 50
    for row in DATA["source_segments"]:
        actual = segments[row["segment"]]
        assert canonical_hash(source_payload(actual)) == row["source_sha256"], (
            "Perceptio source signature"
        )
        assert actual["speaker"] == "sacerdos" and actual["voice"] == "secreto"
    assert words["w001"]["morph"]["case"] == "nom"
    assert words["w002"]["morph"]["case"] == "gen"
    assert words["w003"]["head"] == "w002"
    assert words["w007"]["morph"]["gender"] == "n"
    for identity in ("w013", "w024"):
        assert words[identity]["morph"]["case"] == "dat"
        assert words[identity]["morph"]["number"] == "sg"
    for identity in ("w014", "w023"):
        assert words[identity]["morph"]["mood"] == "subj"
        assert words[identity]["morph"]["person"] == 3
    assert words["w025"]["head"] == "w026" and words["w031"]["head"] == "w032"
    assert words["w033"]["head"] == "w032"
    assert all(
        words["w033"]["morph"][key] == value
        for key, value in {
            "mood": "part",
            "tense": "fut",
            "voice": "pass",
            "case": "acc",
            "number": "sg",
            "gender": "f",
        }.items()
    )
    for sid, expected in DATA["retained_prose"].items():
        assert layer["segments"][sid]["translation"] == expected, "Perceptio retained prose"
    assert layer["segments"]["s03"]["translation"] == DATA["purpose_translation"], (
        "Perceptio prayer purpose"
    )
    assert layer["about"] == DATA["about"], "Perceptio retained about"
    for group in DATA["groups"].values():
        assert layer["segments"][group["segment"]]["alignments"] == [group["alignment"]], (
            "Perceptio short group"
        )
    assert layer["words"]["w031"]["gloss"] == "for"
    assert_purpose_help(layer)
    assert words["w049"]["post"] == "."
    assert layer["segments"]["s04"]["translation"].endswith(". Amen.")
    assert layer["words"]["w050"]["gloss"] == "Amen", "Perceptio final onset"
    direct = {word for word, entry in layer["words"].items() if "gloss" in entry}
    shared = [
        word
        for row in layer["segments"].values()
        for group in row.get("alignments", [])
        for word in group["words"]
    ]
    assert len(direct) == 44 and len(shared) == len(set(shared)) == 6
    assert direct.isdisjoint(shared) and direct | set(shared) == set(words)


def current():
    core = store.core(ROOT, DATA["text"])
    layer = store.raw_layer(ROOT, "en", DATA["text"])
    native(core, layer)
    assert_context(core, layer)
    return core, layer


def test_actual_full_prayer_source_controller_and_purpose(monkeypatch):
    core, layer = current()
    assert core["localization"]["explanations"]["w033"] == {"languages": ["en"]}
    pl = store.raw_layer(ROOT, "pl", DATA["text"])
    assert language_packs.check_layer(core, pl, store.layer_path(ROOT, "pl", DATA["text"])) == []
    old_core = before_perceptio_object(DATA["files"]["core"]["relative"], core)
    assert expand_core(old_core) == expand_core(core)
    assert enrich_layer(old_core, pl) == enrich_layer(core, pl)
    rule = DATA["ledger"]
    actual = json.loads((ROOT / rule["relative"]).read_bytes())
    assert actual["sites"][rule["index"]] == rule["after"]
    assert canonical_hash(layer["segments"]["s03"]["translation"]) == rule["after"]["target_sha256"]
    assert (rule["after"]["origin"], rule["after"]["review"], rule["after"]["familiar_core"]) == (
        "working-unsettled",
        "working",
        False,
    )
    registration = next(row for row in registrations.ROWS if row["text"] == DATA["text"])
    graph, _ = bibliography.load(ROOT)
    real = registrations.witness_subject
    calls = []

    def observed(root, witness, evidence, doc):
        assert doc == core and doc["localization"]["explanations"]["w033"] == {"languages": ["en"]}
        calls.append(doc)
        return real(root, witness, evidence, doc)

    monkeypatch.setattr(registrations, "witness_subject", observed)
    registrations.assert_registered_payload(ROOT, graph, registration)
    assert calls


def test_literal_passive_purpose_is_a_healthy_native_countercontrol():
    core, layer = current()
    alternative = deepcopy(layer)
    alternative["segments"]["s03"]["translation"] = DATA["old_purpose_translation"]
    alternative["segments"]["s03"]["alignments"][0]["gloss"] = "healing to be received"
    native(core, alternative)
    # A finite chosen-version oracle is distinct from a universal passive ban.
    with pytest.raises(AssertionError, match=r"^Perceptio prayer purpose(?:\n|$)"):
        assert_context(core, alternative)
    word = alternative["words"]["w033"]
    saved = deepcopy(word)
    for false_help in (
        "After ad, the gerundive imposes an obligation to receive healing.",
        "Receiving Christ’s Body guarantees immediate cure of every illness.",
    ):
        try:
            word["explanation"] = false_help
            native(core, alternative)
            with pytest.raises(AssertionError, match=r"^Perceptio purpose help(?:\n|$)"):
                assert_purpose_help(alternative)
        finally:
            restore(word, saved)
        assert alternative["words"]["w033"] is word and word == saved
        assert_purpose_help(alternative)
    native(core, layer)


def test_final_Amen_onset_fault_then_the_same_word_mapping_recovers():
    core, actual = current()
    word = actual["words"]["w050"]
    saved, whole = deepcopy(word), deepcopy(actual)
    try:
        word["gloss"] = "amen"
        native(core, actual)
        with pytest.raises(AssertionError, match=r"^Perceptio final onset(?:\n|$)"):
            assert_context(core, actual)
    finally:
        restore(word, saved)
    assert actual["words"]["w050"] is word and actual == whole
    native(core, actual)
    assert_context(core, actual)


@pytest.mark.parametrize("fault", MEANING_FAULTS)
def test_purpose_fault_is_exposed_then_the_same_segment_recovers(fault):
    core, actual = current()
    row = actual["segments"]["s03"]
    saved, whole = deepcopy(row), deepcopy(actual)
    faults = {
        "receiver": ("bring me healing", "bring You healing"),
        "healing-agent": ("bring me healing", "let me heal others"),
        "promised-cure": ("bring me healing", "instantly cure every illness"),
        "lost-body": ("my mind and body", "my mind"),
    }
    before, after = faults[fault]
    try:
        assert row["translation"].count(before) == 1
        row["translation"] = row["translation"].replace(before, after, 1)
        assert actual["segments"]["s03"] is row and row != saved
        native(core, actual)
        with pytest.raises(AssertionError, match=r"^Perceptio prayer purpose(?:\n|$)"):
            assert_context(core, actual)
    finally:
        restore(row, saved)
    assert actual["segments"]["s03"] is row and actual == whole
    native(core, actual)
    assert_context(core, actual)


@pytest.mark.parametrize(
    "name,fault", GROUP_FAULTS, ids=[f"{name}-{fault}" for name, fault in GROUP_FAULTS]
)
def test_short_group_native_fault_and_original_objects_recover(name, fault):
    core, actual = current()
    rule = DATA["groups"][name]
    groups = actual["segments"][rule["segment"]]["alignments"]
    group = groups[0]
    entry = actual["words"][group["words"][0]]
    refs, saved_group = list(groups), deepcopy(group)
    saved_entry, whole = deepcopy(entry), deepcopy(actual)
    try:
        if fault == "duplicate-direct":
            entry["gloss"] = "duplicated"
        elif fault == "foreign-anchor":
            group["anchor"] = "w001"
        else:
            assert fault == "missing-group"
            groups.remove(group)
        errors = interlinear.check(expand_core(core), enrich_layer(core, actual))
        assert errors and any(DATA["text"] in error for error in errors)
        assert actual != whole
    finally:
        restore(group, saved_group)
        restore(entry, saved_entry)
        groups[:] = refs
    assert groups[0] is group and actual["words"][rule["alignment"]["words"][0]] is entry
    assert actual == whole
    native(core, actual)
    assert_context(core, actual)


@pytest.mark.parametrize("fault", HELP_FAULTS)
def test_actual_help_topology_and_own_voice_fault_then_same_inputs_recover(fault):
    core, actual = current()
    requirements = core["localization"]["explanations"]
    declaration, entry = requirements["w033"], actual["words"]["w033"]
    refs, saved_declaration = dict(requirements), deepcopy(declaration)
    saved_entry = deepcopy(entry)
    whole_core, whole_layer = deepcopy(core), deepcopy(actual)
    pl = store.raw_layer(ROOT, "pl", DATA["text"])
    try:
        if fault == "undeclared":
            del requirements["w033"]
            errors = language_packs.check_layer(
                core, actual, ROOT / DATA["files"]["layer"]["relative"]
            )
            assert any(
                "explanation topology differs" in error and "extra=['w033']" in error
                for error in errors
            )
        elif fault == "PL-required":
            declaration["languages"] = ["en", "pl"]
            assert language_packs.check_core(core) == []
            errors = language_packs.check_layer(
                core, pl, store.layer_path(ROOT, "pl", DATA["text"])
            )
            assert any("missing=['w033']" in error for error in errors)
        elif fault == "missing-note":
            del entry["explanation"]
            errors = language_packs.check_layer(
                core, actual, ROOT / DATA["files"]["layer"]["relative"]
            )
            assert any("missing=['w033']" in error for error in errors)
        elif fault == "semicolon":
            entry["explanation"] += "; extra."
            assert any("uses a semicolon" in error for error in prose.check(actual))
        else:
            assert fault == "duplicate-language"
            declaration["languages"] = ["en", "en"]
            assert any("sorted unique en/pl" in error for error in language_packs.check_core(core))
    finally:
        restore(declaration, saved_declaration)
        requirements.clear()
        requirements.update(refs)
        restore(entry, saved_entry)
    assert requirements["w033"] is declaration and actual["words"]["w033"] is entry
    assert core == whole_core and actual == whole_layer
    native(core, actual)
    assert language_packs.check_layer(core, pl, store.layer_path(ROOT, "pl", DATA["text"])) == []


@pytest.mark.parametrize("fault", LEDGER_FAULTS)
def test_same_actual_ledger_reaches_native_and_strict_inverse_then_recovers(fault, monkeypatch):
    rule = DATA["ledger"]
    raw = (ROOT / rule["relative"]).read_bytes()
    actual = json.loads(raw)
    rows = actual["sites"]
    row = rows[rule["index"]]
    refs, saved_row, whole = list(rows), deepcopy(row), deepcopy(actual)
    recorded, errors = translation_provenance.load(ROOT)
    assert errors == []
    polish = {site: entry for site, entry in recorded.items() if entry["language"] == "pl"}
    polish_saved = deepcopy(polish)
    assert polish
    for entry in rows:
        assert recorded[entry["site"]] == entry
        recorded[entry["site"]] = entry
    calls = []

    def actual_recorded_input(corpus):
        assert corpus == ROOT
        calls.append(recorded)
        return recorded, []

    monkeypatch.setattr(translation_provenance, "load", actual_recorded_input)
    assert translation_provenance.check(ROOT)[0] == []
    expected = before_perceptio_ledger(rule["relative"], actual)
    try:
        if fault in ("target", "source"):
            row[fault + "_sha256"] = "0" * 64
        elif fault == "origin":
            row["origin"] = "public-domain"
        elif fault == "review":
            row["review"] = "internally-reviewed"
        elif fault == "familiar":
            row["familiar_core"] = True
        else:
            assert fault == "order"
            index = rule["index"]
            rows[index], rows[index + 1] = rows[index + 1], rows[index]
        messages, _ = translation_provenance.check(ROOT)
        assert calls[-1] is recorded and recorded[rule["after"]["site"]] is row
        assert all(recorded[site] is entry for site, entry in polish.items())
        assert {site: recorded[site] for site in polish} == polish_saved
        if fault == "order":
            # The native semantic validator is keyed by site; order belongs to the exact frame.
            assert messages == []
        else:
            diagnostic = {
                "target": "stale target_sha256",
                "source": "stale source_sha256",
                "origin": "origin=public-domain requires a wording citation",
                "review": "unsettled origin cannot claim review=internally-reviewed",
                "familiar": "stale or incorrect familiar_core",
            }[fault]
            assert f"{rule['after']['site']}: {diagnostic}" in messages
        with pytest.raises(AssertionError, match=r"^Perceptio current ledger(?:\n|$)"):
            before_perceptio_ledger(rule["relative"], actual)
        assert actual != whole
    finally:
        restore(row, saved_row)
        rows[:] = refs
    assert rows[rule["index"]] is row and actual == whole
    assert all(recorded[site] is entry for site, entry in polish.items())
    assert {site: recorded[site] for site in polish} == polish_saved
    assert before_perceptio_ledger(rule["relative"], actual) == expected
    assert translation_provenance.check(ROOT)[0] == []


@pytest.mark.parametrize("kind", ("layer", "core", "ledger"))
def test_finite_full_raw_and_object_inverse_keeps_actual_current_input(kind):
    rule = DATA["files"][kind]
    raw = (ROOT / rule["relative"]).read_bytes()
    actual = json.loads(raw)
    saved = deepcopy(actual)
    comparison = before_perceptio_object(rule["relative"], actual)
    comparison_raw = before_perceptio_bytes(rule["relative"], raw)
    assert actual == saved and comparison is not actual
    assert digest(actual) == rule["after_canonical_sha256"]
    assert hashlib.sha256(raw).hexdigest() == rule["after_raw_sha256"]
    assert digest(comparison) == rule["before_canonical_sha256"]
    assert hashlib.sha256(comparison_raw).hexdigest() == rule["before_raw_sha256"]
    assert json.loads(comparison_raw) == comparison
    assert (ROOT / rule["relative"]).read_bytes() == raw
    with pytest.raises(AssertionError, match=r"^Perceptio current comparison(?:\n|$)"):
        before_perceptio_object(rule["relative"], comparison)
    with pytest.raises(AssertionError, match=r"^exact Perceptio comparison bytes(?:\n|$)"):
        before_perceptio_bytes(rule["relative"], comparison_raw)
    if kind == "core":
        assert before_perceptio_core_bytes(DATA["text"], raw) == comparison_raw
    unrelated = {"unchanged": True}
    assert (
        before_perceptio_object("languages/pl/translation-provenance.json", unrelated) is unrelated
    )
    assert before_perceptio_bytes("unrelated.json", b"unchanged") == b"unchanged"


@pytest.mark.parametrize("fault", DRIFT_FAULTS)
def test_comparison_cannot_sanitize_unrelated_drift_and_same_mapping_recovers(fault):
    kind = "layer" if fault == "other-prose" else "core"
    rule = DATA["files"][kind]
    raw = (ROOT / rule["relative"]).read_bytes()
    actual = json.loads(raw)
    changed = (
        actual["segments"]["s02"]
        if kind == "layer"
        else (
            actual["segments"][2]["words"][-2]
            if fault == "Latin"
            else actual["localization"]["explanations"]["w033"]
        )
    )
    saved, whole = deepcopy(changed), deepcopy(actual)
    damaged = bytearray(raw)
    expected = before_perceptio_object(rule["relative"], actual)
    try:
        if fault == "other-prose":
            changed["translation"] += " Extra."
        elif fault == "Latin":
            assert changed["id"] == "w032"
            changed["form"] = "aliud"
        else:
            changed["languages"] = ["pl"]
        damaged[:] = json.dumps(actual, ensure_ascii=False).encode()
        with pytest.raises(AssertionError, match=r"^Perceptio current comparison(?:\n|$)"):
            before_perceptio_object(rule["relative"], actual)
        with pytest.raises(AssertionError, match=r"^exact Perceptio comparison bytes(?:\n|$)"):
            before_perceptio_bytes(rule["relative"], bytes(damaged))
    finally:
        restore(changed, saved)
        damaged[:] = raw
    assert actual == whole and bytes(damaged) == raw
    assert before_perceptio_object(rule["relative"], actual) == expected
    assert before_perceptio_bytes(rule["relative"], bytes(damaged)) == before_perceptio_bytes(
        rule["relative"], raw
    )


def test_composed_ledger_retains_the_two_earlier_successors():
    rule = DATA["files"]["ledger"]
    actual = json.loads((ROOT / rule["relative"]).read_bytes())
    saved = deepcopy(actual)
    comparison = before_perceptio_ledger(rule["relative"], actual)
    assert digest(comparison) == rule["before_canonical_sha256"]
    assert [
        i
        for i, pair in enumerate(zip(actual["sites"], comparison["sites"], strict=True))
        if pair[0] != pair[1]
    ] == [DATA["ledger"]["index"]]
    for previous in DATA["previous_ledger_rows"]:
        assert actual["sites"][previous["index"]] == previous["after"]
        assert comparison["sites"][previous["index"]] == previous["after"]
    assert (
        digest(before_quam_ledger(rule["relative"], actual))
        == DATA["after_communicantes_canonical_sha256"]
    )
    assert actual == saved


def test_actual_complete_reader_damage_rejects_then_exact_paths_recover(reader_copy):
    core, layer = current()
    assert emit.verify(ROOT, reader_copy) == []
    path = reader_copy / DATA["files"]["layer"]["relative"]
    original = path.read_bytes()
    source = json.loads((reader_copy / DATA["files"]["core"]["relative"]).read_bytes())
    tables = [
        json.loads((reader_copy / relative).read_bytes())
        for relative in (
            "tables/morphology.json",
            "tables/analysis.json",
            "tables/citations.json",
            "languages/en/citations.json",
        )
    ]
    for fault in ("purpose-prose", "purpose-group", "body-group", "explanation", "Amen"):
        artifact = json.loads(original)
        rows = {row["id"]: row for row in artifact["seg"]}
        if fault == "purpose-prose":
            rows["s03"]["tr"] = rows["s03"]["tr"].replace("healing", "harm", 1)
        elif fault == "purpose-group":
            rows["s03"]["a"][0]["g"] = "healing others"
        elif fault == "body-group":
            rows["s01"]["a"][0]["g"] = "of my Body"
        elif fault == "explanation":
            rows["s03"]["ex"]["w033"] += "; extra."
        else:
            rows["s04"]["g"][-1] = "amen"
        try:
            path.write_text(json.dumps(artifact, ensure_ascii=False), encoding="utf-8")
            assert path.read_bytes() != original
            assert any(
                f"{DATA['text']}: en." in error for error in emit.verify(ROOT, reader_copy)
            ), fault
        finally:
            path.write_bytes(original)
        assert path.read_bytes() == original
        assert emit.verify(ROOT, reader_copy) == []
        assert_context(*emit.expand(source, json.loads(original), *tables))
    native(core, layer)
