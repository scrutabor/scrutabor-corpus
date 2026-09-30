"""Repeated local English arguments require matching Latin scope and providers."""

from copy import deepcopy

import pytest

from checks import english, interlinear
from checks.english_arguments import check_contextual_repetitions


def example(kind):
    common = {"case": "abl", "number": "sg", "gender": "m"}
    if kind == "demonstrative":
        words = [
            {"id": "w001", "lemma": "dies", "morph": {"pos": "noun", **common}},
            {"id": "w002", "lemma": "iste", "head": "w001", "morph": {"pos": "pron", **common}},
        ]
        glosses = ["this day", "this"]
    elif kind == "genitive":
        words = [
            {"id": "w001", "lemma": "ager", "morph": {"pos": "noun", "case": "acc"}},
            {
                "id": "w002",
                "lemma": "figulus",
                "head": "w001",
                "morph": {"pos": "noun", "case": "gen"},
            },
        ]
        glosses = ["the potter’s field", "potter’s"]
    elif kind == "connector":
        words = [
            {"id": "w001", "lemma": "scio", "morph": {"pos": "verb", "mood": "ind"}},
            {"id": "w002", "lemma": "enim", "morph": {"pos": "conj"}},
        ]
        glosses = ["For he knew", "for"]
    else:
        words = [
            {
                "id": "w001",
                "lemma": "exeo",
                "head": "w002",
                "morph": {"pos": "verb", "mood": "part", **common},
            },
            {"id": "w002", "lemma": "is", "morph": {"pos": "pron", **common}},
        ]
        glosses = ["as he went out", "he"]
        if kind == "absolute-connector":
            words.insert(1, {"id": "w003", "lemma": "autem", "morph": {"pos": "conj"}})
            glosses.insert(1, "but")
    forms = {
        "demonstrative": ["die", "isto"],
        "genitive": ["agrum", "figuli"],
        "connector": ["sciebat", "enim"],
        "absolute": ["exeunte", "eo"],
        "absolute-connector": ["exeunte", "autem", "eo"],
    }[kind]
    for word, form in zip(words, forms, strict=True):
        word["form"] = form
    doc = {"id": "test.arguments", "segments": [{"id": "s01", "words": words}]}
    layer = {
        "lang": "en",
        "segments": {"s01": {}},
        "words": {w["id"]: {"gloss": g} for w, g in zip(words, glosses, strict=True)},
    }
    return doc, layer


KINDS = ("demonstrative", "genitive", "connector", "absolute", "absolute-connector")


@pytest.mark.parametrize("kind", KINDS)
def test_real_dispatch_and_noop_mutant(kind, monkeypatch):
    doc, layer = example(kind)
    assert interlinear.check(doc, layer) == []
    errors = check_contextual_repetitions(doc, layer)
    assert len(errors) == 1
    assert set(errors) <= set(english.check(doc, layer))
    monkeypatch.setattr(english, "check_contextual_repetitions", lambda *_: [])
    assert not set(errors) & set(english.check(doc, layer))


@pytest.mark.parametrize("kind", KINDS)
def test_boundaries_and_provider_ownership(kind):
    baseline, original = example(kind)
    words = baseline["segments"][0]["words"]
    for cut in range(1, len(words)):
        for index, key in ((cut - 1, "post"), (cut, "pre")):
            doc = deepcopy(baseline)
            doc["segments"][0]["words"][index][key] = ";"
            assert check_contextual_repetitions(doc, original) == []
        doc = deepcopy(baseline)
        doc["segments"] = [{"id": "s01", "words": words[:cut]}, {"id": "s02", "words": words[cut:]}]
        assert check_contextual_repetitions(doc, original) == []
    for wid in original["words"]:
        layer = deepcopy(original)
        layer["words"][wid] = {}
        layer["segments"]["s01"]["alignments"] = [{"words": [wid], "reason": "word-order"}]
        assert interlinear.check(baseline, layer) == []
        assert check_contextual_repetitions(baseline, layer) == []
    for lang in ("pl", "la", None):
        layer = deepcopy(original)
        layer["lang"] = lang
        assert check_contextual_repetitions(baseline, layer) == []


@pytest.mark.parametrize("kind", KINDS)
def test_unicode_and_outer_punctuation(kind):
    doc, layer = example(kind)
    for word in layer["words"].values():
        word["gloss"] = word["gloss"].upper().replace(" ", "\u00a0").replace("’", "'") + "?!"
    assert len(check_contextual_repetitions(doc, layer)) == 1
    doc["segments"][0]["words"][0]["pre"] = "«"
    doc["segments"][0]["words"][-1]["post"] = "?»"
    assert len(check_contextual_repetitions(doc, layer)) == 1
    doc, layer = example("demonstrative")
    layer["words"]["w001"]["gloss"] = "ｔｈｉｓ day"
    assert len(check_contextual_repetitions(doc, layer)) == 1


@pytest.mark.parametrize("kind", ("demonstrative", "genitive", "absolute", "absolute-connector"))
def test_explicit_dependency_is_required(kind):
    baseline, layer = example(kind)
    index = 0 if kind.startswith("absolute") else 1
    for head in (None, "another"):
        doc = deepcopy(baseline)
        doc["segments"][0]["words"][index]["head"] = head
        assert check_contextual_repetitions(doc, layer) == []


def test_present_age_does_not_own_the_following_demonstrative():
    doc, layer = example("demonstrative")
    first, second = doc["segments"][0]["words"]
    first["lemma"] = "saeculum"
    first["morph"].update(case="gen", gender="n")
    second.update(lemma="hic", head="w003")
    second["morph"].update(case="gen", gender="n")
    doc["segments"][0]["words"].append(
        {
            "id": "w003",
            "lemma": "studium",
            "morph": {"pos": "noun", "case": "gen", "number": "sg", "gender": "n"},
        }
    )
    layer["words"].update(
        w001={"gloss": "of this present age"}, w002={"gloss": "this"}, w003={"gloss": "study’s"}
    )
    assert interlinear.check(doc, layer) == []
    assert check_contextual_repetitions(doc, layer) == []


@pytest.mark.parametrize("kind", ("demonstrative", "absolute"))
@pytest.mark.parametrize("feature", ("case", "number", "gender"))
def test_agreement_and_missing_features(kind, feature):
    baseline, layer = example(kind)
    for value in (None, "different"):
        doc = deepcopy(baseline)
        doc["segments"][0]["words"][1]["morph"][feature] = value
        assert check_contextual_repetitions(doc, layer) == []
