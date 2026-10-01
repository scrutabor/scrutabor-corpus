"""Bounded necessity subjects and a nominalized medial adjective."""

import copy
import json

import pytest

from build_reader.layers import expand_core
from checks import english
from checks.english_arguments import check_contextual_repetitions
from checks.layout import CORPUS


def fixture(text, start, stop, glosses):
    core = json.loads((CORPUS / "texts/proprium" / (text + ".json")).read_bytes())
    words = expand_core(core)["segments"][0]["words"][start - 1 : stop]
    doc = {"id": "fixture", "segments": [{"id": "s01", "words": words}]}
    layer = {
        "lang": "en",
        "words": {w["id"]: {"gloss": g} for w, g in zip(words, glosses, strict=True)},
        "segments": {"s01": {}},
    }
    return doc, layer


def modal(left="you ought", right="you"):
    return fixture("dominica-ii-in-quadragesima-epistola", 15, 17, [left, right, "to walk"])


@pytest.mark.parametrize(
    "left,right", [("ye ought", "you"), ("you ought", "ye"), ("you must", "you")]
)
def test_necessity_subject_is_reported_by_real_dispatch(left, right):
    doc, layer = modal(left, right)
    assert len(check_contextual_repetitions(doc, layer)) == 1
    assert any("necessity gloss repeats" in error for error in english.check(doc, layer))


@pytest.mark.parametrize(
    "left,right",
    [("ought", "you"), ("it is necessary", "for you"), ("you ought", "your"), ("your duty", "you")],
)
def test_nonduplicated_or_unmeasured_modal_split(left, right):
    doc, layer = modal(left, right)
    assert not check_contextual_repetitions(doc, layer)


@pytest.mark.parametrize(
    "kind",
    [
        "language",
        "lemma",
        "finite",
        "person",
        "number",
        "pronoun",
        "case",
        "pronoun-number",
        "infinitive",
        "punctuation",
        "pre-punctuation",
        "segment",
        "shared",
        "zero",
    ],
)
def test_modal_rule_respects_exact_scope(kind):
    doc, layer = modal()
    words = doc["segments"][0]["words"]
    if kind == "language":
        layer["lang"] = "pl"
    elif kind == "lemma":
        words[0]["lemma"] = "audeo"
    elif kind == "finite":
        words[0]["morph"]["mood"] = "inf"
    elif kind == "person":
        words[0]["morph"]["person"] = 2
    elif kind == "number":
        words[0]["morph"]["number"] = "pl"
    elif kind == "pronoun":
        words[1]["lemma"] = "qui"
    elif kind == "case":
        words[1]["morph"]["case"] = "nom"
    elif kind == "pronoun-number":
        words[1]["morph"]["number"] = "sg"
    elif kind == "infinitive":
        words[2]["morph"]["mood"] = "ind"
    elif kind == "punctuation":
        words[1]["post"] = ";"
    elif kind == "pre-punctuation":
        words[2]["pre"] = "("
    elif kind == "segment":
        doc["segments"][0]["words"] = words[:2]
        doc["segments"].append({"id": "s02", "words": words[2:]})
    else:
        group = {"words": ["w015", "w016"], "anchor": "w015", "gloss": "you ought"}
        if kind == "zero":
            group = {"words": ["w017"], "reason": "inflection"}
        layer["segments"]["s01"]["alignments"] = [group]
    assert not check_contextual_repetitions(doc, layer)


def middle():
    return fixture(
        "dominica-xi-post-pentecosten-evangelium",
        15,
        17,
        ["through", "the midst", "of the borders"],
    )


def test_middle_of_is_not_a_second_through():
    doc, layer = middle()
    assert not english.check_doubled_preposition(doc, layer)
    assert not english.check(doc, layer)


@pytest.mark.parametrize(
    "kind",
    [
        "prep",
        "government",
        "modifier",
        "modifier-pos",
        "object-pos",
        "prep-head",
        "modifier-head",
        "case",
        "gender",
        "number",
        "missing-gender",
        "punctuation",
        "pre-punctuation",
        "segment",
        "shared",
        "zero",
        "own-gloss",
        "modifier-gloss",
        "modifier-missing",
        "object-gloss",
    ],
)
def test_middle_exception_does_not_hide_unproven_preposition_overlap(kind):
    doc, layer = middle()
    words = doc["segments"][0]["words"]
    if kind == "prep":
        words[0]["lemma"] = "contra"
    elif kind == "government":
        words[0]["morph"]["governs"] = "abl"
    elif kind == "modifier":
        words[1]["lemma"] = "magnus"
    elif kind == "modifier-pos":
        words[1]["morph"]["pos"] = "noun"
    elif kind == "object-pos":
        words[2]["morph"]["pos"] = "adj"
    elif kind == "prep-head":
        # Keep a real object and leading of, but break the common governed head.
        words[0]["head"] = "w016"
        layer["words"]["w016"]["gloss"] = "of the midst"
    elif kind == "modifier-head":
        words[1]["head"] = "w015"
    elif kind in {"case", "gender", "number"}:
        words[1]["morph"][kind] = {"case": "gen", "gender": "f", "number": "sg"}[kind]
    elif kind == "missing-gender":
        del words[1]["morph"]["gender"]
    elif kind == "punctuation":
        words[0]["post"] = ":"
    elif kind == "pre-punctuation":
        words[2]["pre"] = "("
    elif kind == "segment":
        doc["segments"][0]["words"] = words[:1]
        doc["segments"].append({"id": "s02", "words": words[1:]})
    elif kind in {"shared", "zero"}:
        group = {"words": ["w016"], "reason": "inflection"}
        if kind == "shared":
            group = {
                "words": ["w016", "w017"],
                "anchor": "w016",
                "gloss": "the midst of the borders",
            }
        layer["segments"]["s01"]["alignments"] = [group]
    elif kind == "own-gloss":
        layer["words"]["w015"]["gloss"] = "from"
    elif kind == "modifier-gloss":
        layer["words"]["w016"]["gloss"] = "middle"
    elif kind == "modifier-missing":
        del layer["words"]["w016"]["gloss"]
    elif kind == "object-gloss":
        layer["words"]["w017"]["gloss"] = "in the borders"
    assert len(english.check_doubled_preposition(doc, layer)) == 1


def test_simple_preposition_object_overlap_is_still_reported():
    doc, layer = middle()
    doc["segments"][0]["words"].pop(1)
    del layer["words"]["w016"]
    assert len(english.check_doubled_preposition(doc, layer)) == 1


def test_retained_middle_modifier_does_not_borrow_another_segment():
    doc, layer = middle()
    other = copy.deepcopy(doc["segments"][0])
    other["id"] = "s02"
    other["words"][1]["lemma"] = "magnus"
    other["words"][0]["id"] = "w115"
    other["words"][1]["id"] = "w116"
    other["words"][2]["id"] = "w117"
    other["words"][0]["head"] = other["words"][1]["head"] = "w117"
    doc["segments"].append(other)
    for a, b in zip(("w115", "w116", "w117"), ("w015", "w016", "w017"), strict=True):
        layer["words"][a] = copy.deepcopy(layer["words"][b])
    assert len(english.check_doubled_preposition(doc, layer)) == 1
