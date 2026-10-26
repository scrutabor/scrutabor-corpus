"""The Ascension Vigil's finite dates, table place and higher-feast boundaries."""

import json
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest

from build_reader.emit import kalendarium
from kalendarium import roman, temporale

VIGIL = "vigilia-ascensionis"
ROOT = Path(__file__).resolve().parents[1]
ORACLE = json.loads(
    (ROOT / "tests/fixtures/ascension-vigil-calendar.json").read_text(encoding="utf-8")
)
BY_YEAR = {row["year"]: row for row in ORACLE["rows"]}
YEARS = list(range(2026, 2102))
ERROR = "calendar: Ascension Vigil requires its own Easter+38 Wednesday of class II"


def decoded(table, ending):
    return [
        [
            row[0],
            table["formularies"][row[1]],
            table["seasons"][row[2]],
            row[3],
            table["formularies"][row[4]],
        ]
        for row in table["years"][str(ending)]
    ]


def test_finite_oracle_has_every_year_and_all_four_higher_feasts():
    assert ORACLE["schema_version"] == "1.0.0"
    assert len(ORACLE["rows"]) == 76
    assert list(BY_YEAR) == YEARS
    assert len({row["vigil"] for row in ORACLE["rows"]}) == 76
    assert {row["vigil"]: row["winner"] for row in ORACLE["rows"] if row["winner"] != VIGIL} == {
        "2067-05-11": "sanctorum-philippi-et-iacobi-apostolorum",
        "2078-05-11": "sanctorum-philippi-et-iacobi-apostolorum",
        "2079-05-31": "beata-maria-virgo-regina",
        "2089-05-11": "sanctorum-philippi-et-iacobi-apostolorum",
    }
    assert sum(row["winner"] == VIGIL for row in ORACLE["rows"]) == 72
    assert sum(row["ordinary_case"] == "lower-date-required" for row in ORACLE["rows"]) == 56
    assert sum(row["ordinary_case"] == "blank-universal-date" for row in ORACLE["rows"]) == 16
    for row in ORACLE["rows"]:
        pascha, vigil, ascension = (
            date.fromisoformat(row[key]) for key in ("easter", "vigil", "ascension")
        )
        assert vigil.weekday() == 2
        assert vigil == pascha + timedelta(days=38)
        assert ascension == vigil + timedelta(days=1)


@pytest.mark.parametrize("ending", YEARS)
def test_actual_temporal_candidate_and_roman_winner_match_the_recorded_date(ending):
    row = BY_YEAR[ending]
    when = date.fromisoformat(row["vigil"])
    candidate = [day for day in temporale.year(ending) if day.formulary == VIGIL]
    assert candidate == [temporale.Dies(when, VIGIL, VIGIL, "paschale", 2)]
    assert candidate[0].transferred is False
    assert roman._temporal_precedence(candidate[0]) == 21
    days = roman.year(ending)
    assert len(days) == len({day.when for day in days})
    kept = [day for day in days if day.when == when]
    assert len(kept) == 1
    assert (kept[0].formulary, kept[0].position, kept[0].season, kept[0].dies_class) == (
        row["winner"],
        row["winner"],
        "paschale",
        row["class"],
    )
    said = [day for day in days if day.formulary == VIGIL]
    assert said == (candidate if row["winner"] == VIGIL else [])
    ascension = [day for day in days if day.formulary == "ascensio-domini"]
    assert len(ascension) == 1
    assert ascension[0].when.isoformat() == row["ascension"]


def test_actual_emitted_table_retains_seventy_two_vigils_and_four_higher_winners():
    table = kalendarium()
    assert list(map(int, table["years"])) == YEARS
    assert table["formularies"].count(VIGIL) == 1
    said = []
    for ending, expected in BY_YEAR.items():
        rows = decoded(table, ending)
        assert len(rows) == len({row[0] for row in rows})
        found = [row for row in rows if row[0] == expected["vigil"]]
        assert found == [
            [
                expected["vigil"],
                expected["winner"],
                "paschale",
                expected["class"],
                expected["winner"],
            ]
        ]
        said.extend(row[0] for row in rows if row[1] == VIGIL)
    assert said == [row["vigil"] for row in ORACLE["rows"] if row["winner"] == VIGIL]
    assert len(said) == 72


def test_may_first_is_a_1962_rule_projection_not_a_shipped_1940_ordo():
    # Deliberately outside reader coverage: project the selected 1962 rules,
    # including the I-class Joseph feast, not the historical calendar of 1940.
    candidate = [day for day in temporale.year(1940) if day.formulary == VIGIL]
    assert len(candidate) == 1
    assert candidate[0].when == date(1940, 5, 1)
    assert roman._temporal_precedence(candidate[0]) == 21
    days = roman.year(1940)
    kept = next(day for day in days if day.when == date(1940, 5, 1))
    assert kept.formulary == "sancti-ioseph-opificis" and kept.dies_class == 1
    assert not any(day.formulary == VIGIL for day in days)


@pytest.mark.parametrize("damage", ["sunday", "another-wednesday", "position", "class", "season"])
def test_actual_precedence_rejects_a_foreign_vigil_shape_and_recovers(damage):
    good = next(day for day in temporale.year(2026) if day.formulary == VIGIL)
    assert roman._temporal_precedence(good) == 21
    if damage == "sunday":
        bad = replace(good, when=date(2026, 5, 10))
    elif damage == "another-wednesday":
        bad = replace(good, when=date(2026, 5, 20))
    elif damage == "position":
        bad = replace(good, position="dominica-v-post-pascha")
    elif damage == "class":
        bad = replace(good, dies_class=1)
    else:
        bad = replace(good, season="per-annum")
    with pytest.raises(ValueError) as caught:
        roman._temporal_precedence(bad)
    assert str(caught.value) == ERROR
    assert roman._temporal_precedence(good) == 21


def test_unrelated_temporal_precedence_controls_keep_their_places():
    days = temporale.year(2026)
    by_name = {day.formulary: day for day in days}
    assert roman._temporal_precedence(by_name["corpus-christi"]) == 3
    assert roman._temporal_precedence(by_name["ascensio-domini"]) == 3
    assert roman._temporal_precedence(by_name["epiphania-domini"]) == 3
    assert roman._temporal_precedence(by_name["dominica-v-post-pascha"]) == 15
    assert roman._temporal_precedence(by_name["in-octava-nativitatis"]) == 5
    assert roman._temporal_precedence(by_name["vigilia-nativitatis"]) == 5
