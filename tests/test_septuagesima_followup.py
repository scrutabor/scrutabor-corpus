"""Septuagesima preserves actors, petitions, pay and common-source boundaries."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.bibliography_bindings import digest, selected_text, witness_subject
from checks.interlinear import alignments_for, check
from checks.language_packs import check_core, check_layer

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "proprium.dominica-in-septuagesima-"
COUNTS = dict(
    introitus=78,
    collecta=42,
    epistola=127,
    graduale=35,
    tractus=37,
    evangelium=240,
    offertorium=9,
    communio=19,
    postcommunio=39,
)
GROUPS = [
    ("introitus", "en", 1, 4, 1, "The groans of death surrounded me"),
    ("introitus", "en", 57, 60, 57, "The groans of death surrounded me"),
    ("collecta", "pl", 8, 14, 14, "abyśmy, słusznie cierpiąc za nasze grzechy,"),
    (
        "collecta",
        "en",
        1,
        7,
        7,
        "We beseech You, O Lord, graciously hear the prayers of Your people",
    ),
    ("epistola", "pl", 51, 53, 53, "jakbym bił powietrze"),
    ("epistola", "pl", 121, 127, 125, "większość z nich nie znalazła upodobania u Boga"),
    ("epistola", "en", 30, 36, 36, "And they indeed do so to receive a perishable crown"),
    ("epistola", "en", 121, 127, 125, "God was not pleased with most of them"),
    ("graduale", "pl", 6, 8, 6, "niech Tobie ufają"),
    ("graduale", "en", 19, 24, 23, "the poor man will not be forgotten forever"),
    ("tractus", "pl", 20, 21, 21, "będziesz zważał na nieprawości"),
    ("tractus", "en", 20, 21, 21, "You mark iniquities"),
    ("evangelium", "pl", 59, 63, 62, "dam wam to, co będzie słuszne"),
    (
        "evangelium",
        "en",
        131,
        141,
        139,
        "When those who had arrived about the eleventh hour came, they received a denarius each",
    ),
    ("evangelium", "en", 142, 147, 147, "But when the first also came, they thought"),
    ("evangelium", "en", 170, 173, 173, "you have made them equal to us"),
    ("evangelium", "en", 202, 210, 202, "but I want to give this last worker the same as you"),
    ("evangelium", "en", 211, 217, 213, "Or is it not lawful for me to do what I want?"),
    ("communio", "pl", 15, 16, 16, "niech nie doznam zawstydzenia"),
    ("communio", "en", 15, 16, 16, "let me not be put to shame"),
    (
        "postcommunio",
        "pl",
        8,
        17,
        12,
        "aby zarówno szukali tych samych darów, przyjmując je, "
        "jak i przyjmowali je bez końca, szukając ich",
    ),
    (
        "postcommunio",
        "en",
        8,
        17,
        12,
        "that they may both seek those same gifts by receiving them, "
        "and receive them without end by seeking them",
    ),
    (
        "epistola",
        "pl",
        62,
        69,
        69,
        "abym przypadkiem, głosiwszy innym naukę, sam nie został odrzucony",
    ),
    ("graduale", "en", 27, 30, 28, "will never perish"),
]
SUPPLEMENTS = {
    "introitus": ["gloria-expansion", "introit-repeat"],
    "collecta": ["expanded-conclusion", "oration-boundaries", "responsive-oration"],
    "graduale": ["continuation"],
    "postcommunio": [
        "expanded-conclusion",
        "oration-boundaries",
        "postcommunion-mode",
        "postcommunion-ritus",
        "responsive-oration",
    ],
}


def load(path):
    return json.loads((ROOT / path).read_text())


def core(role):
    return load(f"texts/proprium/dominica-in-septuagesima-{role}.json")


def layer(role, language):
    return load(f"languages/{language}/texts/proprium/dominica-in-septuagesima-{role}.json")


def verify_group(doc, target, case):
    _, _, lo, hi, anchor, gloss = case
    words = [f"w{n:03d}" for n in range(lo, hi + 1)]
    groups = alignments_for(target, "s01")
    selected = [g for g in groups if set(g["words"]) & set(words)]
    assert selected == [{"words": words, "anchor": f"w{anchor:03d}", "gloss": gloss}]
    assert check(doc, target) == []


@pytest.mark.parametrize("case", GROUPS)
def test_complete_owned_caption_constructions(case):
    role, language = case[:2]
    verify_group(core(role), layer(role, language), case)


@pytest.mark.parametrize("damage", ["word", "anchor", "member", "duplicate"])
def test_caption_integrity_controls_are_live(damage):
    case = GROUPS[13]
    doc, target = core(case[0]), layer(case[0], case[1])
    verify_group(doc, target, case)
    broken = deepcopy(target)
    g = next(g for g in broken["segments"]["s01"]["alignments"] if g["words"][0] == "w131")
    if damage == "word":
        g["gloss"] = g["gloss"].replace("they received", "he received")
    elif damage == "anchor":
        g["anchor"] = "w131"
    elif damage == "member":
        g["words"].remove("w139")
    else:
        broken["segments"]["s01"]["alignments"].append(deepcopy(g))
    with pytest.raises(AssertionError):
        verify_group(doc, broken, case)
    verify_group(doc, target, case)


def verify_local_analysis(doc, word_id, gender=None):
    w = next(w for s in doc["segments"] for w in s["words"] if w["id"] == word_id)
    a = doc["editorial"]["words"][word_id]["analysis"]
    assert a == {
        "confidence": "medium",
        "sources": ["editorial", "whitakers", "collatinus"],
        "review": "pending",
    }
    if gender is not None:
        assert w["morph"]["gender"] == gender
    elif word_id == "w179":
        assert w["morph"]["case"] == "gen" and w["morph"]["number"] == "sg"
    else:
        assert w["morph"]["mood"] == "ind" and w["morph"]["tense"] == "futperf"
    assert word_id in doc["localization"]["explanations"]


@pytest.mark.parametrize(
    "role,word_id,gender",
    [
        ("evangelium", "w061", None),
        ("evangelium", "w179", None),
        ("evangelium", "w205", "m"),
        ("tractus", "w021", None),
    ],
)
def test_contextual_choice_not_promoted_by_form_agreement(role, word_id, gender):
    doc = core(role)
    verify_local_analysis(doc, word_id, gender)
    for language in ("pl", "en"):
        target = layer(role, language)
        assert target["words"][word_id]["explanation"]
        assert (
            check_layer(
                doc,
                target,
                ROOT / f"languages/{language}/texts/proprium/dominica-in-septuagesima-{role}.json",
            )
            == []
        )


def test_huic_worker_gender_control_is_contextual():
    doc = core("evangelium")
    verify_local_analysis(doc, "w205", "m")
    broken = deepcopy(doc)
    next(w for s in broken["segments"] for w in s["words"] if w["id"] == "w205")["morph"][
        "gender"
    ] = "f"
    with pytest.raises(AssertionError):
        verify_local_analysis(broken, "w205", "m")
    verify_local_analysis(doc, "w205", "m")


def verify_source_inventory(graph, role):
    text = PREFIX + role
    witness = next(w for w in graph["witnesses"] if w["id"] == f"witness.{text}.mr1962")
    expected = sorted(f"use.{text}.{suffix}.mr1962" for suffix in SUPPLEMENTS.get(role, []))
    assert witness["source_dependencies"] == {"uses": expected, "raw_binding": None}
    assert witness["review"] == {"status": "pending"}
    subject = witness_subject(ROOT, witness, graph, core(role))
    assert set(subject["source_uses"]) == set(expected) | {witness["use"]}


@pytest.mark.parametrize("role", COUNTS)
def test_complete_body_and_source_inventory(role):
    doc = core(role)
    assert sum(len(s["words"]) for s in doc["segments"]) == COUNTS[role]
    assert check_core(doc) == []
    graph = load("bibliography/graph.json")
    verify_source_inventory(graph, role)
    collation = next(c for c in graph["collations"] if c["text"] == PREFIX + role)
    assert collation["selected_text_sha256"] == digest(selected_text(doc))
    assert collation["review"] == {"status": "pending"}


@pytest.mark.parametrize("role", SUPPLEMENTS)
def test_common_expansion_and_continuation_cannot_be_omitted(role):
    graph = load("bibliography/graph.json")
    verify_source_inventory(graph, role)
    broken = deepcopy(graph)
    witness = next(w for w in broken["witnesses"] if w["id"] == f"witness.{PREFIX + role}.mr1962")
    witness["source_dependencies"]["uses"].pop()
    with pytest.raises(AssertionError):
        verify_source_inventory(broken, role)
    verify_source_inventory(graph, role)


def test_latin_impersonal_representation_and_plus_are_not_retagged():
    ep = core("epistola")
    gospel = core("evangelium")
    words = {w["id"]: w for s in ep["segments"] for w in s["words"]}
    assert words["w125"]["substantive"] is True
    assert words["w127"]["morph"]["case"] == "dat"
    words = {w["id"]: w for s in gospel["segments"] for w in s["words"]}
    assert words["w112"]["substantive"] is True
    assert words["w149"]["morph"]["pos"] == "adv"
    assert "with mine own" not in layer("evangelium", "en")["segments"]["s01"]["translation"]
