"""Personal-negative scopes, provider ownership and real dispatcher coverage."""

from copy import deepcopy

import pytest

from checks import english, interlinear, polish
from checks.personal_negatives import check_personal_negatives


def example(kind="finite"):
    words = [
        {"id": "w001", "form": "nemo", "lemma": "nemo", "morph": {"pos": "pron", "case": "nom"}},
        {"id": "w002", "form": "novit", "lemma": "nosco", "morph": {"pos": "verb", "mood": "ind"}},
    ]
    language, glosses = "pl", ["nikt", "zna"]
    if kind in {"object", "other"}:
        middle = {
            "id": "w003",
            "form": "me",
            "lemma": "ego",
            "morph": {"pos": "pron", "case": "acc"},
        }
        if kind == "other":
            middle.update(form="alius", lemma="alius", morph={"pos": "adj", "case": "nom"})
        words.insert(1, middle)
        glosses.insert(1, "mnie" if kind == "object" else "inny")
    elif kind in {"giving-pl", "giving-en"}:
        words[0]["morph"]["case"] = "dat"
        words[1].update(
            form="dantes",
            lemma="do",
            morph={"pos": "verb", "mood": "part", "tense": "pres", "voice": "act"},
        )
        glosses = ["nikomu", "dając"]
        if kind == "giving-en":
            language = "en"
            words.extend(
                [
                    {
                        "id": "w003",
                        "form": "ullam",
                        "lemma": "ullus",
                        "morph": {"pos": "adj", "case": "acc"},
                    },
                    {
                        "id": "w004",
                        "form": "offensionem",
                        "lemma": "offensio",
                        "morph": {"pos": "noun", "case": "acc"},
                    },
                ]
            )
            glosses = ["to no one", "giving no", "any", "offense"]
    elif kind == "ne-quis":
        language = "en"
        words = [
            {"id": "w001", "form": "ne", "lemma": "ne", "morph": {"pos": "conj"}},
            {
                "id": "w002",
                "form": "quis",
                "lemma": "quis",
                "morph": {"pos": "pron", "case": "nom"},
            },
        ]
        glosses = ["that no man", "no man"]
    doc = {"id": "test.personal-negative", "segments": [{"id": "s01", "words": words}]}
    layer = {
        "lang": language,
        "segments": {"s01": {}},
        "words": {w["id"]: {"gloss": g} for w, g in zip(words, glosses, strict=True)},
    }
    return doc, layer


KINDS = ("finite", "object", "other", "giving-pl", "giving-en", "ne-quis")


@pytest.mark.parametrize("kind", KINDS)
def test_real_dispatcher_reaches_the_guard(kind, monkeypatch):
    doc, layer = example(kind)
    assert interlinear.check(doc, layer) == []
    errors = check_personal_negatives(doc, layer)
    assert len(errors) == 1
    dispatcher = polish if layer["lang"] == "pl" else english
    assert set(errors) <= set(dispatcher.check(doc, layer))
    monkeypatch.setattr(dispatcher, "check_personal_negatives", lambda *_: [])
    assert not set(errors) & set(dispatcher.check(doc, layer))


@pytest.mark.parametrize("kind", KINDS)
def test_punctuation_segment_and_provider_boundaries(kind):
    baseline, original = example(kind)
    words = baseline["segments"][0]["words"]
    for cut in range(1, len(words)):
        for index, key in ((cut - 1, "post"), (cut, "pre")):
            doc = deepcopy(baseline)
            doc["segments"][0]["words"][index][key] = ";"
            assert check_personal_negatives(doc, original) == []
        doc = deepcopy(baseline)
        doc["segments"] = [{"id": "s01", "words": words[:cut]}, {"id": "s02", "words": words[cut:]}]
        assert check_personal_negatives(doc, original) == []
    for wid in original["words"]:
        for bad in (None, 42, "", "   "):
            layer = deepcopy(original)
            layer["words"][wid]["gloss"] = bad
            assert check_personal_negatives(baseline, layer) == []
        layer = deepcopy(original)
        layer["words"][wid] = {}
        assert interlinear.check(baseline, layer)
        assert check_personal_negatives(baseline, layer) == []
        layer["segments"]["s01"]["alignments"] = [{"words": [wid], "reason": "word-order"}]
        assert interlinear.check(baseline, layer) == []
        assert check_personal_negatives(baseline, layer) == []
    for language in ("la", None):
        layer = deepcopy(original)
        layer["lang"] = language
        assert check_personal_negatives(baseline, layer) == []


@pytest.mark.parametrize("kind", ("finite", "object", "other", "giving-pl"))
@pytest.mark.parametrize("negative", ("nie", "NIE", "ｎｉｅ"))
def test_polish_direct_and_shared_concord(kind, negative):
    doc, layer = example(kind)
    layer["words"]["w002"]["gloss"] = negative + "\u00a0" + layer["words"]["w002"]["gloss"]
    assert check_personal_negatives(doc, layer) == []
    ids = [w["id"] for w in doc["segments"][0]["words"]]
    layer["words"] = {wid: {} for wid in ids}
    layer["segments"]["s01"]["alignments"] = [
        {"words": ids, "anchor": "w002", "gloss": "nikt " + negative + " zna"}
    ]
    assert interlinear.check(doc, layer) == []
    assert check_personal_negatives(doc, layer) == []
    layer["segments"]["s01"]["alignments"][0]["gloss"] = "nikt zna"
    assert len(check_personal_negatives(doc, layer)) == 1


def test_predicative_nobody_and_intervening_relative_are_different():
    doc, layer = example()
    doc["segments"][0]["words"][1].update(lemma="sum", form="est")
    layer["words"]["w001"]["gloss"] = "nikim"
    layer["words"]["w002"]["gloss"] = "jest"
    assert check_personal_negatives(doc, layer) == []
    layer["words"]["w001"]["gloss"] = "nikt"
    assert len(check_personal_negatives(doc, layer)) == 1
    doc, layer = example("object")
    doc["segments"][0]["words"][1].update(lemma="qui", form="quem")
    layer["words"]["w003"]["gloss"] = "którego"
    assert check_personal_negatives(doc, layer) == []


@pytest.mark.parametrize("value", ("niebo", "niech", "niezapominajka"))
def test_negative_prefix_is_not_the_predicates_negation(value):
    doc, layer = example()
    layer["words"]["w002"]["gloss"] = value
    assert len(check_personal_negatives(doc, layer)) == 1


def test_non_nemo_and_nonfinite_are_outside_this_scope():
    doc, layer = example()
    doc["segments"][0]["words"].insert(0, {"id": "w003", "form": "non", "lemma": "non"})
    assert check_personal_negatives(doc, layer) == []
    for mood in ("inf", "part"):
        doc, layer = example()
        doc["segments"][0]["words"][1]["morph"]["mood"] = mood
        assert check_personal_negatives(doc, layer) == []


@pytest.mark.parametrize("subject", ("no one", "no man", "nobody", "anyone", "anybody"))
@pytest.mark.parametrize("connector", ("that", "lest", "so that"))
def test_one_indefinite_subject_not_two(subject, connector):
    doc, layer = example("ne-quis")
    layer["words"]["w001"]["gloss"] = connector + " " + subject
    layer["words"]["w002"]["gloss"] = subject
    assert len(check_personal_negatives(doc, layer)) == 1
    layer["words"]["w001"]["gloss"] = connector
    assert check_personal_negatives(doc, layer) == []


@pytest.mark.parametrize(
    "first,second",
    (
        ("that no man", "else"),
        ("before no man", "no man"),
        ("that people", "people"),
        ("not", "anyone"),
    ),
)
def test_nonmatching_subject_counterexamples(first, second):
    doc, layer = example("ne-quis")
    layer["words"]["w001"]["gloss"] = first
    layer["words"]["w002"]["gloss"] = second
    assert check_personal_negatives(doc, layer) == []


def test_ne_subject_morphology_and_provider_ownership():
    baseline, original = example("ne-quis")
    for index, key, value in ((0, "pos", "adv"), (1, "pos", "noun"), (1, "case", "dat")):
        doc = deepcopy(baseline)
        doc["segments"][0]["words"][index]["morph"][key] = value
        assert check_personal_negatives(doc, original) == []
    for index in (0, 1):
        doc = deepcopy(baseline)
        doc["segments"][0]["words"][index].pop("lemma")
        assert check_personal_negatives(doc, original) == []
    layer = deepcopy(original)
    group = {"words": ["w001", "w002"], "anchor": "w002", "gloss": "that no one"}
    layer["segments"]["s01"]["alignments"] = [group]
    assert interlinear.check(baseline, layer)
    assert check_personal_negatives(baseline, layer) == []
    layer["words"] = {"w001": {}, "w002": {}}
    assert interlinear.check(baseline, layer) == []
    assert check_personal_negatives(baseline, layer) == []


def test_one_negative_in_the_giving_of_offense():
    doc, layer = example("giving-en")
    layer["words"]["w002"]["gloss"] = "giving"
    assert check_personal_negatives(doc, layer) == []


def test_an_intervening_relative_cannot_supply_the_main_negative():
    import json

    from build_reader.layers import enrich_layer, expand_core
    from checks.layout import CORPUS

    name = "proprium/dominica-ii-post-pentecosten-evangelium.json"
    core = json.loads((CORPUS / "texts" / name).read_text())
    value = json.loads((CORPUS / "languages/pl/texts" / name).read_text())
    doc, layer = expand_core(core), enrich_layer(core, value)
    layer["words"]["w148"]["gloss"] = "zakosztuje"
    assert len(check_personal_negatives(doc, layer)) == 1
    for wid in ("w146", "w147"):
        altered = deepcopy(layer)
        altered["words"][wid]["gloss"] = "nie zaproszeni"
        assert len(check_personal_negatives(doc, altered)) == 1
    for wid in ("w144", "w147"):
        for mark in (";", ":", "."):
            altered = deepcopy(doc)
            next(w for s in altered["segments"] for w in s.get("words", []) if w["id"] == wid)[
                "post"
            ] = mark
            assert check_personal_negatives(altered, layer) == []
    altered = deepcopy(doc)
    next(w for s in altered["segments"] for w in s.get("words", []) if w["id"] == "w146")[
        "head"
    ] = "w143"
    assert check_personal_negatives(altered, layer) == []
