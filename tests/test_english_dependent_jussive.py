"""Dependent ut clauses do not combine that with an independent let command."""

from copy import deepcopy

import pytest

from checks import english, english_predicates, interlinear


def example():
    doc = {
        "id": "test.dependent-jussive",
        "segments": [
            {
                "id": "s01",
                "words": [
                    {
                        "id": "w0",
                        "form": "dicit",
                        "lemma": "dico",
                        "morph": {
                            "pos": "verb",
                            "mood": "ind",
                            "tense": "pres",
                            "voice": "act",
                            "person": 3,
                            "number": "sg",
                        },
                    },
                    {"id": "w1", "form": "ut", "lemma": "ut", "morph": {"pos": "conj"}},
                    {
                        "id": "w2",
                        "form": "requiescant",
                        "lemma": "requiesco",
                        "morph": {
                            "pos": "verb",
                            "mood": "subj",
                            "tense": "pres",
                            "voice": "act",
                            "person": 3,
                            "number": "pl",
                        },
                    },
                    {"id": "w3", "form": "nunc", "lemma": "nunc", "morph": {"pos": "adv"}},
                ],
            }
        ],
    }
    layer = {
        "lang": "en",
        "segments": {"s01": {}},
        "words": {
            "w0": {"gloss": "he says"},
            "w1": {"gloss": "that"},
            "w2": {"gloss": "let them rest"},
            "w3": {"gloss": "now"},
        },
    }
    assert interlinear.check(doc, layer) == []
    return doc, layer


def matches(doc, layer):
    return [error for error in english.check(doc, layer) if "dependent glosses" in error]


@pytest.mark.parametrize("left", ["that", "so that", " ＴＨＡＴ ", "SO\u00a0\tTHAT"])
@pytest.mark.parametrize(
    "right", ["let them rest", "let him rest.", "let her not fear", "LET\u2003IT\tREST"]
)
def test_ordinary_dispatch_rejects_actual_hybrid(left, right):
    doc, layer = example()
    layer["words"]["w1"]["gloss"] = left
    layer["words"]["w2"]["gloss"] = right
    assert len(matches(doc, layer)) == 1


def test_dispatch_and_nested_guard_are_required(monkeypatch):
    doc, layer = example()
    assert matches(doc, layer)
    monkeypatch.setattr(english_predicates, "check_dependent_jussive", lambda *_: [])
    assert matches(doc, layer) == []


@pytest.mark.parametrize(
    "right",
    [
        "they may rest",
        "they rest",
        "they might rest",
        "they let them rest",
        "he lets them rest",
        "may they rest",
        "‘let them rest’",
        "let",
        "letting them rest",
    ],
)
def test_other_realizations_are_outside_this_diagnostic(right):
    doc, layer = example()
    layer["words"]["w2"]["gloss"] = right
    assert matches(doc, layer) == []


@pytest.mark.parametrize("left", ["as", "when", "that they", "saying:", "‘that’"])
def test_other_connectives_are_not_forced_to_that(left):
    doc, layer = example()
    layer["words"]["w1"]["gloss"] = left
    assert matches(doc, layer) == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("pos", "noun"),
        ("mood", "imp"),
        ("tense", "impf"),
        ("voice", "pass"),
        ("person", 2),
        ("number", None),
    ],
)
def test_each_required_verb_feature_bounds_the_guard(field, value):
    doc, layer = example()
    doc["segments"][0]["words"][2]["morph"][field] = value
    assert matches(doc, layer) == []


def test_conjunction_identity_and_part_of_speech():
    original, layer = example()
    for key, value in [("lemma", "quod"), ("morph", {"pos": "adv"})]:
        doc = deepcopy(original)
        doc["segments"][0]["words"][1][key] = value
        assert matches(doc, layer) == []


@pytest.mark.parametrize("index,field", [(1, "post"), (2, "pre")])
def test_source_clause_or_quotation_boundary(index, field):
    doc, layer = example()
    doc["segments"][0]["words"][index][field] = ":"
    assert interlinear.check(doc, layer) == []
    assert matches(doc, layer) == []


def test_no_cross_segment_language_or_intervening_word():
    doc, layer = example()
    words = doc["segments"][0]["words"]
    doc["segments"] = [{"id": "s01", "words": words[:2]}, {"id": "s02", "words": words[2:]}]
    layer["segments"]["s02"] = {}
    assert interlinear.check(doc, layer) == [] and matches(doc, layer) == []
    doc, layer = example()
    layer["lang"] = "pl"
    assert matches(doc, layer) == []
    assert english_predicates.check_dependent_jussive(doc, layer) == []
    doc, layer = example()
    words = doc["segments"][0]["words"]
    words.insert(2, words.pop())
    assert interlinear.check(doc, layer) == [] and matches(doc, layer) == []


@pytest.mark.parametrize("ids", [["w0", "w1"], ["w1", "w2"], ["w2", "w3"], ["w1"], ["w2"]])
def test_valid_shared_and_zero_providers_are_not_direct_pairs(ids):
    doc, layer = example()
    group = (
        {"words": ids, "reason": "word-order"}
        if len(ids) == 1
        else {"words": ids, "anchor": ids[0], "gloss": "coherent shared realization"}
    )
    layer["segments"]["s01"]["alignments"] = [group]
    for wid in ids:
        del layer["words"][wid]["gloss"]
    assert interlinear.check(doc, layer) == []
    assert matches(doc, layer) == []


@pytest.mark.parametrize("wid", ["w1", "w2"])
def test_missing_provider_is_not_a_valid_zero(wid):
    doc, layer = example()
    del layer["words"][wid]["gloss"]
    assert interlinear.check(doc, layer)
    assert matches(doc, layer) == []


def test_foreign_segment_group_does_not_hide_this_pair():
    doc, layer = example()
    doc["segments"].append(
        {
            "id": "s02",
            "words": [
                {
                    "id": "w4",
                    "form": "in",
                    "lemma": "in",
                    "morph": {"pos": "prep", "governs": "abl"},
                },
                {
                    "id": "w5",
                    "form": "pace",
                    "lemma": "pax",
                    "morph": {"pos": "noun", "case": "abl", "number": "sg", "gender": "f"},
                },
            ],
        }
    )
    layer["segments"]["s02"] = {
        "alignments": [{"words": ["w4", "w5"], "anchor": "w4", "gloss": "in peace"}]
    }
    layer["words"].update({"w4": {}, "w5": {}})
    assert interlinear.check(doc, layer) == []
    assert len(matches(doc, layer)) == 1


def test_free_quote_is_not_examined_as_prose():
    doc, layer = example()
    layer["words"]["w2"]["gloss"] = "they may rest"
    layer["segments"]["s01"]["translation"] = "The Spirit says: let them rest."
    assert matches(doc, layer) == []
