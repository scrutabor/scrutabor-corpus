"""Finite readings preserve tense, negation, patient and dependent phrases."""

from pathlib import Path

import pytest

from build_reader import store
from checks import interlinear

ROOT = Path(__file__).resolve().parents[1]
CHRISTMAS = "nativitas-domini-in-die-introitus"
BAPTIST = "nativitas-sancti-ioannis-baptistae-evangelium"
BLOOD = "pretiosissimi-sanguinis-domini-nostri-iesu-christi"
HEART = "sacratissimi-cordis-iesu-evangelium"


@pytest.mark.parametrize(
    "name,segment,members,gloss",
    [
        (CHRISTMAS, "s01", [2, 3], "is born"),
        (CHRISTMAS, "s01", [7, 8], "is given"),
        (CHRISTMAS, "s01", [50, 51], "is born"),
        (CHRISTMAS, "s01", [55, 56], "is given"),
        (BAPTIST, "s01", [2, 3], "was fulfilled"),
        (BAPTIST, "s01", [70, 71], "him to be called"),
        (BAPTIST, "s01", [85, 86], "was opened"),
        (BAPTIST, "s01", [139, 140], "was filled"),
        (BLOOD + "-communio", "s01", [3, 4], "was offered"),
        (BLOOD + "-communio", "s01", [6, 7, 8], "take away the sins of many"),
        (BLOOD + "-evangelium", "s01", [9, 10], "It is finished"),
        (BLOOD + "-evangelium", "s01", [53, 54], "had been crucified"),
        (BLOOD + "-evangelium", "s01", [67, 68], "did not break"),
        (BLOOD + "-evangelium", "s01", [87, 88], "has borne witness"),
        (HEART, "s02", [40, 41], "had been crucified"),
        (HEART, "s03", [54, 55], "did not break"),
        (HEART, "s04", [74, 75], "has borne witness"),
        (HEART, "s05", [99, 100], "you shall not break"),
    ],
)
def test_complete_predicate_and_complement(name, segment, members, gloss):
    core, layers = store.load(ROOT, "proprium." + name)
    layer = layers["en"]
    assert interlinear.check(core, layer) == []
    ids = [f"w{n:03}" for n in members]
    groups = layer["segments"][segment]["alignments"]
    group = next(g for g in groups if g["words"] == ids)
    assert group == {"words": ids, "anchor": ids[0], "gloss": gloss}
    assert all(not layer["words"][wid].get("gloss") for wid in ids)


@pytest.mark.parametrize("name", [BLOOD + "-evangelium", HEART])
def test_removal_refers_to_bodies_not_legs(name):
    _, layers = store.load(ROOT, "proprium." + name)
    prose = layers["en"]["segments"]["s01"]["translation"]
    assert "their legs might be broken and that the bodies might be taken away" in prose


def test_christmas_relative_clause_belongs_to_its_antecedent():
    _, layers = store.load(ROOT, "proprium." + CHRISTMAS)
    prose = layers["en"]["segments"]["s01"]["translation"]
    assert prose.count(", whose government is upon His shoulder") == 2
    assert "; whose government" not in prose


def test_purification_petition_and_conclusion_retain_their_relations():
    _, layers = store.load(ROOT, "proprium.purificatio-beatae-mariae-virginis-collecta")
    layer = layers["en"]
    prose = layer["segments"]["s01"]["translation"]
    for phrase in (
        "Your only-begotten Son",
        "in the nature of our flesh",
        "grant us to be presented to You with purified minds",
        "Through the same Jesus Christ, our Lord, Your Son",
        "who lives and reigns with You in the unity of the Holy Spirit",
        "God, for ever and ever",
    ):
        assert phrase in prose
    assert layer["segments"]["s02"]["translation"] == "Amen."


@pytest.mark.parametrize(
    "name,words,segments",
    [
        (CHRISTMAS, 69, 1),
        (BAPTIST, 156, 1),
        (BLOOD + "-communio", 16, 1),
        (BLOOD + "-evangelium", 93, 1),
        ("purificatio-beatae-mariae-virginis-collecta", 52, 2),
        (HEART, 111, 5),
    ],
)
def test_whole_english_reading_keeps_one_provider_per_word(name, words, segments):
    core, layers = store.load(ROOT, "proprium." + name)
    assert len(core["segments"]) == segments
    assert sum(len(s.get("words", [])) for s in core["segments"]) == words
    assert interlinear.check(core, layers["en"]) == []
