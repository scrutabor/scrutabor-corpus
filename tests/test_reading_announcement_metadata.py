"""Source-count prose must distinguish one reading from several readings."""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def singular_count_error(method):
    return re.search(r"\b1 further readings\b", method) is not None


@pytest.mark.parametrize(
    "method, expected",
    [
        ("and over the 1 further reading named in the witness header", False),
        ("and over the 2 further readings named in the witness header", False),
        ("and over the 31 further readings named in the witness header", False),
        ("and over the 1 further readings named in the witness header", True),
    ],
)
def test_singular_count_control_has_plural_and_near_match_controls(method, expected):
    assert singular_count_error(method) is expected


def test_all_heading_source_methods_use_the_singular_for_one():
    formulas = json.loads((ROOT / "tests/fixtures/reading-announcement-formulas.json").read_text())[
        "formulas"
    ]
    assert len(formulas) == 26
    for formula in formulas:
        path = ROOT / "texts" / (formula["text"].replace(".", "/", 1) + ".json")
        document = json.loads(path.read_text())
        assert not singular_count_error(document["editorial"]["source"]["method"]), formula["text"]
