"""Exact Palm tract comparison copies, after current-layer validation."""

import json
from copy import deepcopy
from pathlib import Path

from checks.translation_provenance import canonical_hash

DATA = json.loads((Path(__file__).with_name("fixtures") / "palm-tract-captions.json").read_text())
TEXT = DATA["text"]


def reviewed_palm_layer(layer):
    assert layer.get("text") == TEXT, "unchanged contextual remainder"
    assert layer.get("language") in DATA["layers"], "unchanged contextual remainder"
    case = DATA["layers"][layer["language"]]
    assert canonical_hash(layer) == case["after_sha256"], "unchanged contextual remainder"


def predecessor_palm_layer(layer):
    if layer.get("text") != TEXT:
        return deepcopy(layer)
    reviewed_palm_layer(layer)
    case = DATA["layers"][layer["language"]]
    restored = deepcopy(layer)
    for wid, change in case["word_changes"].items():
        assert restored["words"][wid] == change["after"], "unchanged contextual remainder"
        restored["words"][wid] = deepcopy(change["before"])
    assert restored["segments"]["s01"]["alignments"] == case["alignments"]
    assert restored["segments"]["s01"]["translation"] == case["translation"]
    restored["segments"]["s01"]["alignments"] = deepcopy(case["before_alignments"])
    restored["segments"]["s01"]["translation"] = case["before_translation"]
    assert canonical_hash(restored) == case["before_sha256"], "unchanged contextual remainder"
    return restored


def predecessor_palm_rows(rows, text, language):
    if text != TEXT:
        return deepcopy(rows)
    assert language in DATA["layers"], "reviewed Palm provenance row"
    case = DATA["layers"][language]
    assert rows == [case["row_after"]], "reviewed Palm provenance row"
    return [deepcopy(case["row_before"])]


def reviewed_palm_group(layer, case):
    group = case["group"]
    touching = [
        row
        for segment in layer["segments"].values()
        for row in segment.get("alignments", [])
        if set(row["words"]) & set(group["words"])
    ]
    assert touching == [group], "reviewed Palm group"
    assert all("gloss" not in layer["words"][wid] for wid in group["words"]), "reviewed Palm group"
