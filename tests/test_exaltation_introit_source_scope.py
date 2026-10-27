"""Printed proper scope and declared expansions retain exact pending identities."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
import witness_header_fixture as headers
from chant_fragment_fixture import before_chant_graph

from build_reader import bibliography, store
from build_reader import bibliography_bindings as bindings

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "tests/fixtures/exaltation-introit-source-scope.json").read_text())


def graph_data():
    return json.loads((ROOT / "bibliography/graph.json").read_text())


def record(graph, field, identifier):
    rows = [row for row in graph[field] if row["id"] == identifier]
    assert len(rows) == 1
    return rows[0]


def exact_scope(graph):
    witness = record(graph, "witnesses", DATA["witness"]["after"]["id"])
    assert witness == DATA["witness"]["after"], "exact declared source scope"
    primary = DATA["primary_use"]
    assert record(graph, "uses", primary["after"]["id"]) == primary["after"], (
        "exact declared source scope"
    )
    for use in DATA["added_uses"]:
        assert record(graph, "uses", use["id"]) == use, "exact declared source scope"
    assert record(graph, "collations", DATA["collation"]["id"]) == DATA["collation"]
    comparison = before_chant_graph(headers.before_joachim_records(graph))
    for use in DATA["added_uses"]:
        comparison["uses"].remove(use)
    before = record(comparison, "uses", primary["before"]["id"])
    before.clear()
    before.update(deepcopy(primary["before"]))
    before = record(comparison, "witnesses", DATA["witness"]["before"]["id"])
    before.clear()
    before.update(deepcopy(DATA["witness"]["before"]))
    assert bindings.digest(comparison) == DATA["before_graph_sha256"], (
        "unchanged complete source graph remainder"
    )
    return witness


def healthy(graph):
    witness = exact_scope(graph)
    core = store.core(ROOT, DATA["text"])
    assert bindings.digest(core) == DATA["core_sha256"]
    subject = bindings.witness_subject(ROOT, witness, graph, core)
    assert subject == DATA["expected_source_subject"]
    assert witness["review"] == DATA["collation"]["review"] == {"status": "pending"}
    headers.assert_transcript_content(ROOT, DATA["relative"])
    apparatus = json.loads((ROOT / "witnesses" / DATA["text"] / "apparatus.json").read_text())
    assert apparatus == DATA["apparatus"]
    assert len(apparatus["adjudicated"]) == 6
    assert bindings.digest(apparatus) == DATA["collation"]["apparatus_sha256"]
    return subject


def test_complete_real_source_subject_body_apparatus_and_historical_fixture_are_exact():
    graph = graph_data()
    saved = deepcopy(graph)
    healthy(graph)
    assert graph == saved
    raw = (ROOT / "tests/fixtures/witness-header-successors.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == DATA["privacy_fixture_sha256"]
    assert len(headers.TRANSCRIPTS) == 947 and len(headers.REVIEWS) == 34
    rule = headers.TRANSCRIPTS[DATA["relative"]]
    assert (
        headers.expected_transcript(DATA["relative"], rule["before_sha256"])
        == (DATA["header"]["before_sha256"])
    )
    current = record(graph, "witnesses", DATA["witness"]["after"]["id"])
    saved = deepcopy(current)
    historical = headers.before_privacy(current)
    assert current == saved and historical is not current
    assert historical["transcription_sha256"] == rule["before_sha256"]
    assert (
        bindings.digest({k: v for k, v in historical.items() if k != "review"})
        == (rule["before_identity_sha256"])
    )


@pytest.mark.parametrize("fault", ["orthography", "expansion-note", "extra-header", "body"])
def test_actual_qualified_transcript_fault_rejects_and_same_file_recovers(tmp_path, fault):
    path = tmp_path / DATA["relative"]
    path.parent.mkdir(parents=True)
    saved = (ROOT / DATA["relative"]).read_bytes()
    path.write_bytes(saved)
    headers.assert_transcript_content(tmp_path, DATA["relative"])
    try:
        if fault == "orthography":
            changed = saved.replace(
                DATA["header"]["after_line"].encode(), DATA["header"]["before_line"].encode(), 1
            )
        elif fault == "expansion-note":
            changed = saved.replace(DATA["header"]["added_line"].encode(), b"", 1)
        elif fault == "extra-header":
            changed = b"# note: unrelated added metadata\n" + saved
        else:
            changed = saved.replace(b"Nos autem", b"Vos autem", 1)
        assert changed != saved
        path.write_bytes(changed)
        with pytest.raises(AssertionError, match="Exaltation transcript"):
            headers.assert_transcript_content(tmp_path, DATA["relative"])
    finally:
        path.write_bytes(saved)
        assert path.read_bytes() == saved
        headers.assert_transcript_content(tmp_path, DATA["relative"])
    assert (ROOT / DATA["relative"]).read_bytes() == saved


@pytest.mark.parametrize("fault", ["digest", "profile", "basis", "dependency", "review"])
def test_exact_expected_side_witness_inverse_rejects_and_same_record_recovers(fault):
    graph = graph_data()
    current = record(graph, "witnesses", DATA["witness"]["after"]["id"])
    saved = deepcopy(current)
    healthy(graph)
    historical = headers.before_privacy(current)
    try:
        if fault == "digest":
            current["transcription_sha256"] = "0" * 64
        elif fault == "profile":
            current["orthography_profile"] = "exact-page-image"
        elif fault == "basis":
            current["independence_basis"] = DATA["witness"]["before"]["independence_basis"]
        elif fault == "dependency":
            current["source_dependencies"]["uses"].pop()
        else:
            current["review"] = {"status": "reviewed", "sha256": "0" * 64}
        assert current != saved
        with pytest.raises(AssertionError, match="exact Exaltation comparison inverse"):
            headers.before_privacy(current)
    finally:
        current.clear()
        current.update(saved)
        assert current == saved
        assert headers.before_privacy(current) == historical
        healthy(graph)


@pytest.mark.parametrize("fault", ["unknown-use", "duplicate-use", "foreign-edition", "digest"])
def test_real_binding_fault_is_not_hidden_by_expected_side_inverse_and_recovers(fault):
    graph = graph_data()
    saved = deepcopy(graph)
    healthy(graph)
    witness = record(graph, "witnesses", DATA["witness"]["after"]["id"])
    try:
        if fault == "unknown-use":
            witness["source_dependencies"]["uses"][-1] += ".foreign"
            diagnostic = "unknown source use"
        elif fault == "duplicate-use":
            witness["source_dependencies"]["uses"].append(witness["source_dependencies"]["uses"][0])
            diagnostic = "supplemental uses must be sorted unique"
        elif fault == "foreign-edition":
            use = record(graph, "uses", DATA["added_uses"][0]["id"])
            other = next(
                item
                for item in graph["digital_items"]
                if item["edition"] != use["edition"] and item["kind"] == "scan"
            )
            use["edition"], use["digital_item"] = other["edition"], other["id"]
            diagnostic = "supplemental source belongs to another edition"
        else:
            witness["transcription_sha256"] = "0" * 64
            diagnostic = "transcription_sha256 differs from the complete bound transcript"
        assert graph != saved
        with pytest.raises(bindings.BindingError, match=diagnostic):
            bindings.witness_subject(ROOT, witness, graph, store.core(ROOT, DATA["text"]))
    finally:
        graph.clear()
        graph.update(saved)
        assert graph == saved
        healthy(graph)


@pytest.mark.parametrize("fault", ["claim", "locator", "evidence", "unrelated"])
def test_complete_scope_and_outside_graph_guards_reject_then_same_graph_recovers(fault):
    graph = graph_data()
    saved = deepcopy(graph)
    healthy(graph)
    try:
        if fault == "unrelated":
            graph["uses"][0]["claim"] += " Changed."
            diagnostic = "unchanged complete source graph remainder"
        else:
            use = record(graph, "uses", DATA["added_uses"][0]["id"])
            if fault == "claim":
                use["claim"] = "The proper page prints the complete expanded text."
            elif fault == "locator":
                use["locator"]["section"] = "Unspecified expansion"
            else:
                use["evidence_sha256"] = "0" * 64
            diagnostic = "exact declared source scope"
        assert graph != saved
        with pytest.raises(AssertionError, match=diagnostic):
            exact_scope(graph)
    finally:
        graph.clear()
        graph.update(saved)
        assert graph == saved
        healthy(graph)


def test_real_public_projection_includes_bounded_claims_but_withholds_pending_reviews():
    graph = graph_data()
    healthy(graph)
    evidence = bibliography.public_text_evidence(graph)
    text = next(row for row in evidence["texts"] if row["id"] == DATA["text"])
    entries = [entry for group in text["source_groups"] for entry in group["entries"]]
    for use in [DATA["primary_use"]["after"], *DATA["added_uses"]]:
        projected = next(entry for entry in entries if entry["id"] == use["id"])
        assert projected["claim"] == use["claim"]
        assert projected["address"] == {k: v for k, v in use["address"].items() if k != "text"}
    assert text["witnesses"] == [] and "collation" not in text
