"""Exact wording and provenance successors of 2026-10-21."""

import json
from copy import deepcopy
from pathlib import Path

from checks.translation_provenance import protected

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures/translation-provenance-successor-2026-10-21.json").read_text(
        encoding="utf-8"
    )
)
INTROITS = {row["site"]: row for row in FIXTURE["introits"]}
REFLEXIVE = json.loads(
    (Path(__file__).parent / "fixtures/polish-reflexive-case-successors.json").read_text(
        encoding="utf-8"
    )
)


def assert_formula(target):
    assert target.count(FIXTURE["protected_polish"]) == 1, "protected Gloria Patri"


def assert_protection_scope(text, language, segment, target):
    expected = f"{text}.{segment}.{language}" in INTROITS
    assert protected(text, language, segment) is expected, "protection scope"
    if expected:
        assert_formula(target)
    return expected


def metadata_successors(rows):
    """Apply exact successors to historical expected rows, never to actual rows."""
    result = deepcopy(rows)
    for row in result:
        site = row["site"]
        if site in FIXTURE["after_rows"]:
            assert row == FIXTURE["before_rows"][site] or row == FIXTURE["after_rows"][site]
            row.update(FIXTURE["after_rows"][site])
    return result


def restore_preface_prose(layer, slug):
    """Reverse only twelve exact English ending successors for historical digests."""
    result = deepcopy(layer)
    for site, wording in FIXTURE["prose_successors"].items():
        text, segment, language = site.rsplit(".", 2)
        if text == "ordinarium.praefatio-" + slug:
            assert language == "en"
            assert result["segments"][segment]["translation"] == wording["after"], (
                "preface ending successor"
            )
            result["segments"][segment]["translation"] = wording["before"]
    return result


def current_expected_reflexive_row(row):
    """Advance only a historical expected row, never an actual observation."""
    result = deepcopy(row)
    change = REFLEXIVE["rows"].get(row["site"])
    if change is not None:
        assert result == change["before"], "historical reflexive expected row"
        result = deepcopy(change["after"])
    return result


def restore_reflexive_rows(rows):
    """Reverse only the exact current row at its stable site."""
    result = deepcopy(rows)
    for index, row in enumerate(result):
        change = REFLEXIVE["rows"].get(row["site"])
        if change is not None:
            assert row == change["after"], "current reflexive row inverse"
            result[index] = deepcopy(change["before"])
    return result


def restore_reflexive_prose(layer, text):
    """Restore named current prose for a historical digest, not whole layers."""
    result = deepcopy(layer)
    for site, wording in REFLEXIVE["prose"].items():
        expected_text, segment, language = site.rsplit(".", 2)
        if expected_text == text:
            assert language == "pl"
            assert result["segments"][segment]["translation"] == wording["after"], (
                "current reflexive prose inverse"
            )
            result["segments"][segment]["translation"] = wording["before"]
    return result
