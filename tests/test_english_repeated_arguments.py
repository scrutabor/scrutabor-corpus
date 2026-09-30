"""Adjacent direct realizations must not repeat one source argument."""

from copy import deepcopy

import pytest

from checks.english import check
from checks.interlinear import check as check_interlinear


def example(kind="subject", reverse=False):
    subject = kind == "subject"
    argument = {
        "id": "w1",
        "form": "ego" if subject else "testimonium",
        "lemma": "ego" if subject else "testimonium",
        "morph": {
            "pos": "pron" if subject else "noun",
            "case": "nom" if subject else "acc",
            "number": "sg",
        },
    }
    verb = {
        "id": "w2",
        "form": "vidi" if subject else "perhibui",
        "lemma": "video" if subject else "perhibeo",
        "morph": {"pos": "verb", "person": 1, "number": "sg", "mood": "ind", "tense": "perf"},
    }
    words = [verb, argument] if reverse else [argument, verb]
    return {"id": "test.text", "segments": [{"id": "s01", "words": words}]}, {
        "lang": "en",
        "segments": {"s01": {}},
        "words": {
            "w1": {"gloss": "I" if subject else "witness"},
            "w2": {"gloss": "I saw" if subject else "bore witness"},
        },
    }


@pytest.mark.parametrize("kind", ["subject", "witness"])
@pytest.mark.parametrize("reverse", [False, True])
def test_dispatch_detects_both_orders_without_mutating(kind, reverse):
    doc, layer = example(kind, reverse)
    before = deepcopy((doc, layer))
    errors = check(doc, layer)
    assert len(errors) == 1 and "twice" in errors[0]
    assert (doc, layer) == before


@pytest.mark.parametrize("left,right", [(" Ｉ ", "Ｉ\u00a0saw"), ("i", "I   saw")])
def test_subject_normalization(left, right):
    doc, layer = example()
    layer["words"]["w1"]["gloss"] = left
    layer["words"]["w2"]["gloss"] = right
    assert check(doc, layer)


@pytest.mark.parametrize("kind,correct", [("subject", "saw"), ("witness", "bore")])
def test_coherent_split(kind, correct):
    doc, layer = example(kind)
    layer["words"]["w2"]["gloss"] = correct
    assert check(doc, layer) == []


@pytest.mark.parametrize("language", ["pl", "la", None])
def test_language_dispatch(language):
    doc, layer = example()
    layer["lang"] = language
    assert check(doc, layer) == []


@pytest.mark.parametrize("kind", ["subject", "witness"])
@pytest.mark.parametrize("index,key,value", [(0, "post", ","), (0, "post", ":"), (1, "pre", "(")])
def test_punctuation_bounds(kind, index, key, value):
    doc, layer = example(kind)
    doc["segments"][0]["words"][index][key] = value
    assert check(doc, layer) == []


@pytest.mark.parametrize("kind", ["subject", "witness"])
def test_outer_punctuation_does_not_hide_duplication(kind):
    doc, layer = example(kind)
    words = doc["segments"][0]["words"]
    words[0]["pre"], words[1]["post"] = "(", ".)"
    assert check(doc, layer)


@pytest.mark.parametrize("kind", ["subject", "witness"])
def test_segment_and_adjacency_bounds(kind):
    doc, layer = example(kind)
    first, second = doc["segments"][0]["words"]
    doc["segments"] = [{"id": "s01", "words": [first]}, {"id": "s02", "words": [second]}]
    assert check(doc, layer) == []
    doc, layer = example(kind)
    doc["segments"][0]["words"].insert(1, {"id": "w3", "form": "autem", "morph": {"pos": "adv"}})
    assert check(doc, layer) == []


@pytest.mark.parametrize("kind", ["subject", "witness"])
@pytest.mark.parametrize("wid", ["w1", "w2"])
def test_missing_provider_still_requires_interlinear_validation(kind, wid):
    doc, layer = example(kind)
    layer["words"][wid] = {}
    assert check(doc, layer) == []
    assert check_interlinear(doc, layer)


@pytest.mark.parametrize("kind", ["subject", "witness"])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("anchor", ["w1", "w2"])
def test_shared_provider_is_one_realization(kind, reverse, anchor):
    doc, layer = example(kind, reverse)
    ids = [w["id"] for w in doc["segments"][0]["words"]]
    layer["words"] = {wid: {} for wid in ids}
    layer["segments"]["s01"]["alignments"] = [
        {"words": ids, "anchor": anchor, "gloss": "I saw" if kind == "subject" else "bore witness"}
    ]
    assert check(doc, layer) == []
    assert check_interlinear(doc, layer) == []
    layer["words"]["w1"]["gloss"] = "I" if kind == "subject" else "witness"
    assert check(doc, layer) == []
    assert check_interlinear(doc, layer)


@pytest.mark.parametrize(
    "kind,index,key,value",
    [
        ("subject", 0, "case", "acc"),
        ("subject", 0, "number", "pl"),
        ("subject", 0, "pos", "noun"),
        ("subject", 1, "person", 3),
        ("subject", 1, "number", "pl"),
        ("subject", 1, "mood", "inf"),
        ("subject", 1, "pos", "noun"),
        ("witness", 0, "case", "nom"),
        ("witness", 0, "number", "pl"),
        ("witness", 0, "pos", "pron"),
        ("witness", 1, "mood", "part"),
        ("witness", 1, "pos", "noun"),
    ],
)
def test_required_morphology(kind, index, key, value):
    doc, layer = example(kind)
    doc["segments"][0]["words"][index]["morph"][key] = value
    assert check(doc, layer) == []


@pytest.mark.parametrize("kind,index", [("subject", 0), ("witness", 0), ("witness", 1)])
def test_exact_lemmas(kind, index):
    doc, layer = example(kind)
    doc["segments"][0]["words"][index]["lemma"] = "other"
    assert check(doc, layer) == []


@pytest.mark.parametrize(
    "kind,predicate",
    [("subject", "is"), ("witness", "gave evidence"), ("witness", "bore witness faithfully")],
)
def test_token_boundaries_and_explicit_lexical_limits(kind, predicate):
    doc, layer = example(kind)
    layer["words"]["w2"]["gloss"] = predicate
    assert check(doc, layer) == []


def test_testimony_variant():
    doc, layer = example("witness")
    layer["words"] = {"w1": {"gloss": "testimony"}, "w2": {"gloss": "gave testimony"}}
    assert check(doc, layer)


@pytest.mark.parametrize("ending", [".", ",", ";", ":", "!", "?", "”"])
def test_predicate_punctuation_does_not_hide_witness(ending):
    doc, layer = example("witness")
    layer["words"]["w2"]["gloss"] += ending
    assert check(doc, layer)


@pytest.mark.parametrize("number,person,mood", [("sg", 3, "ind"), ("pl", 2, "subj")])
def test_witness_idiom_is_not_limited_to_first_person(number, person, mood):
    doc, layer = example("witness")
    doc["segments"][0]["words"][1]["morph"].update(number=number, person=person, mood=mood)
    assert check(doc, layer)


def test_subject_subjunctive_is_finite():
    doc, layer = example()
    doc["segments"][0]["words"][1]["morph"]["mood"] = "subj"
    assert check(doc, layer)
