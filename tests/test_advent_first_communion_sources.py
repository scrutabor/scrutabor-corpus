"""A complete Communion keeps its literal source identity and pending reviews."""

import hashlib
import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.bibliography import public_text_evidence
from build_reader.bibliography_bindings import (
    BindingError,
    collation_subject,
    digest,
    validate_bindings,
    witness_subject,
)
from checks.document import check as check_document
from checks.raw_binding import BindingError as RawBindingError
from checks.raw_binding import resolve_binding

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.dominica-i-adventus-communio"
REGISTRY = "witnesses/raw/bindings.json"
KEY = "advent-i-communion"
ARCHIVE = "advent-i-b5e250b"
REVISION = "b5e250b0af79bc3fb4fc3ac631a622d8cb0f2a19"
RAW_SHA = "db065ed4bb77f9100aa0dacce7ac11668a331d6defd3ff5331aed19cfb7283f9"
LITERAL = "Dóminus dabit benignitátem: et terra nostra dabit fructum suum."
DO_ID = f"witness.{TEXT}.dob5e250b"
MR_ID = f"witness.{TEXT}.mr1962"
COLLATION_ID = f"collation.{TEXT}.mr1962-dob5e250b"
CONTROL_EDITION = "edition.divinum-officium-missa.44667ff"
CONTROL_ITEM = "item.divinum-officium-missa.44667ff.github"
PLAN = {
    "witness": f"witnesses/{TEXT}/do.txt",
    "revision": REVISION,
    "evidence": [
        {"archive": ARCHIVE, "first": 55, "last": 56, "section": "Communio", "section_line": 54}
    ],
    "references": [],
    "reading": [{"archive": ARCHIVE, "first": 56, "last": 56}],
}


def record(graph, collection, identity):
    rows = [row for row in graph[collection] if row["id"] == identity]
    assert len(rows) == 1
    return rows[0]


def file_bytes(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def digital_subject(root, graph, doc):
    return witness_subject(root, record(graph, "witnesses", DO_ID), graph, doc)


@pytest.fixture
def communion(tmp_path):
    root = tmp_path / "source"
    full_graph = json.loads((ROOT / "bibliography/graph.json").read_bytes())
    witnesses = [deepcopy(record(full_graph, "witnesses", i)) for i in (DO_ID, MR_ID)]
    uses = [deepcopy(record(full_graph, "uses", w["use"])) for w in witnesses]
    item_ids = {u["digital_item"] for u in uses} | {CONTROL_ITEM}
    edition_ids = {u["edition"] for u in uses} | {CONTROL_EDITION}
    editions = [deepcopy(record(full_graph, "editions", i)) for i in sorted(edition_ids)]
    work_ids = {e["work"] for e in editions}
    graph = {
        "schema_version": full_graph["schema_version"],
        "works": [deepcopy(record(full_graph, "works", i)) for i in sorted(work_ids)],
        "editions": editions,
        "digital_items": [
            deepcopy(record(full_graph, "digital_items", i)) for i in sorted(item_ids)
        ],
        "uses": sorted(uses, key=lambda row: row["id"]),
        "witnesses": sorted(witnesses, key=lambda row: row["id"]),
        "collations": [deepcopy(record(full_graph, "collations", COLLATION_ID))],
    }
    # The extra real item/edition is solely the same-byte wrong-revision control.
    registry = json.loads((ROOT / REGISTRY).read_bytes())
    binding = deepcopy(registry["bindings"][KEY])
    assert binding == PLAN
    contributors = {
        span["archive"]
        for field in ("evidence", "references", "reading")
        for span in binding[field]
    }
    assert contributors == {ARCHIVE}
    registry = {
        "version": registry["version"],
        "archives": {name: deepcopy(registry["archives"][name]) for name in contributors},
        "bindings": {KEY: binding},
    }
    registry_raw = (json.dumps(registry, ensure_ascii=False, indent=2) + "\n").encode()
    paths = [f"texts/proprium/{TEXT.split('.', 1)[1]}.json"]
    paths += [f"witnesses/{TEXT}/{name}" for name in ("do.txt", "mr.txt", "apparatus.json")]
    paths += [row["path"] for row in registry["archives"].values()]
    for relative in paths:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    registry_path = root / REGISTRY
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_bytes(registry_raw)
    doc = json.loads((root / paths[0]).read_bytes())
    return root, graph, doc, registry


def test_complete_literal_raw_reading_has_exact_membership(communion):
    root, _, doc, registry = communion
    assert len(doc["segments"]) == 1 and doc["segments"][0]["id"] == "s01"
    words = doc["segments"][0]["words"]
    assert [w["id"] for w in words] == [f"w{i:03}" for i in range(1, 10)]
    assert " ".join(w.get("pre", "") + w["form"] + w.get("post", "") for w in words) == LITERAL
    assert set(registry["bindings"]) == {KEY} and set(registry["archives"]) == {ARCHIVE}
    archive = root / registry["archives"][ARCHIVE]["path"]
    lines = archive.read_text(encoding="utf-8").splitlines()
    assert lines[53:56] == ["[Communio]", "!Ps 84:13.", LITERAL]
    resolved = resolve_binding(root / PLAN["witness"], root)
    assert resolved is not None and resolved.text == LITERAL
    assert resolved.source["contract"] == "raw-reading-1"
    assert resolved.source["binding_id"] == KEY and resolved.source["binding"] == PLAN
    assert set(resolved.source["archives"]) == {ARCHIVE}
    assert resolved.spans == ((archive, 56, 56),)
    assert len(resolved.fragments) == 1
    assert resolved.fragments[0].line == 56 and resolved.fragments[0].text == LITERAL
    assert resolved.fragments[0].marker is None


def test_complete_source_subjects_withhold_pending_reviews(communion):
    root, graph, doc, _ = communion
    assert check_document(doc, root / "texts/proprium/dominica-i-adventus-communio.json") == []
    before = deepcopy(graph)
    assert {w["id"] for w in graph["witnesses"]} == {DO_ID, MR_ID}
    subjects = {}
    for witness in graph["witnesses"]:
        assert witness["coverage"] == {"kind": "full"}
        assert witness["review"] == {"status": "pending"}
        assert witness["source_dependencies"] == {
            "uses": [],
            "raw_binding": KEY if witness["id"] == DO_ID else None,
        }
        subject = witness_subject(root, witness, graph, doc)
        assert set(subject["source_uses"]) == {witness["use"]}
        assert subject["contract"] == "witness-review-2"
        subjects[witness["id"]] = subject
    assert subjects[MR_ID]["raw_resolution"] is None
    assert subjects[DO_ID]["raw_resolution"]["binding"] == PLAN
    collation = record(graph, "collations", COLLATION_ID)
    assert collation["review"] == {"status": "pending"}
    assert set(collation["witnesses"]) == {DO_ID, MR_ID}
    assert collation["selected_text_sha256"] == digest(subjects[DO_ID]["selected_text"])
    assert collation["apparatus"] == {"entries": 0, "classes": []}
    assert collation_subject(root, collation, doc, subjects)["contract"] == "collation-review-2"
    assert validate_bindings(root, graph) == []
    evidence = public_text_evidence(graph)
    assert len(evidence["texts"]) == 1
    public = evidence["texts"][0]
    assert public["id"] == TEXT and public["witnesses"] == [] and "collation" not in public
    assert {entry["id"] for group in public["source_groups"] for entry in group["entries"]} == {
        w["use"] for w in graph["witnesses"]
    }
    assert graph == before


def test_same_byte_concordance_preserves_historical_header(communion):
    root, graph, _, registry = communion
    archive_raw = (root / registry["archives"][ARCHIVE]["path"]).read_bytes()
    assert len(archive_raw) == 3167 and hashlib.sha256(archive_raw).hexdigest() == RAW_SHA
    assert (
        archive_raw
        == (ROOT / "witnesses/raw/do-44667ff/missa/Latin/Tempora/Adv1-0.txt").read_bytes()
    )
    transcript = (root / PLAN["witness"]).read_text(encoding="utf-8")
    assert f"# revision: {REVISION}\n" in transcript
    assert "# fetched: 2026-08-10\n" in transcript
    assert f"# sha256: {RAW_SHA}\n" in transcript
    assert f"# raw-binding: {KEY}\n" in transcript
    assert transcript.splitlines()[-1] == LITERAL
    assert (root / f"witnesses/{TEXT}/mr.txt").read_text().splitlines()[-1] == LITERAL
    witness = record(graph, "witnesses", DO_ID)
    use = record(graph, "uses", witness["use"])
    item = record(graph, "digital_items", use["digital_item"])
    assert item["revision"] == REVISION and item["edition"] == use["edition"]
    assert record(graph, "digital_items", CONTROL_ITEM)["revision"] != REVISION
    assert not any(".do44667ff" in w["id"] for w in graph["witnesses"])


@pytest.mark.parametrize(
    "damage,error,message",
    [
        ("marker", RawBindingError, "raw-binding marker and registered witness identity disagree"),
        ("declared", BindingError, "declared raw binding differs from registered resolution"),
        ("reference", RawBindingError, "reading contains framing or lies outside textual evidence"),
        ("repeat", RawBindingError, "reading omits or repeats source text"),
        ("revision", BindingError, "digital item revision or kind differs from raw binding"),
        ("archive", RawBindingError, "SHA-256 mismatch"),
    ],
    ids=["marker", "declared", "reference", "repeat", "revision", "archive"],
)
def test_source_damage_is_rejected_and_same_copy_recovers(communion, damage, error, message):
    root, graph, doc, registry = communion
    witness_path = root / PLAN["witness"]
    healthy = digital_subject(root, graph, doc)
    assert resolve_binding(witness_path, root) is not None
    saved_graph, saved_files = deepcopy(graph), file_bytes(root)
    broken = deepcopy(registry)
    try:
        if damage in {"marker", "declared"}:
            raw = witness_path.read_bytes()
            assert raw.count(f"# raw-binding: {KEY}\n".encode()) == 1
            raw = raw.replace(f"# raw-binding: {KEY}\n".encode(), b"", 1)
            witness_path.write_bytes(raw)
            if damage == "declared":
                del broken["bindings"][KEY]
                record(graph, "witnesses", DO_ID)["transcription_sha256"] = hashlib.sha256(
                    raw
                ).hexdigest()
        elif damage == "reference":
            broken["bindings"][KEY]["reading"][0]["first"] = 55
            broken["bindings"][KEY]["reading"][0]["last"] = 55
        elif damage == "repeat":
            broken["bindings"][KEY]["reading"].append(deepcopy(PLAN["reading"][0]))
        elif damage == "revision":
            use = record(graph, "uses", record(graph, "witnesses", DO_ID)["use"])
            use["edition"], use["digital_item"] = CONTROL_EDITION, CONTROL_ITEM
        else:
            archive = root / registry["archives"][ARCHIVE]["path"]
            archive.write_bytes(archive.read_bytes() + b"\n# outside the selected reading\n")
        (root / REGISTRY).write_text(
            json.dumps(broken, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        assert graph != saved_graph or file_bytes(root) != saved_files
        with pytest.raises(error, match=message):
            if damage in {"declared", "revision"}:
                digital_subject(root, graph, doc)
            else:
                resolve_binding(witness_path, root)
    finally:
        graph.clear()
        graph.update(saved_graph)
        for relative, raw in saved_files.items():
            (root / relative).write_bytes(raw)
    assert graph == saved_graph and file_bytes(root) == saved_files
    assert digital_subject(root, graph, doc) == healthy
    assert resolve_binding(witness_path, root).text == LITERAL
