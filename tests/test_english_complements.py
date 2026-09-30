"""Direct English complement checks must respect lexical and clause scope."""

from copy import deepcopy

import pytest

from checks import english


def example():
    words = [
        {
            "id": "w1",
            "form": "quaternionibus",
            "lemma": "quaternio",
            "morph": {"pos": "noun", "case": "dat", "number": "pl"},
        },
        {
            "id": "w2",
            "form": "militum",
            "lemma": "miles",
            "morph": {"pos": "noun", "case": "gen", "number": "pl"},
            "post": ".",
        },
        {
            "id": "w3",
            "form": "discessit",
            "lemma": "discedo",
            "morph": {"pos": "verb", "mood": "ind", "tense": "perf"},
        },
        {
            "id": "w4",
            "form": "Angelus",
            "lemma": "angelus",
            "morph": {"pos": "noun", "case": "nom"},
        },
        {
            "id": "w5",
            "form": "ab",
            "lemma": "ab",
            "morph": {"pos": "prep", "governs": "abl"},
            "head": "w6",
        },
        {
            "id": "w6",
            "form": "eo",
            "lemma": "is",
            "morph": {"pos": "pron", "case": "abl"},
            "post": ".",
        },
    ]
    doc = {"id": "test.complements", "segments": [{"id": "s01", "words": words}]}
    layer = {
        "lang": "en",
        "segments": {"s01": {}},
        "words": {
            wid: {"gloss": value}
            for wid, value in zip(
                [w["id"] for w in words],
                ["detachments of four", "of soldiers", "left", "the angel", "from", "him"],
                strict=True,
            )
        },
    }
    return doc, layer


def matches(doc, layer):
    return [
        e
        for e in english.check(doc, layer)
        if "quaternion glosses" in e or "departure glosses" in e
    ]


def test_two_actual_dispatch_calls(monkeypatch):
    doc, layer = example()
    assert len(matches(doc, layer)) == 2
    monkeypatch.setattr(english, "check_lexical_complements", lambda *_: [])
    assert matches(doc, layer) == []


@pytest.mark.parametrize(
    "left,right",
    [
        ("detachments of four", "of soldiers"),
        ("squads of four", "of soldiers"),
        (" ＤＥＴＡＣＨＭＥＮＴＳ  OF\u00a0FOUR ", "OF SOLDIERS"),
    ],
)
def test_exact_count_phrases_with_unicode_and_spacing(left, right):
    doc, layer = example()
    layer["words"]["w1"]["gloss"] = left
    layer["words"]["w2"]["gloss"] = right
    assert len(matches(doc, layer)) == 2


@pytest.mark.parametrize("person", ["him", "her", "me", "us", "them", "you", " ＨＩＭ\t"])
def test_direct_person_departure(person):
    doc, layer = example()
    layer["words"]["w6"]["gloss"] = person
    assert len(matches(doc, layer)) == 2


@pytest.mark.parametrize(
    "wid,key,value",
    [
        ("w1", "lemma", "custodia"),
        ("w1", "pos", "adj"),
        ("w1", "number", "sg"),
        ("w2", "lemma", "puer"),
        ("w2", "pos", "pron"),
        ("w2", "case", "dat"),
        ("w2", "number", "sg"),
        ("w2", "head", "other"),
        ("w3", "lemma", "relinquo"),
        ("w3", "pos", "noun"),
        ("w4", "case", "abl"),
        ("w4", "pos", "verb"),
        ("w4", "pos", "conj"),
        ("w4", "pos", "adv"),
        ("w4", "head", "other"),
        ("w5", "lemma", "de"),
        ("w5", "pos", "adv"),
        ("w5", "head", "other"),
        ("w6", "pos", "noun"),
        ("w6", "case", "acc"),
    ],
)
def test_other_latin_scopes_are_not_judged(wid, key, value):
    doc, layer = example()
    word = next(w for w in doc["segments"][0]["words"] if w["id"] == wid)
    (word if key in {"lemma", "head"} else word["morph"])[key] = value
    assert len(matches(doc, layer)) == 1


@pytest.mark.parametrize(
    "wid,value",
    [
        ("w1", "detachments"),
        ("w2", "soldiers"),
        ("w2", "of the soldiers"),
        ("w3", "departed"),
        ("w3", "went away"),
        ("w5", "away from"),
        ("w6", "his house"),
        ("w6", "there"),
    ],
)
def test_valid_or_unexamined_english_complements(wid, value):
    doc, layer = example()
    layer["words"][wid]["gloss"] = value
    assert len(matches(doc, layer)) == 1


@pytest.mark.parametrize("wid", ["w1", "w2", "w3", "w4", "w5", "w6"])
def test_missing_direct_provider(wid):
    doc, layer = example()
    del layer["words"][wid]["gloss"]
    assert len(matches(doc, layer)) == 1


@pytest.mark.parametrize("wid", ["w1", "w2", "w3", "w4", "w5", "w6"])
def test_grouped_and_zero_member_is_not_a_direct_junction(wid):
    doc, layer = example()
    layer["segments"]["s01"]["alignments"] = [{"words": [wid], "reason": "inflection"}]
    del layer["words"][wid]["gloss"]
    assert len(matches(doc, layer)) == 1


@pytest.mark.parametrize(
    "wid,key",
    [
        ("w1", "post"),
        ("w2", "pre"),
        ("w3", "post"),
        ("w4", "pre"),
        ("w4", "post"),
        ("w5", "pre"),
        ("w5", "post"),
        ("w6", "pre"),
    ],
)
def test_any_intervening_punctuation_stops_the_junction(wid, key):
    doc, layer = example()
    next(w for w in doc["segments"][0]["words"] if w["id"] == wid)[key] = ";"
    assert len(matches(doc, layer)) == 1


def test_subject_is_optional_and_consistent_heads_are_valid():
    doc, layer = example()
    words = doc["segments"][0]["words"]
    words[1]["head"] = "w1"
    words[3]["head"] = "w3"
    assert len(matches(doc, layer)) == 2
    words.pop(3)
    assert len(matches(doc, layer)) == 2


def test_preposition_needs_its_actual_object_link():
    doc, layer = example()
    doc["segments"][0]["words"][4].pop("head")
    assert len(matches(doc, layer)) == 1


def test_another_predicate_cannot_supply_the_departure_complement():
    doc, layer = example()
    words = doc["segments"][0]["words"]
    words[3:4] = [
        {"id": "other1", "form": "et", "lemma": "et", "morph": {"pos": "conj"}},
        {
            "id": "other2",
            "form": "accepit",
            "lemma": "accipio",
            "morph": {"pos": "verb", "mood": "ind"},
        },
    ]
    layer["words"].update(other1={"gloss": "and"}, other2={"gloss": "received"})
    assert len(matches(doc, layer)) == 1


def test_two_nominals_are_outside_the_declared_window():
    doc, layer = example()
    words = doc["segments"][0]["words"]
    words.insert(4, {**deepcopy(words[3]), "id": "another"})
    layer["words"]["another"] = {"gloss": "Peter"}
    assert len(matches(doc, layer)) == 1


@pytest.mark.parametrize("split", [1, 4, 5])
def test_segment_boundary_is_not_joined(split):
    doc, layer = example()
    words = doc["segments"][0]["words"]
    doc["segments"] = [{"id": "s01", "words": words[:split]}, {"id": "s02", "words": words[split:]}]
    layer["segments"]["s02"] = {}
    assert len(matches(doc, layer)) == 1


def test_other_segment_alignment_does_not_hide_the_error():
    doc, layer = example()
    layer["segments"]["s02"] = {
        "alignments": [{"words": ["w1", "w3"], "anchor": "w1", "gloss": "elsewhere"}]
    }
    assert len(matches(doc, layer)) == 2


def test_other_language_and_empty_input():
    doc, layer = example()
    layer["lang"] = "pl"
    assert english.check(doc, layer) == []
    assert english.check_lexical_complements({"segments": []}, {}) == []
