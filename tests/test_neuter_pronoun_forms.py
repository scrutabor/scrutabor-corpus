"""The bounded surface/lemma class does not require gender on every pronoun."""

import copy
import json
from pathlib import Path

import pytest

from checks.lint import NEUTER_PRONOUN_FORMS, lint_text


def class_errors(form, lemma, morph):
    doc = {
        "segments": [
            {"id": "s01", "words": [{"id": "w001", "form": form, "lemma": lemma, "morph": morph}]}
        ]
    }
    errors, count = lint_text(doc)
    assert count == 1
    return [error for error in errors if "neuter pronoun form" in error]


FORMS = [
    ("quid", "quis"),
    ("quod", "qui"),
    ("quod", "quis"),
    ("quidquid", "quisquis"),
    ("quicquid", "quisquis"),
    ("quodcumque", "quicumque"),
    ("quodcunque", "quicumque"),
    ("quidquam", "quisquam"),
    ("quicquam", "quisquam"),
    ("aliquid", "aliquis"),
    ("aliquod", "aliquis"),
    ("aliquod", "aliqui"),
    ("quiddam", "quidam"),
    ("quoddam", "quidam"),
    ("quidpiam", "quispiam"),
    ("quodpiam", "quispiam"),
    ("quidvis", "quivis"),
    ("quodvis", "quivis"),
    ("quidlibet", "quilibet"),
    ("quodlibet", "quilibet"),
    ("quidque", "quisque"),
    ("quodque", "quisque"),
    ("quidnam", "quisnam"),
    ("quodnam", "quisnam"),
    ("ecquid", "ecquis"),
    ("ecquod", "ecquis"),
]
HEALTHY = {"pos": "pron", "case": "acc", "number": "sg", "gender": "n"}


def test_named_class_cannot_shrink_with_its_own_parameter_source():
    assert set(FORMS) == {
        (form, lemma) for form, lemmas in NEUTER_PRONOUN_FORMS.items() for lemma in lemmas
    }


@pytest.mark.parametrize(("form", "lemma"), FORMS)
@pytest.mark.parametrize("case", ["nom", "acc"])
def test_neuter_forms_accept_both_syncretic_cases(form, lemma, case):
    assert not class_errors(form, lemma, {**HEALTHY, "case": case})


@pytest.mark.parametrize(("form", "lemma"), FORMS)
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("gender", None),
        ("gender", "m"),
        ("gender", "f"),
        ("number", None),
        ("number", "pl"),
        ("case", None),
        ("case", "gen"),
        ("case", "dat"),
        ("case", "abl"),
        ("case", "voc"),
    ],
)
def test_neuter_forms_reject_missing_or_impossible_features(form, lemma, field, value):
    assert not class_errors(form, lemma, HEALTHY)
    changed = copy.deepcopy(HEALTHY)
    if value is None:
        del changed[field]
    else:
        changed[field] = value
    assert len(class_errors(form, lemma, changed)) == 1
    assert not class_errors(form, lemma, HEALTHY)


@pytest.mark.parametrize("pos", ["pron", "adj"])
def test_quoddam_adjectival_agreement_is_not_ignored(pos):
    assert not class_errors("quoddam", "quidam", {**HEALTHY, "pos": pos})
    assert class_errors("quoddam", "quidam", {**HEALTHY, "pos": pos, "gender": "m"})


@pytest.mark.parametrize(("form", "lemma"), [("Áliquid", "aliquis"), ("Quodcúmque", "quicumque")])
def test_house_accents_and_capitals_do_not_hide_class(form, lemma):
    assert not class_errors(form, lemma, HEALTHY)
    assert class_errors(form, lemma, {**HEALTHY, "gender": "f"})


def test_indefinite_adjective_alias_preserves_its_real_nominative_context():
    root = Path(__file__).resolve().parent.parent
    doc = json.loads((root / "texts/proprium/dominica-iv-post-pascha-epistola.json").read_text())
    word = next(w for s in doc["segments"] for w in s.get("words", []) if w["id"] == "w032")
    assert word["lemma"] == "aliqui"
    assert word["morph"] == {"pos": "pron", "case": "nom", "number": "sg", "gender": "n"}
    assert not class_errors(word["form"], word["lemma"], word["morph"])
    for field, value in [("gender", "f"), ("number", "pl"), ("case", "gen")]:
        assert class_errors(word["form"], word["lemma"], {**word["morph"], field: value})
    assert not class_errors(word["form"], word["lemma"], word["morph"])


@pytest.mark.parametrize(
    ("form", "lemma", "morph"),
    [
        ("quis", "quis", {"pos": "pron", "case": "nom", "number": "sg", "gender": "m"}),
        ("quis", "quis", {"pos": "pron", "case": "nom", "number": "sg", "gender": "f"}),
        ("quisquis", "quisquis", {"pos": "pron", "case": "nom", "number": "sg", "gender": "m"}),
        ("cui", "qui", {"pos": "pron", "case": "dat", "number": "sg"}),
        ("qui", "qui", {"pos": "pron", "case": "nom", "number": "pl", "gender": "m"}),
        ("quæ", "qui", {"pos": "pron", "case": "nom", "number": "pl", "gender": "n"}),
        ("quem", "qui", {"pos": "pron", "case": "acc", "number": "sg", "gender": "m"}),
        ("quod", "quod", {"pos": "conj"}),
        ("aliquid", "aliquis", {"pos": "adv"}),
        ("quid", "quis", {"pos": "adv"}),
    ],
)
def test_personal_oblique_and_conjunction_exceptions(form, lemma, morph):
    assert not class_errors(form, lemma, morph)
