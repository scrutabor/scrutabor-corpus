"""Current EO Latin witnesses preserve historical uncertainty and exact page identity."""

import hashlib
import json
import shutil
from copy import deepcopy
from pathlib import Path
from typing import TypedDict

import pytest

from build_reader import bibliography
from build_reader.bibliography_bindings import BindingError, transcript_digest, witness_subject
from build_reader.layers import expand_core
from checks.collate import collate, load_witness

ROOT = Path(__file__).resolve().parents[1]


class WitnessCase(TypedDict):
    text: str
    words: int
    document: dict[str, str | int]
    old_transcript_sha256: str
    old_apparatus_sha256: str
    fresh_transcript_sha256: str


CASES: list[WitnessCase] = [
    {
        "text": "ordinarium.confiteor-sacerdotis",
        "words": 66,
        "document": {
            "contract": "paginated-pdf-1",
            "use": "use.ordinarium.confiteor-sacerdotis.handmissal-eo2025",
            "digital_item": "item.extraordinaryform.handmissal-chant.2025-12-12.pdf",
            "sha256": "43e21a0356b4ab1641c8dfa3927d8e29b53f3b26f926b23080842d601e07d84d",
            "media_type": "application/pdf",
            "pdf_page": 4,
            "printed": "2",
            "region": "left-half",
            "page_image_sha256": "6f1ce1f0e66649f05c65f1f82c556dd5ab4bca009c315f7c5805e66c34bb59bf",
        },
        "old_transcript_sha256": "421f24ba883c2b4cd112f41aa3fa15ad37a687cc5f930e6cc9dfe92c9a3b5815",
        "old_apparatus_sha256": "d23b4d1119d071d3878d4de8725aef23e02cb1678a96b8e1de3b3c2ba48776ec",
        "fresh_transcript_sha256": (
            "21453e1fefd8a5d8b824234da554e475886472a8f45aa96fdb2573d38001d0ec"
        ),
    },
    {
        "text": "ordinarium.confiteor",
        "words": 66,
        "document": {
            "contract": "paginated-pdf-1",
            "use": "use.ordinarium.confiteor.handmissal-eo2025",
            "digital_item": "item.extraordinaryform.handmissal-chant.2025-12-12.pdf",
            "sha256": "43e21a0356b4ab1641c8dfa3927d8e29b53f3b26f926b23080842d601e07d84d",
            "media_type": "application/pdf",
            "pdf_page": 6,
            "printed": "4",
            "region": "left-half",
            "page_image_sha256": "e554421da2c8241462b4f3d3bf46a64ee1f1a873362ff2623983da81ba3e07fe",
        },
        "old_transcript_sha256": "62458249de00c41c1d3bfa00ca17e2f7c08386294f5db2467a8189037bda2894",
        "old_apparatus_sha256": "affa0a2d429dc7b29ff5b5b5174ffcf53b2f6ea9458fc28f3c9261a4000a24fc",
        "fresh_transcript_sha256": (
            "192794ba3fc35fcfa1f33ad8408e5c77a963383ad2f6d4ec1ef19ae520e99d76"
        ),
    },
    {
        "text": "ordinarium.evangelium-ultimum",
        "words": 189,
        "document": {
            "contract": "paginated-pdf-1",
            "use": "use.ordinarium.evangelium-ultimum.handmissal-eo2025",
            "digital_item": "item.extraordinaryform.handmissal-chant.2025-12-12.pdf",
            "sha256": "43e21a0356b4ab1641c8dfa3927d8e29b53f3b26f926b23080842d601e07d84d",
            "media_type": "application/pdf",
            "pdf_page": 28,
            "printed": "26",
            "region": "left-half",
            "page_image_sha256": "35e0cbcd059bd4c45036267a76cbec2b7b4adb3cdab22f219b8bb6ed5ac98262",
        },
        "old_transcript_sha256": "ed9adcb567f480eca7937ac247665fa437febd855a8a39cfdd74322e63d3f42d",
        "old_apparatus_sha256": "865f63c150be31cddd25eb843eee5c9d82cdb069c1ab5d8f769ede4fe4d206ed",
        "fresh_transcript_sha256": (
            "413c75ab5eed62d6164a37c375c642af2b697b44cc1cdb2eb689e4f83b54c2b4"
        ),
    },
]
CASE_IDS = [row["text"] for row in CASES]


def load_core(row):
    category, slug = row["text"].split(".", 1)
    return json.loads((ROOT / f"texts/{category}/{slug}.json").read_text())


def lookup(graph, collection, identifier):
    matches = [value for value in graph[collection] if value["id"] == identifier]
    assert len(matches) == 1
    return matches[0]


def bound(graph, row):
    return lookup(graph, "witnesses", f"witness.{row['text']}.handmissal-eo2025")


def healthy(root, graph, row):
    witness = bound(graph, row)
    result = witness_subject(root, witness, graph, load_core(row))
    assert result["contract"] == "witness-review-2"
    assert result["document_resolution"]["documents"] == {
        f"use.{row['text']}.handmissal-eo2025": row["document"]
    }
    return result


@pytest.fixture(scope="module")
def actual():
    graph, languages = bibliography.load(ROOT)
    for row in CASES:
        healthy(ROOT, graph, row)
    return graph, languages


@pytest.mark.parametrize("row", CASES, ids=CASE_IDS)
def test_current_full_witness_has_exact_pending_pdf_inventory(actual, row):
    graph, _ = actual
    witness = bound(graph, row)
    assert witness["review"] == {"status": "pending"}
    assert witness["coverage"] == {"kind": "full"}
    assert witness["transcription"] == "handmissal-eo2025"
    assert witness["source_dependencies"] == {
        "uses": [],
        "raw_binding": None,
        "documents": [row["document"]],
    }
    use = lookup(graph, "uses", witness["use"])
    assert use["digital_item"] == row["document"]["digital_item"]
    assert use["evidence_sha256"] == row["document"]["page_image_sha256"]
    assert use["role"] == "corroborating_latin_witness"
    assert use["address"] == {"kind": "text", "text": row["text"]}
    assert use["verified_on"] == "2026-10-24"
    assert "unretained August" in use["claim"]


@pytest.mark.parametrize("row", CASES, ids=CASE_IDS)
def test_complete_active_body_uses_real_collation_not_only_hashes(actual, row):
    folder = ROOT / f"witnesses/{row['text']}"
    errors, warnings, stats = collate(expand_core(load_core(row)), folder)
    assert errors == warnings == []
    assert stats["words"] == row["words"]
    expected_partial = 1 if row["text"] == "ordinarium.evangelium-ultimum" else 0
    assert (stats["witnesses"], stats["partial"]) == (3, expected_partial)
    meta, literal = load_witness(folder / "handmissal-eo2025.txt")
    assert meta["witness"] == "handmissal-eo2025"
    assert len(literal.split()) == row["words"]
    assert literal.split()[37 if row["words"] == 66 else 33] == (
        "Ídeo" if row["words"] == 66 else "Ómnia"
    )
    apparatus = json.loads((folder / "apparatus.json").read_text())
    assert not any("handmissal-eo" in e["witnesses"] for e in apparatus["adjudicated"])
    if row["words"] == 189:
        assert literal.split()[165:170] == ["ET", "VERBUM", "CARO", "FACTUM", "EST"]
        dispute = next(e for e in apparatus["adjudicated"] if e["at"] == "w143")
        assert "DISPUTED" in dispute["ruling"]


@pytest.mark.parametrize("row", CASES, ids=CASE_IDS)
def test_historical_bytes_are_unchanged_but_not_active(actual, row):
    folder = ROOT / f"witnesses/{row['text']}"
    assert not (folder / "handmissal-eo.txt").exists()
    old = folder / "historical-2026-10-24/handmissal-eo.txt"
    old_apparatus = folder / "historical-2026-10-24/apparatus.json"
    assert hashlib.sha256(old.read_bytes()).hexdigest() == row["old_transcript_sha256"]
    assert hashlib.sha256(old_apparatus.read_bytes()).hexdigest() == row["old_apparatus_sha256"]
    fresh = folder / "handmissal-eo2025.txt"
    assert hashlib.sha256(fresh.read_bytes()).hexdigest() == row["fresh_transcript_sha256"]
    assert load_witness(old)[1] == load_witness(fresh)[1]
    assert old not in folder.glob("*.txt")


@pytest.mark.parametrize("row", CASES, ids=CASE_IDS)
@pytest.mark.parametrize(
    "field,value",
    [
        ("pdf_page", 32),
        ("printed", "999"),
        ("region", "right-half"),
        ("page_image_sha256", "0" * 64),
    ],
)
def test_wrong_legal_document_identity_fails_and_recovers(actual, row, field, value):
    graph = deepcopy(actual[0])
    witness = bound(graph, row)
    record = witness["source_dependencies"]["documents"][0]
    record[field] = value
    with pytest.raises(BindingError):
        healthy(ROOT, graph, row)
    record[field] = row["document"][field]
    healthy(ROOT, graph, row)


@pytest.mark.parametrize("row", CASES, ids=CASE_IDS)
def test_body_order_mutation_is_rejected_even_after_rehash(actual, row, tmp_path):
    graph = deepcopy(actual[0])
    folder = tmp_path / f"witnesses/{row['text']}"
    shutil.copytree(ROOT / f"witnesses/{row['text']}", folder)
    path = folder / "handmissal-eo2025.txt"
    original = path.read_text()
    lines = original.splitlines()
    index = next(i for i, line in enumerate(lines) if line and not line.startswith("#"))
    words = lines[index].split()
    # Swap an internal pair, not one of the three assigned accent initials.
    words[7], words[8] = words[8], words[7]
    lines[index] = " ".join(words)
    path.write_text("\n".join(lines) + "\n")
    bound(graph, row)["transcription_sha256"] = transcript_digest(path.read_text())
    # A recomputed identity cannot substitute for whole-text comparison.
    healthy(tmp_path, graph, row)
    errors, _, _ = collate(expand_core(load_core(row)), folder)
    assert errors
    path.write_text(original)
    bound(graph, row)["transcription_sha256"] = transcript_digest(original)
    healthy(tmp_path, graph, row)
    errors, warnings, _ = collate(expand_core(load_core(row)), folder)
    assert errors == warnings == []


@pytest.mark.parametrize("row", CASES, ids=CASE_IDS)
def test_missing_document_inventory_is_not_a_reviewable_source(actual, row):
    graph = deepcopy(actual[0])
    del bound(graph, row)["source_dependencies"]["documents"]
    with pytest.raises(BindingError, match="evidence contract"):
        healthy(ROOT, graph, row)
    bound(graph, row)["source_dependencies"]["documents"] = [row["document"]]
    healthy(ROOT, graph, row)


def pending_package_sources(graph, languages, language):
    authored = graph if language is None else languages[language]
    expected = {
        row["text"]: sorted(
            use["id"]
            for use in authored["uses"]
            if use.get("decision") in {"RETAIN", "RETAIN_WITH_CORRECTION"}
            and use.get("address", {}).get("text") == row["text"]
        )
        for row in CASES
    }
    expected = {text: uses for text, uses in expected.items() if uses}
    expected_texts = set(CASE_IDS)
    if language == "pl":
        expected_texts.remove("ordinarium.evangelium-ultimum")
    assert set(expected) == expected_texts
    if language is None:
        for row in CASES:
            assert row["document"]["use"] in expected[row["text"]]
    return expected


def assert_pending_package(package, expected):
    entries = [entry for entry in package["texts"] if entry["id"] in CASE_IDS]
    assert [entry["id"] for entry in entries] == sorted(expected)
    for entry in entries:
        assert entry["witnesses"] == []
        assert "collation" not in entry
        uses = sorted(use["id"] for group in entry["source_groups"] for use in group["entries"])
        assert uses == expected[entry["id"]]


@pytest.mark.parametrize("language", [None, "pl", "en"])
def test_pending_witnesses_are_not_public_source_reviews(actual, language):
    graph, languages = actual
    for row in CASES:
        assert bound(graph, row)["review"] == {"status": "pending"}
    assert not any(record["text"] in CASE_IDS for record in graph["collations"])
    expected = pending_package_sources(graph, languages, language)
    package = bibliography.public_text_evidence(graph, languages[language] if language else None)
    assert_pending_package(package, expected)


@pytest.mark.parametrize("language", [None, "pl", "en"])
@pytest.mark.parametrize("row", CASES, ids=CASE_IDS)
def test_projection_review_inventory_and_package_boundaries_recover(actual, language, row):
    graph = deepcopy(actual[0])
    saved = deepcopy(graph)
    languages = actual[1]
    local = languages[language] if language else None
    expected = pending_package_sources(graph, languages, language)
    baseline = bibliography.public_text_evidence(graph, local)
    assert_pending_package(baseline, expected)
    witness = bound(graph, row)
    assert witness["review"] == {"status": "pending"}

    # A pending witness contributes no public review, even when removed.
    index = graph["witnesses"].index(witness)
    graph["witnesses"].pop(index)
    assert bibliography.public_text_evidence(graph, local) == baseline
    graph["witnesses"].insert(index, witness)

    # Synthetic projection shape only: no source files or review ledger are
    # changed, and this digest is not a valid source-review certification.
    # public_text_evidence requires validated inputs at its real build boundary.
    witness["review"] = {"status": "reviewed", "sha256": "0" * 64}
    projected = bibliography.public_text_evidence(graph, local)
    want = deepcopy(baseline)
    if language is None:
        entry = next(entry for entry in want["texts"] if entry["id"] == row["text"])
        entry["witnesses"] = [
            {
                key: witness[key]
                for key in ("id", "text", "use", "role", "coverage", "independence_basis")
            }
        ]
    assert projected == want

    # The valid review shape cannot bypass either a nonretained primary use
    # or an unknown dependency inventory. Compare actual producer outputs.
    for fault in ("nonretained-use", "unknown-inventory"):
        ineligible = deepcopy(graph)
        if fault == "nonretained-use":
            lookup(ineligible, "uses", witness["use"])["decision"] = "REMOVE"
        else:
            del bound(ineligible, row)["source_dependencies"]
        withheld = bibliography.public_text_evidence(ineligible, local)
        assert not any(
            value["id"] == witness["id"]
            for entry in withheld["texts"]
            for value in entry["witnesses"]
        )
        bound(ineligible, row)["review"] = {"status": "pending"}
        assert bibliography.public_text_evidence(ineligible, local) == withheld
        assert bibliography.public_text_evidence(graph, local) == want

    witness["review"] = {"status": "pending"}
    recovered = bibliography.public_text_evidence(graph, local)
    assert recovered == baseline
    assert_pending_package(recovered, expected)
    assert graph == saved
