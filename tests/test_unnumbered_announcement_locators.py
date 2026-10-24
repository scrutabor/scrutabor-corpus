"""Illustrated feast openings have scan positions, not printed page numerals."""

from copy import deepcopy

import pytest
from test_reading_announcement_sources import snapshot, source_errors

OPENINGS = {
    "ordinarium.lectio-actuum-apostolorum": 437,
    "ordinarium.lectio-epistolae-beati-pauli-apostoli-ad-titum": 98,
    "ordinarium.lectio-isaiae-prophetae": 118,
    "ordinarium.lectio-libri-iudith": 708,
}


@pytest.mark.parametrize("text,page", OPENINGS.items())
def test_each_illustrated_opening_distinguishes_print_from_scan(text, page):
    state = snapshot()
    assert source_errors(state) == []
    use = next(row for row in state["graph"]["uses"] if row["id"] == f"use.{text}.vatican1962")
    assert use["locator"]["printed"] == "No printed page numeral (illustrated opening)"
    assert use["locator"]["scan"] == f"PDF page {page}"


@pytest.mark.parametrize("text,page", OPENINGS.items())
@pytest.mark.parametrize("damage", ["missing", "invented-number"])
def test_missing_or_invented_printed_locator_is_not_a_source_repair(text, page, damage):
    state = snapshot()
    assert source_errors(state) == []
    changed = deepcopy(state)
    use = next(row for row in changed["graph"]["uses"] if row["id"] == f"use.{text}.vatican1962")
    if damage == "missing":
        del use["locator"]["printed"]
    else:
        use["locator"]["printed"] = str(page)
    assert source_errors(changed) == [f"{text}: Vatican page/reference/source identity differs"]
