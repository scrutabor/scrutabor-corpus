"""Mixed wording has bounded received sources, never a whole inherited basis."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from test_translation_provenance import initialize_all, set_basis, set_origin, write_text

from build_reader import bibliography, store
from checks import translation_basis
from checks import translation_provenance as provenance

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT / "tests/fixtures/mixed-translation-origins.json").read_text())
RECORDS = FIXTURE["records"]
MIXED = [row for row in RECORDS if row["after"]["origin"] == "mixed"]
BOUNDED_USES = [*FIXTURE["new_uses"], FIXTURE["corrected_use"]["after"]]


def covers(use, row):
    address = use.get("address") or {}
    return (
        use.get("role") == "historical_wording_basis"
        and use.get("decision") in {"RETAIN", "RETAIN_WITH_CORRECTION"}
        and address.get("text") == row["text"]
        and (
            address.get("kind") == "text"
            or (address.get("kind") == "segment" and address.get("segment") == row["segment"])
        )
    )


@pytest.fixture(scope="module")
def baseline():
    graphs = bibliography.load(ROOT)
    assert bibliography.validate(ROOT, *graphs) == []
    rows, errors = provenance.load(ROOT)
    assert errors == []
    assert provenance.check(ROOT)[0] == []
    assert translation_basis.check(ROOT)[0] == []
    docs = store.all_texts(ROOT)
    return {"graphs": graphs, "rows": rows, "docs": docs}


def test_exact_seven_site_population_and_bounded_source_account():
    assert len(RECORDS) == 7 and len({row["site"] for row in RECORDS}) == 7
    assert len(MIXED) == 4
    assert sum(row["positions"] for row in RECORDS) == 510
    assert len(FIXTURE["new_uses"]) == 5
    assert len({use["id"] for use in FIXTURE["new_uses"]}) == 5
    assert all(use["role"] == "historical_wording_basis" for use in FIXTURE["new_uses"])
    assert all(use["address"]["kind"] == "segment" for use in FIXTURE["new_uses"])
    assert all(
        use["claim"] and use["locator"]["printed"] and use["locator"]["scan"]
        for use in FIXTURE["new_uses"]
    )


def test_lateran_reuse_keeps_its_distinct_source_and_working_state(baseline):
    expected = FIXTURE["eighth"]
    row = baseline["rows"][expected["provenance_after"]["site"]]
    assert row == expected["provenance_after"]
    assert row["origin"] == "own" and row["review"] == "working"
    assert row["source_sha256"] == expected["provenance_before"]["source_sha256"]
    lent = next(
        record
        for record in RECORDS
        if record["text"].endswith("dominica-iv-in-quadragesima-tractus")
    )
    assert row["source_sha256"] != lent["after"]["source_sha256"]
    assert row["target_sha256"] == lent["after"]["target_sha256"]
    core, layers = store.load(ROOT, expected["text"])
    assert store.raw_layer(ROOT, "en", expected["text"]) == expected["after"]
    assert layers["en"]["segments"]["s01"]["translation"] == lent["translation"]
    segment = next(s for s in core["segments"] if s["id"] == "s01")
    assert len(segment["words"]) == 32
    assert provenance.canonical_hash(provenance.source_payload(segment)) == row["source_sha256"]
    assert expected["text"] + ".s01.en" not in store.translation_relationships(ROOT, "en")


@pytest.mark.parametrize("expected", BOUNDED_USES, ids=lambda use: use["id"])
def test_each_received_source_keeps_its_exact_visible_scope(expected, baseline):
    matches = [use for use in baseline["graphs"][1]["en"]["uses"] if use["id"] == expected["id"]]
    assert matches == [expected]
    assert "only" in expected["locator"]["section"]
    assert expected["locator"]["section"] and expected["claim"]
    assert expected["verified_on"] == "2026-10-26"


@pytest.mark.parametrize("record", RECORDS, ids=lambda row: row["site"])
def test_adopted_target_has_exact_origin_source_and_working_state(record, baseline):
    row = baseline["rows"][record["site"]]
    assert row == record["after"]
    assert row["review"] == "working"
    for field in ("text", "segment", "language", "familiar_core", "review", "source_sha256"):
        assert row[field] == record["before"][field]
    core, layers = store.load(ROOT, row["text"])
    segment = next(s for s in core["segments"] if s["id"] == row["segment"])
    target = layers["en"]["segments"][row["segment"]]["translation"]
    assert target == record["translation"]
    assert provenance.canonical_hash(target) == row["target_sha256"]
    assert provenance.canonical_hash(provenance.source_payload(segment)) == row["source_sha256"]
    assert len(segment["words"]) == record["positions"]
    if row["origin"] == "mixed":
        assert record["site"] not in store.translation_relationships(ROOT, "en")
        uses = [use for use in baseline["graphs"][1]["en"]["uses"] if covers(use, row)]
        assert sorted(use["id"] for use in uses) == record["basis_use_ids"]
        assert uses
    else:
        assert row["origin"] == "own"
        assert not provenance.corpus_sites(ROOT)[record["site"]]["has_wording_citations"]


@pytest.mark.parametrize("record", MIXED, ids=lambda row: row["site"])
@pytest.mark.parametrize(
    "damage", ["missing", "comparator", "removed", "segment", "word", "language"]
)
def test_every_real_mixed_basis_route_rejects_damage_and_same_copy_recovers(
    record, damage, baseline, monkeypatch
):
    graph, packages = deepcopy(baseline["graphs"])
    original = deepcopy(packages)
    row = record["after"]
    matches = [use for use in packages["en"]["uses"] if covers(use, row)]
    assert matches and sorted(use["id"] for use in matches) == record["basis_use_ids"]
    monkeypatch.setattr(store, "all_texts", lambda _root: baseline["docs"])
    monkeypatch.setattr(bibliography, "load", lambda _root: (graph, packages))
    assert provenance.check(ROOT)[0] == []
    for use in matches:
        if damage == "missing":
            packages["en"]["uses"].remove(use)
        elif damage == "comparator":
            use["role"] = "historical_wording_comparator"
        elif damage == "removed":
            use["decision"] = "REMOVE"
        elif damage == "segment":
            use["address"]["segment"] = "s99"
        elif damage == "word":
            use["address"] = {"kind": "word", "text": row["text"], "word": "w001"}
        else:
            packages["en"]["uses"].remove(use)
            packages["pl"]["uses"].append(use)
    assert packages != original
    diagnostic = f"{row['site']}: origin=mixed requires a retained historical_wording_basis use"
    assert diagnostic in provenance.check(ROOT)[0]
    packages.clear()
    packages.update(deepcopy(original))
    assert packages == original
    assert provenance.check(ROOT)[0] == []


@pytest.mark.parametrize("record", MIXED, ids=lambda row: row["site"])
@pytest.mark.parametrize("origin", ["own", "trivial"])
def test_received_contributors_cannot_be_hidden_by_an_own_label(
    record, origin, baseline, monkeypatch
):
    rows = deepcopy(baseline["rows"])
    row = rows[record["site"]]
    saved = deepcopy(row)
    monkeypatch.setattr(store, "all_texts", lambda _root: baseline["docs"])
    monkeypatch.setattr(provenance, "load", lambda _root: (rows, []))
    assert provenance.check(ROOT)[0] == []
    row["origin"] = origin
    assert row != saved
    diagnostic = f"{row['site']}: origin={origin} cannot carry a wording citation"
    assert diagnostic in provenance.check(ROOT)[0]
    row.clear()
    row.update(saved)
    assert row == saved
    assert provenance.check(ROOT)[0] == []


def synthetic(root, origin="mixed", version="1.1.0", legacy=False):
    write_text(root, cited_pl=legacy)
    initialize_all(root)
    language = "pl" if legacy else "en"
    set_origin(root, origin, language)
    path = root / f"languages/{language}/translation-provenance.json"
    ledger = json.loads(path.read_text())
    ledger["schema_version"] = version
    path.write_text(json.dumps(ledger))
    for lang in ("pl", "en"):
        (root / f"languages/{lang}/translation-basis.json").write_text(
            json.dumps({"schema_version": "1.0.0", "language": lang, "records": []})
        )
    return language, path, ledger


@pytest.mark.parametrize(
    "relationship", ["exact", "normalized", "revised", "traditional-composite"]
)
def test_mixed_is_not_a_whole_inherited_basis_and_removed_extra_recovers(tmp_path, relationship):
    language, _, _ = synthetic(tmp_path)
    set_basis(
        tmp_path,
        {"kind": "segment", "text": "orationes.test", "segment": "s01"},
        language=language,
    )
    assert provenance.check(tmp_path)[0] == []
    assert translation_basis.check(tmp_path)[0] == []
    path = tmp_path / f"languages/{language}/translation-basis.json"
    saved = path.read_bytes()
    doc = json.loads(saved)
    doc["records"] = [
        {"texts": ["orationes.test"], "segments": ["s01"], "relationship": relationship}
    ]
    path.write_text(json.dumps(doc))
    assert path.read_bytes() != saved
    assert any(
        "1 non-inherited site(s) classified" in error
        for error in translation_basis.check(tmp_path)[0]
    )
    path.write_bytes(saved)
    assert path.read_bytes() == saved
    assert translation_basis.check(tmp_path)[0] == []


@pytest.mark.parametrize("version", ["1.0.0", "1.1.0"])
@pytest.mark.parametrize(
    "origin", ["working-unsettled", "own", "public-domain", "traditional", "trivial"]
)
def test_existing_origin_contracts_remain_supported(tmp_path, version, origin):
    language, _, _ = synthetic(tmp_path, origin, version)
    if origin in {"public-domain", "traditional"}:
        set_basis(tmp_path, {"kind": "text", "text": "orationes.test"}, language=language)
    assert provenance.check(tmp_path)[0] == []


@pytest.mark.parametrize("version", ["1.0.0", "1.2.0"])
def test_mixed_requires_the_explicit_supported_version_and_real_record_recovers(tmp_path, version):
    language, path, ledger = synthetic(tmp_path)
    set_basis(tmp_path, {"kind": "text", "text": "orationes.test"}, language=language)
    saved = path.read_bytes()
    assert provenance.check(tmp_path)[0] == []
    ledger["schema_version"] = version
    path.write_text(json.dumps(ledger))
    assert path.read_bytes() != saved
    assert provenance.check(tmp_path)[0]
    path.write_bytes(saved)
    assert provenance.check(tmp_path)[0] == []


def test_legacy_only_cannot_substitute_for_the_mixed_normalized_basis(tmp_path):
    language, _, _ = synthetic(tmp_path, legacy=True)
    address = {"kind": "text", "text": "orationes.test"}
    set_basis(tmp_path, address, language=language)
    assert provenance.check(tmp_path)[0] == []
    path = tmp_path / f"languages/{language}/bibliography.json"
    saved = path.read_bytes()
    doc = json.loads(saved)
    doc["uses"] = []
    path.write_text(json.dumps(doc))
    assert path.read_bytes() != saved
    site = "orationes.test.s01.pl"
    assert provenance.corpus_sites(tmp_path)[site]["has_wording_citations"] is True
    diagnostic = f"{site}: origin=mixed requires a retained historical_wording_basis use"
    assert diagnostic in provenance.check(tmp_path)[0]
    path.write_bytes(saved)
    assert provenance.check(tmp_path)[0] == []
