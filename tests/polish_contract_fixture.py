"""Finite Polish wording successors, inverted on historical comparison copies only."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from canon_consecration_successor_fixture import (
    before_canon_bytes,
    before_canon_layer,
    before_canon_object,
)

from build_reader.bibliography_bindings import digest

DATA = json.loads((Path(__file__).parent / "fixtures/polish-contract-2026-10-29.json").read_bytes())
LAYERS = {rule["relative"]: rule for rule in DATA["layers"]}
TEXTS = {rule["text"]: rule for rule in DATA["layers"]}
LEDGER = DATA["ledger"]


def require(condition, diagnostic):
    if not condition:
        raise AssertionError(diagnostic)


def parent_at(value, pointer):
    for key in pointer[:-1]:
        value = value[key]
    return value, pointer[-1]


def before_polish_contract_layer(layer, diagnostic="Polish contract layer"):
    """Bind the complete current Polish layer, then restore the declared fields on a copy."""
    rule = TEXTS.get(layer.get("text")) if layer.get("language") == "pl" else None
    if rule is None:
        return layer
    layer = before_canon_layer(layer, diagnostic)
    require(digest(layer) == rule["after_canonical_sha256"], diagnostic)
    result = deepcopy(layer)
    for operation in reversed(rule["operations"]):
        parent, key = parent_at(result, operation["pointer"])
        require(key in parent and parent[key] == operation["after"], diagnostic)
        parent[key] = deepcopy(operation["before"])
    require(digest(result) == rule["before_canonical_sha256"], diagnostic)
    return result


def before_polish_contract_ledger(relative, value, diagnostic="Polish contract ledger"):
    """Bind the complete current Polish ledger, then restore the declared rows on a copy."""
    if relative != LEDGER["relative"]:
        return value
    value = before_canon_object(relative, value, diagnostic)
    require(digest(value) == LEDGER["after_canonical_sha256"], diagnostic)
    result = deepcopy(value)
    for change in LEDGER["rows"]:
        before, after = change["before"], change["after"]
        require(before.keys() == after.keys(), diagnostic)
        require(before["site"] == after["site"] == change["site"], diagnostic)
        require(
            {key for key in before if before[key] != after[key]} == {"target_sha256"}, diagnostic
        )
        indices = [i for i, row in enumerate(value["sites"]) if row["site"] == change["site"]]
        require(indices == [change["index"]], diagnostic)
        require(value["sites"][change["index"]] == after, diagnostic)
        result["sites"][change["index"]] = deepcopy(before)
    require(digest(result) == LEDGER["before_canonical_sha256"], diagnostic)
    return result


def before_polish_contract_bytes(relative, raw, diagnostic="exact Polish contract bytes"):
    """Require every current byte, then invert only the declared fragments of one file."""
    if relative == LEDGER["relative"]:
        raw = before_canon_bytes(relative, raw, diagnostic)
        require(hashlib.sha256(raw).hexdigest() == LEDGER["after_raw_sha256"], diagnostic)
        result = raw
        for change in reversed(LEDGER["rows"]):
            after, before = change["after_raw"].encode(), change["before_raw"].encode()
            require(json.loads(after) == change["after"], diagnostic)
            require(json.loads(before) == change["before"], diagnostic)
            require(result.count(after) == 1, diagnostic)
            result = result.replace(after, before, 1)
        require(hashlib.sha256(result).hexdigest() == LEDGER["before_raw_sha256"], diagnostic)
        return result
    rule = LAYERS.get(relative)
    if rule is None:
        return raw
    raw = before_canon_bytes(relative, raw, diagnostic)
    require(hashlib.sha256(raw).hexdigest() == rule["after_raw_sha256"], diagnostic)
    result = raw
    for operation in reversed(rule["raw_operations"]):
        after, before = operation["after"].encode(), operation["before"].encode()
        require(result.count(after) == 1, diagnostic)
        result = result.replace(after, before, 1)
    require(hashlib.sha256(result).hexdigest() == rule["before_raw_sha256"], diagnostic)
    return result


def current_polish_contract_value(text, pointer, recorded):
    """Map one historical expected value to its declared successor, else keep it."""
    rule = TEXTS.get(text)
    if rule is None:
        return recorded
    for operation in rule["operations"]:
        if operation["pointer"] == list(pointer) and operation["before"] == recorded:
            return operation["after"]
    return recorded
