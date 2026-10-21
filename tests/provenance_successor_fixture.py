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
