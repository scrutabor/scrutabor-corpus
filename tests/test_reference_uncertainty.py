"""An unclear scan glyph must not become a definite printing-error claim."""

import copy
import json
from pathlib import Path

import pytest

from build_reader import introductiones as reader

ROOT = Path(__file__).resolve().parents[1]
LOW = "proprium/dominica-in-albis-evangelium"
LENT = "proprium/dominica-iii-in-quadragesima-evangelium"


def binding(table, reading):
    return next(row for row in table["announcements"] if row["reading"] == reading)


def test_uncertain_scan_and_definite_numeric_error_project_differently():
    table = reader.resource(ROOT)
    assert table == reader.expected(ROOT)
    assert len(table["announcements"]) == 206
    low = binding(table, LOW)
    assert low["reference"] == "Ioann. 80, 19-31"
    assert low["pericope"] == {"book": "Ioann", "passages": [{"chapter": 20, "verses": [[19, 31]]}]}
    assert low["reference_uncertain"] is True and "misprint" not in low
    lent = binding(table, LENT)
    assert lent["reference"] == "Luc. 11, 4-28"
    assert lent["pericope"] == {"book": "Luc", "passages": [{"chapter": 11, "verses": [[14, 28]]}]}
    assert lent["misprint"] is True and "reference_uncertain" not in lent
    assert [row["reading"] for row in table["announcements"] if row.get("reference_uncertain")] == [
        LOW
    ]
    assert [row["reading"] for row in table["announcements"] if row.get("misprint")] == [LENT]
    authored = json.loads((ROOT / "ordo/introductiones.json").read_text())
    for original in authored["announcements"]:
        emitted = binding(table, original["reading"].replace(".", "/", 1))
        assert emitted["reference"] == original["reference_as_printed"]
        assert emitted["pericope"] == original["pericope"]
        assert "uncertain" not in emitted and "comparator" not in emitted
    detail = next(row for row in authored["announcements"] if "uncertain" in row)
    assert detail["reading"].replace(".", "/", 1) == LOW
    assert detail["uncertain"] == "the first digit of the chapter, read as 8, may be a damaged 2"
    reader.validate(table)


@pytest.mark.parametrize("invalid", [False, None, 1, "true"])
def test_uncertainty_flag_is_only_ever_true(invalid):
    pristine = reader.resource(ROOT)
    damaged = copy.deepcopy(pristine)
    binding(damaged, LOW)["reference_uncertain"] = invalid
    with pytest.raises(ValueError, match="introductiones:"):
        reader.validate(damaged)
    reader.validate(pristine)


def test_uncertainty_and_definite_misprint_flags_are_mutually_exclusive():
    pristine = reader.resource(ROOT)
    damaged = copy.deepcopy(pristine)
    binding(damaged, LOW)["misprint"] = True
    with pytest.raises(ValueError, match="uncertain scan reading"):
        reader.validate(damaged)
    reader.validate(pristine)
