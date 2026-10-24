"""Expected-side successors of the sung Gospel delivery, its exact inverse, and their
composition with the sung Preface overlay.

Every verse of the 101 Gospel bodies other than the solemn Passion carries the
celebrant's sung-Mass override. The source identity of each verse, the selected
Latin/ritual subject of each text and the graph records that store that subject's
digest moved with it, and nothing else did. Historical expectations elsewhere keep
the values they were written with: these helpers advance only an EXPECTED value whose
before-value is exactly the recorded one, and reverse only the exact recorded
overrides of a current document. They never normalize an observation.

The `current_sung_*` and `without_sung_delivery` helpers apply the Preface overlay and
then the Gospel overlay. A text belongs to at most one of them, so each historical
value is advanced by the overlay that recorded it and passes the other unchanged.
"""

import json
from copy import deepcopy
from pathlib import Path

import preface_delivery_fixture as preface

DATA = json.loads(
    (Path(__file__).parent / "fixtures/gospel-delivery-source-successors.json").read_text(
        encoding="utf-8"
    )
)


def current_gospel_source_hash(text, segment, historical):
    """The current source identity of a Gospel verse whose historical one is given."""
    if text not in DATA["source"]:
        return historical
    assert segment in DATA["source"][text], "Gospel source segment identity"
    change = DATA["source"][text][segment]
    assert historical == change["before"], "historical Gospel source hash"
    return change["after"]


def current_gospel_expected_row(row):
    """Advance a historical EXPECTED ledger row; every other field stays as written."""
    result = deepcopy(row)
    if "source_sha256" not in row:
        return result
    text, segment, _language = row["site"].rsplit(".", 2)
    assert row.get("text", text) == text and row.get("segment", segment) == segment, (
        "Gospel ledger row identity"
    )
    result["source_sha256"] = current_gospel_source_hash(text, segment, row["source_sha256"])
    return result


def _expected_hash(table, identity, historical):
    change = DATA[table].get(identity)
    if change is None:
        return historical
    assert historical == change["before"], "historical Gospel " + table + " hash"
    return change["after"]


def current_gospel_selected_hash(text, historical):
    """The current digest of a Gospel's selected Latin/ritual subject."""
    return _expected_hash("selected", text, historical)


def current_gospel_graph_hash(text, historical):
    """The current digest of a Gospel's graph uses, witnesses and collations."""
    return _expected_hash("graph_sets", text, historical)


def current_gospel_record_hash(identifier, historical):
    """The current digest of a Gospel collation record without its apparatus hash."""
    return _expected_hash("collation_records", identifier, historical)


def current_gospel_witness_hash(identifier, historical):
    """The current digest of a Gospel witness subject."""
    return _expected_hash("witness_subjects", identifier, historical)


def without_gospel_delivery(core):
    """Reverse ONLY the exact sung overrides of a Gospel; keep every other field and order."""
    result = deepcopy(core)
    text = result["id"]
    if text not in DATA["source"]:
        return result
    verses = [seg for seg in result["segments"] if seg["type"] == "verse"]
    assert [seg["id"] for seg in verses] == list(DATA["source"][text]), (
        "current Gospel inverse topology"
    )
    for seg in verses:
        assert seg.get("delivery") == DATA["source"][text][seg["id"]]["delivery"], (
            "current Gospel delivery inverse"
        )
        del seg["delivery"]
    return result


def current_sung_source_hash(text, segment, historical):
    """A historical verse source identity advanced by whichever sung overlay recorded it."""
    return current_gospel_source_hash(
        text, segment, preface.current_source_hash(text, segment, historical)
    )


def current_sung_expected_row(row):
    """A historical EXPECTED ledger row advanced by whichever sung overlay recorded it."""
    return current_gospel_expected_row(preface.current_expected_row(row))


def current_sung_selected_hash(text, historical):
    """A historical selected-subject digest advanced by whichever sung overlay recorded it."""
    return current_gospel_selected_hash(text, preface.current_selected_hash(text, historical))


def current_sung_record_hash(identifier, historical):
    """A historical collation-record digest advanced by whichever sung overlay recorded it."""
    return current_gospel_record_hash(
        identifier, preface.current_record_hash(identifier, historical)
    )


def without_sung_delivery(core):
    """Reverse only the exact recorded sung overrides of a Preface or a Gospel."""
    return without_gospel_delivery(preface.without_preface_delivery(core))
