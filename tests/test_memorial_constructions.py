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


def assert_polish_offertory_relative_reprises(core, layer):
    assert core["id"] == layer["text"] == OFFERTORY
    assert layer["language"] == "pl"
    words = {word["id"]: word for segment in core["segments"] for word in segment["words"]}
    assert words["w038"]["lemma"] == "lux"
    assert words["w070"]["lemma"] == "vita"
    assert words["w039"]["post"] == ":"
    assert words["w070"]["post"] == "."
    for word in ("w040", "w071"):
        assert words[word]["form"] == "Quam"
        assert words[word]["morph"] == {"pos": "pron", "case": "acc", "number": "sg", "gender": "f"}
    for word, expected in (
        ("w038", "światłości"),
        ("w040", "którą"),
        ("w070", "życia"),
        ("w071", "Które"),
    ):
        assert layer["words"][word]["gloss"] == expected, f"Polish Offertory reprise {word}"


def test_polish_offertory_relatives_keep_their_local_antecedents():
    core, layer = documents("pl", OFFERTORY)
    saved = deepcopy((core, layer))
    assert_polish_offertory_relative_reprises(core, layer)
    assert check(core, layer) == []
    assert (core, layer) == saved


@pytest.mark.parametrize(
    "word,wrong",
    [
        ("w038", "życia"),
        ("w040", "które"),
        ("w040", "Którą"),
        ("w070", "światłości"),
        ("w071", "którą"),
        ("w071", "które"),
    ],
    ids=[
        "first-antecedent",
        "first-neuter",
        "first-capital",
        "second-antecedent",
        "second-feminine",
        "second-lowercase",
    ],
)
def test_polish_offertory_reprise_mutation_is_rejected_and_restored(word, wrong):
    core, layer = documents("pl", OFFERTORY)
    saved = deepcopy((core, layer))
    assert_polish_offertory_relative_reprises(core, layer)
    broken = deepcopy(layer)
    previous = broken["words"][word]["gloss"]
    assert wrong != previous
    broken["words"][word]["gloss"] = wrong
    assert broken != layer
    with pytest.raises(AssertionError) as caught:
        assert_polish_offertory_relative_reprises(core, broken)
    assert str(caught.value).splitlines()[0] == f"Polish Offertory reprise {word}"
    broken["words"][word]["gloss"] = previous
    assert broken == layer
    assert_polish_offertory_relative_reprises(core, broken)
    assert check(core, broken) == []
    assert (core, layer) == saved
