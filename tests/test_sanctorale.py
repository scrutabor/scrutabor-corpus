"""Universal major fixed feasts resolved against the temporal cycle."""

from datetime import date

from kalendarium.roman import year
from kalendarium.sanctorale import FESTA

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
