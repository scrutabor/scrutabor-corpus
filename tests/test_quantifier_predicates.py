"""Bounded negative quantifiers: real readings and adversarial scope controls."""

import json
from copy import deepcopy

import pytest

from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, polish
from checks.layout import CORPUS
from checks.polish_negatives import check_quantifier_predicates

CASES = (
    ("litaniae/sanctissimi-nominis-iesu", "s145", "w447 w448 w449", "w449", "przestawali"),
    ("litaniae/sanctissimi-nominis-iesu", "s146", "w463 w464 w465 w466", "w466", "pozbawiasz"),
    ("ordinarium/fili-dei-vivi", "s04", "w045 w046 w047", "w047", "dopuść"),
    ("ordinarium/praefatio-sacratissimi-cordis-iesu", "s04", "w049 w050", "w050", "przestało"),
    ("proprium/corporis-christi-sequentia", "s20", "w208 w209 w210 w211", "w210", "dokonuje się"),
    (
        "proprium/dominica-ii-post-pentecosten-collecta",
        "s01",
        "w014 w015 w016 w017",
        "w017",
        "pozbawiasz",
    ),
    (
        "proprium/dominica-iii-post-epiphaniam-epistola",
        "s01",
        "w007 w008 w009 w010 w011",
        "w011",
        "odpłacający",
    ),
    (
        "proprium/dominica-in-sexagesima-collecta",
        "s01",
        "w006 w007 w008 w009",
        "w009",
        "pokładamy ufność",
    ),
)


def example(case):
    text, sid, span = case[:3]
    core = json.loads((CORPUS / "texts" / (text + ".json")).read_text())
    layer = enrich_layer(
        core, json.loads((CORPUS / "languages/pl/texts" / (text + ".json")).read_text())
    )
    doc = expand_core(core)
    segment = next(s for s in doc["segments"] if s["id"] == sid)
    words = [w for w in segment["words"] if w["id"] in span.split()]
    assert [w["id"] for w in words] == span.split()
    # Isolate the exact source span; unrelated alignment topology is not copied.
    doc["segments"] = [{"id": sid, "words": words}]
    layer["segments"] = {sid: {}}
    layer["words"] = {w["id"]: layer["words"][w["id"]] for w in words}
    return doc, layer


@pytest.mark.parametrize("case", CASES)
def test_current_concord_and_original_defect_through_real_dispatch(case, monkeypatch):
    doc, layer = example(case)
    assert interlinear.check(doc, layer) == []
    assert check_quantifier_predicates(doc, layer) == []
    layer["words"][case[3]]["gloss"] = case[4]
    errors = check_quantifier_predicates(doc, layer)
    assert len(errors) == 1
    assert set(errors) <= set(polish.check(doc, layer))
    monkeypatch.setattr(polish, "check_quantifier_predicates", lambda *_: [])
    assert not set(errors) & set(polish.check(doc, layer))


@pytest.mark.parametrize("case", CASES)
def test_only_the_governed_predicate_can_pay_concord(case):
    doc, layer = example(case)
    layer["words"][case[3]]["gloss"] = case[4]
    first = case[2].split()[0]
    for wid in layer["words"]:
        if wid in {first, case[3]}:
            continue
        changed = deepcopy(layer)
        changed["words"][wid]["gloss"] = "nie " + changed["words"][wid]["gloss"]
        assert len(check_quantifier_predicates(doc, changed)) == 1
    for fake in ("niebo", "niech", "niezapominajka"):
        changed = deepcopy(layer)
        changed["words"][case[3]]["gloss"] = fake
        assert len(check_quantifier_predicates(doc, changed)) == 1


@pytest.mark.parametrize("case", CASES)
def test_clause_language_and_provider_boundaries(case):
    doc, layer = example(case)
    layer["words"][case[3]]["gloss"] = case[4]
    words = doc["segments"][0]["words"]
    for cut in range(1, len(words)):
        for index, key in ((cut - 1, "post"), (cut, "pre")):
            changed = deepcopy(doc)
            changed["segments"][0]["words"][index][key] = ";"
            assert check_quantifier_predicates(changed, layer) == []
        changed = deepcopy(doc)
        changed["segments"] = [
            {"id": case[1], "words": words[:cut]},
            {"id": "s999", "words": words[cut:]},
        ]
        assert check_quantifier_predicates(changed, layer) == []
    for wid in (words[0]["id"], case[3]):
        for bad in (None, 42, "", " "):
            changed = deepcopy(layer)
            changed["words"][wid]["gloss"] = bad
            assert check_quantifier_predicates(doc, changed) == []
        changed = deepcopy(layer)
        changed["words"][wid] = {}
        assert interlinear.check(doc, changed)
        changed["segments"][case[1]]["alignments"] = [{"words": [wid], "reason": "word-order"}]
        assert interlinear.check(doc, changed) == []
        assert check_quantifier_predicates(doc, changed) == []
    for language in ("en", "la", None):
        changed = deepcopy(layer)
        changed["lang"] = language
        assert check_quantifier_predicates(doc, changed) == []


@pytest.mark.parametrize("case", CASES)
def test_non_nullus_and_numquam_non_are_not_simple_concord(case):
    doc, layer = example(case)
    layer["words"][case[3]]["gloss"] = case[4]
    for position in (0, 1):
        changed = deepcopy(doc)
        changed["segments"][0]["words"].insert(
            position, {"id": "w999", "form": "non", "lemma": "non", "morph": {"pos": "adv"}}
        )
        assert check_quantifier_predicates(changed, layer) == []


def test_shared_negation_and_wider_realizations_are_not_guessed():
    case = CASES[3]
    doc, layer = example(case)
    ids = case[2].split()
    layer["words"] = {wid: {} for wid in ids}
    layer["segments"][case[1]]["alignments"] = [
        {"words": ids, "anchor": case[3], "gloss": "nigdy nie przestało"}
    ]
    assert interlinear.check(doc, layer) == []
    assert check_quantifier_predicates(doc, layer) == []
    layer["segments"][case[1]]["alignments"][0]["gloss"] = "nigdy przestało"
    assert len(check_quantifier_predicates(doc, layer)) == 1
    case = CASES[2]
    doc, layer = example(case)
    ids = case[2].split()
    layer["words"] = {wid: {} for wid in ids}
    layer["segments"][case[1]]["alignments"] = [
        {"words": ids, "anchor": case[3], "gloss": "nigdy nie dopuść do odłączenia"}
    ]
    assert interlinear.check(doc, layer) == []
    # Wider than the checked adverb/governing-predicate pair: not a semantic pass.
    assert check_quantifier_predicates(doc, layer) == []


def test_nominal_and_elliptical_possessive_copulas_remain_outside_scope():
    for text in ("dominica-vi-post-pentecosten-secreta", "dominica-v-post-pascha-evangelium"):
        core = json.loads((CORPUS / "texts/proprium" / (text + ".json")).read_text())
        layer = json.loads((CORPUS / "languages/pl/texts/proprium" / (text + ".json")).read_text())
        assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
        assert check_quantifier_predicates(expand_core(core), enrich_layer(core, layer)) == []


@pytest.mark.parametrize("case_index", (1, 4, 5, 7))
def test_nominal_agreement_and_dependency_are_required(case_index):
    case = CASES[case_index]
    doc, layer = example(case)
    layer["words"][case[3]]["gloss"] = case[4]
    modifiers = [w for w in doc["segments"][0]["words"] if w.get("head")]
    assert modifiers
    for modifier in modifiers:
        for key, value in (("head", "missing"), ("gender", "missing"), ("number", "missing")):
            changed = deepcopy(doc)
            word = next(w for w in changed["segments"][0]["words"] if w["id"] == modifier["id"])
            if key == "head":
                word[key] = value
            else:
                word["morph"][key] = value
            assert check_quantifier_predicates(changed, layer) == []


def test_joint_participial_negation_is_not_an_arbitrary_prefix():
    case = CASES[6]
    doc, layer = example(case)
    for value in ("nieodpłacający", "NIEODPŁACAJĄCY", "nie odpłacający"):
        layer["words"][case[3]]["gloss"] = value
        assert check_quantifier_predicates(doc, layer) == []
    layer["words"][case[3]]["gloss"] = "niedaleko"
    assert len(check_quantifier_predicates(doc, layer)) == 1
    # The semantic check does not replace the orthographic regression pin.
