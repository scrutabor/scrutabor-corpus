"""An explicit digital inventory must identify a real finite evidence subject."""

import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from build_reader.bibliography import load, validate
from build_reader.bibliography_bindings import (
    text_document,
    validate_bindings,
    witness_subject,
)
from checks.raw_binding import REGISTRY, RawBindingSnapshot

CORPUS = Path(__file__).resolve().parent.parent
TEXT = "proprium.dominica-vi-post-pentecosten-collecta"
PRIMARY = f"use.{TEXT}.do44667ff"
SUPPLEMENT = PRIMARY + ".same-source"
MESSAGE = "digital evidence_sha256 identifies neither"


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def select(graph):
    graph["witnesses"] = [w for w in graph["witnesses"] if w["text"] == TEXT]
    graph["collations"] = [c for c in graph["collations"] if c["text"] == TEXT]
    return next(w for w in graph["witnesses"] if w["use"] == PRIMARY)


@pytest.fixture
def bound(tmp_path):
    graph, _ = load(CORPUS)
    witness = select(graph)
    registry = json.loads((CORPUS / REGISTRY).read_text())
    binding = registry["bindings"][witness["source_dependencies"]["raw_binding"]]
    registry["bindings"] = {"pentecost-vi-collect": binding}
    for key in {entry["archive"] for entry in binding["evidence"] + binding["reading"]}:
        relative = registry["archives"][key]["path"]
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CORPUS / relative, path)
    shutil.copytree(CORPUS / "witnesses" / TEXT, tmp_path / "witnesses" / TEXT)
    relative = "texts/" + TEXT.replace(".", "/", 1) + ".json"
    (tmp_path / relative).parent.mkdir(parents=True)
    shutil.copyfile(CORPUS / relative, tmp_path / relative)
    (tmp_path / REGISTRY).write_bytes(encode(registry))
    return tmp_path, graph, witness, text_document(tmp_path, TEXT)


def subject(bound):
    root, graph, witness, doc = bound
    return witness_subject(root, witness, graph, doc)


def add_supplement(bound):
    _, graph, witness, _ = bound
    use = copy.deepcopy(next(u for u in graph["uses"] if u["id"] == PRIMARY))
    use["id"] = SUPPLEMENT
    graph["uses"].append(use)
    witness["source_dependencies"]["uses"] = [SUPPLEMENT]
    return use


@pytest.mark.parametrize("which", ["primary", "supplement"])
@pytest.mark.parametrize("bad", ["zero", "unrelated-real", "missing", "null", "array"])
def test_pending_primary_and_supplement_reject_wrong_evidence_and_restore(bound, which, bad):
    root, graph, _, _ = bound
    use = (
        add_supplement(bound)
        if which == "supplement"
        else next(u for u in graph["uses"] if u["id"] == PRIMARY)
    )
    healthy = subject(bound)
    assert validate_bindings(root, graph) == []
    previous = copy.deepcopy(use)
    if bad == "missing":
        del use["evidence_sha256"]
    else:
        use["evidence_sha256"] = {
            "zero": "0" * 64,
            "unrelated-real": hashlib.sha256(
                (CORPUS / "witnesses/raw/do-44667ff/missa/Latin/Tempora/Pent01-0r.txt").read_bytes()
            ).hexdigest(),
            "null": None,
            "array": [],
        }[bad]
    with pytest.raises(ValueError, match=MESSAGE):
        subject(bound)
    assert any(MESSAGE in error for error in validate_bindings(root, graph))
    use.clear()
    use.update(previous)
    assert subject(bound) == healthy
    assert validate_bindings(root, graph) == []


@pytest.mark.parametrize("which", ["primary", "supplement"])
@pytest.mark.parametrize("kind", ["proper", "macro", "reading"])
def test_named_alias_composite_and_expanded_reading_subjects_are_valid(bound, which, kind):
    root, graph, witness, _ = bound
    use = (
        add_supplement(bound)
        if which == "supplement"
        else next(u for u in graph["uses"] if u["id"] == PRIMARY)
    )
    reading = RawBindingSnapshot(root).resolve(root / f"witnesses/{TEXT}/do.txt")
    assert reading is not None
    assert reading.source["archives"]["pentecost-vi"]["upstream"].endswith("/Pent06-0.txt")
    assert reading.source["archives"]["prayers"]["upstream"].endswith("/Ordo/Prayers.txt")
    value = (
        hashlib.sha256((reading.text + "\n").encode()).hexdigest()
        if kind == "reading"
        else reading.source["archives"]["prayers" if kind == "macro" else "pentecost-vi"]["sha256"]
    )
    use["evidence_sha256"] = value
    assert subject(bound)["raw_resolution"] == reading.source
    assert witness["review"] == {"status": "pending"}
    assert validate_bindings(root, graph) == []


@pytest.mark.parametrize("change", ["missing-archive", "corrupt-archive", "revision"])
def test_existing_raw_integrity_is_not_replaced_by_evidence_membership(bound, change):
    root, graph, _, _ = bound
    healthy = subject(bound)
    registry_path = root / REGISTRY
    registry_bytes = registry_path.read_bytes()
    registry = json.loads(registry_bytes)
    path = root / registry["archives"]["pentecost-vi"]["path"]
    original = path.read_bytes()
    if change == "missing-archive":
        path.unlink()
    elif change == "corrupt-archive":
        path.write_bytes(original + b"\ncorrupt\n")
    else:
        registry["archives"]["pentecost-vi"]["revision"] = "0" * 40
        registry_path.write_bytes(encode(registry))
    with pytest.raises(ValueError):
        subject(bound)
    assert validate_bindings(root, graph)
    path.write_bytes(original)
    registry_path.write_bytes(registry_bytes)
    assert subject(bound) == healthy
    assert validate_bindings(root, graph) == []


def test_production_validator_checks_pending_evidence_and_scan_digests_separately():
    graph, languages = load(CORPUS)
    witness = select(graph)
    assert validate(CORPUS, graph, languages) == []
    use = next(u for u in graph["uses"] if u["id"] == PRIMARY)
    before = copy.deepcopy(use)
    use["evidence_sha256"] = "0" * 64
    assert any(MESSAGE in error for error in validate(CORPUS, graph, languages))
    use.clear()
    use.update(before)
    # Page-image hashes are not reinterpreted as DO raw-file identities.
    scan = next(u for u in graph["uses"] if u["id"] == f"use.{TEXT}.mr1962")
    previous = scan["evidence_sha256"]
    scan["evidence_sha256"] = "a" * 64
    assert validate(CORPUS, graph, languages) == []
    scan["evidence_sha256"] = previous
    assert witness["review"] == {"status": "pending"}
    assert validate(CORPUS, graph, languages) == []


def test_unknown_legacy_inventory_is_not_a_reviewable_fallback():
    graph, _ = load(CORPUS)
    text = "proprium.sanctissimae-trinitatis-alleluia"
    graph["witnesses"] = [w for w in graph["witnesses"] if w["text"] == text]
    graph["collations"] = [c for c in graph["collations"] if c["text"] == text]
    witness = next(w for w in graph["witnesses"] if w["transcription"] == "do")
    assert "source_dependencies" not in witness
    assert witness["review"] == {"status": "pending"}
    assert validate_bindings(CORPUS, graph) == []
    with pytest.raises(ValueError, match="complete explicit source_dependencies"):
        witness_subject(CORPUS, witness, graph, text_document(CORPUS, text))
