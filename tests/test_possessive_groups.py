"""Shared possessives remain distinct from another noun's direct modifier."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.layers import enrich_layer
from checks.interlinear import check as check_interlinear
from checks.lint import lint_gloss

ROOT = Path(__file__).resolve().parents[1]


def subject():
    text = {
        "id": "proprium.test",
        "segments": [
            {
                "id": "s01",
                "type": "verse",
                "words": [
                    {
                        "id": "w001",
                        "form": "fáciem",
                        "lemma": "facies",
                        "morph": {"pos": "noun"},
                    },
                    {
                        "id": "w002",
                        "form": "tuam",
                        "lemma": "tuus",
                        "morph": {"pos": "adj"},
                        "head": "w001",
                    },
                    {
                        "id": "w003",
                        "form": "sonet",
                        "lemma": "sono",
                        "morph": {"pos": "verb"},
                    },
                    {
                        "id": "w004",
                        "form": "vox",
                        "lemma": "vox",
                        "morph": {"pos": "noun"},
                    },
                    {
                        "id": "w005",
                        "form": "tua",
                        "lemma": "tuus",
                        "morph": {"pos": "adj"},
                        "head": "w004",
                    },
                ],
            }
        ],
    }
    layer = {
        "lang": "en",
        "words": {
            "w001": {"gloss": "face"},
            "w002": {"gloss": "your"},
            "w003": {},
            "w004": {},
            "w005": {},
        },
        "segments": {
            "s01": {
                "translation": "Show me your face; let your voice sound.",
                "alignments": [
                    {
                        "words": ["w003", "w004", "w005"],
                        "anchor": "w003",
                        "gloss": "let your voice sound",
                    }
                ],
            }
        },
    }
    return text, layer


def absorption(text, layer):
    return [error for error in lint_gloss(layer, text) if "absorbs the possessive" in error]


def test_actual_visitation_keeps_both_explicit_possessives():
    slug = "visitatio-beatae-mariae-virginis-epistola"
    text = json.loads((ROOT / "texts/proprium" / f"{slug}.json").read_bytes())
    layer = json.loads((ROOT / "languages/en/texts/proprium" / f"{slug}.json").read_bytes())
    assert layer["words"]["w093"]["gloss"] == "your"
    group = next(g for g in layer["segments"]["s01"]["alignments"] if g["anchor"] == "w094")
    assert group["words"] == ["w094", "w095", "w096"]
    assert group["gloss"] == "let your voice sound"
    assert check_interlinear(text, layer) == []
    assert lint_gloss(enrich_layer(text, layer), text) == []


@pytest.mark.parametrize(
    "lemma,possessive",
    [
        ("meus", "my"),
        ("tuus", "your"),
        ("suus", "his"),
        ("noster", "our"),
        ("vester", "your"),
    ],
)
@pytest.mark.parametrize("reverse", [False, True])
def test_distinct_noun_heads_license_two_possessives(lemma, possessive, reverse):
    text, layer = subject()
    words = text["segments"][0]["words"]
    words[1]["lemma"] = words[4]["lemma"] = lemma
    layer["words"]["w002"]["gloss"] = possessive
    group = layer["segments"]["s01"]["alignments"][0]
    group["gloss"] = f"let {possessive} voice sound"
    if reverse:
        text["segments"][0]["words"] = words[2:] + words[:2]
        # Keep the direct modifier adjacent to the group's last anchor.
        text["segments"][0]["words"][3:] = [words[1], words[0]]
        group["anchor"] = "w005"
    assert check_interlinear(text, layer) == []
    assert absorption(text, layer) == []


@pytest.mark.parametrize(
    "index,field,value",
    [
        (1, "head", None),
        (4, "head", None),
        (1, "head", "w004"),
        (4, "head", "w001"),
        (1, "head", "absent"),
        (4, "head", "absent"),
        (1, "head", "w003"),
        (4, "head", "w005"),
        (1, "lemma", "fidelis"),
        (4, "lemma", "fidelis"),
        (1, "lemma", "meus"),
        (4, "lemma", "meus"),
        (1, "morph", {"pos": "pron", "case": "gen"}),
        (4, "morph", {"pos": "pron", "case": "acc"}),
        (0, "morph", {"pos": "adj"}),
        (3, "morph", {"pos": "adj"}),
    ],
)
def test_unknown_or_conflicting_ownership_does_not_suppress_absorption(index, field, value):
    text, layer = subject()
    text["segments"][0]["words"][index][field] = value
    assert absorption(text, layer)


def test_direct_glosses_do_not_borrow_an_unrelated_group():
    text, layer = subject()
    layer["segments"]["s01"]["alignments"] = []
    layer["words"].update(
        w003={"gloss": "let your voice sound"},
        w004={"gloss": "voice"},
        w005={"gloss": "your"},
    )
    assert check_interlinear(text, layer) == []
    assert absorption(text, layer)


def test_malformed_double_provider_still_fails_the_interlinear_gate():
    text, layer = subject()
    layer["words"]["w003"]["gloss"] = "let your voice sound"
    assert any("exactly one" in error for error in check_interlinear(text, layer))


def test_losing_the_group_possessive_is_not_an_ownership_exception():
    text, layer = subject()
    layer["segments"]["s01"]["alignments"][0]["words"] = ["w003", "w004"]
    layer["words"]["w005"]["gloss"] = "your"
    assert check_interlinear(text, layer) == []
    assert absorption(text, layer)


def test_polish_uses_the_same_explicit_ownership_rule():
    text, layer = subject()
    layer["lang"] = "pl"
    layer["words"]["w001"]["gloss"] = "oblicze"
    layer["words"]["w002"]["gloss"] = "twoje"
    layer["segments"]["s01"]["translation"] = "Ukaż mi twoje oblicze; niech brzmi twój głos."
    layer["segments"]["s01"]["alignments"][0]["gloss"] = "twoje wołanie"
    assert absorption(text, layer) == []
    changed = deepcopy(text)
    changed["segments"][0]["words"][4]["head"] = "w001"
    assert absorption(changed, layer)
