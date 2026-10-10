"""A Latin eternity idiom keeps its internal and without absorbing et."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.layers import enrich_layer, expand_core
from checks.interlinear import check, effective_gloss
from checks.language_packs import check_layer
from checks.lint import lint_gloss

ROOT = Path(__file__).resolve().parents[1]
IDS = ["w064", "w065", "w066"]


def subject():
    rel = "texts/proprium/dominica-in-quinquagesima-introitus.json"
    core = json.loads((ROOT / rel).read_bytes())
    layer = json.loads((ROOT / "languages/en" / rel).read_bytes())
    target = layer["segments"]["s01"]
    covered = {"w063", *IDS}
    target["alignments"] = [
        group for group in target.get("alignments", []) if not covered.intersection(group["words"])
    ]
    for wid in covered:
        layer["words"][wid].pop("gloss", None)
    layer["words"]["w063"]["gloss"] = "and"
    group = {"words": IDS.copy(), "anchor": "w064", "gloss": "forever and ever"}
    target["alignments"].append(group)
    positions = {word["id"]: i for i, word in enumerate(core["segments"][0]["words"])}
    target["alignments"].sort(key=lambda item: positions[item["words"][0]])
    return core, layer, group


def absorption(core, layer):
    return [
        error
        for error in lint_gloss(enrich_layer(core, layer), expand_core(core))
        if "absorbs the conjunction" in error
    ]


def stream(layer):
    return " ".join(filter(None, (effective_gloss(layer, f"w{i:03}") for i in range(63, 67))))


def test_actual_et_with_a_separate_idiom_does_not_duplicate_and():
    core, layer, _ = subject()
    assert check(core, layer) == []
    assert (
        check_layer(
            core,
            layer,
            ROOT / "languages/en/texts/proprium/dominica-in-quinquagesima-introitus.json",
        )
        == []
    )
    assert stream(layer) == "and forever and ever"
    assert absorption(core, layer) == []


def test_equivalent_four_member_group_still_passes():
    core, layer, group = subject()
    group.update(words=["w063", *IDS], anchor="w063", gloss="and forever and ever")
    del layer["words"]["w063"]["gloss"]
    assert check(core, layer) == []
    assert stream(layer) == "and forever and ever"
    assert absorption(core, layer) == []


@pytest.mark.parametrize("caption", ["and forever and ever", "and ever", "forever and truth"])
def test_nonidiomatic_or_prefixed_conjunction_is_not_exempt(caption):
    core, layer, group = subject()
    assert absorption(core, layer) == []
    group["gloss"] = caption
    assert absorption(core, layer)
    if caption == "and forever and ever":
        assert stream(layer) == "and and forever and ever"
    group["gloss"] = "forever and ever"
    assert absorption(core, layer) == []


@pytest.mark.parametrize(
    "wid,field,value",
    [
        ("w063", "form", "aut"),
        ("w063", "lemma", "aut"),
        ("w063", "morph", {"pos": "adv"}),
        ("w064", "form", "per"),
        ("w064", "lemma", "per"),
        ("w064", "morph", {"pos": "prep", "governs": "abl"}),
        ("w065", "form", "veritatem"),
        ("w065", "lemma", "veritas"),
        ("w065", "morph", {"pos": "noun", "case": "abl", "number": "pl"}),
        ("w066", "form", "veritatis"),
        ("w066", "lemma", "veritas"),
        ("w066", "morph", {"pos": "noun", "case": "gen", "number": "sg"}),
    ],
)
def test_wrong_source_identity_or_morphology_cannot_license_internal_and(wid, field, value):
    core, layer, _ = subject()
    assert absorption(core, layer) == []
    word = next(word for word in core["segments"][0]["words"] if word["id"] == wid)
    before = deepcopy(word)
    word[field] = value
    assert absorption(core, layer)
    word.clear()
    word.update(before)
    assert absorption(core, layer) == []


@pytest.mark.parametrize(
    "members", [["w064", "w065"], ["w064", "w066", "w065"], ["w064", "w065", "w067"]]
)
def test_wrong_span_does_not_receive_the_idiom_exception(members):
    core, layer, group = subject()
    group["words"] = members
    assert absorption(core, layer)


def test_bare_word_with_internal_and_is_not_an_idiom_group():
    core, layer, group = subject()
    layer["segments"]["s01"]["alignments"].remove(group)
    layer["words"]["w064"]["gloss"] = "forever and ever"
    layer["words"]["w065"]["gloss"] = "ages"
    layer["words"]["w066"]["gloss"] = "of ages"
    assert check(core, layer) == []
    assert absorption(core, layer)


@pytest.mark.parametrize("wid", ["w064", "w065", "w066"])
def test_duplicate_direct_member_is_still_refused(wid):
    core, layer, _ = subject()
    assert check(core, layer) == []
    layer["words"][wid]["gloss"] = "ages"
    assert any("exactly one direct gloss or alignment" in error for error in check(core, layer))
    del layer["words"][wid]["gloss"]
    assert check(core, layer) == []


def test_anchor_outside_the_span_is_still_refused():
    core, layer, group = subject()
    group["anchor"] = "w063"
    assert any("anchor must name" in error for error in check(core, layer))
    group["anchor"] = "w064"
    assert check(core, layer) == []


def test_duplicate_alignment_is_still_refused():
    core, layer, group = subject()
    assert check(core, layer) == []
    layer["segments"]["s01"]["alignments"].append(deepcopy(group))
    assert any("more than one alignment" in error for error in check(core, layer))
    layer["segments"]["s01"]["alignments"].pop()
    assert check(core, layer) == []


def test_polish_is_not_given_an_english_caption_exception():
    core, layer, _ = subject()
    layer["language"] = "pl"
    layer["words"]["w063"]["gloss"] = "i"
    group = next(
        group for group in layer["segments"]["s01"]["alignments"] if group["anchor"] == "w064"
    )
    group["gloss"] = "na i zawsze"
    assert absorption(core, layer)
