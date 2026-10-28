"""A literal Common reading is distinct from an inherited runtime selection."""

import hashlib
import json
import shutil
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

import pytest
from documentary_successor_fixture import before_additional_records, before_additional_registry
from lateran_epistle_source_fixture import (
    DATA as F,
)
from lateran_epistle_source_fixture import (
    before_lateran_core,
    before_lateran_graph,
    before_lateran_records,
    before_lateran_registry,
    canonical_hash,
)
from rosary_gospel_source_fixture import before_rosary_graph, before_rosary_registry

from build_reader.bibliography import public_text_evidence
from build_reader.bibliography_bindings import BindingError, validate_bindings, witness_subject
from build_reader.layers import expand_core
from checks import attribute
from checks.collate import collate
from checks.raw_binding import (
    BindingError as RawBindingError,
)
from checks.raw_binding import (
    RawBindingSnapshot,
    load_registry,
    resolve_binding,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = "witnesses/raw/bindings.json"
GRAPH = "bibliography/graph.json"


def write(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def record(graph, collection, identity):
    rows = [row for row in graph[collection] if row["id"] == identity]
    assert len(rows) == 1
    return rows[0]


def coordinates(value, root):
    if isinstance(value, Path):
        return value.relative_to(root).as_posix()
    if isinstance(value, dict):
        return {key: coordinates(child, root) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [coordinates(child, root) for child in value]
    return value


@pytest.fixture
def source(tmp_path):
    graph = json.loads((ROOT / GRAPH).read_bytes())
    graph["uses"] = [
        row for row in graph["uses"] if row.get("address", {}).get("text") == F["text"]
    ]
    for collection in ("witnesses", "collations"):
        graph[collection] = [row for row in graph[collection] if row["text"] == F["text"]]
    current = json.loads((ROOT / REGISTRY).read_bytes())
    registry = {
        "version": 1,
        "archives": {F["archive_id"]: deepcopy(current["archives"][F["archive_id"]])},
        "bindings": {F["binding_id"]: deepcopy(current["bindings"][F["binding_id"]])},
    }
    assert registry["archives"][F["archive_id"]] == F["archive"]
    assert registry["bindings"][F["binding_id"]] == F["binding"]
    paths = [F["core"], F["witness"], F["mr"], F["apparatus_path"], F["archive"]["path"]]
    for relative in paths:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, path)
    write(tmp_path, REGISTRY, registry)
    return {"root": tmp_path, "graph": graph, "registry": registry, "files": [*paths, REGISTRY]}


def healthy(state):
    root, graph = state["root"], state["graph"]
    assert load_registry(root) == state["registry"]
    assert (root / F["witness"]).read_text() == F["transcript"]["after"]
    actual = resolve_binding(root / F["witness"], root)
    assert actual is not None
    assert coordinates(asdict(actual), root) == F["expected_reading"], (
        "complete Lateran raw payload"
    )
    doc = json.loads((root / F["core"]).read_bytes())
    before_lateran_core(doc)
    for collection, rule in F["records"].items():
        assert record(graph, collection, rule["after"]["id"]) == rule["after"]
    subject = witness_subject(root, record(graph, "witnesses", F["witness_id"]), graph, doc)
    assert subject == F["expected_subject"]
    assert validate_bindings(root, graph) == []
    errors, warnings, stats = collate(expand_core(doc), root / f"witnesses/{F['text']}")
    assert errors == warnings == []
    assert (stats["words"], stats["witnesses"], stats["variants_adjudicated"]) == (82, 2, 4)
    assert stats["orthographic"] == 3 and stats["substantive_variants"] == 0
    return actual, subject


@contextmanager
def recover(state):
    graph, registry = state["graph"], state["registry"]
    saved_graph, saved_registry = deepcopy(graph), deepcopy(registry)
    files = {p: (state["root"] / p).read_bytes() for p in state["files"]}
    try:
        yield
    finally:
        graph.clear()
        graph.update(saved_graph)
        registry.clear()
        registry.update(saved_registry)
        for relative, raw in files.items():
            (state["root"] / relative).write_bytes(raw)
        assert state["graph"] is graph and state["registry"] is registry
        assert graph == saved_graph and registry == saved_registry
        assert all((state["root"] / p).read_bytes() == raw for p, raw in files.items())
        healthy(state)


def test_complete_direct_reading_and_all_eighty_two_coordinates(source):
    actual, _ = healthy(source)
    raw = (source["root"] / F["archive"]["path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == F["archive"]["sha256"]
    lines = raw.decode().splitlines()
    assert lines[583:589] == F["reading_frame"]
    assert actual.text == " ".join(row["literal"] for row in F["words"])
    assert len(F["words"]) == 82
    for row in F["words"]:
        assert lines[row["line"] - 1][row["start"] : row["end"]] == row["literal"]


def test_direct_common_claim_does_not_prove_inherited_selection_or_review(source):
    _, subject = healthy(source)
    root, graph = source["root"], source["graph"]
    proper = (ROOT / F["proper_path"]).read_bytes()
    assert hashlib.sha256(proper).hexdigest() == F["proper_sha256"]
    assert "[Lectio]" not in proper.decode().splitlines()
    assert proper.decode().splitlines()[1].endswith("ex C8")
    assert proper.decode().splitlines()[4] == "ex C8;"
    assert F["binding"]["references"] == [] and "contract" not in F["binding"]
    assert subject["contract"] == "witness-review-2"
    assert set(subject["source_uses"]) == {F["use_id"]}
    assert all(
        row["review"] == {"status": "pending"} for row in graph["witnesses"] + graph["collations"]
    )
    mr = record(graph, "witnesses", F["mr_id"])
    doc = json.loads((root / F["core"]).read_bytes())
    with pytest.raises(
        BindingError, match="complete explicit source_dependencies declaration required"
    ):
        witness_subject(root, mr, graph, doc)
    public = next(row for row in public_text_evidence(graph)["texts"] if row["id"] == F["text"])
    assert public["witnesses"] == [] and "collation" not in public
    entries = [entry for group in public["source_groups"] for entry in group["entries"]]
    assert (
        next(row for row in entries if row["id"] == F["use_id"])["claim"]
        == (F["records"]["uses"]["after"]["claim"])
    )
    assert "raw_resolution" not in json.dumps(public)


RAW_FAULTS = (
    ("explicit-raw1", "unsupported per-binding contract"),
    ("old-feast-path", "witness path declarations differ from bound evidence"),
    ("archive-revision", "revision differs from binding"),
    ("binding-revision", "witness revision differs from its raw binding"),
    ("archive-hash", "SHA-256 mismatch"),
    ("section", "source section does not match evidence"),
    ("section-line", "source section does not match evidence"),
    ("repeat", "reading omits or repeats source text"),
    ("framing", "reading contains framing or lies outside textual evidence"),
    ("missing-binding", "raw-binding marker and registered witness identity disagree"),
    ("missing-marker", "raw-binding marker and registered witness identity disagree"),
    ("duplicate-marker", "raw-binding marker and registered witness identity disagree"),
    ("normalized-body", "transcription differs from its exact ordered raw reading"),
    ("raw-bytes", "SHA-256 mismatch"),
)


@pytest.mark.parametrize("fault,message", RAW_FAULTS, ids=[row[0] for row in RAW_FAULTS])
def test_actual_raw_guard_rejects_fault_and_same_subject_recovers(source, fault, message):
    healthy(source)
    root, registry = source["root"], source["registry"]
    with recover(source):
        saved = deepcopy(registry)
        path = root / F["witness"]
        raw = path.read_text()
        plan = registry["bindings"][F["binding_id"]]
        archive = registry["archives"][F["archive_id"]]
        if fault == "explicit-raw1":
            plan["contract"] = "raw-reading-1"
        elif fault == "old-feast-path":
            declaration = "# path: web/www/missa/Latin/Sancti/11-09.txt [Lectio] (lines 587-587)\n"
            path.write_text(raw.replace(F["path_header"], declaration, 1))
        elif fault == "archive-revision":
            archive["revision"] = "0" * 40
        elif fault == "binding-revision":
            plan["revision"] = "0" * 40
        elif fault == "archive-hash":
            archive["sha256"] = "0" * 64
        elif fault == "section":
            plan["evidence"][0]["section"] = "Graduale"
        elif fault == "section-line":
            plan["evidence"][0]["section_line"] = 583
        elif fault == "repeat":
            plan["reading"].append(deepcopy(plan["reading"][0]))
        elif fault == "framing":
            plan["reading"][0]["first"] = 586
        elif fault == "missing-binding":
            del registry["bindings"][F["binding_id"]]
        elif fault == "missing-marker":
            path.write_text(raw.replace(F["marker"], "", 1))
        elif fault == "duplicate-marker":
            path.write_text(F["marker"] + raw)
        elif fault == "normalized-body":
            path.write_text(
                raw.replace(F["literal"], F["transcript"]["before"].splitlines()[-1], 1)
            )
        else:
            archive_path = root / archive["path"]
            archive_path.write_bytes(archive_path.read_bytes() + b"\n")
        write(root, REGISTRY, registry)
        assert registry != saved or path.read_text() != raw or fault == "raw-bytes"
        with pytest.raises(RawBindingError, match=message):
            resolve_binding(path, root)


SOURCE_FAULTS = (
    ("feast-evidence", "digital evidence_sha256 identifies neither"),
    ("raw-dependency", "source requires its explicit exact raw binding"),
    ("wrong-binding", "declared raw binding differs from registered resolution"),
    ("missing-inventory", "complete explicit source_dependencies declaration required"),
    ("transcript-digest", "transcription_sha256 differs from the complete bound transcript"),
    ("apparatus-digest", "apparatus_sha256 differs from the complete apparatus"),
    ("apparatus-summary", "apparatus summary differs from the actual adjudicated entries"),
    ("witness-review", "reviewed subject changed"),
    ("collation-review", "reviewed collation requires reviewed witness bindings"),
)


@pytest.mark.parametrize(
    "section,heading,number",
    [("Graduale", 589, 590), ("Lectio1", 148, 151)],
    ids=["wrong-common-part", "office-lesson"],
)
def test_coherent_other_source_is_raw1_but_not_the_exact_epistle(source, section, heading, number):
    healthy(source)
    root, registry = source["root"], source["registry"]
    with recover(source):
        plan = registry["bindings"][F["binding_id"]]
        plan["evidence"] = [
            {
                "archive": F["archive_id"],
                "first": number,
                "last": number,
                "section": section,
                "section_line": heading,
            }
        ]
        plan["reading"] = [{"archive": F["archive_id"], "first": number, "last": number}]
        lines = (root / F["archive"]["path"]).read_text().splitlines()
        body = " ".join(lines[number - 1].split())
        path = root / F["witness"]
        text = (
            path.read_text()
            .replace(
                F["path_header"],
                f"# path: {F['archive']['upstream']} [{section}] (lines {number}-{number})\n",
                1,
            )
            .replace(F["literal"], body, 1)
        )
        path.write_text(text)
        write(root, REGISTRY, registry)
        actual = resolve_binding(path, root)
        assert actual is not None and actual.source["contract"] == "raw-reading-1"
        assert actual.text == body and actual.text != F["literal"]
        with pytest.raises(AssertionError, match=r"^exact Epistle source selection(?:\n|$)"):
            assert actual.source["binding"] == F["binding"], "exact Epistle source selection"


@pytest.mark.parametrize("fault,message", SOURCE_FAULTS, ids=[row[0] for row in SOURCE_FAULTS])
def test_actual_source_identity_fault_and_same_graph_recovers(source, fault, message):
    healthy(source)
    root, graph = source["root"], source["graph"]
    with recover(source):
        saved = deepcopy(graph)
        witness = record(graph, "witnesses", F["witness_id"])
        collation = record(graph, "collations", F["collation_id"])
        if fault == "feast-evidence":
            record(graph, "uses", F["use_id"])["evidence_sha256"] = F["proper_sha256"]
        elif fault == "raw-dependency":
            witness["source_dependencies"]["raw_binding"] = None
        elif fault == "wrong-binding":
            witness["source_dependencies"]["raw_binding"] = "foreign-binding"
        elif fault == "missing-inventory":
            del witness["source_dependencies"]
        elif fault == "transcript-digest":
            witness["transcription_sha256"] = "0" * 64
        elif fault == "apparatus-digest":
            collation["apparatus_sha256"] = hashlib.sha256(
                (root / F["apparatus_path"]).read_bytes()
            ).hexdigest()
        elif fault == "apparatus-summary":
            collation["apparatus"]["entries"] = 4
        elif fault == "witness-review":
            witness["review"] = {"status": "reviewed", "sha256": "0" * 64}
        else:
            collation["review"] = {"status": "reviewed", "sha256": "0" * 64}
        assert graph != saved
        if fault == "missing-inventory":
            assert validate_bindings(root, graph) == []
            doc = json.loads((root / F["core"]).read_bytes())
            with pytest.raises(BindingError, match=message):
                witness_subject(root, witness, graph, doc)
        else:
            assert any(message in error for error in validate_bindings(root, graph))


@pytest.mark.parametrize("word", ["w007", "w011", "w039", "w063", "w065", "w074", "w079"])
def test_each_actual_variant_is_required_and_same_apparatus_recovers(source, word):
    healthy(source)
    root = source["root"]
    with recover(source):
        app = json.loads((root / F["apparatus_path"]).read_bytes())
        saved = deepcopy(app)
        app["adjudicated"] = [entry for entry in app["adjudicated"] if entry["at"] != word]
        assert len(saved["adjudicated"]) - len(app["adjudicated"]) == 1
        write(root, F["apparatus_path"], app)
        doc = json.loads((root / F["core"]).read_bytes())
        errors, _, _ = collate(expand_core(doc), root / f"witnesses/{F['text']}")
        message = (
            f"SUBSTANTIVE divergence at word {int(word[1:])} ({word})"
            if word in {"w007", "w011", "w039"}
            else f"UNADJUDICATED variant at {word}"
        )
        assert any(message in error for error in errors)
        assert any(
            "apparatus_sha256 differs" in error
            for error in validate_bindings(root, source["graph"])
        )


@pytest.mark.parametrize("collection", ["uses", "witnesses", "collations"])
def test_complete_current_graph_inverse_rejects_unlisted_fields_and_recovers(collection):
    current = json.loads((ROOT / GRAPH).read_bytes())
    saved = deepcopy(current)
    before = before_lateran_graph(before_rosary_graph(before_additional_records(current)))
    assert canonical_hash(before) == F["before_graph_canonical_sha256"]
    row = record(current, collection, F["records"][collection]["after"]["id"])
    original = deepcopy(row)
    try:
        row["unexpected"] = True
        assert row != original
        with pytest.raises(AssertionError, match="exact Lateran source comparison inverse"):
            before_lateran_graph(before_rosary_graph(before_additional_records(current)))
    finally:
        row.clear()
        row.update(original)
        assert (
            current == saved
            and before_lateran_graph(before_rosary_graph(before_additional_records(current)))
            == before
        )


@pytest.mark.parametrize("fault", ["missing", "reading", "extra", "archive"])
def test_one_binding_only_inverse_preserves_all_old_objects_and_recovers(fault):
    current = json.loads((ROOT / REGISTRY).read_bytes())
    saved = deepcopy(current)
    same_bindings, same_archives = current["bindings"], current["archives"]
    before = before_lateran_registry(before_rosary_registry(before_additional_registry(current)))
    assert canonical_hash(before) == F["before_registry_canonical_sha256"]
    assert (
        before["archives"]
        == before_rosary_registry(before_additional_registry(current))["archives"]
    )
    assert list(before["bindings"]) == [
        key
        for key in before_rosary_registry(before_additional_registry(current))["bindings"]
        if key != F["binding_id"]
    ]
    try:
        if fault == "missing":
            del same_bindings[F["binding_id"]]
        elif fault == "reading":
            same_bindings[F["binding_id"]]["reading"][0]["first"] = 586
        elif fault == "extra":
            same_bindings[F["binding_id"]]["unexpected"] = True
        else:
            same_archives[F["archive_id"]]["sha256"] = "0" * 64
        assert current != saved
        with pytest.raises(AssertionError, match="exact Lateran registry successor"):
            before_lateran_registry(before_rosary_registry(before_additional_registry(current)))
    finally:
        same_bindings.clear()
        same_bindings.update(deepcopy(saved["bindings"]))
        same_archives.clear()
        same_archives.update(deepcopy(saved["archives"]))
        assert current["bindings"] is same_bindings and current["archives"] is same_archives
        assert (
            current == saved
            and before_lateran_registry(before_rosary_registry(before_additional_registry(current)))
            == before
        )


@pytest.mark.parametrize("fault", ["contract", "payload", "uses", "selected"])
def test_exact_complete_current_subject_inverse_rejects_then_recovers(source, fault):
    _, subject = healthy(source)
    saved = deepcopy(subject)
    historical = before_lateran_records(subject)
    assert subject == saved and historical["contract"] == "witness-identity-2"
    assert "raw_resolution" not in historical
    try:
        if fault == "contract":
            subject["contract"] = "witness-identity-2"
        elif fault == "payload":
            subject["raw_resolution"]["binding"]["reading"].clear()
        elif fault == "uses":
            subject["source_uses"].clear()
        else:
            subject["selected_text"]["id"] += "-foreign"
        assert subject != saved
        with pytest.raises(AssertionError, match="exact Lateran source subject"):
            before_lateran_records(subject)
    finally:
        subject.clear()
        subject.update(saved)
        assert before_lateran_records(subject) == historical
        healthy(source)


def test_raw1_is_actor_eligible_but_unmarked_priest_is_mass_policy(source, monkeypatch):
    actual, _ = healthy(source)
    monkeypatch.setattr(attribute, "CORPUS", source["root"])
    doc = expand_core(json.loads((source["root"] / F["core"]).read_bytes()))
    saved = deepcopy(doc)
    actor = attribute._actor_sources(F["text"])
    assert actor.scope == "SCOPED" and len(actor.units) == 1 and len(actor.units[0]) == 1
    fragment, first, last, explicit = actor.units[0][0]
    assert fragment == actual.fragments[0] and first == last == 587 and explicit
    assert fragment.marker is None and fragment.marker_scope_verified
    assert attribute._owned_speakers(doc, actor.units[0]) == {"s01": "sacerdos"}
    assert attribute.span_covers(doc)
    assessment = attribute.assess(doc)
    assert assessment.scope == "SCOPED" and assessment.write_eligible
    assert assessment.proposals == {"s01": {"speaker": "sacerdos", "voice": "clara"}}
    assert attribute.voice_ruling(doc) == ("clara", "RG 511 e")
    other_category = deepcopy(doc)
    other_category["category"] = "orationes"
    assert attribute._owned_speakers(other_category, actor.units[0]) == {}
    assert doc == saved
    # No source performer prefix is invented and no authored ritual field is written.
    healthy(source)


@pytest.mark.parametrize("fault", ["method", "latin", "ritual", "extra"])
def test_whole_core_comparison_allows_only_the_documentary_method(source, fault):
    healthy(source)
    doc = json.loads((source["root"] / F["core"]).read_bytes())
    saved = deepcopy(doc)
    historical = before_lateran_core(doc)
    try:
        if fault == "method":
            doc["editorial"]["source"]["method"] += " Inherited runtime verified."
        elif fault == "latin":
            doc["segments"][0]["words"][0]["form"] = "Altered"
        elif fault == "ritual":
            doc["segments"][0]["speaker"] = "minister"
        else:
            doc["unexpected"] = True
        assert doc != saved
        with pytest.raises(AssertionError, match="exact Lateran core successor"):
            before_lateran_core(doc)
    finally:
        doc.clear()
        doc.update(saved)
        assert before_lateran_core(doc) == historical
        healthy(source)


def test_old_source_controls_and_documentary_history_remain_exact(source):
    healthy(source)
    for relative, expected in F["unchanged"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
    actual = (source["root"] / F["witness"]).read_text()
    assert all(line in actual.splitlines() for line in F["historical_lines"])
    old = [row for row in F["apparatus"]["adjudicated"] if row["class"] == "punctuation"]
    assert old == F["old_punctuation"]
    assert record(source["graph"], "witnesses", F["mr_id"]) == F["unchanged_mr_record"]


def test_snapshot_returns_independent_complete_source_values(source):
    healthy(source)
    snapshot = RawBindingSnapshot(source["root"])
    first = snapshot.resolve(source["root"] / F["witness"])
    saved = deepcopy(first.source)
    first.source["binding"]["reading"].clear()
    assert first.source != saved
    assert (
        snapshot.resolve(source["root"] / F["witness"]).source
        == saved
        == (F["expected_reading"]["source"])
    )
