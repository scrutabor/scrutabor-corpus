"""A Polish quantifier cannot alone negate a Latin finite non predicate."""

from copy import deepcopy

import pytest

from checks import interlinear, polish
from checks.polish_negatives import check_quantifier_predicates


def example():
    return (
        {
            "id": "test.non",
            "segments": [
                {
                    "id": "s01",
                    "words": [
                        {
                            "id": "w001",
                            "lemma": "non",
                            "form": "non",
                            "morph": {"pos": "adv"},
                        },
                        {
                            "id": "w002",
                            "lemma": "tango",
                            "form": "tanget",
                            "morph": {"pos": "verb", "mood": "ind", "tense": "fut"},
                        },
                    ],
                }
            ],
        },
        {
            "lang": "pl",
            "words": {"w001": {"gloss": "żadna"}, "w002": {"gloss": "dosięgnie"}},
            "segments": {"s01": {}},
        },
    )


@pytest.mark.parametrize("quantifier", ("żaden", "żadna", "żadne", "żadnych", "ŻADNA"))
def test_lost_negation_reaches_normal_polish_dispatch(quantifier, monkeypatch):
    doc, layer = example()
    layer["words"]["w001"]["gloss"] = quantifier
    assert interlinear.check(doc, layer) == []
    errors = check_quantifier_predicates(doc, layer)
    assert len(errors) == 1
    assert set(errors) <= set(polish.check(doc, layer))
    monkeypatch.setattr(polish, "check_quantifier_predicates", lambda *_: [])
    assert not set(errors) & set(polish.check(doc, layer))


@pytest.mark.parametrize("negation", ("nie", "NIE", "Niech nie", "Czy nie"))
def test_direct_negative_is_not_a_quantifier(negation):
    doc, layer = example()
    layer["words"]["w001"]["gloss"] = negation
    assert check_quantifier_predicates(doc, layer) == []


def test_shared_predicate_must_still_carry_negative_concord():
    doc, layer = example()
    layer["words"] = {"w001": {}, "w002": {}}
    group = {"words": ["w001", "w002"], "anchor": "w002", "gloss": "żadna dosięgnie"}
    layer["segments"]["s01"]["alignments"] = [group]
    assert len(check_quantifier_predicates(doc, layer)) == 1
    group["gloss"] = "żadna nie dosięgnie"
    assert check_quantifier_predicates(doc, layer) == []
    group["gloss"] = "nie dosięgnie"
    assert check_quantifier_predicates(doc, layer) == []


@pytest.mark.parametrize(
    "kind",
    (
        "punctuation",
        "split",
        "intervening",
        "double",
        "infinitive",
        "not-adverb",
        "other-language",
        "zero",
        "wider",
    ),
)
def test_outside_local_finite_scope_is_not_guessed(kind):
    doc, layer = example()
    words = doc["segments"][0]["words"]
    if kind == "punctuation":
        words[0]["post"] = ";"
    elif kind == "split":
        doc["segments"].append({"id": "s02", "words": [words.pop()]})
        layer["segments"]["s02"] = {}
    elif kind == "intervening":
        words.insert(1, {"id": "w003", "form": "ille", "lemma": "ille", "morph": {"pos": "pron"}})
        layer["words"]["w003"] = {"gloss": "on"}
    elif kind == "double":
        words.insert(0, {"id": "w003", "form": "non", "lemma": "non", "morph": {"pos": "adv"}})
        layer["words"]["w003"] = {"gloss": "nie"}
    elif kind == "infinitive":
        words[1]["morph"]["mood"] = "inf"
    elif kind == "not-adverb":
        words[0]["morph"]["pos"] = "noun"
    elif kind == "other-language":
        layer["lang"] = "en"
    elif kind == "zero":
        layer["words"]["w001"] = {}
        layer["segments"]["s01"]["alignments"] = [{"words": ["w001"], "reason": "idiom"}]
    elif kind == "wider":
        words.append({"id": "w003", "form": "ille", "lemma": "ille", "morph": {"pos": "pron"}})
        layer["words"] = {w["id"]: {} for w in words}
        layer["segments"]["s01"]["alignments"] = [
            {
                "words": ["w001", "w002", "w003"],
                "anchor": "w002",
                "gloss": "żadna dosięgnie ich",
            }
        ]
    assert interlinear.check(doc, layer) == []
    assert check_quantifier_predicates(doc, layer) == []


def test_negation_elsewhere_cannot_repair_the_local_predicate():
    doc, layer = example()
    for misleading in ("niebo", "niech", "niegodziwości"):
        changed = deepcopy(layer)
        changed["words"]["w002"]["gloss"] = misleading
        assert len(check_quantifier_predicates(doc, changed)) == 1
    doc["segments"][0]["words"].append(
        {"id": "w003", "form": "ille", "lemma": "ille", "morph": {"pos": "pron"}}
    )
    layer["words"]["w003"] = {"gloss": "nie"}
    assert len(check_quantifier_predicates(doc, layer)) == 1


def test_missing_provider_is_distinct_from_a_declared_zero():
    doc, layer = example()
    layer["words"]["w001"] = {}
    assert interlinear.check(doc, layer)
    assert check_quantifier_predicates(doc, layer) == []
