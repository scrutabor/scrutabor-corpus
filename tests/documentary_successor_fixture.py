"""Exact additional source and language inverses on comparison copies only."""

import json
from copy import deepcopy
from pathlib import Path

from anne_documentary_fixture import (
    before_anne_graph,
    before_anne_records,
    before_anne_registry,
)
from lateran_epistle_source_fixture import before_lateran_graph, before_lateran_registry
from michael_gospel_source_fixture import before_michael_records, before_michael_registry
from rosary_gospel_source_fixture import before_rosary_graph, before_rosary_registry

from build_reader.bibliography_bindings import digest

DATA = json.loads(
    (Path(__file__).parent / "fixtures/documentary-successor-comparisons.json").read_bytes()
)


def before_additional_records(value):
    return before_michael_records(before_anne_records(value))


def before_additional_registry(value):
    return before_michael_registry(before_anne_registry(value))


def before_documentary_graph(value):
    return before_lateran_graph(
        before_rosary_graph(before_michael_records(before_anne_graph(value)))
    )


def before_documentary_registry(value):
    return before_lateran_registry(before_rosary_registry(before_additional_registry(value)))


def before_language_successors(relative, value, diagnostic="exact Joachim target successor"):
    rule = DATA["ledgers"][relative]
    assert digest(value) == rule["after_sha256"], diagnostic
    result = deepcopy(value)
    for change in rule["rows"]:
        indices = [
            i for i, row in enumerate(result["sites"]) if row["site"] == change["after"]["site"]
        ]
        assert len(indices) == 1, diagnostic
        (index,) = indices
        assert result["sites"][index] == change["after"], diagnostic
        result["sites"][index] = deepcopy(change["before"])
    assert digest(result) == rule["before_sha256"], diagnostic
    return result
