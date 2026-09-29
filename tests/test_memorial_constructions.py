"""Memorial relations remain complete without duplicating their predicate."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from checks.interlinear import check

ROOT = Path(__file__).resolve().parents[1]
STEPHEN = "proprium.sancti-stephani-protomartyris-secreta"
CATHEDRA = "proprium.cathedra-sancti-petri-collecta"
OFFERTORY = "proprium.commemoratio-omnium-fidelium-defunctorum-missa-i-offertorium"
GROUPS = [
    ("en", "ordinarium.simili-modo", "s13", 58, 59, "w059", "memory of Me"),
    ("pl", STEPHEN, "s01", 5, 7, "w006", "pamiątkę Twoich Świętych"),
    ("en", STEPHEN, "s01", 5, 7, "w006", "memory of Your Saints"),
    (
        "en",
        CATHEDRA,
        "s04",
        56,
        63,
        "w063",
        "we may experience the protection before You of him whose commemoration we celebrate",
    ),
    ("en", "proprium.corporis-christi-sequentia", "s09", 93, 95, "w095", "in remembrance of Him"),
    ("en", OFFERTORY, "s01", 61, 62, "w062", "we commemorate"),
]


def documents(language, text):
    category, name = text.split(".", 1)
    relative = f"texts/{category}/{name}.json"
    core = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    layer = json.loads((ROOT / "languages" / language / relative).read_text(encoding="utf-8"))
    return core, layer


@pytest.mark.parametrize("language,text,segment,start,end,anchor,gloss", GROUPS)
def test_complete_memorial_group(language, text, segment, start, end, anchor, gloss):
    core, layer = documents(language, text)
    ids = [f"w{number:03}" for number in range(start, end + 1)]
    groups = layer["segments"][segment].get("alignments", [])
    expected = {"words": ids, "anchor": anchor, "gloss": gloss}
    assert expected in groups
    assert all("gloss" not in layer["words"][word] for word in ids)
    assert check(core, layer) == []


@pytest.mark.parametrize("language,text,segment,start,end,anchor,gloss", GROUPS)
def test_memorial_members_cannot_be_duplicated_or_lost(
    language, text, segment, start, end, anchor, gloss
):
    core, layer = documents(language, text)
    ids = [f"w{number:03}" for number in range(start, end + 1)]
    expected = {"words": ids, "anchor": anchor, "gloss": gloss}
    assert expected in layer["segments"][segment].get("alignments", [])
    duplicate = deepcopy(layer)
    duplicate["words"][ids[0]]["gloss"] = "duplicate"
    assert any("exactly one" in error for error in check(core, duplicate))
    missing = deepcopy(layer)
    missing["segments"][segment]["alignments"].remove(expected)
    assert any("exactly one" in error for error in check(core, missing))


def test_polish_possessive_and_correlative_keep_their_government():
    _, simili = documents("pl", "ordinarium.simili-modo")
    assert [simili["words"][word]["gloss"] for word in ("w057", "w058", "w059")] == [
        "na",
        "moją",
        "pamiątkę",
    ]
    _, cathedra = documents("pl", CATHEDRA)
    assert [cathedra["words"][f"w{number:03}"]["gloss"] for number in range(55, 64)] == [
        "abyśmy",
        "czyją",
        "pamiątkę",
        "czcimy",
        "tego",
        "u",
        "Ciebie",
        "opieki",
        "doświadczali",
    ]


def test_memorial_group_preserves_its_word_explanation():
    _, simili = documents("en", "ordinarium.simili-modo")
    assert simili["words"]["w058"]["explanation"] == (
        "Latin says literally “in memory of Me”. English preserves the same construction."
    )
    assert simili["words"]["w057"]["gloss"] == "in"


@pytest.mark.parametrize(
    "language,expected",
    [("pl", ["w", "pamięci", "wiecznej"]), ("en", ["in", "remembrance", "everlasting"])],
)
def test_enduring_remembrance_is_not_a_memorial_command(language, expected):
    _, data = documents(
        language, "proprium.commemoratio-omnium-fidelium-defunctorum-missa-i-graduale"
    )
    assert [data["words"][f"w{number:03}"]["gloss"] for number in range(11, 14)] == expected


def test_commemorating_does_not_absorb_the_next_petition():
    _, data = documents("en", OFFERTORY)
    assert [data["words"][word]["gloss"] for word in ("w059", "w060", "w063")] == [
        "whom",
        "today",
        "make",
    ]
