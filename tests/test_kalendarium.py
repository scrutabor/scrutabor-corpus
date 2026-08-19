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


def test_the_immaculate_conception_takes_the_sunday_n15_gives_it():
    # n. 15, second sentence. The one feast of the saints this module knows,
    # and it is here because the article that governs Sundays prints it. Ten
    # years of the shipped window put 8 December on a Sunday of Advent, and
    # until 2026-08-19 the book opened on the Sunday's Mass on every one.
    met = 0
    for y in YEARS:
        eighth = date(y - 1, 12, 8)
        if eighth.weekday() != 6:
            continue
        met += 1
        day = {d.when: d for d in year(y)}[eighth]
        assert day.formulary == "immaculata-conceptio"
        assert day.position.endswith("-adventus"), "the Sunday keeps its own name"
        assert day.dies_class == 1
    assert met > 10, f"only {met} years put 8 December on a Sunday"


def test_the_vigil_of_the_nativity_is_a_day_in_every_year():
    # n. 30 a. It was emitted only where it displaced a Sunday, so on the 66
    # years of 76 it falls on a weekday the table had nothing — and the app
    # called Christmas Eve an ordinary weekday.
    for y in YEARS:
        eve = {d.when: d for d in year(y)}.get(date(y - 1, 12, 24))
        assert eve is not None, f"{y - 1}-12-24 has no entry"
        assert eve.formulary == "vigilia-nativitatis"
        assert eve.dies_class == 1


def test_the_sunday_in_the_octave_reaches_the_thirty_first():
    # n. 69: "a die 26 ad 31 decembris", inclusive. An exclusive stop lost ten
    # years of this window entirely.
    met = 0
    for y in YEARS:
        last = date(y - 1, 12, 31)
        if last.weekday() != 6:
            continue
        met += 1
        day = {d.when: d for d in year(y)}[last]
        assert day.formulary == "dominica-infra-octavam-nativitatis"
    assert met > 10, f"only {met} years put 31 December on a Sunday"


def test_the_octave_day_of_the_nativity_is_the_first_of_january():
    # n. 67: "dies autem octavus est I classis", and the Missale gives it its
    # own Mass under "Die 1 ianuarii - IN OCTAVA NATIVITATIS DOMINI".
    for y in YEARS:
        day = {d.when: d for d in year(y)}.get(date(y, 1, 1))
        assert day is not None, f"{y}-01-01 has no entry"
        assert day.formulary == "in-octava-nativitatis"
        assert day.dies_class == 1


def test_both_vigils_of_the_first_class_are_carried():
    # n. 30 names two. Only one of them was here.
    for y in YEARS:
        said = {d.formulary for d in year(y)}
        assert "vigilia-nativitatis" in said
        assert "vigilia-pentecostes" in said


def test_the_declared_gap_is_still_a_gap():
    # When Christmas falls on a Sunday no Sunday occurs between 26 and 31
    # December, and the Mass of the Sunday within the octave is said on the
    # 30th by a rule n. 70 sends to the Missale's own rubrics — which this
    # edition has not transcribed. The gap is named in the module docstring;
    # this holds the two together, so that closing one without the other
    # fails rather than drifts.
    short = [
        y
        for y in YEARS
        if date(y - 1, 12, 25).weekday() == 6
        and not any(d.formulary == "dominica-infra-octavam-nativitatis" for d in year(y))
    ]
    assert short, "the gap closed — say so in kalendarium/__init__.py and delete this"
    from kalendarium import __doc__ as charter

    assert charter and "30 December" in charter, "the gap must stay declared while it stands"


def test_a_shipped_table_that_drifts_from_the_book_is_caught(monkeypatch):
    # The check used to re-derive its eight values from the computus — the
    # same functions year() is built from, never year() itself — so a
    # Pentecost moved a whole week inside the SHIPPED table still printed
    # verified=416. This pins the check to what ships: shift Pentecost in
    # year()'s own output and the tabella must contradict it.
    from dataclasses import replace

    import checks.kalendarium as ck

    def shifted(ending):
        return tuple(
            replace(d, when=d.when + timedelta(days=7))
            if d.position == "dominica-pentecostes"
            else d
            for d in year(ending)
        )

    monkeypatch.setattr(ck, "_year", shifted)
    errors, _compared, _misprints = ck.check()
    assert errors, "a moved Pentecost in the shipped table must redden the check"
    assert any("Pentecostes" in e for e in errors)
