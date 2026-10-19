"""Revised historical bases retain exact source scope and inherited provenance."""

import copy
import json
from pathlib import Path

import pytest

from build_reader import bibliography, store
from checks import translation_provenance

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = json.loads((ROOT / "tests/fixtures/revised-wording-bases.json").read_text())
REPAIRS = PAYLOAD["records"]
EXPECTED_IDS = {
    "use.en.ab7ebc9c8480b9df2abe",
    "use.en.c851cc4624ad0c9b8e90",
    "use.en.187222f69552357689e2",
    "use.en.c1bf1b3d4d5d50fac3c2",
    "use.en.0cfda2b4bcac3b4851cb",
    "use.en.fccee24c364e44f09cac",
    "use.pl.a9e8eb327d2b26261368",
    "use.pl.889d0b8c94319f3489ce",
    "use.pl.01b2450083e337848657",
    "use.pl.5f5e1d491387644bdcd2",
    "use.pl.3c4887b171db3d7431ff",
}
AVE_IDS = {"use.pl.a9e8eb327d2b26261368", "use.pl.889d0b8c94319f3489ce"}


def assert_source_record(actual, record):
    assert actual == record["use"]
    assert actual["role"] == "historical_wording_basis"
    assert actual["decision"] == "RETAIN_WITH_CORRECTION"
    assert actual["address"]["kind"] == "segment"


@pytest.fixture(scope="module")
def baseline():
    graphs = bibliography.load(ROOT)
    assert bibliography.validate(ROOT, *graphs) == []
    recorded, errors = translation_provenance.load(ROOT)
    assert errors == []
    return {
        "graphs": graphs,
        "sites": translation_provenance.corpus_sites(ROOT),
        "recorded": recorded,
        "check": translation_provenance.check(ROOT),
    }


def test_revised_source_fixture_is_nonempty_and_covers_every_intended_site():
    assert PAYLOAD["schema_version"] == 1
    assert len(REPAIRS) == 11
    assert {record["use"]["id"] for record in REPAIRS} == EXPECTED_IDS
    assert len({record["site"] for record in REPAIRS}) == 11
    assert sum(record["language"] == "en" for record in REPAIRS) == 6
    assert sum(record["language"] == "pl" for record in REPAIRS) == 5


@pytest.mark.parametrize("record", REPAIRS, ids=lambda record: record["site"])
def test_revised_source_has_exact_identity_scope_claim_and_unchanged_target(record, baseline):
    language, site = record["language"], record["site"]
    graph, packages = baseline["graphs"]
    matches = [use for use in packages[language]["uses"] if use["id"] == record["use"]["id"]]
    assert len(matches) == 1
    use = matches[0]
    assert_source_record(use, record)
    assert baseline["recorded"][site] == record["provenance"]
    assert record["provenance"]["origin"] == "public-domain"
    assert record["provenance"]["familiar_core"] is False
    assert record["relationship"] == "revised"
    assert store.translation_relationships(ROOT, language)[site] == record["relationship"]
    current = baseline["sites"][site]
    assert current["has_wording_citations"] is True
    for field in ("source_sha256", "target_sha256"):
        assert current[field] == record["provenance"][field]
    assert not any(error.startswith(site + ":") for error in baseline["check"][0])

    address = use["address"]
    doc, layers = store.load(ROOT, address["text"])
    segment = next(segment for segment in doc["segments"] if segment["id"] == address["segment"])
    localized = layers[language]["segments"][address["segment"]]
    assert (
        translation_provenance.canonical_hash(localized["translation"])
        == (record["provenance"]["target_sha256"])
    )
    source = translation_provenance.source_payload(segment)
    assert translation_provenance.canonical_hash(source) == record["provenance"]["source_sha256"]
    decisions = bibliography.LegacyCitationDecisions(graph, packages)
    assert not decisions.has_unmapped_citation(
        f"languages/{language}/texts/{address['text'].replace('.', '/', 1)}.json",
        ("segments", address["segment"], "translation_citations"),
        localized["translation_citations"],
    )
    bases = [
        candidate["id"]
        for candidate in packages[language]["uses"]
        if candidate.get("role") == "historical_wording_basis"
        and candidate.get("decision") in {"RETAIN", "RETAIN_WITH_CORRECTION"}
        and candidate["address"].get("text") == address["text"]
        and (
            candidate["address"]["kind"] == "text"
            or (
                candidate["address"]["kind"] == "segment"
                and candidate["address"]["segment"] == address["segment"]
            )
        )
    ]
    assert bases == [use["id"]]


@pytest.mark.parametrize("record", REPAIRS, ids=lambda record: record["site"])
@pytest.mark.parametrize(
    "damage",
    [
        "COMPARATOR",
        "REMOVE",
        "REPLACE",
        "UNVERIFIED_NO_DIRECT_EVIDENCE",
        "text",
        "segment",
        "language",
    ],
)
def test_real_revised_basis_rejection_and_exact_restoration(record, damage, baseline, monkeypatch):
    original = baseline["graphs"]
    graph, packages = copy.deepcopy(original)
    language, site = record["language"], record["site"]
    use = next(use for use in packages[language]["uses"] if use["id"] == record["use"]["id"])
    assert_source_record(use, record)
    if damage == "COMPARATOR":
        use["role"] = "historical_wording_comparator"
    elif damage in {"REMOVE", "REPLACE", "UNVERIFIED_NO_DIRECT_EVIDENCE"}:
        use["decision"] = damage
        use["decision_reason"] = "This source use is withheld."
    elif damage == "text":
        use["address"] = {"kind": "segment", "text": "orationes.ave-maria", "segment": "s01"}
    elif damage == "segment":
        use["address"]["segment"] = record["wrong_segment"]
        assert record["wrong_segment"] != record["use"]["address"]["segment"]
    else:
        packages[language]["uses"].remove(use)
        other = "pl" if language == "en" else "en"
        packages[other]["uses"].append(use)
        packages[other]["uses"].sort(key=lambda candidate: candidate["id"])
    # Keep every immutable pointer mapped: deleting a use would instead test
    # the separately supported genuinely-unmapped compatibility contract.
    assert use["legacy_refs"] == record["use"]["legacy_refs"]
    loader = bibliography.load
    monkeypatch.setattr(bibliography, "load", lambda _root: (graph, packages))
    assert translation_provenance.corpus_sites(ROOT)[site]["has_wording_citations"] is False
    errors, tally = translation_provenance.check(ROOT)
    diagnostic = f"{site}: origin=public-domain requires a wording citation"
    assert diagnostic not in baseline["check"][0]
    assert set(errors) == set(baseline["check"][0]) | {diagnostic}
    assert tally == baseline["check"][1]

    monkeypatch.setattr(bibliography, "load", loader)
    assert bibliography.load(ROOT) == original
    assert translation_provenance.corpus_sites(ROOT) == baseline["sites"]
    assert translation_provenance.check(ROOT) == baseline["check"]
    assert translation_provenance.load(ROOT) == (baseline["recorded"], [])


@pytest.mark.parametrize(
    "record",
    [record for record in REPAIRS if record["use"]["id"] in AVE_IDS],
    ids=lambda record: record["site"],
)
@pytest.mark.parametrize("damage", ["old-pages", "old-publication"])
def test_ave_revised_basis_rejects_old_page_and_publication_identity(record, damage):
    original = copy.deepcopy(record["use"])
    mutant = copy.deepcopy(original)
    assert_source_record(original, record)
    if damage == "old-pages":
        mutant["locator"]["printed"] = "druk. s. 130"
        mutant["locator"]["scan"] = "PDF s. 144"
    else:
        mutant["locator"]["page_url"] = mutant["locator"]["page_url"].replace("13965", "13065")
    with pytest.raises(AssertionError):
        assert_source_record(mutant, record)
    mutant.clear()
    mutant.update(original)
    assert_source_record(mutant, record)
