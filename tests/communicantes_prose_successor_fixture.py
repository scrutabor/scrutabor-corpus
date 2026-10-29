"""One exact English prose successor, reversed only on comparison copies."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from quam_rationabilem_successor_fixture import before_quam_bytes, before_quam_ledger

from build_reader.bibliography_bindings import digest

DATA = json.loads(
    (Path(__file__).parent / "fixtures/communicantes-prose-successor.json").read_bytes()
)


def require(condition, diagnostic):
    if not condition:
        raise AssertionError(diagnostic)


def before_communicantes_layer(relative, value, diagnostic="Communicantes current layer"):
    rule = DATA["layer"]
    if relative != rule["relative"]:
        return value
    require(digest(value) == rule["after_canonical_sha256"], diagnostic)
    require(value["segments"]["s01"]["translation"] == rule["after"], diagnostic)
    result = deepcopy(value)
    result["segments"]["s01"]["translation"] = rule["before"]
    require(digest(result) == rule["before_canonical_sha256"], diagnostic)
    return result


def before_communicantes_ledger(relative, value, diagnostic="Communicantes current ledger"):
    rule = DATA["ledger"]
    if relative != rule["relative"]:
        return value
    value = before_quam_ledger(relative, value, diagnostic)
    require(digest(value) == rule["after_canonical_sha256"], diagnostic)
    before, after = rule["before"], rule["after"]
    require(before.keys() == after.keys(), diagnostic)
    require({key for key in before if before[key] != after[key]} == {"target_sha256"}, diagnostic)
    indices = [i for i, row in enumerate(value["sites"]) if row["site"] == after["site"]]
    require(indices == [rule["index"]], diagnostic)
    require(value["sites"][rule["index"]] == after, diagnostic)
    result = deepcopy(value)
    result["sites"][rule["index"]] = deepcopy(before)
    require(digest(result) == rule["before_canonical_sha256"], diagnostic)
    return result


def before_communicantes_bytes(relative, raw, diagnostic="exact Communicantes comparison bytes"):
    rules = {DATA[key]["relative"]: DATA[key] for key in ("layer", "ledger")}
    if relative not in rules:
        return raw
    rule = rules[relative]
    raw = before_quam_bytes(relative, raw, diagnostic)
    require(hashlib.sha256(raw).hexdigest() == rule["after_raw_sha256"], diagnostic)
    after, before = rule["raw_after"].encode(), rule["raw_before"].encode()
    require(raw.count(after) == 1, diagnostic)
    result = raw.replace(after, before, 1)
    require(hashlib.sha256(result).hexdigest() == rule["before_raw_sha256"], diagnostic)
    return result
