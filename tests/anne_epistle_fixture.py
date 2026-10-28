"""Exact Anne targets and guarded historical comparison copies."""

import json
from copy import deepcopy
from pathlib import Path

from anne_documentary_fixture import target_core

from checks.translation_provenance import canonical_hash, source_payload

FIXTURE = json.loads(
    (Path(__file__).with_name("fixtures") / "anne-epistle-constructions.json").read_text()
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
        key = int(parts[-1]) if isinstance(parent, list) else parts[-1]
        after, before = operation["after"], operation["before"]
        present = key < len(parent) if isinstance(parent, list) else key in parent
        require(present == after["exists"], "Anne successor field presence")
        if after["exists"]:
            require(parent[key] == after["value"], "Anne successor field value")
        if before["exists"]:
            parent[key] = deepcopy(before["value"])
        else:
            del parent[key]
    return restored


def predecessor_core(core):
    if core["id"] != TEXT:
        return deepcopy(core)
    core = target_core(core, "Anne contextual core")
    require(canonical_hash(core) == FIXTURE["core_after_sha256"], "Anne contextual core")
    restored = inverse(core, FIXTURE["core_operations"])
    require(canonical_hash(restored) == FIXTURE["core_before_sha256"], "Anne predecessor core")
    return restored


def predecessor_layer(layer, message="Anne complete target layer"):
    if layer["text"] != TEXT:
        return deepcopy(layer)
    language = layer["language"]
    require(layer == FIXTURE["after_layers"][language], message)
    restored = inverse(layer, FIXTURE["layer_operations"][language])
    require(
        canonical_hash(restored) == FIXTURE["before_layer_sha256"][language],
        "Anne predecessor target layer",
    )
    return restored


def current_row(core, layer, row):
    if core["id"] != TEXT:
        return row
    require(row == FIXTURE["ledger"][layer["language"]]["after"], "Anne complete provenance row")
    require(
        row["source_sha256"] == canonical_hash(source_payload(core["segments"][0])),
        "Anne current source hash",
    )
    require(
        row["target_sha256"] == canonical_hash(layer["segments"]["s01"]["translation"]),
        "Anne current target hash",
    )
    return row


def predecessor_row(row):
    if row["text"] != TEXT:
        return deepcopy(row)
    expected = FIXTURE["ledger"][row["language"]]
    require(row == expected["after"], "Anne complete provenance row")
    return deepcopy(expected["before"])


def predecessor_rows(core, layer, rows):
    return [predecessor_row(current_row(core, layer, row)) for row in rows]


def opening_tuple(row):
    language, text, segment, members, anchor, gloss, forms, wrong = row
    return (language, text, segment, tuple(members), anchor, gloss, tuple(forms), tuple(wrong))


def opening_case(row, core, layer):
    if row[0] != "en" or row[1] != TEXT:
        return row
    require(row == opening_tuple(FIXTURE["opening_before"]), "Anne first-opening predecessor")
    predecessor_core(core)
    predecessor_layer(layer)
    return opening_tuple(FIXTURE["opening_after"])
