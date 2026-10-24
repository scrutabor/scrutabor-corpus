"""Sentence case and direct-address relatives in the Trinity Preface."""

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REL = "texts/ordinarium/praefatio-sanctissimae-trinitatis.json"
CASES = [
    ("pl", "w046", "co", "Co"),
    ("pl", "w066", "aby", "Aby"),
    ("pl", "w085", "którą", "Którą"),
    ("en", "w001", "truly", "Truly"),
    ("en", "w066", "that", "That"),
    ("en", "w085", "which", "Which"),
]


def load():
    core = json.loads((ROOT / REL).read_text(encoding="utf-8"))
    layers = {
        language: json.loads((ROOT / "languages" / language / REL).read_text(encoding="utf-8"))
        for language in ("pl", "en")
    }
    return core, layers


def words(core):
    return {w["id"]: w for segment in core["segments"] for w in segment.get("words", [])}


def assert_case(layer, language, wid, expected):
    assert layer["words"][wid].get("gloss") == expected, (
        f"{language} {wid}: sentence-opening caption"
    )
    assert not any(
        wid in group["words"]
        for segment in layer["segments"].values()
        for group in segment.get("alignments", [])
    ), f"{language} {wid}: sentence lead remains directly realized"


def assert_boundaries(core):
    indexed = words(core)
    assert indexed["w021"].get("post") == ":", "w021: address continues before Qui"
    for wid in ("w045", "w065", "w084"):
        assert indexed[wid].get("post") == ".", f"{wid}: sentence-ending source punctuation"


def assert_relative(core, layers):
    indexed = words(core)
    relative = indexed["w022"]
    assert relative["lemma"] == "qui", "w022: relative lemma, not a forced tu"
    assert {key: relative["morph"].get(key) for key in ("pos", "case", "number", "gender")} == {
        "pos": "pron",
        "case": "nom",
        "number": "sg",
        "gender": "m",
    }, "w022: nominative masculine singular relative"
    for wid in ("w031", "w034"):
        verb = indexed[wid]
        assert verb["lemma"] == "sum" and verb["form"] == "es", f"{wid}: addressed es retained"
        assert (verb["morph"].get("person"), verb["morph"].get("number")) == (2, "sg"), (
            f"{wid}: second-person singular address"
        )
    for language, expected in (("pl", "który"), ("en", "who")):
        assert layers[language]["words"]["w022"].get("gloss") == expected, (
            f"{language} w022: lower-case continuing relative"
        )


@pytest.mark.parametrize("language,wid,before,after", CASES)
def test_selected_sentence_lead(language, wid, before, after):
    core, layers = load()
    assert_boundaries(core)
    assert_case(layers[language], language, wid, after)


@pytest.mark.parametrize("language,wid,before,after", CASES)
def test_old_lower_case_is_rejected_at_its_caption_site(language, wid, before, after):
    _, layers = load()
    layer = layers[language]
    assert_case(layer, language, wid, after)
    changed = deepcopy(layer)
    changed["words"][wid]["gloss"] = before
    with pytest.raises(
        AssertionError, match=re.escape(f"{language} {wid}: sentence-opening caption")
    ):
        assert_case(changed, language, wid, after)


@pytest.mark.parametrize("language,wid,before,after", CASES)
def test_extra_realization_cannot_hide_behind_a_correct_capital(language, wid, before, after):
    _, layers = load()
    layer = layers[language]
    assert_case(layer, language, wid, after)
    changed = deepcopy(layer)
    changed["segments"]["s02"].setdefault("alignments", []).append(
        {"words": [wid], "anchor": wid, "gloss": after}
    )
    message = f"{language} {wid}: sentence lead remains directly realized"
    with pytest.raises(AssertionError, match=re.escape(message)):
        assert_case(changed, language, wid, after)


def test_relative_and_both_addressed_predicates_are_retained():
    core, layers = load()
    assert_relative(core, layers)


@pytest.mark.parametrize("wid", ["w021", "w045", "w065", "w084"])
def test_case_decision_requires_the_actual_boundary(wid):
    core, _ = load()
    assert_boundaries(core)
    changed = deepcopy(core)
    words(changed)[wid]["post"] = ","
    message = (
        "w021: address continues before Qui"
        if wid == "w021"
        else f"{wid}: sentence-ending source punctuation"
    )
    with pytest.raises(AssertionError, match=re.escape(message)):
        assert_boundaries(changed)


@pytest.mark.parametrize(
    "site,message",
    [
        ("lemma", "w022: relative lemma, not a forced tu"),
        ("case", "w022: nominative masculine singular relative"),
        ("w031", "w031: second-person singular address"),
        ("w034", "w034: second-person singular address"),
        ("pl", "pl w022: lower-case continuing relative"),
        ("en", "en w022: lower-case continuing relative"),
    ],
)
def test_forced_pronoun_or_changed_person_is_rejected_at_its_site(site, message):
    core, layers = load()
    assert_relative(core, layers)
    changed, changed_layers = deepcopy(core), deepcopy(layers)
    indexed = words(changed)
    if site == "lemma":
        indexed["w022"]["lemma"] = "tu"
    elif site == "case":
        indexed["w022"]["morph"]["case"] = "acc"
    elif site in ("w031", "w034"):
        indexed[site]["morph"]["person"] = 3
    else:
        changed_layers[site]["words"]["w022"]["gloss"] = "Ty" if site == "pl" else "You"
    with pytest.raises(AssertionError, match=re.escape(message)):
        assert_relative(changed, changed_layers)


def test_internal_descriptors_and_angelic_continuation_are_not_blanket_capitalized():
    _, layers = load()
    for language, holy, relative in (("pl", "święty", "którzy"), ("en", "holy", "and they")):
        assert layers[language]["words"]["w017"]["gloss"] == holy, (
            f"{language} w017: internal descriptor"
        )
        assert layers[language]["words"]["w094"]["gloss"] == relative, (
            f"{language} w094: angelic continuation after colon"
        )


def test_case_contract_does_not_lock_unrelated_prose():
    core, layers = load()
    # Synthetic scope probe, not permission to rewrite protected translation.
    changed = deepcopy(layers)
    changed["en"]["segments"]["s07"]["translation"] = "Unrelated future wording."
    for language, wid, _, after in CASES:
        assert_case(changed[language], language, wid, after)
    assert_relative(core, changed)
