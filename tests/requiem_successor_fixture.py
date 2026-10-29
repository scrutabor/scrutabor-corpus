"""Finite Requiem successor inverses for historical comparison copies only."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from build_reader.bibliography_bindings import digest

DATA = json.loads(
    (Path(__file__).parent / "fixtures/requiem-successor-comparisons.json").read_bytes()
)


def require(condition, diagnostic):
    if not condition:
        raise AssertionError(diagnostic)


def before_requiem_ledger(relative, value, diagnostic="Requiem current ledger"):
    """Guard the complete actual frame, then undo only exact rows on a copy."""
    require(relative in DATA["ledgers"], diagnostic)
    rule = DATA["ledgers"][relative]
    require(digest(value) == rule["after_sha256"], diagnostic)
    result = deepcopy(value)
    for change in rule["changed"]:
        index = change["index_after"]
        require(index == change["index_before"], diagnostic)
        require(result["sites"][index] == change["after"], diagnostic)
        require(change["before"].keys() == change["after"].keys(), diagnostic)
        require(change["before"]["site"] == change["after"]["site"], diagnostic)
        result["sites"][index] = deepcopy(change["before"])
    for added in reversed(rule["added"]):
        index = added["index"]
        require(index == len(result["sites"]) - 1, diagnostic)
        require(result["sites"][index] == added["row"], diagnostic)
        del result["sites"][index]
    require(digest(result) == rule["before_sha256"], diagnostic)
    return result


def before_requiem_graph(value, diagnostic="exact Requiem graph additions"):
    """Remove 25 exact new records; inherited guards still check all old fields.

    This is called only at complete-graph historical comparison entries. It
    deliberately preserves unrelated mutations, so existing whole-graph guards
    retain their original diagnostics. It is never used for native validation or
    isolated witness/record objects, and does not claim an independent old-frame
    acceptance for arbitrary input.
    """
    result = deepcopy(value)
    for collection, additions in DATA["graph"].items():
        rows = result[collection]
        for added in additions:
            identity = added["row"]["id"]
            indices = [i for i, row in enumerate(rows) if row.get("id") == identity]
            require(indices == [added["index"]], diagnostic)
            require(rows[added["index"]] == added["row"], diagnostic)
        for added in reversed(additions):
            del rows[added["index"]]
    return result


def before_requiem_bytes(relative, raw, diagnostic="exact Requiem comparison bytes"):
    """Invert four declared raw expected-side inputs, preserving every other byte."""
    if relative not in DATA["raw"]:
        return raw
    rule = DATA["raw"][relative]
    require(hashlib.sha256(raw).hexdigest() == rule["after_sha256"], diagnostic)
    comparison = raw
    for operation in rule["operations"]:
        after = operation["after"].encode()
        before = operation["before"].encode()
        require(comparison.count(after) == 1, diagnostic)
        comparison = comparison.replace(after, before, 1)
    require(hashlib.sha256(comparison).hexdigest() == rule["before_sha256"], diagnostic)
    return comparison


def before_ordinary_agnus_core_bytes(text, raw, diagnostic="ordinary Agnus core successor"):
    """Undo six exact performance additions only for the historical hash comparison.

    The native caller retains raw and parses that actual current source. No
    predecessor is accepted as a current frame or passed to a native consumer.
    """
    rule = DATA["ordinary_agnus_core"]
    if text != rule["text"]:
        return raw
    require(hashlib.sha256(raw).hexdigest() == rule["after_sha256"], diagnostic)
    actual = json.loads(raw)
    require(actual["id"] == text, diagnostic)
    require(digest(actual) == rule["after_canonical_sha256"], diagnostic)
    comparison_object = deepcopy(actual)
    verses = [segment for segment in comparison_object["segments"] if segment["type"] == "verse"]
    require([segment["id"] for segment in verses] == rule["segments"], diagnostic)
    for segment in verses:
        require(segment.get("delivery") == rule["delivery"], diagnostic)
        require(
            segment["participation"]["cantu"].get("performance") == rule["performance"], diagnostic
        )
        del segment["delivery"]
        del segment["participation"]["cantu"]["performance"]
    require(digest(comparison_object) == rule["before_canonical_sha256"], diagnostic)
    comparison_raw = raw
    for operation in rule["raw_inverse_operations"]:
        after, before = operation["after"].encode(), operation["before"].encode()
        require(comparison_raw.count(after) == operation["count"], diagnostic)
        comparison_raw = comparison_raw.replace(after, before, operation["count"])
    require(hashlib.sha256(comparison_raw).hexdigest() == rule["before_sha256"], diagnostic)
    require(json.loads(comparison_raw) == comparison_object, diagnostic)
    return comparison_raw
