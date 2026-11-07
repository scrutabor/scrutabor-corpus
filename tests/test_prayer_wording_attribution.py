"""Printed wording support must remain distinct from a related historical text."""

import copy
import json
from pathlib import Path

import pytest

from build_reader import bibliography, store
from build_reader.emit import Table, language_artifact

CORPUS = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def evidence():
    graph, languages = bibliography.load(CORPUS)
    ledger = json.loads((CORPUS / "languages/en/translation-provenance.json").read_text())
    return graph, languages, {row["site"]: row for row in ledger["sites"]}


def reading(text, evidence):
    graph, languages, _ = evidence
    doc, layers = store.load(CORPUS, text)
    projection = bibliography.ReaderCitationProjection(CORPUS, graph, languages)
    artifact = language_artifact(
        doc, layers["en"], Table(), store.translation_relationships(CORPUS, "en"), projection
    )
    return {row["id"]: row for row in artifact["seg"]}


def bases(text, evidence):
    graph, languages, _ = evidence
    projection = bibliography.public_text_evidence(graph, languages["en"])
    document = next((row for row in projection["texts"] if row["id"] == text), None)
    return [
        entry["address"]
        for group in (document or {}).get("source_groups", [])
        if group["role"] == "historical_wording_basis"
        for entry in group["entries"]
    ]


def assert_anima_scope(evidence):
    addresses = bases("orationes.anima-christi", evidence)
    assert all(address["kind"] == "segment" for address in addresses)
    assert {address["segment"] for address in addresses} == {
        "s01",
        "s02",
        "s03",
        "s04",
        "s05",
        "s06",
        "s13",
    }
    assert len(addresses) == 7


def test_english_memorare_keeps_its_independent_draft_separate_from_historical_comparisons(
    evidence,
):
    _, _, ledger = evidence
    rows = reading("orationes.memorare", evidence)
    for segment in ("s01", "s02", "s03", "s04", "s05"):
        assert ledger[f"orationes.memorare.{segment}.en"]["origin"] == "own"
        assert "tc" not in rows[segment]
        assert "tb" not in rows[segment]
    assert bases("orationes.memorare", evidence) == []


def test_anima_historical_support_covers_only_the_attested_invocations_and_ending(evidence):
    _, _, ledger = evidence
    rows = reading("orationes.anima-christi", evidence)
    assert_anima_scope(evidence)
    for segment in ("s07", "s08", "s09", "s10", "s11", "s12"):
        site = ledger[f"orationes.anima-christi.{segment}.en"]
        assert (site["origin"], site["review"]) == ("working-unsettled", "working")
        assert "tc" not in rows[segment]
        assert "tb" not in rows[segment]
    for segment in ("s01", "s02", "s03", "s04", "s05", "s06"):
        assert rows[segment]["tb"] == "exact"
    assert rows["s13"]["tb"] == "normalized"


def test_magnificat_distinguishes_revision_unsettled_wording_and_exact_doxology_reuse(evidence):
    _, _, ledger = evidence
    rows = reading("orationes.magnificat", evidence)
    for segment in ("s01", "s02", "s03", "s04", "s05", "s08"):
        site = ledger[f"orationes.magnificat.{segment}.en"]
        assert (site["origin"], site["review"]) == ("working-unsettled", "working")
        assert "tc" not in rows[segment]
        assert "tb" not in rows[segment]
    for segment in ("s06", "s07", "s09"):
        assert rows[segment]["tb"] == "revised"
    assert rows["s11"]["tb"] == "traditional-composite"
    assert {address["segment"] for address in bases("orationes.magnificat", evidence)} == {
        "s06",
        "s07",
        "s09",
        "s10",
        "s11",
        "s12",
    }
    _, layers = store.load(CORPUS, "orationes.magnificat")
    _, donor = store.load(CORPUS, "orationes.gloria-patri")
    assert (
        layers["en"]["segments"]["s11"]["translation"]
        == (donor["en"]["segments"]["s01"]["translation"])
    )


def test_whole_prayer_source_revival_fails_the_narrow_anima_contract(evidence):
    assert_anima_scope(evidence)
    graph, languages, ledger = copy.deepcopy(evidence)
    removed = [
        use
        for use in languages["en"]["uses"]
        if use["id"] == "use.en.6cbf3a9a9e7a1bca2242"
        and use["address"] == {"kind": "text", "text": "orationes.anima-christi"}
        and use["role"] == "historical_wording_basis"
        and use["decision"] == "REMOVE"
    ]
    assert len(removed) == 1
    removed[0]["decision"] = "RETAIN"
    with pytest.raises(AssertionError):
        assert_anima_scope((graph, languages, ledger))
    assert_anima_scope(evidence)
