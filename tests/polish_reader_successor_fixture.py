"""Finite Polish target successors for historical comparison copies only."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from build_reader.bibliography_bindings import digest

DATA = json.loads((Path(__file__).parent / "fixtures/polish-reader-successors.json").read_bytes())
RULE = DATA["ledger"]
SITES = (
    "ordinarium.praefatio-apostolorum.s04.pl",
    "proprium.dominica-i-in-quadragesima-postcommunio.s01.pl",
    "proprium.dominica-i-in-quadragesima-tractus.s01.pl",
)


def before_polish_reader_ledger(relative, value, diagnostic="Polish reader current ledger"):
    """Bind the complete actual frame, then restore exactly three old rows on a copy."""
    if relative != RULE["relative"]:
        return value
    assert digest(value) == RULE["after_canonical_sha256"], diagnostic
    assert tuple(change["after"]["site"] for change in RULE["rows"]) == SITES, diagnostic
    result = deepcopy(value)
    for change in RULE["rows"]:
        before, after = change["before"], change["after"]
        assert before.keys() == after.keys(), diagnostic
        assert before["site"] == after["site"], diagnostic
        assert {key for key in before if before[key] != after[key]} == {"target_sha256"}, diagnostic
        indices = [i for i, row in enumerate(value["sites"]) if row["site"] == after["site"]]
        assert indices == [change["index"]], diagnostic
        assert value["sites"][change["index"]] == after, diagnostic
        result["sites"][change["index"]] = deepcopy(before)
    assert digest(result) == RULE["before_canonical_sha256"], diagnostic
    return result


def before_polish_reader_bytes(relative, raw, diagnostic="exact Polish reader comparison bytes"):
    """Require every new byte, then invert only the three complete declared row blocks."""
    if relative != RULE["relative"]:
        return raw
    assert hashlib.sha256(raw).hexdigest() == RULE["after_raw_sha256"], diagnostic
    assert tuple(change["after"]["site"] for change in RULE["rows"]) == SITES, diagnostic
    result = raw
    for change in reversed(RULE["rows"]):
        after, before = change["after_raw"].encode(), change["before_raw"].encode()
        assert json.loads(after) == change["after"], diagnostic
        assert json.loads(before) == change["before"], diagnostic
        assert result.count(after) == 1, diagnostic
        result = result.replace(after, before, 1)
    assert hashlib.sha256(result).hexdigest() == RULE["before_raw_sha256"], diagnostic
    return result


def before_polish_reader_core(core, diagnostic="Polish explanation declaration"):
    """Invert only the three exact PL-only declarations on a comparison copy.

    Source fields are left intact, including unrelated faults. Callers' complete
    historical core hashes retain responsibility for the complete old frames.
    """
    rule = next((row for row in DATA["cores"] if row["text"] == core["id"]), None)
    if rule is None:
        return core
    assert core["localization"] == rule["after_localization"], diagnostic
    result = deepcopy(core)
    result["localization"] = deepcopy(rule["before_localization"])
    return result


def before_apostles_role_comparison(layer, diagnostic="Polish Apostles role comparison"):
    """Restore four admitted PL fragments, preserving every other value and fault.

    The old case-context caller already restored its older s03 comparison. Its
    unchanged complete formatted hash, after this finite s04 inverse, is the oracle.
    """
    rule = DATA["apostles_layer"]
    if layer["text"] != rule["text"] or layer["language"] != "pl":
        return layer
    result = deepcopy(layer)
    for fragment in rule["fragments"]:
        collection, key = fragment["collection"], fragment["key"]
        assert layer[collection][key] == fragment["after"], diagnostic
        result[collection][key] = deepcopy(fragment["before"])
    return result


def before_polish_reader_wording(site, row, target, diagnostic="unchanged wording"):
    """Restore only Apostles s04 on historical row/verse comparison copies."""
    rule = DATA["apostles_wording"]
    if site != rule["site"]:
        return row, target
    change = next(change for change in RULE["rows"] if change["after"]["site"] == site)
    assert row == change["after"] and target == rule["after_target"], diagnostic
    assert digest(target) == change["after"]["target_sha256"], diagnostic
    assert digest(rule["before_target"]) == change["before"]["target_sha256"], diagnostic
    return deepcopy(change["before"]), rule["before_target"]
