"""The grouped relationship registry covers every inherited translation once."""

from pathlib import Path

from checks.translation_basis import check

CORPUS = Path(__file__).resolve().parent.parent


def test_translation_basis_is_complete_and_nonoverlapping() -> None:
    errors, tally = check(CORPUS)
    assert errors == []
    assert sum(tally.values()) > 1000
    assert tally["traditional-composite"] > 0
