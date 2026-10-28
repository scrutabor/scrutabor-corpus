"""Exact comparison predecessors for the composed Marian Gospel changes.

Native and reader inputs remain current. Historical fixtures stay unchanged.
"""

import json
from copy import deepcopy
from pathlib import Path

from iste_gender_fixture import before_iste_gender, current_iste_expected_row
from rosary_gospel_source_fixture import before_rosary_core

from checks.translation_provenance import canonical_hash

FIXTURE = json.loads(
    (Path(__file__).with_name("fixtures") / "marian-gospel-constructions.json").read_text()
)
LAYERS = {(row["text"], row["language"]): row for row in FIXTURE["layers"]}
CORES = {row["text"]: row for row in FIXTURE["cores"]}
ROWS = {row["after_row"]["site"]: row for row in FIXTURE["layers"]}


def predecessor_core(core):
    case = CORES.get(core["id"])
    if case is None:
        return deepcopy(core)
    # Each named primitive guards its own actual leaf before a whole-object
    # guard fixes the complete remainder, including all three companions.
    result = before_rosary_core(before_iste_gender(core))
    assert canonical_hash(result) == case["after_sha256"], "Marian Gospel core remainder"
    assert result["localization"] == case["localization_after"]
    result["localization"] = deepcopy(case["localization_before"])
    assert canonical_hash(result) == case["before_sha256"]
    return result


def current_expected_row(row):
    case = ROWS.get(row["site"])
    if case is None:
        return current_iste_expected_row(row)
    assert row == case["before_row"], "historical Marian Gospel provenance row"
    result = current_iste_expected_row(row)
    assert result["target_sha256"] == case["before_row"]["target_sha256"]
    result["target_sha256"] = case["after_row"]["target_sha256"]
    return result


def predecessor_layer(layer):
    result = deepcopy(layer)
    case = LAYERS.get((layer["text"], layer["language"]))
    if case is None:
        return result
    assert canonical_hash(layer) == case["after_sha256"], "unchanged passive-layer remainder"
    for wid, change in case["word_changes"].items():
        assert result["words"][wid] == change["after"]
        result["words"][wid] = deepcopy(change["before"])
    assert result["segments"]["s01"]["alignments"] == case["alignments_after"]
    result["segments"]["s01"]["alignments"] = deepcopy(case["alignments_before"])
    prose = result["segments"]["s01"]["translation"]
    for change in reversed(case["prose_changes"]):
        start = change["after_start"]
        assert prose[start : start + len(change["after"])] == change["after"]
        prose = prose[:start] + change["before"] + prose[start + len(change["after"]) :]
    result["segments"]["s01"]["translation"] = prose
    assert canonical_hash(result) == case["before_sha256"]
    return result


def predecessor_row(row):
    result = deepcopy(row)
    case = ROWS.get(row["site"])
    if case is None:
        return result
    expected = current_expected_row(case["before_row"])
    assert row == expected, "Marian Gospel provenance row"
    for field in ("source_sha256", "target_sha256"):
        result[field] = case["before_row"][field]
    assert result == case["before_row"]
    return result
