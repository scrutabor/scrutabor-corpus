"""Exact expected-side inverse; never supplies a native source subject."""

import json
from copy import deepcopy
from pathlib import Path

DATA = json.loads((Path(__file__).parent / "fixtures/thomas-simon-chant-sources.json").read_bytes())
ROWS = DATA["rows"]


def before_chant_registry(registry):
    historical = deepcopy(registry)
    for row in ROWS:
        identity = row["binding_id"]
        assert historical["bindings"].get(identity) == row["binding"], (
            "exact two-chant registry successor"
        )
        del historical["bindings"][identity]
    return historical


def before_chant_graph(graph):
    historical = deepcopy(graph)
    for row in ROWS:
        for collection, field in (
            ("uses", "use"),
            ("witnesses", "witness"),
            ("collations", "collation"),
        ):
            change = row[field]
            matches = [
                item for item in historical[collection] if item["id"] == change["after"]["id"]
            ]
            assert len(matches) == 1 and matches[0] == change["after"], (
                "exact two-chant graph successor"
            )
            matches[0].clear()
            matches[0].update(deepcopy(change["before"]))
    return historical
