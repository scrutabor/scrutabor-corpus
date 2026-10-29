"""Dated Requiem source uses survive while pending textual reviews stay withheld."""

import copy
import json
from pathlib import Path

import pytest

from build_reader import bibliography, emit
from build_reader.bibliography_bindings import digest, selected_text

CORPUS = Path(__file__).resolve().parents[1]
AGNUS = "ordinarium.agnus-dei-defunctorum"
DISMISSAL = "ordinarium.ite-missa-est-defunctorum"
TEXTS = [AGNUS, DISMISSAL]
EXPECTED_NEUTRAL = {
    AGNUS: {
        f"use.{AGNUS}.{suffix}"
        for suffix in (
            "stem.mr1962",
            "replacement.mr1962",
            "stem.vatican1962",
            "replacement.vatican1962",
            "participation.dms1958",
            "priestly-recitation.mr1962",
            "recitation-voice.mr1962",
            "requiem-exception.mr1962",
        )
    },
    DISMISSAL: {
        f"use.{DISMISSAL}.{suffix}"
        for suffix in (
            "clauses.mr1962",
            "replacement.mr1962",
            "clauses.vatican1962",
            "replacement.vatican1962",
            "all-souls-scope.mr1962",
            "ending-conditions.mr1962",
            "greeting-and-dismissal.mr1962",
            "participation.dms1958",
            "requiem-exception.mr1962",
        )
    },
}


def read(relative, root=CORPUS):
    return json.loads((root / relative).read_text(encoding="utf-8"))


def use_ids(record):
    return {entry["id"] for group in record["source_groups"] for entry in group["entries"]}


def keys(value):
    if isinstance(value, dict):
        return set(value) | {key for child in value.values() for key in keys(child)}
    if isinstance(value, list):
        return {key for child in value for key in keys(child)}
    return set()


def no_internal_fields(record):
    assert not keys(record) & {
        "review",
        "source_dependencies",
        "source_uses",
        "raw_resolution",
        "raw_binding",
        "transcription",
        "transcription_sha256",
        "selected_text_sha256",
        "apparatus_sha256",
        "evidence_sha256",
        "decision",
        "decision_reason",
        "legacy_refs",
    }


@pytest.mark.parametrize("text", TEXTS)
def test_pending_textual_reviews_do_not_hide_dated_source_claims_or_publish_acceptance(
    reader_out, text
):
    graph, _ = bibliography.load(CORPUS)
    witnesses = [record for record in graph["witnesses"] if record["text"] == text]
    collations = [record for record in graph["collations"] if record["text"] == text]
    assert len(witnesses) == 2 and len(collations) == 1
    assert all(record["review"] == {"status": "pending"} for record in [*witnesses, *collations])
    expected = next(
        record
        for record in bibliography.public_text_evidence(graph)["texts"]
        if record["id"] == text
    )
    manifest = read("manifest.json", reader_out)
    entry = next(record for record in manifest["texts"] if record["id"] == text)
    assert entry["evidence"] == f"bibliography/texts/{text.replace('.', '/', 1)}.json"
    actual = read(entry["evidence"], reader_out)
    assert actual == expected
    assert actual["witnesses"] == [] and "collation" not in actual
    assert use_ids(actual) == EXPECTED_NEUTRAL[text]
    assert all(group["verified_on"] for group in actual["source_groups"])
    assert all(
        group["locator"] and all(row["claim"] for row in group["entries"])
        for group in actual["source_groups"]
    )
    no_internal_fields(actual)


@pytest.mark.parametrize("text", TEXTS)
@pytest.mark.parametrize("language", ["pl", "en"])
def test_each_actual_language_slice_contains_its_wording_uses_without_other_language(
    reader_out, text, language
):
    graph, language_graphs = bibliography.load(CORPUS)
    expected = next(
        record
        for record in bibliography.public_text_evidence(graph, language_graphs[language])["texts"]
        if record["id"] == text
    )
    manifest = read(f"languages/{language}/manifest.json", reader_out)
    entry = next(record for record in manifest["texts"] if record["id"] == text)
    actual = read(entry["evidence"], reader_out)
    assert actual == expected and actual["language"] == language
    own = {
        record["id"]
        for record in language_graphs[language]["uses"]
        if record["address"].get("text") == text
        and record["decision"] in {"RETAIN", "RETAIN_WITH_CORRECTION"}
    }
    other = "en" if language == "pl" else "pl"
    foreign = {record["id"] for record in language_graphs[other]["uses"]}
    assert own and use_ids(actual) == own
    assert not use_ids(actual) & (foreign | EXPECTED_NEUTRAL[text])
    assert actual["witnesses"] == [] and "collation" not in actual
    no_internal_fields(actual)


@pytest.mark.parametrize("text", TEXTS)
@pytest.mark.parametrize("fault", ["witness", "collation"])
def test_complete_artifact_verifier_rejects_fabricated_pending_acceptance_and_recovers(
    reader_copy, text, fault
):
    graph, languages = bibliography.load(CORPUS)
    projection = bibliography.ReaderCitationProjection(CORPUS, graph, languages)
    assert emit.verify_edition_artifacts(CORPUS, reader_copy, graph, projection) == []
    path = reader_copy / f"bibliography/texts/{text.replace('.', '/', 1)}.json"
    original = path.read_bytes()
    bad = json.loads(original)
    assert bad["witnesses"] == [] and "collation" not in bad
    if fault == "witness":
        bad["witnesses"].append({"id": f"witness.{text}.mr1962", "role": "controlling"})
    else:
        bad["collation"] = {
            "id": f"collation.{text}.mr1962-vatican1962",
            "apparatus": {"entries": 0, "classes": []},
        }
    try:
        path.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
        assert path.read_bytes() != original
        errors = emit.verify_edition_artifacts(CORPUS, reader_copy, graph, projection)
        assert any(f"emitted evidence.{text}" in error for error in errors)
    finally:
        path.write_bytes(original)
    assert path.read_bytes() == original
    assert emit.verify_edition_artifacts(CORPUS, reader_copy, graph, projection) == []


@pytest.mark.parametrize("text", TEXTS)
def test_complete_artifact_verifier_rejects_a_foreign_wording_use_and_recovers(reader_copy, text):
    graph, languages = bibliography.load(CORPUS)
    projection = bibliography.ReaderCitationProjection(CORPUS, graph, languages)
    assert emit.verify_edition_artifacts(CORPUS, reader_copy, graph, projection) == []
    path = reader_copy / f"languages/en/bibliography/texts/{text.replace('.', '/', 1)}.json"
    original = path.read_bytes()
    bad = json.loads(original)
    foreign = read(f"languages/pl/bibliography/texts/{text.replace('.', '/', 1)}.json", reader_copy)
    bad["source_groups"].append(copy.deepcopy(foreign["source_groups"][0]))
    try:
        path.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
        assert path.read_bytes() != original
        errors = emit.verify_edition_artifacts(CORPUS, reader_copy, graph, projection)
        assert any(
            f"en text evidence: emitted language evidence.{text}" in error for error in errors
        )
    finally:
        path.write_bytes(original)
    assert path.read_bytes() == original
    assert emit.verify_edition_artifacts(CORPUS, reader_copy, graph, projection) == []


def test_selected_agnus_source_subject_binds_each_sung_performance():
    graph, _ = bibliography.load(CORPUS)
    core = read("texts/ordinarium/agnus-dei-defunctorum.json")
    collation = next(record for record in graph["collations"] if record["text"] == AGNUS)
    original = digest(selected_text(core))
    assert collation["selected_text_sha256"] == original
    assert all("participation_performance" in row for row in selected_text(core)["segments"])
    for index in range(3):
        bad = copy.deepcopy(core)
        bad["segments"][index]["participation"]["cantu"]["performance"]["source"] = "Changed source"
        assert digest(selected_text(bad)) != original
    assert digest(selected_text(core)) == original
