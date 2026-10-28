"""Complete current provenance rows precede their exact historical comparisons."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from documentary_successor_fixture import (
    DATA,
    LEDGER_FRAMES,
    before_language_successors,
    predecessor_ledger,
)
from lauda_sion_fixture import FIXTURE as LAUDA
from lauda_sion_fixture import current as lauda_current

from build_reader import store
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_current_rows_reject_each_changed_field_and_recover_same_container(language):
    relative = f"languages/{language}/translation-provenance.json"
    value = json.loads((ROOT / relative).read_bytes())
    snapshot = deepcopy(value)
    healthy = before_language_successors(relative, value)
    for change in DATA["ledgers"][relative]["rows"]:
        (row,) = [r for r in value["sites"] if r["site"] == change["after"]["site"]]
        core = store.core(ROOT, row["text"])
        layer = store.raw_layer(ROOT, language, row["text"])
        assert language_packs.check_core(core) == []
        assert (
            language_packs.check_layer(core, layer, store.layer_path(ROOT, language, row["text"]))
            == []
        )
        assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
        (segment,) = [s for s in core["segments"] if s["id"] == row["segment"]]
        assert row == change["after"]
        assert row["source_sha256"] == canonical_hash(source_payload(segment))
        assert row["target_sha256"] == canonical_hash(
            layer["segments"][row["segment"]]["translation"]
        )
        saved = deepcopy(row)
        for field in ("source_sha256", "target_sha256", "unexpected"):
            try:
                row[field] = "0" * 64
                assert row != saved
                with pytest.raises(AssertionError, match=r"^exact Joachim target successor$"):
                    before_language_successors(relative, value)
            finally:
                row.clear()
                row.update(saved)
            assert any(r is row for r in value["sites"])
            assert value == snapshot
            assert before_language_successors(relative, value) == healthy


LAUDA_LEDGER_FAULTS = ("source", "target", "origin", "review", "familiar", "extra")
LAUDA_LEDGER_CASES = [
    (row["site"], fault) for row in LAUDA["ledger"] for fault in LAUDA_LEDGER_FAULTS
]


def lauda_ledger_subject(language):
    core = store.core(ROOT, LAUDA["text"])
    layer = store.raw_layer(ROOT, language, LAUDA["text"])
    lauda_current(core, layer)
    relative = f"languages/{language}/translation-provenance.json"
    value = json.loads((ROOT / relative).read_bytes())
    for change in LAUDA["ledger"]:
        if change["after"]["language"] != language:
            continue
        (row,) = [r for r in value["sites"] if r["site"] == change["site"]]
        (segment,) = [s for s in core["segments"] if s["id"] == row["segment"]]
        assert row == change["after"]
        assert row["source_sha256"] == canonical_hash(source_payload(segment))
        assert row["target_sha256"] == canonical_hash(
            layer["segments"][row["segment"]]["translation"]
        )
    return relative, value


@pytest.mark.parametrize(
    "site,fault",
    LAUDA_LEDGER_CASES,
    ids=[f"{site}-{fault}" for site, fault in LAUDA_LEDGER_CASES],
)
def test_lauda_current_rows_reject_drift_and_recover_same_container(site, fault):
    relative, value = lauda_ledger_subject(site.rsplit(".", 1)[1])
    snapshot = deepcopy(value)
    healthy = predecessor_ledger(relative, value)
    assert healthy is not value and value == snapshot
    assert canonical_hash(healthy) == DATA["ledgers"][relative]["after_sha256"]
    (row,) = [r for r in value["sites"] if r["site"] == site]
    saved = deepcopy(row)
    try:
        if fault in ("source", "target"):
            row[f"{fault}_sha256"] = "0" * 64
        elif fault == "origin":
            row["origin"] = "own"
        elif fault == "review":
            row["review"] = "internally-reviewed"
        elif fault == "familiar":
            row["familiar_core"] = not row["familiar_core"]
        else:
            assert fault == "extra" and "unexpected" not in row
            row["unexpected"] = "unexpected"
        assert row != saved
        with pytest.raises(AssertionError, match=r"^Lauda current ledger(?:\n|$)"):
            predecessor_ledger(relative, value)
    finally:
        row.clear()
        row.update(saved)
    assert any(r is row for r in value["sites"])
    assert value == snapshot
    assert predecessor_ledger(relative, value) == healthy


@pytest.mark.parametrize("language", ["pl", "en"])
def test_lauda_ledger_rejects_unrelated_drift_and_recovers_same_container(language):
    relative, value = lauda_ledger_subject(language)
    snapshot = deepcopy(value)
    healthy = predecessor_ledger(relative, value)
    assert canonical_hash(healthy) == LEDGER_FRAMES[relative]["before"]
    saved = value["status"]
    try:
        value["status"] = "unexpected-status"
        assert value != snapshot
        with pytest.raises(AssertionError, match=r"^Lauda current ledger(?:\n|$)"):
            predecessor_ledger(relative, value)
    finally:
        value["status"] = saved
    assert value == snapshot
    assert predecessor_ledger(relative, value) == healthy
