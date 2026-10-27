"""Two literal chant fragments retain boundaries, spelling and pending evidence."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from chant_fragment_fixture import ROWS, before_chant_graph, before_chant_registry

from build_reader.bibliography import public_text_evidence
from build_reader.bibliography_bindings import digest, validate_bindings, witness_subject
from build_reader.layers import expand_core
from checks import attribute
from checks.collate import collate
from checks.raw_binding import BindingError, resolve_binding
from checks.transcription import check_transcriptions
from checks.witness_archive import check as check_archives

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = "witnesses/raw/bindings.json"
RAW_FAULTS = (
    ("normalized", "transcription differs from its exact ordered raw reading"),
    ("section", "source section does not match evidence"),
    ("split", "fragment splits a source token"),
    ("marker", "fragment text, marker context or boundary reason differs"),
    ("repeat", "reading omits or repeats source text"),
    ("order", "reading reorders textual fragments"),
    ("neighbor", "reading contains framing or lies outside textual evidence"),
    ("archive", "SHA-256 mismatch"),
    ("header", "witness path declarations differ from bound evidence"),
    ("extra", "fragment: expected fields"),
)


def load(root, relative):
    return json.loads((root / relative).read_bytes())


def write(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (
        value
        if isinstance(value, bytes)
        else (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    )
    path.write_bytes(raw)


def record(graph, collection, identity):
    rows = [row for row in graph[collection] if row["id"] == identity]
    assert len(rows) == 1
    return rows[0]


def file_bytes(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.fixture(params=ROWS, ids=["thomas", "simon"])
def chant(tmp_path, request):
    row = request.param
    graph = load(ROOT, "bibliography/graph.json")
    graph["witnesses"] = [item for item in graph["witnesses"] if item["text"] == row["text"]]
    graph["collations"] = [item for item in graph["collations"] if item["text"] == row["text"]]
    paths = ["texts/" + row["text"].replace(".", "/", 1) + ".json", row["archive"]["path"]]
    paths += [
        "witnesses/" + row["text"] + "/" + name for name in ("do.txt", "mr.txt", "apparatus.json")
    ]
    for relative in paths:
        write(tmp_path, relative, (ROOT / relative).read_bytes())
    write(
        tmp_path,
        REGISTRY,
        dict(
            version=1,
            archives={row["archive_id"]: row["archive"]},
            bindings={row["binding_id"]: row["binding"]},
        ),
    )
    return tmp_path, graph, row


def healthy(state):
    root, graph, row = state
    witness_path = root / row["binding"]["witness"]
    assert witness_path.read_bytes() == row["transcript"]["after"].encode()
    reading = resolve_binding(witness_path, root)
    assert reading is not None and reading.text == row["literal_body"]
    assert reading.source == row["expected_source"]
    core = load(root, "texts/" + row["text"].replace(".", "/", 1) + ".json")
    witness = record(graph, "witnesses", row["witness"]["after"]["id"])
    assert witness == row["witness"]["after"] and witness["review"] == {"status": "pending"}
    assert witness_subject(root, witness, graph, core)["raw_resolution"] == reading.source
    assert validate_bindings(root, graph) == []
    errors, warnings, stats = collate(expand_core(core), witness_path.parent)
    assert errors == warnings == [] and stats["words"] == row["word_count"]
    assert check_transcriptions(witness_path.parent) == ([], 1)
    assert check_archives(root) == []
    return reading


def test_complete_literal_source_and_native_collation_remain_pending(chant):
    root, graph, row = chant
    healthy(chant)
    public = next(
        item for item in public_text_evidence(graph)["texts"] if item["id"] == row["text"]
    )
    assert public["witnesses"] == [] and "collation" not in public
    assert record(graph, "uses", row["use"]["after"]["id"]) == row["use"]["after"]
    assert (ROOT / row["binding"]["witness"]).read_bytes() == (
        root / row["binding"]["witness"]
    ).read_bytes()


@pytest.mark.parametrize("fault,message", RAW_FAULTS, ids=[row[0] for row in RAW_FAULTS])
def test_real_raw_consumers_reject_and_same_files_recover(chant, fault, message):
    root, _, row = chant
    expected = healthy(chant)
    saved = file_bytes(root)
    registry = load(root, REGISTRY)
    plan = registry["bindings"][row["binding_id"]]
    fragment = next(item for item in plan["evidence"] if "fragment" in item)
    witness = root / plan["witness"]
    try:
        if fault == "normalized":
            old_body = row["transcript"]["before"].splitlines()[-1]
            witness.write_bytes(
                witness.read_bytes().replace(row["literal_body"].encode(), old_body.encode(), 1)
            )
        elif fault == "section":
            plan["evidence"][0]["section"] = "Allelúia"
        elif fault == "split":
            fragment["fragment"]["start"] += 1
        elif fault == "marker":
            fragment["fragment"]["marker"] = None
        elif fault == "repeat":
            plan["reading"] *= 2
        elif fault == "order":
            plan["reading"].reverse()
        elif fault == "neighbor":
            item = next(item for item in plan["reading"] if "fragment" in item)
            if row["word_count"] == 17:
                item["fragment"]["end"] = 72
            else:
                item["fragment"]["start"] = 0
        elif fault == "archive":
            path = root / row["archive"]["path"]
            path.write_bytes(path.read_bytes() + b"\n")
        elif fault == "header":
            line = next(
                line
                for line in witness.read_bytes().splitlines(keepends=True)
                if line.startswith(b"# path: ")
            )
            witness.write_bytes(
                witness.read_bytes().replace(
                    line, line.replace(b"[Graduale]", "[Allelúia]".encode(), 1), 1
                )
            )
        else:
            fragment["fragment"]["extra"] = True
        write(root, REGISTRY, registry)
        assert file_bytes(root) != saved
        with pytest.raises(BindingError, match=message):
            resolve_binding(witness, root)
        errors, checked = check_transcriptions(witness.parent)
        assert errors and checked == 0 and check_archives(root)
    finally:
        for relative, raw in saved.items():
            write(root, relative, raw)
        assert file_bytes(root) == saved and healthy(chant) == expected


@pytest.mark.parametrize(
    "fault,message",
    [
        ("transcript-digest", "transcription_sha256 differs from the complete bound transcript"),
        ("evidence-digest", "digital evidence_sha256 identifies neither"),
        ("apparatus-raw-digest", "apparatus_sha256 differs from the complete apparatus"),
    ],
)
def test_actual_binding_validation_not_expected_inverse_rejects_and_recovers(chant, fault, message):
    root, graph, row = chant
    healthy(chant)
    saved = deepcopy(graph)
    try:
        if fault == "transcript-digest":
            record(graph, "witnesses", row["witness"]["after"]["id"])["transcription_sha256"] = (
                "0" * 64
            )
        elif fault == "evidence-digest":
            record(graph, "uses", row["use"]["after"]["id"])["evidence_sha256"] = "0" * 64
        else:
            raw = (root / "witnesses" / row["text"] / "apparatus.json").read_bytes()
            assert hashlib.sha256(raw).hexdigest() != digest(json.loads(raw))
            record(graph, "collations", row["collation"]["after"]["id"])["apparatus_sha256"] = (
                hashlib.sha256(raw).hexdigest()
            )
        assert graph != saved
        errors = validate_bindings(root, graph)
        assert errors and any(message in error for error in errors)
    finally:
        graph.clear()
        graph.update(saved)
        assert graph == saved
        healthy(chant)


def test_coherently_extended_neighbor_still_fails_actual_selected_text_collation(chant):
    root, _, row = chant
    healthy(chant)
    saved = file_bytes(root)
    registry = load(root, REGISTRY)
    plan = registry["bindings"][row["binding_id"]]
    evidence = next(item for item in plan["evidence"] if "fragment" in item)
    reading = next(item for item in plan["reading"] if "fragment" in item)
    lines = (root / row["archive"]["path"]).read_text().splitlines()
    fragment = evidence["fragment"]
    old_extent = f"chars {fragment['start']}:{fragment['end']}"
    try:
        fragment["start"], fragment["end"] = 0, len(lines[evidence["first"] - 1])
        fragment["text"] = lines[evidence["first"] - 1]
        reading["fragment"] = {key: fragment[key] for key in ("start", "end")}
        selected = []
        for item in plan["reading"]:
            text = lines[item["first"] - 1]
            if "fragment" in item:
                text = text[item["fragment"]["start"] : item["fragment"]["end"]]
            selected.append(text.removeprefix("V. "))
        body = " ".join(selected)
        assert body != row["literal_body"]
        path = root / plan["witness"]
        raw = path.read_text()
        line = next(line for line in raw.splitlines() if line.startswith("# path: "))
        changed = line.replace(old_extent, f"chars 0:{fragment['end']}")
        path.write_text(raw.replace(line, changed, 1).replace(row["literal_body"], body, 1))
        write(root, REGISTRY, registry)
        actual = resolve_binding(path, root)
        assert actual is not None and actual.text == body
        core = load(root, "texts/" + row["text"].replace(".", "/", 1) + ".json")
        errors, _, _ = collate(expand_core(core), path.parent)
        assert any("SUBSTANTIVE length mismatch" in error for error in errors)
    finally:
        for relative, raw in saved.items():
            write(root, relative, raw)
        assert file_bytes(root) == saved
        healthy(chant)


@pytest.mark.parametrize("fault", ["missing", "wrong", "duplicate"])
def test_real_collation_rejects_unaccounted_variants_and_same_apparatus_recovers(chant, fault):
    root, _, row = chant
    healthy(chant)
    path = root / "witnesses" / row["text"] / "apparatus.json"
    saved = path.read_bytes()
    app = json.loads(saved)
    try:
        if fault == "missing":
            app["adjudicated"].pop()
        elif fault == "wrong":
            app["adjudicated"][0]["witnesses"]["do"] += "x"
        else:
            app["adjudicated"].append(deepcopy(app["adjudicated"][0]))
        write(root, path.relative_to(root).as_posix(), app)
        core = load(root, "texts/" + row["text"].replace(".", "/", 1) + ".json")
        errors, _, _ = collate(expand_core(core), path.parent)
        assert errors
    finally:
        path.write_bytes(saved)
        assert path.read_bytes() == saved
        healthy(chant)


def test_two_exact_successors_restore_old_whole_objects_without_new_baselines():
    graph, registry = load(ROOT, "bibliography/graph.json"), load(ROOT, REGISTRY)
    saved_graph, saved_registry = deepcopy(graph), deepcopy(registry)
    expected_graph, expected_registry = deepcopy(graph), deepcopy(registry)
    for row in ROWS:
        del expected_registry["bindings"][row["binding_id"]]
        for collection, field in (
            ("uses", "use"),
            ("witnesses", "witness"),
            ("collations", "collation"),
        ):
            target = record(expected_graph, collection, row[field]["after"]["id"])
            target.clear()
            target.update(deepcopy(row[field]["before"]))
    assert before_chant_graph(graph) == expected_graph
    assert before_chant_registry(registry) == expected_registry
    assert graph == saved_graph and registry == saved_registry


@pytest.mark.parametrize("collection", ["graph", "registry"])
@pytest.mark.parametrize("fault", ["missing", "wrong", "extra"])
def test_exact_comparison_inverse_rejects_changed_records_and_same_objects_recover(
    collection, fault
):
    current = load(ROOT, "bibliography/graph.json" if collection == "graph" else REGISTRY)
    saved = deepcopy(current)
    check = before_chant_graph if collection == "graph" else before_chant_registry
    expected = check(current)
    row = ROWS[0]
    try:
        if collection == "graph":
            records = current["witnesses"]
            selected = record(current, "witnesses", row["witness"]["after"]["id"])
            if fault == "missing":
                records.remove(selected)
            else:
                selected["transcription_sha256" if fault == "wrong" else "extra"] = "0" * 64
        else:
            records = current["bindings"]
            if fault == "missing":
                del records[row["binding_id"]]
            else:
                records[row["binding_id"]]["revision" if fault == "wrong" else "extra"] = "0" * 40
        assert current != saved
        with pytest.raises(AssertionError, match="exact two-chant"):
            check(current)
    finally:
        current.clear()
        current.update(saved)
        assert current == saved and check(current) == expected


def test_midline_simon_fragment_does_not_invent_a_versicle_performer(tmp_path, monkeypatch):
    row = ROWS[1]
    relative = row["binding"]["witness"]
    write(tmp_path, relative, (ROOT / relative).read_bytes())
    write(tmp_path, row["archive"]["path"], (ROOT / row["archive"]["path"]).read_bytes())
    write(
        tmp_path,
        REGISTRY,
        dict(
            version=1,
            archives={row["archive_id"]: row["archive"]},
            bindings={row["binding_id"]: row["binding"]},
        ),
    )
    reading = resolve_binding(tmp_path / relative, tmp_path)
    assert reading is not None and reading.fragments[0].marker == "V"
    assert reading.fragments[0].marker_scope_verified is False
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    assert attribute.marked_lines(row["text"]) == []
    with pytest.raises(BindingError, match="partial or framed source evidence"):
        attribute.witness_ranges(row["text"])
