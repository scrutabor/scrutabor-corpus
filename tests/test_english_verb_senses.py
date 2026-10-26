"""English dictionary verbs use infinitives without rewriting fixed formulas."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from checks.lexicon import lint_senses

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "colloco": ["to place, set", "to arrange, station", "to invest"],
    "edo_proferre": ["to bring forth, produce", "to send out, utter", "to publish, announce"],
    "fragro": ["to give off a scent", "to be fragrant"],
    "occumbo": ["to fall dead", "to die"],
}
FORMULAS = {
    "absum": "far be it",
    "aveo": "hail, greetings",
    "eleison": "have mercy",
    "nolo": "do not",
    "salveo": "hail, greetings",
}


def dictionaries():
    return tuple(
        json.loads((ROOT / path).read_text(encoding="utf-8"))["entries"]
        for path in ("lexicon/lemmata.json", "languages/en/lexicon.json")
    )


def sense_errors(lemma, senses, *, pos="verb", language="en"):
    return lint_senses(language, {lemma: {"senses": senses}}, {lemma: {"pos": pos}})


def test_all_actual_english_verb_senses_and_formula_exceptions():
    heads, entries = dictionaries()
    verbs = {key: entries[key] for key, value in heads.items() if value.get("pos") == "verb"}
    assert verbs
    assert lint_senses("en", verbs, heads, required=verbs) == []
    actual_exceptions = {
        (key, sense)
        for key, value in verbs.items()
        for sense in value["senses"]
        if not sense.startswith(("to ", "not to "))
    }
    assert actual_exceptions == set(FORMULAS.items())


@pytest.mark.parametrize("lemma", EXPECTED)
def test_reviewed_verb_senses_reject_regression_and_recover(lemma):
    heads, entries = dictionaries()
    healthy = entries[lemma]
    assert healthy["senses"] == EXPECTED[lemma]
    assert lint_senses("en", {lemma: healthy}, heads, required={lemma}) == []
    damaged = deepcopy(healthy)
    damaged["senses"][0] = damaged["senses"][0].removeprefix("to ")
    errors = lint_senses("en", {lemma: damaged}, heads, required={lemma})
    assert len(errors) == 1 and "English verb senses use an infinitive" in errors[0]
    assert lint_senses("en", {lemma: healthy}, heads, required={lemma}) == []
    assert dictionaries()[1][lemma] == healthy


@pytest.mark.parametrize(
    "sense",
    [
        "place, set",
        "arrange, station",
        "invest",
        "bring forth, produce",
        "send out, utter",
        "publish, announce",
        "give off a scent",
        "be fragrant",
        "fall in death",
        "die",
    ],
)
def test_bare_english_verb_meanings_are_rejected(sense):
    errors = sense_errors("test", [sense])
    assert len(errors) == 1 and "English verb senses use an infinitive" in errors[0]


@pytest.mark.parametrize("lemma,sense", FORMULAS.items())
def test_exact_formula_is_preserved_but_not_a_whole_head_exemption(lemma, sense):
    assert sense_errors(lemma, [sense]) == []
    errors = sense_errors(lemma, [sense, "walk"])
    assert len(errors) == 1 and "English verb senses use an infinitive" in errors[0]
    assert sense_errors(lemma, [sense]) == []


@pytest.mark.parametrize("lemma,sense", FORMULAS.items())
def test_formula_cannot_be_copied_to_another_verb(lemma, sense):
    assert sense_errors(lemma, [sense]) == []
    errors = sense_errors("another", [sense])
    assert len(errors) == 1 and "English verb senses use an infinitive" in errors[0]


@pytest.mark.parametrize("sense", ["to know", "not to know"])
def test_positive_and_negative_infinitives_are_valid(sense):
    assert sense_errors("test", [sense]) == []


def test_polish_verbs_and_english_nouns_are_not_subject_to_english_verb_rule():
    assert sense_errors("test", ["umierać"], language="pl") == []
    assert sense_errors("test", ["place"], pos="noun") == []


def test_occumbo_note_explains_the_shared_head_not_one_prayer():
    _heads, entries = dictionaries()
    assert entries["occumbo"]["note"] == (
        "With a person as subject, it can mean to die or fall dead. "
        "Of heavenly bodies, it can mean to set."
    )
