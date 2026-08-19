"""The temporal cycle: it must agree with the book, article by article."""

from datetime import date, timedelta

import pytest

from checks.kalendarium import check
from kalendarium.computus import advent_i, easter
from kalendarium.temporale import FORMULARIES, sundays_after_pentecost, year

YEARS = range(1961, 2101)


def test_the_book_verifies_the_computation():
    # 52 rows of the Missale's own TABELLA TEMPORARIA, eight values each.
    errors, compared, misprints = check()
    assert errors == []
    assert compared == 416, "the table is the whole verification — read all of it"
    assert misprints == 1, "the one misprint is declared; a second would be a transcription error"


def test_the_first_sunday_of_advent_is_the_one_nearest_saint_andrew():
    # n. 20. Sundays are seven days apart, so exactly one falls within three
    # days of 30 November and "nearest" never has to be broken.
    for y in YEARS:
        when = advent_i(y)
        assert when.weekday() == 6
        assert abs((when - date(y, 11, 30)).days) <= 3


def test_easter_stays_inside_its_own_window():
    for y in YEARS:
        assert date(y, 3, 22) <= easter(y) <= date(y, 4, 25)


def test_the_vigil_of_the_nativity_takes_the_fourth_sunday_when_they_meet():
    # n. 30 a. It happens whenever Christmas falls on a Monday.
    met = 0
    for y in YEARS:
        days = {d.when: d for d in year(y)}
        eve = date(y - 1, 12, 24)
        if eve.weekday() != 6:
            continue
        met += 1
        assert days[eve].formulary == "vigilia-nativitatis"
        assert days[eve].position == "dominica-iv-adventus", "the Sunday keeps its own name"
    assert met > 10, f"only {met} years put the Vigil on a Sunday — the case is not being tested"


@pytest.mark.parametrize(
    "total, transferred",
    [
        (25, ["vi"]),
        (26, ["v", "vi"]),
        (27, ["iv", "v", "vi"]),
        (28, ["iii", "iv", "v", "vi"]),
    ],
)
def test_n18_sends_the_leftover_sundays_after_epiphany_to_the_end(total, transferred):
    # The article's own table, read back off the years that have that shape.
    # "Ultimo tamen loco semper ponitur ea quae in ordine est XXIV post
    # Pentecosten": the last Sunday always says the XXIV, whatever precedes it.
    #
    # A position may be taken by Christ the King (n. 17 d) — see the test
    # below — and where it is, the transferred Mass is not said at all. So the
    # comparison is per position rather than over the sequence.
    tested = 0
    for y in YEARS:
        if sundays_after_pentecost(y) != total:
            continue
        tested += 1
        after = [d for d in year(y) if d.position.endswith("-post-pentecosten")]
        assert len(after) == total
        assert after[-1].formulary == "dominica-xxiv-post-pentecosten"
        for offset, roman in enumerate(transferred):
            day = after[23 + offset]
            if day.formulary == "d-n-iesu-christi-regis":
                continue
            assert day.formulary == f"dominica-{roman}-post-epiphaniam", (y, offset)
    assert tested, f"no year in {YEARS} has {total} Sundays after Pentecost"


def test_christ_the_king_can_swallow_a_transferred_sunday():
    # A consequence of three articles read together, and surprising enough to
    # be stated rather than left to be discovered: n. 18 puts a leftover Sunday
    # after Epiphany at the twenty-fourth place after Pentecost; n. 17 d puts
    # Christ the King on the last Sunday of October; and in a long year those
    # are the same Sunday. n. 14 then settles it — "Officium et Missa dominicae
    # impeditae nec anticipantur nec resumuntur" — so that Mass is simply not
    # said that year.
    swallowed = []
    for y in YEARS:
        total = sundays_after_pentecost(y)
        after = [d for d in year(y) if d.position.endswith("-post-pentecosten")]
        for day in after[23 : total - 1]:
            if day.formulary == "d-n-iesu-christi-regis":
                swallowed.append(y)
                assert day.when.month == 10
    assert 10 <= len(swallowed) <= 20, f"{len(swallowed)} years in 140 — the shape has changed"
    assert 1967 in swallowed, "1967 is the worked example: 28 Sundays, the King on 29 October"


def test_a_year_with_no_leftovers_still_ends_on_the_twenty_fourth():
    # "omissis, si opus sit, ceteris, quae aliquando locum habere non possunt" —
    # at 23 Sundays the XXIII is the one omitted, not the XXIV.
    for y in YEARS:
        if sundays_after_pentecost(y) != 23:
            continue
        after = [d for d in year(y) if d.position.endswith("-post-pentecosten")]
        assert after[-1].formulary == "dominica-xxiv-post-pentecosten"
        assert "dominica-xxiii-post-pentecosten" not in {d.formulary for d in after}
        return
    pytest.skip("no year in range holds 23 Sundays after Pentecost")


def test_no_mass_is_said_twice_and_none_is_invented():
    for y in YEARS:
        said = [d.formulary for d in year(y)]
        assert len(said) == len(set(said)), y
        assert set(said) <= FORMULARIES, y


def test_the_four_sundays_that_belong_to_a_feast_keep_their_own_position():
    # n. 17 b, c, d: the Holy Family, Trinity and Christ the King take the
    # Sunday's place. The Sunday is still counted — n. 16 a — and this edition
    # says both things rather than losing one of them.
    for y in YEARS:
        days = year(y)
        by_formulary = {d.formulary: d for d in days}
        assert by_formulary["sancta-familia"].position == "dominica-i-post-epiphaniam"
        assert by_formulary["sanctissimae-trinitatis"].position == "dominica-i-post-pentecosten"
        king = by_formulary["d-n-iesu-christi-regis"]
        assert king.when.month == 10 and king.when.day > 24, "the last Sunday of October"
        assert king.position.endswith("-post-pentecosten")


def test_every_season_runs_where_the_law_puts_it():
    # nn. 71-77, in the order the year walks them.
    for y in YEARS:
        days = year(y)
        seen = [d.season for d in days]
        first = {s: seen.index(s) for s in dict.fromkeys(seen)}
        assert first["adventus"] == 0
        assert first["adventus"] < first["nativitas"] < first["epiphania"]
        assert (
            first["septuagesima"] < first["quadragesima"] < first["passionis"] < first["paschale"]
        )
        pascha = easter(y)
        for d in days:
            if d.season == "paschale":
                assert pascha <= d.when <= pascha + timedelta(days=56)


def test_the_year_is_continuous_and_in_order():
    for y in YEARS:
        days = year(y)
        assert days == sorted(days, key=lambda d: d.when)
        assert days[0].when == advent_i(y - 1)
        assert days[-1].when < advent_i(y)
