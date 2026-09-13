"""The temporal and supported sanctoral cycles resolved into one calendar."""

from __future__ import annotations

from datetime import date, timedelta

from kalendarium.computus import easter
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


def _season(when, ending: int) -> str:
    pascha = easter(ending)
    if when < date(ending - 1, 12, 25):
        return "adventus"
    if when < date(ending, 1, 6):
        return "nativitas"
    if when <= date(ending, 1, 13):
        return "epiphania"
    if when < pascha - timedelta(days=63):
        return "per-annum"
    if when < pascha - timedelta(days=46):
        return "septuagesima"
    if when < pascha - timedelta(days=14):
        return "quadragesima"
    if when < pascha:
        return "passionis"
    if when <= pascha + timedelta(days=55):
        return "paschale"
    return "per-annum"


def _unrepresented_precedence(when, ending: int) -> int | None:
    """Rank first/second-class days whose ferial Mass is outside v1 scope."""

    pascha = easter(ending)
    if when == pascha - timedelta(days=46):
        return 7
    if pascha - timedelta(days=6) <= when <= pascha - timedelta(days=4):
        return 7
    if when == pascha - timedelta(days=2):
        return 2
    if pascha < when < pascha + timedelta(days=7):
        return 10
    pentecost = pascha + timedelta(days=49)
    if pentecost < when < pentecost + timedelta(days=7):
        return 10
    if when.month == 12 and 26 <= when.day <= 31:
        return 17
    if when.month == 12 and 17 <= when.day <= 23:
        return 18
    return None


def _as_day(
    when, feast: Festum, ending: int, position: str | None = None, season: str | None = None
) -> Dies:
    return Dies(
        when=when,
        formulary=feast.formulary,
        position=position or feast.formulary,
        season=season or _season(when, ending),
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
        current_precedence = (
            precedence[when] if current is not None else _unrepresented_precedence(when, ending)
        )
        if current_precedence is None:
            days[when] = _as_day(when, feast, ending)
            precedence[when] = feast.precedence
            continue

        if feast.precedence < current_precedence:
            position = (
                current.position
                if current is not None and current.position.startswith("dominica-")
                else None
            )
            season = current.season if current is not None else None
            days[when] = _as_day(when, feast, ending, position, season)
            precedence[when] = feast.precedence
            continue

        if not feast.transferable:
            continue

        # n. 96: only first-class feasts have a right of transfer, and their
        # destination must not itself be a first- or second-class day.
        if feast.formulary == "annuntiatio-beatae-mariae-virginis" and original >= easter(
            ending
        ) - timedelta(days=7):
            when = easter(ending) + timedelta(days=8)
        else:
            when += timedelta(days=1)
        while when in days or _unrepresented_precedence(when, ending) is not None:
            when += timedelta(days=1)
        days[when] = _as_day(when, feast, ending)
        precedence[when] = feast.precedence

    ordered = sorted(days.values(), key=lambda day: day.when)
    assert len({day.when for day in ordered}) == len(ordered), ending
    assert {day.formulary for day in ordered} <= FORMULARIES
    return ordered
