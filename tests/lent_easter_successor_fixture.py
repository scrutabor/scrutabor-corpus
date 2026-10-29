"""One exact English ledger successor, reversed on historical comparison copies."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from communicantes_prose_successor_fixture import (
    before_communicantes_bytes,
    before_communicantes_ledger,
)

from build_reader.bibliography_bindings import digest

DATA = json.loads(
    (Path(__file__).parent / "fixtures/lent-easter-english-successors.json").read_bytes()
)
RULE = DATA["ledger"]


def before_lent_easter_ledger(relative, value, diagnostic="Lent/Easter current ledger"):
    """Require the complete new frame; restore one exact old row on a copy."""
    if relative != RULE["relative"]:
        return value
    value = before_communicantes_ledger(relative, value, diagnostic)
    assert digest(value) == RULE["after_canonical_sha256"], diagnostic
    before, after = RULE["before"], RULE["after"]
    assert before.keys() == after.keys(), diagnostic
    assert {key for key in before if before[key] != after[key]} == {"target_sha256"}, diagnostic
    indices = [i for i, row in enumerate(value["sites"]) if row["site"] == after["site"]]
    assert indices == [RULE["index"]], diagnostic
    assert value["sites"][RULE["index"]] == after, diagnostic
    result = deepcopy(value)
    result["sites"][RULE["index"]] = deepcopy(before)
    assert digest(result) == RULE["before_canonical_sha256"], diagnostic
    return result


def before_lent_easter_bytes(relative, raw, diagnostic="exact Lent/Easter comparison bytes"):
    """Reverse the unique target digest only after checking every actual byte."""
    if relative != RULE["relative"]:
        return raw
    raw = before_communicantes_bytes(relative, raw, diagnostic)
    assert hashlib.sha256(raw).hexdigest() == RULE["after_raw_sha256"], diagnostic
    after = RULE["after"]["target_sha256"].encode()
    before = RULE["before"]["target_sha256"].encode()
    assert raw.count(after) == 1, diagnostic
    result = raw.replace(after, before, 1)
    assert hashlib.sha256(result).hexdigest() == RULE["before_raw_sha256"], diagnostic
    return result
