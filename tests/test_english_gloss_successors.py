"""Successors of the English gloss register repair adjudicated after the independent challenge:
the Dom XX Gradual's subject group and the Holy Name litany's parallel future."""

import json
from pathlib import Path

from checks import interlinear

ROOT = Path(__file__).resolve().parents[1]
GRADUALE = "proprium.dominica-xx-post-pentecosten-graduale"
LITANY = "litaniae.sanctissimi-nominis-iesu"


def layer(text):
    category, name = text.split(".", 1)
    return json.loads(
        (ROOT / "languages/en/texts" / category / f"{name}.json").read_text(encoding="utf-8")
    )


def core(text):
    category, name = text.split(".", 1)
    return json.loads((ROOT / "texts" / category / f"{name}.json").read_text(encoding="utf-8"))


def test_aperis_tu_is_one_subject_group_in_the_dom_xx_gradual():
    doc = layer(GRADUALE)
    groups = [a for a in doc["segments"]["s01"]["alignments"] if a["words"] == ["w015", "w016"]]
    assert len(groups) == 1 and groups[0] == {
        "words": ["w015", "w016"],
        "anchor": "w015",
        "gloss": "You open",
    }
    assert "gloss" not in doc["words"].get("w015", {}) and "gloss" not in doc["words"].get(
        "w016", {}
    )
    assert interlinear.check(core(GRADUALE), doc) == []


def test_holy_name_promise_triad_reads_will_throughout():
    words = layer(LITANY)["words"]
    assert words["w420"]["gloss"] == "you will receive"
    assert words["w423"]["gloss"] == "you will find"
    assert words["w426"]["gloss"] == "will be opened"
