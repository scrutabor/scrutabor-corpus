"""When Easter falls, and the days that hang off it."""

from __future__ import annotations

from datetime import date, timedelta


def easter(year: int) -> date:
    """Easter Sunday in the Gregorian calendar.

    The anonymous Gregorian algorithm. The Missale explains the reform it
    implements at length (De anno et eius partibus, printed pages XXXVII-XL)
    and prints the resulting dates for 1960-2011; this reproduces every one of
    them, which is the only claim made for it here.
    """
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    ell = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ell) // 451
    month, day = divmod(h + ell - 7 * m + 114, 31)
    return date(year, month, day + 1)


def advent_i(year: int) -> date:
    """The First Sunday of Advent, which opens the year that ENDS in `year`.

    n. 20: "Dominica I Adventus ea est, quae cadit die 30 novembris vel est
    ipsi proximior" — the Sunday falling on 30 November or nearest to it. Since
    Sundays are seven days apart, exactly one falls within three days of the
    30th, so "nearest" never has to be broken.
    """
    andrew = date(year, 11, 30)
    ahead = andrew + timedelta(days=(6 - andrew.weekday()) % 7)
    behind = ahead - timedelta(days=7)
    return ahead if (ahead - andrew) <= (andrew - behind) else behind
