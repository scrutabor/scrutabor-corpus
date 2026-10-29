"""The registration comparison keeps actual ordinary Agnus native inputs."""

import hashlib
import json
from pathlib import Path

import pytest
import test_main_ordo_registrations as registration
from requiem_successor_fixture import DATA, before_ordinary_agnus_core_bytes

from build_reader import bibliography
from build_reader.bibliography_bindings import digest
from checks.participation_performance import publication_errors

ROOT = Path(__file__).resolve().parents[1]


def test_ordinary_agnus_comparison_preserves_actual_native_input_and_recovers(monkeypatch):
    rule = DATA["ordinary_agnus_core"]
    raw = (ROOT / rule["relative"]).read_bytes()
    core = json.loads(raw)
    assert hashlib.sha256(raw).hexdigest() == rule["after_sha256"]
    assert publication_errors(core) == []
    graph, _ = bibliography.load(ROOT)
    row = next(row for row in registration.ROWS if row["text"] == rule["text"])
    assert row["core_sha256"] == rule["before_sha256"]
    original_native = registration.witness_subject
    native_seen = []

    def actual_source(*args, **kwargs):
        actual = args[3]
        assert digest(actual) == rule["after_canonical_sha256"]
        assert publication_errors(actual) == []
        assert all(
            segment["delivery"] == rule["delivery"]
            and segment["participation"]["cantu"]["performance"] == rule["performance"]
            for segment in actual["segments"]
            if segment["type"] == "verse"
        )
        native_seen.append(actual)
        return original_native(*args, **kwargs)

    monkeypatch.setattr(registration, "witness_subject", actual_source)
    original_registration = registration.assert_registered_payload(ROOT, graph, row)
    predecessor = before_ordinary_agnus_core_bytes(rule["text"], raw)
    assert hashlib.sha256(predecessor).hexdigest() == row["core_sha256"]
    assert publication_errors(core) == []
    faults = (
        ("word", b'"form": "Agnus"', b'"form": "Altered"', 3),
        ("lemma", b'"lemma": "agnus"', b'"lemma": "alienus"', 3),
        ("speaker", b'"speaker": "sacerdos"', b'"speaker": "minister"', 3),
        ("delivery", b'"voice": "secreto"', b'"voice": "clara"', 3),
        ("performance", b'"source": "DMS 25 b; 26"', b'"source": "Changed source"', 3),
        ("unrelated", b'"title": "Agnus Dei"', b'"title": "Changed title"', 1),
    )
    for kind, before, after, count in faults:
        assert raw.count(before) == count
        damaged = bytearray(raw.replace(before, after, 1))
        same_input = damaged
        assert bytes(damaged) != raw
        try:
            if kind in ("speaker", "delivery", "performance"):
                # Native validation receives the actual damaged current object.
                assert publication_errors(json.loads(damaged))
            with pytest.raises(AssertionError, match=r"^ordinary Agnus core successor$"):
                before_ordinary_agnus_core_bytes(rule["text"], bytes(damaged))
        finally:
            damaged[:] = raw
        assert damaged is same_input and bytes(damaged) == raw
        assert before_ordinary_agnus_core_bytes(rule["text"], bytes(damaged)) == predecessor
        assert publication_errors(json.loads(damaged)) == []
    assert registration.assert_registered_payload(ROOT, graph, row) == original_registration
    assert len(native_seen) == 2
    assert (ROOT / rule["relative"]).read_bytes() == raw
