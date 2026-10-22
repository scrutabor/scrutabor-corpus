"""Expected-side successors of the sung Preface delivery, and its exact inverse.

Every verse of the 24 Preface bodies carries the celebrant's sung-Mass
override. The source identity of each verse, the selected Latin/ritual
subject of each text and the graph records that store that subject's digest
moved with it, and nothing else did. Historical expectations elsewhere keep
the values they were written with: these helpers advance only an EXPECTED
value whose before-value is exactly the recorded one, and reverse only the
exact recorded overrides of a current document. They never normalize an
observation.
"""

import json
from copy import deepcopy
from pathlib import Path

DATA = json.loads(
    (Path(__file__).parent / "fixtures/preface-delivery-source-successors.json").read_text(
        encoding="utf-8"
    )
)


def current_source_hash(text, segment, historical):
    """The current source identity of a Preface verse whose historical one is given."""
    if text not in DATA["source"]:
        return historical
    assert segment in DATA["source"][text], "Preface source segment identity"
    change = DATA["source"][text][segment]
    assert historical == change["before"], "historical Preface source hash"
    return change["after"]


def current_expected_row(row):
    """Advance a historical EXPECTED ledger row; every other field stays as written."""
    result = deepcopy(row)
    if "source_sha256" not in row:
        return result
    text, segment, _language = row["site"].rsplit(".", 2)
    assert row.get("text", text) == text and row.get("segment", segment) == segment, (
        "Preface ledger row identity"
    )
    result["source_sha256"] = current_source_hash(text, segment, row["source_sha256"])
    return result


def _expected_hash(table, identity, historical):
    change = DATA[table].get(identity)
    if change is None:
        return historical
    assert historical == change["before"], "historical Preface " + table + " hash"
    return change["after"]


def current_selected_hash(text, historical):
    """The current digest of a Preface's selected Latin/ritual subject."""
    return _expected_hash("selected", text, historical)


def current_graph_hash(text, historical):
    """The current digest of a Preface's graph uses, witnesses and collations."""
    return _expected_hash("graph_sets", text, historical)


def current_record_hash(identifier, historical):
    """The current digest of a Preface collation record without its apparatus hash."""
    return _expected_hash("collation_records", identifier, historical)


def current_witness_hash(identifier, historical):
    """The current digest of a Preface witness subject."""
    return _expected_hash("witness_subjects", identifier, historical)


def without_preface_delivery(core):
    """Reverse ONLY the exact sung overrides of a Preface; keep every other field and order."""
    result = deepcopy(core)
    text = result["id"]
    if text not in DATA["source"]:
        return result
    verses = [seg for seg in result["segments"] if seg["type"] == "verse"]
    assert [seg["id"] for seg in verses] == list(DATA["source"][text]), (
        "current Preface inverse topology"
    )
    for seg in verses:
        assert seg.get("delivery") == DATA["source"][text][seg["id"]]["delivery"], (
            "current Preface delivery inverse"
        )
        del seg["delivery"]
    return result
