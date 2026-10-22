"""Reflexive compounds retain their distinct identities and contextual readings."""

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest
from preface_delivery_fixture import current_source_hash, without_preface_delivery

from build_reader import store
from build_reader.bibliography_bindings import selected_text
from build_reader.emit import lexicon_slice
from build_reader.layers import expand_core
from checks import translation_provenance as provenance
from checks.lexicon import lint_lemmata, lint_senses

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures/reflexive-compounds.json").read_text(encoding="utf-8")
)
CONTEXTS = FIXTURE["contexts"]
VERSES = FIXTURE["source_verses"]


def segment(doc, identifier):
    found = [row for row in doc["segments"] if row["id"] == identifier]
    assert len(found) == 1, "reflexive segment identity"
    return found[0]


def word(doc, context):
    found = [
        row
        for row in segment(doc, context["segment"]).get("words", [])
        if row["id"] == context["word"]
    ]
    assert len(found) == 1, "reflexive word identity"
    return found[0]


def assert_context(token, context):
    assert token["id"] == context["word"], "selected reflexive ID"
    assert token["form"] == context["surface"]["form"], "selected reflexive surface"
    assert token.get("post", "") == context["surface"].get("post", ""), (
        "selected reflexive punctuation"
    )
    assert token["morph"] == context["surface"]["morph"], "selected reflexive morphology"
    assert token["lemma"] == context["lemma"], "selected reflexive lemma"


def assert_inventory(observed):
    expected = [(row["text"], row["segment"], row["word"], row["lemma"]) for row in CONTEXTS]
    assert Counter(observed) == Counter(expected), "exact reflexive context inventory"


@pytest.mark.parametrize("language", ["pl", "en"])
def test_distinct_heads_and_language_dictionary_projection(language):
    expected_heads = FIXTURE["heads"]
    assert expected_heads == {
        "seipse": {"head": "seípse", "pos": "pron"},
        "semetipse": {"head": "semetípse", "pos": "pron"},
    }
    assert lexicon_slice(ROOT, lemmas=set(expected_heads)) == expected_heads
    assert lint_lemmata(expected_heads) == []
    senses = FIXTURE["senses"][language]
    assert lexicon_slice(ROOT, language, set(expected_heads)) == senses
    assert lint_senses(language, senses, expected_heads) == []


def test_exact_eight_short_and_eleven_met_context_inventory():
    fixture_snapshot = deepcopy(FIXTURE)
    observed = []
    for path in sorted((ROOT / "texts").glob("*/*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for part in doc["segments"]:
            for token in part.get("words", []):
                if token.get("lemma") in {"seipse", "semetipse"}:
                    observed.append((doc["id"], part["id"], token["id"], token["lemma"]))
    assert len(observed) == 19
    assert Counter(row[3] for row in observed) == {"seipse": 8, "semetipse": 11}
    assert_inventory(observed)
    damaged = deepcopy(observed)
    short = next(i for i, row in enumerate(damaged) if row[3] == "seipse")
    longer = next(i for i, row in enumerate(damaged) if row[3] == "semetipse")
    damaged[short] = (*damaged[short][:3], "semetipse")
    damaged[longer] = (*damaged[longer][:3], "seipse")
    assert Counter(row[3] for row in damaged) == Counter(row[3] for row in observed)
    with pytest.raises(AssertionError) as substituted:
        assert_inventory(damaged)
    assert str(substituted.value).splitlines()[0] == "exact reflexive context inventory"
    with pytest.raises(AssertionError) as duplicated:
        assert_inventory([*observed, observed[0]])
    assert str(duplicated.value).splitlines()[0] == "exact reflexive context inventory"
    assert_inventory(observed)
    assert fixture_snapshot == FIXTURE


@pytest.mark.parametrize("context", CONTEXTS, ids=lambda row: row["id"])
def test_surface_morphology_and_existing_review_state_survive_rekey(context):
    doc = store.core(ROOT, context["text"])
    before = deepcopy(doc)
    assert_context(word(doc, context), context)
    expanded = expand_core(doc)
    token = word(expanded, context)
    analysis = (
        token.get("analysis")
        or expanded.get("analysis_defaults_words")
        or expanded.get("analysis_defaults")
        or {}
    )
    assert {key: analysis[key] for key in ("confidence", "review")} == context["analysis_state"]
    assert analysis["sources"] == ["editorial", "whitakers"]
    assert doc == before


def test_regnum_and_satan_do_not_exchange_gender_despite_the_shared_surface():
    contexts = {
        row["word"]: row
        for row in CONTEXTS
        if row["text"] == "proprium.dominica-iii-in-quadragesima-evangelium"
    }
    assert set(contexts) == {"w054", "w067"}
    assert contexts["w054"]["surface"]["morph"]["gender"] == "n"
    assert contexts["w067"]["surface"]["morph"]["gender"] == "m"
    doc = store.core(ROOT, contexts["w054"]["text"])
    original = deepcopy(doc)
    for context in contexts.values():
        healthy = word(doc, context)
        assert_context(healthy, context)
        damaged = deepcopy(healthy)
        damaged["morph"]["gender"] = "m" if healthy["morph"]["gender"] == "n" else "n"
        assert damaged["morph"] != healthy["morph"]
        with pytest.raises(AssertionError) as caught:
            assert_context(damaged, context)
        assert str(caught.value).splitlines()[0] == "selected reflexive morphology"
        assert_context(healthy, context)
    assert doc == original


@pytest.mark.parametrize("verse", VERSES, ids=lambda row: row["id"])
def test_lemma_inverse_preserves_selected_latin_and_current_targets(verse):
    fixture_snapshot = deepcopy(FIXTURE)
    doc = store.core(ROOT, verse["text"])
    original = deepcopy(doc)
    current = segment(doc, verse["segment"])
    assert provenance.canonical_hash(provenance.source_payload(current)) == current_source_hash(
        verse["text"], verse["segment"], verse["source_after"]
    )
    legacy = without_preface_delivery(doc)
    old_segment = segment(legacy, verse["segment"])
    affected = [w for w in old_segment["words"] if w["id"] in verse["words"]]
    assert len(affected) == len(verse["words"]) and affected
    for token in affected:
        assert token["lemma"] == "seipse"
        token["lemma"] = "semetipse"
    assert (
        provenance.canonical_hash(provenance.source_payload(old_segment)) == verse["source_before"]
    )
    assert verse["source_before"] != verse["source_after"]
    assert selected_text(without_preface_delivery(doc)) == selected_text(legacy)
    rows, errors = provenance.load(ROOT)
    assert errors == []
    for language in ("pl", "en"):
        site = f"{verse['text']}.{verse['segment']}.{language}"
        recorded = rows[site]
        assert recorded["source_sha256"] == current_source_hash(
            verse["text"], verse["segment"], verse["source_after"]
        )
        target = store.raw_layer(ROOT, language, verse["text"])["segments"][verse["segment"]][
            "translation"
        ]
        assert recorded["target_sha256"] == provenance.canonical_hash(target)
        assert {key: recorded[key] for key in ("origin", "review", "familiar_core")} == verse[
            "states"
        ][language]
    assert doc == original
    assert fixture_snapshot == FIXTURE


def test_actual_provenance_consumer_rejects_all_fourteen_old_source_hashes(monkeypatch):
    fixture_snapshot = deepcopy(FIXTURE)
    recorded, errors = provenance.load(ROOT)
    assert errors == []
    original = deepcopy(recorded)
    healthy_errors, healthy_tally = provenance.check(ROOT)
    assert healthy_errors == []
    damaged = deepcopy(recorded)
    expected = []
    for verse in VERSES:
        for language in ("pl", "en"):
            site = f"{verse['text']}.{verse['segment']}.{language}"
            assert damaged[site]["source_sha256"] == current_source_hash(
                verse["text"], verse["segment"], verse["source_after"]
            )
            assert verse["source_before"] != verse["source_after"]
            damaged[site]["source_sha256"] = verse["source_before"]
            assert {
                key: value for key, value in damaged[site].items() if key != "source_sha256"
            } == {key: value for key, value in original[site].items() if key != "source_sha256"}
            expected.append(f"{site}: stale source_sha256")
    assert len(expected) == len(set(expected)) == 14
    with monkeypatch.context() as control:
        control.setattr(provenance, "load", lambda _root: (deepcopy(damaged), []))
        actual_errors, actual_tally = provenance.check(ROOT)
        assert Counter(actual_errors) == Counter(expected)
        assert actual_tally == healthy_tally
    assert provenance.load(ROOT) == (original, [])
    assert provenance.check(ROOT) == (healthy_errors, healthy_tally)
    assert recorded == original
    assert fixture_snapshot == FIXTURE
