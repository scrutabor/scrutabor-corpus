"""Protect contextual subjects and the recorded deponent-voice convention.

These are known-reading regressions, not a general Latin disambiguator.
The three checked lexical paradigms do not classify other deponents,
semi-deponents, gerunds or gerundives.
"""

import json
from pathlib import Path

import pytest

from checks.collate import load_witness

CORPUS = Path(__file__).resolve().parents[1]


def tokens(slug):
    core = json.loads((CORPUS / "texts/proprium" / f"{slug}.json").read_text())
    return {w["id"]: w for s in core["segments"] for w in s.get("words", [])}


def test_known_deponent_present_participles_keep_the_lexical_voice():
    subjects = []
    for path in sorted((CORPUS / "texts").glob("*/*.json")):
        core = json.loads(path.read_text())
        for segment in core["segments"]:
            for word in segment.get("words", []):
                morph = word["morph"]
                if (
                    word["lemma"] in {"largior", "loquor", "convescor"}
                    and morph.get("mood") == "part"
                    and morph.get("tense") == "pres"
                ):
                    subjects.append((core["id"], word["id"], morph["voice"]))
    assert len(subjects) >= 17  # Includes ten previously correct controls.
    assert not [row for row in subjects if row[2] != "dep"]


@pytest.mark.parametrize("identifier", ["w019", "w042", "w045", "w050"])
def test_ascension_participles_describe_jesus(identifier):
    word = tokens("ascensio-domini-epistola")[identifier]
    assert word.get("head") == "w011"
    assert not word.get("substantive")
    assert tuple(word["morph"][k] for k in ("case", "number", "gender")) == (
        "nom",
        "sg",
        "m",
    )


def test_ascension_retains_the_printed_multis_and_declares_the_digital_variant():
    words = tokens("ascensio-domini-epistola")
    assert words["w036"]["morph"]["governs"] == "abl"
    assert words["w036"]["head"] == "w038"
    assert words["w037"]["form"] == "multis"
    assert words["w037"]["head"] == "w038"
    assert tuple(words["w037"]["morph"][k] for k in ("case", "number", "gender")) == (
        "abl",
        "pl",
        "n",
    )
    directory = CORPUS / "witnesses/proprium.ascensio-domini-epistola"
    _, printed = load_witness(directory / "mr.txt")
    _, digital = load_witness(directory / "do.txt")
    assert "in multis arguméntis" in printed
    assert "in multas arguméntis" in digital
    apparatus = json.loads((directory / "apparatus.json").read_text())
    entry = next(item for item in apparatus["adjudicated"] if item["at"] == "w037")
    assert entry["ours"] == "multis"
    assert entry["witnesses"] == {"do": "multas"}
    assert entry["class"] == "substantive"


def test_spiritual_gifts_preserves_subjects_and_content_conjunction():
    words = tokens("dominica-x-post-pentecosten-epistola")
    assert words["w005"]["morph"]["case"] == "nom"
    assert words["w017"]["lemma"] == "quod"
    assert words["w017"]["morph"] == {"pos": "conj"}
    assert words["w022"]["head"] == "w018"  # nemo speaks, not quod.
    assert words["w115"]["morph"]["case"] == "nom"
    assert words["w116"]["head"] == "w115"  # Spiritus distributes.
    for identifier in ("w022", "w116"):
        assert not words[identifier].get("substantive")
        assert tuple(words[identifier]["morph"][k] for k in ("case", "number", "gender")) == (
            "nom",
            "sg",
            "m",
        )


def test_octave_alleluia_speaks_about_god_rather_than_addressing_him():
    words = tokens("in-octava-nativitatis-alleluia")
    assert words["w005"]["morph"]["case"] == "nom"
    for identifier in ("w006", "w013"):
        assert words[identifier]["head"] == "w005"
        assert not words[identifier].get("substantive")
        assert words[identifier]["morph"]["case"] == "nom"


def test_genuine_vocative_and_gerund_remain_distinct():
    assert tokens("dominica-ii-passionis-evangelium")["w059"]["morph"]["case"] == "voc"
    gerund = tokens("dominica-resurrectionis-collecta")["w017"]["morph"]
    assert (gerund["mood"], gerund["voice"]) == ("ger", "act")
