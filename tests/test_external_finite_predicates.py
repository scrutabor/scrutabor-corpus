"""Compound finite predicates retain natural order and their contextual tense."""

from pathlib import Path

import pytest

from build_reader import store
from checks import interlinear

ROOT = Path(__file__).resolve().parents[1]
READINGS = [
    ("ordinarium.evangelium-ultimum", "s10", 164, 165, "were born"),
    ("ordinarium.lavabo", "s06", 50, 51, "is filled"),
    ("proprium.assumptio-beatae-mariae-virginis-evangelium", "s01", 4, 5, "was filled"),
    ("proprium.dominica-i-post-epiphaniam-epistola", "s01", 46, 47, "is given"),
    ("proprium.dominica-ii-passionis-evangelium", "s79", 1173, 1174, "were crucified"),
    ("proprium.dominica-ii-passionis-evangelium", "s83", 1262, 1263, "had been crucified"),
    ("proprium.dominica-ii-post-epiphaniam-epistola", "s01", 7, 8, "is given"),
    ("proprium.dominica-in-albis-epistola", "s01", 4, 5, "is born"),
    ("proprium.dominica-xi-post-pentecosten-evangelium", "s01", 63, 64, "were opened"),
    ("proprium.dominica-xiii-post-pentecosten-epistola", "s01", 98, 99, "had been given"),
    ("proprium.dominica-xix-post-pentecosten-evangelium", "s01", 139, 140, "was filled"),
    ("proprium.dominica-xviii-post-pentecosten-epistola", "s01", 13, 14, "was given"),
    ("proprium.dominica-xxi-post-pentecosten-evangelium", "s01", 28, 29, "was brought"),
    ("proprium.dominica-xxi-post-pentecosten-offertorium", "s01", 20, 21, "was given"),
    ("proprium.epiphania-domini-evangelium", "s01", 22, 23, "has been born"),
    ("proprium.immaculata-conceptio-tractus", "s01", 22, 23, "is born"),
    ("proprium.nativitas-domini-in-aurora-introitus", "s01", 7, 8, "is born"),
    ("proprium.nativitas-domini-in-aurora-introitus", "s01", 63, 64, "is born"),
    ("proprium.nativitas-domini-in-die-evangelium", "s01", 150, 151, "were born"),
    ("proprium.nativitas-domini-in-nocte-evangelium", "s01", 70, 71, "were fulfilled"),
    ("proprium.nativitas-domini-in-nocte-evangelium", "s01", 143, 144, "is born"),
    (
        "proprium.purificatio-beatae-mariae-virginis-evangelium",
        "s01",
        5,
        9,
        "the days of Mary’s purification were fulfilled",
    ),
    ("proprium.sacratissimi-cordis-iesu-epistola", "s01", 6, 7, "is given"),
    (
        "proprium.sancti-ioseph-sponsi-beatae-mariae-virginis-communio",
        "s01",
        14,
        15,
        "has been begotten",
    ),
    (
        "proprium.sancti-ioseph-sponsi-beatae-mariae-virginis-extra-tempus-paschale-communio",
        "s01",
        14,
        15,
        "has been begotten",
    ),
    ("proprium.sanctissimae-trinitatis-evangelium", "s01", 8, 9, "Is given"),
    ("proprium.vigilia-nativitatis-evangelium", "s01", 58, 59, "has been begotten"),
    ("proprium.visitatio-beatae-mariae-virginis-evangelium", "s01", 36, 37, "was filled"),
]


@pytest.mark.parametrize("text,segment,first,last,gloss", READINGS)
def test_finite_realization_keeps_auxiliary_and_context(text, segment, first, last, gloss):
    core, layers = store.load(ROOT, text)
    layer = layers["en"]
    members = [f"w{n:03}" for n in range(first, last + 1)]
    group = next(
        g for g in layer["segments"][segment].get("alignments", []) if g["words"] == members
    )
    assert group == {"words": members, "anchor": members[0], "gloss": gloss}
    assert all(not layer["words"][word].get("gloss") for word in members)
    assert interlinear.check(core, layer) == []


@pytest.mark.parametrize("text", sorted({r[0] for r in READINGS}))
def test_whole_finite_reading_has_one_provider_per_word(text):
    core, layers = store.load(ROOT, text)
    assert interlinear.check(core, layers["en"]) == []
