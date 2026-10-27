"""A reusable two-word source stays literal and distinct from occurrence claims."""

import hashlib
import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import bibliography
from build_reader.bibliography import public_text_evidence
from build_reader.bibliography_bindings import BindingError, validate_bindings, witness_subject
from checks.raw_binding import BindingError as RawBindingError
from checks.raw_binding import resolve_binding

ROOT = Path(__file__).resolve().parents[1]
TEXT = "ordinarium.deo-gratias-epistolae"
REGISTRY = "witnesses/raw/bindings.json"
KEY = "deo-gratias-epistolae-44667ff"
ARCHIVE = "prayers"
REVISION = "44667ff518b8ff1439780470828b39714f5306a2"
RAW_SHA = "7bf86beb01c170212fa07438de45b16b321f117013321400d65c2229c6624d9b"
ITEM = "item.divinum-officium-missa.44667ff.prayers"
USE = f"use.{TEXT}.do44667ff"
WITNESS = f"witness.{TEXT}.do44667ff"
LITERAL = "Deo grátias."
PATH_HEADER = "# path: web/www/missa/Latin/Ordo/Prayers.txt [Deo gratias] (lines 81-82)\n"
PLAN = {
    "witness": f"witnesses/{TEXT}/do.txt",
    "revision": REVISION,
    "evidence": [
        {
            "archive": ARCHIVE,
            "first": 81,
            "last": 82,
            "section": "Deo gratias",
            "section_line": 81,
        }
    ],
    "references": [],
    "reading": [{"archive": ARCHIVE, "first": 82, "last": 82}],
}


def record(graph, collection, identity):
    rows = [row for row in graph[collection] if row["id"] == identity]
    assert len(rows) == 1
    return rows[0]


def files(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def subject(root, graph, doc):
    return witness_subject(root, record(graph, "witnesses", WITNESS), graph, doc)


@pytest.fixture
def response(tmp_path):
    root = tmp_path / "source"
    full = json.loads((ROOT / "bibliography/graph.json").read_bytes())
    use = deepcopy(record(full, "uses", USE))
    edition = deepcopy(record(full, "editions", use["edition"]))
    graph = {
        "schema_version": full["schema_version"],
        "works": [deepcopy(record(full, "works", edition["work"]))],
        "editions": [edition],
        "digital_items": [deepcopy(record(full, "digital_items", ITEM))],
        "uses": [use],
        "witnesses": [deepcopy(record(full, "witnesses", WITNESS))],
        "collations": [],
    }
    full_registry = json.loads((ROOT / REGISTRY).read_bytes())
    assert full_registry["bindings"][KEY] == PLAN
    registry = {
        "version": full_registry["version"],
        "archives": {ARCHIVE: deepcopy(full_registry["archives"][ARCHIVE])},
        "bindings": {KEY: deepcopy(PLAN)},
    }
    paths = ["texts/ordinarium/deo-gratias-epistolae.json", PLAN["witness"]]
    paths += [registry["archives"][ARCHIVE]["path"]]
    for relative in paths:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    (root / REGISTRY).write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    doc = json.loads((root / paths[0]).read_bytes())
    return root, graph, doc, registry


def test_complete_reusable_response_has_exact_raw_identity(response):
    root, _, doc, registry = response
    assert set(registry["bindings"]) == {KEY} and set(registry["archives"]) == {ARCHIVE}
    words = doc["segments"][0]["words"]
    assert [w["id"] for w in words] == ["w001", "w002"]
    assert " ".join(w["form"] + w.get("post", "") for w in words) == LITERAL
    archive = root / registry["archives"][ARCHIVE]["path"]
    raw = archive.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == RAW_SHA
    assert raw.decode().splitlines()[80:82] == ["[Deo gratias]", "R. Deo grátias."]
    resolved = resolve_binding(root / PLAN["witness"], root)
    assert resolved is not None and resolved.text == LITERAL
    assert resolved.source["contract"] == "raw-reading-1"
    assert resolved.source["binding_id"] == KEY and resolved.source["binding"] == PLAN
    assert set(resolved.source["archives"]) == {ARCHIVE}
    assert resolved.spans == ((archive, 82, 82),)
    assert len(resolved.fragments) == 1
    assert resolved.fragments[0].raw == "R. Deo grátias."
    assert resolved.fragments[0].text == LITERAL and resolved.fragments[0].marker == "R"


def test_pending_subject_withholds_review_without_changing_occurrence(response):
    root, graph, doc, _ = response
    before = deepcopy(graph)
    witness = record(graph, "witnesses", WITNESS)
    assert witness["coverage"] == {"kind": "full"}
    assert witness["review"] == {"status": "pending"}
    assert witness["source_dependencies"] == {"uses": [], "raw_binding": KEY}
    actual = subject(root, graph, doc)
    assert actual["contract"] == "witness-review-2"
    assert actual["raw_resolution"]["binding"] == PLAN
    assert set(actual["source_uses"]) == {USE}
    assert validate_bindings(root, graph) == []
    public = public_text_evidence(graph)["texts"]
    assert len(public) == 1 and public[0]["id"] == TEXT
    assert public[0]["witnesses"] == [] and "collation" not in public[0]
    assert {u["id"] for group in public[0]["source_groups"] for u in group["entries"]} == {USE}
    assert doc["segments"][0]["speaker"] == "minister"
    assert doc["segments"][0]["participation"] == {"lecta": {"gradus": 1, "source": "DMS 31 a"}}
    assert graph == before


def test_current_consultation_preserves_the_distinct_historical_fold(response):
    root, _, _, registry = response
    old = (ROOT / "witnesses/raw/do-ordo-prayers.txt").read_bytes()
    assert hashlib.sha256(old).hexdigest() == (
        "feb761b53b62cdcba177787fc30135d6befe06a5ab495e4f2f294d724fcb175a"
    )
    assert old.decode().splitlines()[81:83] == ["[Deo gratias]", "R. Deo grátias."]
    pinned = (root / registry["archives"][ARCHIVE]["path"]).read_bytes()
    assert old == pinned.replace(b"[Pater noster]\n", b"[Pater noster]\n# fold-ji: true\n", 1)
    transcript = (root / PLAN["witness"]).read_text()
    assert PATH_HEADER in transcript and f"# revision: {REVISION}\n" in transcript
    assert "2026-08-11 master fetch" in transcript
    assert "revision and byte identity remain unestablished" in transcript
    assert "# scope: reusable response only;" in transcript
    assert "\n".join(x for x in transcript.splitlines() if not x.startswith("#")) == LITERAL


DamageCase = tuple[str, type[ValueError], str]
CASES: tuple[DamageCase, ...] = (
    ("archive-bytes", RawBindingError, "SHA-256 mismatch"),
    ("binding-revision", RawBindingError, "witness revision differs"),
    ("heading", RawBindingError, "source section does not match evidence"),
    ("line", RawBindingError, "reading contains framing or lies outside textual evidence"),
    ("marker", RawBindingError, "raw-binding marker and registered witness identity disagree"),
    ("body", RawBindingError, "transcription differs from its exact ordered raw reading"),
    ("repeated-reading", RawBindingError, "reading omits or repeats source text"),
    (
        "missing-binding",
        RawBindingError,
        "raw-binding marker and registered witness identity disagree",
    ),
    ("missing-archive", RawBindingError, "unknown archive"),
    ("source-item", BindingError, "unknown source digital item"),
    ("item-revision", BindingError, "digital item revision or kind differs from raw binding"),
    ("source-digest", BindingError, "digital evidence_sha256 identifies neither"),
    ("duplicate-member", BindingError, "unknown, duplicate or out-of-order word coverage"),
    ("legacy-path", RawBindingError, "witness path declarations differ from bound evidence"),
)


@pytest.mark.parametrize("damage,error,message", CASES, ids=[case[0] for case in CASES])
def test_damage_rejects_and_same_fixture_recovers(response, damage, error, message):
    root, graph, doc, registry = response
    path = root / PLAN["witness"]
    healthy = subject(root, graph, doc)
    resolved = resolve_binding(path, root)
    assert resolved is not None and resolved.text == LITERAL
    saved_graph, saved_files = deepcopy(graph), files(root)
    broken = deepcopy(registry)
    try:
        if damage == "archive-bytes":
            archive = root / registry["archives"][ARCHIVE]["path"]
            archive.write_bytes(archive.read_bytes() + b"\n# changed outside reading\n")
        elif damage == "binding-revision":
            broken["bindings"][KEY]["revision"] = "0" * 40
        elif damage == "heading":
            broken["bindings"][KEY]["evidence"][0]["section"] = "Gloria tibi"
        elif damage == "line":
            broken["bindings"][KEY]["reading"][0].update(first=81, last=81)
        elif damage == "marker":
            raw = path.read_text()
            marker = f"# raw-binding: {KEY}\n"
            assert raw.count(marker) == 1
            path.write_text(raw.replace(marker, "", 1), encoding="utf-8")
        elif damage == "body":
            raw = path.read_text()
            assert raw.endswith(LITERAL + "\n")
            path.write_text(raw.removesuffix(LITERAL + "\n") + "Deo laudes.\n", encoding="utf-8")
        elif damage == "repeated-reading":
            broken["bindings"][KEY]["reading"].append(deepcopy(PLAN["reading"][0]))
        elif damage == "missing-binding":
            del broken["bindings"][KEY]
        elif damage == "missing-archive":
            del broken["archives"][ARCHIVE]
        elif damage == "source-item":
            record(graph, "uses", USE)["digital_item"] = "item.missing"
        elif damage == "item-revision":
            record(graph, "digital_items", ITEM)["revision"] = "0" * 40
        elif damage == "source-digest":
            record(graph, "uses", USE)["evidence_sha256"] = "0" * 64
        elif damage == "duplicate-member":
            record(graph, "witnesses", WITNESS)["coverage"] = {
                "kind": "words",
                "words": ["w001", "w001"],
            }
        else:
            assert damage == "legacy-path"
            raw = path.read_text()
            assert raw.count(PATH_HEADER) == 1
            wrong = PATH_HEADER.replace("lines 81-82", "heading 81; reading 82")
            path.write_text(raw.replace(PATH_HEADER, wrong, 1), encoding="utf-8")
        (root / REGISTRY).write_text(
            json.dumps(broken, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        assert graph != saved_graph or files(root) != saved_files
        with pytest.raises(error, match=message):
            if damage in {"source-item", "item-revision", "source-digest", "duplicate-member"}:
                subject(root, graph, doc)
            else:
                resolve_binding(path, root)
    finally:
        graph.clear()
        graph.update(saved_graph)
        for relative, raw in saved_files.items():
            (root / relative).write_bytes(raw)
    assert graph == saved_graph and files(root) == saved_files
    assert subject(root, graph, doc) == healthy
    recovered = resolve_binding(path, root)
    assert recovered is not None and recovered.text == LITERAL


@pytest.mark.parametrize(
    "collection,identity",
    [("digital_items", ITEM), ("uses", USE), ("witnesses", WITNESS)],
    ids=["digital-item", "use", "witness"],
)
def test_complete_graph_rejects_unsorted_new_source_and_recovers(collection, identity):
    graph, languages = bibliography.load(ROOT)
    saved, saved_languages = deepcopy(graph), deepcopy(languages)
    assert bibliography.validate(ROOT, graph, languages) == []
    assert graph == saved and languages == saved_languages
    matches = [(index, row) for index, row in enumerate(graph[collection]) if row["id"] == identity]
    assert len(matches) == 1
    original_index, record = matches[0]
    assert original_index < len(graph[collection]) - 1
    try:
        assert graph[collection].pop(original_index) is record
        graph[collection].append(record)
        assert graph != saved and graph[collection][-1] is record
        assert bibliography.validate(ROOT, graph, languages) == [
            f"bibliography.{collection}: records must be sorted by id"
        ]
        assert languages == saved_languages
    finally:
        graph.clear()
        graph.update(deepcopy(saved))
        assert graph == saved and languages == saved_languages
        assert bibliography.validate(ROOT, graph, languages) == []
    assert bibliography.load(ROOT) == (saved, saved_languages)
