"""Exact Rosary Communion comparisons never replace current native inputs."""

import json
from copy import deepcopy
from pathlib import Path

from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs, prose
from checks.lint import lint_text
from checks.translation_provenance import canonical_hash

DATA = json.loads(
    (Path(__file__).with_name("fixtures") / "rosary-communion-constructions.json").read_text()
)
TEXT = DATA["text"]


def healthy_rosary(core, layer):
    assert language_packs.check_core(core) == []
    assert lint_text(core) == ([], 19)
    name = TEXT.split(".", 1)[1] + ".json"
    path = Path("languages") / layer["language"] / "texts/proprium" / name
    assert language_packs.check_layer(core, layer, path) == []
    assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
    assert prose.check(layer) == []


def reviewed_rosary(core, layer):
    assert core.get("id") == layer.get("text") == TEXT, "complete Rosary subject"
    assert canonical_hash(core) == DATA["core_after_sha256"], "complete Rosary core"
    assert layer.get("language") in DATA["layers"], "complete Rosary layer"
    case = DATA["layers"][layer["language"]]
    assert canonical_hash(layer) == case["after_sha256"], "complete Rosary layer"


def predecessor_rosary_core(core):
    if core.get("id") != TEXT:
        return deepcopy(core)
    assert canonical_hash(core) == DATA["core_after_sha256"], "complete Rosary core"
    result = deepcopy(core)
    word = result["segments"][0]["words"][1]
    assert (word["id"], word["morph"]["case"]) == ("w002", "acc")
    word["morph"]["case"] = "voc"
    expected = DATA["core_after"]["localization"]["explanations"]
    assert result["localization"]["explanations"] == expected
    del result["localization"]["explanations"]
    assert canonical_hash(result) == DATA["core_before_sha256"], "complete Rosary predecessor"
    return result


def predecessor_rosary_layer(layer):
    if layer.get("text") != TEXT:
        return deepcopy(layer)
    assert layer.get("language") in DATA["layers"], "complete Rosary layer"
    case = DATA["layers"][layer["language"]]
    assert canonical_hash(layer) == case["after_sha256"], "complete Rosary layer"
    result = deepcopy(layer)
    for wid, before in case["before"]["words"].items():
        after = case["after"]["words"][wid]
        if before != after:
            assert result["words"][wid] == after
            result["words"][wid] = deepcopy(before)
    assert result["segments"]["s01"] == case["after"]["segments"]["s01"]
    result["segments"]["s01"]["translation"] = case["before"]["segments"]["s01"]["translation"]
    del result["segments"]["s01"]["alignments"]
    assert canonical_hash(result) == case["before_sha256"], "complete Rosary predecessor"
    return result


def predecessor_rosary_wording(row, target):
    assert row.get("language") in DATA["layers"], "unchanged wording"
    case = DATA["layers"][row["language"]]
    assert row == case["row_after"], "unchanged wording"
    assert target == case["after"]["segments"]["s01"]["translation"], "unchanged wording"
    result = deepcopy(row)
    for field in ("source_sha256", "target_sha256"):
        result[field] = case["row_before"][field]
    assert result == case["row_before"], "unchanged wording"
    return result, case["before"]["segments"]["s01"]["translation"]


def rosary_opening_case(row):
    if row[1] != TEXT:
        return deepcopy(row)
    assert row[0] in DATA["opening_rows"], "historical Rosary opening"
    case = DATA["opening_rows"][row[0]]
    assert list(row) == case["before"], "historical Rosary opening"
    return deepcopy(case["after"])
