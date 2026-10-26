"""Source-literal supported temporal identities and occurrence consistency.

These finite ordinal/coalescence controls do not extend the shipped calendar
range or assert historical Ordos. No persistent mutation.
"""

from dataclasses import replace
from datetime import date, timedelta

import pytest

from kalendarium import roman, temporale
from kalendarium.computus import easter
from kalendarium.sanctorale import FESTA

YEARS = tuple(range(2026, 2102))
# Independent literal oracle from printed table1/2/3/4/5/6/9 plus the actual
# source constructors. Expected counts are declared before any test execution.
EXPECTED = {
    "nativitas-domini": (1, 76),
    "dominica-resurrectionis": (1, 76),
    "dominica-pentecostes": (1, 76),
    "feria-v-in-cena-domini": (2, 76),
    "vigilia-paschalis": (2, 76),
    "epiphania-domini": (3, 76),
    "ascensio-domini": (3, 76),
    "sanctissimae-trinitatis": (3, 76),
    "corpus-christi": (3, 76),
    "sacratissimi-cordis-iesu": (3, 76),
    "d-n-iesu-christi-regis": (3, 76),
    "immaculata-conceptio": (4, 10),
    "vigilia-nativitatis": (5, 76),
    "in-octava-nativitatis": (5, 76),
    "dominica-i-adventus": (6, 76),
    "dominica-ii-adventus": (6, 66),
    "dominica-iii-adventus": (6, 76),
    "dominica-iv-adventus": (6, 66),
    "dominica-i-in-quadragesima": (6, 76),
    "dominica-ii-in-quadragesima": (6, 76),
    "dominica-iii-in-quadragesima": (6, 76),
    "dominica-iv-in-quadragesima": (6, 76),
    "dominica-i-passionis": (6, 76),
    "dominica-ii-passionis": (6, 76),
    "dominica-in-albis": (6, 76),
    "vigilia-pentecostes": (9, 76),
}
IMMACULATE_SUNDAYS = [
    (2031, "2030-12-08"),
    (2042, "2041-12-08"),
    (2048, "2047-12-08"),
    (2053, "2052-12-08"),
    (2059, "2058-12-08"),
    (2070, "2069-12-08"),
    (2076, "2075-12-08"),
    (2081, "2080-12-08"),
    (2087, "2086-12-08"),
    (2098, "2097-12-08"),
]
INCONSISTENT = "calendar: repeated observance has inconsistent class/precedence"


@pytest.fixture(scope="module")
def candidates():
    return {year: temporale.year(year) for year in YEARS}


def test_complete_actual_classI_constructor_inventory_and_day_boundaries(candidates):
    first = [day for days in candidates.values() for day in days if day.dies_class == 1]
    assert set(day.formulary for day in first) == set(EXPECTED)
    assert len(first) == sum(count for _place, count in EXPECTED.values()) == 1890
    assert {
        place: sum(count for value, count in EXPECTED.values() if value == place)
        for place in (1, 2, 3, 4, 5, 6, 9)
    } == {
        1: 228,
        2: 152,
        3: 456,
        4: 10,
        5: 152,
        6: 816,
        9: 76,
    }
    for year, days in candidates.items():
        thursday = next(day for day in days if day.formulary == "feria-v-in-cena-domini")
        paschal_route = next(day for day in days if day.formulary == "vigilia-paschalis")
        assert thursday.when == easter(year) - timedelta(days=3)
        assert paschal_route.when == easter(year) - timedelta(days=1)
        assert paschal_route.when.weekday() == 5  # Holy Saturday, not a day named by a vigil.
        assert roman._temporal_precedence(paschal_route) == 2


@pytest.mark.parametrize("identity", list(EXPECTED))
def test_each_source_literal_weight_count_and_recovery(candidates, monkeypatch, identity):
    place, count = EXPECTED[identity]
    selected = [day for days in candidates.values() for day in days if day.formulary == identity]
    assert len(selected) == count
    assert all(roman._temporal_precedence(day) == place for day in selected)
    actual = roman._temporal_precedence
    wrong = 5 if place == 6 else 6
    with monkeypatch.context() as context:
        context.setattr(
            roman,
            "_temporal_precedence",
            lambda day: wrong if day.formulary == identity else actual(day),
        )
        with pytest.raises(AssertionError):
            assert all(roman._temporal_precedence(day) == place for day in selected)
    assert all(roman._temporal_precedence(day) == place for day in selected)


def test_unknown_classI_temporal_identity_has_no_generic_place6(candidates):
    good = next(day for day in candidates[2026] if day.formulary == "ascensio-domini")
    assert roman._temporal_precedence(good) == 3
    wrong = replace(good, formulary="unrepresented-first-class-temporal")
    with pytest.raises(ValueError) as caught:
        roman._temporal_precedence(wrong)
    assert str(caught.value) == "calendar: unsupported first-class temporal identity"
    assert roman._temporal_precedence(good) == 3


@pytest.mark.parametrize("ending,iso", IMMACULATE_SUNDAYS)
def test_same_actual_observance_is_not_duplicated_or_transferred(ending, iso):
    when = date.fromisoformat(iso)
    assert when.year == ending - 1 and when.weekday() == 6
    raw = [day for day in temporale.year(ending) if day.formulary == "immaculata-conceptio"]
    assert len(raw) == 1 and raw[0].when == when
    assert raw[0].position == "dominica-ii-adventus"
    days = roman.year(ending)
    selected = [day for day in days if day.formulary == "immaculata-conceptio"]
    assert selected == raw
    assert not any(
        day.formulary == "immaculata-conceptio" and day.when == when + timedelta(days=1)
        for day in days
    )
    assert roman.year(ending) == days


@pytest.mark.parametrize("field,value", [("dies_class", 2), ("precedence", 5)])
def test_same_identity_inconsistent_metadata_rejects_and_recovers(monkeypatch, field, value):
    ending = 2031
    good = roman.year(ending)
    original = roman.occurrences

    def damaged(year):
        return [
            (
                when,
                replace(feast, **{field: value})
                if feast.formulary == "immaculata-conceptio"
                else feast,
            )
            for when, feast in original(year)
        ]

    with monkeypatch.context() as context:
        context.setattr(roman, "occurrences", damaged)
        with pytest.raises(ValueError) as caught:
            roman.year(ending)
        assert str(caught.value) == INCONSISTENT
    assert roman.year(ending) == good


def test_different_known_identities_at_equal_weight_are_not_coalesced(monkeypatch):
    # Deliberately impossible input collision: put the ACTUAL other place4
    # Festum object at the Immaculate date. This is a branch negative, NOT
    # an authored calendar record, source date or historical Ordo.
    ending = 2031
    when = date(2030, 12, 8)
    good = roman.year(ending)
    original = roman.occurrences
    other = next(feast for feast in FESTA if feast.formulary == "assumptio-beatae-mariae-virginis")
    assert other.dies_class == 1 and other.precedence == 4 and other.transferable

    def different_identity(year):
        return [
            (day, other if feast.formulary == "immaculata-conceptio" else feast)
            for day, feast in original(year)
        ]

    with monkeypatch.context() as context:
        context.setattr(roman, "occurrences", different_identity)
        days = roman.year(ending)
        kept = next(day for day in days if day.when == when)
        assert kept.formulary == "immaculata-conceptio"
        moved = next(day for day in days if day.when == when + timedelta(days=1))
        assert moved.formulary == other.formulary  # Not silently lost as an equal-weight duplicate.
    assert roman.year(ending) == good
