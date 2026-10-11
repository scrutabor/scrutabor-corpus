"""Contextual constructions in the Palm Sunday readings and prayers.

Keep the target clauses grammatical without changing the Latin analysis. A
caption belongs to its complete contiguous construction, not just its last word.
These cases preserve specific readings, not a general proof of translation quality.
"""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PA = "proprium.dominica-ii-passionis-"
GOSPEL = PA + "evangelium"
EPISTLE = "proprium.exaltatio-sanctae-crucis-epistola"


def layer(language, text):
    path = ROOT / "languages" / language / "texts" / (text.replace(".", "/", 1) + ".json")
    return json.loads(path.read_text(encoding="utf-8"))


GROUPS = [
    (
        "en",
        PA + "collecta",
        "s01",
        22,
        30,
        30,
        "we may be worthy both to learn from His patience and to share in His resurrection",
    ),
    (
        "pl",
        PA + "collecta",
        "s01",
        22,
        30,
        30,
        "byli godni zarówno czerpać naukę z Jego cierpliwości, "
        "jak i uczestniczyć w Jego zmartwychwstaniu",
    ),
    ("en", PA + "communio", "s01", 3, 7, 4, "this chalice cannot pass away"),
    ("en", GOSPEL, "s10", 120, 124, 121, "this chalice cannot pass away"),
    ("en", GOSPEL, "s19", 245, 246, 246, "they laid hands"),
    ("pl", GOSPEL, "s19", 245, 246, 246, "położyli ręce"),
    ("en", GOSPEL, "s34", 516, 517, 516, "He is deserving"),
    ("en", GOSPEL, "s51", 781, 785, 782, "whom some of the children of Israel valued"),
    (
        "pl",
        GOSPEL,
        "s51",
        781,
        785,
        782,
        "którego wycenili niektórzy spośród synów Izraela",
    ),
    ("pl", GOSPEL, "s22", 340, 342, 342, "nie pojmaliście Mnie"),
    (
        "en",
        GOSPEL,
        "s62",
        933,
        938,
        934,
        "Which of the two do you want to be released to you",
    ),
    (
        "pl",
        GOSPEL,
        "s62",
        933,
        938,
        934,
        "Którego z dwóch chcecie, aby wam wypuszczono",
    ),
    ("en", GOSPEL, "s70", 960, 962, 962, "What evil, then,"),
    ("en", GOSPEL, "s77", 1035, 1037, 1037, "they put a scarlet cloak around"),
    (
        "pl",
        EPISTLE,
        "s01",
        18,
        25,
        20,
        "nie uznał za przywłaszczenie tego, że jest równy Bogu",
    ),
    ("pl", EPISTLE, "s01", 48, 49, 48, "i to śmierci"),
    ("en", EPISTLE, "s01", 18, 21, 20, "did not regard it as robbery"),
]


@pytest.mark.parametrize("language,text,segment,first,last,anchor,caption", GROUPS)
def test_complete_constructions(language, text, segment, first, last, anchor, caption):
    doc = layer(language, text)
    ids = [f"w{number:03d}" for number in range(first, last + 1)]
    overlapping = [
        group
        for group in doc["segments"][segment].get("alignments", [])
        if set(group["words"]) & set(ids)
    ]
    assert overlapping == [{"words": ids, "anchor": f"w{anchor:03d}", "gloss": caption}]
    assert all("gloss" not in doc["words"][wid] for wid in ids)


@pytest.mark.parametrize(
    "word,caption",
    [
        ("w468", "Chrystusem"),
        ("w469", "Synem"),
        ("w1208", "Synem"),
        ("w1241", "uwierzymy"),
        ("w248", "Jezusie"),
        ("w1243", "pokłada ufność"),
    ],
)
def test_polish_contextual_government_and_tense(word, caption):
    assert layer("pl", GOSPEL)["words"][word]["gloss"] == caption


@pytest.mark.parametrize(
    "language,expected",
    [
        (
            "en",
            "we may be worthy both to learn from His patience and to share in His resurrection",
        ),
        (
            "pl",
            "abyśmy byli godni zarówno czerpać naukę z Jego cierpliwości, "
            "jak i uczestniczyć w Jego zmartwychwstaniu",
        ),
    ],
)
def test_collect_prose_has_both_petitions(language, expected):
    assert expected in layer(language, PA + "collecta")["segments"]["s01"]["translation"]


def test_polish_conditional_promise_in_prose():
    verse = layer("pl", GOSPEL)["segments"]["s82"]["translation"]
    assert "a uwierzymy Mu" in verse
    assert "a wierzymy Mu" not in verse


def test_english_conditional_keeps_its_surrounding_units():
    for text, first in [(PA + "communio", 2), (GOSPEL, 119)]:
        doc = layer("en", text)
        assert doc["words"][f"w{first:03d}"]["gloss"] == "if"
        assert doc["words"][f"w{first + 6:03d}"]["gloss"] == "unless"
        assert doc["words"][f"w{first + 7:03d}"]["gloss"] == "I drink"
        assert doc["words"][f"w{first + 8:03d}"]["gloss"] == "it"


@pytest.mark.parametrize(
    "language,segment,phrase",
    [
        ("en", "s34", "He deserves death."),
        ("en", "s51", "whom some of the children of Israel valued"),
        ("pl", "s51", "którego wycenili niektórzy spośród synów Izraela"),
        ("en", "s79", "so that the words spoken by the prophet might be fulfilled:"),
    ],
)
def test_contextual_relations_in_prose(language, segment, phrase):
    assert phrase in layer(language, GOSPEL)["segments"][segment]["translation"]
