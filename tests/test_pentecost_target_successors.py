"""Pentecost's compact local readings, uncertainty and exact current transport.

Named examples are local editorial regressions, not universal translation rules.
"""

from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest
from pentecost_successor_fixture import FIXTURE, expected_pentecost_row
from provenance_successor_fixture import assert_formula, assert_protection_scope

from build_reader import emit, store
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear
from checks import translation_provenance as provenance
from checks.language_packs import check_core, check_layer

ROOT = Path(__file__).resolve().parents[1]
TEXTS = tuple(FIXTURE["texts"])
READINGS = [pytest.param(row, id=row["id"]) for row in FIXTURE["readings"]]
CAPITALS = [pytest.param(row, id=row["id"]) for row in FIXTURE["target_case"]]
ROWS = [pytest.param(row, id=row["after"]["site"]) for row in FIXTURE["provenance_rows"]]


def words(core):
    return [word for segment in core["segments"] for word in segment.get("words", [])]


def transport(raw, layer):
    core, localized = expand_core(raw), enrich_layer(raw, layer)
    tables = [emit.Table() for _ in range(4)]
    artifact = emit.core_artifact(core, raw, *tables[:3])
    target = emit.language_artifact(core, localized, tables[3])
    result = emit.expand(artifact, target, *[table.order for table in tables])
    expected, layers = emit._strip(core, {layer["language"]: localized})
    assert result == (expected, layers[layer["language"]])
    return result


@pytest.mark.parametrize("text", TEXTS)
@pytest.mark.parametrize("language", ("pl", "en"))
def test_all_scoped_words_details_and_sources_survive_reader_transport(text, language):
    core, layer = store.core(ROOT, text), store.raw_layer(ROOT, language, text)
    snapshot, fixture_snapshot = deepcopy((core, layer)), deepcopy(FIXTURE)
    expected = FIXTURE["texts"][text]
    assert len(words(core)) == expected["words"]
    assert provenance.canonical_hash(words(core)) == expected["word_objects_sha256"]
    assert check_core(core) == []
    assert check_layer(core, layer, store.layer_path(ROOT, language, text)) == []
    assert interlinear.check(core, layer) == []
    memberships = Counter()
    for word in words(core):
        if layer["words"][word["id"]].get("gloss"):
            memberships[word["id"]] += 1
    for segment in layer["segments"].values():
        for group in segment.get("alignments", []):
            memberships.update(group["words"])
    assert memberships == Counter(word["id"] for word in words(core))
    transport(core, layer)
    assert (core, layer) == snapshot and fixture_snapshot == FIXTURE


def assert_reading(layer, row):
    groups = [
        g
        for g in layer["segments"][row["segment"]].get("alignments", [])
        if set(g["words"]) & set(row["alignment"]["words"])
    ]
    assert groups == [row["alignment"]], "selected compact contextual reading"
    assert all("gloss" not in layer["words"][wid] for wid in row["alignment"]["words"]), (
        "one compact provider"
    )
    realized = [(wid, interlinear.effective_gloss(layer, wid)) for wid in row["alignment"]["words"]]
    assert [(wid, value) for wid, value in realized if value] == [
        (row["alignment"]["anchor"], row["alignment"]["gloss"])
    ], "one visible compact reading"


@pytest.mark.parametrize("row", READINGS)
def test_compact_predicates_keep_outside_dependents_and_owned_provider_controls(row):
    core, layer = store.core(ROOT, row["text"]), store.raw_layer(ROOT, row["language"], row["text"])
    snapshot, fixture_snapshot = deepcopy((core, layer)), deepcopy(FIXTURE)
    assert_reading(layer, row)
    assert interlinear.check(core, layer) == []
    for wid, expected_outside in row["outside"].items():
        assert layer["words"][wid] == expected_outside["word_fields"]
        groups = [
            g
            for s in layer["segments"].values()
            for g in s.get("alignments", [])
            if wid in g["words"]
        ]
        assert groups == ([expected_outside["alignment"]] if expected_outside["alignment"] else [])
    wrong = deepcopy(layer)
    group = next(
        g for g in wrong["segments"][row["segment"]]["alignments"] if g == row["alignment"]
    )
    group["gloss"] = row["wrong"]
    assert wrong != layer and interlinear.check(core, wrong) == []
    with pytest.raises(AssertionError, match=r"^selected compact contextual reading(?:\n|$)"):
        assert_reading(wrong, row)
    missing, duplicate = deepcopy(layer), deepcopy(layer)
    wid = row["alignment"]["words"][-1]
    missing["segments"][row["segment"]]["alignments"].remove(row["alignment"])
    duplicate["words"][wid]["gloss"] = "duplicate"
    expected = (
        f"{row['text']}:{wid}:{row['language']}: expected exactly one direct gloss or alignment"
    )
    assert Counter(interlinear.check(core, missing)) == Counter(
        f"{row['text']}:{lost}:{row['language']}: expected exactly one direct gloss or alignment"
        for lost in row["alignment"]["words"]
    )
    assert Counter(interlinear.check(core, duplicate)) == Counter([expected])
    assert_reading(layer, row)
    assert interlinear.check(core, layer) == []
    assert (core, layer) == snapshot and fixture_snapshot == FIXTURE


def assert_target_case(layer, row):
    if "alignment" in row:
        actual = next(
            g
            for g in layer["segments"]["s01"]["alignments"]
            if g["words"] == row["alignment"]["words"]
        )
        assert actual == row["alignment"], "selected target sentence case"
    else:
        assert layer["words"][row["word"]]["gloss"] == row["after"], "selected target sentence case"


@pytest.mark.parametrize("row", CAPITALS)
def test_target_sentence_case_is_a_local_target_decision(row):
    core, layer = store.core(ROOT, row["text"]), store.raw_layer(ROOT, row["language"], row["text"])
    snapshot, fixture_snapshot = deepcopy((core, layer)), deepcopy(FIXTURE)
    assert_target_case(layer, row)
    bad = deepcopy(layer)
    if "alignment" in row:
        next(
            g
            for g in bad["segments"]["s01"]["alignments"]
            if g["words"] == row["alignment"]["words"]
        )["gloss"] = row["before"]
    else:
        bad["words"][row["word"]]["gloss"] = row["before"]
    assert bad != layer and interlinear.check(core, bad) == []
    with pytest.raises(AssertionError, match=r"^selected target sentence case(?:\n|$)"):
        assert_target_case(bad, row)
    assert_target_case(layer, row)
    assert (core, layer) == snapshot and fixture_snapshot == FIXTURE


@pytest.mark.parametrize("language", ("pl", "en"))
def test_communicantes_semicolon_is_not_blindly_capitalized_from_full_prose(language):
    text = "ordinarium.communicantes-in-pentecoste"
    core, layer = store.core(ROOT, text), store.raw_layer(ROOT, language, text)
    snapshot = deepcopy((core, layer))
    assert next(w for w in words(core) if w["id"] == "w075")["post"] == ";"
    expected = "przez ich" if language == "pl" else "through their"
    assert layer["words"]["w076"]["gloss"] == expected
    start = ". Przez ich" if language == "pl" else ". Through their"
    assert start in layer["segments"]["s10"]["translation"]
    assert interlinear.check(core, layer) == []
    assert (core, layer) == snapshot


@pytest.mark.parametrize("language", ("pl", "en"))
def test_ignis_keeps_selected_nominative_with_honest_uncertainty_and_no_source_promotion(language):
    row = FIXTURE["ignis"]
    text = row["text"]
    core, layer = store.core(ROOT, text), store.raw_layer(ROOT, language, text)
    snapshot, fixture_snapshot = deepcopy((core, layer)), deepcopy(FIXTURE)
    assert next(w for w in words(core) if w["id"] == "w036") == row["selected_word"]
    assert row["selected_word"]["morph"]["case"] == "nom"

    def uncertainty(doc):
        assert doc["editorial"]["words"]["w036"]["analysis"] == row["analysis_after"], (
            "honest ignis uncertainty"
        )

    uncertainty(core)
    assert core["localization"]["notes"] == ["w036"]
    assert layer["words"]["w036"]["note"] == row["notes"][language]
    restored = deepcopy(core)
    restored["editorial"]["words"]["w036"]["analysis"] = deepcopy(row["analysis_before"])
    del restored["localization"]["notes"]
    assert restored != core
    assert [provenance.source_payload(s) for s in restored["segments"]] == [
        provenance.source_payload(s) for s in core["segments"]
    ]
    assert layer["segments"] == row["localized_segments"][language]
    decoded, translated = transport(core, layer)
    assert next(w for w in words(decoded) if w["id"] == "w036")["analysis"] == row["analysis_after"]
    assert translated["words"]["w036"]["note"] == row["notes"][language]
    confident = deepcopy(core)
    confident["editorial"]["words"]["w036"]["analysis"]["confidence"] = "high"
    assert confident != core
    with pytest.raises(AssertionError, match=r"^honest ignis uncertainty(?:\n|$)"):
        uncertainty(confident)
    missing = deepcopy(layer)
    del missing["words"]["w036"]["note"]
    assert Counter(check_layer(core, missing, store.layer_path(ROOT, language, text))) == Counter(
        [f"{language}:{text}: note topology differs — missing=['w036'] extra=[]"]
    )
    uncertainty(core)
    assert check_layer(core, layer, store.layer_path(ROOT, language, text)) == []
    assert (core, layer) == snapshot and fixture_snapshot == FIXTURE


@pytest.mark.parametrize("row", ROWS)
def test_prose_successor_binds_real_scanner_without_relabeling(row, monkeypatch):
    expected = row["after"]
    text, language, segment = expected["text"], expected["language"], expected["segment"]
    core, layer = store.core(ROOT, text), store.raw_layer(ROOT, language, text)
    snapshot, fixture_snapshot = deepcopy((core, layer)), deepcopy(FIXTURE)
    actual, errors = provenance.load(ROOT)
    assert errors == [] and actual[expected["site"]] == expected
    assert layer["segments"][segment]["translation"] == row["translation_after"]
    assert {k: v for k, v in expected.items() if k != "target_sha256"} == {
        k: v for k, v in row["before"].items() if k != "target_sha256"
    }
    source = next(s for s in core["segments"] if s["id"] == segment)
    assert provenance.canonical_hash(provenance.source_payload(source)) == expected["source_sha256"]
    assert provenance.canonical_hash(row["translation_after"]) == expected["target_sha256"]
    current = {expected["site"]: provenance.corpus_sites(ROOT)[expected["site"]]}
    recorded = {expected["site"]: deepcopy(actual[expected["site"]])}
    frozen = deepcopy((current, recorded))
    monkeypatch.setattr(provenance, "corpus_sites", lambda _root: deepcopy(current))
    monkeypatch.setattr(provenance, "load", lambda _root: (deepcopy(recorded), []))
    assert provenance.check(ROOT) == ([], {expected["origin"]: 1})
    recorded[expected["site"]]["target_sha256"] = row["before"]["target_sha256"]
    assert recorded != frozen[1]
    errors, tally = provenance.check(ROOT)
    assert Counter(errors) == Counter([expected["site"] + ": stale target_sha256"])
    assert tally == {expected["origin"]: 1}
    recorded = deepcopy(frozen[1])
    assert provenance.check(ROOT) == ([], {expected["origin"]: 1})
    assert (current, recorded) == frozen
    assert (core, layer) == snapshot and fixture_snapshot == FIXTURE


def test_protected_gloria_survives_the_admitted_outside_clause_successor():
    text = "proprium.dominica-pentecostes-introitus"
    layer = store.raw_layer(ROOT, "pl", text)
    snapshot, fixture_snapshot = deepcopy(layer), deepcopy(FIXTURE)
    target = layer["segments"]["s01"]["translation"]
    assert target.count("rozumie to, co się mówi") == 2
    assert {wid: layer["words"][wid] for wid in FIXTURE["gloria_words"]} == FIXTURE["gloria_words"]
    assert_protection_scope(text, "pl", "s01", target)
    bad = target.replace("Chwała Ojcu", "Chwała Ojcowi", 1)
    assert bad != target
    with pytest.raises(AssertionError, match=r"^protected Gloria Patri(?:\n|$)"):
        assert_formula(bad)
    assert_formula("Próba przed. " + target + " Próba po.")
    assert_formula(target)
    assert layer == snapshot and fixture_snapshot == FIXTURE


@pytest.mark.parametrize("language", ("pl", "en"))
def test_sequence_explanation_is_reader_first_and_required_without_public_comparator(language):
    text = "proprium.dominica-pentecostes-sequentia"
    core, layer = store.core(ROOT, text), store.raw_layer(ROOT, language, text)
    snapshot, fixture_snapshot = deepcopy((core, layer)), deepcopy(FIXTURE)
    expected = FIXTURE["sequence_explanations"][language]
    assert layer["words"]["w046"]["explanation"] == expected and "Connelly" not in expected
    assert core["localization"]["explanations"]["w046"] == {}
    assert transport(core, layer)[1]["words"]["w046"]["explanation"] == expected
    missing = deepcopy(layer)
    del missing["words"]["w046"]["explanation"]
    assert missing != layer
    assert Counter(check_layer(core, missing, store.layer_path(ROOT, language, text))) == Counter(
        [f"{language}:{text}: explanation topology differs — missing=['w046'] extra=[]"]
    )
    assert check_layer(core, layer, store.layer_path(ROOT, language, text)) == []
    assert (core, layer) == snapshot and fixture_snapshot == FIXTURE


def test_historical_expected_row_overlay_is_exact_and_does_not_normalize_observations():
    snapshot = deepcopy(FIXTURE)
    for change in FIXTURE["provenance_rows"]:
        before, after = deepcopy(change["before"]), deepcopy(change["after"])
        frozen = deepcopy(before)
        assert expected_pentecost_row(before) == after and before == frozen
        for field, value in (("target_sha256", "0" * 64), ("review", "internally-reviewed")):
            bad = deepcopy(before)
            bad[field] = value
            assert bad != before
            with pytest.raises(AssertionError, match=r"^historical Pentecost expected row(?:\n|$)"):
                expected_pentecost_row(bad)
        with pytest.raises(AssertionError, match=r"^historical Pentecost expected row(?:\n|$)"):
            expected_pentecost_row(after)
        augmented = deepcopy(before)
        augmented["untouched"] = {"nested": ["retained"]}
        result = expected_pentecost_row(augmented)
        result["untouched"]["nested"].append("independent result")
        assert augmented["untouched"] == {"nested": ["retained"]}
        assert expected_pentecost_row(before) == after
    unrelated = {"site": "proprium.unrelated.s01.en", "nested": {"values": ["unchanged"]}}
    copied = expected_pentecost_row(unrelated)
    assert copied == unrelated and copied is not unrelated
    assert copied["nested"] is not unrelated["nested"]
    assert snapshot == FIXTURE


def test_used_quis_note_reaches_the_reader_lemma_card():
    text = "proprium.dominica-pentecostes-evangelium"
    core = store.core(ROOT, text)
    assert next(w for w in words(core) if w["id"] == "w009")["lemma"] == "quis"
    card = emit.lexicon_slice(ROOT, "en", {"quis"})["quis"]
    snapshot, fixture_snapshot = deepcopy(card), deepcopy(FIXTURE)

    def expected_note(candidate):
        assert candidate["note"] == FIXTURE["quis_note"]["after"], "reader quis quotation note"

    expected_note(card)
    bad = deepcopy(card)
    bad["note"] = FIXTURE["quis_note"]["before"]
    assert bad != card
    assert {k: v for k, v in bad.items() if k != "note"} == {
        k: v for k, v in card.items() if k != "note"
    }
    with pytest.raises(AssertionError, match=r"^reader quis quotation note(?:\n|$)"):
        expected_note(bad)
    expected_note(card)
    assert emit.lexicon_slice(ROOT, "en", {"quis"})["quis"] == card
    assert card == snapshot and fixture_snapshot == FIXTURE
