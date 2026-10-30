"""Exact Quam wording and note metadata on historical comparison copies only."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from canon_consecration_successor_fixture import before_canon_bytes, before_canon_object
from perceptio_purpose_successor_fixture import before_perceptio_bytes, before_perceptio_object

from build_reader.bibliography_bindings import digest

DATA = json.loads(
    (Path(__file__).parent / "fixtures/quam-rationabilem-successor.json").read_bytes()
)


def require(condition, diagnostic):
    if not condition:
        raise AssertionError(diagnostic)


def before_quam_object(relative, value, diagnostic="Quam current comparison"):
    if relative not in DATA["objects"]:
        return value
    value = before_canon_object(relative, value, diagnostic)
    value = before_perceptio_object(relative, value, diagnostic)
    rule = DATA["objects"][relative]
    require(digest(value) == rule["after_canonical_sha256"], diagnostic)
    result = deepcopy(value)
    for operation in reversed(rule["operations"]):
        parent = result
        for key in operation["pointer"][:-1]:
            parent = parent[key]
        key = operation["pointer"][-1]
        exists = 0 <= key < len(parent) if isinstance(parent, list) else key in parent
        require(exists == operation["after_exists"], diagnostic)
        if exists:
            require(parent[key] == operation["after"], diagnostic)
        if operation["before_exists"]:
            parent[key] = deepcopy(operation["before"])
        else:
            del parent[key]
    require(digest(result) == rule["before_canonical_sha256"], diagnostic)
    return result


def before_quam_ledger(relative, value, diagnostic="Quam current ledger"):
    if relative != DATA["ledger_relative"]:
        return value
    return before_quam_object(relative, value, diagnostic)


def before_quam_bytes(relative, raw, diagnostic="exact Quam comparison bytes"):
    if relative not in DATA["objects"]:
        return raw
    raw = before_canon_bytes(relative, raw, diagnostic)
    raw = before_perceptio_bytes(relative, raw, diagnostic)
    rule = DATA["objects"][relative]
    require(hashlib.sha256(raw).hexdigest() == rule["after_raw_sha256"], diagnostic)
    result = raw
    for operation in reversed(rule["raw_operations"]):
        before, after = operation["before"].encode(), operation["after"].encode()
        require(result.count(after) == 1, diagnostic)
        result = result.replace(after, before, 1)
    require(hashlib.sha256(result).hexdigest() == rule["before_raw_sha256"], diagnostic)
    return result


def before_quam_core_bytes(text, raw, diagnostic="exact Quam core metadata"):
    if text != DATA["text"]:
        return raw
    return before_quam_bytes(DATA["core_relative"], raw, diagnostic)
