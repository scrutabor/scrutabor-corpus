"""Exact English Easter-night transitions; retain the earlier protection."""

import json
from copy import deepcopy
from pathlib import Path

DATA = json.loads(Path(__file__).with_suffix(".json").read_text())
TARGET = DATA["target_sha256"]
SACRIFICE = [f"w{i:03d}" for i in range(21, 27)]
ALTERNATIVES = {
    "for Christ, our Passover, has been sacrificed",
    "for Christ, our Pasch, has been sacrificed",
    "when Christ, our Passover, has been sacrificed",
}


def restore_vigil_preface(layer):
    """Validate every named postimage before reversing only named fields.

    Unexpected metadata survives the inverse and therefore the original
    whole-layer baseline still rejects it. Arrays are compared completely,
    including every member, anchor, gloss and order. Only the earlier valid
    sacrifice alternatives vary, and they survive reversal unchanged.
    """
    value = deepcopy(layer)
    assert value["text"] == DATA["text"]
    for row in DATA["transitions"]:
        parts = row["path"].split("/")[1:]
        parent = value
        for part in parts[:-1]:
            parent = parent[part.replace("~1", "/").replace("~0", "~")]
        key = parts[-1]
        assert (key in parent) == row["after_present"]
        before, after = deepcopy(row["before"]), deepcopy(row["after"])
        if row["path"] == "/segments/s01/alignments":
            actual = parent[key]
            chosen = [g for g in actual if g["words"] == SACRIFICE]
            assert len(chosen) == 1 and chosen[0]["gloss"] in ALTERNATIVES
            for groups in (before, after):
                group = next(g for g in groups if g["words"] == SACRIFICE)
                group["gloss"] = chosen[0]["gloss"]
        if row["after_present"]:
            assert parent[key] == after
        if row["before_present"]:
            parent[key] = before
        else:
            del parent[key]
    return value


def current_prose():
    return next(r["after"] for r in DATA["transitions"] if r["path"].endswith("/translation"))
