"""Publication decisions do not rewrite frozen attachment accounting."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from build_reader import bibliography, store
from build_reader.emit import (
    Table,
    _project_glosses,
    _strip,
    core_artifact,
    expand,
    language_artifact,
)

CORPUS = Path(__file__).resolve().parent.parent
PARTS = ("segments", "s01", "translation_citations")
LORETO = {
    "use.en.b7006dedaf2ec2101d90": "s042",
    "use.en.94df27e1dc35e43045a2": "s130",
    "use.en.eb7ef5c3b722ca81f2ee": "s131",
    "use.en.3682554096d72dac3369": "s132",
}


@pytest.fixture
def attachments(tmp_path):
    citation = {"title": "Same work", "locator": "Same page"}
    sources = {
        "neutral": (
            "texts/orationes/sample.json",
            ("localization", "about_citations"),
        ),
        "pl": ("languages/pl/texts/orationes/sample.json", PARTS),
        "en": ("languages/en/texts/orationes/sample.json", PARTS),
    }
    for relative, parts in sources.values():
        document = {}
        node = document
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = [copy.deepcopy(citation), copy.deepcopy(citation)]
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document), encoding="utf-8")
    graph = {"uses": [], "migration": {"removals": []}}
    languages = {language: {"uses": []} for language in ("pl", "en")}
    return tmp_path, graph, languages, sources, citation


def add_use(graph, languages, scope, refs, decision, identifier="use.test"):
    record = {
        "id": identifier,
        "decision": decision,
        "legacy_refs": refs,
        "address": {"kind": "segment", "text": "orationes.sample", "segment": "s01"},
        "role": "official_liturgical_context" if scope == "neutral" else "historical_wording_basis",
        "edition": "edition.test",
        "digital_item": "item.test",
        "locator": {"section": "1"},
        "claim": "A claim.",
    }
    (graph if scope == "neutral" else languages[scope])["uses"].append(record)


def consume_inventory(corpus, projection):
    inspected = set()
    for record in bibliography.legacy_inventory(corpus):
        relative, pointer = record["ref"].split("#/", 1)
        parts = tuple(
            part.replace("~1", "/").replace("~0", "~") for part in pointer.split("/")[:-1]
        )
        if (relative, parts) in inspected:
            continue
        inspected.add((relative, parts))
        node = json.loads((corpus / relative).read_text(encoding="utf-8"))
        for part in parts:
            node = node[int(part)] if isinstance(node, list) else node[part]
        projection.citations(relative, parts, node)


def test_legacy_reference_preserves_json_pointer_escaping_and_original_index():
    assert (
        bibliography.legacy_reference(
            "lexicon/lemmata.json",
            ("entries", "a/b~c", "localization", "note_citations"),
            2,
        )
        == "lexicon/lemmata.json#/entries/a~1b~0c/localization/note_citations/2"
    )


@pytest.mark.parametrize("scope", ["neutral", "pl", "en"])
@pytest.mark.parametrize(
    ("decision", "retained"),
    [
        ("RETAIN", True),
        ("RETAIN_WITH_CORRECTION", True),
        ("REMOVE", False),
        ("REPLACE", False),
        ("UNVERIFIED_NO_DIRECT_EVIDENCE", False),
        (None, False),
        ("UNKNOWN", False),
    ],
)
def test_exact_mapped_attachment_follows_the_normalized_decision(
    attachments, scope, decision, retained
):
    corpus, graph, languages, sources, citation = attachments
    relative, parts = sources[scope]
    reference = bibliography.legacy_reference(relative, parts, 0)
    add_use(graph, languages, scope, [reference], decision)
    frozen = copy.deepcopy((graph, languages, bibliography.legacy_inventory(corpus)))
    projection = bibliography.ReaderCitationProjection(corpus, graph, languages)
    consume_inventory(corpus, projection)
    assert projection.citations(relative, parts, [citation, citation]) == [citation] * (
        2 if retained else 1
    )
    assert projection.errors() == []
    assert projection.counts() == {
        "legacy": 6,
        "mapped": 1,
        "kept": 6 if retained else 5,
        "excluded": 0 if retained else 1,
        "unresolved": 5,
        "rejected_exposed": 0,
    }
    assert (graph, languages, bibliography.legacy_inventory(corpus)) == frozen
    assert projection.removed == set()
    for other_scope, (other_path, other_parts) in sources.items():
        if other_scope != scope:
            assert projection.citations(other_path, other_parts, [citation, citation]) == [
                citation,
                citation,
            ]


def test_one_rejected_use_excludes_both_original_refs_without_reindexing(attachments):
    corpus, graph, languages, sources, citation = attachments
    relative, parts = sources["en"]
    refs = [bibliography.legacy_reference(relative, parts, index) for index in (0, 1)]
    add_use(graph, languages, "en", refs, "REPLACE")
    projection = bibliography.ReaderCitationProjection(corpus, graph, languages)
    consume_inventory(corpus, projection)
    assert projection.citations(relative, parts, [citation, citation]) == []
    assert projection.excluded == set(refs)
    assert projection.counts()["mapped"] == 2
    assert projection.counts()["unresolved"] == 4
    assert projection.errors() == []


def test_mixed_same_title_attachments_keep_the_retained_original_index(attachments):
    corpus, graph, languages, sources, citation = attachments
    relative, parts = sources["en"]
    first, second = [bibliography.legacy_reference(relative, parts, index) for index in (0, 1)]
    add_use(graph, languages, "en", [first], "REMOVE", "use.first")
    add_use(graph, languages, "en", [second], "RETAIN_WITH_CORRECTION", "use.second")
    projection = bibliography.ReaderCitationProjection(corpus, graph, languages)
    consume_inventory(corpus, projection)
    assert projection.citations(relative, parts, [citation, citation]) == [citation]
    assert first in projection.excluded and first not in projection.kept
    assert second in projection.kept and second not in projection.excluded
    assert projection.errors() == []


def test_unmapped_compatibility_remains_unresolved_not_verified(attachments):
    corpus, graph, languages, sources, citation = attachments
    projection = bibliography.ReaderCitationProjection(corpus, graph, languages)
    consume_inventory(corpus, projection)
    assert projection.counts() == {
        "legacy": 6,
        "mapped": 0,
        "kept": 6,
        "excluded": 0,
        "unresolved": 6,
        "rejected_exposed": 0,
    }
    for relative, parts in sources.values():
        assert projection.has_unmapped_citation(relative, parts, [citation, citation])
    assert projection.errors() == []


@pytest.mark.parametrize("explicit", [False, True])
def test_projection_diagnostics_cover_explicit_and_decision_rejections(attachments, explicit):
    corpus, graph, languages, sources, _citation = attachments
    relative, parts = sources["en"]
    reference = bibliography.legacy_reference(relative, parts, 0)
    if explicit:
        graph["migration"]["removals"] = [{"legacy_ref": reference, "reason": "Unsupported claim."}]
    else:
        add_use(graph, languages, "en", [reference], "UNVERIFIED_NO_DIRECT_EVIDENCE")
    projection = bibliography.ReaderCitationProjection(corpus, graph, languages)
    consume_inventory(corpus, projection)
    assert projection.errors() == []
    projection.kept.add(reference)
    assert projection.counts()["rejected_exposed"] == 1
    assert any("retained rejected attachments" in error for error in projection.errors())
    projection.kept.remove(reference)
    projection.excluded.remove(reference)
    assert any(
        "did not exclude every rejected attachment" in error for error in projection.errors()
    )
    projection.excluded.add(reference)
    assert projection.errors() == []


@pytest.mark.parametrize(
    ("mutation", "diagnostic"),
    [
        ("duplicate", "mapped more than once"),
        ("unknown", "mappings name unknown legacy references"),
        ("foreign-package", "another package's citation"),
        ("mapped-and-removed", "both mapped and removed"),
        ("unresolved-complete", "migration is complete"),
    ],
)
def test_decision_filter_does_not_weaken_real_graph_guards(mutation, diagnostic):
    graph, languages = bibliography.load(CORPUS)
    selected = next(use for use in languages["en"]["uses"] if use["id"] == next(iter(LORETO)))
    reference = selected["legacy_refs"][0]
    if mutation == "duplicate":
        other = next(use for use in languages["en"]["uses"] if use["id"] != selected["id"])
        other.setdefault("legacy_refs", []).append(reference)
    elif mutation == "unknown":
        selected["legacy_refs"] = [reference.rsplit("/", 1)[0] + "/9999"]
    elif mutation == "foreign-package":
        languages["en"]["uses"].remove(selected)
        languages["pl"]["uses"].append(selected)
        languages["pl"]["uses"].sort(key=lambda use: use["id"])
    elif mutation == "mapped-and-removed":
        graph["migration"]["removals"].append({"legacy_ref": reference, "reason": "Unsupported."})
        graph["migration"]["removals"].sort(key=lambda row: row["legacy_ref"])
    else:
        selected["legacy_refs"] = []
    assert any(diagnostic in error for error in bibliography.validate(CORPUS, graph, languages))


@pytest.mark.parametrize("decision", ["REMOVE", "REPLACE", "UNVERIFIED_NO_DIRECT_EVIDENCE"])
def test_four_real_mapped_exclusions_reach_emitter_and_expected_view_without_remapping(decision):
    original_graph, original_languages = bibliography.load(CORPUS)
    original = copy.deepcopy((original_graph, original_languages))
    assert bibliography.validate(CORPUS, *original) == []
    original_parity = bibliography.parity(CORPUS, *original)
    text_id = "litaniae.lauretanae"
    doc, layers = store.load(CORPUS, text_id)
    original_projection = bibliography.ReaderCitationProjection(CORPUS, *original)
    consume_inventory(CORPUS, original_projection)
    assert original_projection.errors() == []
    original_table = Table()
    original_artifact = language_artifact(
        doc, layers["en"], original_table, projection=original_projection
    )
    original_evidence = bibliography.public_text_evidence(original[0], original[1]["en"])

    # Only this in-memory control baseline retains the four pointers. It does
    # not require or confer retained editorial decisions in the real graph.
    baseline_graph, baseline_languages = copy.deepcopy(original)
    selected = {use["id"]: use for use in baseline_languages["en"]["uses"] if use["id"] in LORETO}
    assert set(selected) == set(LORETO)
    for identifier, use in selected.items():
        segment = LORETO[identifier]
        index = 1 if segment == "s042" else 0
        assert use["legacy_refs"] == [
            f"languages/en/texts/litaniae/lauretanae.json#/segments/{segment}/translation_citations/{index}"
        ]
        use["decision"] = "RETAIN_WITH_CORRECTION"
        use["decision_reason"] = "Retained only in a publication-control test fixture."
    assert bibliography.validate(CORPUS, baseline_graph, baseline_languages) == []
    assert bibliography.parity(CORPUS, baseline_graph, baseline_languages) == original_parity
    baseline = bibliography.ReaderCitationProjection(CORPUS, baseline_graph, baseline_languages)
    consume_inventory(CORPUS, baseline)
    assert baseline.errors() == []
    baseline_artifact = language_artifact(doc, layers["en"], Table(), projection=baseline)
    baseline_sizes = {row["id"]: len(row.get("tc", [])) for row in baseline_artifact["seg"]}
    baseline_evidence = bibliography.public_text_evidence(baseline_graph, baseline_languages["en"])
    baseline_published = {
        entry["id"]
        for record in baseline_evidence["texts"]
        for group in record["source_groups"]
        for entry in group["entries"]
    }
    assert set(LORETO) <= baseline_published

    graph, languages = copy.deepcopy((baseline_graph, baseline_languages))
    for use in languages["en"]["uses"]:
        if use["id"] in LORETO:
            use["decision"] = decision
            use["decision_reason"] = "Withheld in a publication-control test fixture."
    assert bibliography.validate(CORPUS, graph, languages) == []
    assert bibliography.parity(CORPUS, graph, languages) == original_parity
    projection = bibliography.ReaderCitationProjection(CORPUS, graph, languages)
    consume_inventory(CORPUS, projection)
    assert projection.errors() == []
    assert projection.counts()["excluded"] == baseline.counts()["excluded"] + 4
    assert projection.counts()["kept"] == baseline.counts()["kept"] - 4
    assert projection.counts()["mapped"] == baseline.counts()["mapped"]
    assert projection.counts()["unresolved"] == baseline.counts()["unresolved"]
    parses, analyses, shared, local = Table(), Table(), Table(), Table()
    core = core_artifact(doc, store.core(CORPUS, text_id), parses, analyses, shared, projection)
    artifact = language_artifact(doc, layers["en"], local, projection=projection)
    _want_doc, want = _strip(doc, _project_glosses(doc, layers, projection))
    _got_doc, got = expand(core, artifact, parses.order, analyses.order, shared.order, local.order)
    assert got == want["en"]
    normalized = bibliography.public_text_evidence(graph, languages["en"])
    published = {
        entry["id"]
        for record in normalized["texts"]
        for group in record["source_groups"]
        for entry in group["entries"]
    }
    assert published == baseline_published - set(LORETO)
    for identifier, segment in LORETO.items():
        raw = layers["en"]["segments"][segment]["translation_citations"]
        row = next(row for row in artifact["seg"] if row["id"] == segment)
        assert baseline_sizes[segment] >= 1
        assert len(row.get("tc", [])) == baseline_sizes[segment] - 1
        injected = copy.deepcopy(artifact)
        bad_row = next(row for row in injected["seg"] if row["id"] == segment)
        bad_row["tc"] = local.intern_all(raw)
        _bad_doc, bad = expand(
            core, injected, parses.order, analyses.order, shared.order, local.order
        )
        assert bad != want["en"], identifier
    restored_graph, restored_languages = copy.deepcopy(original)
    assert (restored_graph, restored_languages) == original
    assert bibliography.validate(CORPUS, restored_graph, restored_languages) == []
    restored = bibliography.ReaderCitationProjection(CORPUS, restored_graph, restored_languages)
    consume_inventory(CORPUS, restored)
    restored_table = Table()
    restored_artifact = language_artifact(doc, layers["en"], restored_table, projection=restored)
    assert restored_artifact == original_artifact
    assert restored_table.edition() == original_table.edition()
    assert (
        bibliography.public_text_evidence(restored_graph, restored_languages["en"])
        == original_evidence
    )
    assert restored.counts() == original_projection.counts()
    assert restored.errors() == []
    assert bibliography.parity(CORPUS, restored_graph, restored_languages) == original_parity
    assert bibliography.load(CORPUS) == original
