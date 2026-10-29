"""Six Pater noster to Agnus Dei core successors are exact and reject every other byte."""

import hashlib
import json
from pathlib import Path

import pytest
from pater_agnus_successor_fixture import (
    DATA,
    DIAGNOSTIC,
    before_pater_agnus_core_bytes,
    before_pater_agnus_core_object,
)
from requiem_successor_fixture import before_ordinary_agnus_core_bytes

ROOT = Path(__file__).resolve().parents[1]
REGISTERED = {
    row["text"]: row["core_sha256"]
    for row in json.loads((ROOT / "tests/fixtures/main-ordo-registrations.json").read_bytes())[
        "rows"
    ]
}
TEXTS = (
    "orationes.pater-noster",
    "ordinarium.agnus-dei",
    "ordinarium.haec-commixtio",
    "ordinarium.libera-nos",
    "ordinarium.pater-noster",
    "ordinarium.pax-domini",
)
RUBRICS = {
    "ordinarium.pater-noster": ("s01", "s04", "s13"),
    "ordinarium.libera-nos": ("s01", "s03", "s05", "s07", "s09", "s11"),
    "ordinarium.pax-domini": ("s01",),
    "ordinarium.haec-commixtio": ("s01",),
    "ordinarium.agnus-dei": ("s01", "s05"),
}
RETAINED = (
    "The approved Benziger printing's punctuation is retained. "
    "The difference marks phrasing and does not change the words."
)
RETAINED_SITES = {
    "ordinarium.pater-noster": ("w001", "w016", "w019", "w022", "w028", "w037"),
    "ordinarium.libera-nos": ("w009", "w040"),
}
PATTERN = rf"^{DIAGNOSTIC}$"


def core_path(text):
    return ROOT / ("texts/" + text.replace(".", "/", 1) + ".json")


def core_tokens(text):
    doc = json.loads(core_path(text).read_bytes())
    return [
        (word["id"], word.get("pre", "") + word["form"] + word.get("post", ""))
        for segment in doc["segments"]
        for word in segment.get("words", [])
    ]


def printed_tokens(text):
    lines = (ROOT / "witnesses" / text / "mr.txt").read_text(encoding="utf-8").splitlines()
    return " ".join(line for line in lines if not line.startswith("#")).split()


def test_successor_names_exactly_the_six_texts():
    assert tuple(sorted(DATA["texts"])) == TEXTS
    for text in TEXTS:
        assert DATA["texts"][text]["relative"] == core_path(text).relative_to(ROOT).as_posix()


@pytest.mark.parametrize("text", TEXTS)
def test_current_core_inverts_to_its_registered_bytes(text):
    raw = core_path(text).read_bytes()
    comparison = before_pater_agnus_core_bytes(text, raw)
    assert comparison != raw
    # The ordinary Agnus registration predates its sung-performance adjunct.
    comparison = before_ordinary_agnus_core_bytes(text, comparison)
    assert hashlib.sha256(comparison).hexdigest() == REGISTERED[text]
    assert core_path(text).read_bytes() == raw, "the actual source is never rewritten"


@pytest.mark.parametrize("text", TEXTS)
def test_successor_leaves_the_latin_and_ritual_subject_unchanged(text):
    raw = core_path(text).read_bytes()
    current = json.loads(raw)
    predecessor = json.loads(before_pater_agnus_core_bytes(text, raw))
    assert current["segments"] == predecessor["segments"]
    assert {k: v for k, v in current.items() if k != "editorial"} == {
        k: v for k, v in predecessor.items() if k != "editorial"
    }


def test_thirteen_rubrics_cite_the_printed_missal():
    cited = {}
    for text in TEXTS:
        doc = json.loads(core_path(text).read_bytes())
        analysis = doc["editorial"].get("segments", {})
        for segment in doc["segments"]:
            if segment["type"] == "rubric":
                cited[f"{text}.{segment['id']}"] = analysis[segment["id"]]["analysis"]["sources"]
    assert sorted(cited) == sorted(f"{t}.{s}" for t, ids in RUBRICS.items() for s in ids)
    assert len(cited) == 13
    assert set(map(tuple, cited.values())) == {("editorial", "mr")}


@pytest.mark.parametrize("text", sorted(RETAINED_SITES))
def test_retained_punctuation_matches_the_printed_page(text):
    apparatus = json.loads((ROOT / "witnesses" / text / "apparatus.json").read_bytes())
    ours = core_tokens(text)
    printed = printed_tokens(text)
    assert len(ours) == len(printed)
    position = {wid: index for index, (wid, _) in enumerate(ours)}
    seen = set()
    for entry in apparatus["adjudicated"]:
        if entry["at"] in RETAINED_SITES[text]:
            index = position[entry["at"]]
            assert entry["class"] == "punctuation"
            assert entry["ruling"] == RETAINED
            assert entry["ours"] == ours[index][1] == printed[index]
            seen.add(entry["at"])
    assert seen == set(RETAINED_SITES[text])


def test_mass_pater_rulings_do_not_cite_the_devotional_text():
    apparatus = json.loads((ROOT / "witnesses/ordinarium.pater-noster/apparatus.json").read_bytes())
    assert not any("orationes.pater-noster" in e["ruling"] for e in apparatus["adjudicated"])


def test_libera_apposition_ruling_describes_the_page():
    text = "ordinarium.libera-nos"
    apparatus = json.loads((ROOT / "witnesses" / text / "apparatus.json").read_bytes())
    ours = core_tokens(text)
    printed = printed_tokens(text)
    index = [wid for wid, _ in ours].index("w061")
    (entry,) = [e for e in apparatus["adjudicated"] if e["at"] == "w061"]
    assert entry["ours"] == ours[index][1] == printed[index] == "Christum"
    assert "prints the comma" not in entry["ruling"]


@pytest.mark.parametrize("fault", ("rubric-byte", "provenance", "historical", "appended"))
def test_inverse_rejects_any_other_current_bytes(fault):
    text = "ordinarium.agnus-dei"
    raw = core_path(text).read_bytes()
    if fault == "rubric-byte":
        changed = raw.replace(b'"In Missis defunctorum', b'"In missis defunctorum', 1)
    elif fault == "provenance":
        changed = raw.replace(
            b'"sources": ["editorial", "mr"]', b'"sources": ["editorial", "do", "mr"]', 1
        )
    elif fault == "historical":
        changed = before_pater_agnus_core_bytes(text, raw)
    else:
        changed = raw + b"\n"
    assert changed != raw
    with pytest.raises(AssertionError, match=PATTERN):
        before_pater_agnus_core_bytes(text, changed)
    comparison = before_ordinary_agnus_core_bytes(text, before_pater_agnus_core_bytes(text, raw))
    assert hashlib.sha256(comparison).hexdigest() == REGISTERED[text]


@pytest.mark.parametrize("text", TEXTS)
def test_current_object_inverts_to_the_parsed_predecessor(text):
    raw = core_path(text).read_bytes()
    current = json.loads(raw)
    saved = json.loads(raw)
    comparison = before_pater_agnus_core_object(text, current)
    assert comparison == json.loads(before_pater_agnus_core_bytes(text, raw))
    assert comparison != current and current == saved, "the actual object is never rewritten"


@pytest.mark.parametrize("fault", ("sources", "rubric", "word"))
def test_object_inverse_rejects_any_other_current_object(fault):
    text = "ordinarium.pax-domini"
    current = json.loads(core_path(text).read_bytes())
    if fault == "sources":
        current["editorial"]["segments"]["s01"]["analysis"]["sources"] = ["editorial", "do"]
    elif fault == "rubric":
        current["segments"][0]["text"] += " "
    else:
        current["segments"][1]["words"][0]["form"] = "Pax,"
    with pytest.raises(AssertionError, match=PATTERN):
        before_pater_agnus_core_object(text, current)


def test_unrelated_text_passes_through_untouched():
    raw = core_path("ordinarium.confiteor").read_bytes()
    assert before_pater_agnus_core_bytes("ordinarium.confiteor", raw) is raw
    value = json.loads(raw)
    assert before_pater_agnus_core_object("ordinarium.confiteor", value) is value
