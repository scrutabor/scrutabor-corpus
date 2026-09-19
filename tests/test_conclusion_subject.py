"""Reject the contextually wrong case even when a dictionary permits its form."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import store
from checks import english, polish
from checks.syntax import check, check_conclusion_subject

ROOT = Path(__file__).resolve().parents[1]


def conclusion(phrase, case="nom"):
    words = [
        dict(id=f"w{i:03}", form=form, lemma=form.lower(), morph={"pos": "noun"})
        for i, form in enumerate(phrase.split(), 1)
    ]
    words[-1]["morph"]["case"] = case
    return dict(id="fixture", segments=[dict(id="s01", words=words)])


@pytest.mark.parametrize("extra", ["", "eiúsdem "])
def test_exact_third_person_formula_requires_nominative(extra):
    phrase = f"Qui tecum vivit et regnat in unitáte {extra}Spíritus Sancti Deus"
    doc = conclusion(phrase)
    assert check_conclusion_subject(doc) == []
    for case in ("voc", "acc", None):
        invalid = deepcopy(doc)
        invalid["segments"][0]["words"][-1]["morph"]["case"] = case
        assert len(check_conclusion_subject(invalid)) == 1


@pytest.mark.parametrize(
    "phrase",
    [
        "Deus",
        "Qui vivis et regnas cum Deo Patre in unitáte Spíritus Sancti Deus",
        "Dómine Deus",
    ],
)
def test_other_address_formulas_are_not_inferred_from_the_surface_deus(phrase):
    assert check_conclusion_subject(conclusion(phrase, "voc")) == []


def test_normal_syntax_check_rejects_mutation_in_actual_complete_prayer():
    doc = json.loads((ROOT / "texts/proprium/sanctissimae-trinitatis-collecta.json").read_text())
    words = [w for s in doc["segments"] for w in s.get("words", [])]
    token = next(w for w in reversed(words) if w["form"] == "Deus")
    assert token["morph"]["case"] == "nom"
    assert check_conclusion_subject(doc) == []
    token["morph"]["case"] = "voc"
    assert any("third-person subject" in error for error in check(doc))


@pytest.mark.parametrize(
    "language,checker,wrong", [("pl", polish.check, "Boże"), ("en", english.check, "O God")]
)
def test_normal_target_check_rejects_explicit_vocative_subject(language, checker, wrong):
    doc, layers = store.load(ROOT, "proprium.sanctissimae-trinitatis-collecta")
    layer = deepcopy(layers[language])
    words = [w for s in doc["segments"] for w in s.get("words", [])]
    subject = next(w for w in reversed(words) if w["form"] == "Deus")
    assert checker(doc, layer) == []
    layer["words"][subject["id"]]["gloss"] = wrong
    assert any("third-person subject" in error for error in checker(doc, layer))


@pytest.mark.parametrize(
    "phrase", ["Dómine Deus", "Qui vivis et regnas cum Deo Patre in unitáte Spíritus Sancti Deus"]
)
def test_target_subject_rule_does_not_reject_real_or_ambiguous_address(phrase):
    from checks.syntax import check_conclusion_gloss

    doc = conclusion(phrase, "voc")
    wid = doc["segments"][0]["words"][-1]["id"]
    for language, target in [("pl", "Boże"), ("en", "O God")]:
        assert (
            check_conclusion_gloss(doc, {"lang": language, "words": {wid: {"gloss": target}}}) == []
        )
