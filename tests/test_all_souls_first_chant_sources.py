"""Literal Common comparisons do not grant Mass-context or pending source approvals."""

import hashlib
import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest
import witness_header_fixture as headers
from chant_fragment_fixture import before_chant_registry
from lateran_epistle_source_fixture import before_lateran_registry
from rosary_gospel_source_fixture import before_rosary_registry

from build_reader.bibliography import public_text_evidence
from build_reader.bibliography_bindings import (
    BindingError,
    collation_subject,
    digest,
    validate_bindings,
    witness_subject,
)
from build_reader.layers import expand_core
from checks.collate import collate
from checks.raw_binding import BindingError as RawBindingError
from checks.raw_binding import resolve_binding

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = "witnesses/raw/bindings.json"
FIXTURE = json.loads(
    (ROOT / "tests/fixtures/all-souls-first-source-successors.json").read_text(encoding="utf-8")
)
PARTS = ("communio", "introitus")
RAW_FAULTS = (
    ("normalized", "transcription differs from its exact ordered raw reading"),
    ("order", "reading reorders textual fragments"),
    ("repeat", "reading omits or repeats source text"),
    ("marker", "raw-binding marker and registered witness identity disagree"),
    ("archive", "SHA-256 mismatch"),
    ("section", "source section does not match evidence"),
)


def record(graph, field, identifier):
    (row,) = [r for r in graph[field] if r["id"] == identifier]
    return row


def files(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def digital(root, graph, doc):
    return witness_subject(
        root, record(graph, "witnesses", f"witness.{doc['id']}.do44667ff"), graph, doc
    )


def restore(root, graph, saved_graph, saved_files):
    graph.clear()
    graph.update(deepcopy(saved_graph))
    for relative, raw in saved_files.items():
        (root / relative).write_bytes(raw)
    assert graph == saved_graph and files(root) == saved_files


@pytest.fixture
def chants(tmp_path):
    root = tmp_path / "chants"
    full = json.loads((ROOT / "bibliography/graph.json").read_bytes())
    texts = {case["text"] for case in FIXTURE["cases"].values()}
    witnesses = [deepcopy(row) for row in full["witnesses"] if row["text"] in texts]
    assert len(witnesses) == 4
    uses = [deepcopy(record(full, "uses", row["use"])) for row in witnesses]
    edition_ids = {row["edition"] for row in uses}
    item_ids = {row["digital_item"] for row in uses}
    editions = [deepcopy(record(full, "editions", i)) for i in sorted(edition_ids)]
    work_ids = {row["work"] for row in editions}
    graph = {
        "schema_version": full["schema_version"],
        "works": [deepcopy(record(full, "works", i)) for i in sorted(work_ids)],
        "editions": editions,
        "digital_items": [deepcopy(record(full, "digital_items", i)) for i in sorted(item_ids)],
        "uses": sorted(uses, key=lambda row: row["id"]),
        "witnesses": sorted(witnesses, key=lambda row: row["id"]),
        "collations": [deepcopy(row) for row in full["collations"] if row["text"] in texts],
    }
    current = json.loads((ROOT / REGISTRY).read_bytes())
    plans = {
        case["binding_id"]: deepcopy(current["bindings"][case["binding_id"]])
        for case in FIXTURE["cases"].values()
    }
    assert all(plans[case["binding_id"]] == case["binding"] for case in FIXTURE["cases"].values())
    contributors = {
        item["archive"]
        for plan in plans.values()
        for field in ("evidence", "references", "reading")
        for item in plan[field]
    }
    assert contributors == set(FIXTURE["archive"])
    registry = {
        "version": current["version"],
        "archives": {key: deepcopy(current["archives"][key]) for key in sorted(contributors)},
        "bindings": plans,
    }
    assert registry["archives"] == FIXTURE["archive"]
    paths = [f"texts/proprium/{text.split('.', 1)[1]}.json" for text in sorted(texts)]
    paths += [
        f"witnesses/{text}/{name}"
        for text in sorted(texts)
        for name in ("do.txt", "mr.txt", "apparatus.json")
    ]
    paths += [row["path"] for row in registry["archives"].values()]
    for relative in paths:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    registry_raw = (json.dumps(registry, ensure_ascii=False, indent=2) + "\n").encode()
    (root / REGISTRY).write_bytes(registry_raw)
    assert len(registry["bindings"]) == 2 and len(registry["archives"]) == 1
    return root, graph, registry


def document(root, part):
    text = FIXTURE["cases"][part]["text"]
    return json.loads((root / f"texts/proprium/{text.split('.', 1)[1]}.json").read_bytes())


@pytest.mark.parametrize("part", PARTS)
def test_complete_literal_readings_and_every_raw_word_coordinate(chants, part):
    root, _, _ = chants
    case = FIXTURE["cases"][part]
    resolved = resolve_binding(root / case["binding"]["witness"], root)
    assert resolved is not None and resolved.text == case["literal"]
    assert resolved.source["contract"] == "raw-reading-2"
    assert resolved.source["binding_id"] == case["binding_id"]
    assert resolved.source["binding"] == case["binding"]
    assert resolved.source["archives"] == FIXTURE["archive"]
    assert len(resolved.fragments) == (4 if part == "communio" else 3)
    (archive,) = FIXTURE["archive"].values()
    lines = (root / archive["path"]).read_text(encoding="utf-8").splitlines()
    words = document(root, part)["segments"][0]["words"]
    assert len(words) == len(case["memberships"]) == (31 if part == "communio" else 40)
    assert [word["id"] for word in words] == [row["word"] for row in case["memberships"]]
    assert " ".join(row["literal"] for row in case["memberships"]) == resolved.text
    for row in case["memberships"]:
        assert lines[row["line"] - 1][row["start"] : row["end"]] == row["literal"]
    if part == "communio":
        assert [fragment.line for fragment in resolved.fragments] == [419, 420, 421, 422]
        assert resolved.fragments[1].start == resolved.fragments[3].start == 2
        assert not resolved.fragments[1].whole_line and not resolved.fragments[3].whole_line
    else:
        assert [fragment.line for fragment in resolved.fragments] == [283, 285, 286]
        assert resolved.fragments[0].text == resolved.fragments[2].text


@pytest.mark.parametrize("part", PARTS)
def test_native_subjects_and_collation_remain_pending_not_public_approvals(chants, part):
    root, graph, _ = chants
    doc = document(root, part)
    saved = deepcopy(graph)
    subjects = {}
    for witness in [row for row in graph["witnesses"] if row["text"] == doc["id"]]:
        assert witness["review"] == {"status": "pending"}
        assert witness["coverage"] == {"kind": "full"}
        subject = witness_subject(root, witness, graph, doc)
        assert subject["contract"] == "witness-review-2"
        assert set(subject["source_uses"]) == {witness["use"]}
        subjects[witness["id"]] = subject
    assert subjects[f"witness.{doc['id']}.mr1962"]["raw_resolution"] is None
    assert subjects[f"witness.{doc['id']}.do44667ff"]["raw_resolution"]["contract"] == (
        "raw-reading-2"
    )
    (collation,) = [row for row in graph["collations"] if row["text"] == doc["id"]]
    assert collation["review"] == {"status": "pending"}
    actual = collation_subject(root, collation, doc, subjects)
    assert actual["contract"] == "collation-review-2"
    apparatus = json.loads((root / f"witnesses/{doc['id']}/apparatus.json").read_bytes())
    assert apparatus == FIXTURE["cases"][part]["apparatus"]
    assert collation["apparatus_sha256"] == digest(apparatus)
    assert validate_bindings(root, graph) == []
    errors, warnings, stats = collate(expand_core(doc), root / f"witnesses/{doc['id']}")
    assert errors == warnings == []
    assert stats["witnesses"] == 2 and stats["words"] == (31 if part == "communio" else 40)
    assert stats["corrigenda"] == 0
    assert stats["variants_adjudicated"] == (1 if part == "communio" else 0)
    assert stats["orthographic"] == (0 if part == "communio" else 1)
    (public,) = [row for row in public_text_evidence(graph)["texts"] if row["id"] == doc["id"]]
    assert public["witnesses"] == [] and "collation" not in public
    assert graph == saved


@pytest.mark.parametrize("part", PARTS)
@pytest.mark.parametrize(
    "fault,message",
    RAW_FAULTS,
    ids=(
        "normalized-body",
        "reading-order",
        "repeated-reading",
        "marker",
        "archive",
        "section",
    ),
)
def test_actual_literal_damage_and_same_file_recovery(chants, part, fault, message):
    root, graph, registry = chants
    case = FIXTURE["cases"][part]
    path = root / case["binding"]["witness"]
    healthy = resolve_binding(path, root)
    assert healthy is not None
    saved_graph, saved_files = deepcopy(graph), files(root)
    changed = deepcopy(registry)
    plan = changed["bindings"][case["binding_id"]]
    try:
        if fault == "normalized":
            raw = path.read_bytes()
            old, new = ("Requiem", "Réquiem") if part == "communio" else ("Jerúsalem", "Ierúsalem")
            assert raw.count(old.encode()) == 1
            path.write_bytes(raw.replace(old.encode(), new.encode(), 1))
        elif fault == "order":
            plan["reading"][0], plan["reading"][1] = plan["reading"][1], plan["reading"][0]
        elif fault == "repeat":
            plan["reading"].append(deepcopy(plan["reading"][-1]))
        elif fault == "marker":
            marker = f"# raw-binding: {case['binding_id']}\n".encode()
            assert path.read_bytes().count(marker) == 1
            path.write_bytes(path.read_bytes().replace(marker, b"", 1))
        elif fault == "archive":
            (archive,) = changed["archives"].values()
            archive_path = root / archive["path"]
            archive_path.write_bytes(archive_path.read_bytes() + b"\n")
        else:
            plan["evidence"][0]["section_line"] += 1
        (root / REGISTRY).write_text(json.dumps(changed, ensure_ascii=False, indent=2) + "\n")
        assert files(root) != saved_files
        with pytest.raises(RawBindingError, match=message):
            resolve_binding(path, root)
    finally:
        restore(root, graph, saved_graph, saved_files)
    assert resolve_binding(path, root) == healthy


@pytest.mark.parametrize("fault", ("offset", "text"))
def test_real_response_fragment_boundary_and_same_registry_recovery(chants, fault):
    root, graph, registry = chants
    case = FIXTURE["cases"]["communio"]
    saved_graph, saved_files = deepcopy(graph), files(root)
    healthy = resolve_binding(root / case["binding"]["witness"], root)
    changed = deepcopy(registry)
    fragment = changed["bindings"][case["binding_id"]]["evidence"][1]["fragment"]
    try:
        if fault == "offset":
            fragment["start"] = 3
        else:
            fragment["text"] += "!"
        assert changed != registry
        (root / REGISTRY).write_text(json.dumps(changed, ensure_ascii=False, indent=2) + "\n")
        message = (
            "fragment splits a source token"
            if fault == "offset"
            else "fragment text, marker context or boundary reason differs"
        )
        with pytest.raises(RawBindingError, match=message):
            resolve_binding(root / case["binding"]["witness"], root)
    finally:
        restore(root, graph, saved_graph, saved_files)
    assert resolve_binding(root / case["binding"]["witness"], root) == healthy


@pytest.mark.parametrize("part", PARTS)
def test_actual_proper_context_is_not_a_resolved_sacred_archive(chants, part):
    root, graph, _ = chants
    doc = document(root, part)
    healthy = digital(root, graph, doc)
    saved = deepcopy(graph)
    use = deepcopy(FIXTURE["cases"][part]["context_use"])
    try:
        graph["uses"].append(use)
        graph["uses"].sort(key=lambda row: row["id"])
        record(graph, "witnesses", f"witness.{doc['id']}.do44667ff")["source_dependencies"][
            "uses"
        ] = [use["id"]]
        assert graph != saved
        with pytest.raises(BindingError, match="digital evidence_sha256 identifies neither"):
            digital(root, graph, doc)
    finally:
        graph.clear()
        graph.update(saved)
    assert graph == saved and digital(root, graph, doc) == healthy


@pytest.mark.parametrize("part", PARTS)
@pytest.mark.parametrize("fault", ("raw-hash", "entry", "transcript"))
def test_actual_source_identity_damage_and_exact_recovery(chants, part, fault):
    root, graph, _ = chants
    doc = document(root, part)
    saved_graph, saved_files = deepcopy(graph), files(root)
    assert validate_bindings(root, graph) == []
    (collation,) = [row for row in graph["collations"] if row["text"] == doc["id"]]
    try:
        if fault == "raw-hash":
            path = root / f"witnesses/{doc['id']}/apparatus.json"
            collation["apparatus_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            assert collation["apparatus_sha256"] != digest(json.loads(path.read_bytes()))
            message = "apparatus_sha256 differs from the complete apparatus"
        elif fault == "entry":
            path = root / f"witnesses/{doc['id']}/apparatus.json"
            app = json.loads(path.read_bytes())
            app["adjudicated"] = []
            app["summary"] = {"entries": 0, "classes": []}
            path.write_text(json.dumps(app, ensure_ascii=False, indent=2) + "\n")
            collation["apparatus_sha256"] = digest(app)
            collation["apparatus"] = app["summary"]
            message = (
                "UNADJUDICATED variant at w014"
                if part == "communio"
                else "SUBSTANTIVE divergence at word 22 (w022)"
            )
        else:
            witness = record(graph, "witnesses", f"witness.{doc['id']}.do44667ff")
            witness["transcription_sha256"] = "0" * 64
            message = "transcription_sha256 differs from the complete bound transcript"
        assert graph != saved_graph or files(root) != saved_files
        if fault == "entry":
            # Consistent hashes cannot authorize erasing a real source divergence.
            assert validate_bindings(root, graph) == []
            errors, _, _ = collate(expand_core(doc), root / f"witnesses/{doc['id']}")
        else:
            errors = validate_bindings(root, graph)
        assert any(message in error for error in errors)
    finally:
        restore(root, graph, saved_graph, saved_files)
    assert validate_bindings(root, graph) == []
    errors, warnings, _ = collate(expand_core(doc), root / f"witnesses/{doc['id']}")
    assert errors == warnings == []


def test_directed_reprise_and_exact_header_successor(chants):
    root, graph, _ = chants
    rule = FIXTURE["scope_header"]
    raw = (root / rule["relative"]).read_bytes()
    assert raw.count(rule["added_line"].encode()) == 1
    assert headers.before_source_scope_header(rule["relative"], raw) != raw
    headers.assert_transcript_content(root, rule["relative"])
    text = FIXTURE["cases"]["introitus"]["text"]
    assert (
        record(graph, "uses", f"use.{text}.mr1962")["claim"]
        == (FIXTURE["cases"]["introitus"]["mr_claim"])
    )
    assert (
        "then directs repetition of the opening antiphon alone, without repeating the psalm"
        in (FIXTURE["cases"]["introitus"]["mr_claim"])
    )
    assert len(headers.TRANSCRIPTS) == len(headers.BY_ID) == 947
    row = headers.TRANSCRIPTS[rule["relative"]]
    assert rule["before_sha256"] == row["after_sha256"]
    assert (
        headers.expected_transcript(rule["relative"], row["before_sha256"])
        == (rule["before_sha256"])
    )


@pytest.mark.parametrize("fault", ("missing", "extra", "body"))
def test_exact_current_header_boundary_rejects_then_same_bytes_recover(chants, fault):
    root, _, _ = chants
    rule = FIXTURE["scope_header"]
    path = root / rule["relative"]
    saved = path.read_bytes()
    headers.assert_transcript_content(root, rule["relative"])
    try:
        if fault == "missing":
            changed = saved.replace(rule["added_line"].encode(), b"", 1)
        elif fault == "extra":
            changed = b"# scope: unsupported extra source assertion\n" + saved
        else:
            changed = saved + b"Synthetic body damage.\n"
        assert changed != saved
        path.write_bytes(changed)
        with pytest.raises(AssertionError, match="source-scope complete transcript"):
            headers.assert_transcript_content(root, rule["relative"])
    finally:
        path.write_bytes(saved)
    assert path.read_bytes() == saved
    headers.assert_transcript_content(root, rule["relative"])


@pytest.mark.parametrize("part", PARTS)
@pytest.mark.parametrize("fault", ("digest", "dependency", "basis", "review"))
def test_two_exact_mr_comparison_inverses_reject_damage_and_same_object_recovers(
    chants, part, fault
):
    _, graph, _ = chants
    text = FIXTURE["cases"][part]["text"]
    observed = record(graph, "witnesses", f"witness.{text}.mr1962")
    changed = deepcopy(observed)
    saved = deepcopy(changed)
    healthy = headers.before_privacy(changed)
    assert changed == observed
    try:
        if fault == "digest":
            changed["transcription_sha256"] = "0" * 64
        elif fault == "dependency":
            del changed["source_dependencies"]
        elif fault == "basis":
            changed["independence_basis"] += " Unrelated mutation."
        else:
            changed["review"] = {"status": "reviewed", "sha256": "0" * 64}
        assert changed != saved
        with pytest.raises(AssertionError, match="exact source-scope comparison inverse"):
            headers.before_privacy(changed)
    finally:
        changed.clear()
        changed.update(saved)
    assert changed == observed == saved
    assert headers.before_privacy(changed) == healthy


def test_only_two_new_plans_and_one_archive_extend_the_original_registry():
    current = json.loads((ROOT / REGISTRY).read_bytes())
    source_rows = json.loads((ROOT / "tests/fixtures/main-ordo-source-oracle.json").read_bytes())[
        "rows"
    ]
    plans = {row["id"]: row["expected_source"]["binding"] for row in source_rows}
    assert len(plans) == len(source_rows) == 49

    def check():
        before = before_chant_registry(
            headers.before_joachim_registry(
                before_rosary_registry(before_lateran_registry(current))
            )
        )
        for identity, expected in plans.items():
            assert before["bindings"].get(identity) == expected, "exact main Ordo plan"
            del before["bindings"][identity]
        for case in FIXTURE["cases"].values():
            assert before["bindings"].pop(case["binding_id"]) == case["binding"]
        for key, archive in FIXTURE["archive"].items():
            assert before["archives"].pop(key) == archive
        raw = (json.dumps(before, ensure_ascii=False, indent=2) + "\n").encode()
        assert hashlib.sha256(raw).hexdigest() == (
            "bb880b8c2b91834f90dda703e3cd60b9ad562158fbaacce24886f8413e1d9661"
        )

    check()
    identity = next(row["id"] for row in source_rows if row["text"] == "ordinarium.per-ipsum")
    for fault in ("missing", "profile", "witness", "revision", "contract", "extra"):
        saved = deepcopy(current)
        same_bindings = current["bindings"]
        try:
            plan = same_bindings[identity]
            if fault == "missing":
                del same_bindings[identity]
            elif fault == "profile":
                plan["profile"] += "-foreign"
            elif fault == "witness":
                plan["witness"] = "witnesses/ordinarium.kyrie/do.txt"
            elif fault == "revision":
                plan["revision"] = "0" * 40
            elif fault == "contract":
                plan["contract"] = "raw-reading-unsupported"
            else:
                plan["extra"] = True
            assert digest(current) != digest(saved)
            with pytest.raises(AssertionError, match=r"^exact main Ordo plan(?:\n|$)"):
                check()
        finally:
            same_bindings.clear()
            same_bindings.update(deepcopy(saved["bindings"]))
            assert current["bindings"] is same_bindings
            assert current == saved and digest(current) == digest(saved)
            check()
