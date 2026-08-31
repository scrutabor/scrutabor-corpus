"""The temporal and supported sanctoral cycles resolved into one calendar."""

from __future__ import annotations

from datetime import timedelta

from kalendarium.sanctorale import FORMULARIES as SANCTORAL_FORMULARIES
from kalendarium.sanctorale import Festum, occurrences
from kalendarium.temporale import FORMULARIES as TEMPORAL_FORMULARIES
from kalendarium.temporale import Dies
from kalendarium.temporale import year as temporal_year

FORMULARIES = TEMPORAL_FORMULARIES | SANCTORAL_FORMULARIES

_FIRST_CLASS_FEASTS_OF_THE_LORD = frozenset(
    {
        "sanctissimae-trinitatis",
        "corpus-christi",
        "sacratissimi-cordis-iesu",
        "d-n-iesu-christi-regis",
    }
)


def _temporal_precedence(day: Dies) -> int:
    """Return the numbered place of a temporal day in the table at n. 91."""

    if day.formulary in _FIRST_CLASS_FEASTS_OF_THE_LORD:
        return 3
    if day.dies_class == 1:
        return 6
    if day.position.startswith("dominica-"):
        return 15
    # The supported range has no other second-class temporal day, but keeping
    # the table's next place makes a future addition fail conservatively.
    return 18


def _as_day(when, feast: Festum, position: str | None = None) -> Dies:
    return Dies(
        when=when,
        formulary=feast.formulary,
        position=position or feast.formulary,
        season="per-annum",
        dies_class=feast.dies_class,
    )


def year(ending: int) -> list[Dies]:
    """One Roman liturgical year with the supported universal feasts resolved.

    n. 91 supplies the precedence table; n. 93 suppresses the lower day;
    n. 96 moves an impeded first-class feast to the next day that is neither
    first nor second class, with its special Monday rule for All Souls.
    """

    days = {day.when: day for day in temporal_year(ending)}
    precedence = {day.when: _temporal_precedence(day) for day in days.values()}

    for original, feast in occurrences(ending):
        when = original
        current = days.get(when)
        if current is None:
            days[when] = _as_day(when, feast)
            precedence[when] = feast.precedence
            continue

        if feast.precedence < precedence[when]:
            position = current.position if current.position.startswith("dominica-") else None
            days[when] = _as_day(when, feast, position)
            precedence[when] = feast.precedence
            continue

        if not feast.transferable:
            continue

        # n. 96: only first-class feasts have a right of transfer, and their
        # destination must not itself be a first- or second-class day.
        when += timedelta(days=1)
        while when in days:
            when += timedelta(days=1)
        days[when] = _as_day(when, feast)
        precedence[when] = feast.precedence

    ordered = sorted(days.values(), key=lambda day: day.when)
    assert len({day.formulary for day in ordered}) == len(ordered), ending
    assert {day.formulary for day in ordered} <= FORMULARIES
    return ordered
