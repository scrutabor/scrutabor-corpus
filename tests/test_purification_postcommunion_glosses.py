"""Contextual postcommunion constructions and their separate word providers."""

from pathlib import Path

import pytest

from build_reader import store
from checks import interlinear

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.purificatio-beatae-mariae-virginis-postcommunio"


@pytest.mark.parametrize(
    "language,words,anchor,gloss",
    [
        ("pl", ["w010", "w011", "w012"], "w012", "ochrony naszego odnowienia"),
        ("pl", ["w023", "w024"], "w024", "uczynił"),
        ("en", ["w010", "w011"], "w010", "our restoration’s"),
        ("en", ["w023", "w024"], "w024", "You may make"),
        ("en", ["w003", "w004"], "w003", "our God"),
        ("en", ["w028", "w029"], "w028", "our Lord"),
        ("en", ["w030", "w031"], "w030", "Jesus Christ"),
        ("en", ["w032", "w033"], "w032", "Your Son"),
        ("en", ["w034", "w035", "w036", "w037", "w038"], "w036", "who lives and reigns with You"),
        ("en", ["w044", "w045", "w046", "w047"], "w046", "forever and ever"),
    ],
)
def test_minimal_construction(language, words, anchor, gloss):
    layer = store.raw_layer(ROOT, language, TEXT)
    matches = [
        a for a in layer["segments"]["s01"].get("alignments", []) if set(a["words"]) & set(words)
    ]
    assert matches == [{"words": words, "anchor": anchor, "gloss": gloss}]
    assert all("gloss" not in layer["words"].get(w, {}) for w in words)


@pytest.mark.parametrize(
    "word,gloss",
    [
        ("w006", "the most holy"),
        ("w012", "safeguard"),
        ("w013", "You have bestowed"),
        ("w020", "now"),
        ("w022", "a remedy"),
        ("w026", "in the future"),
    ],
)
def test_contextual_english_realization(word, gloss):
    layer = store.raw_layer(ROOT, "en", TEXT)
    assert layer["words"][word]["gloss"] == gloss
    assert word not in interlinear.alignment_by_word(layer)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_every_word_has_one_provider(language):
    core = store.core(ROOT, TEXT)
    layer = store.raw_layer(ROOT, language, TEXT)
    assert sum(len(s["words"]) for s in core["segments"]) == 48
    assert list(layer["words"]) == [w["id"] for s in core["segments"] for w in s["words"]]
    assert interlinear.check(core, layer) == []
    groups = layer["segments"]["s01"]["alignments"]
    assert len(groups) == (2 if language == "pl" else 9)
    assert sum(len(a["words"]) for a in groups) == (5 if language == "pl" else 23)
    assert layer["words"]["w048"]["gloss"] == "Amen"
    assert layer["segments"]["s02"]["translation"] == "Amen."
    assert not layer["segments"]["s02"].get("alignments")


def test_temporal_pair_and_beneficiary_remain_distinct():
    layer = store.raw_layer(ROOT, "en", TEXT)
    expected = {
        "w019": "both",
        "w020": "now",
        "w021": "for us",
        "w022": "a remedy",
        "w025": "and",
        "w026": "in the future",
    }
    assert {w: layer["words"][w]["gloss"] for w in expected} == expected
    assert not (set(expected) & set(interlinear.alignment_by_word(layer)))


def test_polish_government_and_separate_preposition():
    layer = store.raw_layer(ROOT, "pl", TEXT)
    assert [layer["words"][w]["gloss"] for w in ["w008", "w009", "w013"]] == [
        "których",
        "jako",
        "udzieliłeś",
    ]
    assert not ({"w008", "w009", "w013"} & set(interlinear.alignment_by_word(layer)))


@pytest.mark.parametrize(
    "language,prefix",
    [("pl", "Modlitwa po Komunii formularza"), ("en", "The postcommunion prayer of")],
)
def test_about_localization(language, prefix):
    assert store.raw_layer(ROOT, language, TEXT)["about"].startswith(prefix)
