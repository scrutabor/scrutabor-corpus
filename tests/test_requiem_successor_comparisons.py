"""Real current inputs precede finite historical comparison-copy inverses."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from documentary_successor_fixture import before_agency_ledger, before_language_successors
from lent_easter_successor_fixture import before_lent_easter_bytes, before_lent_easter_ledger
from polish_reader_successor_fixture import before_polish_reader_bytes, before_polish_reader_ledger
from prayer_prose_successor_fixture import AFTER, BEFORE, before_prayer_prose_ledger
from requiem_successor_fixture import (
    DATA,
    before_requiem_bytes,
    before_requiem_graph,
    before_requiem_ledger,
)

from build_reader import bibliography
from build_reader.bibliography_bindings import digest
from checks import translation_provenance

ROOT = Path(__file__).resolve().parents[1]
RAW_INPUTS = tuple(DATA["raw"])
LEDGER_FAULTS = (
    "added-row",
    "ordinary-source",
    "ordinary-review",
    "familiar",
    "unrelated-row",
    "missing-added-row",
    "duplicate-added-row",
    "top-level-extra",
)
GRAPH_CASES = [
    (collection, fault)
    for collection in ("uses", "witnesses", "collations")
    for fault in ("missing", "wrong", "extra", "order")
]


def restore(value, saved):
    value.clear()
    value.update(deepcopy(saved))


def ledger(language):
    relative = f"languages/{language}/translation-provenance.json"
    return relative, json.loads((ROOT / relative).read_bytes())


def test_real_current_inputs_validate_before_any_comparison_inverse():
    graph, languages = bibliography.load(ROOT)
    saved = deepcopy((graph, languages))
    assert bibliography.validate(ROOT, graph, languages) == []
    assert translation_provenance.check(ROOT)[0] == []
    assert digest(graph) == DATA["graph_frames"]["after"]
    comparison = before_requiem_graph(graph)
    assert digest(comparison) == DATA["graph_frames"]["before"]
    assert (graph, languages) == saved and comparison is not graph


@pytest.mark.parametrize("language", ["pl", "en"])
def test_direct_and_documentary_ledger_entries_share_the_same_exact_successor(language):
    relative, actual = ledger(language)
    saved = deepcopy(actual)
    current = before_requiem_ledger(relative, actual)
    assert (
        digest(before_lent_easter_ledger(relative, before_polish_reader_ledger(relative, actual)))
        == (DATA["ledgers"][relative]["after_sha256"])
    )
    assert digest(current) == AFTER[language]
    assert digest(before_prayer_prose_ledger(relative, actual)) == BEFORE[language]
    assert before_agency_ledger(relative, actual) is not actual
    assert before_language_successors(relative, actual) is not actual
    assert actual == saved and current is not actual
    assert len(actual["sites"]) - len(current["sites"]) == 7


@pytest.mark.parametrize("relative", RAW_INPUTS)
def test_four_exact_raw_inverses_keep_every_prior_byte_and_current_input(relative):
    raw = (ROOT / relative).read_bytes()
    comparison = before_requiem_bytes(relative, raw)
    assert (
        hashlib.sha256(
            before_lent_easter_bytes(relative, before_polish_reader_bytes(relative, raw))
        ).hexdigest()
        == (DATA["raw"][relative]["after_sha256"])
    )
    assert hashlib.sha256(comparison).hexdigest() == DATA["raw"][relative]["before_sha256"]
    assert raw == (ROOT / relative).read_bytes() and comparison != raw
    with pytest.raises(AssertionError, match=r"^exact Requiem comparison bytes$"):
        before_requiem_bytes(relative, raw + b" ")
    assert before_requiem_bytes(relative, raw) == comparison


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("fault", LEDGER_FAULTS)
def test_complete_ledger_guard_rejects_drift_and_recovers_same_input(language, fault):
    relative, actual = ledger(language)
    saved = deepcopy(actual)
    expected = before_requiem_ledger(relative, actual)
    rule = DATA["ledgers"][relative]
    added = actual["sites"][rule["added"][0]["index"]]
    ordinary = actual["sites"][rule["changed"][0]["index_after"]]
    try:
        if fault == "added-row":
            added["target_sha256"] = "0" * 64
        elif fault == "ordinary-source":
            ordinary["source_sha256"] = "0" * 64
        elif fault == "ordinary-review":
            ordinary["review"] = "internally-reviewed"
        elif fault == "familiar":
            selected = next(
                (c for c in rule["changed"] if c["changed_fields"] == ["familiar_core"]), None
            )
            row = actual["sites"][selected["index_after"]] if selected else added
            row["familiar_core"] = not row["familiar_core"]
        elif fault == "unrelated-row":
            actual["sites"][0]["unexpected"] = True
        elif fault == "missing-added-row":
            actual["sites"].pop()
        elif fault == "duplicate-added-row":
            actual["sites"].append(deepcopy(added))
        else:
            assert fault == "top-level-extra"
            actual["unexpected"] = True
        assert actual != saved
        # The inherited label must survive both direct and documentary entries.
        for entry in (before_prayer_prose_ledger, before_language_successors):
            with pytest.raises(AssertionError, match=r"^inherited comparison diagnostic$"):
                entry(relative, actual, "inherited comparison diagnostic")
    finally:
        restore(actual, saved)
    assert actual == saved
    assert before_requiem_ledger(relative, actual) == expected


@pytest.mark.parametrize("collection,fault", GRAPH_CASES)
def test_exact_new_graph_membership_fields_and_order_reject_then_recover(collection, fault):
    graph = json.loads((ROOT / "bibliography/graph.json").read_bytes())
    saved = deepcopy(graph)
    expected = before_requiem_graph(graph)
    case = DATA["graph"][collection][0]
    rows, index = graph[collection], case["index"]
    try:
        if fault == "missing":
            rows.pop(index)
        elif fault == "wrong":
            rows[index]["id"] += ".foreign"
        elif fault == "extra":
            rows[index]["unexpected"] = True
        else:
            assert fault == "order"
            rows[index], rows[index + 1] = rows[index + 1], rows[index]
        assert graph != saved
        with pytest.raises(AssertionError, match=r"^exact Requiem graph additions$"):
            before_requiem_graph(graph)
    finally:
        restore(graph, saved)
    assert graph == saved and before_requiem_graph(graph) == expected


def test_unrelated_graph_fault_survives_comparison_and_public_validator_rejects_it():
    graph, languages = bibliography.load(ROOT)
    saved = deepcopy(graph)
    row = graph["uses"][0]
    original = deepcopy(row)
    try:
        row["edition"] = "unknown-existing-edition-control"
        # The public validator sees the same damaged current object first.
        assert any(
            "unknown-existing-edition-control" in error
            for error in bibliography.validate(ROOT, graph, languages)
        )
        comparison = before_requiem_graph(graph)
        assert comparison["uses"][0] == row
        assert digest(comparison) != DATA["graph_frames"]["before"]
        assert graph != saved
    finally:
        restore(row, original)
    assert graph == saved and any(value is row for value in graph["uses"])
    assert bibliography.validate(ROOT, graph, languages) == []


def test_new_graph_fault_reaches_public_validator_before_comparison_rejects_it():
    graph, languages = bibliography.load(ROOT)
    saved = deepcopy(graph)
    index = DATA["graph"]["uses"][0]["index"]
    row = graph["uses"][index]
    original = deepcopy(row)
    try:
        row["edition"] = "unknown-new-edition-control"
        assert any(
            "unknown-new-edition-control" in error
            for error in bibliography.validate(ROOT, graph, languages)
        )
        assert graph["uses"][index] is row and graph != saved
        with pytest.raises(AssertionError, match=r"^exact Requiem graph additions$"):
            before_requiem_graph(graph)
    finally:
        restore(row, original)
    assert graph == saved and graph["uses"][index] is row
    assert bibliography.validate(ROOT, graph, languages) == []


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("field", ["source_sha256", "target_sha256", "familiar_core"])
def test_native_provenance_receives_original_damaged_row_and_recovers(language, field, monkeypatch):
    recorded, errors = translation_provenance.load(ROOT)
    assert errors == []
    relative = f"languages/{language}/translation-provenance.json"
    site = DATA["ledgers"][relative]["added"][0]["row"]["site"]
    row = recorded[site]
    original = deepcopy(row)
    calls = []

    def actual_recorded_input(corpus):
        assert corpus == ROOT
        calls.append(recorded)
        return recorded, []

    # Inject the actual loaded row without any comparison inverse. All current
    # source/target expectations are still read through the normal corpus API.
    monkeypatch.setattr(translation_provenance, "load", actual_recorded_input)
    assert translation_provenance.check(ROOT)[0] == []
    try:
        row[field] = not row[field] if field == "familiar_core" else "0" * 64
        messages, _ = translation_provenance.check(ROOT)
        assert any(site in message and field in message for message in messages)
        assert calls[-1] is recorded and recorded[site] is row and row != original
    finally:
        restore(row, original)
    assert row == original and recorded[site] is row
    assert translation_provenance.check(ROOT)[0] == []
