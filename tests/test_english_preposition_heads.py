"""Direct preposition glosses must not absorb their separately realized noun."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from checks.english import SIMPLE_PREPOSITIONS, check, check_doubled_noun_head
from checks.interlinear import check as check_interlinear

ROOT = Path(__file__).resolve().parents[1]


def source():
    return {
        "id": "t.t",
        "segments": [
            {
                "id": "s01",
                "words": [
                    {
                        "id": "w1",
                        "form": "in",
                        "lemma": "in",
                        "head": "w2",
                        "morph": {"pos": "prep"},
                    },
                    {"id": "w2", "form": "aqua", "lemma": "aqua", "morph": {"pos": "noun"}},
                ],
            }
        ],
    }


def layer(left="with water", right="water"):
    return {"lang": "en", "words": {"w1": {"gloss": left}, "w2": {"gloss": right}}}


@pytest.mark.parametrize("prep", sorted(SIMPLE_PREPOSITIONS))
def test_ordinary_dispatch_detects_complete_duplicated_head(prep):
    errors = check(source(), layer(prep + " water"))
    assert len(errors) == 1
    assert "t.t:w1–w2" in errors[0] and "noun twice" in errors[0]


@pytest.mark.parametrize(
    "left,right",
    [
        (" WITH WATER! ", "Water"),
        ("with\u00a0water", "water"),
        ("with-water", "water"),
        ("with grâce", "grâce"),
        ("with gra\u0302ce", "grâce"),
        ("with the water", "the water"),
        ("to Good Hope", "Good Hope"),
    ],
)
def test_full_token_comparison_handles_unicode_and_punctuation(left, right):
    assert len(check(source(), layer(left, right))) == 1


@pytest.mark.parametrize(
    "left,right",
    [
        ("with", "water"),
        ("in", "water"),
        ("among", "Israel"),
        ("in front of", "the ark"),
        ("toward", "ward"),
        ("with goodness", "good"),
        ("with pure water", "water"),
        ("by means of water", "water"),
    ],
)
def test_valid_splits_and_explicit_lexical_limits_are_not_rejected(left, right):
    assert check(source(), layer(left, right)) == []


@pytest.mark.parametrize("language", ["pl", "la", "fr", None])
def test_language_dispatch_is_preserved(language):
    localized = layer()
    localized["lang"] = language
    assert check(source(), localized) == []


@pytest.mark.parametrize("position,pos", [(0, "noun"), (1, "pron"), (1, "adj")])
def test_only_preposition_and_noun_are_checked(position, pos):
    doc = source()
    doc["segments"][0]["words"][position]["morph"]["pos"] = pos
    assert check(doc, layer()) == []


@pytest.mark.parametrize("head", [None, "w99", "w1"])
def test_dependency_must_explicitly_identify_the_noun(head):
    doc = source()
    doc["segments"][0]["words"][0]["head"] = head
    assert check_doubled_noun_head(doc, layer()) == []


def test_nonadjacent_and_cross_segment_heads_are_outside_scope():
    doc = source()
    first, second = doc["segments"][0]["words"]
    doc["segments"] = [{"id": "s01", "words": [first]}, {"id": "s02", "words": [second]}]
    assert check(doc, layer()) == []
    doc = source()
    doc["segments"][0]["words"].insert(
        1, {"id": "w3", "form": "pura", "lemma": "purus", "morph": {"pos": "adj"}}
    )
    assert check(doc, layer()) == []


def test_later_segments_are_checked_without_mutating_inputs():
    doc, localized = source(), layer()
    doc["segments"].insert(0, {"id": "rubric"})
    before = deepcopy((doc, localized))
    assert len(check(doc, localized)) == 1
    assert (doc, localized) == before


def test_shared_provider_is_one_realization_and_conflicts_still_fail():
    doc, localized = source(), layer()
    localized["words"] = {"w1": {}, "w2": {}}
    localized["segments"] = {
        "s01": {"alignments": [{"words": ["w1", "w2"], "anchor": "w1", "gloss": "with water"}]}
    }
    assert check(doc, localized) == []
    assert check_interlinear(doc, localized) == []
    localized["words"]["w2"]["gloss"] = "water"
    assert check_interlinear(doc, localized)


@pytest.mark.parametrize("word", ["w1", "w2"])
def test_missing_provider_is_not_a_valid_way_to_hide_duplication(word):
    doc, localized = source(), layer()
    localized["words"][word].pop("gloss")
    assert check_interlinear(doc, localized)


@pytest.mark.parametrize("missing_noun", [None, "", []])
def test_one_token_preposition_does_not_invent_a_duplicated_empty_noun(missing_noun):
    doc, localized = source(), layer("with", missing_noun)
    assert check_doubled_noun_head(doc, localized) == []
    assert check_interlinear(doc, localized)


@pytest.mark.parametrize(
    "slug,word,head,prep,noun",
    [
        ("commemoratio-baptismatis-domini-evangelium", "w045", "w046", "to", "Israel"),
        ("commemoratio-baptismatis-domini-evangelium", "w050", "w051", "with", "water"),
        ("commemoratio-baptismatis-domini-evangelium", "w079", "w080", "with", "water"),
    ],
)
def test_real_noun_retained_and_individual_regression_rejected(slug, word, head, prep, noun):
    doc = json.loads((ROOT / "texts/proprium" / f"{slug}.json").read_text())
    localized = json.loads((ROOT / "languages/en/texts/proprium" / f"{slug}.json").read_text())
    localized["lang"] = "en"
    assert localized["words"][word]["gloss"] == prep
    assert localized["words"][head]["gloss"] == noun
    assert check(doc, localized) == []
    assert check_interlinear(doc, localized) == []
    localized["words"][word]["gloss"] = f"{prep} {noun}"
    errors = check_doubled_noun_head(doc, localized)
    assert len(errors) == 1 and f"{word}–{head}" in errors[0]
    assert any("noun twice" in error for error in check(doc, localized))


@pytest.mark.parametrize("word,gloss", [("w079", "with good"), ("w080", "good")])
def test_real_group_keeps_good_once_and_rejects_a_second_provider(word, gloss):
    path = "texts/proprium/dominica-iii-post-epiphaniam-epistola.json"
    doc = json.loads((ROOT / path).read_text())
    localized = json.loads((ROOT / "languages/en" / path).read_text())
    ids = ["w078", "w079", "w080", "w081"]
    actual = [g for g in localized["segments"]["s01"]["alignments"] if set(ids) & set(g["words"])]
    assert actual == [{"words": ids, "anchor": "w078", "gloss": "overcome evil with good"}]
    assert all("gloss" not in localized["words"][wid] for wid in ids)
    assert check(doc, localized) == []
    assert check_interlinear(doc, localized) == []
    changed = deepcopy(localized)
    changed["words"][word]["gloss"] = gloss
    assert any(
        f":{word}:en: expected exactly one direct gloss or alignment" in error
        for error in check_interlinear(doc, changed)
    )
    assert check_interlinear(doc, localized) == []
