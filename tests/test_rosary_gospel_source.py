"""A direct Gospel comparison does not resolve an unpadded proper reference."""

import hashlib
import json
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

import pytest
from documentary_successor_fixture import before_additional_records, before_additional_registry
from lateran_epistle_source_fixture import before_lateran_graph, before_lateran_registry
from marian_gospel_fixture import predecessor_core
from rosary_gospel_source_fixture import (
    DATA,
    before_rosary_graph,
    before_rosary_records,
    before_rosary_registry,
)

from build_reader.bibliography import public_text_evidence
from build_reader.bibliography_bindings import digest, validate_bindings, witness_subject
from build_reader.layers import expand_core
from checks import attribute
from checks.collate import collate
from checks.raw_binding import BindingError, load_registry, resolve_binding

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = "witnesses/raw/bindings.json"


def write(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalized(value, root):
    if isinstance(value, Path):
        return value.relative_to(root).as_posix()
    if isinstance(value, dict):
        return {key: normalized(field, root) for key, field in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalized(field, root) for field in value]
    return value


@pytest.fixture
def source(tmp_path):
    graph = json.loads((ROOT / "bibliography/graph.json").read_bytes())
    for field in ("uses", "witnesses", "collations"):
        graph[field] = [
            row
            for row in graph[field]
            if row.get("text", row.get("address", {}).get("text")) == DATA["text"]
        ]
    current = json.loads((ROOT / REGISTRY).read_bytes())
    registry = {
        "version": 1,
        "archives": {DATA["archive_id"]: deepcopy(current["archives"][DATA["archive_id"]])},
        "bindings": {DATA["binding_id"]: deepcopy(current["bindings"][DATA["binding_id"]])},
    }
    paths = [DATA[key] for key in ("core", "witness", "mr", "apparatus")]
    paths.append(DATA["archive"]["path"])
    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    write(tmp_path, REGISTRY, registry)
    return {"root": tmp_path, "graph": graph, "registry": registry, "paths": [*paths, REGISTRY]}


def healthy(state):
    root, graph, registry = state["root"], state["graph"], state["registry"]
    assert registry["archives"][DATA["archive_id"]] == DATA["archive"], "literal source identity"
    assert registry["bindings"][DATA["binding_id"]] == DATA["binding"], "literal source plan"
    assert load_registry(root) == registry
    reading = resolve_binding(root / DATA["witness"], root)
    assert reading is not None
    assert normalized(asdict(reading), root) == DATA["expected_reading"]
    for row in DATA["records"]:
        assert [r for r in graph[row["collection"]] if r["id"] == row["id"]] == [row["after"]]
    doc = json.loads((root / DATA["core"]).read_bytes())
    assert digest(predecessor_core(doc)) == DATA["before_core_sha256"]
    assert (
        hashlib.sha256((root / DATA["mr"]).read_bytes()).hexdigest() == DATA["unchanged_mr_sha256"]
    )
    witness = next(row for row in graph["witnesses"] if row["transcription"] == "do")
    subject = witness_subject(root, witness, graph, doc)
    assert subject["contract"] == "witness-review-2"
    assert subject["raw_resolution"] == DATA["expected_source"]
    assert validate_bindings(root, graph) == []
    errors, warnings, stats = collate(expand_core(doc), root / "witnesses" / DATA["text"])
    assert errors == warnings == []
    assert stats["words"] == 189 and stats["witnesses"] == 2
    assert stats["variants_adjudicated"] + stats["orthographic"] == 25
    return reading, subject


@contextmanager
def recover(state):
    graph, registry = state["graph"], state["registry"]
    saved_graph, saved_registry = deepcopy(graph), deepcopy(registry)
    files = {path: (state["root"] / path).read_bytes() for path in state["paths"]}
    try:
        yield
    finally:
        graph.clear()
        graph.update(saved_graph)
        registry.clear()
        registry.update(saved_registry)
        for path, raw in files.items():
            (state["root"] / path).write_bytes(raw)
        assert state["graph"] is graph and state["registry"] is registry
        assert graph == saved_graph and registry == saved_registry
        assert all((state["root"] / path).read_bytes() == raw for path, raw in files.items())
        healthy(state)


def test_complete_literal_source_fragments_and_pending_reader_boundary(source, monkeypatch):
    reading, subject = healthy(source)
    root, graph = source["root"], source["graph"]
    raw = (root / DATA["archive"]["path"]).read_bytes()
    assert len(raw) == 2591 and hashlib.sha256(raw).hexdigest() == DATA["archive"]["sha256"]
    lines = raw.decode().splitlines()
    assert lines[29] == "[Evangelium]" and lines[32] == DATA["source_line"]
    assert lines[32][184:187] == " ¶ "
    assert reading.text == lines[32][:184] + " " + lines[32][187:]
    assert len(reading.text.split()) == 189 and reading.spans == ()
    assert all(fragment.marker is None for fragment in reading.fragments)
    monkeypatch.setattr(attribute, "CORPUS", root)
    actual = attribute._actor_sources(DATA["text"])
    assert actual.scope == "COMPOSITE_TEXT_ONLY" and actual.units == ()
    (public,) = [row for row in public_text_evidence(graph)["texts"] if row["id"] == DATA["text"]]
    assert public["witnesses"] == [] and "collation" not in public
    assert subject["witness"]["id"] not in json.dumps(public["witnesses"])
    assert all(
        row["review"] == {"status": "pending"} for row in graph["witnesses"] + graph["collations"]
    )


RAW_FAULTS = (
    ("archive-bytes", "SHA-256 mismatch"),
    ("archive-revision", "revision differs from binding"),
    ("section-line", "source section does not match evidence"),
    ("split-token", "fragment splits a source token"),
    ("fragment-text", "fragment text, marker context or boundary reason differs"),
    ("fragment-marker", "fragment text, marker context or boundary reason differs"),
    ("fragment-reason", "fragment text, marker context or boundary reason differs"),
    ("unpadded-path", "witness path declarations differ from bound evidence"),
    ("house-body", "transcription differs from its exact ordered raw reading"),
    ("omit", "reading omits or repeats source text"),
    ("repeat", "reading omits or repeats source text"),
    ("reverse", "reading reorders textual fragments"),
    ("duplicate-marker", "raw-binding marker and registered witness identity disagree"),
    ("missing-marker", "raw-binding marker and registered witness identity disagree"),
    ("raw1-paragraph", "transcription differs from its exact ordered raw reading"),
)


@pytest.mark.parametrize("fault,message", RAW_FAULTS, ids=[row[0] for row in RAW_FAULTS])
def test_real_raw_contract_rejects_then_recovers_same_source(source, fault, message):
    healthy(source)
    root, registry = source["root"], source["registry"]
    path = root / DATA["witness"]
    with recover(source):
        plan = registry["bindings"][DATA["binding_id"]]
        text = path.read_text()
        if fault == "archive-bytes":
            target = root / DATA["archive"]["path"]
            target.write_bytes(target.read_bytes() + b"\n")
        elif fault == "archive-revision":
            registry["archives"][DATA["archive_id"]]["revision"] = "0" * 40
        elif fault == "section-line":
            plan["evidence"][0]["section_line"] = 29
        elif fault == "split-token":
            plan["evidence"][0]["fragment"]["start"] = 1
        elif fault.startswith("fragment-"):
            fragment = plan["evidence"][0]["fragment"]
            keys = {
                "fragment-text": "text",
                "fragment-marker": "marker",
                "fragment-reason": "reason",
            }
            key = keys[fault]
            fragment[key] = {
                "fragment-text": "changed",
                "fragment-marker": "R",
                "fragment-reason": "",
            }[fault]
        elif fault == "unpadded-path":
            path.write_text(text.replace("Sancti/09-12.txt", "Sancti/9-12.txt"))
        elif fault == "house-body":
            path.write_text(text.replace("Missus est Angelus", "Missus est Ángelus", 1))
        elif fault == "omit":
            plan["reading"].pop()
        elif fault == "repeat":
            plan["reading"].append(deepcopy(plan["reading"][0]))
        elif fault == "reverse":
            plan["reading"].reverse()
        elif fault == "duplicate-marker":
            path.write_text("# raw-binding: " + DATA["binding_id"] + "\n" + text)
        elif fault == "missing-marker":
            path.write_text(text.replace("# raw-binding: " + DATA["binding_id"] + "\n", ""))
        else:
            plan.pop("contract")
            plan["evidence"] = [
                {key: field for key, field in plan["evidence"][0].items() if key != "fragment"}
            ]
            plan["reading"] = [
                {key: field for key, field in plan["reading"][0].items() if key != "fragment"}
            ]
            header = next(line for line in text.splitlines() if line.startswith("# path:"))
            declared = "# path: " + DATA["archive"]["upstream"] + " [Evangelium] (lines 33-33)"
            path.write_text(text.replace(header, declared))
        write(root, REGISTRY, registry)
        with pytest.raises(BindingError, match=message):
            resolve_binding(path, root)


@pytest.mark.parametrize("index", range(25))
def test_each_actual_apparatus_quote_is_required_then_recovers(source, index):
    healthy(source)
    root = source["root"]
    with recover(source):
        apparatus = json.loads((root / DATA["apparatus"]).read_bytes())
        removed = apparatus["adjudicated"].pop(index)
        assert removed == DATA["apparatus_after"]["adjudicated"][index]
        write(root, DATA["apparatus"], apparatus)
        doc = json.loads((root / DATA["core"]).read_bytes())
        errors, _, _ = collate(expand_core(doc), root / "witnesses" / DATA["text"])
        assert any(removed["at"] in error for error in errors)
        assert any(
            "apparatus_sha256 differs" in error
            for error in validate_bindings(root, source["graph"])
        )


def test_global_complete_comparison_inverses_keep_original_baselines():
    graph = json.loads((ROOT / "bibliography/graph.json").read_bytes())
    registry = json.loads((ROOT / REGISTRY).read_bytes())
    saved = deepcopy((graph, registry))
    assert (
        digest(before_rosary_graph(before_lateran_graph(before_additional_records(graph))))
        == DATA["prior_graph_sha256"]
    )
    assert (
        digest(
            before_rosary_registry(before_lateran_registry(before_additional_registry(registry)))
        )
        == DATA["prior_registry_sha256"]
    )
    assert (graph, registry) == saved


@pytest.mark.parametrize("collection", ["uses", "witnesses", "collations"])
def test_complete_record_inverse_rejects_unrelated_fields_and_recovers(source, collection):
    healthy(source)
    graph = source["graph"]
    before_rosary_graph(graph)
    with recover(source):
        rule = next(row for row in DATA["records"] if row["collection"] == collection)
        row = next(row for row in graph[collection] if row["id"] == rule["id"])
        row["extra"] = True
        with pytest.raises(AssertionError, match=r"^complete Rosary graph record(?:\n|$)"):
            before_rosary_graph(graph)


@pytest.mark.parametrize("field", ["archives", "bindings"])
def test_complete_registry_inverse_rejects_new_field_drift_then_recovers(source, field):
    healthy(source)
    registry = source["registry"]
    before_rosary_registry(registry)
    with recover(source):
        identity = DATA["archive_id"] if field == "archives" else DATA["binding_id"]
        registry[field][identity]["extra"] = True
        with pytest.raises(AssertionError, match=r"^exact Rosary registry addition(?:\n|$)"):
            before_rosary_registry(registry)


@pytest.mark.parametrize("field", ["contract", "raw_resolution", "source_uses"])
def test_subject_comparison_does_not_discard_unverified_new_fields(source, field):
    _, subject = healthy(source)
    saved = deepcopy(subject)
    before_rosary_records(subject)
    try:
        subject[field] = {} if field != "contract" else "witness-identity-2"
        assert subject != saved
        with pytest.raises(AssertionError):
            before_rosary_records(subject)
    finally:
        subject.clear()
        subject.update(saved)
    assert subject == saved
    before_rosary_records(subject)


@pytest.mark.parametrize(
    "fault",
    ["paragraph", "reason", "wrong-office", "false-reference", "method", "latin", "review", "mr"],
)
def test_literal_scope_controls_reject_then_restore(source, fault):
    # These are exact source/claim controls, not claims that generic raw2 can
    # independently recognize a feast or adjudicate the omitted paragraph sign.
    healthy(source)
    root, graph, registry = source["root"], source["graph"], source["registry"]
    with recover(source):
        if fault == "paragraph":
            path = root / DATA["archive"]["path"]
            changed = path.read_bytes().replace(" ¶ ".encode(), b" + ", 1)
            path.write_bytes(changed)
            registry["archives"][DATA["archive_id"]]["sha256"] = hashlib.sha256(changed).hexdigest()
            write(root, REGISTRY, registry)
        elif fault == "reason":
            fragment = registry["bindings"][DATA["binding_id"]]["evidence"][0]["fragment"]
            fragment["reason"] += " Changed."
            write(root, REGISTRY, registry)
        elif fault == "wrong-office":
            next(row for row in graph["uses"] if row["id"].endswith(".do44667ff"))["claim"] = (
                "The Rosary proper reference resolves exactly to this selected Mass."
            )
        elif fault == "false-reference":
            registry["bindings"][DATA["binding_id"]]["references"].append({"padded": True})
            write(root, REGISTRY, registry)
        elif fault in {"method", "latin"}:
            doc = json.loads((root / DATA["core"]).read_bytes())
            if fault == "method":
                doc["editorial"]["source"]["method"] = "The original reference was resolved."
            else:
                doc["segments"][0]["words"][0]["form"] = "changed"
            write(root, DATA["core"], doc)
        elif fault == "review":
            next(row for row in graph["witnesses"] if row["transcription"] == "do")["review"] = {
                "status": "reviewed",
                "sha256": "0" * 64,
            }
        else:
            path = root / DATA["mr"]
            path.write_bytes(path.read_bytes() + b"\n")
        with pytest.raises(AssertionError):
            healthy(source)
