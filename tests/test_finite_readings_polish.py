"""Polish finite readings retain their patients, negation and case relations."""

from pathlib import Path

import pytest

from build_reader import store
from checks import interlinear

ROOT = Path(__file__).resolve().parents[1]
CHRISTMAS = "nativitas-domini-in-die-introitus"
BAPTIST = "nativitas-sancti-ioannis-baptistae-evangelium"
BLOOD = "pretiosissimi-sanguinis-domini-nostri-iesu-christi"
PURIFICATION = "purificatio-beatae-mariae-virginis-collecta"
HEART = "sacratissimi-cordis-iesu-evangelium"


@pytest.mark.parametrize(
    "name,segment,members,anchor,gloss",
    [
        (CHRISTMAS, "s01", [7, 8], 7, "został dany"),
        (CHRISTMAS, "s01", [55, 56], 55, "został dany"),
        (BAPTIST, "s01", [55, 56], 55, "nie ma nikogo"),
        (BAPTIST, "s01", [70, 71], 70, "żeby go nazwano"),
        (BAPTIST, "s01", [99, 100], 99, "padła"),
        (BAPTIST, "s01", [139, 140], 139, "został napełniony"),
        (BLOOD + "-communio", "s01", [3, 4], 3, "został ofiarowany"),
        (BLOOD + "-communio", "s01", [6, 7, 8], 6, "zgładzić grzechy wielu"),
        (BLOOD + "-evangelium", "s01", [53, 54], 53, "był ukrzyżowany"),
        (PURIFICATION, "s01", [21, 22], 22, "został przedstawiony"),
        (PURIFICATION, "s01", [24, 25], 24, "sprawił, abyśmy"),
        (HEART, "s02", [40, 41], 40, "był ukrzyżowany"),
    ],
)
def test_complete_polish_predicate(name, segment, members, anchor, gloss):
    core, layers = store.load(ROOT, "proprium." + name)
    layer = layers["pl"]
    assert interlinear.check(core, layer) == []
    ids = [f"w{n:03}" for n in members]
    groups = layer["segments"][segment]["alignments"]
    assert next(g for g in groups if g["words"] == ids) == {
        "words": ids,
        "anchor": f"w{anchor:03}",
        "gloss": gloss,
    }
    assert all(not layer["words"][wid].get("gloss") for wid in ids)


@pytest.mark.parametrize(
    "name,word,gloss",
    [
        (BAPTIST, "w049", "Janem"),
        (BAPTIST, "w061", "byłby zwany"),
        (BAPTIST, "w078", "to"),
        (BLOOD + "-communio", "w005", "aby"),
        (PURIFICATION, "w008", "abyś"),
        (PURIFICATION, "w026", "z oczyszczonymi"),
        (PURIFICATION, "w029", "zostali przedstawieni"),
        (HEART, "w087", "abyście"),
        (HEART, "w098", "kości"),
    ],
)
def test_polish_dependent_word_keeps_its_relation(name, word, gloss):
    _, layers = store.load(ROOT, "proprium." + name)
    layer = layers["pl"]
    assert layer["words"][word]["gloss"] == gloss
    assert word not in interlinear.alignment_by_word(layer)


def test_baptist_restored_speech_keeps_both_faculties():
    _, layers = store.load(ROOT, "proprium." + BAPTIST)
    prose = layers["pl"]["segments"]["s01"]["translation"]
    assert (
        "Otworzyły się zaś od razu jego usta i rozwiązał się jego język, "
        "i mówił, błogosławiąc Boga."
    ) in prose


def test_purification_preserves_petition_and_familiar_conclusion():
    _, layers = store.load(ROOT, "proprium." + PURIFICATION)
    layer = layers["pl"]
    prose = layer["segments"]["s01"]["translation"]
    assert "majestat, abyśmy, jak" in prose
    assert "tak i my za Twoją sprawą zostali Tobie przedstawieni" in prose
    assert prose.endswith(
        "Przez tegoż Pana naszego Jezusa Chrystusa, Syna Twojego, "
        "który z Tobą żyje i króluje w jedności Ducha Świętego, "
        "Bóg, na wieki wieków."
    )
    assert layer["segments"]["s02"]["translation"] == "Amen."


@pytest.mark.parametrize(
    "name,words,segments",
    [
        (CHRISTMAS, 69, 1),
        (BAPTIST, 156, 1),
        (BLOOD + "-communio", 16, 1),
        (BLOOD + "-evangelium", 93, 1),
        (PURIFICATION, 52, 2),
        (HEART, 111, 5),
    ],
)
def test_whole_polish_reading_keeps_one_provider_per_word(name, words, segments):
    core, layers = store.load(ROOT, "proprium." + name)
    assert len(core["segments"]) == segments
    assert sum(len(s.get("words", [])) for s in core["segments"]) == words
    assert interlinear.check(core, layers["pl"]) == []
