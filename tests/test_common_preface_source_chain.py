"""The current Common Preface has a complete, still-pending source chain."""

import hashlib
import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest
from common_preface_source_fixture import DATA, without_common_preface_source_chain

from build_reader import bibliography
from build_reader.bibliography_bindings import (
    BindingError,
    collation_subject,
    digest,
    selected_text,
    validate_bindings,
    witness_subject,
)
from build_reader.layers import expand_core
from checks import raw_binding, witness_archive
from checks.collate import collate, load_witness
from checks.transcription import check_transcriptions

ROOT = Path(__file__).resolve().parents[1]
TEXT = DATA["text"]
FOLDER = f"witnesses/{TEXT}"
DO = f"witness.{TEXT}.do44667ff"
EO = f"witness.{TEXT}.handmissal-eo2025"
MR = f"witness.{TEXT}.mr1962"


def core(root):
    return json.loads((root / "texts/ordinarium/praefatio-communis.json").read_text())


def witness(graph, identifier):
    return next(row for row in graph["witnesses"] if row["id"] == identifier)


def subject(root, graph, identifier):
    return witness_subject(root, witness(graph, identifier), graph, core(root))


def healthy(root, graph):
    assert validate_bindings(root, graph) == []
    subjects = {identifier: subject(root, graph, identifier) for identifier in (DO, EO, MR)}
    assert all(s["contract"] == "witness-review-2" for s in subjects.values())
    row = next(c for c in graph["collations"] if c["text"] == TEXT)
    bound = collation_subject(root, row, core(root), subjects)
    assert bound["contract"] == "collation-review-2"
    assert set(bound["witnesses"]) == {DO, EO, MR}
    return subjects, row


@pytest.fixture(scope="module")
def actual():
    graph, languages = bibliography.load(ROOT)
    # This exact inverse first requires all six complete current additions and
    # both untouched earlier source uses; empty or foreign inventories fail.
    without_common_preface_source_chain(graph)
    assert digest(selected_text(core(ROOT))) == DATA["selected_sha256"]
    subjects, row = healthy(ROOT, graph)
    return graph, languages, subjects, row


def test_actual_three_witnesses_bind_real_raw_document_and_rubric_dependencies(actual):
    graph, _, subjects, row = actual
    active = sorted(p.stem for p in (ROOT / FOLDER).glob("*.txt"))
    assert active == ["do-44667ff", "handmissal-eo2025", "mr"]
    assert [w["id"] for w in graph["witnesses"] if w["text"] == TEXT] == sorted((DO, EO, MR))
    assert all(witness(graph, key)["review"] == {"status": "pending"} for key in (DO, EO, MR))
    assert row["review"] == {"status": "pending"}
    assert set(subjects[MR]["source_uses"]) == {
        f"use.{TEXT}.mr1962",
        f"use.{TEXT}.hand-position-rubric.mr1962",
    }
    assert subjects[DO]["raw_resolution"]["binding"] == DATA["binding"]
    assert subjects[EO]["document_resolution"]["documents"] == {
        f"use.{TEXT}.handmissal-eo2025": witness(graph, EO)["source_dependencies"]["documents"][0]
    }
    reading = raw_binding.resolve_binding(ROOT / FOLDER / "do-44667ff.txt", ROOT)
    assert reading is not None and reading.source["contract"] == "raw-reading-1"
    assert reading.spans == ((ROOT / DATA["archive"]["path"], 69, 69),)
    assert len(reading.text.split()) == 56
    meta, literal = load_witness(ROOT / FOLDER / "handmissal-eo2025.txt")
    assert len(literal.split()) == 56 and literal.split()[19] == "ætérnæ"
    assert meta["corrigenda"] == [
        (
            "ætérnæ",
            "ætérne",
            "the Common Preface prints the ligature, while the Sunday Preface directly above "
            "prints ætérne Deus; the surrounding address is vocative",
        )
    ]


def test_actual_collation_and_transcription_contracts_examine_the_whole_body(actual):
    errors, warnings, stats = collate(expand_core(core(ROOT)), ROOT / FOLDER)
    assert errors == warnings == []
    assert (stats["witnesses"], stats["partial"], stats["words"], stats["corrigenda"]) == (
        3,
        0,
        56,
        1,
    )
    assert stats["variants_adjudicated"] > 0
    assert check_transcriptions(ROOT / FOLDER) == ([], 1)


def test_archived_bytes_are_preserved_not_reinterpreted_or_counted_active(actual):
    assert (
        hashlib.sha256((ROOT / DATA["historical_raw_path"]).read_bytes()).hexdigest()
        == DATA["historical_raw_sha256"]
    )
    for move in DATA["moves"]:
        assert not (ROOT / move["from"]).exists()
        assert hashlib.sha256((ROOT / move["to"]).read_bytes()).hexdigest() == move["sha256"]
    historical = ROOT / FOLDER / "historical-2026-10-24/apparatus.json"
    assert (
        hashlib.sha256(historical.read_bytes()).hexdigest() == DATA["historical_apparatus_sha256"]
    )
    assert len(json.loads(historical.read_text())["adjudicated"]) == 21
    current = json.loads((ROOT / FOLDER / "apparatus.json").read_text())
    assert len(current["adjudicated"]) == 22
    assert {name for e in current["adjudicated"] for name in e["witnesses"]} == {
        "do-44667ff",
        "handmissal-eo2025",
        "mr",
    }


@pytest.mark.parametrize("language", [None, "pl", "en"])
def test_real_pending_chain_is_withheld_while_retained_source_uses_remain(actual, language):
    graph, languages, _, _ = actual
    package = bibliography.public_text_evidence(graph, languages[language] if language else None)
    rows = [row for row in package["texts"] if row["id"] == TEXT]
    assert len(rows) == 1
    assert rows[0]["witnesses"] == [] and "collation" not in rows[0]
    if language is None:
        uses = {e["id"] for group in rows[0]["source_groups"] for e in group["entries"]}
        assert {
            f"use.{TEXT}.mr1962",
            f"use.{TEXT}.do44667ff",
            f"use.{TEXT}.handmissal-eo2025",
        } <= uses


@pytest.fixture
def isolated(tmp_path, actual):
    graph = deepcopy(actual[0])
    graph["uses"] = [u for u in graph["uses"] if u.get("address", {}).get("text") == TEXT]
    graph["witnesses"] = [w for w in graph["witnesses"] if w["text"] == TEXT]
    graph["collations"] = [c for c in graph["collations"] if c["text"] == TEXT]
    (tmp_path / "texts/ordinarium").mkdir(parents=True)
    shutil.copyfile(
        ROOT / "texts/ordinarium/praefatio-communis.json",
        tmp_path / "texts/ordinarium/praefatio-communis.json",
    )
    shutil.copytree(ROOT / FOLDER, tmp_path / FOLDER)
    archive = tmp_path / DATA["archive"]["path"]
    archive.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / DATA["archive"]["path"], archive)
    shutil.copyfile(
        ROOT / "witnesses/raw/do-prefationes.txt", tmp_path / "witnesses/raw/do-prefationes.txt"
    )
    registry = {
        "version": 1,
        "archives": {"prefaces": DATA["archive"]},
        "bindings": {DATA["binding_id"]: DATA["binding"]},
    }
    write_registry(tmp_path, registry)
    healthy(tmp_path, graph)
    # The ordinary rglob validator still sees the archived legacy transcripts.
    # No broad exemption was added to make their relocation pass.
    assert witness_archive.check(tmp_path) == []
    return tmp_path, graph, deepcopy(registry)


def write_registry(root, registry):
    (root / raw_binding.REGISTRY).write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n"
    )


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "foreign",
        "page-swap",
        "wrong-region",
        "wrong-pdf",
        "boolean-page",
        "unknown-page",
        "malformed-page",
    ],
)
def test_document_contract_mutants_reject_and_recover(isolated, fault):
    root, graph, _ = isolated
    bad = deepcopy(graph)
    deps = witness(bad, EO)["source_dependencies"]
    document = deps["documents"][0]
    use = next(u for u in bad["uses"] if u["id"] == witness(bad, EO)["use"])
    if fault == "missing":
        deps.pop("documents")
    elif fault == "foreign":
        document["use"] += ".foreign"
    elif fault == "page-swap":
        # A real allowed Aufer page is not allowed for the Common Preface.
        document.update(
            pdf_page=6,
            printed="4",
            page_image_sha256="e554421da2c8241462b4f3d3bf46a64ee1f1a873362ff2623983da81ba3e07fe",
        )
        use["evidence_sha256"] = document["page_image_sha256"]
    elif fault == "wrong-region":
        document["region"] = "right-half"
    elif fault == "wrong-pdf":
        document["sha256"] = "0" * 64
    elif fault == "boolean-page":
        document["pdf_page"] = True
    elif fault == "unknown-page":
        document["pdf_page"] = 17
    else:
        document["printed"] = ["14"]
    with pytest.raises(BindingError):
        subject(root, bad, EO)
    healthy(root, graph)


@pytest.mark.parametrize(
    "fault",
    [
        "missing-declaration",
        "foreign-declaration",
        "wrong-section",
        "repeated-reading",
        "reordered-body",
    ],
)
def test_raw_contract_mutants_reject_even_with_recomputed_archive_identity(isolated, fault):
    root, graph, registry = isolated
    original_registry = deepcopy(registry)
    bad = deepcopy(graph)
    archive = root / DATA["archive"]["path"]
    original_bytes = archive.read_bytes()
    binding = registry["bindings"][DATA["binding_id"]]
    if fault == "missing-declaration":
        witness(bad, DO)["source_dependencies"]["raw_binding"] = None
    elif fault == "foreign-declaration":
        witness(bad, DO)["source_dependencies"]["raw_binding"] = "foreign-binding"
    elif fault == "wrong-section":
        binding["evidence"][0]["section"] = "Defunctorum"
    elif fault == "repeated-reading":
        binding["reading"].append(deepcopy(binding["reading"][0]))
    else:
        lines = original_bytes.decode().splitlines(keepends=True)
        assert lines[68].startswith("v. Vere dignum")
        lines[68] = lines[68].replace("v. Vere dignum", "v. dignum Vere", 1)
        archive.write_text("".join(lines))
        digest_value = hashlib.sha256(archive.read_bytes()).hexdigest()
        registry["archives"]["prefaces"]["sha256"] = digest_value
        next(u for u in bad["uses"] if u["id"] == witness(bad, DO)["use"])["evidence_sha256"] = (
            digest_value
        )
    write_registry(root, registry)
    try:
        expected_error = (
            BindingError
            if fault in {"missing-declaration", "foreign-declaration"}
            else raw_binding.BindingError
        )
        with pytest.raises(expected_error):
            subject(root, bad, DO)
    finally:
        archive.write_bytes(original_bytes)
        write_registry(root, original_registry)
    healthy(root, graph)


def test_collation_cannot_drop_an_apparatus_witness_and_still_claim_complete(isolated):
    root, graph, _ = isolated
    subjects, row = healthy(root, graph)
    bad = deepcopy(row)
    bad["witnesses"].remove(EO)
    with pytest.raises(BindingError, match="collation omits apparatus witness dependencies"):
        collation_subject(root, bad, core(root), subjects)
    healthy(root, graph)


def test_literal_eo_slip_cannot_be_silently_corrected_under_a_retained_corrigendum(isolated):
    root, graph, _ = isolated
    path = root / FOLDER / "handmissal-eo2025.txt"
    original = path.read_text()
    header, body = original.split("\nVere", 1)
    assert body.count("ætérnæ") == 1
    path.write_text(header + "\nVere" + body.replace("ætérnæ", "ætérne"))
    try:
        errors, _, _ = collate(expand_core(core(root)), root / FOLDER)
        assert any("corrigendum" in error for error in errors)
    finally:
        path.write_text(original)
    assert collate(expand_core(core(root)), root / FOLDER)[0] == []
    healthy(root, graph)


def test_exact_inverse_refuses_a_missing_rubric_dependency_or_entire_chain(actual):
    original = actual[0]
    for fault in ("rubric", "empty", "foreign-same-count"):
        bad = deepcopy(original)
        if fault == "rubric":
            witness(bad, MR)["source_dependencies"]["uses"] = []
        elif fault == "empty":
            for key, rows in DATA["additions"].items():
                added = {r["id"] for r in rows}
                bad[key] = [r for r in bad[key] if r["id"] not in added]
        else:
            witness(bad, DO)["id"] += ".foreign"
        with pytest.raises(AssertionError, match="current Common Preface source additions"):
            without_common_preface_source_chain(bad)
    without_common_preface_source_chain(original)


def assert_selected_source_subject(doc):
    if digest(selected_text(doc)) != DATA["selected_sha256"]:
        raise AssertionError("Common Preface selected Latin/ritual source subject")


def test_selected_source_identity_ignores_analysis_notes_but_not_latin(actual):
    original = core(ROOT)
    assert_selected_source_subject(original)
    changed = deepcopy(original)
    editorial = changed.setdefault("editorial", {})
    editorial["notes"] = editorial.get("notes", "") + " Synthetic source-scope control."
    editorial.setdefault("analysis_defaults", {})["confidence"] = "medium"
    assert changed != original
    # Analysis-only scope control, not an approval to change the annotation.
    assert selected_text(changed) == selected_text(original)
    assert_selected_source_subject(changed)
    changed = deepcopy(original)
    first = next(word for segment in changed["segments"] for word in segment.get("words", []))
    first["form"] += "x"
    assert selected_text(changed) != selected_text(original)
    with pytest.raises(
        AssertionError, match=r"^Common Preface selected Latin/ritual source subject$"
    ):
        assert_selected_source_subject(changed)
    assert_selected_source_subject(original)
