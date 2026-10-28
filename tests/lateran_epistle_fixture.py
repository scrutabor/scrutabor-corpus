"""Exact target expectations and comparison-only predecessor for one lesson."""

import json
from copy import deepcopy
from pathlib import Path

from checks.translation_provenance import canonical_hash

DATA = json.loads(
    (Path(__file__).parent / "fixtures/lateran-epistle-targets.json").read_text(encoding="utf-8")
)
TEXT = DATA["text"]


def before_lateran_targets(layer, message="complete Lateran target layer"):
    comparison = deepcopy(layer)
    if layer.get("text") != TEXT:
        return comparison
    language = layer.get("language", layer.get("lang"))
    case = DATA["layers"][language]
    assert canonical_hash(layer) == case["after_sha256"], message
    for change in reversed(case["changes_after_negative"]):
        parts = change["pointer"].strip("/").split("/")
        parent = comparison
        for key in parts[:-1]:
            parent = parent[key]
        key = parts[-1]
        assert (key in parent) == change["after"]["exists"], message
        if key in parent:
            assert parent[key] == change["after"]["value"], message
        if change["before"]["exists"]:
            parent[key] = deepcopy(change["before"]["value"])
        else:
            del parent[key]
    assert canonical_hash(comparison) == case["negative_sha256"], message
    return comparison


def before_lateran_rows(rows, message="complete Lateran target provenance"):
    comparison = deepcopy(rows)
    expected = DATA["ledger"]["en"]
    matching = [r for r in comparison if r["site"] == expected["after"]["site"]]
    if matching:
        assert len(matching) == 1 and matching[0] == expected["after"], message
        matching[0]["target_sha256"] = expected["before"]["target_sha256"]
        assert matching[0] == expected["before"], message
    return comparison


def realization(layer, wid):
    groups = [
        g for s in layer["segments"].values() for g in s.get("alignments", []) if wid in g["words"]
    ]
    direct = layer["words"][wid].get("gloss")
    assert len(groups) <= 1 and not (groups and direct is not None), "Lateran membership"
    return {"group": groups[0]} if groups else {"direct": direct}


def assert_caption(layer, language, wid):
    expected = DATA["layers"][language]
    group = next((g for g in expected["groups"] if wid in g["words"]), None)
    wanted = {"group": group} if group else {"direct": expected["direct"][wid]}
    assert realization(layer, wid) == wanted, "Lateran literal realization"
