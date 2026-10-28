"""Direct Common documentation preserves literal spelling and pending review."""

import hashlib
import json
import re
import shutil
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

import pytest
from anne_documentary_fixture import (
    F,
    before_anne_core,
    before_anne_graph,
    before_anne_registry,
    current,
    record,
)
from documentary_successor_fixture import before_documentary_graph, before_documentary_registry

from build_reader.bibliography import public_text_evidence
from build_reader.bibliography_bindings import (
    BindingError,
    digest,
    validate_bindings,
    witness_subject,
)
from build_reader.layers import expand_core
from checks.collate import collate
from checks.raw_binding import (
    BindingError as RawBindingError,
)
from checks.raw_binding import (
    RawBindingSnapshot,
    resolve_binding,
)
from checks.translation_provenance import source_payload

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = "witnesses/raw/bindings.json"


def write(root, path, value):
    (root / path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


@pytest.fixture
def state(tmp_path):
    full = json.loads((ROOT / "bibliography/graph.json").read_bytes())
    graph = deepcopy(full)
    for field in ("uses", "witnesses", "collations"):
        graph[field] = [
            r
            for r in graph[field]
            if r.get("text") == F["text"] or r.get("address", {}).get("text") == F["text"]
        ]
    registry = {
        "version": 1,
        "archives": {F["archive_id"]: deepcopy(F["archive"])},
        "bindings": {F["binding_id"]: deepcopy(F["binding"])},
    }
    paths = [F["core"], F["witness"], F["mr"], F["apparatus"], F["archive"]["path"]]
    for path in paths:
        destination = tmp_path / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, destination)
    write(tmp_path, REGISTRY, registry)
    return {"root": tmp_path, "graph": graph, "registry": registry, "paths": [*paths, REGISTRY]}


@contextmanager
def recovered(state):
    root = state["root"]
    graph, registry = state["graph"], state["registry"]
    saved_graph, saved_registry = deepcopy(graph), deepcopy(registry)
    files = {path: (root / path).read_bytes() for path in state["paths"]}
    healthy = current(root, graph)
    try:
        yield
    finally:
        assert (
            graph != saved_graph
            or registry != saved_registry
            or any((root / path).read_bytes() != raw for path, raw in files.items())
        ), "adverse source actually changed"
        graph.clear()
        graph.update(saved_graph)
        registry.clear()
        registry.update(saved_registry)
        for path, raw in files.items():
            (root / path).write_bytes(raw)
        assert state["graph"] is graph and state["registry"] is registry
        assert current(root, graph) == healthy


def test_real_current_inputs_validate_before_complete_historical_inverse():
    graph = json.loads((ROOT / "bibliography/graph.json").read_bytes())
    registry = json.loads((ROOT / REGISTRY).read_bytes())
    saved_graph, saved_registry = deepcopy(graph), deepcopy(registry)
    current(ROOT, graph)
    assert validate_bindings(ROOT, graph) == []
    assert digest(before_documentary_graph(graph)) == F["graph_before_sha256"]
    assert digest(before_documentary_registry(registry)) == F["registry_before_sha256"]
    assert graph == saved_graph and registry == saved_registry


def test_complete_member_framing_and_single_literal_body_fragment(state):
    actual, _ = current(state["root"], state["graph"])
    root = state["root"]
    raw = (root / F["archive"]["path"]).read_bytes()
    assert len(raw) == 6675 and hashlib.sha256(raw).hexdigest() == F["archive"]["sha256"]
    lines = raw.decode().splitlines()
    assert [{"line": n, "text": lines[n - 1]} for n in range(74, 80)] == F["frame"]
    assert actual.spans == ((root / F["archive"]["path"], 77, 77),)
    assert len(actual.fragments) == 1
    (fragment,) = actual.fragments
    assert (fragment.line, fragment.start, fragment.end) == (77, 0, len(F["literal"]))
    assert fragment.raw == fragment.text == F["literal"]
    assert fragment.marker is None and fragment.whole_line
    assert not fragment.partial_contract and fragment.marker_scope_verified
    assert fragment.binding_id == F["binding_id"] and fragment.framing == ()


@pytest.mark.parametrize("row", F["ij"], ids=[r["word"] for r in F["ij"]])
def test_each_raw_ejus_has_one_exact_nonduplicate_house_reading(state, row):
    actual, _ = current(state["root"], state["graph"])
    assert len(actual.text.split()) == 229
    assert actual.text.split()[row["index"]] == row["literal"]
    app = json.loads((state["root"] / F["apparatus"]).read_bytes())
    entries = [r for r in app["adjudicated"] if r["at"] == row["word"]]
    assert len(entries) == 1
    assert entries[0]["ours"] == row["ours"]
    assert entries[0]["witnesses"] == {"do": row["literal"]}
    assert entries[0]["class"] == "orthography"
    assert app["adjudicated"][:6] == F["old_apparatus"]["adjudicated"]


def test_pending_identity_is_not_a_source_review_or_public_witness_grant(state):
    root, graph = state["root"], state["graph"]
    current(root, graph)
    assert validate_bindings(root, graph) == []
    assert all(
        r["review"] == {"status": "pending"}
        for field in ("witnesses", "collations")
        for r in graph[field]
    )
    mr = next(r for r in graph["witnesses"] if r["transcription"] == "mr")
    core = json.loads((root / F["core"]).read_bytes())
    with pytest.raises(BindingError, match="complete explicit source_dependencies"):
        witness_subject(root, mr, graph, core)
    (public,) = [r for r in public_text_evidence(graph)["texts"] if r["id"] == F["text"]]
    assert public["witnesses"] == [] and "collation" not in public
    assert "raw_resolution" not in json.dumps(public)


def test_method_is_documentary_not_a_translation_source_payload_edit(state):
    core = json.loads((state["root"] / F["core"]).read_bytes())
    historical = before_anne_core(core)
    after = source_payload(core["segments"][0])
    core["editorial"]["source"]["method"] = F["method"]["before"]
    assert source_payload(core["segments"][0]) == after
    assert digest(historical["segments"]) == F["core_segments_sha256"]


RAW_FAULTS = (
    ("upstream", "witness path declarations differ from bound evidence"),
    ("archive-revision", "revision differs from binding"),
    ("binding-revision", "witness revision differs from its raw binding"),
    ("digest", "SHA-256 mismatch"),
    ("section", "source section does not match evidence"),
    ("section-line", "source section does not match evidence"),
    ("range", "invalid source line range"),
    ("reference", "reference differs from source evidence"),
    ("repeat", "reading omits or repeats source text"),
    ("missing-binding", "raw-binding marker and registered witness identity disagree"),
    ("missing-marker", "raw-binding marker and registered witness identity disagree"),
    ("duplicate-marker", "raw-binding marker and registered witness identity disagree"),
    ("wrong-witness", "raw-binding marker and registered witness identity disagree"),
    ("missing-archive", "unknown archive"),
    ("escape", "invalid confined path"),
    ("normalized", "transcription differs from its exact ordered raw reading"),
    ("body-order", "transcription differs from its exact ordered raw reading"),
    ("raw-bytes", "SHA-256 mismatch"),
)


@pytest.mark.parametrize("fault,message", RAW_FAULTS, ids=[r[0] for r in RAW_FAULTS])
def test_actual_raw_failure_and_same_copy_restoration(state, fault, message):
    root, registry = state["root"], state["registry"]
    with recovered(state):
        plan = registry["bindings"][F["binding_id"]]
        archive = registry["archives"][F["archive_id"]]
        path = root / F["witness"]
        text = path.read_text()
        marker = "# raw-binding: " + F["binding_id"] + "\n"
        if fault == "upstream":
            archive["upstream"] = "obsolete/missa/Latin/Commune/C7a.txt"
        elif fault == "archive-revision":
            archive["revision"] = "0" * 40
        elif fault == "binding-revision":
            plan["revision"] = "0" * 40
        elif fault == "digest":
            archive["sha256"] = "0" * 64
        elif fault == "section":
            plan["evidence"][0]["section"] = "Lectio1"
        elif fault == "section-line":
            plan["evidence"][0]["section_line"] = 75
        elif fault == "range":
            plan["reading"][0]["first"] = 0
        elif fault == "reference":
            plan["references"] = [
                {"archive": F["archive_id"], "line": 76, "text": "!Prov 31:10-31", "target": 0}
            ]
        elif fault == "repeat":
            plan["reading"].append(deepcopy(plan["reading"][0]))
        elif fault == "missing-binding":
            del registry["bindings"][F["binding_id"]]
        elif fault == "missing-marker":
            path.write_text(text.replace(marker, "", 1))
        elif fault == "duplicate-marker":
            path.write_text(marker + text)
        elif fault == "wrong-witness":
            plan["witness"] = F["mr"]
        elif fault == "missing-archive":
            del registry["archives"][F["archive_id"]]
        elif fault == "escape":
            archive["path"] = "witnesses/raw/../foreign.txt"
        elif fault == "normalized":
            path.write_text(text.replace(F["literal"], F["literal"].replace("ejus", "eius"), 1))
        elif fault == "body-order":
            words = F["literal"].split()
            words[0], words[1] = words[1], words[0]
            path.write_text(text.replace(F["literal"], " ".join(words), 1))
        else:
            raw = root / F["archive"]["path"]
            raw.write_bytes(raw.read_bytes() + b"\n# altered\n")
        write(root, REGISTRY, registry)
        with pytest.raises(RawBindingError, match=re.escape(message)):
            resolve_binding(path, root)


SOURCE_FAULTS = (
    ("evidence", "digital evidence_sha256 identifies neither"),
    ("null-binding", "source requires its explicit exact raw binding"),
    ("foreign-binding", "declared raw binding differs from registered resolution"),
    ("missing-inventory", "complete explicit source_dependencies declaration required"),
    ("item-revision", "digital item revision or kind differs from raw binding"),
    ("role", "source use has an incompatible role"),
    ("transcript", "transcription_sha256 differs from the complete bound transcript"),
)


@pytest.mark.parametrize("fault,message", SOURCE_FAULTS, ids=[r[0] for r in SOURCE_FAULTS])
def test_actual_reviewable_source_rejects_identity_forgery_and_recovers(state, fault, message):
    root, graph = state["root"], state["graph"]
    with recovered(state):
        witness = record(graph, "witnesses", F["records"]["witnesses"]["after"]["id"])
        use = record(graph, "uses", witness["use"])
        if fault == "evidence":
            use["evidence_sha256"] = "0" * 64
        elif fault == "null-binding":
            witness["source_dependencies"]["raw_binding"] = None
        elif fault == "foreign-binding":
            witness["source_dependencies"]["raw_binding"] = "foreign"
        elif fault == "missing-inventory":
            del witness["source_dependencies"]
        elif fault == "item-revision":
            record(graph, "digital_items", use["digital_item"])["revision"] = "0" * 40
        elif fault == "role":
            use["role"] = "lexical_support"
        else:
            witness["transcription_sha256"] = "0" * 64
        core = json.loads((root / F["core"]).read_bytes())
        with pytest.raises(BindingError, match=re.escape(message)):
            witness_subject(root, witness, graph, core)


@pytest.mark.parametrize(
    "fault",
    [
        "missing-archive",
        "extra-binding",
        "wrong-line",
        "extra-use",
        "missing-dependency",
        "wrong-apparatus",
    ],
)
def test_historical_inverse_requires_whole_exact_additions_and_rows(fault):
    graph = json.loads((ROOT / "bibliography/graph.json").read_bytes())
    registry = json.loads((ROOT / REGISTRY).read_bytes())
    current(ROOT, graph)
    saved_graph, saved_registry = deepcopy(graph), deepcopy(registry)
    try:
        if fault == "missing-archive":
            del registry["archives"][F["archive_id"]]
        elif fault == "extra-binding":
            registry["bindings"][F["binding_id"]]["extra"] = True
        elif fault == "wrong-line":
            registry["bindings"][F["binding_id"]]["reading"][0]["first"] = 76
        else:
            field = {
                "extra-use": "uses",
                "missing-dependency": "witnesses",
                "wrong-apparatus": "collations",
            }[fault]
            item = record(graph, field, F["records"][field]["after"]["id"])
            if fault == "extra-use":
                item["extra"] = True
            elif fault == "missing-dependency":
                del item["source_dependencies"]
            else:
                item["apparatus_sha256"] = "0" * 64
        with pytest.raises(AssertionError, match=r"exact Anne (registry|graph) successor"):
            before_anne_registry(registry) if fault in {
                "missing-archive",
                "extra-binding",
                "wrong-line",
            } else before_anne_graph(graph)
    finally:
        graph.clear()
        graph.update(saved_graph)
        registry.clear()
        registry.update(saved_registry)
    assert digest(before_documentary_graph(graph)) == F["graph_before_sha256"]
    assert digest(before_documentary_registry(registry)) == F["registry_before_sha256"]


def test_raw1_can_read_other_plain_text_but_cannot_certify_the_mass_profile(state):
    root, registry = state["root"], state["registry"]
    with recovered(state):
        plan = registry["bindings"][F["binding_id"]]
        plan["evidence"][0]["first"] = 75
        plan["reading"].insert(0, {"archive": F["archive_id"], "first": 75, "last": 75})
        path = root / F["witness"]
        text = path.read_text().replace("(lines 76-77)", "(lines 75-77)", 1)
        heading = F["frame"][1]["text"]
        path.write_text(text.replace(F["literal"], heading + " " + F["literal"], 1))
        write(root, REGISTRY, registry)
        actual = resolve_binding(path, root)
        assert actual is not None and actual.text == heading + " " + F["literal"]
        assert actual.source["contract"] == "raw-reading-1"
        with pytest.raises(AssertionError, match="exact Mass body without heading"):
            assert actual.text == F["literal"], "exact Mass body without heading"


def test_snapshot_returns_independent_complete_payloads(state):
    root = state["root"]
    snapshot = RawBindingSnapshot(root)
    first = snapshot.resolve(root / F["witness"])
    assert first is not None
    first.source["binding"]["reading"][0]["first"] = 1
    second = snapshot.resolve(root / F["witness"])
    assert second is not None and second.source == F["expected_source"]


@pytest.mark.parametrize("fault", ["missing-ruling", "wrong-class"])
def test_actual_collation_rejects_an_unruled_literal_ij_difference_and_recovers(state, fault):
    root = state["root"]
    with recovered(state):
        app = json.loads((root / F["apparatus"]).read_bytes())
        (row,) = [r for r in app["adjudicated"] if r["at"] == "w011"]
        if fault == "missing-ruling":
            app["adjudicated"].remove(row)
        else:
            row["class"] = "punctuation"
        app["summary"] = {
            "entries": len(app["adjudicated"]),
            "classes": sorted({r["class"] for r in app["adjudicated"]}),
        }
        write(root, F["apparatus"], app)
        core = json.loads((root / F["core"]).read_bytes())
        errors, _, _ = collate(expand_core(core), root / "witnesses" / F["text"])
        assert any("do: SUBSTANTIVE divergence at word 11 (w011)" in e for e in errors)


ANNE_LAYERS = [
    pytest.param(row, id=row["language"])
    for row in json.loads(
        (ROOT / "tests/fixtures/proper-eighth-twelve-passive-captions.json").read_bytes()
    )["layers"]
    if row["text"] == F["text"]
]


@pytest.mark.parametrize("case", ANNE_LAYERS)
@pytest.mark.parametrize("fault", ["method", "missing-method", "unrelated-core"])
def test_method_history_copy_rejects_corruption_and_same_core_recovers(case, fault):
    from test_proper_eighth_twelve_passive_captions import load, shape

    core, layer = load(case)
    saved_core, saved_layer = deepcopy(core), deepcopy(layer)
    shape(core, layer)
    healthy = before_anne_core(core)
    assert digest(healthy) == case["core_sha256"]
    assert core == saved_core and healthy is not core
    try:
        if fault == "method":
            core["editorial"]["source"]["method"] = F["method"]["before"]
            diagnostic = "exact Anne current documentary method"
        elif fault == "missing-method":
            del core["editorial"]["source"]["method"]
            diagnostic = "exact Anne current documentary method"
        else:
            core["title"] += " Changed."
            diagnostic = "exact Anne complete core predecessor"
        assert core != saved_core and layer == saved_layer
        # These metadata faults still satisfy native layer shape. The exact
        # documentary history assertion, not a generic API, must reject them.
        shape(core, layer)
        with pytest.raises(AssertionError, match=diagnostic):
            before_anne_core(core)
    finally:
        core.clear()
        core.update(saved_core)
        assert core == saved_core and layer == saved_layer
        shape(core, layer)
        assert before_anne_core(core) == healthy
