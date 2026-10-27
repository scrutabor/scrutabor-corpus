"""A direct Common text binding is not an executed feast-selection claim."""

import hashlib
import json
import shutil
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

import pytest
import witness_header_fixture as headers
from chant_fragment_fixture import before_chant_graph, before_chant_registry
from test_main_ordo_registrations import before_exaltation_comparison

from build_reader.bibliography import public_text_evidence
from build_reader.bibliography_bindings import (
    BindingError,
    digest,
    validate_bindings,
    witness_subject,
)
from build_reader.layers import expand_core
from checks.apparatus import capital_accent_positions
from checks.collate import collate
from checks.raw_binding import BindingError as RawBindingError
from checks.raw_binding import RawBindingSnapshot, load_registry, resolve_binding

ROOT = Path(__file__).resolve().parents[1]
F = json.loads((ROOT / "tests/fixtures/joachim-source.json").read_text())
TEXT = "proprium.sancti-ioachim-confessoris-epistola"
REGISTRY = "witnesses/raw/bindings.json"
GRAPH = "bibliography/graph.json"


def write(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def record(graph, field, identity):
    rows = [r for r in graph[field] if r["id"] == identity]
    assert len(rows) == 1
    return rows[0]


@pytest.fixture
def source(tmp_path):
    full = json.loads((ROOT / GRAPH).read_bytes())
    graph = deepcopy(full)
    graph["uses"] = [r for r in graph["uses"] if r.get("address", {}).get("text") == TEXT]
    graph["witnesses"] = [r for r in graph["witnesses"] if r["text"] == TEXT]
    graph["collations"] = [r for r in graph["collations"] if r["text"] == TEXT]
    current = json.loads((ROOT / REGISTRY).read_bytes())
    registry = {
        "version": 1,
        "archives": {F["archive_id"]: deepcopy(current["archives"][F["archive_id"]])},
        "bindings": {F["binding_id"]: deepcopy(current["bindings"][F["binding_id"]])},
    }
    assert registry["archives"][F["archive_id"]] == F["archive"]
    assert registry["bindings"][F["binding_id"]] == F["binding"]
    paths = [F["witness"], F["mr"], F["apparatus_path"], F["core"], F["archive"]["path"]]
    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    write(tmp_path, REGISTRY, registry)
    return {"root": tmp_path, "graph": graph, "registry": registry, "files": [*paths, REGISTRY]}


def healthy(state):
    root, graph = state["root"], state["graph"]
    assert load_registry(root) == state["registry"]
    actual = resolve_binding(root / F["witness"], root)
    assert actual is not None and actual.text == F["literal"]
    assert actual.source == F["expected_source"], "complete direct Common source"
    assert actual.spans == ((root / F["archive"]["path"], 349, 349),)
    assert len(actual.fragments) == 1
    fragment = actual.fragments[0]
    assert (fragment.path, fragment.line, fragment.start, fragment.end) == (
        root / F["archive"]["path"],
        349,
        0,
        len(F["literal"]),
    )
    assert fragment.raw == fragment.text == F["literal"]
    assert fragment.marker is None and fragment.whole_line and not fragment.partial_contract
    assert fragment.binding_id == F["binding_id"] and fragment.framing == ()
    doc = json.loads((root / F["core"]).read_bytes())
    witness = record(graph, "witnesses", F["witness_id"])
    subject = witness_subject(root, witness, graph, doc)
    assert subject["raw_resolution"] == F["expected_source"]
    assert set(subject["source_uses"]) == {F["use_id"]}
    assert validate_bindings(root, graph) == []
    return actual, subject


@contextmanager
def recover(state):
    root = state["root"]
    same_graph, same_registry = state["graph"], state["registry"]
    saved_graph, saved_registry = deepcopy(same_graph), deepcopy(same_registry)
    files = {p: (root / p).read_bytes() for p in state["files"]}
    try:
        yield
    finally:
        same_graph.clear()
        same_graph.update(saved_graph)
        same_registry.clear()
        same_registry.update(saved_registry)
        for relative, raw in files.items():
            (root / relative).write_bytes(raw)
        assert state["graph"] is same_graph and state["registry"] is same_registry
        assert state["graph"] == saved_graph and state["registry"] == saved_registry
        assert all((root / p).read_bytes() == raw for p, raw in files.items())
        healthy(state)


def test_complete_current_common_bytes_and_all_sixty_nine_word_coordinates(source):
    actual, _ = healthy(source)
    raw = (source["root"] / F["archive"]["path"]).read_bytes()
    assert len(raw) == 23833 and hashlib.sha256(raw).hexdigest() == F["archive"]["sha256"]
    lines = raw.decode().splitlines()
    assert lines[345:349] == F["mass_frame"]
    assert lines[349] == "" and lines[350] == "[Graduale]"
    assert len(actual.text.split()) == len(F["words"]) == 69
    assert " ".join(r["literal"] for r in F["words"]) == actual.text
    for row in F["words"]:
        assert lines[row["line"] - 1][row["start"] : row["end"]] == row["literal"]


def test_pending_native_and_reader_boundaries_do_not_promote_source_review(source):
    _, subject = healthy(source)
    root, graph = source["root"], source["graph"]
    doc = json.loads((root / F["core"]).read_bytes())
    assert subject["contract"] == "witness-review-2"
    mr = record(graph, "witnesses", F["mr_id"])
    assert "source_dependencies" not in mr
    with pytest.raises(
        BindingError, match="complete explicit source_dependencies declaration required"
    ):
        witness_subject(root, mr, graph, doc)
    assert all(
        r["review"] == {"status": "pending"} for r in graph["witnesses"] + graph["collations"]
    )
    (public,) = [r for r in public_text_evidence(graph)["texts"] if r["id"] == TEXT]
    assert public["witnesses"] == [] and "collation" not in public
    entries = [r for g in public["source_groups"] for r in g["entries"]]
    assert (
        next(r for r in entries if r["id"] == F["use_id"])["claim"]
        == (F["records"]["uses"]["after"]["claim"])
    )
    assert "raw_resolution" not in json.dumps(public)


RAW_FAULTS = (
    ("obsolete-path", "witness path declarations differ from bound evidence"),
    ("proper-path", "witness path declarations differ from bound evidence"),
    ("archive-revision", "revision differs from binding"),
    ("binding-revision", "witness revision differs from its raw binding"),
    ("digest", "SHA-256 mismatch"),
    ("section", "source section does not match evidence"),
    ("section-line", "source section does not match evidence"),
    ("range", "invalid source line range"),
    ("framing", "reading contains framing or lies outside textual evidence"),
    ("repeat", "reading omits or repeats source text"),
    ("missing-binding", "raw-binding marker and registered witness identity disagree"),
    ("missing-marker", "raw-binding marker and registered witness identity disagree"),
    ("duplicate-marker", "raw-binding marker and registered witness identity disagree"),
    ("wrong-witness", "raw-binding marker and registered witness identity disagree"),
    ("missing-archive", "unknown archive"),
    ("path-traversal", "invalid confined path"),
    ("uncorrected-accent", "transcription differs from its exact ordered raw reading"),
    ("body-order", "transcription differs from its exact ordered raw reading"),
    ("raw-bytes", "SHA-256 mismatch"),
)


@pytest.mark.parametrize("fault,message", RAW_FAULTS, ids=[r[0] for r in RAW_FAULTS])
def test_actual_raw_contract_fault_and_same_subject_recovery(source, fault, message):
    healthy(source)
    root, registry = source["root"], source["registry"]
    with recover(source):
        old = deepcopy(registry)
        witness = root / F["witness"]
        old_text = witness.read_text()
        plan = registry["bindings"][F["binding_id"]]
        archive = registry["archives"][F["archive_id"]]
        if fault in {"obsolete-path", "proper-path"}:
            archive["upstream"] = (
                "obsolete/missa/Latin/Commune/C5.txt"
                if fault == "obsolete-path"
                else "web/www/missa/Latin/Sancti/08-16.txt"
            )
        elif fault == "archive-revision":
            archive["revision"] = "0" * 40
        elif fault == "binding-revision":
            plan["revision"] = "0" * 40
        elif fault == "digest":
            archive["sha256"] = "0" * 64
        elif fault == "section":
            plan["evidence"][0]["section"] = "Lectio1"
        elif fault == "section-line":
            plan["evidence"][0]["section_line"] = 345
        elif fault == "range":
            plan["reading"][0]["last"] = 348
        elif fault == "framing":
            plan["reading"][0]["first"] = 348
        elif fault == "repeat":
            plan["reading"].append(deepcopy(plan["reading"][0]))
        elif fault == "missing-binding":
            del registry["bindings"][F["binding_id"]]
        elif fault == "missing-marker":
            witness.write_text(old_text.replace(F["marker"], "", 1))
        elif fault == "duplicate-marker":
            witness.write_text(F["marker"] + old_text)
        elif fault == "wrong-witness":
            plan["witness"] = F["mr"]
        elif fault == "missing-archive":
            del registry["archives"][F["archive_id"]]
        elif fault == "path-traversal":
            archive["path"] = "witnesses/raw/../escape.txt"
        elif fault == "uncorrected-accent":
            witness.write_text(
                old_text.replace(F["literal"], F["literal"].replace("potuit", "pótuit"), 1)
            )
        elif fault == "body-order":
            tokens = F["literal"].split()
            tokens[0], tokens[1] = tokens[1], tokens[0]
            witness.write_text(old_text.replace(F["literal"], " ".join(tokens), 1))
        else:
            raw = root / F["archive"]["path"]
            raw.write_bytes(raw.read_bytes() + b"\n# changed\n")
        write(root, REGISTRY, registry)
        assert registry != old or witness.read_text() != old_text or fault == "raw-bytes"
        with pytest.raises(RawBindingError, match=message):
            resolve_binding(witness, root)


def test_self_consistent_office_reading_is_not_a_mass_profile(source):
    healthy(source)
    root, registry = source["root"], source["registry"]
    with recover(source):
        plan = registry["bindings"][F["binding_id"]]
        plan["evidence"] = [
            {
                "archive": F["archive_id"],
                "first": 39,
                "last": 42,
                "section": "Lectio1",
                "section_line": 36,
            }
        ]
        plan["reading"] = [{"archive": F["archive_id"], "first": 39, "last": 42}]
        lines = (root / F["archive"]["path"]).read_text().splitlines()
        declaration = F["archive"]["upstream"] + " [Lectio1] (lines 39-42)"
        text = (root / F["witness"]).read_text()
        text = text.replace(F["path_header"], "# path: " + declaration + "\n", 1)
        text = text.replace(F["literal"], " ".join(lines[38:42]), 1)
        (root / F["witness"]).write_text(text)
        write(root, REGISTRY, registry)
        reading = resolve_binding(root / F["witness"], root)
        assert reading is not None and reading.text == " ".join(lines[38:42])
        assert reading.source["contract"] == "raw-reading-1"
        assert reading.text != F["literal"]
        with pytest.raises(AssertionError, match=r"^exact Mass Lectio profile(?:\n|$)"):
            assert reading.source["binding"] == F["binding"], "exact Mass Lectio profile"


SOURCE_FAULTS = (
    ("evidence", "digital evidence_sha256 identifies neither"),
    ("raw-dependency", "source requires its explicit exact raw binding"),
    ("wrong-binding", "declared raw binding differs from registered resolution"),
    ("missing-inventory", "complete explicit source_dependencies declaration required"),
    ("transcript-digest", "transcription_sha256 differs from the complete bound transcript"),
    ("apparatus-digest", "apparatus_sha256 differs from the complete apparatus"),
    ("apparatus-summary", "apparatus summary differs from the actual adjudicated entries"),
    ("witness-review", "reviewed subject changed"),
    ("collation-review", "reviewed collation requires reviewed witness bindings"),
)


@pytest.mark.parametrize("fault,message", SOURCE_FAULTS, ids=[r[0] for r in SOURCE_FAULTS])
def test_actual_bibliographic_identity_fault_and_recovery(source, fault, message):
    healthy(source)
    root, graph = source["root"], source["graph"]
    with recover(source):
        saved = deepcopy(graph)
        use = record(graph, "uses", F["use_id"])
        witness = record(graph, "witnesses", F["witness_id"])
        collation = record(graph, "collations", F["collation_id"])
        if fault == "evidence":
            use["evidence_sha256"] = F["proper_sha256"]
        elif fault == "raw-dependency":
            witness["source_dependencies"]["raw_binding"] = None
        elif fault == "wrong-binding":
            witness["source_dependencies"]["raw_binding"] = "foreign-binding"
        elif fault == "missing-inventory":
            del witness["source_dependencies"]
        elif fault == "transcript-digest":
            witness["transcription_sha256"] = "0" * 64
        elif fault == "apparatus-digest":
            raw_sha = hashlib.sha256((root / F["apparatus_path"]).read_bytes()).hexdigest()
            assert raw_sha != collation["apparatus_sha256"]
            collation["apparatus_sha256"] = raw_sha
        elif fault == "apparatus-summary":
            collation["apparatus"]["entries"] = 1
        elif fault == "witness-review":
            witness["review"] = {"status": "reviewed", "sha256": "0" * 64}
        else:
            collation["review"] = {"status": "reviewed", "sha256": "0" * 64}
        assert graph != saved
        if fault == "missing-inventory":
            # A legacy pending identity remains valid but cannot become a review subject.
            assert validate_bindings(root, graph) == []
            doc = json.loads((root / F["core"]).read_bytes())
            with pytest.raises(BindingError, match=message):
                witness_subject(root, witness, graph, doc)
        else:
            assert any(message in error for error in validate_bindings(root, graph))


@pytest.mark.parametrize("fault", ["missing-accent", "capital-accent"])
def test_the_new_lowercase_acute_is_not_hidden_or_misclassified(source, fault):
    healthy(source)
    root = source["root"]
    with recover(source):
        path = root / F["apparatus_path"]
        app = json.loads(path.read_bytes())
        assert app == F["apparatus"]
        saved = deepcopy(app)
        assert capital_accent_positions(app) == []
        try:
            if fault == "missing-accent":
                app["adjudicated"].pop()
                write(root, F["apparatus_path"], app)
                doc = json.loads((root / F["core"]).read_bytes())
                errors, _, _ = collate(expand_core(doc), root / f"witnesses/{TEXT}")
                assert any("UNADJUDICATED variant at w045" in error for error in errors)
            else:
                app["adjudicated"][-1]["class"] = "capital-accent"
                assert any(
                    "changed acute on a lowercase letter" in error
                    for error in capital_accent_positions(app)
                )
            assert app != saved
        finally:
            app.clear()
            app.update(saved)
            assert app == saved and capital_accent_positions(app) == []


def predecessor_target_input(relative, value):
    """Exact expected-side target inverse, never a native input or hash substitute."""
    rule = F["target_input_successors"][relative]
    assert F["unchanged"][relative] == rule["before_raw_sha256"]
    assert digest(value) == rule["after_value_sha256"], "exact Joachim target successor"
    comparison = deepcopy(value)
    for change in reversed(rule["operations"]):
        field = comparison
        for key in change["key"][:-1]:
            field = field[key]
        assert field[change["key"][-1]] == change["after"], "exact Joachim target successor"
        field[change["key"][-1]] = deepcopy(change["before"])
    assert digest(comparison) == rule["before_value_sha256"], "exact Joachim target predecessor"
    return comparison


def test_real_collation_and_original_fields_remain_exact(source):
    healthy(source)
    root = source["root"]
    doc = json.loads((root / F["core"]).read_bytes())
    errors, warnings, stats = collate(expand_core(doc), root / f"witnesses/{TEXT}")
    assert errors == warnings == []
    assert (stats["words"], stats["witnesses"], stats["variants_adjudicated"]) == (69, 2, 2)
    assert stats["corrigenda"] == stats["substantive_variants"] == 0
    for relative, expected in F["unchanged"].items():
        raw_input = (ROOT / relative).read_bytes()
        if relative not in F["target_input_successors"]:
            assert hashlib.sha256(raw_input).hexdigest() == expected
            continue
        value = json.loads(raw_input)
        saved = deepcopy(value)
        predecessor = predecessor_target_input(relative, value)
        assert value == saved and predecessor is not value
        for fault in ("wrong", "missing", "extra"):
            try:
                if fault == "wrong":
                    key = next(iter(value))
                    value[key] = None
                elif fault == "missing":
                    del value[next(iter(value))]
                else:
                    value["unexpected_comparison_field"] = True
                assert value != saved
                with pytest.raises(
                    AssertionError, match=r"^exact Joachim target successor(?:\n|$)"
                ):
                    predecessor_target_input(relative, value)
            finally:
                value.clear()
                value.update(deepcopy(saved))
                assert value == saved
                assert predecessor_target_input(relative, value) == predecessor
    raw = (root / F["witness"]).read_text()
    assert F["historical_correction"] in raw and "# fetched: 2026-08-31\n" in raw
    assert F["apparatus"]["adjudicated"][0] == F["old_punctuation"]
    proper = (ROOT / F["proper_path"]).read_bytes()
    assert hashlib.sha256(proper).hexdigest() == F["proper_sha256"]
    lines = proper.decode().splitlines()
    assert "[Lectio]" not in lines
    assert lines[4].endswith("ex C5") and lines[6].endswith("ex C5")
    assert lines[9] == "ex C5;"


REGISTRY_FAULTS = (
    "missing-archive",
    "archive-path",
    "archive-revision",
    "archive-sha",
    "missing-binding",
    "witness",
    "binding-revision",
    "evidence",
    "reading",
    "references",
    "extra-field",
)


@pytest.mark.parametrize("fault", REGISTRY_FAULTS)
def test_exact_registry_comparison_inverse_rejects_changed_new_objects(fault):
    current = json.loads((ROOT / REGISTRY).read_bytes())
    saved = deepcopy(current)
    before = before_chant_registry(headers.before_joachim_registry(current))
    assert digest(before) == F["registry_before_canonical_sha256"]
    same_archives, same_bindings = current["archives"], current["bindings"]
    try:
        archive = current["archives"][F["archive_id"]]
        binding = current["bindings"][F["binding_id"]]
        if fault == "missing-archive":
            del same_archives[F["archive_id"]]
        elif fault.startswith("archive-"):
            archive[
                {
                    "archive-path": "upstream",
                    "archive-revision": "revision",
                    "archive-sha": "sha256",
                }[fault]
            ] += "-foreign"
        elif fault == "missing-binding":
            del same_bindings[F["binding_id"]]
        elif fault == "witness":
            binding["witness"] = F["mr"]
        elif fault == "binding-revision":
            binding["revision"] = "0" * 40
        elif fault == "evidence":
            binding["evidence"][0]["section_line"] = 36
        elif fault == "reading":
            binding["reading"][0]["last"] = 350
        elif fault == "references":
            binding["references"] = [{}]
        else:
            binding["optional"] = True
        assert current != saved
        with pytest.raises(AssertionError, match=r"^exact Joachim registry addition(?:\n|$)"):
            headers.before_joachim_registry(current)
    finally:
        same_archives.clear()
        same_archives.update(deepcopy(saved["archives"]))
        same_bindings.clear()
        same_bindings.update(deepcopy(saved["bindings"]))
        assert current["archives"] is same_archives and current["bindings"] is same_bindings
        assert current == saved
        assert before_chant_registry(headers.before_joachim_registry(current)) == before


@pytest.mark.parametrize("field", ["uses", "witnesses", "collations"])
def test_exact_complete_graph_comparison_and_recovery(field):
    graph = json.loads((ROOT / GRAPH).read_bytes())
    saved = deepcopy(graph)
    historical = before_exaltation_comparison(
        before_chant_graph(headers.before_joachim_records(graph))
    )
    assert digest(historical) == F["graph_before_canonical_sha256"]
    row = record(graph, field, F["records"][field]["after"]["id"])
    original = deepcopy(row)
    try:
        row["unexpected"] = True
        assert row != original
        with pytest.raises(
            AssertionError, match=r"^exact Joachim source comparison inverse(?:\n|$)"
        ):
            headers.before_joachim_records(graph)
    finally:
        row.clear()
        row.update(original)
        assert graph == saved
        assert (
            before_exaltation_comparison(before_chant_graph(headers.before_joachim_records(graph)))
            == historical
        )


@pytest.mark.parametrize("fault", ["header", "accent", "body", "extra-field"])
def test_actual_current_transcript_inverse_rejects_and_recovers(source, fault):
    healthy(source)
    root = source["root"]
    path = root / F["witness"]
    saved = path.read_bytes()
    comparison = headers.before_joachim_transcript(F["witness"], saved)
    assert hashlib.sha256(comparison).hexdigest() == F["transcript"]["before_sha256"]
    assert comparison != saved and path.read_bytes() == saved
    with recover(source):
        if fault == "header":
            changed = saved.replace(F["path_header"].encode(), b"# path: foreign\n", 1)
        elif fault == "accent":
            changed = saved.replace(
                F["literal"].encode(), F["literal"].replace("potuit", "pótuit").encode(), 1
            )
        else:
            changed = saved + (b" Altered body.\n" if fault == "body" else b"# note: extra\n")
        assert changed != saved
        path.write_bytes(changed)
        with pytest.raises(AssertionError, match=r"^complete current Joachim transcript(?:\n|$)"):
            headers.before_joachim_transcript(F["witness"], path.read_bytes())
    assert path.read_bytes() == saved
    assert headers.before_joachim_transcript(F["witness"], path.read_bytes()) == comparison


def test_returned_source_does_not_mutate_a_snapshot(source):
    healthy(source)
    root = source["root"]
    snapshot = RawBindingSnapshot(root)
    first = snapshot.resolve(root / F["witness"])
    saved = deepcopy(first.source)
    first.source["binding"]["reading"].clear()
    assert first.source != saved
    assert snapshot.resolve(root / F["witness"]).source == saved == F["expected_source"]
