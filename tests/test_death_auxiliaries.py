"""Finite death realization must not repeat dead as a separate predicate."""

from copy import deepcopy

import pytest

from checks.english_death import check_death_auxiliaries
from checks.interlinear_quality import check


def subject():
    doc = {
        "id": "t.death",
        "segments": [
            {
                "id": "s01",
                "words": [
                    {"id": "w1", "lemma": "mortuus", "morph": {"pos": "adj", "case": "nom"}},
                    {
                        "id": "w2",
                        "lemma": "sum",
                        "morph": {"pos": "verb", "mood": "ind", "tense": "futperf"},
                    },
                ],
            }
        ],
    }
    layer = {"language": "en", "words": {"w1": {"gloss": "dead"}, "w2": {"gloss": "dies"}}}
    return doc, layer


@pytest.mark.parametrize(
    "tense",
    [
        "die",
        "dies",
        "died",
        "has died",
        "have died",
        "had died",
        "will die",
        "shall die",
        "he dies",
        "they have died",
    ],
)
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("language_key", ["language", "lang"])
def test_direct_finite_death_cannot_be_realized_twice(tense, reverse, language_key):
    doc, layer = subject()
    layer[language_key] = layer.pop("language")
    layer["words"]["w2"]["gloss"] = tense
    if reverse:
        doc["segments"][0]["words"].reverse()
    errors = check(doc, layer)
    assert len(errors) == 1 and "duplicate the death predicate" in errors[0]


@pytest.mark.parametrize(
    "a,b",
    [
        (" DEAD ", "DIES"),
        ("dead.", "dies!"),
        ("“dead”", "he\u00a0dies"),
        ("dead", "has\u202fdied"),
        ("ｄｅａｄ", "ｄｉｅｓ"),
    ],
)
def test_normalization_retains_whole_word_boundaries(a, b):
    doc, layer = subject()
    layer["words"]["w1"]["gloss"] = a
    layer["words"]["w2"]["gloss"] = b
    assert len(check_death_auxiliaries(doc, layer)) == 1


@pytest.mark.parametrize(
    "a,b",
    [
        ("dead", "is"),
        ("dead", "was"),
        ("dead", "are"),
        ("dead", "will be"),
        ("having died", "has"),
        ("deadly", "dies"),
        ("dead", "diesel"),
        ("the dead", "die"),
        ("dead", "not dead"),
    ],
)
def test_states_and_other_complete_glosses_are_not_overcorrected(a, b):
    doc, layer = subject()
    layer["words"]["w1"]["gloss"] = a
    layer["words"]["w2"]["gloss"] = b
    assert check_death_auxiliaries(doc, layer) == []


def test_perfect_deponent_participle_is_in_scope_but_future_is_not():
    doc, layer = subject()
    word = doc["segments"][0]["words"][0]
    word.update(
        lemma="morior", morph={"pos": "verb", "mood": "part", "tense": "perf", "case": "nom"}
    )
    assert len(check_death_auxiliaries(doc, layer)) == 1
    word["morph"]["tense"] = "fut"
    assert check_death_auxiliaries(doc, layer) == []


@pytest.mark.parametrize(
    "change",
    [
        "language",
        "lemma",
        "case",
        "mood",
        "pos",
        "split",
        "gap",
        "post",
        "pre",
        "group",
        "zero",
        "missing",
    ],
)
def test_scope_boundaries_and_other_providers(change):
    doc, layer = subject()
    words = doc["segments"][0]["words"]
    if change == "language":
        layer["language"] = "pl"
    elif change == "lemma":
        words[0]["lemma"] = "vivus"
    elif change == "case":
        words[0]["morph"]["case"] = "acc"
    elif change == "mood":
        words[1]["morph"]["mood"] = "inf"
    elif change == "pos":
        words[1]["morph"]["pos"] = "noun"
    elif change == "split":
        doc["segments"].append({"id": "s02", "words": [words.pop()]})
    elif change == "gap":
        words.insert(1, {"id": "w3", "lemma": "enim"})
    elif change == "post":
        words[0]["post"] = "."
    elif change == "pre":
        words[1]["pre"] = "("
    elif change == "group":
        layer["words"] = {"w1": {}, "w2": {}}
        layer["segments"] = {
            "s01": {"alignments": [{"words": ["w1", "w2"], "anchor": "w1", "gloss": "dies"}]}
        }
    elif change == "zero":
        layer["words"]["w2"] = {}
        layer["words"]["w1"]["gloss"] = "dies"
        layer["segments"] = {"s01": {"alignments": [{"words": ["w2"], "reason": "idiom"}]}}
    else:
        layer["words"]["w2"] = {}
    assert check_death_auxiliaries(doc, layer) == []


def test_only_the_matching_window_is_reported_and_input_is_immutable():
    doc, layer = subject()
    correct = deepcopy(doc["segments"][0]["words"])
    for n, word in enumerate(correct, 3):
        word["id"] = f"w{n}"
    doc["segments"][0]["words"][-1]["post"] = ";"
    doc["segments"][0]["words"] += correct
    layer["words"].update(w3={"gloss": "dead"}, w4={"gloss": "was"})
    before = deepcopy((doc, layer))
    assert len(check_death_auxiliaries(doc, layer)) == 1
    assert (doc, layer) == before
