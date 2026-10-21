"""Universal major fixed feasts resolved against the temporal cycle."""

from datetime import date

import pytest

from kalendarium.roman import year
from kalendarium.sanctorale import FESTA, occurrences

YEARS = range(1961, 2101)


def by_date(ending: int):
    return {day.when: day for day in year(ending)}


def test_every_fixed_major_feast_is_kept_transferred_or_lawfully_suppressed():
    expected = {feast.formulary for feast in FESTA}
    for ending in YEARS:
        said = {day.formulary for day in year(ending)}
        missing = expected - said
        assert all(
            next(feast for feast in FESTA if feast.formulary == formulary).dies_class == 2
            for formulary in missing
        )


def test_annunciation_has_its_proper_post_easter_seat():
    day = next(day for day in year(2016) if day.formulary == "annuntiatio-beatae-mariae-virginis")
    assert day.when == date(2016, 4, 4)


def test_first_class_feasts_move_past_the_whole_easter_octave():
    day = next(day for day in year(2038) if day.formulary == "sancti-ioseph-opificis")
    assert day.when == date(2038, 5, 3)


def test_second_class_feasts_do_not_displace_first_class_ferias():
    assert "sancti-marci-evangelistae" not in {day.formulary for day in year(2011)}
    assert "cathedra-sancti-petri" not in {day.formulary for day in year(2023)}


def test_sanctoral_days_keep_the_actual_liturgical_season():
    days_2026 = by_date(2026)
    assert days_2026[date(2025, 11, 30)].season == "adventus"
    assert days_2026[date(2025, 12, 26)].season == "nativitas"
    assert days_2026[date(2026, 3, 19)].season == "quadragesima"
    assert by_date(2027)[date(2027, 5, 1)].season == "paschale"


MATTHIAS = "sancti-matthiae-apostoli"
MATTHIAS_LEAP_YEARS = (
    2028,
    2032,
    2036,
    2040,
    2044,
    2048,
    2052,
    2056,
    2060,
    2064,
    2068,
    2072,
    2076,
    2080,
    2084,
    2088,
    2092,
    2096,
)


@pytest.mark.parametrize("ending", MATTHIAS_LEAP_YEARS)
def test_matthias_has_february25_as_his_proper_leap_year_date(ending):
    found = [(when, feast) for when, feast in occurrences(ending) if feast.formulary == MATTHIAS]
    assert len(found) == 1
    when, feast = found[0]
    assert when == date(ending, 2, 25)
    assert all(candidate != date(ending, 2, 24) for candidate, _ in found)
    assert (feast.month, feast.day) == (2, 24)
    assert feast.dies_class == 2 and not feast.transferable


@pytest.mark.parametrize("ending,day", [(2000, 25), (2027, 24), (2100, 24)])
def test_matthias_date_obeys_gregorian_century_and_common_year_rules(ending, day):
    found = [when for when, feast in occurrences(ending) if feast.formulary == MATTHIAS]
    assert found == [date(ending, 2, day)]
    wrong_day = 24 if day == 25 else 25
    assert date(ending, 2, wrong_day) not in found


def test_correct_matthias_occurrence_preserves_precedence_without_transfer():
    impeded = {
        2052: "dominica-in-sexagesima",
        2080: "dominica-i-in-quadragesima",
        2088: None,  # Ash Wednesday's proper feria is not represented here.
    }
    for ending in MATTHIAS_LEAP_YEARS:
        days = by_date(ending)
        proper = days.get(date(ending, 2, 25))
        wrong = days.get(date(ending, 2, 24))
        assert wrong is None or wrong.formulary != MATTHIAS
        matthias_days = [day for day in days.values() if day.formulary == MATTHIAS]
        if ending in impeded:
            assert matthias_days == []
            if impeded[ending] is None:
                assert proper is None
            else:
                assert proper is not None
                assert proper.formulary == impeded[ending]
        else:
            assert proper is not None
            assert proper.formulary == MATTHIAS and proper.dies_class == 2
            assert len(matthias_days) == 1 and matthias_days[0].when == date(ending, 2, 25)
