"""Exact comparison-copy inverse of five later contextual target successors."""

import json
from copy import deepcopy
from pathlib import Path

from lateran_epistle_fixture import before_lateran_targets
from lateran_epistle_source_fixture import DATA as LATERAN_SOURCE
from lateran_epistle_source_fixture import before_lateran_core

from checks.translation_provenance import canonical_hash

DATA = json.loads(
    (Path(__file__).parent / "fixtures/negative-government-contexts.json").read_text()
)


def predecessor_core(core):
    """Only the named complete-current source method has a historical inverse."""
    if core["id"] == LATERAN_SOURCE["text"]:
        return before_lateran_core(core)
    return deepcopy(core)


def predecessor_layer(layer, message="complete current government layer"):
    case = next(
        (
            r
            for r in DATA["layers"]
            if (r["text"], r["language"])
            == (layer.get("text"), layer.get("language", layer.get("lang")))
        ),
        None,
    )
    comparison = before_lateran_targets(layer, message)
    if case is None:
        return comparison
    assert canonical_hash(comparison) == case["after_sha256"], message
    for change in reversed(case["changes"]):
        parts = change["pointer"].strip("/").split("/")
        obj = comparison
        for key in parts[:-1]:
            obj = obj[key]
        assert obj[parts[-1]] == change["after"], message
        obj[parts[-1]] = deepcopy(change["before"])
    assert canonical_hash(comparison) == case["before_sha256"], message
    return comparison


def predecessor_rows(rows, message="complete current government provenance"):
    comparison = deepcopy(rows)
    change = DATA["provenance"]
    matching = [row for row in comparison if row["site"] == change["after"]["site"]]
    if not matching:
        return comparison
    assert len(matching) == 1 and matching[0] == change["after"], message
    matching[0]["target_sha256"] = change["before"]["target_sha256"]
    assert matching[0] == change["before"], message
    return comparison
