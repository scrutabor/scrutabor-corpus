"""Literal Mass data, declared correction and strict historical comparisons."""

import hashlib
import json
import shutil
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

import pytest
import witness_header_fixture as headers
from gospel_delivery_fixture import DATA as GOSPEL
from michael_gospel_source_fixture import (
    DATA as F,
)
from michael_gospel_source_fixture import (
    TEXT,
    assert_michael_transcript,
    before_michael_records,
    before_michael_registry,
)
from witness_header_fixture import TRANSCRIPTS

from build_reader import bibliography
from build_reader.bibliography_bindings import (
    BindingError,
    _SourceSnapshot,
    _witness_subject,
    collation_subject,
    digest,
    selected_text,
    validate_bindings,
    witness_subject,
)
from build_reader.layers import expand_core
from checks.collate import collate
from checks.raw_binding import BindingError as RawError
from checks.raw_binding import load_registry, resolve_binding
from checks.transcription import check_transcriptions

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = "witnesses/raw/bindings.json"
GRAPH = "bibliography/graph.json"


def record(graph, collection, identity):
    matches = [row for row in graph[collection] if row["id"] == identity]
    assert len(matches) == 1
    return matches[0]


def write_registry(state):
    (state["root"] / REGISTRY).write_text(
        json.dumps(state["registry"], ensure_ascii=False, indent=2) + "\n"
    )


@pytest.fixture
def source(tmp_path):
    graph = json.loads((ROOT / GRAPH).read_text())
    for field in ("uses", "witnesses", "collations"):
        graph[field] = [
            row
            for row in graph[field]
            if row.get("text", row.get("address", {}).get("text")) == TEXT
        ]
    for row in F["records"]:
        assert record(graph, row["collection"], row["id"]) == row["after"]
    current = load_registry(ROOT)
    registry = {
        "version": 1,
        "archives": {key: deepcopy(current["archives"][key]) for key in F["archives"]},
        "bindings": {F["binding_id"]: deepcopy(current["bindings"][F["binding_id"]])},
    }
    paths = [F["core"], F["witness"], F["mr"], F["apparatus_path"]]
    paths += [row["path"] for row in F["archives"].values()]
    for relative in paths:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, path)
    (tmp_path / REGISTRY).parent.mkdir(parents=True, exist_ok=True)
    state = dict(root=tmp_path, graph=graph, registry=registry, files=[*paths, REGISTRY])
    write_registry(state)
    return state


def current(state):
    root, graph = state["root"], state["graph"]
    assert load_registry(root) == state["registry"]
    assert state["registry"]["bindings"][F["binding_id"]] == F["binding"]
    assert "contract" not in F["binding"]  # Genuine default raw1, not a closed-profile trap.
    assert_michael_transcript(root)
    reading = resolve_binding(root / F["witness"], root)
    assert reading is not None and reading.text == F["literal"]
    assert reading.source == F["expected_source"], "complete literal Michael Mass source"
    assert reading.spans == ((root / F["archives"]["michael-apparition"]["path"], 36, 36),)
    assert len(reading.fragments) == 1
    fragment = reading.fragments[0]
    assert fragment.raw == fragment.text == F["literal"]
    assert fragment.line == 36 and fragment.start == 0 and fragment.end == len(F["literal"])
    assert fragment.whole_line and fragment.marker is None and fragment.marker_scope_verified
    assert fragment.binding_id == F["binding_id"] and fragment.framing == ()
    assert check_transcriptions(root / Path(F["witness"]).parent) == ([], 1)
    core = json.loads((root / F["core"]).read_text())
    assert core["editorial"]["source"]["method"] == F["method"]["after"]
    assert digest(selected_text(core)) == F["gospel_selected"]["after"]
    assert len(core["segments"][0]["words"]) == 196
    assert validate_bindings(root, graph) == []
    witness = next(row["after"] for row in F["records"] if row["collection"] == "witnesses")
    subject = witness_subject(root, record(graph, "witnesses", witness["id"]), graph, core)
    assert subject["contract"] == "witness-review-2"
    assert subject["raw_resolution"] == F["expected_source"]
    assert subject["source_uses"] == F["source_uses"]["after"]
    errors, warnings, stats = collate(expand_core(core), root / Path(F["witness"]).parent)
    assert errors == warnings == []
    assert stats["words"] == 196 and stats["witnesses"] == 2 and stats["corrigenda"] == 1
    assert stats["orthographic"] + stats["variants_adjudicated"] == 28
    return core, subject


@contextmanager
def recovery(state):
    graph, registry = state["graph"], state["registry"]
    saved_graph, saved_registry = deepcopy(graph), deepcopy(registry)
    saved_files = {name: (state["root"] / name).read_bytes() for name in state["files"]}
    try:
        yield
    finally:
        graph.clear()
        graph.update(saved_graph)
        registry.clear()
        registry.update(saved_registry)
        for name, raw in saved_files.items():
            (state["root"] / name).write_bytes(raw)
        assert state["graph"] is graph and state["registry"] is registry
        assert graph == saved_graph and registry == saved_registry
        assert all((state["root"] / name).read_bytes() == raw for name, raw in saved_files.items())
        current(state)


def test_full_current_source_precedes_all_comparison_copies(source):
    core, subject = current(source)
    raw = assert_michael_transcript(source["root"])
    assert F["witness"] not in TRANSCRIPTS and F["mr"] in TRANSCRIPTS
    assert len(TRANSCRIPTS) == 947
    body = "\n".join(line for line in raw.decode().splitlines() if not line.startswith("#"))
    assert body == F["literal"] and body.split()[139] == "niitti"
    assert F["literal"].count("niitti") == 1
    app = json.loads((source["root"] / F["apparatus_path"]).read_text())
    assert app == F["apparatus"]["after"] and app["summary"]["entries"] == 27
    assert not any(row["at"] == "w140" for row in app["adjudicated"])
    for key, archive in F["archives"].items():
        data = (source["root"] / archive["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == archive["sha256"]
        assert load_registry(ROOT)["archives"][key] == archive
    expected = before_michael_records(subject)
    assert expected["contract"] == "witness-identity-2" and "raw_resolution" not in expected
    assert expected["selected_text"] == selected_text(core)


RAW_FAULTS = {
    "marker": "marker and registered witness identity disagree",
    "revision": "witness revision differs",
    "path": "path declarations differ",
    "archive-hash": "SHA-256 mismatch",
    "heading": "source section does not match",
    "reference": "reference differs from source evidence",
    "reading-frame": "reading contains framing or lies outside textual evidence",
    "reading-duplicate": "reading omits or repeats source text",
    "boolean-line": "invalid source line range",
    "missing-plan": "marker and registered witness identity disagree",
    "body-normalized": "transcription differs from its exact ordered raw reading",
    "explicit-raw1": "unsupported per-binding contract",
}


@pytest.mark.parametrize("fault", list(RAW_FAULTS))
def test_real_raw1_failures_restore_the_same_objects(source, fault):
    current(source)
    root, registry = source["root"], source["registry"]
    path = root / F["witness"]
    old = path.read_text()
    with recovery(source):
        plan = registry["bindings"][F["binding_id"]]
        if fault == "marker":
            path.write_text(old.replace("# raw-binding: " + F["binding_id"] + "\n", "", 1))
        elif fault == "revision":
            path.write_text(old.replace(plan["revision"], "0" * 40, 1))
        elif fault == "path":
            path.write_text(old.replace("(lines 36-36)", "(lines 35-36)", 1))
        elif fault == "archive-hash":
            registry["archives"]["michael-apparition"]["sha256"] = "0" * 64
        elif fault == "heading":
            plan["evidence"][1]["section_line"] = 32
        elif fault == "reference":
            plan["references"][0]["text"] = "@Sancti/05-09"
        elif fault == "reading-frame":
            plan["reading"][0]["first"] = 35
        elif fault == "reading-duplicate":
            plan["reading"].append(deepcopy(plan["reading"][0]))
        elif fault == "boolean-line":
            plan["reading"][0]["first"] = True
        elif fault == "missing-plan":
            del registry["bindings"][F["binding_id"]]
        elif fault == "body-normalized":
            path.write_text(old.replace("habéntem niitti", "habéntem mitti", 1))
        else:
            plan["contract"] = "raw-reading-1"
        write_registry(source)
        assert path.read_text() != old or registry != {
            "version": 1,
            "archives": F["archives"],
            "bindings": {F["binding_id"]: F["binding"]},
        }
        with pytest.raises(RawError, match=RAW_FAULTS[fault]):
            resolve_binding(path, root)


@pytest.mark.parametrize("fault", ["missing", "stale-reading", "no-reason"])
def test_corrigendum_is_not_hidden_before_raw_validation(source, fault):
    core, _ = current(source)
    path = source["root"] / F["witness"]
    old = path.read_text()
    line = next(row for row in old.splitlines(True) if row.startswith("# corrigendum:"))
    replacement = {
        "missing": "",
        "stale-reading": line.replace("niitti ->", "nitti ->", 1),
        "no-reason": "# corrigendum: niitti -> mitti\n",
    }[fault]
    with recovery(source):
        path.write_text(old.replace(line, replacement, 1))
        actual = resolve_binding(path, source["root"])
        assert actual is not None and actual.text == F["literal"]
        errors, _, _ = collate(expand_core(core), path.parent)
        expected = (
            "SUBSTANTIVE divergence at word 140"
            if fault == "missing"
            else (
                "which this witness does not print"
                if fault == "stale-reading"
                else "carries no reason"
            )
        )
        assert any(expected in error for error in errors)


@pytest.mark.parametrize(
    "word", ["w007", "w011", "w015", "w018", "w041", "w051", "w054", "w085", "w187", "w195"]
)
def test_each_literal_orthography_ruling_is_required(source, word):
    core, _ = current(source)
    path = source["root"] / F["apparatus_path"]
    app = json.loads(path.read_text())
    target = next(row for row in app["adjudicated"] if row["at"] == word)
    assert target["class"] == "orthography"
    with recovery(source):
        app["adjudicated"].remove(target)
        path.write_text(json.dumps(app, ensure_ascii=False, indent=2) + "\n")
        errors, _, _ = collate(expand_core(core), path.parent)
        assert any(
            word in error and ("SUBSTANTIVE" in error or "UNADJUDICATED" in error)
            for error in errors
        )


def test_pending_raw1_inventory_absence_is_not_a_reviewable_subject(source):
    core, _ = current(source)
    witness = next(row for row in source["graph"]["witnesses"] if row["transcription"] == "do")
    with recovery(source):
        witness.pop("source_dependencies")
        assert validate_bindings(source["root"], source["graph"]) == []
        with pytest.raises(
            BindingError, match="complete explicit source_dependencies declaration required"
        ):
            witness_subject(source["root"], witness, source["graph"], core)


def test_reader_and_collation_keep_pending_distinct_from_resolution(source):
    core, subject = current(source)
    graph = source["graph"]
    mr = next(row for row in graph["witnesses"] if row["transcription"] == "mr")
    old_mr = json.loads((ROOT / GRAPH).read_text())
    assert mr == record(old_mr, "witnesses", mr["id"])
    with pytest.raises(
        BindingError, match="complete explicit source_dependencies declaration required"
    ):
        witness_subject(source["root"], mr, graph, core)
    subjects = {subject["witness"]["id"]: subject}
    subjects[mr["id"]] = _witness_subject(
        source["root"], mr, core, _SourceSnapshot(source["root"], graph), reviewable=False
    )
    with pytest.raises(
        BindingError, match="reviewable collation requires complete witness source inventories"
    ):
        collation_subject(source["root"], graph["collations"][0], core, subjects)
    assert all(
        row["review"] == {"status": "pending"} for row in graph["witnesses"] + graph["collations"]
    )
    public = next(
        row for row in bibliography.public_text_evidence(graph)["texts"] if row["id"] == TEXT
    )
    assert public["witnesses"] == [] and "collation" not in public
    entries = [entry for group in public["source_groups"] for entry in group["entries"]]
    expected = next(row["after"] for row in F["records"] if row["collection"] == "uses")
    assert next(row for row in entries if row["id"] == expected["id"])["claim"] == expected["claim"]
    assert "raw_resolution" not in json.dumps(public) and F["binding_id"] not in json.dumps(public)


@pytest.mark.parametrize("field", ["uses", "witnesses", "collations", "registry"])
@pytest.mark.parametrize("fault", ["missing", "wrong", "extra"])
def test_exact_comparison_guards_reject_then_restore_same_containers(source, field, fault):
    current(source)
    if field == "registry":
        original = before_michael_registry(source["registry"])
    else:
        original = before_michael_records(source["graph"])
    with recovery(source):
        if field == "registry":
            rows, key = source["registry"]["bindings"], F["binding_id"]
            if fault == "missing":
                del rows[key]
            else:
                rows[key]["revision" if fault == "wrong" else "extra"] = "control"
        else:
            rows = source["graph"][field]
            identity = next(row["id"] for row in F["records"] if row["collection"] == field)
            row = record(source["graph"], field, identity)
            if fault == "missing":
                rows.remove(row)
            else:
                row["claim" if fault == "wrong" else "extra"] = "control"
        with pytest.raises(AssertionError):
            if field == "registry":
                before_michael_registry(source["registry"])
            else:
                before_michael_records(source["graph"])
    restored = (
        before_michael_registry(source["registry"])
        if field == "registry"
        else before_michael_records(source["graph"])
    )
    assert restored == original


def test_office_label_cannot_borrow_the_literal_mass_source_approval(source):
    current(source)
    root = source["root"]
    path = root / F["witness"]
    with recovery(source):
        for archive in source["registry"]["archives"].values():
            archive["upstream"] = archive["upstream"].replace("web/www/missa/", "web/www/horas/", 1)
        path.write_text(path.read_text().replace("web/www/missa/", "web/www/horas/"))
        write_registry(source)
        actual = resolve_binding(path, root)
        assert actual is not None and actual.text == F["literal"]
        with pytest.raises(AssertionError, match="complete literal Michael Mass source"):
            assert actual.source == F["expected_source"], "complete literal Michael Mass source"


@pytest.mark.parametrize("view", ["current", "historical-sung"])
def test_real_witness_payloads_recover_both_unchanged_gospel_fixture_hashes(source, view):
    core, _ = current(source)
    doc = deepcopy(core)
    if view == "historical-sung":
        del doc["segments"][0]["delivery"]
    witness = next(row for row in source["graph"]["witnesses"] if row["transcription"] == "do")
    actual = _witness_subject(
        source["root"],
        witness,
        doc,
        _SourceSnapshot(source["root"], source["graph"]),
        reviewable=False,
    )
    snapshot = deepcopy(actual)
    comparison = headers.before_privacy(actual)
    expected = GOSPEL["witness_subjects"][witness["id"]]
    assert digest(comparison) == expected["after" if view == "current" else "before"]
    assert actual == snapshot and actual["contract"] == "witness-review-2"


@pytest.mark.parametrize("damage", ["header", "body", "normalized", "private-header"])
def test_dedicated_do_content_guard_never_invents_947_membership(source, damage):
    current(source)
    path = source["root"] / F["witness"]
    old = path.read_text()
    changed = {
        "header": "# note: unreviewed extra metadata\n" + old,
        "body": old.replace("Accessérunt", "accesserunt", 1),
        "normalized": old.replace("habéntem niitti", "habéntem mitti", 1),
        "private-header": "# local-archive: /private/source\n" + old,
    }[damage]
    with recovery(source):
        assert changed != old and F["witness"] not in TRANSCRIPTS
        path.write_text(changed)
        with pytest.raises(AssertionError, match="complete current Michael Gospel transcript"):
            assert_michael_transcript(source["root"])
