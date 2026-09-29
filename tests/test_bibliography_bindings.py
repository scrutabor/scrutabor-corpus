"""Current bytes, source associations and approval must not be conflated."""

import copy
import json
import shutil
from pathlib import Path

import pytest

from build_reader import bibliography
from build_reader.bibliography import load, public_text_evidence, validate
from build_reader.bibliography_bindings import (
    collation_subject,
    digest,
    selected_text,
    transcript_digest,
    validate_bindings,
    witness_subject,
)
from checks.apparatus import derived_summary
from checks.raw_binding import REGISTRY

CORPUS = Path(__file__).resolve().parent.parent
TEXT = "proprium.dominica-vi-post-pentecosten-collecta"
SUPPLEMENTS = sorted(
    f"use.{TEXT}.{suffix}.mr1962"
    for suffix in ("continued-body", "expanded-conclusion", "oration-boundaries")
)


@pytest.mark.parametrize("change", ["witness", "selected", "apparatus"])
def test_real_graph_rejects_the_previous_format_only_false_positives(change):
    graph, languages = load(CORPUS)
    witness = next(w for w in graph["witnesses"] if w["id"] == f"witness.{TEXT}.mr1962")
    collation = next(c for c in graph["collations"] if c["text"] == TEXT)
    if change == "witness":
        witness["transcription_sha256"] = "0" * 64
        expected = "transcription_sha256 differs"
    elif change == "selected":
        collation["selected_text_sha256"] = "0" * 64
        expected = "selected_text_sha256 differs"
    else:
        collation["apparatus"] = {"entries": 99999, "classes": ["invented-class"]}
        expected = "apparatus summary differs"
    assert any(expected in error for error in validate(CORPUS, graph, languages))


@pytest.mark.parametrize("field", ["title", "responsible"])
def test_abstract_work_changes_invalidate_the_full_source_review(field):
    graph, languages = load(CORPUS)
    bound_graph = copy.deepcopy(graph)
    bound_graph["witnesses"] = [w for w in graph["witnesses"] if w["text"] == TEXT]
    bound_graph["collations"] = [c for c in graph["collations"] if c["text"] == TEXT]
    doc = json.loads((CORPUS / "texts/proprium" / f"{TEXT.split('.', 1)[1]}.json").read_text())
    reviewed(CORPUS, bound_graph, doc)
    assert validate(CORPUS, graph, languages) == []
    work = next(w for w in graph["works"] if w["id"] == "work.divinum-officium")
    work[field] = "A different work or responsible party"
    assert any("reviewed subject changed" in e for e in validate(CORPUS, graph, languages))


def fixture(root, text_id=TEXT):
    graph = json.loads((CORPUS / "bibliography/graph.json").read_text())
    graph["witnesses"] = [w for w in graph["witnesses"] if w["text"] == text_id]
    graph["collations"] = [c for c in graph["collations"] if c["text"] == text_id]
    use_ids = {w["use"] for w in graph["witnesses"]}
    if text_id == TEXT:
        use_ids.update(SUPPLEMENTS)
    graph["uses"] = [u for u in graph["uses"] if u["id"] in use_ids]
    category, slug = text_id.split(".", 1)
    relative = f"texts/{category}/{slug}.json"
    path = root / relative
    path.parent.mkdir(parents=True)
    shutil.copyfile(CORPUS / relative, path)
    shutil.copytree(CORPUS / "witnesses" / text_id, root / "witnesses" / text_id)
    shutil.copytree(CORPUS / "witnesses/raw", root / "witnesses/raw")
    registry = json.loads((root / REGISTRY).read_text())
    for binding in registry["bindings"].values():
        destination = root / binding["witness"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CORPUS / binding["witness"], destination)
    doc = json.loads(path.read_text())
    aliases = {"mr1962": "mr", "do44667ff": "do", "lu1961": "lu"}
    for witness in graph["witnesses"]:
        suffix = witness["id"].removeprefix(f"witness.{text_id}.")
        witness["transcription"] = aliases.get(suffix, suffix)
        transcript = root / "witnesses" / text_id / f"{witness['transcription']}.txt"
        witness["transcription_sha256"] = transcript_digest(transcript.read_text())
        witness["review"] = {"status": "pending"}
    for collation in graph["collations"]:
        apparatus = json.loads((root / "witnesses" / text_id / "apparatus.json").read_text())
        collation.update(
            selected_text_sha256=digest(selected_text(doc)),
            apparatus_sha256=digest(apparatus),
            apparatus=derived_summary(apparatus),
            review={"status": "pending"},
        )
    return graph, doc, path


@pytest.fixture
def bound(tmp_path):
    graph, doc, path = fixture(tmp_path)
    assert validate_bindings(tmp_path, graph) == []
    return tmp_path, graph, doc, path


def reviewed(root, graph, doc):
    subjects = {}
    for witness in graph["witnesses"]:
        assert witness["text"] == TEXT
        witness["source_dependencies"] = {
            "uses": SUPPLEMENTS.copy() if witness["transcription"] == "mr" else [],
            "raw_binding": "pentecost-vi-collect" if witness["transcription"] == "do" else None,
        }
        subject = witness_subject(root, witness, graph, doc)
        witness["review"] = {"status": "reviewed", "sha256": digest(subject)}
        subjects[witness["id"]] = subject
    for collation in graph["collations"]:
        subject = collation_subject(root, collation, doc, subjects)
        collation["review"] = {"status": "reviewed", "sha256": digest(subject)}
    assert validate_bindings(root, graph) == []


def test_integral_pending_data_does_not_publish_a_source_review(bound):
    _, graph, _, _ = bound
    record = public_text_evidence(graph)["texts"][0]
    assert record["witnesses"] == []
    assert "collation" not in record
    assert record["source_groups"]  # Separately dated bibliographic claims survive.


def test_reviewed_exact_bindings_publish_without_internal_fields(bound):
    root, graph, doc, _ = bound
    reviewed(root, graph, doc)
    record = public_text_evidence(graph)["texts"][0]
    assert len(record["witnesses"]) == 2
    apparatus = json.loads((root / "witnesses" / TEXT / "apparatus.json").read_text())
    assert record["collation"]["apparatus"] == derived_summary(apparatus)
    serialized = json.dumps(record)
    for field in (
        "transcription",
        "transcription_sha256",
        "apparatus_sha256",
        "review",
        "source_dependencies",
        "source_uses",
        "raw_resolution",
        "raw_binding",
    ):
        assert f'"{field}":' not in serialized
    assert "witnesses/raw/" not in serialized


@pytest.mark.parametrize(
    "field", ["transcription_sha256", "selected_text_sha256", "apparatus_sha256"]
)
def test_arbitrary_well_formed_digest_fails(bound, field):
    root, graph, _, _ = bound
    target = graph["witnesses"][0] if field == "transcription_sha256" else graph["collations"][0]
    target[field] = "0" * 64
    assert any(field in error for error in validate_bindings(root, graph))


@pytest.mark.parametrize(
    "change", ["body", "header", "missing", "identity", "duplicate-header", "symlink"]
)
def test_transcript_changes_fail_closed(bound, change):
    root, graph, _, _ = bound
    witness = graph["witnesses"][0]
    path = root / "witnesses" / TEXT / f"{witness['transcription']}.txt"
    text = path.read_text()
    if change == "missing":
        path.unlink()
    elif change == "symlink":
        other = path.with_suffix(".other")
        path.rename(other)
        path.symlink_to(other)
    elif change == "body":
        path.write_text(text + "Alterum verbum.\n")
    elif change == "header":
        path.write_text(text.replace("# source:", "# altered-source:"))
    else:
        altered = (
            text.replace(f"# witness: {witness['transcription']}", "# witness: other")
            if change == "identity"
            else f"# witness: {witness['transcription']}\n" + text
        )
        path.write_text(altered)
        witness["transcription_sha256"] = transcript_digest(altered)
    assert validate_bindings(root, graph)


@pytest.mark.parametrize("name", ["../do", "raw/do", "/tmp/do", "mr.txt", "mr\\do", "", None])
def test_transcription_cannot_escape_its_text_directory(bound, name):
    root, graph, _, _ = bound
    graph["witnesses"][0]["transcription"] = name
    assert validate_bindings(root, graph)


def test_identical_body_is_not_the_same_witness_binding(bound):
    root, graph, _, _ = bound
    first, second = graph["witnesses"]
    first["transcription"] = second["transcription"]
    first["transcription_sha256"] = second["transcription_sha256"]
    assert any("same transcript" in e for e in validate_bindings(root, graph))


@pytest.mark.parametrize(
    "change", ["form", "pre", "post", "rubric", "voice", "parentheses", "order"]
)
def test_selected_subject_includes_text_punctuation_and_structure(bound, change):
    root, graph, doc, path = bound
    segment = doc["segments"][0]
    if change in {"form", "pre", "post"}:
        segment["words"][0][change] = "changed"
    elif change == "rubric":
        doc["segments"].append({"id": "s03", "type": "rubric", "text": "Other ritual text."})
    elif change == "order":
        segment["words"].reverse()
    else:
        segment[change] = "changed"
    path.write_text(json.dumps(doc))
    assert any("selected_text_sha256" in e for e in validate_bindings(root, graph))


@pytest.mark.parametrize("change", ["summary", "reading", "ruling", "missing"])
def test_apparatus_is_not_just_a_count(bound, change):
    root, graph, _, _ = bound
    path = root / "witnesses" / TEXT / "apparatus.json"
    if change == "summary":
        graph["collations"][0]["apparatus"] = {"entries": 99999, "classes": ["invented-class"]}
    elif change == "missing":
        path.unlink()
    else:
        apparatus = json.loads(path.read_text())
        entry = apparatus["adjudicated"][0]
        entry["ruling" if change == "ruling" else "ours"] = "Different reading or decision."
        path.write_text(json.dumps(apparatus))
    assert validate_bindings(root, graph)


def test_a_boolean_is_not_an_apparatus_count(bound):
    root, graph, _, _ = bound
    path = root / "witnesses" / TEXT / "apparatus.json"
    apparatus = json.loads(path.read_text())
    apparatus["adjudicated"] = apparatus["adjudicated"][:1]
    apparatus["summary"] = derived_summary(apparatus)
    path.write_text(json.dumps(apparatus))
    collation = graph["collations"][0]
    collation["apparatus_sha256"] = digest(apparatus)
    collation["apparatus"] = {**derived_summary(apparatus), "entries": True}
    assert any("apparatus summary differs" in e for e in validate_bindings(root, graph))


@pytest.mark.parametrize("entries", [[None], ["bad"], [{"class": []}], None, 1])
def test_malformed_apparatus_returns_an_error_instead_of_crashing(bound, entries):
    root, graph, _, _ = bound
    path = root / "witnesses" / TEXT / "apparatus.json"
    apparatus = json.loads(path.read_text())
    apparatus["adjudicated"] = entries
    path.write_text(json.dumps(apparatus))
    graph["collations"][0]["apparatus_sha256"] = digest(apparatus)
    assert any("apparatus adjudicated" in e for e in validate_bindings(root, graph))


def test_a_collation_cannot_drop_a_pending_apparatus_dependency():
    graph, languages = load(CORPUS)
    text_id = "proprium.cathedra-sancti-petri-introitus"
    collation = next(c for c in graph["collations"] if c["text"] == text_id)
    omitted = next(
        w for w in graph["witnesses"] if w["text"] == text_id and w["transcription"] == "lu"
    )
    assert omitted["review"] == {"status": "pending"}
    collation["witnesses"].remove(omitted["id"])
    assert any(
        "omits apparatus witness dependencies" in e for e in validate(CORPUS, graph, languages)
    )


@pytest.mark.parametrize(
    "change",
    ["claim", "edition", "item", "coverage", "transcript", "selection", "apparatus", "swapped-use"],
)
def test_changed_dependencies_cannot_inherit_review(bound, change):
    root, graph, doc, path = bound
    reviewed(root, graph, doc)
    witness = graph["witnesses"][0]
    use = next(u for u in graph["uses"] if u["id"] == witness["use"])
    if change == "claim":
        use["claim"] += " Another claim."
    elif change == "edition":
        next(e for e in graph["editions"] if e["id"] == use["edition"])["year"] = "1900"
    elif change == "item":
        next(i for i in graph["digital_items"] if i["id"] == use["digital_item"])["record_url"] += (
            "?different"
        )
    elif change == "swapped-use":
        witness["use"] = graph["witnesses"][1]["use"]
    elif change == "coverage":
        witness["coverage"] = {"kind": "words", "words": ["w001"]}
    elif change == "transcript":
        transcript = root / "witnesses" / TEXT / f"{witness['transcription']}.txt"
        text = transcript.read_text() + "\n"
        transcript.write_text(text)
        witness["transcription_sha256"] = transcript_digest(text)
    elif change == "selection":
        doc["segments"][0]["words"][0]["post"] = ","
        path.write_text(json.dumps(doc))
        graph["collations"][0]["selected_text_sha256"] = digest(selected_text(doc))
    else:
        apparatus_path = root / "witnesses" / TEXT / "apparatus.json"
        apparatus = json.loads(apparatus_path.read_text())
        apparatus["note"] += " Changed."
        apparatus_path.write_text(json.dumps(apparatus))
        graph["collations"][0]["apparatus_sha256"] = digest(apparatus)
    assert validate_bindings(root, graph)


def test_a_pending_dependency_prevents_collation_acceptance(bound):
    root, graph, doc, _ = bound
    reviewed(root, graph, doc)
    graph["witnesses"][0]["review"] = {"status": "pending"}
    assert any("requires reviewed witness" in e for e in validate_bindings(root, graph))
    assert "collation" not in public_text_evidence(graph)["texts"][0]


def test_partial_coverage_matches_the_transcript_not_a_numeric_id_sort(tmp_path):
    graph, _, _ = fixture(tmp_path, "proprium.cathedra-sancti-petri-introitus")
    assert validate_bindings(tmp_path, graph) == []
    witness = next(w for w in graph["witnesses"] if w["transcription"] == "lu")
    witness["coverage"] = {"kind": "full"}
    assert any("coverage disagree" in e for e in validate_bindings(tmp_path, graph))


def test_crlf_and_json_layout_do_not_invalidate_identity_or_review(bound):
    root, graph, doc, path = bound
    reviewed(root, graph, doc)
    path.write_text(json.dumps(doc, sort_keys=True, indent=4))
    for witness in graph["witnesses"]:
        transcript = root / "witnesses" / TEXT / f"{witness['transcription']}.txt"
        transcript.write_bytes(transcript.read_bytes().replace(b"\n", b"\r\n"))
    assert validate_bindings(root, graph) == []


@pytest.mark.parametrize("subject", ["apparatus", "text"])
def test_duplicate_json_keys_cannot_hide_changed_reviewed_content(bound, subject):
    root, graph, doc, path = bound
    reviewed(root, graph, doc)
    if subject == "apparatus":
        path = root / "witnesses" / TEXT / "apparatus.json"
        key = "ruling"
    else:
        key = "form"
    original = path.read_text()
    path.write_text(original.replace(f'"{key}":', f'"{key}": "Contradictory value", "{key}":', 1))
    assert any("duplicate JSON key" in e for e in validate_bindings(root, graph))


@pytest.mark.parametrize("package", ["neutral", "pl", "en"])
def test_duplicate_keys_in_bibliography_packages_are_rejected(tmp_path, monkeypatch, package):
    original_path = bibliography.language_graph_path
    source = (
        bibliography.graph_path(CORPUS) if package == "neutral" else original_path(CORPUS, package)
    )
    path = tmp_path / "duplicate.json"
    path.write_text(source.read_text().replace("{", '{"schema_version": "conflicting",', 1))
    if package == "neutral":
        monkeypatch.setattr(bibliography, "graph_path", lambda root: path)
    else:
        monkeypatch.setattr(
            bibliography,
            "language_graph_path",
            lambda root, lang: path if lang == package else original_path(root, lang),
        )
    assert any("duplicate JSON key" in e for e in validate(CORPUS))


@pytest.mark.parametrize("scope", ["words", "segments", "witnesses"])
@pytest.mark.parametrize("member", [{}, [], None, 17])
def test_hostile_member_in_identity_lists_returns_a_validation_error(scope, member):
    graph, languages = load(CORPUS)
    if scope == "witnesses":
        graph["collations"][0]["witnesses"][0] = member
    else:
        graph["witnesses"][0]["coverage"] = {"kind": scope, scope: [member]}
    errors = validate(CORPUS, graph, languages)
    assert errors
    assert any("unique" in error for error in errors)


def test_morphology_is_explicitly_outside_the_latin_source_contract(bound):
    root, graph, doc, path = bound
    reviewed(root, graph, doc)
    before = copy.deepcopy(doc)
    doc["segments"][0]["words"][0]["morph"] = {"pos": "noun"}
    assert selected_text(doc) == selected_text(before)
    path.write_text(json.dumps(doc))
    assert validate_bindings(root, graph) == []  # The annotation checks have their own job.
