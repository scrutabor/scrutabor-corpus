"""The normalized bibliography graph is typed, isolated, and loss-aware."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from build_reader.bibliography import (
    SCHEMA,
    legacy_digest,
    legacy_inventory,
    load,
    parity,
    public_catalog,
    public_catalog_delta,
    public_index,
    public_text_evidence,
    validate,
)
from build_reader.emit import emit

CORPUS = Path(__file__).resolve().parent.parent


def migration() -> dict:
    inventory = legacy_inventory(CORPUS)
    return {
        "complete": False,
        "legacy_inventory": {"count": len(inventory), "sha256": legacy_digest(inventory)},
        "removals": [],
    }


def edition(identifier: str, work: str, title: str) -> dict:
    return {
        "id": identifier,
        "work": work,
        "title": title,
        "year": "1962",
        "publication_type": "official_act",
        "authority": "official_document",
        "rights": {"status": "public-domain", "basis": "Official text."},
    }


def item(identifier: str, edition_id: str) -> dict:
    return {
        "id": identifier,
        "edition": edition_id,
        "repository": "Example repository",
        "kind": "born-digital",
        "record_url": f"https://example.org/{identifier}",
        "access": "open",
    }


def use(identifier: str, edition_id: str, item_id: str, role: str) -> dict:
    return {
        "id": identifier,
        "edition": edition_id,
        "digital_item": item_id,
        "role": role,
        "address": {
            "kind": "segment",
            "text": "orationes.benedic-domine",
            "segment": "s01",
        },
        "locator": {"section": "§ 1"},
        "claim": "The cited section supports this use.",
        "verified_on": "2026-08-28",
        "decision": "RETAIN",
        "legacy_refs": [],
    }


def sample() -> tuple[dict, dict[str, dict]]:
    graph: dict = {
        "schema_version": SCHEMA,
        "migration": migration(),
        "works": [
            {"id": "work-neutral", "responsible": "A", "title": "Neutral work"},
            {"id": "work-pl", "responsible": "B", "title": "Polish work"},
        ],
        "editions": [
            edition("edition-neutral", "work-neutral", "Neutral edition"),
            edition("edition-pl", "work-pl", "Polish edition"),
        ],
        "digital_items": [
            item("item-neutral", "edition-neutral"),
            item("item-pl", "edition-pl"),
        ],
        "uses": [
            use(
                "use-neutral",
                "edition-neutral",
                "item-neutral",
                "official_liturgical_context",
            )
        ],
        "witnesses": [],
        "collations": [],
    }
    languages: dict[str, dict] = {
        "en": {"schema_version": SCHEMA, "language": "en", "uses": []},
        "pl": {
            "schema_version": SCHEMA,
            "language": "pl",
            "uses": [
                use(
                    "use-pl",
                    "edition-pl",
                    "item-pl",
                    "historical_wording_basis",
                )
            ],
        },
    }
    return graph, languages


def test_the_authored_foundation_reconciles_every_legacy_citation():
    graph, languages = load(CORPUS)
    assert validate(CORPUS, graph, languages) == []
    state = parity(CORPUS, graph, languages)
    assert state == {
        "legacy": 2776,
        "mapped": 0,
        "removed": 0,
        "unmapped": 2776,
        "sha256": "0a98de216bb10472089375a1a1845327c1dbcaceb180d688f3e55c5aa6cbb48f",
        "complete": False,
    }


def test_a_complete_typed_sample_is_valid():
    graph, languages = sample()
    assert validate(CORPUS, graph, languages) == []


def test_a_use_cannot_point_to_an_unknown_edition():
    graph, languages = sample()
    graph["uses"][0]["edition"] = "edition-missing"
    errors = validate(CORPUS, graph, languages)
    assert any("unknown edition" in error for error in errors)


def test_a_language_package_rejects_a_neutral_role():
    graph, languages = sample()
    languages["pl"]["uses"][0]["role"] = "lexical_support"
    errors = validate(CORPUS, graph, languages)
    assert any("only wording evidence" in error for error in errors)


def test_a_scanned_print_requires_both_printed_and_scan_locators():
    graph, languages = sample()
    graph["digital_items"][0]["kind"] = "scan"
    graph["digital_items"][0]["scan_url"] = "https://example.org/scan.pdf"
    graph["uses"][0]["locator"] = {"printed": "p. 1"}
    errors = validate(CORPUS, graph, languages)
    assert any("requires printed and scan locators" in error for error in errors)


def test_partial_witness_can_name_an_explicit_stable_word_set():
    graph, languages = sample()
    graph["uses"][0]["role"] = "direct_approved_print"
    graph["witnesses"] = [
        {
            "id": "witness-partial",
            "text": "orationes.benedic-domine",
            "use": "use-neutral",
            "role": "approved_corroboration",
            "coverage": {"kind": "words", "words": ["w001", "w002", "w003"]},
            "transcription_sha256": "a" * 64,
            "orthography_profile": "The source is transcribed without editorial accents.",
            "independence_basis": "The witness is an independently printed approved edition.",
        }
    ]
    assert validate(CORPUS, graph, languages) == []


def test_partial_witness_word_ids_follow_text_order():
    graph, languages = sample()
    graph["uses"][0]["role"] = "direct_approved_print"
    graph["witnesses"] = [
        {
            "id": "witness-partial",
            "text": "orationes.benedic-domine",
            "use": "use-neutral",
            "role": "approved_corroboration",
            "coverage": {"kind": "words", "words": ["w003", "w001"]},
            "transcription_sha256": "a" * 64,
            "orthography_profile": "The source is transcribed without editorial accents.",
            "independence_basis": "The witness is an independently printed approved edition.",
        }
    ]
    errors = validate(CORPUS, graph, languages)
    assert any("must follow canonical text order" in error for error in errors)


def test_one_legacy_attachment_cannot_map_to_two_uses():
    graph, languages = sample()
    reference = legacy_inventory(CORPUS)[0]["ref"]
    graph["uses"][0]["legacy_refs"] = [reference]
    second = copy.deepcopy(graph["uses"][0])
    second["id"] = "use-neutral-two"
    graph["uses"].append(second)
    errors = validate(CORPUS, graph, languages)
    assert any("mapped more than once" in error for error in errors)


def test_complete_migration_refuses_unmapped_legacy_attachments():
    graph, languages = sample()
    graph["migration"]["complete"] = True
    errors = validate(CORPUS, graph, languages)
    assert any("migration is complete" in error for error in errors)


def test_language_only_identities_do_not_leak_into_neutral_or_other_languages():
    graph, languages = sample()
    neutral = public_catalog(graph)
    polish = public_catalog_delta(graph, languages["pl"])
    english = public_catalog_delta(graph, languages["en"])
    assert [edition["id"] for edition in neutral["editions"]] == ["edition-neutral"]
    assert [edition["id"] for edition in polish["editions"]] == ["edition-pl"]
    assert english["editions"] == []
    assert "edition-pl" not in json.dumps(public_index(graph, languages["en"]))
    assert "edition-pl" in json.dumps(public_index(graph, languages["pl"]))


def test_one_edition_can_appear_in_each_section_it_actually_supports():
    graph, languages = sample()
    language_use = languages["pl"]["uses"][0]
    language_use["edition"] = "edition-neutral"
    language_use["digital_item"] = "item-neutral"
    sections = {
        section["id"]: section["entries"]
        for section in public_index(graph, languages["pl"])["sections"]
    }
    assert [entry["edition"] for entry in sections["wording_witnesses"]] == ["edition-neutral"]
    assert [
        entry["edition"] for entry in sections["official_documents_and_liturgical_history"]
    ] == ["edition-neutral"]


def test_a_corrected_and_reverified_use_is_published():
    graph, languages = sample()
    graph["uses"][0]["decision"] = "RETAIN_WITH_CORRECTION"
    graph["uses"][0]["decision_reason"] = "The locator was corrected against the scan."
    assert public_index(graph)["sections"][1]["entries"][0]["edition"] == "edition-neutral"
    assert public_text_evidence(graph)["texts"][0]["uses"][0]["id"] == "use-neutral"
    assert validate(CORPUS, graph, languages) == []


def test_per_text_slices_are_self_contained_and_language_is_not_duplicated():
    graph, languages = sample()
    neutral = public_text_evidence(graph)["texts"][0]
    polish = public_text_evidence(graph, languages["pl"])["texts"][0]
    assert [use["id"] for use in neutral["uses"]] == ["use-neutral"]
    assert [edition["id"] for edition in neutral["catalog"]["editions"]] == ["edition-neutral"]
    assert [use["id"] for use in polish["uses"]] == ["use-pl"]
    assert [edition["id"] for edition in polish["catalog"]["editions"]] == ["edition-pl"]
    assert polish["language"] == "pl"


def test_public_projection_is_an_allowlist():
    graph, _languages = sample()
    graph["uses"][0]["evidence_sha256"] = "a" * 64
    graph["uses"][0]["decision_reason"] = "Internal adjudication."
    graph["digital_items"][0]["sha256"] = "b" * 64
    graph["digital_items"][0]["owner_scan_id"] = "shelf-1"
    projected = json.dumps(
        {
            "catalog": public_catalog(graph),
            "index": public_index(graph),
            "texts": public_text_evidence(graph),
        }
    )
    for private_key in (
        "evidence_sha256",
        "decision_reason",
        "legacy_refs",
        "owner_scan_id",
        "sha256",
    ):
        assert private_key not in projected


def test_reader_emits_new_and_legacy_source_surfaces_together(tmp_path):
    out = tmp_path / "reader"
    emit(CORPUS, out)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert (out / manifest["base"]["citations"]).is_file()
    assert (out / manifest["bibliography"]["catalog"]).is_file()
    assert (out / manifest["bibliography"]["index"]).is_file()
    assert not (out / "bibliography/texts.json").exists()
    for language in manifest["languages"]:
        language_manifest = json.loads((out / language["path"]).read_text(encoding="utf-8"))
        assert (out / language_manifest["citations"]).is_file()
        assert (out / language_manifest["bibliography"]["catalog"]).is_file()
        assert (out / language_manifest["bibliography"]["index"]).is_file()


def test_reader_declares_independent_per_text_evidence(tmp_path, monkeypatch):
    graph, languages = sample()
    monkeypatch.setattr(
        "build_reader.emit.bibliography.load",
        lambda _corpus: (graph, languages),
    )
    out = tmp_path / "reader"
    emit(CORPUS, out)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    text_entry = next(
        entry for entry in manifest["texts"] if entry["id"] == "orationes.benedic-domine"
    )
    assert text_entry["evidence"] == "bibliography/texts/orationes/benedic-domine.json"
    assert (out / text_entry["evidence"]).is_file()
    polish_manifest_path = next(
        entry["path"] for entry in manifest["languages"] if entry["id"] == "pl"
    )
    polish_manifest = json.loads((out / polish_manifest_path).read_text(encoding="utf-8"))
    polish_entry = next(
        entry for entry in polish_manifest["texts"] if entry["id"] == "orationes.benedic-domine"
    )
    assert polish_entry["evidence"] == (
        "languages/pl/bibliography/texts/orationes/benedic-domine.json"
    )
    assert (out / polish_entry["evidence"]).is_file()
