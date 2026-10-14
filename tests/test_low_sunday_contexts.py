"""Keep Low Sunday's complete clauses and printed milk metaphor intact."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import store
from checks import interlinear

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "proprium.dominica-in-albis-"
COUNTS = {
    "alleluia": 29,
    "collecta": 38,
    "communio": 16,
    "epistola": 127,
    "evangelium": 243,
    "introitus": 53,
    "offertorium": 14,
    "postcommunio": 43,
    "secreta": 38,
}


def layer(slug, language="pl"):
    return store.raw_layer(ROOT, language, PREFIX + slug)


def group(doc, first, last):
    ids = [f"w{i:03}" for i in range(first, last + 1)]
    matches = [a for a in doc["segments"]["s01"].get("alignments", []) if a["words"] == ids]
    assert len(matches) == 1
    assert all("gloss" not in doc["words"][wid] for wid in ids)
    return matches[0]["gloss"]


@pytest.mark.parametrize("slug,count", COUNTS.items())
@pytest.mark.parametrize("language", ["pl", "en"])
def test_all_proper_words_have_one_language_realization(slug, count, language):
    doc = store.core(ROOT, PREFIX + slug)
    assert sum(len(s.get("words", [])) for s in doc["segments"]) == count
    assert interlinear.check(doc, layer(slug, language)) == []


def test_rationabile_modifies_milk_in_both_antiphons():
    core = store.core(ROOT, PREFIX + "introitus")
    words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    for adjective, milk in [("w006", "w009"), ("w046", "w049")]:
        w = words[adjective]
        assert w["form"] == "rationábile"
        assert w["head"] == milk
        assert w["morph"] == {
            "pos": "adj",
            "case": "acc",
            "gender": "n",
            "number": "sg",
        }
        assert words[milk]["lemma"] == "lac"
    apparatus = json.loads(
        (ROOT / "witnesses" / (PREFIX + "introitus") / "apparatus.json").read_text()
    )
    variants = [e for e in apparatus["adjudicated"] if e["class"] == "substantive"]
    assert [(e["at"], e["ours"], e["witnesses"]) for e in variants] == [
        ("w006", "rationábile,", {"do": "rationábiles,"}),
        ("w046", "rationábile,", {"do": "rationábiles,"}),
    ]


def assert_thomas_condition(doc):
    # This protects this translated clause, not arbitrary Polish conditionals.
    assert doc["words"]["w108"]["gloss"] == "Dopóki nie", "joint condition changed"
    for first, last in [(115, 116), (122, 123)]:
        assert group(doc, first, last) == "i nie włożę"
    assert [doc["words"][w]["gloss"] for w in ["w113", "w117", "w118", "w124", "w125"]] == [
        "śladu",
        "palca",
        "mojego",
        "ręki",
        "mojej",
    ], "negative government changed"
    assert "wszystkie te warunki" in doc["words"]["w108"]["explanation"]
    assert "Nie uwierzę, chyba że" in doc["segments"]["s01"]["translation"]


def test_thomas_condition_and_later_positive_commands_remain_distinct():
    doc = layer("evangelium")
    assert_thomas_condition(doc)
    assert doc["words"]["w160"]["gloss"] == "palec"
    assert doc["words"]["w169"]["gloss"] == "rękę"
    assert doc["words"]["w234"]["gloss"] == "Synem"
    assert layer("epistola")["words"]["w030"]["gloss"] == "Synem"


@pytest.mark.parametrize("word,wrong", [("w108", "Jeśli nie"), ("w117", "palec"), ("w124", "rękę")])
def test_prior_conditional_scope_and_case_regressions_are_rejected(word, wrong):
    doc = layer("evangelium")
    assert_thomas_condition(doc)
    damaged = deepcopy(doc)
    damaged["words"][word]["gloss"] = wrong
    with pytest.raises(AssertionError):
        assert_thomas_condition(damaged)
    assert_thomas_condition(doc)


def test_secret_eternal_quality_belongs_to_joy_not_fruit():
    assert group(layer("secreta"), 13, 16) == "udziel owocu wiecznej radości"


def test_both_testimony_lists_keep_their_own_unity_clause():
    doc = layer("epistola", "en")
    assert group(doc, 76, 77) == "are one"
    assert group(doc, 94, 95) == "are one"


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("word", ["w056", "w112"])
def test_quoniam_selection_does_not_erase_the_recorded_alternative(language, word):
    doc = layer("epistola", language)
    assert doc["words"][word]["gloss"] == ("ponieważ" if language == "pl" else "because")
    note = doc["words"][word]["explanation"]
    assert ("że" if language == "pl" else "that") in note
    assert "«" not in note and "»" not in note


@pytest.mark.parametrize("language", ["pl", "en"])
def test_breathing_explanation_keeps_context_distinct_from_printed_object(language):
    note = layer("evangelium", language)["words"]["w065"]["explanation"]
    assert ("nie zawiera dopełnienia" if language == "pl" else "does not separately say") in note
    assert ";" not in note
