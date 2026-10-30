"""Bibliography uses of the divided Canon verses address both halves of their wording.

Qui pridie s02 and s13, Quam oblationem s05 and s09 and Simili modo s15 and s06
were one verse each; the words did not change, only the segment boundary did.
Each of the nine uses that quotes the undivided wording has a record addressed
to the new segment, identical but for its id and segment and without the legacy
citation pointer of the earlier segment, so the reader shows one source for both
halves. The new ledger rows stay unclassified working sites.
"""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from split_segment_uses_successor_fixture import (
    DATA,
    FILES,
    before_split_uses_bytes,
    before_split_uses_object,
)

from build_reader import store

ROOT = Path(__file__).resolve().parents[1]
DIVISIONS = {
    "ordinarium.qui-pridie": ("s02", "s13"),
    "ordinarium.quam-oblationem": ("s05", "s09"),
    "ordinarium.simili-modo": ("s06", "s15"),
}
PUBLISHED = {"RETAIN", "RETAIN_WITH_CORRECTION"}


def current(relative):
    return json.loads((ROOT / relative).read_bytes())


def by_id(value):
    return {use["id"]: use for use in value["uses"]}


def test_nine_records_extend_nine_uses_in_two_languages():
    assert len(DATA["added"]) == len({row["row"]["id"] for row in DATA["added"]}) == 9
    assert sorted(FILES) == ["languages/en/bibliography.json", "languages/pl/bibliography.json"]
    assert sum(row["file"].startswith("languages/en/") for row in DATA["added"]) == 6
    for row in DATA["added"]:
        text = row["row"]["address"]["text"]
        assert row["row"]["address"]["segment"] == DIVISIONS[text][1]


@pytest.mark.parametrize("row", DATA["added"], ids=lambda row: row["row"]["id"])
def test_each_new_segment_record_is_its_parent_at_the_new_segment(row):
    uses = current(row["file"])["uses"]
    matches = [use for use in uses if use["id"] == row["row"]["id"]]
    parents = [use for use in uses if use["id"] == row["parent"]]
    assert matches == [row["row"]] and len(parents) == 1
    parent = parents[0]
    text = parent["address"]["text"]
    kept, new = DIVISIONS[text]
    assert parent["address"] == {"kind": "segment", "text": text, "segment": kept}
    expected = deepcopy(parent)
    expected.pop("legacy_refs", None)
    expected["id"] = row["row"]["id"]
    expected["address"]["segment"] = new
    assert row["row"] == expected
    assert list(row["row"]) == [key for key in parent if key != "legacy_refs"]


@pytest.mark.parametrize("text", sorted(DIVISIONS))
def test_the_new_segment_is_the_divided_half_and_stays_unclassified(text):
    kept, new = DIVISIONS[text]
    core, layers = store.load(ROOT, text)
    order = [segment["id"] for segment in core["segments"]]
    segments = {segment["id"]: segment for segment in core["segments"]}
    first, last = sorted((order.index(kept), order.index(new)))
    assert segments[kept]["type"] == segments[new]["type"] == "verse"
    assert [segments[s]["type"] for s in order[first + 1 : last]] == ["rubric"]
    for language in ("en", "pl"):
        assert layers[language]["segments"][new]["translation"]
        ledger = current(f"languages/{language}/translation-provenance.json")["sites"]
        rows = [row for row in ledger if row["site"] == f"{text}.{new}.{language}"]
        assert len(rows) == 1
        assert (rows[0]["origin"], rows[0]["review"]) == ("working-unsettled", "working")


def test_qui_pridie_quotes_read_across_both_halves():
    _core, layers = store.load(ROOT, "ordinarium.qui-pridie")
    for row in DATA["added"]:
        if row["row"]["address"]["text"] != "ordinarium.qui-pridie":
            continue
        language = row["file"].split("/")[1]
        segments = layers[language]["segments"]
        joined = segments["s02"]["translation"] + " " + segments["s13"]["translation"]
        claim = row["row"]["claim"]
        quoted = claim.split("„", 1)[1].removesuffix("”") if language == "pl" else claim
        assert quoted == joined


@pytest.mark.parametrize("relative", sorted(FILES))
def test_inverse_removes_exactly_the_new_records(relative):
    actual = current(relative)
    saved = deepcopy(actual)
    previous = before_split_uses_object(relative, actual)
    assert actual == saved and previous is not actual
    added = {row["row"]["id"] for row in DATA["added"] if row["file"] == relative}
    assert [use for use in actual["uses"] if use["id"] not in added] == previous["uses"]
    assert list(previous) == list(actual)
    assert before_split_uses_object(relative, previous) is previous
    raw = (ROOT / relative).read_bytes()
    assert json.loads(before_split_uses_bytes(relative, raw)) == previous
    assert before_split_uses_bytes(relative, raw + b" ") == raw + b" "


@pytest.mark.parametrize("fault", ["changed", "segment"])
def test_a_damaged_record_reaches_the_older_oracle(fault):
    relative = "languages/en/bibliography.json"
    actual = current(relative)
    row = next(row for row in DATA["added"] if row["file"] == relative)
    index = next(i for i, use in enumerate(actual["uses"]) if use["id"] == row["row"]["id"])
    if fault == "changed":
        actual["uses"][index]["claim"] += " Changed."
    else:
        actual["uses"][index]["address"]["segment"] = "s02"
    previous = before_split_uses_object(relative, actual)
    assert row["row"]["id"] in by_id(previous)
    assert by_id(previous)[row["row"]["id"]] == actual["uses"][index]


def test_the_reader_shows_one_source_for_both_halves(reader_out):
    for row in DATA["added"]:
        if row["row"]["decision"] not in PUBLISHED:
            continue
        language = row["file"].split("/")[1]
        category, slug = row["row"]["address"]["text"].split(".", 1)
        path = reader_out / f"languages/{language}/bibliography/texts/{category}/{slug}.json"
        groups = json.loads(path.read_text(encoding="utf-8"))["source_groups"]
        holding = [
            group
            for group in groups
            if row["parent"] in {entry["id"] for entry in group["entries"]}
        ]
        assert len(holding) == 1
        entries = {entry["id"]: entry for entry in holding[0]["entries"]}
        assert entries[row["row"]["id"]]["address"] == {
            "kind": "segment",
            "segment": row["row"]["address"]["segment"],
        }
        assert entries[row["row"]["id"]]["claim"] == entries[row["parent"]]["claim"]
