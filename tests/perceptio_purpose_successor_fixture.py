"""Finite Perceptio successors, inverted only on historical comparison copies."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from english_contract_successor_fixture import (
    before_english_contract_bytes,
    before_english_contract_object,
)

from build_reader.bibliography_bindings import digest

DATA = json.loads(
    (Path(__file__).parent / "fixtures/perceptio-purpose-successor.json").read_bytes()
)


def require(condition, diagnostic):
    if not condition:
        raise AssertionError(diagnostic)


def before_perceptio_object(relative, value, diagnostic="Perceptio current comparison"):
    """Require every current field, then recover only the declared predecessor."""
    rules = {rule["relative"]: rule for rule in DATA["files"].values()}
    if relative not in rules:
        return value
    value = before_english_contract_object(relative, value, diagnostic)
    rule = rules[relative]
    require(digest(value) == rule["after_canonical_sha256"], diagnostic)
    result = deepcopy(value)
    for operation in reversed(rule["object_inverse"]):
        container = result
        for key in operation["path"][:-1]:
            container = container[key]
        key = operation["path"][-1]
        require(container[key] == operation["after"], diagnostic)
        if operation["before_exists"]:
            container[key] = deepcopy(operation["before"])
        else:
            del container[key]
    require(digest(result) == rule["before_canonical_sha256"], diagnostic)
    return result


def before_perceptio_ledger(relative, value, diagnostic="Perceptio current ledger"):
    if relative != DATA["files"]["ledger"]["relative"]:
        return value
    return before_perceptio_object(relative, value, diagnostic)


def before_perceptio_bytes(relative, raw, diagnostic="exact Perceptio comparison bytes"):
    rules = {rule["relative"]: rule for rule in DATA["files"].values()}
    if relative not in rules:
        return raw
    raw = before_english_contract_bytes(relative, raw, diagnostic)
    rule = rules[relative]
    require(hashlib.sha256(raw).hexdigest() == rule["after_raw_sha256"], diagnostic)
    result = raw
    for operation in reversed(rule["raw_inverse"]):
        after, before = operation["after"].encode(), operation["before"].encode()
        require(result.count(after) == operation["count"], diagnostic)
        result = result.replace(after, before, operation["count"])
    require(hashlib.sha256(result).hexdigest() == rule["before_raw_sha256"], diagnostic)
    require(digest(json.loads(result)) == rule["before_canonical_sha256"], diagnostic)
    return result


def before_perceptio_core_bytes(text, raw, diagnostic="exact Perceptio core metadata"):
    if text != DATA["text"]:
        return raw
    return before_perceptio_bytes(DATA["files"]["core"]["relative"], raw, diagnostic)
