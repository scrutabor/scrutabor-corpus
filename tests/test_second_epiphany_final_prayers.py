"""The final prayers retain their requests, means and separate conclusions."""

from copy import deepcopy

import pytest

from build_reader import store
from checks import interlinear
from checks.layout import CORPUS

DAY = "proprium.dominica-ii-post-epiphaniam-"
GROUPS = [
    ("pl", "secreta", "s01", 1, 4, 4, "Złożone dary, Panie, uświęć"),
    ("pl", "secreta", "s01", 7, 9, 9, "zmaz naszych grzechów"),
    ("en", "secreta", "s01", 1, 4, 4, "Sanctify, Lord, the gifts offered"),
    ("en", "secreta", "s01", 5, 10, 10, "and cleanse us from the stains of our sins"),
    ("en", "secreta", "s01", 12, 13, 12, "our Lord"),
    ("en", "secreta", "s01", 16, 17, 16, "Your Son"),
    ("en", "secreta", "s01", 19, 22, 20, "lives and reigns with You"),
    ("en", "secreta", "s02", 28, 31, 30, "forever and ever"),
    ("pl", "postcommunio", "s01", 6, 8, 8, "działanie Twojej mocy"),
    ("pl", "postcommunio", "s01", 10, 12, 11, "pokrzepieni Bożymi sakramentami"),
    ("pl", "postcommunio", "s01", 14, 16, 16, "otrzymania tego, co obiecują,"),
    (
        "en",
        "postcommunio",
        "s01",
        1,
        8,
        1,
        "May the working of Your power increase within us, we beseech You, Lord,",
    ),
    ("en", "postcommunio", "s01", 10, 12, 11, "strengthened by the divine sacraments,"),
    (
        "en",
        "postcommunio",
        "s01",
        13,
        19,
        19,
        "we may be prepared by Your gift to receive what they promise",
    ),
    ("en", "postcommunio", "s01", 21, 22, 21, "our Lord"),
    ("en", "postcommunio", "s01", 25, 26, 25, "Your Son"),
    ("en", "postcommunio", "s01", 28, 31, 29, "lives and reigns with You"),
    ("en", "postcommunio", "s01", 37, 40, 39, "forever and ever"),
]


def load(language, kind):
    core, layers = store.load(CORPUS, DAY + kind)
    return core, layers[language]


def assert_construction(core, layer, case):
    _, _, segment, first, last, anchor, gloss = case
    members = [f"w{number:03}" for number in range(first, last + 1)]
    matches = [
        group
        for group in layer["segments"][segment].get("alignments", [])
        if group["words"] == members
    ]
    assert matches == [{"words": members, "anchor": f"w{anchor:03}", "gloss": gloss}]
    assert not interlinear.check(core, layer)
    assert [
        interlinear.effective_gloss(layer, word)
        for word in members
        if interlinear.effective_gloss(layer, word)
    ] == [gloss]


@pytest.mark.parametrize("case", GROUPS)
def test_constructions_preserve_requests_and_dependents(case):
    assert_construction(*load(case[0], case[1]), case)


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("kind,count,assent", [("secreta", 32, "s03"), ("postcommunio", 41, "s02")])
def test_all_words_and_separate_assent_remain(language, kind, count, assent):
    core, layer = load(language, kind)
    ids = [word["id"] for segment in core["segments"] for word in segment.get("words", [])]
    assert ids == list(layer["words"]) == [f"w{number:03}" for number in range(1, count + 1)]
    response = next(segment for segment in core["segments"] if segment["id"] == assent)
    assert [(word["id"], word["form"]) for word in response["words"]] == [(f"w{count:03}", "Amen")]
    assert layer["segments"][assent] == {"translation": "Amen."}
    assert layer["words"][f"w{count:03}"] == {"gloss": "Amen"}
    assert not interlinear.check(core, layer)


@pytest.mark.parametrize(
    "language,expected",
    [
        (
            "pl",
            "Niech wzrasta w nas prosimy Panie działanie Twojej mocy abyśmy "
            "pokrzepieni Bożymi sakramentami do otrzymania tego, co obiecują, "
            "Twoim darem zostali przygotowani",
        ),
        (
            "en",
            "May the working of Your power increase within us, we beseech You, Lord, "
            "that strengthened by the divine sacraments, we may be prepared by Your gift "
            "to receive what they promise",
        ),
    ],
)
def test_postcommunion_body_is_a_complete_request(language, expected):
    _, layer = load(language, "postcommunio")
    # Checking the composed sequence catches well-formed but misplaced groups.
    assert (
        " ".join(
            filter(None, (interlinear.effective_gloss(layer, f"w{n:03}") for n in range(1, 20)))
        )
        == expected
    )


@pytest.mark.parametrize("kind", ["secreta", "postcommunio"])
def test_ordinary_english_conclusion_keeps_one_register(kind):
    _, layer = load("en", kind)
    prose = " ".join(segment["translation"] for segment in layer["segments"].values())
    assert prose.endswith(
        "Through our Lord Jesus Christ, Your Son, who lives and reigns with You "
        "in the unity of the Holy Spirit, God, forever and ever. Amen."
    )
    captions = " ".join(interlinear.effective_gloss(layer, word) for word in layer["words"])
    assert not any(
        old in prose or old in captions
        for old in ("Thy", "Thee", "liveth", "reigneth", "Holy Ghost", "world without end")
    )


@pytest.mark.parametrize(
    "damage", ["missing-member", "duplicate-caption", "changed-beneficiary", "changed-means"]
)
def test_contextual_regressions_fail_after_a_healthy_control(damage):
    case = GROUPS[13]
    core, layer = load(case[0], case[1])
    assert_construction(core, layer, case)
    broken = deepcopy(layer)
    group = next(g for g in broken["segments"]["s01"]["alignments"] if g["anchor"] == "w019")
    if damage == "missing-member":
        group["words"].remove("w017")
    elif damage == "duplicate-caption":
        broken["words"]["w017"]["gloss"] = "Your"
    elif damage == "changed-beneficiary":
        group["gloss"] = group["gloss"].replace("we may", "You may")
    else:
        group["gloss"] = group["gloss"].replace("Your gift", "our gift")
    if damage in {"changed-beneficiary", "changed-means"}:
        # Structural validity alone is not semantic correctness.
        assert not interlinear.check(core, broken)
    with pytest.raises(AssertionError):
        assert_construction(core, broken, case)


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("kind,count,assent", [("secreta", 32, "s03"), ("postcommunio", 41, "s02")])
def test_assent_cannot_be_absorbed_into_the_preceding_oration(
    language, kind, count, assent, monkeypatch
):
    core, layer = load(language, kind)
    test_all_words_and_separate_assent_remain(language, kind, count, assent)
    broken = deepcopy(core)
    response = next(segment for segment in broken["segments"] if segment["id"] == assent)
    prior = broken["segments"][broken["segments"].index(response) - 1]
    prior["words"].append(response["words"].pop())
    monkeypatch.setattr(store, "load", lambda *args: (broken, {language: layer}))
    with pytest.raises(AssertionError):
        test_all_words_and_separate_assent_remain(language, kind, count, assent)
