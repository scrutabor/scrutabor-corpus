"""The words are the servant's; the divine acts have God as their subject."""

from pathlib import Path

import pytest

from build_reader import store
from checks import interlinear

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.sancti-ioseph-sponsi-beatae-mariae-virginis-epistola"


@pytest.mark.parametrize(
    ("language", "possessive", "deed", "prose", "name"),
    [
        (
            "en",
            "his words",
            "He brought the portents to an end",
            "at his words God brought the portents to an end.",
            "Moses",
        ),
        (
            "pl",
            "jego słowa",
            "położył kres groźnym znakom",
            "na jego słowa Bóg położył kres groźnym znakom.",
            "Mojżesza",
        ),
    ],
)
def test_moses_words_and_the_divine_act_have_distinct_subjects(
    language, possessive, deed, prose, name
):
    core = store.core(ROOT, TEXT)
    words = core["segments"][0]["words"]
    assert [w["form"] for w in words[22:27]] == ["in", "verbis", "suis", "monstra", "placávit"]
    layer = store.raw_layer(ROOT, language, TEXT)
    segment = layer["segments"]["s01"]
    assert prose in segment["translation"] and name not in segment["translation"]
    assert name in layer["words"]["w025"]["explanation"]
    groups = {tuple(group["words"]): group["gloss"] for group in segment["alignments"]}
    assert groups["w024", "w025"] == possessive
    assert groups["w026", "w027"] == deed
    assert core["localization"]["explanations"]["w025"] == {}
    assert interlinear.check(core, layer) == []
