"""Local source-preserving readings and their unsettled provenance bindings."""

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest
from corpus_christi_epistle_fixture import (
    CHANGES,
    FIXTURE,
    expected_corpus_christi_epistle_row,
)

from build_reader import store
from build_reader.layers import enrich_layer, expand_core
from checks import english, interlinear, notes, prose
from checks import translation_provenance as provenance
from checks.language_packs import check_core, check_layer

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.corporis-christi-epistola"
LANGUAGES = ("pl", "en")
ROWS = [pytest.param(row, id=row["after"]["site"]) for row in FIXTURE["provenance_rows"]]
CHANGED = [
    pytest.param(row, id=row["after"]["site"])
    for row in FIXTURE["provenance_rows"]
    if row["target_changed"]
]
NOTES = [
    pytest.param(language, wid, id=f"{language}-{wid}")
    for language in LANGUAGES
    for wid in FIXTURE["layers"][language]["explanations"]
]


SOURCE_SUCCESSOR_SITES = {f"{TEXT}.s05.{language}" for language in LANGUAGES}
SOURCE_BEFORE = "28305bacf7a846221dd4ce5d9bbdb8b0716ac7887ace7521e31b59ccd4ee0337"
SOURCE_AFTER = "9944ff5f1c74f53d2c05495c76ab9c352872a2e11cc2fa19fad84fc134bafe3e"


def expected_source_before(row):
    """Advance only the two exact historical s05 source expectations."""
    result = deepcopy(row["before"])
    if result["site"] in SOURCE_SUCCESSOR_SITES:
        assert result["source_sha256"] == SOURCE_BEFORE, "historical reflexive source preimage"
        assert row["after"]["source_sha256"] == SOURCE_AFTER, "current reflexive source expectation"
        result["source_sha256"] = SOURCE_AFTER
    return result


def assert_source(core):
    original = deepcopy(core)
    assert original["localization"].pop("explanations") == FIXTURE["neutral_explanations"]
    assert provenance.canonical_hash(original) == FIXTURE["core_without_explanations_sha256"], (
        "selected Latin and exact neutral editorial successor"
    )


def assert_groups(layer):
    assert {
        sid: segment.get("alignments", []) for sid, segment in layer["segments"].items()
    } == FIXTURE["layers"][layer["language"]]["groups"], "selected compact groups and referents"


@pytest.fixture(scope="module")
def scanned_sites():
    actual = provenance.corpus_sites(ROOT)
    selected = {key: value for key, value in actual.items() if value["text"] == TEXT}
    assert len(selected) == 12
    return selected


def test_inventory_and_unchanged_latin_with_owned_source_controls():
    core = store.core(ROOT, TEXT)
    snapshot = deepcopy(core)
    assert FIXTURE["text"] == core["id"] == TEXT
    assert [len(s["words"]) for s in core["segments"]] == [41, 21, 13, 16, 14, 15]
    assert sum(len(s["words"]) for s in core["segments"]) == FIXTURE["words"] == 120
    assert len(ROWS) == 12 and len(CHANGED) == 10 and len(NOTES) == 7
    assert_source(core)
    for damage in ("form", "analysis", "lemma", "provider"):
        bad = deepcopy(core)
        if damage == "form":
            bad["segments"][0]["words"][0]["form"] = "Different"
        elif damage == "analysis":
            bad["editorial"]["analysis_defaults"]["review"] = "approved"
        elif damage == "lemma":
            next(w for part in bad["segments"] for w in part["words"] if w["id"] == "w094")[
                "lemma"
            ] = "semetipse"
        else:
            bad["editorial"]["words"]["w094"]["analysis"]["sources"] = ["editorial"]
        assert bad != core
        with pytest.raises(
            AssertionError, match=r"^selected Latin and exact neutral editorial successor"
        ):
            assert_source(bad)
    assert_source(core)
    assert core == snapshot


@pytest.mark.parametrize("language", LANGUAGES)
def test_complete_actual_layers_have_exactly_120_providers_and_valid_help(language):
    core, layer = store.core(ROOT, TEXT), store.raw_layer(ROOT, language, TEXT)
    snapshot = deepcopy((core, layer))
    assert provenance.canonical_hash(layer) == FIXTURE["layers"][language]["canonical_sha256"]
    assert check_core(core) == []
    assert check_layer(core, layer, store.layer_path(ROOT, language, TEXT)) == []
    assert interlinear.check(core, layer) == []
    assert prose.check(layer) == []
    counts = Counter(wid for wid, word in layer["words"].items() if word.get("gloss"))
    groups = [g for segment in layer["segments"].values() for g in segment.get("alignments", [])]
    assert len(groups) == (3 if language == "pl" else 17)
    assert sum(len(g["words"]) for g in groups) == (7 if language == "pl" else 40)
    for group in groups:
        counts.update(group["words"])
        visible = [
            (wid, interlinear.effective_gloss(layer, wid))
            for wid in group["words"]
            if interlinear.effective_gloss(layer, wid)
        ]
        assert visible == [(group["anchor"], group["gloss"])]
    expected = [word["id"] for segment in core["segments"] for word in segment["words"]]
    assert counts == Counter(expected) and len(counts) == 120
    loaded, layers = store.load(ROOT, TEXT)
    assert loaded == expand_core(core)
    assert layers[language] == enrich_layer(core, layer)
    assert notes.check(loaded, layers[language]) == []
    assert english.check(loaded, layers[language]) == []
    assert (core, layer) == snapshot


@pytest.mark.parametrize(
    "section,identifier,field",
    (
        ("segments", "s03", "translation"),
        ("segments", "s04", "translation"),
        ("segments", "s06", "translation"),
        ("words", "w086", "explanation"),
    ),
)
def test_actual_english_checker_rejects_each_ascii_apostrophe_predecessor(
    section, identifier, field
):
    layer = store.raw_layer(ROOT, "en", TEXT)
    snapshot = deepcopy(layer)
    bad = deepcopy(layer)
    value = bad[section][identifier][field]
    assert "Lord’s" in value and "'" not in value
    bad[section][identifier][field] = value.replace("Lord’s", "Lord's")
    assert bad != layer
    assert english.check_apostrophes(bad) == [
        f"{TEXT}:{identifier}.{field}: straight apostrophe — the English layer types ’"
    ]
    assert english.check_apostrophes(layer) == [] and layer == snapshot


@pytest.mark.parametrize("row", ROWS)
def test_all_twelve_prose_sites_keep_exact_admitted_or_retained_wording(row):
    expected = row["after"]
    layer = store.raw_layer(ROOT, expected["language"], TEXT)
    target = layer["segments"][expected["segment"]]["translation"]
    assert target == row["translation_after"]
    assert provenance.canonical_hash(target) == expected["target_sha256"]
    assert (target != row["translation_before"]) is row["target_changed"]
    if not row["target_changed"]:
        assert expected["language"] == "pl" and expected["segment"] in ("s03", "s05")
        assert row["after"] == expected_source_before(row)


@pytest.mark.parametrize("language", LANGUAGES)
def test_exact_groups_and_three_retained_english_constructions(language):
    layer = store.raw_layer(ROOT, language, TEXT)
    assert_groups(layer)
    if language == "en":
        retained = FIXTURE["retained_en_groups"]
        assert sum(len(groups) for groups in retained.values()) == 3
        for sid, groups in retained.items():
            assert all(group in layer["segments"][sid]["alignments"] for group in groups)
        assert layer["words"]["w081"]["gloss"] == "or"
        assert layer["words"]["w088"]["gloss"] == "against the Body"
        assert layer["words"]["w089"]["gloss"] == "and"
        assert layer["words"]["w090"]["gloss"] == "the Blood"
        assert layer["words"]["w091"]["gloss"] == "of the Lord"


@pytest.mark.parametrize("language,wid", NOTES)
def test_each_contextual_explanation_keeps_exact_words_and_quote_punctuation(language, wid):
    layer = store.raw_layer(ROOT, language, TEXT)
    expected = FIXTURE["layers"][language]["explanations"][wid]
    assert layer["words"][wid]["explanation"] == expected
    assert ";" not in expected
    if language == "en" and wid == "w044":
        assert "“took.”" in expected and "“accépit panem.”" in expected
    if language == "en" and wid == "w069":
        assert "“bibétis,”" in expected and "“you drink the chalice.”" in expected


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("damage", ("missing", "duplicate", "gap"))
def test_actual_interlinear_checker_rejects_missing_duplicate_or_noncontiguous_members(
    language, damage
):
    core, layer = store.core(ROOT, TEXT), store.raw_layer(ROOT, language, TEXT)
    snapshot = deepcopy(layer)
    bad = deepcopy(layer)
    group = bad["segments"]["s01"]["alignments"][0]
    if damage == "missing":
        bad["segments"]["s01"]["alignments"].remove(group)
        expected = Counter(
            f"{TEXT}:{wid}:{language}: expected exactly one direct gloss or alignment"
            for wid in group["words"]
        )
        assert Counter(interlinear.check(core, bad)) == expected
    elif damage == "duplicate":
        wid = group["words"][-1]
        bad["words"][wid]["gloss"] = "duplicate"
        assert interlinear.check(core, bad) == [
            f"{TEXT}:{wid}:{language}: expected exactly one direct gloss or alignment"
        ]
    else:
        group["words"][-1] = "w017" if language == "pl" else "w004"
        where = f"{TEXT}:s01:alignment-1:{language}"
        assert f"{where}: aligned words must be contiguous and in source order" in (
            interlinear.check(core, bad)
        )
    assert bad != layer
    assert interlinear.check(core, layer) == [] and layer == snapshot


@pytest.mark.parametrize("language", LANGUAGES)
def test_required_shared_explanation_removal_is_rejected_and_original_restored(language):
    core, layer = store.core(ROOT, TEXT), store.raw_layer(ROOT, language, TEXT)
    bad = deepcopy(layer)
    del bad["words"]["w044"]["explanation"]
    assert check_layer(core, bad, store.layer_path(ROOT, language, TEXT)) == [
        f"{language}:{TEXT}: explanation topology differs — missing=['w044'] extra=[]"
    ]
    assert check_layer(core, layer, store.layer_path(ROOT, language, TEXT)) == []


def test_bibitis_english_only_requirement_does_not_invent_a_polish_note():
    core = store.core(ROOT, TEXT)
    assert core["localization"]["explanations"] == {
        "w044": {},
        "w069": {"languages": ["en"]},
        "w086": {},
        "w112": {},
    }
    for language in LANGUAGES:
        layer = store.raw_layer(ROOT, language, TEXT)
        assert ("explanation" in layer["words"]["w069"]) is (language == "en")
        bad = deepcopy(layer)
        if language == "en":
            del bad["words"]["w069"]["explanation"]
            suffix = "missing=['w069'] extra=[]"
        else:
            bad["words"]["w069"]["explanation"] = "Unrequested note."
            suffix = "missing=[] extra=['w069']"
        assert check_layer(core, bad, store.layer_path(ROOT, language, TEXT)) == [
            f"{language}:{TEXT}: explanation topology differs — {suffix}"
        ]
        assert check_layer(core, layer, store.layer_path(ROOT, language, TEXT)) == []


@pytest.mark.parametrize("damage", ("five-word", "guilt", "genitive", "anchor"))
def test_locally_wrong_or_superseded_readings_fail_owned_group_assertion(damage):
    layer = store.raw_layer(ROOT, "en", TEXT)
    snapshot = deepcopy(layer)
    bad = deepcopy(layer)
    if damage == "five-word":
        groups = bad["segments"]["s02"]["alignments"]
        groups[:2] = [
            {
                "words": [f"w{i:03}" for i in range(48, 53)],
                "anchor": "w048",
                "gloss": "This chalice is the new covenant",
            }
        ]
    else:
        group = bad["segments"]["s04"]["alignments"][1]
        if damage == "guilt":
            group["gloss"] = "the Body and Blood will be guilty"
        elif damage == "genitive":
            group["gloss"] = "will be guilty"
        else:
            group["anchor"] = "w087"
    assert bad != layer
    assert interlinear.check(store.core(ROOT, TEXT), bad) == []
    with pytest.raises(AssertionError, match=r"^selected compact groups and referents"):
        assert_groups(bad)
    assert_groups(layer)
    assert layer == snapshot


@pytest.mark.parametrize("language", LANGUAGES)
def test_actual_prose_checker_rejects_the_punctuation_predecessor(language):
    layer = store.raw_layer(ROOT, language, TEXT)
    bad = deepcopy(layer)
    bad["words"]["w112"]["explanation"] = FIXTURE["punctuation_predecessor"][language]
    assert bad != layer
    errors = prose.check(bad)
    assert len(errors) == 1
    assert errors[0].startswith(f"{TEXT}:w112.explanation.{language}: uses a semicolon")
    assert prose.check(layer) == []


@pytest.mark.parametrize("row", ROWS)
def test_actual_source_target_ledger_stays_unsettled_without_status_promotion(row, scanned_sites):
    expected = row["after"]
    recorded, errors = provenance.load(ROOT)
    assert errors == [] and recorded[expected["site"]] == expected
    actual = scanned_sites[expected["site"]]
    for key in ("text", "segment", "language", "source_sha256", "target_sha256", "familiar_core"):
        assert actual[key] == expected[key]
    assert actual["has_wording_citations"] is False
    assert expected["origin"] == "working-unsettled" and expected["review"] == "working"
    assert expected["familiar_core"] is False
    assert {k: v for k, v in expected.items() if k != "target_sha256"} == {
        k: v for k, v in expected_source_before(row).items() if k != "target_sha256"
    }


@pytest.mark.parametrize("row", CHANGED)
def test_real_provenance_checker_rejects_stale_target_then_accepts_exact_restore(
    row, scanned_sites, monkeypatch
):
    site = row["after"]["site"]
    observed, errors = provenance.load(ROOT)
    assert errors == [] and observed[site] == row["after"]
    current, recorded = {site: deepcopy(scanned_sites[site])}, {site: deepcopy(observed[site])}
    snapshot = deepcopy((current, recorded))
    monkeypatch.setattr(provenance, "corpus_sites", lambda _root: deepcopy(current))
    monkeypatch.setattr(provenance, "load", lambda _root: (deepcopy(recorded), []))
    assert provenance.check(ROOT) == ([], {"working-unsettled": 1})
    recorded[site]["target_sha256"] = row["before"]["target_sha256"]
    assert provenance.check(ROOT) == ([f"{site}: stale target_sha256"], {"working-unsettled": 1})
    recorded = deepcopy(snapshot[1])
    assert provenance.check(ROOT) == ([], {"working-unsettled": 1})
    assert (current, recorded) == snapshot


@pytest.mark.parametrize("site", sorted(CHANGES))
def test_historical_four_row_successor_is_expected_only_exact_and_fail_closed(site):
    change = CHANGES[site]
    before = deepcopy(change["before"])
    keys = ("origin", "review", "target_sha256", "familiar_core")
    historical = {key: before[key] for key in keys}
    expected = {key: change["after"][key] for key in historical}
    assert expected_corpus_christi_epistle_row(historical, site) == expected
    assert expected_corpus_christi_epistle_row(before, site) == change["after"]
    for field, value in (("target_sha256", "0" * 64), ("review", "expert-reviewed")):
        bad = deepcopy(historical)
        bad[field] = value
        with pytest.raises(AssertionError, match=r"^historical Corpus Christi expected row"):
            expected_corpus_christi_epistle_row(bad, site)
    with pytest.raises(AssertionError, match=r"^historical Corpus Christi expected row"):
        expected_corpus_christi_epistle_row(change["after"], site)
    assert change["before"] == before
    assert expected_corpus_christi_epistle_row(historical, site) == expected


def test_historical_overlay_leaves_every_other_site_and_original_fixture_intact():
    path = ROOT / "tests/fixtures/own-relabel-2026-10-20-round-2.json"
    historical = json.loads(path.read_text(encoding="utf-8"))["sites"]
    assert len(historical) == 406
    assert set(CHANGES) == {f"{TEXT}.{sid}.pl" for sid in ("s01", "s02", "s04", "s06")}
    for site, row in historical.items():
        value = deepcopy(row)
        value["familiar_core"] = False
        if site not in CHANGES:
            assert expected_corpus_christi_epistle_row(value, site) == value
        else:
            assert row["target_sha256"] == CHANGES[site]["before"]["target_sha256"]
