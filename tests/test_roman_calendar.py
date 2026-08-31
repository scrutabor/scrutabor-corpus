"""The supported sanctoral resolved against the temporal cycle."""

from datetime import date

from kalendarium.roman import FORMULARIES, year


def by_date(ending: int):
    return {day.when: day for day in year(ending)}


def test_2026_names_every_supported_observance_through_advent():
    days = by_date(2026)
    assert days[date(2026, 5, 31)].formulary == "sanctissimae-trinitatis"
    assert days[date(2026, 6, 12)].formulary == "sacratissimi-cordis-iesu"
    assert days[date(2026, 11, 1)].formulary == "omnium-sanctorum"
    assert days[date(2026, 11, 1)].position == "dominica-xxiii-post-pentecosten"
    assert days[date(2026, 11, 2)].formulary == "commemoratio-omnium-fidelium-defunctorum"
    assert days[date(2026, 11, 9)].formulary == ("dedicatio-archibasilicae-sanctissimi-salvatoris")
    assert days[date(2026, 11, 22)].formulary == "dominica-xxiv-post-pentecosten"


def test_a_second_class_feast_that_is_not_of_the_lord_yields_to_sunday():
    days = by_date(2026)
    assert days[date(2026, 7, 26)].formulary == "dominica-ix-post-pentecosten"
    assert days[date(2026, 10, 11)].formulary == "dominica-xx-post-pentecosten"
    assert days[date(2026, 10, 18)].formulary == "dominica-xxi-post-pentecosten"


def test_a_second_class_feast_of_the_lord_takes_a_second_class_sunday():
    transfiguration = by_date(2023)[date(2023, 8, 6)]
    assert transfiguration.formulary == "transfiguratio-domini"
    assert transfiguration.position.endswith("-post-pentecosten")

    dedication = by_date(2025)[date(2025, 11, 9)]
    assert dedication.formulary == "dedicatio-archibasilicae-sanctissimi-salvatoris"
    assert dedication.position.endswith("-post-pentecosten")


def test_an_impeded_first_class_feast_moves_to_the_next_free_day():
    # In 2022 the Sacred Heart falls on 24 June. It has place 3 in n. 91;
    # St John has place 11 and therefore moves under n. 96.
    days = by_date(2022)
    assert days[date(2022, 6, 24)].formulary == "sacratissimi-cordis-iesu"
    assert days[date(2022, 6, 25)].formulary == "nativitas-sancti-ioannis-baptistae"


def test_all_souls_uses_its_special_monday_when_second_november_is_sunday():
    days = by_date(2031)
    assert days[date(2031, 11, 2)].formulary.endswith("post-pentecosten")
    assert days[date(2031, 11, 3)].formulary == ("commemoratio-omnium-fidelium-defunctorum")


def test_the_merged_calendar_neither_repeats_nor_invents_a_formulary():
    for ending in range(1961, 2101):
        said = [day.formulary for day in year(ending)]
        assert len(said) == len(set(said)), ending
        assert set(said) <= FORMULARIES
