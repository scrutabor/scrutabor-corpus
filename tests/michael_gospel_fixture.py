"""Exact Michael Gospel constructions and their historical comparison views."""

import json
from copy import deepcopy
from pathlib import Path

from michael_gospel_source_fixture import DATA as SOURCE

from checks.translation_provenance import canonical_hash

FIXTURE = json.loads(
    (Path(__file__).with_name("fixtures") / "michael-gospel-constructions.json").read_text()
)
TEXT = FIXTURE["text"]
COMPOSED_CORE_SHA256 = "8e4c230ae41b6852538aba3b771ac388a9d1120b6c9101bf0a914d924085d333"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def inverse(value, operations):
    restored = deepcopy(value)
    for operation in reversed(operations):
        parts = operation["pointer"].split("/")[1:]
        parent = restored
        for part in parts[:-1]:
            parent = parent[int(part)] if isinstance(parent, list) else parent[part]
        key = parts[-1]
        after, before = operation["after"], operation["before"]
        require((key in parent) == after["exists"], "Gospel successor field presence")
        if after["exists"]:
            require(parent[key] == after["value"], "Gospel successor field value")
        if before["exists"]:
            parent[key] = deepcopy(before["value"])
        else:
            del parent[key]
    return restored


def predecessor_core(core):
    if core["id"] != TEXT:
        return deepcopy(core)
    require(canonical_hash(core) == COMPOSED_CORE_SHA256, "Gospel contextual core")
    comparison = deepcopy(core)
    require(
        comparison["editorial"]["source"]["method"] == SOURCE["method"]["after"],
        "Gospel contextual core",
    )
    comparison["editorial"]["source"]["method"] = SOURCE["method"]["before"]
    require(canonical_hash(comparison) == FIXTURE["core_after_sha256"], "Gospel contextual core")
    restored = inverse(comparison, FIXTURE["core_operations"])
    require(canonical_hash(restored) == FIXTURE["core_before_sha256"], "Gospel predecessor core")
    return restored


def predecessor_layer(layer):
    if layer["text"] != TEXT:
        return deepcopy(layer)
    language = layer["language"]
    require(layer == FIXTURE["after_layers"][language], "Gospel complete target layer")
    restored = inverse(layer, FIXTURE["layer_operations"][language])
    require(restored == FIXTURE["before_layers"][language], "Gospel predecessor target layer")
    return restored


def predecessor_row(row):
    if row["text"] != TEXT:
        return deepcopy(row)
    expected = FIXTURE["ledger"][row["language"]]
    require(row == expected["after"], "Gospel complete provenance row")
    return deepcopy(expected["before"])
