"""Contextual finite predicates; shared auxiliaries and valid ellipses remain."""

import copy
from pathlib import Path

import pytest

from build_reader import store
from checks import english, interlinear, polish

ROOT = Path(__file__).resolve().parents[1]
READINGS = [
    ("pl", "epiphania-domini-evangelium", [2, 3], 2, {"narodził się"}),
    ("en", "ascensio-domini-evangelium", [85, 86], 85, {"He had spoken", "He spoke"}),
    (
        "en",
        "dominica-ii-post-pentecosten-evangelium",
        [29, 30, 31],
        29,
        {"everything is ready", "everything has been prepared"},
    ),
    ("en", "epiphania-domini-evangelium", [2, 3, 4], 2, {"Jesus had been born", "Jesus was born"}),
    (
        "en",
        "sanctissimi-nominis-iesu-epistola",
        [63, 64],
        63,
        {"was rejected", "has been rejected"},
    ),
    (
        "en",
        "sanctorum-innocentium-martyrum-epistola",
        [86, 87, 88],
        88,
        {"have not been defiled", "were not defiled"},
    ),
    (
        "en",
        "sanctorum-innocentium-martyrum-graduale",
        [11, 12],
        11,
        {"has been broken", "was broken", "is broken"},
    ),
    (
        "en",
        "sanctorum-innocentium-martyrum-offertorium",
        [11, 12],
        11,
        {"has been broken", "was broken", "is broken"},
    ),
    ("en", "vigilia-paschalis-evangelium", [73, 74], 73, {"was crucified", "has been crucified"}),
    (
        "en",
        "vigilia-paschalis-evangelium",
        [88, 89, 90],
        88,
        {"the Lord had been laid", "the Lord was laid"},
    ),
]


def assert_reading(doc, layer, numbers, anchor, accepted):
    ids = [f"w{n:03d}" for n in numbers]
    groups = [
        g for g in layer["segments"]["s01"].get("alignments", []) if set(g["words"]) & set(ids)
    ]
    assert len(groups) == 1
    assert groups[0]["words"] == ids
    assert groups[0]["anchor"] == f"w{anchor:03d}"
    assert groups[0]["gloss"] in accepted
    assert all("gloss" not in layer["words"][wid] for wid in ids)
    assert interlinear.check(doc, layer) == []


@pytest.mark.parametrize("language,slug,numbers,anchor,accepted", READINGS)
def test_contextual_finiteness(language, slug, numbers, anchor, accepted):
    doc, layers = store.load(ROOT, "proprium." + slug)
    assert_reading(doc, layers[language], numbers, anchor, accepted)


@pytest.mark.parametrize("language,slug,numbers,anchor,accepted", READINGS)
def test_other_faithful_tenses_do_not_create_provider_errors(
    language, slug, numbers, anchor, accepted
):
    doc, layers = store.load(ROOT, "proprium." + slug)
    layer = copy.deepcopy(layers[language])
    ids = [f"w{n:03d}" for n in numbers]
    groups = layer["segments"]["s01"]["alignments"]
    groups[:] = [g for g in groups if not set(g["words"]) & set(ids)]
    group = {"words": ids, "anchor": f"w{anchor:03d}", "gloss": ""}
    groups.append(group)
    groups.sort(key=lambda g: g["words"][0])
    for wid in ids:
        layer["words"][wid].pop("gloss", None)
    for gloss in sorted(accepted):
        group["gloss"] = gloss
        assert_reading(doc, layer, numbers, anchor, accepted)
        assert (english if language == "en" else polish).check(doc, layer) == []


@pytest.mark.parametrize(
    "slug,first,gloss,external",
    [
        (
            "dominica-xiii-post-pentecosten-evangelium",
            87,
            "cleansed",
            {"w085": "Were not", "w086": "ten"},
        ),
        (
            "sanctorum-simonis-et-iudae-apostolorum-evangelium",
            95,
            "spoken",
            {"w091": "If I", "w093": "had not come", "w094": "and"},
        ),
    ],
)
def test_existing_auxiliary_is_shared_not_duplicated(slug, first, gloss, external):
    doc, layers = store.load(ROOT, "proprium." + slug)
    layer = layers["en"]
    assert_reading(doc, layer, [first, first + 1], first, {gloss})
    for wid, expected in external.items():
        assert interlinear.effective_gloss(layer, wid) == expected


def test_polish_present_copula_ellipsis_is_retained():
    doc, layers = store.load(ROOT, "proprium.dominica-ii-post-pentecosten-evangelium")
    assert_reading(doc, layers["pl"], [29, 30], 29, {"gotowe"})
    assert layers["pl"]["words"]["w031"]["gloss"] == "wszystko"


def test_traditional_subject_inversion_is_a_valid_alternative_not_selected_mapping():
    doc, layers = store.load(ROOT, "proprium.vigilia-paschalis-evangelium")
    layer = copy.deepcopy(layers["en"])
    groups = layer["segments"]["s01"]["alignments"]
    ids = {"w088", "w089", "w090"}
    groups[:] = [g for g in groups if not ids & set(g["words"])]
    groups.append({"words": ["w088", "w089"], "anchor": "w088", "gloss": "had been laid"})
    groups.sort(key=lambda g: g["words"][0])
    for wid in ["w088", "w089"]:
        layer["words"][wid].pop("gloss", None)
    layer["words"]["w090"]["gloss"] = "the Lord"
    assert interlinear.check(doc, layer) == []
    assert english.check(doc, layer) == []


# Appended to the existing test module; contextual preservation, not a grammar law.
BOUNDARIES = [
    (
        "en",
        "ascensio-domini-evangelium",
        {
            81: ("dominus", "the Lord"),
            83: ("Iesus", "Jesus"),
            84: ("postquam", "when"),
            87: ("is", "to them"),
            90: ("in", "into"),
            91: ("caelum", "heaven"),
        },
        [([88, 89], 88, "was taken up")],
    ),
    (
        "en",
        "sanctissimi-nominis-iesu-epistola",
        {
            61: ("lapis", "the stone"),
            62: ("qui", "which"),
            65: ("ab", "by"),
            66: ("vos", "you"),
            67: ("aedifico", "the builders"),
        },
        [],
    ),
    (
        "en",
        "sanctorum-innocentium-martyrum-epistola",
        {83: ("qui", "those who"), 84: ("cum", "with"), 85: ("mulier", "women")},
        [([89, 90, 91], 89, "for they are virgins")],
    ),
    (
        "en",
        "vigilia-paschalis-evangelium",
        {
            70: ("quod", "that"),
            71: ("Iesus", "Jesus"),
            72: ("qui", "who"),
            75: ("quaero", "you seek"),
            86: ("locus", "the place"),
            87: ("ubi", "where"),
        },
        [],
    ),
    (
        "en",
        "epiphania-domini-evangelium",
        {1: ("cum", "When"), 5: ("in", "in"), 6: ("Bethlehem", "Bethlehem")},
        [],
    ),
    (
        "pl",
        "epiphania-domini-evangelium",
        {1: ("cum", "Gdy"), 4: ("Iesus", "Jezus"), 5: ("in", "w")},
        [],
    ),
    (
        "en",
        "dominica-ii-post-pentecosten-evangelium",
        {27: ("quia", "for"), 28: ("iam", "now")},
        [],
    ),
]


def assert_boundary(doc, layer, direct, groups):
    words = {w["id"]: w for s in doc["segments"] for w in s.get("words", [])}
    aligned = interlinear.alignment_by_word(layer)
    for number, (lemma, gloss) in direct.items():
        wid = f"w{number:03d}"
        assert words[wid]["lemma"] == lemma
        assert wid not in aligned
        assert layer["words"][wid]["gloss"] == gloss
    for numbers, anchor, gloss in groups:
        assert_reading(doc, layer, numbers, anchor, {gloss})
    assert interlinear.check(doc, layer) == []


@pytest.mark.parametrize("language,slug,direct,groups", BOUNDARIES)
def test_external_subjects_recipients_agents_and_clause_links_remain(
    language, slug, direct, groups
):
    doc, layers = store.load(ROOT, "proprium." + slug)
    assert_boundary(doc, layers[language], direct, groups)
