"""Keep Common Preface caption case tied to its actual sentence boundaries."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REL = "texts/ordinarium/praefatio-communis.json"
LEADS = {
    "w001": ("s02", "Vere", "Truly", "truly"),
    "w026": ("s04", "Per", "Through", "through"),
    "w036": ("s05", "Cæli", "The heavens", "the heavens"),
}
CASE_CONTROLS = {
    "w017": ("holy", "Holy", "internal adjective"),
    "w018": ("Father", "father", "divine title"),
    "w022": ("through", "Through", "internal colon"),
    "w027": ("whom", "Whom", "relative pronoun"),
}


def load():
    return (
        json.loads((ROOT / REL).read_text()),
        json.loads((ROOT / "languages/en" / REL).read_text()),
    )


def assert_caption_case(core, layer):
    assert core["id"] == layer["text"] == "ordinarium.praefatio-communis"
    verses = {s["id"]: s for s in core["segments"] if s["type"] == "verse"}
    for wid, (sid, form, gloss, _old) in LEADS.items():
        word = verses[sid]["words"][0]
        assert word["id"] == wid, wid + " source position"
        assert word["form"] == form, wid + " source form"
        assert layer["words"][wid] == {"gloss": gloss}, wid + " sentence lead"
        assert not any(
            wid in group["words"] for group in layer["segments"][sid].get("alignments", [])
        ), wid + " direct realization"
    for sid, wid in [("s03", "w025"), ("s04", "w035")]:
        last = verses[sid]["words"][-1]
        assert last["id"] == wid, wid + " preceding source position"
        assert last["post"] == ".", wid + " sentence boundary"
        assert layer["segments"][sid]["translation"].endswith("."), wid + " target boundary"
    address = {word["id"]: word for word in verses["s03"]["words"]}
    assert address["w021"]["form"] == "Deus"
    assert address["w021"]["post"] == ":", "internal source colon"
    assert address["w022"]["form"] == "per"
    for wid, (good, _bad, label) in CASE_CONTROLS.items():
        assert layer["words"][wid]["gloss"] == good, wid + " " + label


def test_common_preface_caption_leads_and_internal_case_controls():
    assert_caption_case(*load())


@pytest.mark.parametrize("wid", LEADS)
def test_each_lowercase_regression_has_its_own_failure(wid):
    core, layer = load()
    assert_caption_case(core, layer)
    layer["words"][wid]["gloss"] = LEADS[wid][3]
    with pytest.raises(AssertionError, match=wid + " sentence lead"):
        assert_caption_case(core, layer)


@pytest.mark.parametrize("wid", CASE_CONTROLS)
def test_internal_continuations_and_divine_title_keep_their_distinct_rules(wid):
    core, layer = load()
    assert_caption_case(core, layer)
    _good, bad, label = CASE_CONTROLS[wid]
    layer["words"][wid]["gloss"] = bad
    with pytest.raises(AssertionError, match=wid + " " + label):
        assert_caption_case(core, layer)


@pytest.mark.parametrize("sid,wid", [("s03", "w025"), ("s04", "w035")])
def test_case_decision_is_bound_to_the_actual_preceding_sentence(sid, wid):
    core, layer = load()
    assert_caption_case(core, layer)
    damaged = deepcopy(core)
    next(s for s in damaged["segments"] if s["id"] == sid)["words"][-1]["post"] = ","
    with pytest.raises(AssertionError, match=wid + " sentence boundary"):
        assert_caption_case(damaged, layer)


def test_unrelated_reader_context_does_not_trip_the_caption_case_contract():
    core, layer = load()
    assert_caption_case(core, layer)
    layer["about"] += " Further context can be added independently."
    assert_caption_case(core, layer)
