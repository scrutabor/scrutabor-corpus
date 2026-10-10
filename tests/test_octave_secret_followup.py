"""The shared Secret keeps one addressed reception and two coordinated requests."""

import copy
import json
from pathlib import Path

import pytest

from checks.interlinear import check

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.in-octava-nativitatis-secreta"
PATH = "texts/proprium/in-octava-nativitatis-secreta.json"
OPENING = {
    "pl": "Prosimy, Panie: przyjąwszy nasze dary i modlitwy,",
    "en": "We beseech You, Lord: having received our gifts and prayers,",
}


def material(language):
    core = json.loads((ROOT / PATH).read_text())
    layer = json.loads((ROOT / "languages" / language / PATH).read_text())
    return core, layer


def assert_construction(core, layer):
    language = layer["language"]
    assert not check(core, layer)
    groups = layer["segments"]["s01"]["alignments"]
    assert groups[0] == {
        "words": [f"w{i:03}" for i in range(1, 7)],
        "anchor": "w003",
        "gloss": OPENING[language],
    }
    if language == "pl":
        assert groups[1] == {
            "words": [f"w{i:03}" for i in range(7, 12)],
            "anchor": "w010",
            "gloss": "oczyść nas niebieskimi misteriami",
        }
    else:
        assert layer["words"]["w007"]["gloss"] == "both"
        assert groups[1] == {
            "words": [f"w{i:03}" for i in range(8, 12)],
            "anchor": "w010",
            "gloss": "cleanse us by the heavenly mysteries",
        }
    assert layer["words"]["w012"]["gloss"] == ("i" if language == "pl" else "and")
    assert layer["words"]["w013"]["gloss"] == ("łaskawie" if language == "pl" else "mercifully")
    assert layer["words"]["w014"]["gloss"] == ("wysłuchaj" if language == "pl" else "hear")
    words = {w["id"]: w for s in core["segments"] for w in s["words"]}
    assert [words[f"w{i:03}"]["lemma"] for i in range(1, 15)] == [
        "munus",
        "noster",
        "quaeso",
        "dominus",
        "prex",
        "suscipio",
        "et",
        "caelestis",
        "nos",
        "mundo",
        "mysterium",
        "et",
        "clementer",
        "exaudio",
    ]
    assert words["w006"]["morph"] == {
        "pos": "verb",
        "case": "abl",
        "gender": "n",
        "number": "pl",
        "tense": "perf",
        "voice": "pass",
        "mood": "part",
        "conj": 3,
    }
    assert words["w010"]["morph"]["mood"] == "imp"
    assert words["w014"]["morph"]["mood"] == "imp"


@pytest.mark.parametrize("language", ["pl", "en"])
def test_complete_opening_and_two_requests(language):
    assert_construction(*material(language))


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize(
    "damage",
    [
        "opening",
        "gifts",
        "prayers",
        "petition",
        "vocative",
        "you",
        "reception",
        "cause",
        "member",
        "order",
        "anchor",
        "duplicate",
        "command",
        "means",
        "coordination",
        "passive",
        "lemma",
    ],
)
def test_construction_rejects_local_corruption(language, damage):
    core, layer = material(language)
    assert_construction(core, layer)
    bad_core, bad_layer = copy.deepcopy(core), copy.deepcopy(layer)
    groups = bad_layer["segments"]["s01"]["alignments"]
    if damage == "opening":
        groups[0]["gloss"] = "Our gifts we beseech Lord and prayers having been received"
    elif damage in {
        "gifts",
        "prayers",
        "petition",
        "vocative",
        "you",
        "reception",
        "cause",
    }:
        replacements = {
            "pl": {
                "gifts": ("dary", ""),
                "prayers": ("i modlitwy", ""),
                "petition": ("Prosimy, ", ""),
                "vocative": ("Panie: ", ""),
                "you": ("Panie", "my"),
                "reception": ("przyjąwszy", "przyjmij"),
                "cause": ("przyjąwszy", "ponieważ przyjąłeś"),
            },
            "en": {
                "gifts": ("gifts", ""),
                "prayers": ("and prayers", ""),
                "petition": ("We beseech You, ", ""),
                "vocative": ("Lord: ", ""),
                "you": ("You, ", ""),
                "reception": ("having received", "receive"),
                "cause": ("having received", "because You received"),
            },
        }
        old, new = replacements[language][damage]
        assert old in groups[0]["gloss"]
        groups[0]["gloss"] = groups[0]["gloss"].replace(old, new)
    elif damage == "member":
        groups[0]["words"].pop()
    elif damage == "order":
        groups[0]["words"].reverse()
    elif damage == "anchor":
        groups[0]["anchor"] = "w006"
    elif damage == "duplicate":
        bad_layer["words"]["w001"]["gloss"] = "gift"
    elif damage == "command":
        groups[1]["gloss"] = "receive our gifts"
    elif damage == "means":
        groups[1]["gloss"] = "cleanse the heavenly mysteries"
    elif damage == "coordination":
        bad_layer["words"]["w012"]["gloss"] = "because"
    elif damage == "passive":
        bad_core["segments"][0]["words"][5]["morph"]["voice"] = "act"
    else:
        bad_core["segments"][0]["words"][4]["lemma"] = "munus"
    with pytest.raises(AssertionError):
        assert_construction(bad_core, bad_layer)
    assert_construction(core, layer)


def test_both_formulary_consumers_share_the_same_secret():
    consumers = []
    for path in sorted((ROOT / "formularies").rglob("*.json")):
        for component in json.loads(path.read_text()).get("components", []):
            if component.get("text") == TEXT:
                consumers.append((str(path.relative_to(ROOT)), component))
    assert consumers == [
        (
            "formularies/temporale/dominica-in-septuagesima.json",
            {
                "key": "secreta",
                "role": "secreta",
                "text": TEXT,
                "relation": "reference",
            },
        ),
        (
            "formularies/temporale/in-octava-nativitatis.json",
            {
                "key": "secreta",
                "role": "secreta",
                "text": TEXT,
                "relation": "proper",
            },
        ),
    ]
