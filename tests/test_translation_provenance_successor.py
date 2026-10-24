"""Fixed Introit doxology scope and revised, segment-scoped historical bases."""

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest
from gospel_delivery_fixture import current_sung_expected_row
from pentecost_successor_fixture import expected_pentecost_row
from post_ascension_fixture import expected_row_successor
from provenance_successor_fixture import (
    FIXTURE,
    INTROITS,
    REFLEXIVE,
    assert_formula,
    assert_protection_scope,
    current_expected_reflexive_row,
    metadata_successors,
    restore_preface_prose,
    restore_reflexive_prose,
    restore_reflexive_rows,
)

from build_reader import bibliography, store
from checks import translation_provenance as provenance

ROOT = Path(__file__).resolve().parents[1]
PROJECTIONS = {row["site"]: row for row in FIXTURE["projections"]}
PREFACES = {site: row for site, row in PROJECTIONS.items() if row["formula"] != "JOHN_EXCERPT"}
JOHN = set(PROJECTIONS) - set(PREFACES)


def core_segment(text, segment):
    return next(s for s in store.core(ROOT, text)["segments"] if s["id"] == segment)


def assert_mapping(mapping):
    expected = {row["text"]: frozenset({row["segment"]}) for row in INTROITS.values()}
    assert mapping == expected, "Introit protection inventory"


def assert_projected(expected, actual, use, basis, source, target):
    assert actual == current_sung_expected_row(expected["provenance"]), "projected provenance"
    assert use == expected["use"], "segment source use"
    assert basis == expected["basis"], "revised relationship scope"
    assert actual["origin"] == "public-domain" and actual["review"] == "working"
    assert basis["relationship"] == "revised"
    assert use["address"] == {
        "kind": "segment",
        "text": actual["text"],
        "segment": actual["segment"],
    }
    assert use["role"] == "historical_wording_basis" and use["decision"] == "RETAIN"
    assert target == expected["translation"], "projected target"
    assert provenance.canonical_hash(target) == actual["target_sha256"], "target hash"
    assert (
        provenance.canonical_hash(provenance.source_payload(source)) == actual["source_sha256"]
    ), "Latin hash"
    assert [{"id": w["id"], "form": w["form"]} for w in source["words"]] == expected[
        "latin_words"
    ], "Latin identity"


@pytest.fixture(scope="module")
def baseline():
    graph, packages = bibliography.load(ROOT)
    rows, errors = provenance.load(ROOT)
    assert errors == []
    current = provenance.corpus_sites(ROOT)
    checked = provenance.check(ROOT)
    affected = set(FIXTURE["after_rows"]) | set(INTROITS)
    assert not [
        error for error in checked[0] if any(error.startswith(site + ":") for site in affected)
    ]
    return {
        "graph": graph,
        "packages": packages,
        "rows": rows,
        "current": current,
        "checked": checked,
    }


def test_exact_inventory_and_partition():
    assert FIXTURE["schema_version"] == 1
    assert len(INTROITS) == len(FIXTURE["introits"]) == 91
    assert_mapping(provenance.PROTECTED_PL_INTROIT_SEGMENTS)
    assert len(FIXTURE["after_rows"]) == 173
    assert len(PREFACES) == 43 and len(JOHN) == 3
    assert Counter(row["formula"] for row in PREFACES.values()) == {
        "EN_OPENING_FULL": 18,
        "EN_OPENING_APOSTLES_SHORT": 1,
        "EN_ENDING": 12,
        "PL_ENDING": 12,
    }
    assert {
        "proprium.dominica-iv-post-pascha-communio.s01.en",
        "proprium.dominica-iv-post-pascha-evangelium.s01.en",
        "proprium.dominica-v-post-pascha-evangelium.s01.en",
    } == JOHN
    remaining = set(FIXTURE["remaining_unsettled"])
    assert len(remaining) == 38 and remaining.isdisjoint(PREFACES)
    assert len(remaining | set(PREFACES)) == 81
    assert (
        sum(
            not FIXTURE["before_rows"][site]["familiar_core"]
            for site in set(INTROITS) & set(FIXTURE["before_rows"])
        )
        == 89
    )
    for site in remaining:
        row = FIXTURE["after_rows"][site]
        assert (row["origin"], row["review"]) == ("working-unsettled", "working")
    assert len(FIXTURE["prose_successors"]) == 12


def test_full_latin_introit_population_is_bound_to_the_inventory():
    found = {}
    forms = FIXTURE["latin_gloria"]
    assert len(forms) == 20
    for path in sorted((ROOT / "texts").glob("*/*introitus.json")):
        text = path.parent.name + "." + path.stem
        for segment in store.core(ROOT, text)["segments"]:
            words = segment.get("words", [])
            for start in range(len(words) - len(forms) + 1):
                if [w["form"] for w in words[start : start + len(forms)]] == forms:
                    site = f"{text}.{segment['id']}.pl"
                    assert site not in found
                    found[site] = [w["id"] for w in words[start : start + len(forms)]]
    assert found == {site: row["latin_words"] for site, row in INTROITS.items()}


@pytest.mark.parametrize("site", sorted(INTROITS))
def test_each_fixed_introit_formula_and_flag(site, baseline):
    row = INTROITS[site]
    segment = core_segment(row["text"], row["segment"])
    words = {word["id"]: word for word in segment["words"]}
    assert [words[wid]["form"] for wid in row["latin_words"]] == FIXTURE["latin_gloria"]
    target = store.raw_layer(ROOT, "pl", row["text"])["segments"][row["segment"]]["translation"]
    assert_protection_scope(row["text"], "pl", row["segment"], target)
    assert baseline["rows"][site]["familiar_core"] is True
    assert baseline["current"][site]["familiar_core"] is True
    assert provenance.canonical_hash(target) == baseline["rows"][site]["target_sha256"]
    standalone = store.raw_layer(ROOT, "pl", "orationes.gloria-patri")
    assert FIXTURE["protected_polish"] == " ".join(
        standalone["segments"][sid]["translation"] for sid in ("s01", "s02")
    )


@pytest.mark.parametrize("site", sorted(INTROITS))
@pytest.mark.parametrize("damage", ["dative", "gender", "amen", "missing", "duplicate"])
def test_formula_mutation_does_not_remove_protection_and_is_rejected(site, damage):
    row = INTROITS[site]
    target = store.raw_layer(ROOT, "pl", row["text"])["segments"][row["segment"]]["translation"]
    formula = FIXTURE["protected_polish"]
    changed = {
        "dative": formula.replace("Ojcu", "Ojcowi", 1),
        "gender": formula.replace("Jak była", "Jak był", 1),
        "amen": formula.removesuffix("Amen."),
        "missing": "",
        "duplicate": formula + " " + formula,
    }[damage]
    candidate = target.replace(formula, changed, 1)
    assert candidate != target
    assert provenance.protected(row["text"], "pl", row["segment"]) is True
    with pytest.raises(AssertionError, match="protected Gloria Patri"):
        assert_formula(candidate)


@pytest.mark.parametrize("site", sorted(INTROITS))
def test_surrounding_wording_can_change_without_changing_the_formula(site):
    row = INTROITS[site]
    target = store.raw_layer(ROOT, "pl", row["text"])["segments"][row["segment"]]["translation"]
    candidate = "Próba przed. " + target + " Próba po."
    assert candidate != target
    assert_formula(candidate)
    assert_protection_scope(row["text"], "pl", row["segment"], candidate)
    # This is not whole-text or language-independent protection. Two older
    # Annunciation entries separately retain their pre-existing whole-text rule.
    if row["text"] not in provenance.PROTECTED_PL_TEXTS:
        assert provenance.protected(row["text"], "pl") is False
        assert provenance.protected(row["text"], "pl", "s99") is False
    if row["text"] not in provenance.PROTECTED_EN_TEXTS:
        assert provenance.protected(row["text"], "en", row["segment"]) is False
    assert provenance.protected(row["text"], "la", row["segment"]) is False


@pytest.mark.parametrize("site", sorted(INTROITS))
@pytest.mark.parametrize("damage", ["remove", "segment", "extra"])
def test_static_inventory_damage_is_rejected(site, damage):
    mapping = deepcopy(provenance.PROTECTED_PL_INTROIT_SEGMENTS)
    text = INTROITS[site]["text"]
    if damage == "remove":
        del mapping[text]
    elif damage == "segment":
        mapping[text] = frozenset({"s99"})
    else:
        mapping[text] |= {"s99"}
    with pytest.raises(AssertionError, match="Introit protection inventory"):
        assert_mapping(mapping)


@pytest.mark.parametrize("site", sorted(INTROITS))
def test_the_provenance_validator_rejects_a_cleared_flag(site, baseline, monkeypatch):
    rows = deepcopy(baseline["rows"])
    rows[site]["familiar_core"] = False
    # Current sites were computed by the real scanner once for this immutable
    # corpus. Only the ledger is changed; isolate the validator's flag comparison.
    monkeypatch.setattr(provenance, "corpus_sites", lambda _root: deepcopy(baseline["current"]))
    monkeypatch.setattr(provenance, "load", lambda _root: (deepcopy(rows), []))
    errors, tally = provenance.check(ROOT)
    assert set(errors) == set(baseline["checked"][0]) | {
        f"{site}: stale or incorrect familiar_core"
    }
    assert tally == baseline["checked"][1]


def test_all_173_successor_rows_match_exactly(baseline):
    for site, row in FIXTURE["after_rows"].items():
        assert baseline["rows"][site] == expected_pentecost_row(
            current_sung_expected_row(expected_row_successor(current_expected_reflexive_row(row)))
        )
    fixture_before = deepcopy(FIXTURE)
    before = deepcopy(list(FIXTURE["before_rows"].values()))
    assert {row["site"]: row for row in metadata_successors(before)} == FIXTURE["after_rows"]
    assert before == list(fixture_before["before_rows"].values()), (
        "successor input must stay unchanged"
    )
    assert before[0]["review"] != "expert-reviewed"
    before[0]["review"] = "expert-reviewed"
    with pytest.raises(AssertionError):
        metadata_successors(before)
    assert fixture_before == FIXTURE


@pytest.mark.parametrize("site", sorted(PROJECTIONS))
def test_each_projection_binds_exact_use_basis_latin_target_and_working_state(site, baseline):
    expected = PROJECTIONS[site]
    row = baseline["rows"][site]
    language, text, segment = row["language"], row["text"], row["segment"]
    uses = [
        use for use in baseline["packages"][language]["uses"] if use["id"] == expected["use"]["id"]
    ]
    assert len(uses) == 1
    basis_doc = json.loads(
        (ROOT / f"languages/{language}/translation-basis.json").read_text(encoding="utf-8")
    )
    basis = [
        record
        for record in basis_doc["records"]
        if text in record["texts"]
        and (record.get("segments") is None or segment in record["segments"])
    ]
    assert len(basis) == 1
    assert_projected(
        expected,
        row,
        uses[0],
        basis[0],
        core_segment(text, segment),
        store.raw_layer(ROOT, language, text)["segments"][segment]["translation"],
    )
    assert store.translation_relationships(ROOT, language)[site] == "revised"
    assert baseline["current"][site]["has_wording_citations"] is True
    assert baseline["current"][site]["source_sha256"] == row["source_sha256"]
    assert baseline["current"][site]["target_sha256"] == row["target_sha256"]


def test_projection_source_population_has_no_missing_or_extra_successor_uses(baseline):
    suffixes = (".family1839-revised", ".pamiatka1903-revised", ".douay1914-revised")
    actual = {
        use["id"]
        for package in baseline["packages"].values()
        for use in package["uses"]
        if use["id"].endswith(suffixes)
    }
    assert actual == {row["use"]["id"] for row in PROJECTIONS.values()}


@pytest.mark.parametrize("site", sorted(PROJECTIONS))
@pytest.mark.parametrize(
    "damage",
    [
        "origin",
        "review",
        "source-hash",
        "target-hash",
        "role",
        "decision",
        "edition",
        "item",
        "locator",
        "evidence",
        "claim",
        "whole-text",
        "wrong-segment",
        "relation",
        "coverage",
        "target",
        "Latin",
    ],
)
def test_every_projection_rejects_label_source_scope_and_hash_mutations(site, damage):
    expected = PROJECTIONS[site]
    row, use, basis = (
        current_sung_expected_row(expected["provenance"]),
        deepcopy(expected["use"]),
        deepcopy(expected["basis"]),
    )
    source = deepcopy(core_segment(row["text"], row["segment"]))
    target = expected["translation"]
    assert_projected(expected, row, use, basis, source, target)
    if damage == "origin":
        row["origin"] = "own"
    elif damage == "review":
        row["review"] = "internally-reviewed"
    elif damage == "source-hash":
        row["source_sha256"] = "0" * 64
    elif damage == "target-hash":
        row["target_sha256"] = "0" * 64
    elif damage == "role":
        use["role"] = "historical_wording_comparator"
    elif damage == "decision":
        use["decision"] = "REMOVE"
    elif damage == "edition":
        use["edition"] += "-other"
    elif damage == "item":
        use["digital_item"] += "-other"
    elif damage == "locator":
        use["locator"]["scan"] = "PDF p. 1"
    elif damage == "evidence":
        use["evidence_sha256"] = "0" * 64
    elif damage == "claim":
        use["claim"] = "The source supplies the complete Preface."
    elif damage == "whole-text":
        use["address"] = {"kind": "text", "text": row["text"]}
    elif damage == "wrong-segment":
        use["address"]["segment"] = "s99"
    elif damage == "relation":
        basis["relationship"] = "equal"
    elif damage == "coverage":
        basis.pop("segments")
    elif damage == "target":
        target += " Changed."
    else:
        source["words"][0]["form"] += "x"
    with pytest.raises(AssertionError):
        assert_projected(expected, row, use, basis, source, target)


@pytest.mark.parametrize(
    "site",
    [
        "ordinarium.praefatio-communis.s02.en",
        "ordinarium.praefatio-communis.s06.pl",
        "proprium.dominica-iv-post-pascha-evangelium.s01.en",
    ],
)
def test_real_scanner_does_not_treat_a_comparator_as_a_wording_basis(site, baseline, monkeypatch):
    graph, packages = deepcopy((baseline["graph"], baseline["packages"]))
    language = PROJECTIONS[site]["provenance"]["language"]
    use = next(
        use for use in packages[language]["uses"] if use["id"] == PROJECTIONS[site]["use"]["id"]
    )
    use["role"] = "historical_wording_comparator"
    monkeypatch.setattr(bibliography, "load", lambda _root: (graph, packages))
    current = provenance.corpus_sites(ROOT)
    assert current[site]["has_wording_citations"] is False
    errors, tally = provenance.check(ROOT)
    assert set(errors) == set(baseline["checked"][0]) | {
        f"{site}: origin=public-domain requires a wording citation"
    }
    assert tally == baseline["checked"][1]


@pytest.mark.parametrize("site", sorted(PREFACES))
def test_shared_latin_identity_is_exact_not_prefix_inference(site):
    expected = PREFACES[site]
    common = next(
        row
        for row in PREFACES.values()
        if row["provenance"]["text"] == "ordinarium.praefatio-communis"
        and row["formula"]
        == (
            "EN_OPENING_FULL"
            if expected["formula"] == "EN_OPENING_APOSTLES_SHORT"
            else expected["formula"]
        )
    )
    forms = [word["form"] for word in expected["latin_words"]]
    common_forms = [word["form"] for word in common["latin_words"]]
    assert forms == (
        common_forms[:8] if expected["formula"] == "EN_OPENING_APOSTLES_SHORT" else common_forms
    )
    if expected["formula"] == "EN_OPENING_APOSTLES_SHORT":
        assert "give You thanks" not in expected["translation"]
    else:
        assert expected["translation"] == common["translation"]


@pytest.mark.parametrize("site", sorted(FIXTURE["prose_successors"]))
def test_twelve_english_endings_and_historical_digest_inverse_are_exact(site):
    text, segment, language = site.rsplit(".", 2)
    assert language == "en"
    wording = FIXTURE["prose_successors"][site]
    assert (
        wording["after"]
        == "We beseech You to grant that our voices too may join theirs, as we humbly proclaim:"
    )
    assert wording["before"] != wording["after"]
    layer = store.raw_layer(ROOT, language, text)
    assert layer["segments"][segment]["translation"] == wording["after"]
    slug = text.removeprefix("ordinarium.praefatio-")
    restored = restore_preface_prose(layer, slug)
    expected = deepcopy(layer)
    expected["segments"][segment]["translation"] = wording["before"]
    assert restored == expected
    damaged = deepcopy(layer)
    damaged["segments"][segment]["translation"] += " Changed."
    with pytest.raises(AssertionError, match="preface ending successor"):
        restore_preface_prose(damaged, slug)
    outside = deepcopy(layer)
    other = next(
        sid for sid, value in layer["segments"].items() if sid != segment and "translation" in value
    )
    outside["segments"][other]["translation"] += " Changed."
    restored_outside = restore_preface_prose(outside, slug)
    assert restored_outside != restored
    assert restored_outside["segments"][other] == outside["segments"][other]


def test_trinity_ending_and_embedded_full_prefaces_are_outside_the_shared_route():
    assert "ordinarium.praefatio-sanctissimae-trinitatis.s02.en" in PREFACES
    assert "ordinarium.praefatio-sanctissimae-trinitatis.s07.en" not in PREFACES
    assert not any(
        "praefatio-de-spiritu-sancto" in site or "praefatio-ascensionis" in site
        for site in PREFACES
    )


def test_reflexive_current_expectation_and_inverse_preserve_the_173_historical_rows():
    site = "proprium.dominica-resurrectionis-introitus.s01.pl"
    assert set(REFLEXIVE["rows"]) == set(REFLEXIVE["prose"]) == {site}
    historical = deepcopy(list(FIXTURE["after_rows"].values()))
    current = [current_expected_reflexive_row(row) for row in historical]
    assert len(historical) == len(current) == 173
    assert [row["site"] for row in current] == [row["site"] for row in historical]
    assert [a["site"] for a, b in zip(current, historical, strict=True) if a != b] == [site]
    assert restore_reflexive_rows(current) == historical
    assert historical == list(FIXTURE["after_rows"].values())
    change = REFLEXIVE["rows"][site]
    assert change["before"] == FIXTURE["after_rows"][site]
    assert change["before"]["target_sha256"] != change["after"]["target_sha256"]
    assert {k: v for k, v in change["before"].items() if k != "target_sha256"} == {
        k: v for k, v in change["after"].items() if k != "target_sha256"
    }
    assert change["after"]["origin"] == "working-unsettled"
    assert change["after"]["review"] == "working"
    assert change["after"]["familiar_core"] is True
    with pytest.raises(AssertionError, match="historical reflexive expected row"):
        current_expected_reflexive_row(change["after"])


@pytest.mark.parametrize("field", ["source_sha256", "target_sha256", "review", "origin"])
def test_reflexive_row_inverse_refuses_a_damaged_current_preimage(field):
    change = next(iter(REFLEXIVE["rows"].values()))
    wrong = deepcopy(change["after"])
    wrong[field] += "-changed"
    with pytest.raises(AssertionError, match="current reflexive row inverse"):
        restore_reflexive_rows([wrong])
    historical = deepcopy(change["before"])
    historical[field] += "-changed"
    with pytest.raises(AssertionError, match="historical reflexive expected row"):
        current_expected_reflexive_row(historical)


def test_reflexive_prose_inverse_preserves_the_formula_and_unrelated_fields():
    site = next(iter(REFLEXIVE["prose"]))
    text, segment, language = site.rsplit(".", 2)
    current = store.raw_layer(ROOT, language, text)
    snapshot = deepcopy(current)
    wording, rows = REFLEXIVE["prose"][site], REFLEXIVE["rows"][site]
    assert current["segments"][segment]["translation"] == wording["after"]
    restored = restore_reflexive_prose(current, text)
    expected = deepcopy(current)
    expected["segments"][segment]["translation"] = wording["before"]
    assert restored == expected
    assert current == snapshot
    for state in ("before", "after"):
        assert_formula(wording[state])
        assert provenance.canonical_hash(wording[state]) == rows[state]["target_sha256"]
    outside = deepcopy(current)
    outside["about"] += " Additional context."
    assert restore_reflexive_prose(outside, text)["about"] == outside["about"]
    assert restore_reflexive_prose(current, "proprium.other-text") == current
    unrelated_site = next(s for s in INTROITS if s in FIXTURE["after_rows"] and s != site)
    unrelated = deepcopy(FIXTURE["after_rows"][unrelated_site])
    assert current_expected_reflexive_row(unrelated) == unrelated
    assert restore_reflexive_rows([unrelated]) == [unrelated]


@pytest.mark.parametrize("damage", ["old-case", "unrelated-wording"])
def test_reflexive_prose_inverse_refuses_wrong_case_and_unrelated_changes(damage):
    site = next(iter(REFLEXIVE["prose"]))
    text, segment, language = site.rsplit(".", 2)
    current = store.raw_layer(ROOT, language, text)
    wording = REFLEXIVE["prose"][site]
    current["segments"][segment]["translation"] = (
        wording["before"] if damage == "old-case" else wording["after"] + " Changed."
    )
    with pytest.raises(AssertionError, match="current reflexive prose inverse"):
        restore_reflexive_prose(current, text)
