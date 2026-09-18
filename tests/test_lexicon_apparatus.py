"""Raw dictionary apparatus must not become published senses."""

import pytest

from checks.lexicon import lint_senses


def check(sense):
    return lint_senses("en", {"test": {"senses": [sense]}}, {"test": {}})


@pytest.mark.parametrize(
    "sense",
    [
        "(w/DAT) be near",
        "[~ x => go]",
        "PERFDEF remember",
        "abb. Sext.??",
        "receive (L+S)",
        "do (Bee)",
        "A: before",
    ],
)
def test_export_apparatus_is_rejected(sense):
    assert any("dictionary apparatus" in error for error in check(sense))


@pytest.mark.parametrize(
    "sense",
    [
        "(shining) white",
        "height (of rank)",
        "vineyard",
        "shoot (of a vine)",
        "as much as",
        "father/mother",
        "Father",
        "memory",
    ],
)
def test_legitimate_meaning_qualifiers_remain_valid(sense):
    assert check(sense) == []
