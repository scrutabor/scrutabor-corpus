"""Keep selected command constructions complete in their interlinear captions.

These are contextual regression fixtures, not a universal translation rule for
iubeo. In particular, Polish can use an active infinitive for a passive Latin
complement, whereas English may need to express its implicit patient.
"""

import json
from copy import deepcopy

import pytest

from checks.interlinear import check, effective_gloss
from checks.layout import CORPUS

GROUPS = [
    (
        "ordinarium.hanc-igitur",
        "pl",
        "s03",
        23,
        34,
        32,
        (
            "rozkazał wyrwać nas od wiecznego potępienia i zaliczyć do trzody Twoich wybranych",
            "rozkazał, abyśmy zostali wyrwani od wiecznego potępienia "
            "i zaliczeni do trzody Twoich wybranych",
        ),
    ),
    (
        "ordinarium.hanc-igitur",
        "en",
        "s03",
        23,
        34,
        32,
        (
            "command that we be rescued from eternal damnation "
            "and counted in the flock of Your chosen ones",
            "command that we be snatched from eternal damnation "
            "and numbered in the flock of Your elect",
        ),
    ),
    (
        "ordinarium.supplices-te-rogamus",
        "pl",
        "s02",
        6,
        8,
        6,
        ("rozkaż, aby te dary zostały zaniesione",),
    ),
    (
        "ordinarium.supplices-te-rogamus",
        "en",
        "s02",
        6,
        8,
        6,
        ("command that these offerings be carried",),
    ),
    (
        "proprium.dominica-ii-passionis-evangelium",
        "en",
        "s95",
        1478,
        1480,
        1478,
        ("commanded the body to be delivered", "ordered the body to be handed over"),
    ),
    (
        "proprium.dominica-vi-post-pentecosten-evangelium",
        "en",
        "s01",
        102,
        103,
        102,
        ("commanded them to be served", "commanded that they be served"),
    ),
    (
        "proprium.dominica-xxi-post-pentecosten-evangelium",
        "en",
        "s01",
        44,
        48,
        44,
        ("his master ordered him to be sold", "his master commanded that he be sold"),
    ),
    (
        "proprium.sanctissimi-nominis-iesu-collecta",
        "pl",
        "s01",
        11,
        13,
        13,
        ("nakazałeś, aby nazwano Go Jezusem", "nakazałeś nazywać Go Jezusem"),
    ),
]
DIRECT = [
    ("ordinarium.hanc-igitur", "en", "w013", "that You"),
    ("proprium.dominica-vi-post-pentecosten-evangelium", "pl", "w090", "podawali"),
    ("proprium.dominica-vi-post-pentecosten-evangelium", "pl", "w092", "podali"),
    ("proprium.dominica-vi-post-pentecosten-evangelium", "pl", "w093", "tłumowi"),
    ("proprium.dominica-vi-post-pentecosten-evangelium", "pl", "w103", "podać"),
    ("proprium.dominica-vi-post-pentecosten-evangelium", "en", "w090", "they should serve them"),
    ("proprium.dominica-vi-post-pentecosten-evangelium", "en", "w092", "they served them"),
    ("proprium.dominica-vi-post-pentecosten-evangelium", "en", "w093", "to the crowd"),
]


def load(text, language):
    category, name = text.split(".", 1)
    path = f"texts/{category}/{name}.json"
    return (
        json.loads((CORPUS / path).read_text()),
        json.loads((CORPUS / "languages" / language / path).read_text()),
    )


def group_for(layer, case):
    _, _, segment, first, _, _, _ = case
    return next(
        (
            g
            for g in layer["segments"][segment].get("alignments", [])
            if f"w{first:03d}" in g["words"]
        ),
        None,
    )


def assert_group(doc, layer, case):
    _, _, segment, first, last, anchor, captions = case
    members = [f"w{n:03d}" for n in range(first, last + 1)]
    source = next(s for s in doc["segments"] if s["id"] == segment)["words"]
    assert [w["id"] for w in source if w["id"] in members] == members
    assert next(w for w in source if w["id"] == f"w{anchor:03d}")["lemma"] == "iubeo"
    group = group_for(layer, case)
    assert group is not None, "The whole construction needs one caption"
    assert group["words"] == members
    assert group["anchor"] == f"w{anchor:03d}"
    assert group["gloss"] in captions
    assert all("gloss" not in layer["words"][wid] for wid in members)
    assert check(doc, layer) == []
    assert [
        (wid, effective_gloss(layer, wid)) for wid in members if effective_gloss(layer, wid)
    ] == [(group["anchor"], group["gloss"])]


@pytest.mark.parametrize("case", GROUPS, ids=[f"{c[0]}-{c[1]}" for c in GROUPS])
def test_current_causative_group(case):
    doc, layer = load(case[0], case[1])
    assert_group(doc, layer, case)


@pytest.mark.parametrize("text,language,word,caption", DIRECT)
def test_current_causative_context(text, language, word, caption):
    doc, layer = load(text, language)
    assert layer["words"][word]["gloss"] == caption
    assert check(doc, layer) == []


@pytest.mark.parametrize("case", GROUPS, ids=[f"{c[0]}-{c[1]}" for c in GROUPS])
def test_supported_causative_alternatives(case):
    doc, layer = load(case[0], case[1])
    for caption in case[-1]:
        candidate = deepcopy(layer)
        group_for(candidate, case)["gloss"] = caption
        assert_group(doc, candidate, case)


@pytest.mark.parametrize(
    "mutation", ["lost-member", "duplicate-gloss", "missing-patient", "wrong-lemma"]
)
def test_causative_regression_controls(mutation):
    case = GROUPS[5]
    doc, layer = load(case[0], case[1])
    candidate = deepcopy(layer)
    group = group_for(candidate, case)
    if mutation == "lost-member":
        group["words"].pop()
    elif mutation == "duplicate-gloss":
        candidate["words"]["w103"]["gloss"] = "to be served"
    elif mutation == "missing-patient":
        group["gloss"] = "commanded to be served"
    else:
        next(w for s in doc["segments"] for w in s["words"] if w["id"] == "w102")["lemma"] = (
            "permitto"
        )
    with pytest.raises(AssertionError):
        assert_group(doc, candidate, case)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_hanc_shared_governor_and_both_passives(language):
    doc, layer = load("ordinarium.hanc-igitur", language)
    words = {w["id"]: w for s in doc["segments"] for w in s.get("words", [])}
    assert words["w013"]["lemma"] == "ut"
    assert layer["words"]["w013"]["gloss"] == ("byś" if language == "pl" else "that You")
    for wid in ("w015", "w021", "w032"):
        assert words[wid]["morph"]["person"] == 2
        assert words[wid]["morph"]["mood"] == "subj"
    for wid in ("w027", "w034"):
        assert words[wid]["morph"]["mood"] == "inf"
        assert words[wid]["morph"]["voice"] == "pass"


@pytest.mark.parametrize("language,caption", [("pl", "każ"), ("en", "bid")])
def test_anima_active_infinitive_is_not_forced_into_passive_group(language, caption):
    doc, layer = load("orationes.anima-christi", language)
    words = next(s for s in doc["segments"] if s["id"] == "s11")["words"]
    assert next(w for w in words if w["id"] == "w052")["morph"]["voice"] == "act"
    assert layer["words"]["w050"]["gloss"] == caption
    assert not layer["segments"]["s11"].get("alignments")
