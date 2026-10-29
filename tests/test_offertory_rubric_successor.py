"""Seven Offertory core successors are exact and reject every other byte."""

import hashlib
import json
from pathlib import Path

import pytest
from offertory_rubric_successor_fixture import (
    DATA,
    before_offertory_core_bytes,
    before_offertory_core_object,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTERED = {
    row["text"]: row["core_sha256"]
    for row in json.loads((ROOT / "tests/fixtures/main-ordo-registrations.json").read_bytes())[
        "rows"
    ]
}
TEXTS = (
    "ordinarium.deus-qui-humanae",
    "ordinarium.in-spiritu-humilitatis",
    "ordinarium.lavabo",
    "ordinarium.offerimus-tibi",
    "ordinarium.orate-fratres",
    "ordinarium.suscipe-sancta-trinitas",
    "ordinarium.suscipe-sancte-pater",
)
DIAGNOSTIC = r"^exact Offertory core successor$"


def core_path(text):
    return ROOT / ("texts/" + text.replace(".", "/", 1) + ".json")


def test_successor_names_exactly_the_seven_offertory_texts():
    assert tuple(sorted(DATA["texts"])) == TEXTS
    for text in TEXTS:
        assert DATA["texts"][text]["relative"] == core_path(text).relative_to(ROOT).as_posix()


@pytest.mark.parametrize("text", TEXTS)
def test_current_core_inverts_to_its_registered_bytes(text):
    raw = core_path(text).read_bytes()
    comparison = before_offertory_core_bytes(text, raw)
    assert comparison != raw
    assert hashlib.sha256(comparison).hexdigest() == REGISTERED[text]
    assert core_path(text).read_bytes() == raw, "the actual source is never rewritten"


def test_twelve_rubrics_cite_the_printed_missal():
    cited = {}
    for text in TEXTS:
        doc = json.loads(core_path(text).read_bytes())
        analysis = doc["editorial"]["segments"]
        for segment in doc["segments"]:
            if segment["type"] == "rubric":
                cited[f"{text}.{segment['id']}"] = analysis[segment["id"]]["analysis"]["sources"]
    assert len(cited) == 12
    assert set(map(tuple, cited.values())) == {("editorial", "mr")}


def test_lavabo_opens_with_the_printed_rubric():
    doc = json.loads(core_path("ordinarium.lavabo").read_bytes())
    assert doc["segments"][0] == {
        "id": "s01",
        "type": "rubric",
        "text": "Interim sacerdos lavat manus, dicens:",
    }


@pytest.mark.parametrize("fault", ("rubric-byte", "provenance", "historical", "appended"))
def test_inverse_rejects_any_other_current_bytes(fault):
    text = "ordinarium.lavabo"
    raw = core_path(text).read_bytes()
    if fault == "rubric-byte":
        changed = raw.replace(b'"Interim sacerdos lavat', b'"Interim Sacerdos lavat', 1)
    elif fault == "provenance":
        changed = raw.replace(
            b'"sources": ["editorial", "mr"]', b'"sources": ["editorial", "do", "mr"]', 1
        )
    elif fault == "historical":
        changed = before_offertory_core_bytes(text, raw)
    else:
        changed = raw + b"\n"
    assert changed != raw
    with pytest.raises(AssertionError, match=DIAGNOSTIC):
        before_offertory_core_bytes(text, changed)
    assert hashlib.sha256(before_offertory_core_bytes(text, raw)).hexdigest() == REGISTERED[text]


@pytest.mark.parametrize("text", TEXTS)
def test_current_object_inverts_to_the_parsed_predecessor(text):
    raw = core_path(text).read_bytes()
    current = json.loads(raw)
    saved = json.loads(raw)
    comparison = before_offertory_core_object(text, current)
    assert comparison == json.loads(before_offertory_core_bytes(text, raw))
    assert comparison != current and current == saved, "the actual object is never rewritten"


@pytest.mark.parametrize("fault", ("sources", "rubric", "word"))
def test_object_inverse_rejects_any_other_current_object(fault):
    text = "ordinarium.suscipe-sancta-trinitas"
    current = json.loads(core_path(text).read_bytes())
    if fault == "sources":
        current["editorial"]["segments"]["s01"]["analysis"]["sources"] = ["editorial", "do"]
    elif fault == "rubric":
        current["segments"][0]["text"] += " "
    else:
        current["segments"][1]["words"][0]["form"] = "Suscipe,"
    with pytest.raises(AssertionError, match=DIAGNOSTIC):
        before_offertory_core_object(text, current)


def test_unrelated_text_passes_through_untouched():
    raw = core_path("ordinarium.confiteor").read_bytes()
    assert before_offertory_core_bytes("ordinarium.confiteor", raw) is raw
    value = json.loads(raw)
    assert before_offertory_core_object("ordinarium.confiteor", value) is value
