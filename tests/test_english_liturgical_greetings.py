"""Short greeting captions preserve their source words and human addressees."""

import copy
import json
from pathlib import Path

import pytest
from english_contract_successor_fixture import before_english_contract_text_layer
from possessive_sweep_b1_successor_fixture import possessive_b1_caption, possessive_b1_realization

from build_reader import bibliography, emit, store
from build_reader.layers import enrich_layer, expand_core
from checks.interlinear import alignments_for
from checks.interlinear import check as alignment_errors
from checks.language_packs import check_layer
from checks.translation_provenance import canonical_hash, source_payload

CORPUS = Path(__file__).resolve().parents[1]
FIXTURE = json.loads(
    (CORPUS / "tests/fixtures/english-liturgical-greetings.json").read_text(encoding="utf-8")
)
CLAUSES = FIXTURE["clauses"]
TEXTS = FIXTURE["texts"]
REPRESENTATIVES = CLAUSES[:2]


def read(relative, root=CORPUS):
    return json.loads((root / relative).read_text(encoding="utf-8"))


def subject(text):
    return store.core(CORPUS, text), store.raw_layer(CORPUS, "en", text)


def segment(core, identity):
    return next(row for row in core["segments"] if row["id"] == identity)


def provider_trace(core, layer, identity):
    """One record per actual provider, including every source member once."""
    shared = {word: group for group in alignments_for(layer, identity) for word in group["words"]}
    trace = []
    for word in segment(core, identity)["words"]:
        word_id = word["id"]
        if word_id in shared:
            group = shared[word_id]
            if word_id == group["words"][0]:
                trace.append({key: group[key] for key in ("words", "anchor", "gloss")})
        else:
            trace.append(
                {
                    "words": [word_id],
                    "anchor": word_id,
                    "gloss": layer["words"][word_id]["gloss"],
                }
            )
    return trace


def assert_clause(case, core, layer):
    """A finite edition oracle; native shape validation is a separate condition."""
    assert alignment_errors(core, layer) == [], "greeting provider structure"
    source = segment(core, case["segment"])
    assert canonical_hash(source_payload(source)) == case["source_sha256"], (
        "greeting source signature"
    )
    assert [word["id"] for word in source["words"]] == case["word_ids"], (
        "greeting source word backmap"
    )
    assert layer["segments"][case["segment"]]["translation"] == case["translation"], (
        "greeting full prose"
    )
    assert provider_trace(core, layer, case["segment"]) == case["providers"], (
        "greeting caption providers"
    )


def prose_subject(layer):
    return {
        "about": layer["about"],
        "segments": {
            identity: {key: value for key, value in row.items() if key != "alignments"}
            for identity, row in layer["segments"].items()
        },
    }


def caption_group(layer, case):
    return next(
        group for group in alignments_for(layer, case["segment"]) if len(group["words"]) == 2
    )


@pytest.mark.parametrize("case", CLAUSES, ids=lambda case: case["id"])
def test_actual_clause_has_exact_source_and_caption_provider_backmap(case):
    core, layer = subject(case["text"])
    assert_clause(case, core, layer)
    trace = provider_trace(core, layer, case["segment"])
    assert [word for provider in trace for word in provider["words"]] == case["word_ids"]


@pytest.mark.parametrize("row", TEXTS, ids=lambda row: row["text"])
def test_full_prose_citations_and_pack_topology_remain_unchanged(row):
    core, layer = subject(row["text"])
    assert check_layer(core, layer, store.layer_path(CORPUS, "en", row["text"])) == []
    previous = before_english_contract_text_layer(layer)
    assert canonical_hash(prose_subject(previous)) == row["prose_sha256"]


@pytest.fixture(scope="module")
def complete_reader_citation_projection(emitted_book):
    """Global citation coverage belongs to verification of the actual whole book."""
    assert emit.verify(CORPUS, emitted_book[0]) == []


@pytest.mark.parametrize("row", TEXTS, ids=lambda row: row["text"])
@pytest.mark.usefixtures("complete_reader_citation_projection")
def test_actual_compaction_and_expansion_keep_the_adopted_caption_providers(row):
    core, layer = subject(row["text"])
    graph, languages = bibliography.load(CORPUS)
    projection = bibliography.ReaderCitationProjection(CORPUS, graph, languages)
    parses = emit.Table(read("build_reader/registry/morphology.json"), locked=True)
    analyses = emit.Table(read("build_reader/registry/analysis.json"), locked=True)
    shared_citations = emit.Table(read("build_reader/registry/citations.json"), locked=True)
    english_citations = emit.Table(read("build_reader/registry/citations.json"), locked=True)
    doc = expand_core(core)
    neutral = emit.core_artifact(doc, core, parses, analyses, shared_citations, projection)
    localized = emit.language_artifact(
        doc,
        enrich_layer(core, layer),
        english_citations,
        store.translation_relationships(CORPUS, "en"),
        projection,
    )
    expanded_core, expanded_layer = emit.expand(
        neutral,
        localized,
        parses.order,
        analyses.order,
        shared_citations.order,
        english_citations.order,
    )
    # This projection owns one neutral/English text; the fixture checks the whole book.
    relative = row["text"].replace(".", "/", 1)
    paths = {f"texts/{relative}.json", f"languages/en/texts/{relative}.json"}
    assert projection.seen == {
        reference for reference in projection.known if reference.split("#/", 1)[0] in paths
    }
    assert projection.kept | projection.excluded == projection.seen
    assert projection.excluded == projection.seen & projection.rejected
    assert not projection.kept & projection.rejected
    for case in CLAUSES:
        if case["text"] == row["text"]:
            assert_clause(case, expanded_core, expanded_layer)


@pytest.mark.parametrize(
    "case_id,wrong",
    [
        pytest.param("deus-tu-conversus-s08", "The Lord be with them", id="greeting-third-person"),
        pytest.param("deus-tu-conversus-s09", "our spirit", id="reply-first-person"),
        pytest.param("deus-tu-conversus-s09", "Your spirit", id="reply-divine-capital"),
    ],
)
def test_finite_semantic_oracle_rejects_wrong_addressee_and_recovers(case_id, wrong):
    case = next(row for row in CLAUSES if row["id"] == case_id)
    core, original = subject(case["text"])
    assert_clause(case, core, original)
    changed = copy.deepcopy(original)
    same_input = changed
    try:
        caption_group(changed, case)["gloss"] = wrong
        # A structurally valid caption can still have the wrong person or referent.
        assert alignment_errors(core, changed) == []
        with pytest.raises(AssertionError, match=r"^greeting caption providers(?:\n|$)"):
            assert_clause(case, core, changed)
    finally:
        changed.clear()
        changed.update(copy.deepcopy(original))
    assert changed is same_input and changed == original
    assert_clause(case, core, changed)


@pytest.mark.parametrize("case", REPRESENTATIVES, ids=lambda case: case["id"])
@pytest.mark.parametrize("fault", ["duplicate-direct", "foreign-anchor", "missing-group"])
def test_native_alignment_checker_rejects_broken_real_group_and_recovers(case, fault):
    core, original = subject(case["text"])
    assert_clause(case, core, original)
    changed = copy.deepcopy(original)
    same_input = changed
    try:
        group = caption_group(changed, case)
        if fault == "duplicate-direct":
            changed["words"][group["words"][0]]["gloss"] = group["gloss"]
        elif fault == "foreign-anchor":
            group["anchor"] = "w999"
        else:
            changed["segments"][case["segment"]]["alignments"].remove(group)
            del changed["segments"][case["segment"]]["alignments"]
        assert changed != original
        assert alignment_errors(core, changed)
    finally:
        changed.clear()
        changed.update(copy.deepcopy(original))
    assert changed is same_input and changed == original
    assert alignment_errors(core, changed) == []
    assert_clause(case, core, changed)


@pytest.mark.parametrize("case", REPRESENTATIVES, ids=lambda case: case["id"])
def test_ordinary_reader_verifier_rejects_wrong_person_in_actual_artifact_and_recovers(
    reader_copy, case
):
    assert emit.verify(CORPUS, reader_copy) == []
    path = reader_copy / f"languages/en/texts/{case['text'].replace('.', '/', 1)}.json"
    original = path.read_bytes()
    artifact = json.loads(original)
    row = next(item for item in artifact["seg"] if item["id"] == case["segment"])
    assert len(row["a"]) == 1 and row["a"][0]["n"] == 2
    row["a"][0]["g"] = "The Lord be with them" if case["kind"] == "greeting" else "our spirit"
    try:
        path.write_text(json.dumps(artifact, ensure_ascii=False), encoding="utf-8")
        assert path.read_bytes() != original
        errors = emit.verify(CORPUS, reader_copy)
        assert any(
            f"{case['text']}: en.segments.{case['segment']}.alignments[0].gloss:" in error
            for error in errors
        )
    finally:
        path.write_bytes(original)
    assert path.read_bytes() == original
    assert emit.verify(CORPUS, reader_copy) == []


def test_healthy_paschal_possessive_group_and_members_remain_exact():
    reference = FIXTURE["paschal_reference"]
    core, layer = subject(reference["text"])
    assert alignments_for(layer, reference["segment"]) == [reference["alignment"]]
    assert {word: layer["words"][word] for word in reference["words"]} == reference["words"]
    assert alignment_errors(core, layer) == []


def test_human_reply_rule_does_not_rewrite_divine_address_or_different_greetings():
    control = FIXTURE["divine_address_control"]
    core, layer = subject(control["text"])
    pinned = ("en", control["text"], [control["word"]], control["gloss"])
    words, caption = possessive_b1_caption(*pinned)
    assert control["gloss"] == "Your" and caption.split()[0] == "Your"
    assert possessive_b1_realization(layer, words) == caption
    assert alignment_errors(core, layer) == []
    scope = {(case["text"], case["segment"]) for case in CLAUSES}
    for control in FIXTURE["different_greetings"]:
        core, layer = subject(control["text"])
        assert (control["text"], control["segment"]) not in scope
        source = segment(core, control["segment"])
        assert canonical_hash(source_payload(source)) == control["source_sha256"]
        assert alignment_errors(core, layer) == []


def test_local_explanation_keeps_ellipsis_distinct_from_the_english_formula():
    control = FIXTURE["explanation"]
    core, layer = subject(control["text"])
    assert layer["words"][control["word"]]["explanation"] == control["value"]
    greeting = next(row for row in CLAUSES if row["id"] == "deus-tu-conversus-s08")
    assert all(word["lemma"] != "sum" for word in segment(core, greeting["segment"])["words"])
    assert_clause(greeting, core, layer)
