"""English knowledge predicates express each Latin negative once."""

from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import store
from checks import english, interlinear

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.dominica-ii-passionis-evangelium"


def example(left="not", right="knew not"):
    doc = {
        "id": "t.t",
        "segments": [
            {
                "id": "s01",
                "words": [
                    {"id": "w1", "form": "non", "lemma": "non", "morph": {"pos": "adv"}},
                    {
                        "id": "w2",
                        "form": "novi",
                        "lemma": "nosco",
                        "morph": {"pos": "verb", "mood": "ind"},
                    },
                ],
            }
        ],
    }
    layer = {"lang": "en", "words": {"w1": {"gloss": left}, "w2": {"gloss": right}}}
    return doc, layer


def matches(doc, layer):
    return [e for e in english.check(doc, layer) if "knowledge negation twice" in e]


@pytest.mark.parametrize(
    "right",
    [
        "knew not",
        "I do not know",
        "he did not know",
        "didn’t know",
        "didn't know",
        "never knew",
        "cannot know",
        "  HE\tDID NOT KNOW  ",
    ],
)
def test_negative_knowledge_predicate_is_not_realized_twice(right):
    doc, layer = example(" NoT ", right)
    before = deepcopy((doc, layer))
    errors = matches(doc, layer)
    assert len(errors) == 1 and "t.t:w1–w2" in errors[0]
    assert (doc, layer) == before


def test_ordinary_english_dispatch_calls_knowledge_guard(monkeypatch):
    doc, layer = example()
    assert len(matches(doc, layer)) == 1
    monkeypatch.setattr(english, "check_knowledge_negation", lambda *_: [])
    assert matches(doc, layer) == []


@pytest.mark.parametrize(
    "left,right",
    [
        ("not", "know"),
        ("not", "knew"),
        ("not", "notable"),
        ("not", "notification"),
        ("not", "knew that it was not true"),
        ("not", "had not expected it"),
        ("not only", "knew not"),
        ("never", "knew not"),
        (None, "knew not"),
        ("not", None),
    ],
)
def test_other_or_absent_realizations_are_not_judged(left, right):
    assert matches(*example(left, right)) == []


@pytest.mark.parametrize(
    "index,key,value",
    [
        (0, "lemma", "neque"),
        (1, "lemma", "nescio"),
        (1, "lemma", "sum"),
        (1, "pos", "noun"),
        (1, "mood", "inf"),
        (1, "mood", "part"),
        (0, "post", ";"),
        (1, "pre", "("),
    ],
)
def test_lexical_morphological_and_punctuation_boundaries(index, key, value):
    doc, layer = example()
    word = doc["segments"][0]["words"][index]
    (word["morph"] if key in {"pos", "mood"} else word)[key] = value
    assert matches(doc, layer) == []


@pytest.mark.parametrize("boundary", ["segment", "intervening", "reversed"])
def test_only_adjacent_order_within_one_segment_is_judged(boundary):
    doc, layer = example()
    words = doc["segments"][0]["words"]
    if boundary == "segment":
        doc["segments"].append({"id": "s02", "words": [words.pop()]})
    elif boundary == "intervening":
        words.insert(1, {"id": "w3", "form": "enim", "lemma": "enim", "morph": {}})
    else:
        words.reverse()
    assert matches(doc, layer) == []


@pytest.mark.parametrize(
    "alignment",
    [
        {"words": ["w1", "w2"], "anchor": "w1", "gloss": "I do not know"},
        {"words": ["w1"], "reason": "idiom"},
    ],
)
def test_shared_and_zero_providers_are_not_direct_pairs(alignment):
    doc, layer = example()
    layer["segments"] = {"s01": {"alignments": [alignment]}}
    # Even conflicting direct values are the provider guard's responsibility.
    assert matches(doc, layer) == []
    assert interlinear.check(doc, layer)
    for wid in alignment["words"]:
        layer["words"][wid] = {}
    assert interlinear.check(doc, layer) == []
    assert matches(doc, layer) == []


@pytest.mark.parametrize("language", ["pl", "la", None])
def test_language_dispatch(language):
    doc, layer = example()
    layer["lang"] = language
    assert english.check(doc, layer) == []


def test_empty_input_and_later_segment():
    assert english.check_knowledge_negation({}, {}) == []
    doc, layer = example()
    doc["segments"].insert(0, {"id": "intro", "words": []})
    assert len(matches(doc, layer)) == 1


@pytest.mark.parametrize(
    "sid,first,gloss",
    [
        ("s43", 598, "I do not know"),
        ("s45", 629, "he did not know"),
    ],
)
def test_peters_denials_keep_person_context_and_one_negative(sid, first, gloss):
    core, layers = store.load(ROOT, TEXT)
    layer = layers["en"]
    ids = [f"w{n:03}" for n in (first, first + 1)]
    group = next(a for a in layer["segments"][sid].get("alignments", []) if a["words"] == ids)
    assert group == {"words": ids, "anchor": ids[0], "gloss": gloss}
    assert all(not layer["words"][wid].get("gloss") for wid in ids)
    assert layer["words"][ids[1]]["explanation"]
    assert interlinear.check(core, layer) == []
    assert matches(core, layer) == []


@pytest.mark.parametrize(
    "wid,tense,mood,person,polish,english_note,polish_note",
    [
        (
            "w599",
            "perf",
            "ind",
            1,
            "znam",
            "Novi is a perfect form with present meaning here: Peter denies knowing Jesus.",
            (
                "Choć „novi” ma formę czasu przeszłego (perfectum), oznacza tu „znam”. "
                "Piotr zaprzecza, że zna Jezusa."
            ),
        ),
        (
            "w630",
            "plup",
            "subj",
            3,
            "zna",
            (
                "Novisset is a pluperfect subjunctive form. "
                "Here it reports Peter’s claim that he did not know Jesus."
            ),
            (
                "„Novisset” jest formą czasu zaprzeszłego trybu łączącego. "
                "W mowie zależnej oddaje zapewnienie Piotra, że nie zna Jezusa, "
                "a nie przypuszczenie."
            ),
        ),
    ],
)
def test_formal_tenses_keep_contextual_help_in_both_languages(
    wid, tense, mood, person, polish, english_note, polish_note
):
    from checks import language_packs

    core = store.core(ROOT, TEXT)
    layers = {language: store.raw_layer(ROOT, language, TEXT) for language in ("pl", "en")}
    word = next(w for s in core["segments"] for w in s.get("words", []) if w["id"] == wid)
    assert {k: word["morph"][k] for k in ("tense", "mood", "person", "number", "voice")} == {
        "tense": tense,
        "mood": mood,
        "person": person,
        "number": "sg",
        "voice": "act",
    }
    assert wid in core["localization"]["explanations"]
    assert layers["en"]["words"][wid]["explanation"] == english_note
    assert layers["pl"]["words"][wid]["explanation"] == polish_note
    assert layers["pl"]["words"][wid]["gloss"] == polish
    for language in ("pl", "en"):
        path = (
            ROOT / "languages" / language / "texts/proprium/dominica-ii-passionis-evangelium.json"
        )
        assert language_packs.check_layer(core, layers[language], path) == []
