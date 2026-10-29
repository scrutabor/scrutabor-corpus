"""Authored ownership through producer, independent reader and exact recovery."""

import copy
import json
from pathlib import Path

import pytest

from build_reader import commemorationes as reader
from build_reader import emit
from checks import commemorationes as checker
from kalendarium import commemorationes as producer
from kalendarium.dismissal import canonical_inputs

CORPUS = Path(__file__).resolve().parent.parent
OWNER = "sancta-petronilla"
TEXT = "proprium/sanctae-petronillae-secreta"


def slot(table, identity=OWNER):
    return next(
        part
        for entry in table["commemorations"]
        if entry["id"] == identity
        for part in entry["slots"]
        if part["key"] == "secreta"
    )


def test_resource_preserves_every_authored_slot_relation(reader_out):
    table = json.loads((reader_out / "commemorationes.json").read_text())
    expected = {
        (doc["id"], part["key"]): part["relation"]
        for path in sorted((CORPUS / "commemorationes").glob("*.json"))
        for doc in [json.loads(path.read_text())]
        for part in doc["slots"]
    }
    actual = {
        (entry["id"], part["key"]): part["relation"]
        for entry in table["commemorations"]
        for part in entry["slots"]
    }
    assert table["schema_version"] == "2.2.0"
    assert len(expected) == len(actual) == 96
    assert actual == expected
    assert slot(table)["relation"] == "proper"
    assert slot(table, "sancta-maria-magdalena-de-pazzis")["relation"] == "reference"
    assert slot(table, "sancta-monica")["relation"] == "reference"


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "null",
        "array",
        "unknown",
        "calendar-with-text",
        "proper-without-text",
        "reference-without-text",
    ],
)
def test_slot_relation_shape_is_required_and_restorable(reader_out, fault):
    table = json.loads((reader_out / "commemorationes.json").read_text())
    original = copy.deepcopy(table)
    target = slot(table)
    if fault == "missing":
        del target["relation"]
    elif fault == "null":
        target["relation"] = None
    elif fault == "array":
        target["relation"] = ["proper"]
    elif fault == "unknown":
        target["relation"] = "shared"
    elif fault == "calendar-with-text":
        target["relation"] = "calendar"
    else:
        target = slot(table, "dominica-impedita")
        target["relation"] = "proper" if fault == "proper-without-text" else "reference"
    with pytest.raises(ValueError, match="commemorationes"):
        producer.validate(table)
    table.clear()
    table.update(copy.deepcopy(original))
    producer.validate(table)
    assert table == original


def test_false_proper_relation_is_rejected_from_authored_source(monkeypatch):
    original = checker.documents(CORPUS)
    mutated = copy.deepcopy(original)
    doc = next(doc for _path, doc in mutated if doc["id"] == "sancta-maria-magdalena-de-pazzis")
    target = next(part for part in doc["slots"] if part["key"] == "secreta")
    assert target["text"] == TEXT.replace("/", ".", 1) and target["relation"] == "reference"
    target["relation"] = "proper"
    with monkeypatch.context() as patch:
        patch.setattr(checker, "documents", lambda corpus: copy.deepcopy(mutated))
        with pytest.raises(ValueError, match="proper relation must address"):
            producer.authored(CORPUS)
    assert checker.documents(CORPUS) == original
    assert producer.authored(CORPUS)


def test_independent_reader_rejects_producer_ownership_fault_and_recovers(reader_copy, monkeypatch):
    path = reader_copy / "commemorationes.json"
    original = path.read_bytes()
    manifest = json.loads((reader_copy / "manifest.json").read_text())
    assert reader.verify(CORPUS, reader_copy, manifest, emit.SCHEMA) == []
    forms, calendar = canonical_inputs(CORPUS)
    entries = producer.entries

    def false_owner(docs):
        result = entries(docs)
        # Still a valid typed shape: only the independent authored projection detects it.
        target = next(entry for entry in result if entry["id"] == OWNER)
        next(part for part in target["slots"] if part["key"] == "secreta")["relation"] = "reference"
        return result

    try:
        with monkeypatch.context() as patch:
            patch.setattr(producer, "entries", false_owner)
            broken = producer.calendar_table(forms, calendar, corpus=CORPUS)
            producer.validate(broken)
            path.write_text(json.dumps(broken, ensure_ascii=False))
            assert reader.verify(CORPUS, reader_copy, manifest, emit.SCHEMA) == [
                "commemorationes: resource differs from independent canonical reconstruction"
            ]
    finally:
        path.write_bytes(original)
    assert producer.calendar_table(forms, calendar, corpus=CORPUS) == json.loads(original)
    assert reader.verify(CORPUS, reader_copy, manifest, emit.SCHEMA) == []
    assert path.read_bytes() == original
