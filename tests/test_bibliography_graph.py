"""The normalized bibliography graph is typed, isolated, and loss-aware."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

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
        "languages": ["la"],
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


def test_the_authored_graph_accounts_for_every_audited_legacy_citation():
    graph, languages = load(CORPUS)
    assert validate(CORPUS, graph, languages) == []
    state = parity(CORPUS, graph, languages)
    assert state == {
        "legacy": 2742,
        "mapped": 1883,
        "removed": 859,
        "unmapped": 0,
        # The seal follows the adopted legacy-citation changes: the Lewis and Short locator
        # of the amen note, `s.v. amen, I` -> `s.v. amen, III.A–B` (2026-10-19); then the
        # English Te Deum attachments (the 28 withdrawn Husenbeth 1853 citations leave with
        # their removal records, Blessed Be God 1925 keeps the 26 segments it prints or revises
        # at exact pages, Douay Ps 30:2 and 32:22 attest s28 and the second sentence of s27) and the
        # Polish Regina caeli s02 Katechizm 1925 attachment, which prints another wording.
        # The historical notes on the litanies now distinguish their 1952 and digital sources.
        "sha256": "6212761ad0d8e748ac0aa2b62248f3d8d608b7a3906eb987de85da99b718ac19",
        "complete": True,
    }


def test_a_complete_typed_sample_is_valid():
    graph, languages = sample()
    assert validate(CORPUS, graph, languages) == []


def test_publication_details_keep_the_date_of_the_copy_distinct_from_its_approval():
    graph, languages = sample()
    book = graph["editions"][0]
    book.update(
        year="s.a.",
        place="New York",
        publisher="The Catholic Publication Society Co.",
        additional_imprints=[{"place": "London", "publisher": "Burns & Oates, Limited"}],
        publication_events=[
            {"kind": "copyright", "date": "1888"},
            {"kind": "imprimatur", "date": "1889-05-17"},
        ],
    )
    assert validate(CORPUS, graph, languages) == []
    projected = next(row for row in public_catalog(graph)["editions"] if row["id"] == book["id"])
    for field in ("year", "additional_imprints", "publication_events"):
        assert projected[field] == book[field]

    book["additional_imprints"] = [{"place": "London"}]
    book["publication_events"] = [{"kind": "imprimatur", "date": "1889-02-31"}]
    errors = validate(CORPUS, graph, languages)
    assert any("additional_imprints[0].publisher" in error for error in errors)
    assert any("publication_events[0].date" in error for error in errors)


def test_a_reproduction_date_stays_with_its_digital_item():
    graph, languages = sample()
    scan = graph["digital_items"][0]
    event = {"kind": "digital_reproduction", "date": "2023"}
    scan["publication_events"] = [event]
    assert validate(CORPUS, graph, languages) == []
    catalog = public_catalog(graph)
    visible = next(row for row in catalog["digital_items"] if row["id"] == scan["id"])
    assert visible["publication_events"] == [event]
    assert all("publication_events" not in row for row in catalog["editions"])
    scan["publication_events"] = [{"kind": "imprimatur", "date": "2023"}]
    assert any("unknown publication event" in error for error in validate(CORPUS, graph, languages))


def test_te_deum_citations_distinguish_the_two_prayer_book_copies():
    graph, languages = load(CORPUS)
    editions = {record["id"]: record for record in graph["editions"]}
    items = {record["id"]: record for record in graph["digital_items"]}
    hymn = [
        use
        for use in languages["en"]["uses"]
        if use["address"].get("text") == "orationes.te-deum" and "blessed-be-god" in use["edition"]
    ]
    earlier, later = sorted(hymn, key=lambda use: use["edition"])
    assert editions[earlier["edition"]]["year"] == "[1925]"
    assert editions[later["edition"]]["year"] == "1952/.."
    assert earlier["role"] == "historical_wording_basis"
    assert later["role"] == "historical_wording_comparator"
    assert items[earlier["digital_item"]]["edition"] == earlier["edition"]
    assert items[later["digital_item"]]["edition"] == later["edition"]
    assert earlier["locator"]["printed"] == "pp. 490–491"
    assert later["locator"]["printed"] == "pp. 500–501"
    assert earlier["locator"]["page_url"].endswith("/page/n266/mode/1up")
    assert len(earlier["legacy_refs"]) == 26
    assert not later.get("legacy_refs")
    index = public_index(graph, languages["en"])
    sources = next(section for section in index["sections"] if section["id"] == "wording_witnesses")
    order = [entry["edition"] for entry in sources["entries"]]
    assert order.index(earlier["edition"]) < order.index(later["edition"])


def test_existing_schema_reads_its_original_publication_fields():
    graph, languages = sample()
    graph["schema_version"] = "1.6.0"
    for package in languages.values():
        package["schema_version"] = graph["schema_version"]
    assert validate(CORPUS, graph, languages) == []
    graph["editions"][0]["publication_events"] = [{"kind": "copyright", "date": "1888"}]
    assert any(
        "publication details require" in error for error in validate(CORPUS, graph, languages)
    )


def test_lemma_evidence_is_indexed_without_inventing_a_text_address():
    graph, languages = sample()
    lexical = use("use-lemma", "edition-neutral", "item-neutral", "lexical_support")
    lexical["address"] = {"kind": "lemma", "lemma": "deus"}
    lexical["evidence_sha256"] = "a" * 64
    lexical["decision_reason"] = "Private validation detail."
    graph["uses"].append(lexical)
    graph["uses"].sort(key=lambda record: record["id"])
    assert validate(CORPUS, graph, languages) == []
    index = public_index(graph)
    section = next(s for s in index["sections"] if s["id"] == "scripture_language_and_scholarship")
    entry = section["entries"][0]
    assert entry["texts"] == []
    assert entry["lemmas"][0]["id"] == "deus"
    assert entry["lemmas"][0]["roles"] == ["lexical_support"]
    assert entry["lemmas"][0]["uses"] == 1
    group = entry["lemmas"][0]["source_groups"][0]
    assert group["entries"][0]["address"] == {"kind": "lemma", "lemma": "deus"}
    assert group["entries"][0]["claim"] == lexical["claim"]
    assert "evidence_sha256" not in json.dumps(entry)
    assert "decision_reason" not in json.dumps(entry)
    assert all(record["id"] != "deus" for record in public_text_evidence(graph)["texts"])


def test_rejected_lemma_evidence_does_not_enter_the_index():
    graph, _languages = sample()
    lexical = use("use-lemma", "edition-neutral", "item-neutral", "lexical_support")
    lexical.update(address={"kind": "lemma", "lemma": "deus"}, decision="REMOVE")
    graph["uses"].append(lexical)
    section = next(
        s
        for s in public_index(graph)["sections"]
        if s["id"] == "scripture_language_and_scholarship"
    )
    assert section["entries"] == []


def test_a_use_cannot_point_to_an_unknown_edition():
    graph, languages = sample()
    graph["uses"][0]["edition"] = "edition-missing"
    errors = validate(CORPUS, graph, languages)
    assert any("unknown edition" in error for error in errors)


def test_an_edition_rejects_an_unsupported_reader_language():
    graph, languages = sample()
    graph["editions"][0]["languages"] = ["lt"]
    errors = validate(CORPUS, graph, languages)
    assert any("unsupported reader language" in error for error in errors)


def test_an_edition_accepts_supported_parallel_languages():
    graph, languages = sample()
    graph["editions"][0]["languages"] = ["en", "la"]
    assert validate(CORPUS, graph, languages) == []


def test_a_use_rejects_the_obsolete_generic_historical_context_role():
    graph, languages = sample()
    graph["uses"][0]["role"] = "historical_context"
    errors = validate(CORPUS, graph, languages)
    assert any("role: must be one of" in error for error in errors)


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
    graph, languages = load(CORPUS)
    (partial,) = [
        copy.deepcopy(w)
        for w in graph["witnesses"]
        if w["id"] == "witness.proprium.dominica-i-post-epiphaniam-postcommunio.mr-lent-ii"
    ]
    # A real printed proper subset retains its complete source identity.
    assert partial["coverage"] == {
        "kind": "words",
        "words": [f"w{index:03d}" for index in range(1, 18)],
    }
    graph["witnesses"] = [partial]
    graph["collations"] = []
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
    entry = public_text_evidence(graph)["texts"][0]["source_groups"][0]["entries"][0]
    assert entry["id"] == "use-neutral"
    assert validate(CORPUS, graph, languages) == []


def test_per_text_slices_share_catalogues_and_language_is_not_duplicated():
    graph, languages = sample()
    neutral = public_text_evidence(graph)["texts"][0]
    polish = public_text_evidence(graph, languages["pl"])["texts"][0]
    assert [entry["id"] for entry in neutral["source_groups"][0]["entries"]] == ["use-neutral"]
    assert "catalog" not in neutral
    assert [entry["id"] for entry in polish["source_groups"][0]["entries"]] == ["use-pl"]
    assert "catalog" not in polish
    assert polish["language"] == "pl"


def test_digital_source_passages_require_distinct_ordered_line_ranges_and_the_first_link():
    graph, languages = sample()
    first = "https://example.org/Ordo.txt#L12-L13"
    second = "https://example.org/Prayers.txt#L6"
    locator = graph["uses"][0]["locator"]
    locator.update(
        page_url=first,
        passages=[{"heading": "Ordo", "url": first}, {"heading": "Gloria", "url": second}],
    )
    assert validate(CORPUS, graph, languages) == []
    projected = public_text_evidence(graph)["texts"][0]["source_groups"][0]
    assert projected["locator"]["passages"] == locator["passages"]
    locator["passages"][1]["url"] = first
    assert any("duplicate source passage" in issue for issue in validate(CORPUS, graph, languages))
    locator["passages"][1]["url"] = "https://example.org/Prayers.txt#L6-L5"
    assert any("ordered source line range" in issue for issue in validate(CORPUS, graph, languages))
    locator["passages"][1]["url"] = second
    locator["page_url"] = second
    assert any("first source passage" in issue for issue in validate(CORPUS, graph, languages))
    graph["digital_items"][0]["kind"] = "scan"
    assert any(
        "line references require a digital text" in issue
        for issue in validate(CORPUS, graph, languages)
    )


@pytest.mark.parametrize("record_kind", ["raw", "commit", "blob"])
def test_revision_links_bind_associated_files_to_the_same_source_tree(record_kind):
    graph, languages = sample()
    revision = "2" * 40
    repository = "example/liturgy"
    source = f"https://github.com/{repository}"
    item = graph["digital_items"][0]
    item["record_url"] = {
        "raw": f"https://raw.githubusercontent.com/{repository}/{revision}/Mass/Ordo.txt",
        "commit": f"{source}/commit/{revision}",
        "blob": f"{source}/blob/{revision}/Mass/Ordo.txt",
    }[record_kind]
    item["revision"] = revision
    pages = [
        {"heading": name, "url": f"{source}/blob/{revision}/{file}#L2-L6"}
        for name, file in [("Ordo", "Mass/Ordo.txt"), ("Per Dominum", "Commune/Prayers.txt")]
    ]
    use = graph["uses"][0]
    use["locator"].update(page_url=pages[0]["url"], passages=pages)
    assert validate(CORPUS, graph, languages) == []
    original = pages[1]["url"]
    for wrong in (
        original.replace(revision, "3" * 40),
        original.replace(repository, "example/another-book"),
        original.replace("github.com", "example.org"),
    ):
        pages[1]["url"] = wrong
        assert any(
            "another repository or revision" in e for e in validate(CORPUS, graph, languages)
        )
    pages[1]["url"] = original
    item["revision"] = "4" * 40
    assert any("differs from its source revision" in e for e in validate(CORPUS, graph, languages))


def test_consultation_date_is_projected_separately_from_the_edition_year():
    graph, languages = sample()
    item = graph["digital_items"][0]
    item["accessed_on"] = "2026-11-26"
    assert validate(CORPUS, graph, languages) == []
    assert public_catalog(graph)["digital_items"][0]["accessed_on"] == "2026-11-26"
    assert public_catalog(graph)["editions"][0]["year"] == "1962"
    item["accessed_on"] = "2026-02-30"
    assert any("accessed_on" in issue for issue in validate(CORPUS, graph, languages))


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


def test_polish_te_deum_opens_the_hymn_in_the_siedlecki_viewer():
    uses = json.loads((CORPUS / "languages/pl/bibliography.json").read_text())["uses"]
    (hymn,) = [u for u in uses if u["id"] == "use.pl.orationes.te-deum.siedlecki1928"]
    assert hymn["locator"]["printed"] == "s. 308–309"
    assert hymn["locator"]["scan"] == "skany DjVu 326–327"
    assert hymn["locator"]["page_url"] == (
        "https://www.wbc.poznan.pl/dlibra/publication/538983/edition/457839/content?p=326"
    )


def test_ordinary_canon_and_psalm_stanza_keep_their_source_roles():
    graph, languages = load(CORPUS)
    by_id = {use["id"]: use for use in graph["uses"]}
    canon = by_id["use.ordinarium.communicantes.ordinary-vatican"]
    amendment = by_id["use.ordinarium.communicantes.joseph-amendment"]
    gesture = by_id["use.ordinarium.communicantes.ordinary-hands-vatican"]
    assert canon["locator"]["printed"] == "pp. 302–303"
    assert canon["locator"]["page_url"].endswith("/page/n382/mode/1up")
    assert gesture["locator"]["page_url"].endswith("/page/n383/mode/1up")
    assert (amendment["address"]["segment"], amendment["locator"]["printed"]) == ("s02", "p. 873")
    assert gesture["address"]["segment"] == "s06" and gesture["role"] == "rubric_control"
    psalm = by_id["use.psalmi.118-he.hetzenauer-1914"]
    assert psalm["role"] == "scripture_text" and psalm["locator"]["printed"] == "pp. 550–551"
    volume = "https://archive.org/details/bibliasacravulga00helzuoft/bibliasacravulga00helzuoft"
    assert psalm["locator"]["page_url"] == f"{volume}/page/550/mode/1up"
    de_profundis = by_id["use.core.6633ed8538a351936777"]
    assert de_profundis["address"]["text"] == "defunctorum.de-profundis"
    assert de_profundis["digital_item"] == psalm["digital_item"]
    assert de_profundis["locator"]["page_url"] == f"{volume}/page/556/mode/1up"
    (comparison,) = (
        use
        for use in languages["pl"]["uses"]
        if use["id"] == "use.pl.psalmi.118-he.wujek-1923-porownanie"
    )
    assert comparison["role"] == "historical_wording_comparator"
    assert comparison["locator"]["page_url"].endswith(".djvu?page=588")
    assert len(comparison["legacy_refs"]) == 8


def test_lateran_liturgy_identifies_the_missals_separately_numbered_common():
    graph, _ = load(CORPUS)
    prefix = "use.proprium.dedicatio-archibasilicae-sanctissimi-salvatoris-"
    sources = {use["id"]: use["locator"] for use in graph["uses"]}
    readings = {
        ("p. (41)", "n868"): ("introitus", "collecta"),
        ("pp. (41)–(42)", "n868"): ("epistola",),
        ("p. (42)", "n869"): ("graduale", "alleluia", "tractus", "evangelium", "offertorium"),
        ("p. (43)", "n870"): ("secreta", "communio", "postcommunio"),
    }
    for (printed, leaf), parts in readings.items():
        for part in parts:
            locator = sources[f"{prefix}{part}.mr1962"]
            assert locator["printed"] == printed
            assert locator["page_url"].endswith(f"/page/{leaf}/mode/1up")
    assert "In anniversario Dedicationis" in sources[prefix + "collecta.mr1962"]["section"]
    assert "Extra ecclesiam ipsam dedicatam" in sources[prefix + "secreta.mr1962"]["section"]
    assert "In anniversario Dedicationis" in sources[prefix + "postcommunio.mr1962"]["section"]


def test_quinquagesima_introit_links_the_doxology_and_its_rubric_to_their_own_pages():
    graph, _ = load(CORPUS)
    prefix = "use.proprium.dominica-in-quinquagesima-introitus."
    uses = {use["id"]: use for use in graph["uses"]}
    doxology = uses[prefix + "doxology.mr1962"]
    gesture = uses[prefix + "introit-ritus-iv-2.mr1962"]
    assert doxology["locator"]["section"] == "First Sunday of Advent Introit, common Gloria Patri"
    assert doxology["locator"]["printed"] == "p. 1"
    assert doxology["locator"]["page_url"].endswith("/page/n80/mode/1up")
    assert gesture["role"] == "rubric_control" and gesture["locator"]["printed"] == "p. lii"
    assert gesture["locator"]["page_url"].endswith("/page/n57/mode/1up")


def test_advent_communion_opens_the_words_in_the_archived_common_and_the_executed_reference():
    graph, _ = load(CORPUS)
    uses = {use["id"]: use for use in graph["uses"]}
    prefix = "use.proprium.dominica-iv-adventus-communio."
    archived = uses[prefix + "do21cb2d37"]["locator"]
    reference = uses[prefix + "reference.do21cb2d37"]["locator"]
    revision = "21cb2d370337ec1fd668e96d035622b4296c32cb"
    upstream = f"https://github.com/DivinumOfficium/divinum-officium/blob/{revision}/"
    relative = "obsolete/missa/Latin/Commune/C10a.txt"
    assert archived["page_url"] == upstream + relative + "#L47-L49"
    assert archived["passages"] == [{"heading": "Communio", "url": archived["page_url"]}]
    lines = (CORPUS / "witnesses/raw/do-21cb2d37" / relative).read_text().splitlines()
    assert lines[46:48] == ["[Communio]", "!Is 7:14"]
    assert lines[48].startswith("Ecce, Virgo concípiet")
    assert reference["page_url"] == upstream + "web/www/missa/Latin/Tempora/Adv4-0.txt#L56-L57"
    assert upstream + "web/www/horas/Latin/Commune/C10a.txt#L39-L41" in {
        page["url"] for page in reference["passages"]
    }
