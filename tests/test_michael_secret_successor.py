"""Finite Michael Secret constructions, composite sources and retained history."""

import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest
from michael_secret_fixture import FIXTURE, predecessor_documents

from build_reader.bibliography_bindings import selected_text
from build_reader.emit import Table, core_artifact, expand, language_artifact
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs, prose
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
TEXT = FIXTURE["text"]
CORE = "texts/" + TEXT.replace(".", "/", 1) + ".json"
LAYERS = {language: f"languages/{language}/{CORE}" for language in ("pl", "en")}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def documents():
    return {path: read(path) for path in (CORE, *LAYERS.values())}


def assert_latin(core):
    require(
        canonical_hash(selected_text(core)) == FIXTURE["selected_latin_ritual_sha256"],
        "Michael selected Latin/ritual",
    )
    words = [word for segment in core["segments"] for word in segment["words"]]
    require(words == FIXTURE["latin_words"], "Michael contextual analyses and stable IDs")
    require(
        [(segment["id"], len(segment["words"])) for segment in core["segments"]]
        == [("s01", 40), ("s02", 4), ("s03", 1)],
        "Michael exact segment boundaries",
    )


def assert_constructions(target, language):
    require(
        target["segments"]["s01"]["alignments"] == FIXTURE["groups"][language],
        "Michael construction groups",
    )
    for word, gloss in FIXTURE["direct"][language].items():
        require(target["words"][word].get("gloss") == gloss, "Michael direct contextual captions")
    require(
        target["segments"]["s01"]["translation"] == FIXTURE["prose"][language]["s01"],
        "Michael complete prose and retained conclusion",
    )
    for segment in ("s02", "s03"):
        require(
            target["segments"][segment] == FIXTURE["continuations"][language][segment],
            "Michael unchanged cadence and response",
        )


def assert_notes(core, target, language):
    require(core["localization"]["explanations"] == {"w013": {}}, "Michael note scope")
    require(
        target["words"]["w013"].get("explanation") == FIXTURE["explanations"][language],
        "Michael shared circumstance note",
    )


def source_records(graph):
    return {
        collection: [
            row
            for row in graph[collection]
            if (row.get("text") or row.get("address", {}).get("text")) == TEXT
        ]
        for collection in ("uses", "witnesses", "collations")
    }


def assert_sources(graph):
    require(source_records(graph) == FIXTURE["source_records"], "Michael exact source chain")


def assert_transcript(text):
    require(
        hashlib.sha256(text.encode()).hexdigest() == FIXTURE["mr_transcription_sha256"],
        "Michael complete MR transcript",
    )
    reading = " ".join(line for line in text.splitlines() if not line.startswith("#"))
    require(reading == FIXTURE["mr_reading"], "Michael unchanged composite reading")


def assert_ledger(core, target, rows, language):
    selected = [row for row in rows if row["text"] == TEXT]
    require(selected == FIXTURE["ledger_after"][language], "Michael provenance exact rows")
    for row in selected:
        (segment,) = [segment for segment in core["segments"] if segment["id"] == row["segment"]]
        require(
            row["source_sha256"] == canonical_hash(source_payload(segment)),
            "Michael ledger source identity",
        )
        require(
            row["target_sha256"]
            == canonical_hash(target["segments"][row["segment"]]["translation"]),
            "Michael ledger target identity",
        )


def test_all45_contextual_analyses_and_selected_ritual_are_unchanged(documents):
    assert_latin(documents[CORE])


@pytest.mark.parametrize("language", ("pl", "en"))
def test_short_constructions_notes_prose_and_all45_memberships(documents, language):
    core, target = documents[CORE], documents[LAYERS[language]]
    assert_constructions(target, language)
    assert_notes(core, target, language)
    counts = Counter(word for word, fields in target["words"].items() if "gloss" in fields)
    counts.update(
        word
        for segment in target["segments"].values()
        for group in segment.get("alignments", [])
        for word in group["words"]
    )
    assert counts == Counter(
        word["id"] for segment in core["segments"] for word in segment["words"]
    )
    assert all(
        group.get("gloss") and "reason" not in group
        for group in target["segments"]["s01"]["alignments"]
    )
    assert interlinear.check(expand_core(core), target) == []
    assert language_packs.check_core(core) == []
    assert language_packs.check_layer(core, target, ROOT / LAYERS[language]) == []
    assert prose.check(target) == []


def test_exact_composite_source_records_and_transcript():
    assert_sources(read("bibliography/graph.json"))
    assert_transcript((ROOT / "witnesses" / TEXT / "mr.txt").read_text(encoding="utf-8"))
    assert len(FIXTURE["source_records"]["uses"]) == 6
    assert all(
        row["review"] == {"status": "pending"}
        for row in FIXTURE["source_records"]["witnesses"] + FIXTURE["source_records"]["collations"]
    )
    apparatus = read(f"witnesses/{TEXT}/apparatus.json")
    assert canonical_hash(apparatus) == FIXTURE["apparatus_sha256"]
    assert len(apparatus["adjudicated"]) == 4


@pytest.mark.parametrize("language", ("pl", "en"))
def test_actual_provenance_only_has_declared_target_hash_successor(documents, language):
    assert_ledger(
        documents[CORE],
        documents[LAYERS[language]],
        read(f"languages/{language}/translation-provenance.json")["sites"],
        language,
    )


def test_keyed_inverse_restores_only_declared_predecessor_fields(documents):
    assert_latin(documents[CORE])
    restored = predecessor_documents(documents)
    for operation in FIXTURE["document_operations"]:
        parent = restored[operation["path"]]
        parts = operation["pointer"].split("/")[1:]
        for part in parts[:-1]:
            parent = parent[part]
        key = parts[-1]
        assert (key in parent) == operation["before"]["exists"]
        if key in parent:
            assert parent[key] == operation["before"]["value"]
    changed = deepcopy(documents)
    changed[CORE]["editorial"]["analysis_defaults"]["confidence"] = "medium"
    assert selected_text(changed[CORE]) == selected_text(documents[CORE])
    assert (
        predecessor_documents(changed)[CORE]["editorial"]["analysis_defaults"]["confidence"]
        == "medium"
    )
    changed[CORE]["segments"][0]["words"][0]["form"] = "Hóstiam"
    assert selected_text(changed[CORE]) != selected_text(documents[CORE])
    with pytest.raises(AssertionError, match=r"^Michael selected Latin/ritual$"):
        assert_latin(changed[CORE])


@pytest.fixture(scope="module")
def projections(documents):
    core, parses, analyses, shared = documents[CORE], Table(), Table(), Table()
    expanded = expand_core(core)
    artifact = core_artifact(expanded, core, parses, analyses, shared)
    result = {}
    for language in ("pl", "en"):
        local = Table()
        localized = language_artifact(
            expanded, enrich_layer(core, documents[LAYERS[language]]), local
        )
        result[language] = expand(
            artifact, localized, parses.order, analyses.order, shared.order, local.order
        )
    return result


@pytest.mark.parametrize("language", ("pl", "en"))
def test_reader_projection_keeps_complete_declared_layer_and_source_subject(
    documents, projections, language
):
    core, layer = projections[language]
    assert selected_text(core) == selected_text(documents[CORE])
    assert layer["segments"] == documents[LAYERS[language]]["segments"]
    assert layer["words"] == documents[LAYERS[language]]["words"]


@pytest.mark.parametrize(
    "language,word,value",
    [
        ("pl", "w001", "ofiary"),
        ("en", "w001", "offerings"),
        ("en", "w024", "through"),
        ("en", "w015", "and"),
    ],
)
def test_direct_caption_mutants_fail_the_owned_assertion_and_restore(
    documents, language, word, value
):
    target = documents[LAYERS[language]]
    assert_constructions(target, language)
    bad = deepcopy(target)
    assert bad["words"][word]["gloss"] != value
    bad["words"][word]["gloss"] = value
    with pytest.raises(AssertionError, match=r"^Michael direct contextual captions$"):
        assert_constructions(bad, language)
    assert_constructions(target, language)


@pytest.mark.parametrize(
    "language,anchor,value",
    [
        ("pl", "w014", "gdy anioł składa ofiarę"),
        ("pl", "w023", "posłużyły sprawił"),
        ("en", "w023", "turn to may grant"),
        ("en", "w025", "Your Lord"),
        ("en", "w029", "our Son"),
    ],
)
def test_group_semantic_mutants_fail_exact_expectation_and_restore(
    documents, language, anchor, value
):
    target = documents[LAYERS[language]]
    assert_constructions(target, language)
    bad = deepcopy(target)
    (group,) = [
        group for group in bad["segments"]["s01"]["alignments"] if group["anchor"] == anchor
    ]
    group["gloss"] = value
    with pytest.raises(AssertionError, match=r"^Michael construction groups$"):
        assert_constructions(bad, language)
    assert_constructions(target, language)


@pytest.mark.parametrize(
    "language,defect",
    [(language, defect) for language in ("pl", "en") for defect in ("missing", "duplicate")],
)
def test_membership_mutants_reach_actual_interlinear_diagnostic(documents, language, defect):
    core, target = documents[CORE], documents[LAYERS[language]]
    assert interlinear.check(expand_core(core), target) == []
    bad = deepcopy(target)
    if defect == "missing":
        bad["segments"]["s01"]["alignments"] = [
            group for group in bad["segments"]["s01"]["alignments"] if "w019" not in group["words"]
        ]
    else:
        bad["words"]["w019"]["gloss"] = "duplicate"
    assert (
        f"{TEXT}:w019:{language}: expected exactly one direct gloss or alignment"
        in interlinear.check(expand_core(core), bad)
    )
    assert interlinear.check(expand_core(core), target) == []


@pytest.mark.parametrize("defect", ("missing-en-note", "scope"))
def test_note_mutants_fail_without_changing_case(documents, defect):
    assert_notes(documents[CORE], documents[LAYERS["en"]], "en")
    core, target = deepcopy(documents[CORE]), deepcopy(documents[LAYERS["en"]])
    if defect == "scope":
        core["localization"]["explanations"]["w013"] = {"languages": ["pl"]}
        diagnostic = "Michael note scope"
    else:
        del target["words"]["w013"]["explanation"]
        diagnostic = "Michael shared circumstance note"
    with pytest.raises(AssertionError) as caught:
        assert_notes(core, target, "en")
    assert str(caught.value) == diagnostic
    assert_notes(documents[CORE], documents[LAYERS["en"]], "en")


@pytest.mark.parametrize(
    "defect",
    (
        "altered-body-use",
        "missing-dependency",
        "foreign-same-text",
        "forged-review",
        "wrong-runninghead-section",
    ),
)
def test_source_chain_mutants_fail_full_object_equality_and_restore(defect):
    graph = read("bibliography/graph.json")
    assert_sources(graph)
    bad = deepcopy(graph)
    if defect == "altered-body-use":
        row = next(row for row in bad["uses"] if row["id"] == f"use.{TEXT}.mr1962")
        row["claim"] = "The proper page prints all45 words."
    elif defect == "wrong-runninghead-section":
        row = next(
            row for row in bad["uses"] if row["id"] == f"use.{TEXT}.conclusion-prefix.mr1962"
        )
        row["locator"]["section"] = (
            "Feria III post dominicam I Passionis, Postcommunio; seventeen-word conclusion prefix"
        )
    elif defect == "foreign-same-text":
        row = deepcopy(
            next(row for row in bad["uses"] if row.get("address", {}).get("text") == TEXT)
        )
        row["id"] += ".foreign"
        bad["uses"].append(row)
    else:
        row = next(row for row in bad["witnesses"] if row["id"] == f"witness.{TEXT}.mr1962")
        if defect == "forged-review":
            row["review"] = {"status": "reviewed", "sha256": "0" * 64}
        else:
            row["source_dependencies"]["uses"].pop()
    with pytest.raises(AssertionError, match=r"^Michael exact source chain$"):
        assert_sources(bad)
    assert_sources(graph)
    unrelated = deepcopy(graph)
    row = deepcopy(next(row for row in graph["uses"] if row.get("address", {}).get("text") == TEXT))
    row["id"] = "use.unrelated.control"
    row["address"]["text"] = "proprium.unrelated-control"
    unrelated["uses"].append(row)
    assert_sources(unrelated)


@pytest.mark.parametrize("field", ("target_sha256", "source_sha256", "review", "origin"))
def test_stale_or_promoted_provenance_is_rejected_and_restored(documents, field):
    rows = read("languages/en/translation-provenance.json")["sites"]
    assert_ledger(documents[CORE], documents[LAYERS["en"]], rows, "en")
    bad = deepcopy(rows)
    row = next(row for row in bad if row["site"] == f"{TEXT}.s01.en")
    row[field] = (
        "0" * 64
        if field.endswith("sha256")
        else ("expert-reviewed" if field == "review" else "own")
    )
    with pytest.raises(AssertionError, match=r"^Michael provenance exact rows$"):
        assert_ledger(documents[CORE], documents[LAYERS["en"]], bad, "en")
    assert_ledger(documents[CORE], documents[LAYERS["en"]], rows, "en")


def test_inverse_rejects_unadjudicated_value_without_mutating_inputs(documents):
    predecessor_documents(documents)
    saved = deepcopy(documents)
    bad = deepcopy(documents)
    bad[LAYERS["en"]]["words"]["w015"]["gloss"] = "also"
    with pytest.raises(AssertionError, match=r"^Michael successor field value$"):
        predecessor_documents(bad)
    predecessor_documents(documents)
    assert documents == saved


def test_inverse_rejects_missing_subject_without_a_vacuous_pass(documents):
    predecessor_documents(documents)
    bad = deepcopy(documents)
    del bad[LAYERS["en"]]
    with pytest.raises(AssertionError, match=r"^Michael successor document set$"):
        predecessor_documents(bad)
