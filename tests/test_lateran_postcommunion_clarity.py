"""The Lateran purpose clause remains explicit without a clause-wide caption."""

import copy
import json
from pathlib import Path

import pytest

CORPUS = Path(__file__).resolve().parent.parent
PATH = "texts/proprium/dedicatio-archibasilicae-sanctissimi-salvatoris-postcommunio.json"
PURPOSE = "aby Twój Kościół wraz z powiększaniem swojej przestrzeni wzrastał także duchowo."
CAPTIONS = [
    (["w019", "w020"], "w019", "Twojemu Kościołowi"),
    (["w021", "w022", "w023"], "w022", "powiększa przestrzeń materialną"),
    (["w024", "w025", "w026"], "w025", "wzrastało duchowo"),
]


def subject():
    core = json.loads((CORPUS / PATH).read_text(encoding="utf-8"))
    layer = json.loads((CORPUS / "languages/pl" / PATH).read_text(encoding="utf-8"))
    return core, layer


def assert_clarity(core, layer):
    words = {word["id"]: word for segment in core["segments"] for word in segment["words"]}
    assert words["w019"]["morph"]["case"] == words["w020"]["morph"]["case"] == "dat"
    assert words["w021"]["head"] == "w023"
    assert words["w024"]["head"] == "w026"
    segment = layer["segments"]["s01"]
    assert PURPOSE in segment["translation"]
    groups = segment["alignments"]
    assert [(group["words"], group["anchor"], group["gloss"]) for group in groups] == CAPTIONS
    assert len({word for group in groups for word in group["words"]}) == 8
    note = layer["words"]["w019"]["explanation"]
    assert "choć te same formy mogą być dopełniaczem określającym przestrzenie" in note
    assert "celownikiem" in note
    assert "quod" in note and "próficit" in note and "amplificétur" in note


def test_actual_lateran_clause_and_small_captions_remain_consistent():
    assert_clarity(*subject())


@pytest.mark.parametrize(
    "mutation",
    ["old-prose", "old-caption", "nine-word", "physical", "anchor", "alternative", "head", "case"],
)
def test_scoped_clarity_fixture_rejects_each_regression(mutation):
    core, layer = copy.deepcopy(subject())
    segment = layer["segments"]["s01"]
    if mutation == "old-prose":
        segment["translation"] = segment["translation"].replace(
            PURPOSE,
            "aby to, co Twojemu Kościołowi powiększa przestrzeń, pomnażało się duchowym wzrostem.",
        )
    elif mutation == "old-caption":
        segment["alignments"][2]["gloss"] = "pomnażało się duchowym wzrostem"
    elif mutation == "nine-word":
        segment["alignments"] = [
            {
                "words": [f"w{number:03}" for number in range(18, 27)],
                "anchor": "w025",
                "gloss": "wzrost materialny i duchowy",
            }
        ]
    elif mutation == "physical":
        segment["alignments"][1]["gloss"] = "powiększa przestrzeń"
    elif mutation == "anchor":
        segment["alignments"][2]["anchor"] = "w024"
    elif mutation == "alternative":
        layer["words"]["w019"]["explanation"] = "Możliwy jest wyłącznie celownik."
    else:
        words = {word["id"]: word for row in core["segments"] for word in row["words"]}
        if mutation == "head":
            words["w021"]["head"] = "w026"
        else:
            words["w019"]["morph"]["case"] = "nom"
    with pytest.raises(AssertionError):
        assert_clarity(core, layer)
