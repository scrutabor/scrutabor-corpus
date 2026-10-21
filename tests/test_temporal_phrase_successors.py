"""Selected temporal phrase aids, complete prose and stable source addresses.

These local readings are not a universal alignment-size or translation rule.
The source and review states remain independent of transport correctness.
"""

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import emit, store
from build_reader.bibliography_bindings import (
    BindingError,
    collation_subject,
    witness_subject,
)
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, translation_provenance
from checks.language_packs import check_core, check_layer
from checks.translation_provenance import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads(
    (Path(__file__).with_name("fixtures") / "temporal-phrase-successors.json").read_text()
)
CASES = [
    pytest.param(row, id=f"{row['language']}-{row['text']}") for row in FIXTURE["caption_cases"]
]
HANC = FIXTURE["hanc"]["text"]


def words(core):
    return [word for segment in core["segments"] for word in segment.get("words", [])]


def owned_provider_error(text, word, language):
    return f"{text}:{word}:{language}: expected exactly one direct gloss or alignment"


def assert_selected_members(layer, case):
    for member in case["members"]:
        wid, expected = member["word"], member["realization"]
        assert layer["words"][wid] == expected["word_fields"], "selected word fields"
        groups = [
            group
            for segment in layer["segments"].values()
            for group in segment.get("alignments", [])
            if wid in group["words"]
        ]
        if expected["kind"] == "realized-alignment":
            assert groups == [expected["alignment"]], "selected phrase provider"
            assert "gloss" not in layer["words"][wid]
        else:
            assert groups == [], "direct provider is not duplicated"
            assert interlinear.effective_gloss(layer, wid) == expected["gloss"]


@pytest.mark.parametrize("case", CASES)
def test_selected_phrases_details_and_owned_provider_controls(case):
    text, language = case["text"], case["language"]
    raw = store.core(ROOT, text)
    layer = store.raw_layer(ROOT, language, text)
    snapshot, fixture_snapshot = deepcopy((raw, layer)), deepcopy(FIXTURE)
    assert canonical_hash(words(raw)) == case["source_word_objects_sha256"]
    assert check_core(raw) == []
    path = store.layer_path(ROOT, language, text)
    assert check_layer(raw, layer, path) == []
    assert interlinear.check(raw, layer) == []
    assert_selected_members(layer, case)
    for wid, explanation in case["explanations"].items():
        assert layer["words"][wid]["explanation"] == explanation

    # Remove one actual provider, then duplicate one without corrupting shape.
    selected = case["members"][0]
    wid, sid = selected["word"], selected["segment"]
    missing, duplicate = deepcopy(layer), deepcopy(layer)
    group = next(
        (g for g in missing["segments"][sid].get("alignments", []) if wid in g["words"]),
        None,
    )
    if group:
        lost = list(group["words"])
        missing["segments"][sid]["alignments"].remove(group)
        duplicate["words"][wid]["gloss"] = "duplicate"
    else:
        lost = [wid]
        del missing["words"][wid]["gloss"]
        groups = duplicate["segments"][sid].setdefault("alignments", [])
        groups.append({"words": [wid], "reason": "word-order"})
        segment = next(s for s in raw["segments"] if s["id"] == sid)
        positions = {word["id"]: i for i, word in enumerate(segment["words"])}
        groups.sort(key=lambda g: positions[g["words"][0]])
    assert missing != layer and duplicate != layer
    assert Counter(interlinear.check(raw, missing)) == Counter(
        owned_provider_error(text, word, language) for word in lost
    )
    assert Counter(interlinear.check(raw, duplicate)) == Counter(
        [owned_provider_error(text, wid, language)]
    )

    assert case["explanations"], "each selected detail has a real required declaration"
    wid = next(iter(case["explanations"]))
    missing_detail = deepcopy(layer)
    del missing_detail["words"][wid]["explanation"]
    assert missing_detail != layer
    assert Counter(check_layer(raw, missing_detail, path)) == Counter(
        [f"{language}:{text}: explanation topology differs — missing=['{wid}'] extra=[]"]
    )
    assert check_layer(raw, layer, path) == []
    assert interlinear.check(raw, layer) == []
    assert_selected_members(layer, case)
    assert (raw, layer) == snapshot and fixture_snapshot == FIXTURE


def assert_retired_addresses(artifact):
    assert artifact.get("rs") == FIXTURE["hanc"]["retired_segments"], "Hanc retirement addresses"


@pytest.mark.parametrize("language", ["pl", "en"])
def test_hanc_merge_round_trips_without_lost_words_or_retired_addresses(language):
    raw, layer = store.core(ROOT, HANC), store.raw_layer(ROOT, language, HANC)
    snapshot, fixture_snapshot = deepcopy((raw, layer)), deepcopy(FIXTURE)
    expected = FIXTURE["hanc"]
    assert [s["id"] for s in raw["segments"]] == expected["live_segments"]
    assert raw["ids"] == expected["ids"]
    assert canonical_hash(words(raw)) == expected["source_word_objects_sha256"]
    merged = next(s for s in raw["segments"] if s["id"] == "s02")
    assert [w["id"] for w in merged["words"]] == expected["merged_word_ids"]
    assert len(merged["words"]) == 35 and len(words(raw)) == 59
    for segment in raw["segments"]:
        if segment["id"] in expected["unchanged_core_segments_sha256"]:
            assert (
                canonical_hash(segment) == expected["unchanged_core_segments_sha256"][segment["id"]]
            )
    assert layer["segments"]["s02"]["translation"] == expected["translations"][language]
    for sid, fields in expected["unchanged_localized_prose"][language].items():
        assert all(layer["segments"][sid][key] == value for key, value in fields.items())
    core, localized = expand_core(raw), enrich_layer(raw, layer)
    tables = [emit.Table() for _ in range(4)]
    artifact = emit.core_artifact(core, raw, *tables[:3])
    target = emit.language_artifact(core, localized, tables[3])
    decoded, translated = emit.expand(artifact, target, *[table.order for table in tables])
    want_core, want_layers = emit._strip(core, {language: localized})
    assert (decoded, translated) == (want_core, want_layers[language])
    assert_retired_addresses(artifact)
    damaged = deepcopy(artifact)
    damaged["rs"]["s03"] = "s05"
    assert damaged != artifact
    with pytest.raises(AssertionError, match=r"^Hanc retirement addresses(?:\n|$)"):
        assert_retired_addresses(damaged)
    assert_retired_addresses(artifact)
    assert (raw, layer) == snapshot and fixture_snapshot == FIXTURE


@pytest.mark.parametrize("language", ["pl", "en"])
def test_hanc_live_provenance_rejects_old_source_and_retired_sites(language, monkeypatch):
    current_all = translation_provenance.corpus_sites(ROOT)
    recorded_all, load_errors = translation_provenance.load(ROOT)
    assert load_errors == []
    current = {
        site: row
        for site, row in current_all.items()
        if row["text"] == HANC and row["language"] == language
    }
    recorded = {
        site: row
        for site, row in recorded_all.items()
        if row["text"] == HANC and row["language"] == language
    }
    expected = FIXTURE["hanc"]["current_sites"][language]
    assert recorded == {row["site"]: row for row in expected.values()}
    assert set(current) == set(recorded) and len(recorded) == 3
    assert all(
        (row["origin"], row["review"], row["familiar_core"])
        == ("working-unsettled", "working", False)
        for row in recorded.values()
    )
    snapshot, fixture_snapshot = deepcopy((current, recorded)), deepcopy(FIXTURE)
    monkeypatch.setattr(translation_provenance, "corpus_sites", lambda _root: deepcopy(current))

    def validate(rows):
        monkeypatch.setattr(translation_provenance, "load", lambda _root: (deepcopy(rows), []))
        return translation_provenance.check(ROOT)

    assert validate(recorded) == ([], {"working-unsettled": 3})
    site = f"{HANC}.s02.{language}"
    old = FIXTURE["hanc"]["previous_sites"][language]
    stale = deepcopy(recorded)
    stale[site]["source_sha256"] = old["s02"]["source_sha256"]
    assert stale != recorded
    errors, tally = validate(stale)
    assert Counter(errors) == Counter([f"{site}: stale source_sha256"])
    assert tally == {"working-unsettled": 3}
    orphaned = deepcopy(recorded)
    retired = old["s03"]
    assert retired["site"] not in current
    orphaned[retired["site"]] = deepcopy(retired)
    errors, tally = validate(orphaned)
    assert Counter(errors) == Counter(
        [f"translation provenance: 1 orphaned site(s); first=['{retired['site']}']"]
    )
    assert tally == {"working-unsettled": 3}
    assert validate(recorded) == ([], {"working-unsettled": 3})
    assert (current, recorded) == snapshot and fixture_snapshot == FIXTURE


def test_hanc_pending_collation_is_bound_to_the_merged_source_not_the_old_layout():
    graph = json.loads((ROOT / "bibliography/graph.json").read_text())
    core = store.core(ROOT, HANC)
    expected = FIXTURE["hanc"]["collation"]
    row = next(r for r in graph["collations"] if r["id"] == expected["id"])
    snapshot, fixture_snapshot = deepcopy((graph, core)), deepcopy(FIXTURE)
    assert row["review"] == expected["review"] == {"status": "pending"}
    assert row["selected_text_sha256"] == expected["selected_after_sha256"]
    witnesses = {
        witness["id"]: witness_subject(ROOT, witness, graph, core)
        for witness in graph["witnesses"]
        if witness["id"] in row["witnesses"]
    }
    healthy = collation_subject(ROOT, row, core, witnesses)
    stale = deepcopy(row)
    stale["selected_text_sha256"] = expected["selected_before_sha256"]
    assert stale != row
    with pytest.raises(
        BindingError, match=r"^selected_text_sha256 differs from the current Latin/ritual subject$"
    ):
        collation_subject(ROOT, stale, core, witnesses)
    assert collation_subject(ROOT, row, core, witnesses) == healthy
    assert (graph, core) == snapshot and fixture_snapshot == FIXTURE


def assert_tract_prose(layer):
    assert layer["segments"]["s01"]["translation"] == FIXTURE["tract"]["translation_after"], (
        "Tract middle-clause and preserved sentence scope"
    )


def test_tract_prose_successor_retains_source_status_captions_and_unchanged_clauses():
    expected = FIXTURE["tract"]
    raw = store.core(ROOT, expected["text"])
    layer = store.raw_layer(ROOT, "en", expected["text"])
    snapshot, fixture_snapshot = deepcopy((raw, layer)), deepcopy(FIXTURE)
    assert_tract_prose(layer)
    rows, errors = translation_provenance.load(ROOT)
    assert errors == []
    row = rows[expected["row_after"]["site"]]
    assert row == expected["row_after"]
    assert row["source_sha256"] == expected["row_before"]["source_sha256"]
    assert row["source_sha256"] == canonical_hash(
        translation_provenance.source_payload(raw["segments"][0])
    )
    assert row["target_sha256"] == canonical_hash(layer["segments"]["s01"]["translation"])
    assert interlinear.check(raw, layer) == []
    for wrong in (
        expected["translation_before"],
        expected["translation_after"].replace("remains forever", "endures forever"),
    ):
        damaged = deepcopy(layer)
        damaged["segments"]["s01"]["translation"] = wrong
        assert damaged != layer
        assert damaged["words"] == layer["words"]
        assert damaged["segments"]["s01"]["alignments"] == layer["segments"]["s01"]["alignments"]
        assert interlinear.check(raw, damaged) == []
        with pytest.raises(
            AssertionError, match=r"^Tract middle-clause and preserved sentence scope(?:\n|$)"
        ):
            assert_tract_prose(damaged)
        assert_tract_prose(layer)
    assert (raw, layer) == snapshot and fixture_snapshot == FIXTURE
