"""Identical response words do not establish an identical sung context."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from checks.participation import check_doc, derive

CORPUS = Path(__file__).resolve().parent.parent


def load(slug):
    return json.loads((CORPUS / "texts/ordinarium" / f"{slug}.json").read_text())


def segment(doc, sid):
    return next(s for s in doc["segments"] if s["id"] == sid)


@pytest.mark.parametrize(
    ("slug", "sid"), [("misereatur", "s03"), ("misereatur", "s06"), ("deus-tu-conversus", "s09")]
)
def test_spoken_preparations_keep_the_low_mass_response_without_sung_degree(slug, sid):
    doc = load(slug)
    seg = segment(doc, sid)
    before = deepcopy(seg)
    assert (seg["speaker"], seg["voice"]) == ("minister", "clara")
    expected = {"lecta": {"gradus": 1, "source": "DMS 31 a"}}
    assert derive(doc, seg) == expected
    assert seg["participation"] == expected
    assert seg == before
    assert check_doc(doc)[0] == []
    bad = deepcopy(doc)
    segment(bad, sid)["participation"]["cantu"] = {"gradus": 1, "source": "DMS 25 a"}
    errors, _ = check_doc(bad)
    assert len(errors) == 1 and errors[0].startswith(f"{sid}: participation ")
    # The same genuine formula in the source-bound Preface dialogue remains sung.
    dialogue = load("praefatio-dialogus")
    answer = segment(dialogue, "s03")
    assert derive(dialogue, answer)["cantu"] == {"gradus": 1, "source": "DMS 25 a"}


def test_sanctus_and_paschal_ritual_are_not_rewritten_by_preparation_exclusion():
    sanctus = load("sanctus")
    for seg in sanctus["segments"]:
        if seg["type"] == "verse":
            assert derive(sanctus, seg)["cantu"] == {
                "gradus": 2,
                "source": "DMS 25 b",
                "performance": {"speaker": "schola", "voice": "cantus", "source": "DMS 25 b; 26"},
            }
    dismissal = load("ite-missa-est-paschale")
    for seg in dismissal["segments"]:
        assert "speaker" not in seg and "voice" not in seg
        assert derive(dismissal, seg) == {}
    assert segment(dismissal, "s05")["delivery"] == {"cantu": {"voice": "cantus"}}
