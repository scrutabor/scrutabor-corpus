"""Real literal-source registrations preserve history and remain pending."""

import hashlib
import json
import shutil
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

import pytest
from chant_fragment_fixture import before_chant_graph, before_chant_registry
from lateran_epistle_source_fixture import before_lateran_graph, before_lateran_registry
from offertory_rubric_successor_fixture import before_offertory_core_bytes
from pater_agnus_successor_fixture import before_pater_agnus_core_bytes
from perceptio_purpose_successor_fixture import before_perceptio_core_bytes
from quam_rationabilem_successor_fixture import before_quam_core_bytes
from requiem_successor_fixture import (
    before_ordinary_agnus_core_bytes,
    before_requiem_graph,
)
from rosary_gospel_source_fixture import before_rosary_graph, before_rosary_registry
from witness_header_fixture import EXALTATION, before_joachim_records, before_joachim_registry

from build_reader import bibliography
from build_reader.bibliography import public_text_evidence
from build_reader.bibliography_bindings import (
    BindingError,
    digest,
    validate_bindings,
    witness_subject,
)
from checks import attribute, raw_binding

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = json.loads((ROOT / "tests/fixtures/main-ordo-registrations.json").read_bytes())
ROWS = EXPECTED["rows"]
ORACLE = json.loads((ROOT / "tests/fixtures/main-ordo-source-oracle.json").read_bytes())["rows"]
BY_TEXT = {row["text"]: row for row in ORACLE}
REGISTRY = "witnesses/raw/bindings.json"
GRAPH = "bibliography/graph.json"


def record(graph, collection, identity):
    matches = [row for row in graph[collection] if row["id"] == identity]
    assert len(matches) == 1
    return matches[0]


def expected_source(row):
    # Preserve the independent synthetic oracle; only the real header differs.
    source = deepcopy(BY_TEXT[row["text"]]["expected_source"])
    source["transcription_sha256"] = row["transcription_sha256"]
    return source


def assert_registered_payload(root, graph, row):
    path = root / row["witness"]
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == row["transcription_sha256"]
    core = root / ("texts/" + row["text"].replace(".", "/", 1) + ".json")
    core_raw = core.read_bytes()
    comparison_raw = before_perceptio_core_bytes(row["text"], core_raw)
    comparison_raw = before_quam_core_bytes(row["text"], comparison_raw)
    comparison_raw = before_pater_agnus_core_bytes(row["text"], comparison_raw)
    comparison_raw = before_ordinary_agnus_core_bytes(row["text"], comparison_raw)
    comparison_raw = before_offertory_core_bytes(row["text"], comparison_raw)
    assert hashlib.sha256(comparison_raw).hexdigest() == row["core_sha256"]
    doc = json.loads(core_raw)
    actual = raw_binding.resolve_binding(path, root)
    assert actual is not None and actual.spans == actual.fragments == ()
    assert actual.source == expected_source(row), "complete registered raw10 source"
    assert len(actual.text.split()) == BY_TEXT[row["text"]]["words"]
    assert hashlib.sha256((actual.text + "\n").encode()).hexdigest() == row["body_sha256"]
    witness = record(graph, "witnesses", row["witness_record"]["id"])
    assert witness == row["witness_record"]
    assert record(graph, "uses", witness["use"]) == row["use_record"]
    assert witness["review"] == {"status": "pending"}
    subject = witness_subject(root, witness, graph, doc)
    assert subject["contract"] == "witness-review-2"
    assert subject["raw_resolution"] == expected_source(row)
    assert subject["raw_resolution"] == actual.source
    assert set(subject["source_uses"]) == {row["use_record"]["id"]}
    return actual, subject


def before_exaltation_comparison(graph):
    """Invert four guarded source records only on a historical comparison copy."""
    result = deepcopy(graph)
    for expected in EXALTATION["added_uses"]:
        matches = [row for row in result["uses"] if row["id"] == expected["id"]]
        assert matches == [expected], "exact Exaltation comparison source record"
        result["uses"].remove(matches[0])
    for field, rule in (
        ("uses", EXALTATION["primary_use"]),
        ("witnesses", EXALTATION["witness"]),
    ):
        matches = [row for row in result[field] if row["id"] == rule["after"]["id"]]
        assert matches == [rule["after"]], "exact Exaltation comparison source record"
        matches[0].clear()
        matches[0].update(deepcopy(rule["before"]))
    return result


def before_registrations(graph, registry):
    historical_graph = before_exaltation_comparison(
        before_chant_graph(
            before_joachim_records(
                before_rosary_graph(before_lateran_graph(before_requiem_graph(graph)))
            )
        )
    )
    historical_raw = before_chant_registry(
        before_joachim_registry(before_rosary_registry(before_lateran_registry(registry)))
    )
    for collection in ("uses", "witnesses"):
        for expected in EXPECTED["graph_additions"][collection]:
            actual = record(historical_graph, collection, expected["id"])
            assert actual == expected, "complete main Ordo graph addition"
            historical_graph[collection].remove(actual)
    for identity, expected in EXPECTED["registry_bindings"].items():
        assert historical_raw["bindings"].get(identity) == expected, (
            "complete main Ordo registry addition"
        )
        del historical_raw["bindings"][identity]
    assert digest(historical_graph) == EXPECTED["before_graph_sha256"]
    assert digest(historical_raw) == EXPECTED["before_registry_sha256"]


@pytest.fixture(scope="module")
def graph():
    return json.loads((ROOT / GRAPH).read_bytes())


def test_real_registration_inventory_is_the_complete_closed_source_set():
    assert [row["text"] for row in ROWS] == [row["text"] for row in ORACLE]
    assert len(ROWS) == len(BY_TEXT) == 49
    assert {row["profile"] for row in ROWS} == set(EXPECTED["registry_bindings"])
    for collection, key in (("uses", "use_record"), ("witnesses", "witness_record")):
        assert {row[key]["id"] for row in ROWS} == {
            row["id"] for row in EXPECTED["graph_additions"][collection]
        }
    for row in ROWS:
        oracle = BY_TEXT[row["text"]]
        assert row["witness"] == oracle["witness"]
        assert row["profile"] == oracle["id"]
        assert EXPECTED["registry_bindings"][row["profile"]] == oracle["expected_source"]["binding"]
    assert (
        hashlib.sha256(
            (ROOT / "tests/fixtures/main-ordo-source-oracle.json").read_bytes()
        ).hexdigest()
        == EXPECTED["unchanged_oracle_sha256"]
    )


@pytest.mark.parametrize("row", ROWS, ids=[row["text"] for row in ROWS])
def test_actual_headers_resolve_complete_sources_and_pending_subjects(
    tmp_path, graph, row, monkeypatch
):
    assert_registered_payload(ROOT, graph, row)
    # Attribute only this real copied witness, not unrelated legacy witnesses.
    state = isolate(tmp_path, row, graph)
    monkeypatch.setattr(attribute, "CORPUS", state["root"])
    assert attribute._actor_sources(row["text"]).scope == "RAW_TEXT_ONLY"
    with pytest.raises(
        raw_binding.BindingError, match="closed Ordo evidence supports textual identity only"
    ):
        attribute.witness_ranges(row["text"])


def test_global_registration_inverse_and_pending_public_projection(graph):
    registry = json.loads((ROOT / REGISTRY).read_bytes())
    before_registrations(graph, registry)
    assert validate_bindings(ROOT, graph) == []
    assert (
        record(graph, "witnesses", EXPECTED["unchanged_sanctus_mr"]["id"])
        == (EXPECTED["unchanged_sanctus_mr"])
    )
    public = public_text_evidence(graph)["texts"]
    reviewed = {w["id"] for text in public for w in text.get("witnesses", [])}
    assert not reviewed & {row["witness_record"]["id"] for row in ROWS}


@pytest.mark.parametrize(
    "fault", ("missing-use", "extra-witness-field", "old-mr", "old-raw", "lavabo-macro-claim")
)
def test_global_inverse_rejects_missing_or_unrelated_changes_and_recovers(graph, fault):
    actual_graph = deepcopy(graph)
    actual_raw = json.loads((ROOT / REGISTRY).read_bytes())
    saved_graph, saved_raw = deepcopy(actual_graph), deepcopy(actual_raw)
    before_registrations(actual_graph, actual_raw)
    try:
        if fault == "missing-use":
            actual_graph["uses"].remove(record(actual_graph, "uses", ROWS[0]["use_record"]["id"]))
        elif fault == "extra-witness-field":
            record(actual_graph, "witnesses", ROWS[0]["witness_record"]["id"])["extra"] = True
        elif fault == "old-mr":
            record(actual_graph, "witnesses", EXPECTED["unchanged_sanctus_mr"]["id"])[
                "independence_basis"
            ] = "changed"
        elif fault == "old-raw":
            actual_raw["archives"]["missa-ordo-44667ff"]["upstream"] += ".foreign"
        else:
            row = next(row for row in ROWS if row["text"] == "ordinarium.lavabo")
            record(actual_graph, "uses", row["use_record"]["id"])["claim"] = (
                "This reading is the exact executed Prayers Gloria macro."
            )
        assert (digest(actual_graph), digest(actual_raw)) != (
            digest(saved_graph),
            digest(saved_raw),
        )
        with pytest.raises(AssertionError):
            before_registrations(actual_graph, actual_raw)
    finally:
        actual_graph.clear()
        actual_graph.update(saved_graph)
        actual_raw.clear()
        actual_raw.update(saved_raw)
        assert actual_graph == saved_graph and actual_raw == saved_raw
        before_registrations(actual_graph, actual_raw)


@pytest.mark.parametrize("collection", ("uses", "witnesses"))
def test_complete_graph_rejects_unsorted_new_records_and_restores(collection):
    graph, languages = bibliography.load(ROOT)
    saved, saved_languages = deepcopy(graph), deepcopy(languages)
    assert bibliography.validate(ROOT, graph, languages) == []
    identity = EXPECTED["graph_additions"][collection][0]["id"]
    rows = graph[collection]
    position = next(i for i, row in enumerate(rows) if row["id"] == identity)
    assert position < len(rows) - 1
    moved = rows[position]
    try:
        rows.append(rows.pop(position))
        assert rows[-1] is moved and digest(graph) != digest(saved)
        assert bibliography.validate(ROOT, graph, languages) == [
            f"bibliography.{collection}: records must be sorted by id"
        ]
    finally:
        assert rows.pop() is moved
        rows.insert(position, moved)
        assert graph[collection][position] is moved
        assert graph == saved and languages == saved_languages
        assert bibliography.validate(ROOT, graph, languages) == []
        assert bibliography.load(ROOT) == (saved, saved_languages)


def isolate(tmp_path, row, complete):
    root = tmp_path / "source"
    witness, use = deepcopy(row["witness_record"]), deepcopy(row["use_record"])
    edition = record(complete, "editions", use["edition"])
    graph = {
        "schema_version": complete["schema_version"],
        "works": [deepcopy(record(complete, "works", edition["work"]))],
        "editions": [deepcopy(edition)],
        "digital_items": [deepcopy(record(complete, "digital_items", use["digital_item"]))],
        "uses": [use],
        "witnesses": [witness],
        "collations": [],
    }
    source = expected_source(row)
    registry = {
        "version": source["registry_version"],
        "archives": deepcopy(source["archives"]),
        "bindings": {row["profile"]: deepcopy(EXPECTED["registry_bindings"][row["profile"]])},
    }
    paths = [row["witness"], "texts/" + row["text"].replace(".", "/", 1) + ".json"]
    paths.extend(a["path"] for a in registry["archives"].values())
    for relative in paths:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    state = dict(root=root, row=row, graph=graph, witness=witness, use=use, registry=registry)
    save_registry(state)
    return state


def save_registry(state):
    (state["root"] / REGISTRY).parent.mkdir(parents=True, exist_ok=True)
    (state["root"] / REGISTRY).write_text(
        json.dumps(state["registry"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


@contextmanager
def restored(state):
    root, graph, registry = state["root"], state["graph"], state["registry"]
    files = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    saved_graph, saved_registry = deepcopy(graph), deepcopy(registry)
    witness, use = state["witness"], state["use"]
    original = assert_registered_payload(root, graph, state["row"])
    assert validate_bindings(root, graph) == []
    try:
        yield
    finally:
        changed = digest(graph) != digest(saved_graph) or (
            digest(registry) != digest(saved_registry)
        )
        changed = changed or any((root / p).read_bytes() != raw for p, raw in files.items())
        assert changed, "the actual registration fixture must change"
        for relative, raw in files.items():
            (root / relative).write_bytes(raw)
        witness.clear()
        witness.update(saved_graph["witnesses"][0])
        use.clear()
        use.update(saved_graph["uses"][0])
        saved_graph["witnesses"], saved_graph["uses"] = [witness], [use]
        graph.clear()
        graph.update(saved_graph)
        registry.clear()
        registry.update(saved_registry)
        assert state["witness"] is graph["witnesses"][0]
        assert state["use"] is graph["uses"][0]
        assert graph == saved_graph and registry == saved_registry
        assert {
            p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()
        } == files
        assert assert_registered_payload(root, graph, state["row"]) == original
        assert validate_bindings(root, graph) == []


RAW_FAULTS = ("marker", "header-revision", "binding-profile", "missing-binding", "path")


@pytest.mark.parametrize("fault", RAW_FAULTS)
def test_real_header_identity_faults_reject_and_same_copy_recovers(tmp_path, graph, fault):
    row = next(row for row in ROWS if row["text"] == "ordinarium.per-ipsum")
    state = isolate(tmp_path, row, graph)
    path = state["root"] / row["witness"]
    with restored(state):
        raw = path.read_text(encoding="utf-8")
        if fault == "marker":
            raw = raw.replace(f"# raw-binding: {row['profile']}\n", "", 1)
        elif fault == "header-revision":
            revision = EXPECTED["registry_bindings"][row["profile"]]["revision"]
            raw = raw.replace(f"# revision: {revision}\n", "# revision: " + "0" * 40 + "\n", 1)
        elif fault == "binding-profile":
            state["registry"]["bindings"][row["profile"]]["profile"] += "-foreign"
        elif fault == "missing-binding":
            del state["registry"]["bindings"][row["profile"]]
        else:
            declaration = BY_TEXT[row["text"]]["expected_source"]["profile"]["path"]
            raw = raw.replace(f"# path: {declaration}\n", "# path: foreign\n", 1)
        path.write_text(raw, encoding="utf-8")
        save_registry(state)
        with pytest.raises(raw_binding.BindingError):
            raw_binding.resolve_binding(path, state["root"])


GRAPH_FAULTS = ("inventory", "role", "evidence", "transcript-hash", "forged-review")


@pytest.mark.parametrize("fault", GRAPH_FAULTS)
def test_real_pending_source_faults_reject_and_same_copy_recovers(tmp_path, graph, fault):
    row = next(row for row in ROWS if row["text"] == "ordinarium.per-ipsum")
    state = isolate(tmp_path, row, graph)
    with restored(state):
        if fault == "inventory":
            del state["witness"]["source_dependencies"]
        elif fault == "role":
            state["use"]["role"] = "rubric_control"
        elif fault == "evidence":
            state["use"]["evidence_sha256"] = row["body_sha256"]
        elif fault == "transcript-hash":
            state["witness"]["transcription_sha256"] = "0" * 64
        else:
            state["witness"]["review"] = {"status": "reviewed", "sha256": "0" * 64}
        if fault == "forged-review":
            assert validate_bindings(state["root"], state["graph"]) == [
                f"bibliography witness {row['witness_record']['id']}: "
                "reviewed subject changed; re-review or mark pending explicitly"
            ]
        else:
            doc = json.loads(
                (
                    state["root"] / ("texts/" + row["text"].replace(".", "/", 1) + ".json")
                ).read_bytes()
            )
            with pytest.raises(BindingError):
                witness_subject(state["root"], state["witness"], state["graph"], doc)


@pytest.mark.parametrize("fault", ("comma", "missing-doxology-word"))
def test_real_lavabo_literal_composite_rejects_altered_body_and_recovers(tmp_path, graph, fault):
    row = next(row for row in ROWS if row["text"] == "ordinarium.lavabo")
    state = isolate(tmp_path, row, graph)
    path = state["root"] / row["witness"]
    with restored(state):
        original = path.read_text(encoding="utf-8")
        before, after = ("semper:", "semper,") if fault == "comma" else ("Glória Patri", "Glória")
        lines = original.splitlines(keepends=True)
        positions = [
            i for i, line in enumerate(lines) if not line.startswith("#") and before in line
        ]
        assert len(positions) == 1
        position = positions[0]
        assert lines[position].count(before) == 1
        lines[position] = lines[position].replace(before, after, 1)
        changed = "".join(lines)
        assert changed != original
        path.write_text(changed, encoding="utf-8")
        with pytest.raises(
            raw_binding.BindingError,
            match="transcription differs from its exact closed Ordo reading",
        ):
            raw_binding.resolve_binding(path, state["root"])


@pytest.mark.parametrize("part", ("doxology", "reprise", "primary", "witness"))
@pytest.mark.parametrize("fault", ("missing", "wrong", "extra", "duplicate"))
def test_exaltation_comparison_rejects_exact_record_damage_and_same_graph_recovers(
    graph, part, fault
):
    registry = json.loads((ROOT / REGISTRY).read_bytes())
    saved, saved_registry = deepcopy(graph), deepcopy(registry)
    before_registrations(graph, registry)
    doc = json.loads(
        (ROOT / ("texts/" + EXALTATION["text"].replace(".", "/", 1) + ".json")).read_bytes()
    )
    current_witness = record(graph, "witnesses", EXALTATION["witness"]["after"]["id"])
    subject = witness_subject(ROOT, current_witness, graph, doc)
    assert subject == EXALTATION["expected_source_subject"]
    fields = {
        "doxology": ("uses", EXALTATION["added_uses"][0]),
        "reprise": ("uses", EXALTATION["added_uses"][1]),
        "primary": ("uses", EXALTATION["primary_use"]["after"]),
        "witness": ("witnesses", EXALTATION["witness"]["after"]),
    }
    field, expected = fields[part]
    current = record(graph, field, expected["id"])
    try:
        if fault == "missing":
            graph[field].remove(current)
        elif fault == "wrong":
            if field == "witnesses":
                current["transcription_sha256"] = "0" * 64
            else:
                current["claim"] += " Changed."
        elif fault == "extra":
            current["unexpected"] = True
        else:
            graph[field].append(deepcopy(current))
        assert graph != saved
        with pytest.raises(
            AssertionError, match=r"^exact Exaltation comparison source record(?:\n|$)"
        ):
            before_registrations(graph, registry)
    finally:
        graph.clear()
        graph.update(saved)
        assert graph == saved and registry == saved_registry
        before_registrations(graph, registry)
        current_witness = record(graph, "witnesses", EXALTATION["witness"]["after"]["id"])
        assert witness_subject(ROOT, current_witness, graph, doc) == subject
