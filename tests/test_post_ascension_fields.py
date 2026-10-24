"""Ascension Sunday: selected fields, complete consumers and bounded source claims.

Exact selected examples are editorial regressions, not general translation
rules or evidence of independent authorship. Source reviews remain pending.
"""

import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest
from gospel_delivery_fixture import (
    current_sung_expected_row,
    current_sung_source_hash,
    without_sung_delivery,
)
from post_ascension_fixture import FIXTURE, expected_row_successor, restore_layer, value_at
from provenance_successor_fixture import assert_protection_scope

from build_reader import bibliography, store
from build_reader.bibliography_bindings import selected_text, transcript_digest
from build_reader.emit import (
    Table,
    core_artifact,
    expand,
    language_artifact,
    language_formulary_catalog,
)
from build_reader.layers import expand_core
from checks import interlinear, translation_provenance
from checks.language_packs import check_layer
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
TEXTS = sorted(FIXTURE["texts"])
LANGUAGES = ("pl", "en")


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def assert_layer(relative, layer):
    assert canonical_hash(layer) == FIXTURE["language_after_hashes"][relative], "selected layer"
    original = restore_layer(layer, relative)
    assert canonical_hash(original) == FIXTURE["language_before_hashes"][relative], (
        "historical layer inverse"
    )


def assert_analysis(core, language, layer, word):
    expected = {
        "confidence": "medium",
        "sources": ["editorial", "whitakers", "collatinus"],
        "review": "disputed",
    }
    assert core["editorial"]["words"][word]["analysis"] == expected, "local uncertainty"
    path = f"languages/{language}/texts/{core['id'].replace('.', '/', 1)}.json"
    note = next(
        field["after"]
        for field in FIXTURE["language_changes"][path]
        if field["keys"] == ["words", word, "note"]
    )
    assert layer["words"][word]["note"] == note, "local uncertainty note"


def assert_composite(text, graph, transcript):
    expected = FIXTURE["composites"][text]
    assert hashlib.sha256(transcript.encode()).hexdigest() == expected["transcript_sha256"], (
        "composite transcript"
    )
    body = "\n".join(line for line in transcript.splitlines() if not line.startswith("#")) + "\n"
    assert hashlib.sha256(body.encode()).hexdigest() == expected["body_sha256"], "unchanged body"
    for collection in ("uses", "witnesses"):
        for row in expected[collection]:
            actual = [item for item in graph[collection] if item["id"] == row["id"]]
            assert actual == [row], "composite source record"
    witness = expected["witnesses"][0]
    assert witness["transcription_sha256"] == transcript_digest(transcript)
    assert witness["review"] == {"status": "pending"}
    dependencies = witness["source_dependencies"]["uses"]
    assert dependencies and dependencies == sorted(set(dependencies))
    assert all(any(row["id"] == identifier for row in graph["uses"]) for identifier in dependencies)


def test_full_subject_and_bilingual_denominator():
    assert len(TEXTS) == 10 and len(set(TEXTS)) == 10
    assert len(FIXTURE["verse_rows"]) == 8
    assert sum(site.endswith(".pl") for site in FIXTURE["verse_rows"]) == 4
    assert sum(site.endswith(".en") for site in FIXTURE["verse_rows"]) == 4
    words = verses = rubrics = 0
    for text in TEXTS:
        core = store.core(ROOT, text)
        assert (
            canonical_hash(without_sung_delivery(core)["segments"])
            == FIXTURE["segment_hashes"][text]
        )
        for field in FIXTURE["core_fields"].get(text, []):
            assert value_at(core, field["keys"]) == field["after"]
        words += sum(len(segment.get("words", [])) for segment in core["segments"])
        verses += sum(segment["type"] == "verse" for segment in core["segments"])
        rubrics += sum(segment["type"] == "rubric" for segment in core["segments"])
    assert (words, verses, rubrics) == (480, 14, 1)
    assert words * len(LANGUAGES) == 960


@pytest.mark.parametrize("text", TEXTS)
@pytest.mark.parametrize("language", LANGUAGES)
def test_complete_component_and_each_consumer(text, language):
    doc = store.core(ROOT, text)
    layer = store.raw_layer(ROOT, language, text)
    relative = f"languages/{language}/texts/{text.replace('.', '/', 1)}.json"
    assert check_layer(doc, layer, ROOT / relative) == []
    assert interlinear.check(doc, layer) == []
    assert list(layer["words"]) == [
        word["id"] for segment in doc["segments"] for word in segment.get("words", [])
    ]
    for segment in doc["segments"]:
        field = "translation" if segment["type"] == "verse" else "narrative"
        assert layer["segments"][segment["id"]][field].strip()
    consumers = [
        json.loads(path.read_text())["id"]
        for path in sorted((ROOT / "formularies").glob("*/*.json"))
        if any(
            component["text"] == text for component in json.loads(path.read_text())["components"]
        )
    ]
    assert consumers == FIXTURE["consumers"][text]
    assert set(consumers) <= {"ascensio-domini", "dominica-post-ascensionem"}
    if relative in FIXTURE["language_changes"]:
        assert_layer(relative, layer)
    else:
        assert canonical_hash(layer) == FIXTURE["language_after_hashes"][relative]


def test_title_and_exact_eight_about_consumers():
    title = read(FIXTURE["title"]["path"])["title"]
    assert title == FIXTURE["title"]["after"]
    titles = language_formulary_catalog(ROOT, "en")["titles"]
    assert next(row["title"] for row in titles if row["id"] == "dominica-post-ascensionem") == title
    assert len(FIXTURE["about_paths"]) == 8
    for path in FIXTURE["about_paths"]:
        assert f"“{title}”" in read(path)["about"]
    for text, language_hashes in FIXTURE["shared_about_hashes"].items():
        for language, expected in language_hashes.items():
            assert canonical_hash(store.raw_layer(ROOT, language, text)["about"]) == expected


@pytest.mark.parametrize("text,word", sorted(FIXTURE["uncertainty_sites"].items()))
@pytest.mark.parametrize("language", LANGUAGES)
def test_local_uncertainty_preserves_chosen_morphology(text, word, language):
    core, layer = store.core(ROOT, text), store.raw_layer(ROOT, language, text)
    assert (
        canonical_hash(without_sung_delivery(core)["segments"]) == FIXTURE["segment_hashes"][text]
    )
    assert_analysis(core, language, layer, word)
    expanded = expand_core(core)
    actual = next(
        w for segment in expanded["segments"] for w in segment.get("words", []) if w["id"] == word
    )
    assert actual["analysis"] == core["editorial"]["words"][word]["analysis"]


@pytest.mark.parametrize("damage", ["confidence", "review", "note"])
def test_uncertainty_mutants_have_healthy_inputs_and_restore(damage):
    text, word, language = "proprium.dominica-post-ascensionem-communio", "w030", "pl"
    core, layer = store.core(ROOT, text), store.raw_layer(ROOT, language, text)
    assert_analysis(core, language, layer, word)
    bad_core, bad_layer = deepcopy(core), deepcopy(layer)
    if damage == "confidence":
        bad_core["editorial"]["words"][word]["analysis"]["confidence"] = "high"
    elif damage == "review":
        bad_core["editorial"]["words"][word]["analysis"]["review"] = "accepted"
    else:
        bad_layer["words"][word].pop("note")
    assert bad_core != core or bad_layer != layer
    with pytest.raises((AssertionError, KeyError)):
        assert_analysis(bad_core, language, bad_layer, word)
    assert_analysis(core, language, layer, word)


@pytest.mark.parametrize("language", LANGUAGES)
def test_shared_and_zero_transport_is_exact(language):
    text = "proprium.dominica-post-ascensionem-collecta"
    doc, layers = store.load(ROOT, text)
    citations = Table([])
    morph_table, analysis_table = Table([]), Table([])
    core = core_artifact(doc, store.core(ROOT, text), morph_table, analysis_table, citations)
    localized = language_artifact(doc, layers[language], citations)
    decoded_doc, decoded_layer = expand(
        core, localized, morph_table.order, analysis_table.order, citations.order, citations.order
    )
    assert interlinear.check(decoded_doc, decoded_layer) == []
    assert (
        decoded_layer["segments"]["s01"]["alignments"]
        == layers[language]["segments"]["s01"]["alignments"]
    )
    if language == "pl":
        assert {"words": ["w008"], "reason": "idiom"} in decoded_layer["segments"]["s01"][
            "alignments"
        ]
    else:
        assert any(
            "w008" in group["words"] and group.get("gloss")
            for group in decoded_layer["segments"]["s01"]["alignments"]
        )


@pytest.mark.parametrize("damage", ["direct", "overlap", "zero"])
def test_actual_alignment_mutants_are_rejected_after_a_healthy_control(damage):
    language = "pl" if damage == "zero" else "en"
    text = "proprium.dominica-post-ascensionem-collecta"
    doc, layer = store.core(ROOT, text), store.raw_layer(ROOT, language, text)
    assert interlinear.check(doc, layer) == []
    bad = deepcopy(layer)
    groups = bad["segments"]["s01"]["alignments"]
    if damage == "zero":
        group = next(group for group in groups if group.get("reason"))
        group.pop("reason")
        diagnostic = "unrealized alignment needs reason"
    elif damage == "direct":
        group = next(group for group in groups if group.get("gloss"))
        bad["words"][group["words"][0]]["gloss"] = "Duplicated."
        diagnostic = "expected exactly one"
    else:
        group = next(group for group in groups if group.get("gloss"))
        groups.append(deepcopy(group))
        diagnostic = "more than one alignment"
    assert bad != layer
    assert any(diagnostic in error for error in interlinear.check(doc, bad))
    assert interlinear.check(doc, layer) == []


def test_polish_epistle_commands_do_not_change_latin_participles_or_english():
    text = "proprium.dominica-post-ascensionem-epistola"
    core, layer = store.core(ROOT, text), store.raw_layer(ROOT, "pl", text)
    words = {word["id"]: word for segment in core["segments"] for word in segment["words"]}
    for wid, expected in (("w016", "miejcie"), ("w033", "służcie")):
        assert words[wid]["morph"]["mood"] == "part"
        assert words[wid]["morph"]["tense"] == "pres"
        assert layer["words"][wid]["gloss"] == expected
        assert layer["words"][wid]["explanation"]
    assert canonical_hash(core["segments"]) == FIXTURE["segment_hashes"][text]
    assert_layer(
        "languages/en/texts/proprium/dominica-post-ascensionem-epistola.json",
        store.raw_layer(ROOT, "en", text),
    )


def test_all_eight_current_rows_preserve_route_and_exact_signatures():
    ledger, errors = translation_provenance.load(ROOT)
    assert errors == []
    assert len(FIXTURE["historical_english_uses"]) == 2
    for site, expected in FIXTURE["verse_rows"].items():
        row = ledger[site]
        assert row == current_sung_expected_row(expected["after"])
        assert current_sung_expected_row(expected_row_successor(expected["before"])) == row
        text, segment, language = site.rsplit(".", 2)
        source = next(s for s in store.core(ROOT, text)["segments"] if s["id"] == segment)
        target = store.raw_layer(ROOT, language, text)["segments"][segment]["translation"]
        assert row["source_sha256"] == canonical_hash(source_payload(source))
        assert row["target_sha256"] == canonical_hash(target)
        assert row["target_sha256"] != hashlib.sha256(target.encode()).hexdigest()
        assert row["source_sha256"] == current_sung_source_hash(
            text, segment, expected["before"]["source_sha256"]
        )
        assert row["review"] == "working"
    public_domain = {
        site
        for site, row in FIXTURE["verse_rows"].items()
        if row["after"]["origin"] == "public-domain"
    }
    assert public_domain == {
        use["address"]["text"] + "." + use["address"]["segment"] + ".en"
        for use in FIXTURE["historical_english_uses"]
    }


@pytest.mark.parametrize("damage", ["review", "origin", "target"])
def test_exact_expected_row_overlay_rejects_unadmitted_input(damage):
    original = deepcopy(FIXTURE)
    good = next(iter(FIXTURE["verse_rows"].values()))["before"]
    assert expected_row_successor(good) != good
    bad = deepcopy(good)
    key, value = {
        "review": ("review", "expert-reviewed"),
        "origin": ("origin", "own"),
        "target": ("target_sha256", "0" * 64),
    }[damage]
    assert bad[key] != value
    bad[key] = value
    with pytest.raises(AssertionError, match="historical expected row"):
        expected_row_successor(bad)
    assert original == FIXTURE


def test_protected_gloria_does_not_freeze_the_repeated_antiphon():
    text = "proprium.dominica-post-ascensionem-introitus"
    target = store.raw_layer(ROOT, "pl", text)["segments"]["s01"]["translation"]
    assert assert_protection_scope(text, "pl", "s01", target)
    assert assert_protection_scope(text, "pl", "s01", "Próba przed. " + target)
    damaged = target.replace("Chwała Ojcu", "Chwała", 1)
    assert damaged != target
    with pytest.raises(AssertionError, match="protected Gloria Patri"):
        assert_protection_scope(text, "pl", "s01", damaged)


@pytest.mark.parametrize(
    "text",
    sorted(
        [
            "proprium.dominica-post-ascensionem-introitus",
            "proprium.dominica-post-ascensionem-collecta",
            "proprium.dominica-post-ascensionem-secreta",
            "proprium.dominica-post-ascensionem-postcommunio",
        ]
    ),
)
def test_four_composite_headers_and_source_dependencies_stay_pending(text):
    graph = read("bibliography/graph.json")
    transcript = (ROOT / "witnesses" / text / "mr.txt").read_text(encoding="utf-8")
    assert_composite(text, graph, transcript)
    counts = {
        "introitus": [84],
        "collecta": [38, 1],
        "secreta": [29, 4, 1],
        "postcommunio": [33, 1],
    }
    assert [
        len(segment.get("words", [])) for segment in store.core(ROOT, text)["segments"]
    ] == counts[text.rsplit("-", 1)[-1]]
    assert (
        canonical_hash(selected_text(store.core(ROOT, text)))
        == FIXTURE["selected_latin_hashes"][text]
    )
    collations = [c for c in graph["collations"] if c["text"] == text]
    assert collations and all(c["review"] == {"status": "pending"} for c in collations)
    evidence = next(
        row for row in bibliography.public_text_evidence(graph)["texts"] if row["id"] == text
    )
    assert evidence["witnesses"] == [] and "collation" not in evidence


def test_all_eleven_latin_additions_and_two_english_admissions_are_exact():
    graph, packages = bibliography.load(ROOT)
    assert len(FIXTURE["latin_added_uses"]) == 11
    for use in FIXTURE["latin_added_uses"]:
        assert [row for row in graph["uses"] if row["id"] == use["id"]] == [use]
        assert use["decision_reason"] == (
            "Verified against the specified passages of the approved 1962 printing; "
            "witness review remains pending."
        )
    for use in FIXTURE["historical_english_uses"]:
        assert [row for row in packages["en"]["uses"] if row["id"] == use["id"]] == [use]
        assert not any(row["id"] == use["id"] for row in packages["pl"]["uses"])
        assert use["role"] == "historical_wording_basis"
        site = use["address"]["text"] + "." + use["address"]["segment"] + ".en"
        assert store.translation_relationships(ROOT, "en")[site] == "revised"


@pytest.mark.parametrize("damage", ["dependency", "claim", "review", "body"])
def test_composite_mutations_begin_and_end_with_healthy_source_scope(damage):
    text = "proprium.dominica-post-ascensionem-collecta"
    graph = read("bibliography/graph.json")
    transcript = (ROOT / "witnesses" / text / "mr.txt").read_text(encoding="utf-8")
    assert_composite(text, graph, transcript)
    bad, changed = deepcopy(graph), transcript
    if damage == "body":
        changed += "Verbum.\n"
    elif damage == "claim":
        next(row for row in bad["uses"] if row["id"] == f"use.{text}.mr1962")["claim"] = (
            "Complete on one page."
        )
    else:
        witness = next(row for row in bad["witnesses"] if row["id"] == f"witness.{text}.mr1962")
        if damage == "dependency":
            witness["source_dependencies"]["uses"].pop()
        else:
            witness["review"] = {"status": "reviewed", "sha256": "0" * 64}
    assert bad != graph or changed != transcript
    with pytest.raises(AssertionError):
        assert_composite(text, bad, changed)
    assert_composite(text, graph, transcript)


@pytest.mark.parametrize("damage", ["comparator", "other-language"])
def test_real_wording_scanner_rejects_source_scope_loss(damage, monkeypatch):
    original = bibliography.load(ROOT)
    pristine = deepcopy((FIXTURE, original))
    graph, packages = deepcopy(original)
    use = FIXTURE["historical_english_uses"][0]
    selected = next(row for row in packages["en"]["uses"] if row["id"] == use["id"])
    assert selected == use
    site = use["address"]["text"] + "." + use["address"]["segment"] + ".en"
    diagnostic = f"{site}: origin=public-domain requires a wording citation"
    baseline, _ = translation_provenance.check(ROOT)
    assert diagnostic not in baseline
    if damage == "comparator":
        selected["role"] = "historical_wording_comparator"
    else:
        packages["en"]["uses"].remove(selected)
        packages["pl"]["uses"].append(selected)
    assert (graph, packages) != original
    assert (FIXTURE, original) == pristine
    expected = Counter(baseline)
    expected[diagnostic] += 1
    with monkeypatch.context() as patch:
        patch.setattr(bibliography, "load", lambda _root: (graph, packages))
        errors, _ = translation_provenance.check(ROOT)
        assert Counter(errors) == expected
    assert bibliography.load(ROOT) == original
    assert translation_provenance.check(ROOT)[0] == baseline
    assert (FIXTURE, original) == pristine


@pytest.mark.parametrize("damage", ["accepted-field", "unrelated-field"])
def test_exact_inverse_never_erases_unreviewed_changes(damage):
    relative = "languages/en/texts/ordinarium/praefatio-ascensionis.json"
    layer = read(relative)
    assert_layer(relative, layer)
    original = deepcopy((FIXTURE, layer))
    historical = restore_layer(layer, relative)
    assert canonical_hash(historical) == FIXTURE["language_before_hashes"][relative]
    bad = deepcopy(layer)
    if damage == "accepted-field":
        bad["segments"]["s02"]["translation"] += " Changed."
    else:
        bad["about"] += " Changed."
    assert bad != layer
    if damage == "accepted-field":
        with pytest.raises(AssertionError, match="current field value"):
            restore_layer(bad, relative)
    else:
        restored = restore_layer(bad, relative)
        expected = deepcopy(historical)
        expected["about"] = bad["about"]
        assert expected["about"] != historical["about"]
        assert restored == expected
        assert canonical_hash(restored) != FIXTURE["language_before_hashes"][relative]
    with pytest.raises(AssertionError):
        assert_layer(relative, bad)
    assert_layer(relative, layer)
    assert (FIXTURE, layer) == original
