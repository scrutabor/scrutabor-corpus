"""Exact Marian source identities do not confer source-review approval."""

import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from build_reader.bibliography import load, public_text_evidence, validate
from build_reader.bibliography_bindings import (
    BindingError as SourceBindingError,
)
from build_reader.bibliography_bindings import (
    collation_subject,
    validate_bindings,
    witness_subject,
)
from checks.collate import collate
from checks.raw_binding import REGISTRY, BindingError, load_registry, resolve_binding

CORPUS = Path(__file__).resolve().parent.parent
SEVEN = "proprium.septem-dolorum-beatae-mariae-virginis-offertorium"
IMMACULATE = "proprium.immaculata-conceptio-graduale"
ASSUMPTION = "proprium.assumptio-beatae-mariae-virginis-offertorium"
TEXTS = (SEVEN, IMMACULATE, ASSUMPTION)
KEY = "do-proprium-septem-dolorum-beatae-mariae-virginis-offertorium"
REVISION = "44667ff518b8ff1439780470828b39714f5306a2"
SEVEN_CLAIM = (
    "At the pinned revision, the September 15 Offertorium inherits the July 16 Offertorium. "
    "Its shorter Marian wording is a substantive comparison to the selected printed text, "
    "as recorded in the apparatus."
)
SEVEN_LOCATOR = {
    "section": "web/www/missa/Latin/Sancti/09-15.txt [Offertorium] (lines 121-121); "
    "web/www/missa/Latin/Sancti/07-16.txt [Offertorium] (lines 38-39)"
}
EVIDENCE_ERROR = (
    "digital evidence_sha256 identifies neither a bound archive nor the complete resolved reading"
)


def row(graph, collection, identifier):
    matches = [value for value in graph[collection] if value["id"] == identifier]
    assert len(matches) == 1
    return matches[0]


def transcript(root, text=SEVEN, name="do"):
    return root / "witnesses" / text / f"{name}.txt"


def body(path):
    return " ".join(
        " ".join(line for line in path.read_text().splitlines() if not line.startswith("#")).split()
    )


def state(case):
    root, graph, docs, registry = case
    files = {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }
    return copy.deepcopy((graph, docs, registry)), files


@pytest.fixture
def sources(tmp_path):
    graph, _ = load(CORPUS)
    graph["witnesses"] = [w for w in graph["witnesses"] if w["text"] in TEXTS]
    graph["collations"] = [c for c in graph["collations"] if c["text"] in TEXTS]
    assert len(graph["witnesses"]) == 6 and len(graph["collations"]) == 3
    uses = {w["use"] for w in graph["witnesses"]}
    graph["uses"] = [u for u in graph["uses"] if u["id"] in uses]
    registry = load_registry(CORPUS)
    bindings = {}
    for witness in graph["witnesses"]:
        declaration = witness["source_dependencies"]
        assert declaration["uses"] == []
        key = declaration["raw_binding"]
        if key is not None:
            bindings[key] = copy.deepcopy(registry["bindings"][key])
    assert KEY in bindings and len(bindings) == 3
    registry["bindings"] = bindings
    archives = {item["archive"] for b in bindings.values() for item in b["evidence"]}
    assert len(archives) == 4
    registry["archives"] = {
        key: value for key, value in registry["archives"].items() if key in archives
    }
    for archive in registry["archives"].values():
        destination = tmp_path / archive["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CORPUS / archive["path"], destination)
    (tmp_path / REGISTRY).write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n")
    docs = {}
    for text in TEXTS:
        relative = Path("texts") / (text.replace(".", "/", 1) + ".json")
        (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CORPUS / relative, tmp_path / relative)
        shutil.copytree(CORPUS / "witnesses" / text, tmp_path / "witnesses" / text)
        docs[text] = json.loads((tmp_path / relative).read_text())
    assert validate_bindings(tmp_path, graph) == []
    return tmp_path, graph, docs, registry


def test_inherited_offertory_is_exact_and_not_the_complete_selected_print(sources):
    root, graph, docs, registry = sources
    snapshot = state(sources)
    binding = registry["bindings"][KEY]
    assert set(binding) == {"witness", "revision", "evidence", "references", "reading"}
    assert binding["revision"] == REVISION
    assert binding["evidence"] == [
        {
            "archive": "do-sancti-09-15",
            "first": 121,
            "last": 121,
            "section": "Offertorium",
            "section_line": 120,
        },
        {
            "archive": "do-sancti-07-16",
            "first": 38,
            "last": 39,
            "section": "Offertorium",
            "section_line": 37,
        },
    ]
    assert binding["references"] == [
        {"archive": "do-sancti-09-15", "line": 121, "text": "@Sancti/07-16", "target": 1}
    ]
    assert binding["reading"] == [{"archive": "do-sancti-07-16", "first": 39, "last": 39}]
    reading = resolve_binding(transcript(root), root)
    assert reading is not None and reading.source["contract"] == "raw-reading-1"
    assert set(reading.source["archives"]) == {"do-sancti-09-15", "do-sancti-07-16"}
    assert reading.text == body(transcript(root))
    assert len(reading.spans) == len(reading.fragments) == 1
    assert reading.spans == ((root / registry["archives"]["do-sancti-07-16"]["path"], 39, 39),)
    assert "# path: " + SEVEN_LOCATOR["section"] in transcript(root).read_text().splitlines()
    assert "Mater, in conspéctu Dei," in reading.text
    assert "Mater Dei, dum stéteris in conspéctu Dómini," in body(transcript(root, name="mr"))
    assert reading.text != body(transcript(root, name="mr"))
    errors, warnings, stats = collate(docs[SEVEN], transcript(root).parent)
    assert errors == warnings == []
    assert stats["substantive_spans"] == 1
    witness = row(graph, "witnesses", f"witness.{SEVEN}.do44667ff")
    use = row(graph, "uses", witness["use"])
    assert use["evidence_sha256"] == reading.source["archives"]["do-sancti-09-15"]["sha256"]
    healthy = witness_subject(root, witness, graph, docs[SEVEN])
    original_use = copy.deepcopy(use)
    accepted = [a["sha256"] for a in reading.source["archives"].values()]
    accepted.append(hashlib.sha256((reading.text + "\n").encode()).hexdigest())
    assert len(set(accepted)) == 3
    for evidence in accepted:
        use["evidence_sha256"] = evidence
        subject = witness_subject(root, witness, graph, docs[SEVEN])
        assert subject["raw_resolution"] == reading.source
        assert witness["review"] == {"status": "pending"}
    use.clear()
    use.update(original_use)
    assert witness_subject(root, witness, graph, docs[SEVEN]) == healthy
    assert state(sources) == snapshot


@pytest.mark.parametrize("change", ["missing", "target", "text"])
def test_inherited_reference_drift_has_an_owned_diagnostic_and_restore(sources, change):
    root, _, _, registry = sources
    snapshot = state(sources)
    healthy = resolve_binding(transcript(root), root)
    assert healthy is not None
    original = (root / REGISTRY).read_bytes()
    mutant = copy.deepcopy(registry)
    binding = mutant["bindings"][KEY]
    if change == "missing":
        binding["references"] = []
        expected = "incomplete source reference coverage"
    elif change == "target":
        binding["references"][0]["target"] = 0
        expected = "reference points to a different source or section"
    else:
        binding["references"][0]["text"] = "@Sancti/07-15"
        expected = "reference differs from source evidence"
    assert mutant != registry
    (root / REGISTRY).write_text(json.dumps(mutant, ensure_ascii=False, indent=2) + "\n")
    with pytest.raises(BindingError) as error:
        resolve_binding(transcript(root), root)
    assert str(error.value) == expected
    (root / REGISTRY).write_bytes(original)
    assert resolve_binding(transcript(root), root) == healthy
    assert state(sources) == snapshot


def test_printed_body_cannot_replace_the_shorter_digital_transcription(sources):
    root, _, _, _ = sources
    snapshot = state(sources)
    path = transcript(root)
    healthy = resolve_binding(path, root)
    assert healthy is not None
    original = path.read_bytes()
    header = [line for line in original.decode().splitlines() if line.startswith("#")]
    mutant = "\n".join([*header, body(transcript(root, name="mr")), ""])
    assert mutant.encode() != original
    path.write_text(mutant)
    with pytest.raises(BindingError) as error:
        resolve_binding(path, root)
    assert str(error.value) == "transcription differs from its exact ordered raw reading"
    path.write_bytes(original)
    assert resolve_binding(path, root) == healthy
    assert state(sources) == snapshot


@pytest.mark.parametrize("change", ["missing", "unrelated"])
def test_pending_evidence_rejects_a_missing_or_unrelated_digest_and_restores(sources, change):
    root, graph, docs, registry = sources
    snapshot = state(sources)
    witness = row(graph, "witnesses", f"witness.{SEVEN}.do44667ff")
    use = row(graph, "uses", witness["use"])
    original = copy.deepcopy(use)
    healthy = witness_subject(root, witness, graph, docs[SEVEN])
    if change == "missing":
        del use["evidence_sha256"]
    else:
        use["evidence_sha256"] = registry["archives"]["do-sancti-12-08"]["sha256"]
    assert use != original
    with pytest.raises(SourceBindingError) as error:
        witness_subject(root, witness, graph, docs[SEVEN])
    assert str(error.value) == EVIDENCE_ERROR
    assert any(EVIDENCE_ERROR in error for error in validate_bindings(root, graph))
    use.clear()
    use.update(original)
    assert witness_subject(root, witness, graph, docs[SEVEN]) == healthy
    assert validate_bindings(root, graph) == []
    assert state(sources) == snapshot


def test_complete_identities_leave_six_witnesses_and_three_collations_pending(sources):
    root, graph, docs, _ = sources
    snapshot = state(sources)
    subjects = {}
    for witness in graph["witnesses"]:
        assert witness["review"] == {"status": "pending"}
        assert witness["source_dependencies"]["uses"] == []
        assert (witness["source_dependencies"]["raw_binding"] is None) == (
            witness["transcription"] == "mr"
        )
        subjects[witness["id"]] = witness_subject(root, witness, graph, docs[witness["text"]])
    assert len(subjects) == 6
    for collation in graph["collations"]:
        assert collation["review"] == {"status": "pending"}
        subject = collation_subject(root, collation, docs[collation["text"]], subjects)
        assert subject["contract"] == "collation-review-2"
    assert len(graph["collations"]) == 3
    assert validate_bindings(root, graph) == []
    assert state(sources) == snapshot


def test_reader_projects_narrow_uses_without_pending_reviews_or_internal_fields(sources):
    snapshot = state(sources)
    graph, languages = load(CORPUS)
    graph_snapshot = copy.deepcopy(graph)
    assert validate(CORPUS, graph, languages) == []
    use = row(graph, "uses", f"use.{SEVEN}.do44667ff")
    assert use["claim"] == SEVEN_CLAIM and use["locator"] == SEVEN_LOCATOR
    edition = row(graph, "editions", "edition.missale-romanum.1962-typica")
    assert edition["edition_statement"] == "Editio iuxta typicam"
    assert edition["authority"] == "approved_ecclesiastical_edition"
    records = [record for record in public_text_evidence(graph)["texts"] if record["id"] in TEXTS]
    assert {record["id"] for record in records} == set(TEXTS)
    for record in records:
        assert record["witnesses"] == [] and "collation" not in record
        groups = record["source_groups"]
        assert len(groups) == 2
        expected = {
            f"use.{record['id']}.mr1962": "direct_approved_print",
            f"use.{record['id']}.do44667ff": "derived_digital_collation_aid",
        }
        entries = {entry["id"]: (group, entry) for group in groups for entry in group["entries"]}
        assert set(entries) == set(expected)
        for identifier, role in expected.items():
            group, entry = entries[identifier]
            authored = row(graph, "uses", identifier)
            assert group["role"] == role
            assert group["locator"] == authored["locator"]
            assert entry["claim"] == authored["claim"]
    serialized = json.dumps(records)
    for field in (
        "evidence_sha256",
        "source_dependencies",
        "raw_binding",
        "raw_resolution",
        "transcription",
        "transcription_sha256",
        "review",
        "decision",
        "decision_reason",
    ):
        assert f'"{field}":' not in serialized
    assert "witnesses/raw/" not in serialized
    assert graph == graph_snapshot
    assert state(sources) == snapshot
