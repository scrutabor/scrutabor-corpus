"""A source review binds the complete declared derivation, not just its first page."""

import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from build_reader.bibliography import load, public_text_evidence, validate
from build_reader.bibliography_bindings import (
    collation_subject,
    digest,
    validate_bindings,
    witness_subject,
)
from checks import raw_binding
from checks.raw_binding import REGISTRY

CORPUS = Path(__file__).resolve().parent.parent
TEXT = "proprium.dominica-vi-post-pentecosten-collecta"
SUPPLEMENTS = sorted(
    f"use.{TEXT}.{suffix}.mr1962"
    for suffix in ("continued-body", "expanded-conclusion", "oration-boundaries")
)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


@pytest.fixture
def composite(tmp_path):
    graph = json.loads((CORPUS / "bibliography/graph.json").read_text())
    graph["witnesses"] = [w for w in graph["witnesses"] if w["text"] == TEXT]
    graph["collations"] = [c for c in graph["collations"] if c["text"] == TEXT]
    relative = f"texts/proprium/{TEXT.split('.', 1)[1]}.json"
    (tmp_path / relative).parent.mkdir(parents=True)
    shutil.copyfile(CORPUS / relative, tmp_path / relative)
    shutil.copytree(CORPUS / "witnesses" / TEXT, tmp_path / "witnesses" / TEXT)
    shutil.copytree(CORPUS / "witnesses/raw", tmp_path / "witnesses/raw")
    # Keep the real registry, including its existence checks for other witnesses.
    registry = json.loads((tmp_path / REGISTRY).read_text())
    for binding in registry["bindings"].values():
        destination = tmp_path / binding["witness"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CORPUS / binding["witness"], destination)
    for witness in graph["witnesses"]:
        witness["source_dependencies"] = {
            "uses": SUPPLEMENTS.copy() if witness["transcription"] == "mr" else [],
            "raw_binding": "pentecost-vi-collect" if witness["transcription"] == "do" else None,
        }
    return tmp_path, graph, json.loads((tmp_path / relative).read_text())


def source(composite, name="mr"):
    root, graph, doc = composite
    witness = next(w for w in graph["witnesses"] if w["transcription"] == name)
    return witness_subject(root, witness, graph, doc)


def approve_fixture(composite):
    root, graph, doc = composite
    subjects = {}
    for witness in graph["witnesses"]:
        subject = witness_subject(root, witness, graph, doc)
        witness["review"] = {"status": "reviewed", "sha256": digest(subject)}
        subjects[witness["id"]] = subject
    for collation in graph["collations"]:
        subject = collation_subject(root, collation, doc, subjects)
        collation["review"] = {"status": "reviewed", "sha256": digest(subject)}
    assert validate_bindings(root, graph) == []


@pytest.mark.parametrize("identifier", SUPPLEMENTS)
@pytest.mark.parametrize("field", ["claim", "evidence_sha256", "verified_on", "locator"])
def test_every_supplemental_claim_invalidates_review(composite, identifier, field):
    root, graph, _ = composite
    approve_fixture(composite)
    use = next(u for u in graph["uses"] if u["id"] == identifier)
    use[field] = {"printed": "changed"} if field == "locator" else "changed"
    assert any("reviewed subject changed" in e for e in validate_bindings(root, graph))


def test_same_reading_with_a_changed_raw_plan_invalidates_review(composite):
    root, graph, _ = composite
    approve_fixture(composite)
    registry = json.loads((root / REGISTRY).read_text())
    registry["bindings"]["pentecost-vi-collect"]["reading"][1:] = [
        {"archive": "prayers", "first": 96, "last": 96},
        {"archive": "prayers", "first": 97, "last": 97},
    ]
    write_json(root / REGISTRY, registry)
    assert any("reviewed subject changed" in e for e in validate_bindings(root, graph))


def test_complete_raw_archive_not_only_selected_lines_is_bound(composite):
    root, graph, _ = composite
    approve_fixture(composite)
    registry = json.loads((root / REGISTRY).read_text())
    record = registry["archives"]["pentecost-vi"]
    path = root / record["path"]
    data = path.read_bytes() + b"\n# changed outside selected lines\n"
    path.write_bytes(data)
    record["sha256"] = hashlib.sha256(data).hexdigest()
    write_json(root / REGISTRY, registry)
    assert any("digital evidence_sha256" in e for e in validate_bindings(root, graph))
    # A coherent new source digest still cannot preserve the prior review.
    use = next(u for u in graph["uses"] if u["id"] == f"use.{TEXT}.do44667ff")
    use["evidence_sha256"] = record["sha256"]
    assert any("reviewed subject changed" in e for e in validate_bindings(root, graph))


def test_wrong_raw_reference_target_cannot_receive_review(composite):
    root, _, _ = composite
    registry = json.loads((root / REGISTRY).read_text())
    registry["bindings"]["pentecost-vi-collect"]["references"][0]["target"] = 0
    write_json(root / REGISTRY, registry)
    with pytest.raises(ValueError, match="reference"):
        source(composite, "do")


@pytest.mark.parametrize(
    "change", ["absent", "duplicate", "unknown", "primary", "unsorted", "type"]
)
def test_review_subject_requires_an_explicit_sound_inventory(composite, change):
    _, graph, _ = composite
    witness = next(w for w in graph["witnesses"] if w["transcription"] == "mr")
    declaration = witness["source_dependencies"]
    if change == "absent":
        del witness["source_dependencies"]
    else:
        declaration["uses"] = {
            "duplicate": [SUPPLEMENTS[0]] * 2,
            "unknown": ["use.missing"],
            "primary": [witness["use"]],
            "unsorted": list(reversed(SUPPLEMENTS)),
            "type": [None],
        }[change]
    with pytest.raises(ValueError):
        source(composite)


@pytest.mark.parametrize("which", ["primary", "supplement"])
@pytest.mark.parametrize("change", ["cross-text", "wrong-role", "unknown-word", "item-edition"])
def test_direct_subject_validates_all_source_joins(composite, which, change):
    _, graph, _ = composite
    identifier = f"use.{TEXT}.mr1962" if which == "primary" else SUPPLEMENTS[0]
    use = next(u for u in graph["uses"] if u["id"] == identifier)
    if change == "cross-text":
        use["address"]["text"] = "other.text"
    elif change == "wrong-role":
        use["role"] = "historical_wording_basis"
    elif change == "unknown-word":
        use["address"] = {"kind": "word", "text": TEXT, "word": "w99999"}
    else:
        use["digital_item"] = "item.divinum-officium-missa.44667ff.github"
    with pytest.raises(ValueError):
        source(composite)


@pytest.mark.parametrize("collection", ["uses", "works", "editions", "digital_items", "witnesses"])
def test_direct_subject_rejects_duplicate_graph_identities(composite, collection):
    _, graph, _ = composite
    graph[collection].append(copy.deepcopy(graph[collection][0]))
    with pytest.raises(ValueError, match="duplicate"):
        source(composite)


def test_direct_subject_rejects_another_document(composite):
    composite[2]["id"] = "other.text"
    with pytest.raises(ValueError, match=r"text|document"):
        source(composite)


def test_nonpublishable_supplement_withholds_witness_and_collation(composite):
    _, graph, _ = composite
    approve_fixture(composite)
    next(u for u in graph["uses"] if u["id"] == SUPPLEMENTS[0])["decision"] = "REMOVE"
    record = next(r for r in public_text_evidence(graph)["texts"] if r["id"] == TEXT)
    assert all(w["use"] != f"use.{TEXT}.mr1962" for w in record["witnesses"])
    assert "collation" not in record


def test_unknown_legacy_inventory_stays_pending_not_reviewable(composite):
    root, graph, _ = composite
    for witness in graph["witnesses"]:
        del witness["source_dependencies"]
    assert validate_bindings(root, graph) == []
    witness = graph["witnesses"][0]
    witness["review"] = {"status": "reviewed", "sha256": "0" * 64}
    assert validate_bindings(root, graph)


def test_returned_subject_does_not_share_mutable_source_records(composite):
    before = digest(source(composite))
    subject = source(composite)
    subject["witness"]["coverage"]["kind"] = "corrupted"
    assert digest(source(composite)) == before


@pytest.mark.parametrize("change", ["missing-key", "extra-key", "array", "null", "bad-raw"])
def test_invalid_declaration_never_downgrades_to_legacy_pending(composite, change):
    root, graph, _ = composite
    witness = graph["witnesses"][0]
    value = witness["source_dependencies"]
    if change == "missing-key":
        del value["uses"]
    elif change == "extra-key":
        value["unknown"] = []
    elif change == "bad-raw":
        value["raw_binding"] = []
    else:
        witness["source_dependencies"] = [] if change == "array" else None
    assert validate_bindings(root, graph)


@pytest.mark.parametrize("which", ["uses", "raw"])
def test_unrelated_valid_records_do_not_change_a_subject(composite, which):
    root, graph, _ = composite
    before = digest(source(composite, "do"))
    if which == "uses":
        unrelated = next(u for u in graph["uses"] if u["address"].get("text") != TEXT)
        unrelated["claim"] += " Clarification outside this text."
    else:
        registry = json.loads((root / REGISTRY).read_text())
        record = registry["archives"]["rosary"]
        path = root / record["path"]
        data = path.read_bytes() + b"\n# unrelated source update\n"
        path.write_bytes(data)
        record["sha256"] = hashlib.sha256(data).hexdigest()
        write_json(root / REGISTRY, registry)
    assert digest(source(composite, "do")) == before


def test_another_item_of_the_same_edition_is_bound_but_allowed(composite):
    _, graph, _ = composite
    before = digest(source(composite))
    use = next(u for u in graph["uses"] if u["id"] == SUPPLEMENTS[0])
    alternate = copy.deepcopy(
        next(i for i in graph["digital_items"] if i["id"] == use["digital_item"])
    )
    alternate["id"] += ".another-item"
    graph["digital_items"].append(alternate)
    use["digital_item"] = alternate["id"]
    assert digest(source(composite)) != before


def test_cross_edition_supplement_is_not_silently_combined(composite):
    _, graph, _ = composite
    use = next(u for u in graph["uses"] if u["id"] == SUPPLEMENTS[0])
    use.update(
        edition="edition.divinum-officium-missa.44667ff",
        digital_item="item.divinum-officium-missa.44667ff.github",
    )
    with pytest.raises(ValueError, match="another edition"):
        source(composite)


@pytest.mark.parametrize("change", ["null", "another-id", "revision", "provider", "missing-source"])
def test_raw_identity_and_provider_are_not_optional(composite, change):
    root, graph, _ = composite
    witness = next(w for w in graph["witnesses"] if w["transcription"] == "do")
    use = next(u for u in graph["uses"] if u["id"] == witness["use"])
    item = next(i for i in graph["digital_items"] if i["id"] == use["digital_item"])
    if change == "null":
        witness["source_dependencies"]["raw_binding"] = None
    elif change == "another-id":
        witness["source_dependencies"]["raw_binding"] = "rosary-introit"
    elif change == "revision":
        item["revision"] = "0" * 40
    elif change == "provider":
        next(e for e in graph["editions"] if e["id"] == use["edition"])["work"] = (
            "work.missale-romanum"
        )
        item["record_url"] = "https://example.org/source"
    else:
        registry = json.loads((root / REGISTRY).read_text())
        (root / registry["archives"]["pentecost-vi"]["path"]).unlink()
    with pytest.raises((ValueError, OSError)):
        source(composite, "do")


def test_missing_legacy_digital_binding_is_not_an_explicit_empty_inventory():
    graph, _ = load(CORPUS)
    text = "proprium.sancti-ioannis-apostoli-et-evangelistae-postcommunio"
    witness = next(
        w for w in graph["witnesses"] if w["text"] == text and w["transcription"] == "do"
    )
    witness["source_dependencies"] = {"uses": [], "raw_binding": None}
    doc = json.loads((CORPUS / f"texts/proprium/{text.split('.', 1)[1]}.json").read_text())
    with pytest.raises(ValueError, match="explicit exact raw binding"):
        witness_subject(CORPUS, witness, graph, doc)


def test_validation_uses_one_registry_snapshot_and_each_archive_once(composite, monkeypatch):
    root, graph, _ = composite
    registry_calls, archive_reads = [], []
    original_load, original_read = raw_binding.load_registry, Path.read_bytes

    def counted_load(path):
        registry_calls.append(path)
        return original_load(path)

    def counted_read(path):
        archive_reads.append(path)
        return original_read(path)

    monkeypatch.setattr(raw_binding, "load_registry", counted_load)
    monkeypatch.setattr(Path, "read_bytes", counted_read)
    assert validate_bindings(root, graph) == []
    assert registry_calls == [root]
    assert len(archive_reads) == len(set(archive_reads)) == 2


@pytest.mark.parametrize(
    "change", ["duplicate", "cross-text", "identity-only", "different-latin", "single-witness"]
)
def test_collation_direct_api_rejects_incomplete_or_wrong_identity(composite, change):
    root, graph, doc = composite
    subjects = {w["id"]: witness_subject(root, w, graph, doc) for w in graph["witnesses"]}
    collation = graph["collations"][0]
    first = collation["witnesses"][0]
    if change == "duplicate":
        collation["witnesses"].append(first)
    elif change == "cross-text":
        subjects[first]["witness"]["text"] = "other.text"
    elif change == "different-latin":
        subjects[first]["selected_text"]["segments"][0]["words"][0]["form"] = "Alienum"
    elif change == "single-witness":
        collation["witnesses"] = [first]
    else:
        subjects[first]["contract"] = "witness-identity-2"
    with pytest.raises(ValueError):
        collation_subject(root, collation, doc, subjects)


def test_projection_never_promotes_an_unknown_legacy_inventory(composite):
    _, graph, _ = composite
    approve_fixture(composite)
    for witness in graph["witnesses"]:
        del witness["source_dependencies"]
    record = next(r for r in public_text_evidence(graph)["texts"] if r["id"] == TEXT)
    assert record["witnesses"] == []
    assert "collation" not in record


def test_emitter_rejects_a_stale_supplement_review_before_projection(
    composite, monkeypatch, tmp_path
):
    from build_reader import bibliography
    from build_reader.emit import emit

    _, graph, doc = composite
    _, languages = load(CORPUS)
    approve_fixture((CORPUS, graph, doc))
    use = next(u for u in graph["uses"] if u["id"] == SUPPLEMENTS[0])
    use["claim"] += " Changed dependency."
    monkeypatch.setattr(bibliography, "load", lambda root: (graph, languages))
    with pytest.raises(ValueError, match="reviewed subject changed"):
        emit(CORPUS, tmp_path / "out")
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "collection", ["uses", "works", "editions", "digital_items", "witnesses", "collations"]
)
def test_direct_graph_id_grammar_matches_full_validator(composite, collection):
    _, graph, _ = composite
    graph[collection][0]["id"] = "123"
    with pytest.raises(ValueError, match="identity"):
        source(composite)


@pytest.mark.parametrize("identifier", [None, True, [], "", "123", "1.leading", "bad_id"])
def test_direct_collation_requires_its_own_valid_id(composite, identifier):
    root, graph, doc = composite
    subjects = {w["id"]: witness_subject(root, w, graph, doc) for w in graph["witnesses"]}
    graph["collations"][0]["id"] = identifier
    with pytest.raises(ValueError, match="identity"):
        collation_subject(root, graph["collations"][0], doc, subjects)


def unsupported_html():
    graph, languages = load(CORPUS)
    witness = next(
        w
        for w in graph["witnesses"]
        if w["text"] == "orationes.angele-dei" and w["transcription"] == "compendium-2005"
    )
    doc = json.loads((CORPUS / "texts/orationes/angele-dei.json").read_text())
    return graph, languages, witness, doc


def test_unsupported_digital_provider_stays_pending_without_inventory():
    graph, languages, witness, _ = unsupported_html()
    assert "source_dependencies" not in witness
    assert witness["review"] == {"status": "pending"}
    assert validate(CORPUS, graph, languages) == []
    record = next(r for r in public_text_evidence(graph)["texts"] if r["id"] == witness["text"])
    assert not any(w["id"] == witness["id"] for w in record["witnesses"])


def test_unsupported_digital_provider_cannot_declare_empty_raw_inventory():
    graph, languages, witness, doc = unsupported_html()
    witness["source_dependencies"] = {"uses": [], "raw_binding": None}
    with pytest.raises(ValueError, match="unsupported born-digital"):
        witness_subject(CORPUS, witness, graph, doc)
    assert any("unsupported born-digital" in e for e in validate(CORPUS, graph, languages))


def test_emitter_rejects_review_for_unsupported_digital_provider(monkeypatch, tmp_path):
    from build_reader import bibliography
    from build_reader.emit import emit

    graph, languages, witness, _ = unsupported_html()
    witness["source_dependencies"] = {"uses": [], "raw_binding": None}
    witness["review"] = {"status": "reviewed", "sha256": "a" * 64}
    monkeypatch.setattr(bibliography, "load", lambda root: (graph, languages))
    with pytest.raises(ValueError, match="unsupported born-digital"):
        emit(CORPUS, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_unsupported_digital_supplement_cannot_hide_behind_scan_primary(composite):
    root, graph, _ = composite
    use = next(u for u in graph["uses"] if u["id"] == SUPPLEMENTS[0])
    item = copy.deepcopy(next(i for i in graph["digital_items"] if i["id"] == use["digital_item"]))
    item.update(id=item["id"] + ".digital", kind="born-digital")
    graph["digital_items"].append(item)
    use["digital_item"] = item["id"]
    with pytest.raises(ValueError, match="unsupported born-digital"):
        source(composite)
    assert any("unsupported born-digital" in e for e in validate_bindings(root, graph))


@pytest.mark.parametrize("kind", [None, [], "unknown"])
def test_direct_subject_rejects_invalid_digital_item_kind(composite, kind):
    _, graph, _ = composite
    use = next(u for u in graph["uses"] if u["id"] == SUPPLEMENTS[0])
    next(i for i in graph["digital_items"] if i["id"] == use["digital_item"])["kind"] = kind
    with pytest.raises(ValueError, match="digital item kind"):
        source(composite)


def test_scan_and_supported_digital_subjects_remain_reviewable(composite):
    assert source(composite)["raw_resolution"] is None
    assert source(composite, "do")["raw_resolution"]["binding_id"] == "pentecost-vi-collect"
    approve_fixture(composite)
    _, graph, _ = composite
    record = next(r for r in public_text_evidence(graph)["texts"] if r["id"] == TEXT)
    assert len(record["witnesses"]) == 2
    assert record["collation"]["apparatus"] == {
        "entries": 5,
        "classes": ["capitalization", "orthography", "punctuation"],
    }
