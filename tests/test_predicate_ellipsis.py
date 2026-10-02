"""Accusative predicates are explicit claims, not substantivized adjectives."""

from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.emit import Table, core_artifact, expand
from checks.language_packs import check_core, check_layer
from checks.syntax import check
from checks.translation_provenance import canonical_hash, source_payload


def example():
    return {
        "schema_version": "0.21.0",
        "id": "proprium.example",
        "category": "proprium",
        "localization": {"about": True, "explanations": {"w001": {}}},
        "segments": [
            {
                "id": "s01",
                "type": "verse",
                "words": [
                    {
                        "id": "w001",
                        "form": "moléstos",
                        "lemma": "molestus",
                        "morph": {"pos": "adj", "case": "acc", "number": "pl", "gender": "m"},
                        "ellipsis": "predicate",
                    },
                    {
                        "id": "w002",
                        "form": "esse",
                        "lemma": "sum",
                        "morph": {"pos": "verb", "mood": "inf", "tense": "pres", "voice": "act"},
                    },
                ],
            }
        ],
    }


@pytest.mark.parametrize("reverse", [False, True])
def test_adjacent_accusative_predicate_has_no_invented_head(reverse):
    doc = example()
    if reverse:
        doc["segments"][0]["words"].reverse()
    assert check(doc) == []
    assert check_core(doc) == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("pos", "noun"),
        ("pos", "verb"),
        ("case", "abl"),
        ("case", "dat"),
        ("number", "dual"),
        ("gender", "common"),
    ],
)
def test_accusative_predicate_rejects_incompatible_features(field, value):
    doc = example()
    doc["segments"][0]["words"][0]["morph"][field] = value
    assert check(doc)


@pytest.mark.parametrize("field", ["pos", "case", "number", "gender"])
def test_accusative_predicate_requires_explicit_features(field):
    doc = example()
    del doc["segments"][0]["words"][0]["morph"][field]
    assert check(doc)


@pytest.mark.parametrize(
    "field,value",
    [
        ("pos", "noun"),
        ("mood", "ind"),
        ("mood", "part"),
        ("tense", "perf"),
        ("tense", "fut"),
        ("voice", "pass"),
        ("voice", "dep"),
        ("person", 3),
        ("number", "pl"),
        ("case", "acc"),
        ("gender", "m"),
    ],
)
def test_copula_must_be_present_active_infinitive(field, value):
    doc = example()
    doc["segments"][0]["words"][1]["morph"][field] = value
    assert check(doc)


@pytest.mark.parametrize("field", ["pos", "mood", "tense", "voice"])
def test_copula_requires_every_feature(field):
    doc = example()
    del doc["segments"][0]["words"][1]["morph"][field]
    assert check(doc)


@pytest.mark.parametrize("mode", ["other-lemma", "other-segment", "missing", "intervening"])
def test_nearby_material_cannot_supply_a_missing_copula(mode):
    doc = example()
    words = doc["segments"][0]["words"]
    if mode == "other-lemma":
        words[1]["lemma"] = "edo"
    elif mode == "other-segment":
        doc["segments"].append({"id": "s02", "type": "verse", "words": [words.pop()]})
    elif mode == "missing":
        words.pop()
    else:
        words.insert(1, {"id": "w003", "form": "et", "lemma": "et", "morph": {"pos": "conj"}})
    assert check(doc)


@pytest.mark.parametrize("index,field", [(0, "post"), (1, "pre")])
@pytest.mark.parametrize("mark", [",", ".", ";", ":", "?", "—"])
def test_punctuation_breaks_the_narrow_adjacent_shape(index, field, mark):
    doc = example()
    doc["segments"][0]["words"][index][field] = mark
    assert check(doc)


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("member", ["w001", "w002"])
def test_parentheses_cannot_separate_an_accusative_predicate_from_its_copula(reverse, member):
    doc = example()
    segment = doc["segments"][0]
    if reverse:
        segment["words"].reverse()
    segment["parentheses"] = [{"from": member, "through": member}]
    assert check_core(doc) == []
    assert check(doc)


@pytest.mark.parametrize("reverse", [False, True])
def test_parentheses_can_enclose_the_complete_predicate_and_copula(reverse):
    doc = example()
    segment = doc["segments"][0]
    if reverse:
        segment["words"].reverse()
    first, last = segment["words"]
    last["post"] = "."
    segment["parentheses"] = [{"from": first["id"], "through": last["id"], "closing": "after-post"}]
    assert check_core(doc) == []
    assert check(doc) == []


@pytest.mark.parametrize("pairs", [[], None, [{"from": "w001", "through": "missing"}]])
def test_accusative_predicate_does_not_ignore_malformed_paired_punctuation(pairs):
    doc = example()
    doc["segments"][0]["parentheses"] = pairs
    assert check(doc)


@pytest.mark.parametrize(
    "field,value",
    [
        ("head", "w002"),
        ("head", "w003"),
        ("head", None),
        ("substantive", True),
        ("substantive", False),
    ],
)
def test_accusative_marker_does_not_coexist_with_other_syntax(field, value):
    doc = example()
    doc["segments"][0]["words"][0][field] = value
    assert check(doc)


def test_real_expressed_accusative_controller_keeps_its_head():
    doc = example()
    adjective = doc["segments"][0]["words"][0]
    adjective.pop("ellipsis")
    adjective["head"] = "w003"
    doc["segments"][0]["words"].insert(
        0,
        {
            "id": "w003",
            "form": "se",
            "lemma": "sui",
            "morph": {"pos": "pron", "case": "acc", "number": "pl"},
        },
    )
    assert check(doc) == []
    adjective["ellipsis"] = "predicate"
    assert check(doc)


def test_original_nominative_predicate_contract_is_retained():
    doc = example()
    doc["segments"][0]["words"].pop()
    doc["segments"][0]["words"][0]["morph"] = {"pos": "adj", "case": "nom"}
    assert check(doc) == []


@pytest.mark.parametrize("language", ["pl", "en"])
def test_predicate_requires_actual_localized_explanation(language):
    doc = example()
    layer = {
        "schema_version": "0.21.0",
        "language": language,
        "text": doc["id"],
        "about": "A syntax fixture.",
        "segments": {"s01": {"translation": "A predicate."}},
        "words": {
            "w001": {"gloss": "troublesome", "explanation": "The subject is understood."},
            "w002": {"gloss": "to be"},
        },
    }
    path = Path(language) / "texts/proprium/example.json"
    assert check_layer(doc, layer, path) == []
    del layer["words"]["w001"]["explanation"]
    assert any("explanation topology differs" in e for e in check_layer(doc, layer, path))
    doc["localization"].pop("explanations")
    assert any("requires a contextual explanation" in e for e in check_core(doc))


def test_existing_reader_marker_and_public_hash_preserve_the_claim():
    doc = example()
    doc.update(
        status="draft",
        analysis_defaults={"confidence": "high", "sources": ["editorial"], "review": "pending"},
    )
    parses, analyses, citations = Table(), Table(), Table()
    artifact = core_artifact(doc, doc, parses, analyses, citations)
    assert artifact["seg"][0]["w"][0]["el"] == "predicate"
    layer = {"language": "en", "about": "", "seg": [{"id": "s01", "g": [None, None]}]}
    restored, _ = expand(artifact, layer, parses.order, analyses.order, citations.order, [])
    assert restored["segments"][0]["words"] == doc["segments"][0]["words"]
    missing = deepcopy(doc["segments"][0])
    missing["words"][0].pop("ellipsis")
    assert canonical_hash(source_payload(missing)) != canonical_hash(
        source_payload(doc["segments"][0])
    )
