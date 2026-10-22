"""The adjudicated successors of the English mereri repairs: the coordinated genitive of the
Joachim Postcommunion and the ablative-of-means group of the Queenship Collect."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from checks import interlinear

ROOT = Path(__file__).resolve().parents[1]
IOACHIM_PC = "proprium.sancti-ioachim-confessoris-postcommunio"
REGINA = "proprium.beata-maria-virgo-regina-collecta"
GROUP = (("w014", "w015", "w016"), "w015", "fortified by her protection")
PREDECESSOR = {"w014": "her", "w015": "safe", "w016": "protection"}


def layer(text):
    category, name = text.split(".", 1)
    return json.loads(
        (ROOT / "languages/en/texts" / category / f"{name}.json").read_text(encoding="utf-8")
    )


def core(text):
    category, name = text.split(".", 1)
    return json.loads((ROOT / "texts" / category / f"{name}.json").read_text(encoding="utf-8"))


def test_joachim_coordinated_genitives_both_disclose_their_relation():
    words = layer(IOACHIM_PC)["words"]
    assert words["w025"]["gloss"] == "of Your" and words["w026"]["gloss"] == "grace"
    assert words["w030"]["gloss"] == "of eternal" and words["w031"]["gloss"] == "glory"


def test_regina_means_group_replaces_the_keep_her_safe_reading():
    doc = layer(REGINA)
    words, anchor, gloss = GROUP
    groups = [a for a in doc["segments"]["s01"]["alignments"] if tuple(a["words"]) == words]
    assert len(groups) == 1 and groups[0]["anchor"] == anchor and groups[0]["gloss"] == gloss
    assert all("gloss" not in doc["words"].get(word, {}) for word in words)
    assert doc["words"]["w013"]["gloss"] == "keep"


@pytest.mark.parametrize("text", [IOACHIM_PC, REGINA])
def test_successor_layers_pass_the_interlinear_check(text):
    assert interlinear.check(core(text), layer(text)) == []


def test_each_predecessor_is_rejected_on_a_copy():
    joachim = deepcopy(layer(IOACHIM_PC))
    joachim["words"]["w025"]["gloss"] = "Your"
    assert joachim["words"]["w025"]["gloss"] != layer(IOACHIM_PC)["words"]["w025"]["gloss"]
    regina = deepcopy(layer(REGINA))
    words, _anchor, _gloss = GROUP
    regina["segments"]["s01"]["alignments"] = [
        a for a in regina["segments"]["s01"]["alignments"] if tuple(a["words"]) != words
    ]
    for word, gloss in PREDECESSOR.items():
        regina["words"][word] = {"gloss": gloss}
    assert interlinear.check(core(REGINA), regina) == []
    assert regina["segments"]["s01"]["alignments"] != layer(REGINA)["segments"]["s01"]["alignments"]
