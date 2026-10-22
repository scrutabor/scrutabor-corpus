"""The adjudicated successors of the Polish mereri repairs: lowercase mid-sentence relatives, the
object government of promereor, and the refined Christmas Night group and notes."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from checks import interlinear

ROOT = Path(__file__).resolve().parents[1]

GLOSSES = (
    ("proprium.exaltatio-sanctae-crucis-collecta", "w015", "którego", "Którego"),
    ("proprium.exaltatio-sanctae-crucis-secreta", "w010", "którego", "Którego"),
    ("orationes.actus-contritionis", "w017", "na kary", "kary"),
)
GROUP = (
    "proprium.nativitas-domini-in-nocte-postcommunio",
    "s01",
    ("w020", "w021", "w022", "w023", "w024"),
    "w022",
    "zasłużyli, by dojść do Jego wspólnoty",
    "byli godni dojść do Jego wspólnoty",
)
NOTES = (
    (
        "proprium.nativitas-domini-in-nocte-postcommunio",
        "w022",
        "„abyśmy zasłużyli, by dojść”",
        "„abyśmy byli godni dojść”",
    ),
    (
        "proprium.sancta-familia-postcommunio",
        "w033",
        "czyli na to, byśmy zostali przyjęci",
        "czyli abyśmy zostali przyjęci",
    ),
)


def layer(text):
    category, name = text.split(".", 1)
    return json.loads(
        (ROOT / "languages/pl/texts" / category / f"{name}.json").read_text(encoding="utf-8")
    )


def core(text):
    category, name = text.split(".", 1)
    return json.loads((ROOT / "texts" / category / f"{name}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize(("text", "word", "expected", "predecessor"), GLOSSES)
def test_successor_gloss_is_lowercase_relative_or_governed_object(
    text, word, expected, predecessor
):
    doc = layer(text)
    assert doc["words"][word]["gloss"] == expected
    assert doc["words"][word]["gloss"] != predecessor


def test_refined_christmas_night_group_avoids_the_godny_echo():
    text, segment, words, anchor, expected, predecessor = GROUP
    doc = layer(text)
    groups = [a for a in doc["segments"][segment]["alignments"] if tuple(a["words"]) == words]
    assert len(groups) == 1 and groups[0]["anchor"] == anchor
    assert groups[0]["gloss"] == expected and groups[0]["gloss"] != predecessor
    assert doc["words"]["w018"]["gloss"] == "godnym"
    assert "godni" not in groups[0]["gloss"]


@pytest.mark.parametrize(("text", "word", "fragment", "predecessor"), NOTES)
def test_refined_notes_keep_the_deponent_governor_explicit(text, word, fragment, predecessor):
    doc = layer(text)
    note = doc["words"][word]["explanation"]
    assert fragment in note and predecessor not in note
    assert core(text)["localization"]["explanations"][word] == {"languages": ["pl"]}


def test_each_successor_predecessor_is_rejected_on_a_copy():
    for text, word, _expected, predecessor in GLOSSES:
        doc = deepcopy(layer(text))
        doc["words"][word]["gloss"] = predecessor
        assert doc["words"][word]["gloss"] != layer(text)["words"][word]["gloss"]
    text, segment, words, _anchor, _expected, predecessor = GROUP
    doc = deepcopy(layer(text))
    group = next(a for a in doc["segments"][segment]["alignments"] if tuple(a["words"]) == words)
    group["gloss"] = predecessor
    original = next(
        a for a in layer(text)["segments"][segment]["alignments"] if tuple(a["words"]) == words
    )
    assert group["gloss"] != original["gloss"]


@pytest.mark.parametrize("text", sorted({row[0] for row in (*GLOSSES, NOTES[0], NOTES[1], GROUP)}))
def test_successor_layers_pass_the_interlinear_check(text):
    assert interlinear.check(core(text), layer(text)) == []
