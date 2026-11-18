"""Exact Michael Epistle constructions and their historical comparison views."""

import json
from copy import deepcopy
from pathlib import Path

from edition_revision_fixture import before_rubric_caption_layer, current_edition_value

from checks.translation_provenance import canonical_hash

FIXTURE = json.loads(
    (Path(__file__).with_name("fixtures") / "michael-epistle-constructions.json").read_text()
)
TEXT = FIXTURE["text"]


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
        require((key in parent) == after["exists"], "Michael successor field presence")
        if after["exists"]:
            require(parent[key] == after["value"], "Michael successor field value")
        if before["exists"]:
            parent[key] = deepcopy(before["value"])
        else:
            del parent[key]
    return restored


def predecessor_core(core):
    if core["id"] != TEXT:
        return deepcopy(core)
    require(canonical_hash(core) == FIXTURE["core_after_sha256"], "Michael contextual core")
    restored = inverse(core, FIXTURE["core_operations"])
    require(canonical_hash(restored) == FIXTURE["core_before_sha256"], "Michael predecessor core")
    return restored


def predecessor_layer(layer):
    if layer["text"] != TEXT:
        return deepcopy(layer)
    language = layer["language"]
    layer = before_rubric_caption_layer(layer)
    require(layer == FIXTURE["after_layers"][language], "Michael complete target layer")
    restored = inverse(layer, FIXTURE["layer_operations"][language])
    require(restored == FIXTURE["before_layers"][language], "Michael predecessor target layer")
    return restored


def current_row(language):
    expected = FIXTURE["ledger"][language]["after"]
    before = FIXTURE["after_layers"][language]["segments"]["s01"]["translation"]
    relative = f"languages/{language}/texts/{TEXT.replace('.', '/', 1)}.json"
    after = current_edition_value(relative, ("segments", "s01", "translation"), before)
    return {**expected, "target_sha256": canonical_hash(after)}


def predecessor_row(row):
    if row["text"] != TEXT:
        return deepcopy(row)
    expected = FIXTURE["ledger"][row["language"]]
    require(
        row in (expected["after"], current_row(row["language"])), "Michael complete provenance row"
    )
    return deepcopy(expected["before"])
