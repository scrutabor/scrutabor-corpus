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

# Exact supported temporal class-I identities at n. 91, places 1-6 and 9.
# The Paschal Vigil route is attached to Holy Saturday (Easter-1), a day of
# the sacred Triduum, not a liturgical vigil of the Pentecost-Vigil place.
_FIRST_CLASS_TEMPORAL_PRECEDENCE = {
    "nativitas-domini": 1,
    "dominica-resurrectionis": 1,
    "dominica-pentecostes": 1,
    "feria-v-in-cena-domini": 2,
    "vigilia-paschalis": 2,
    "epiphania-domini": 3,
    "ascensio-domini": 3,
    "sanctissimae-trinitatis": 3,
    "corpus-christi": 3,
    "sacratissimi-cordis-iesu": 3,
    "d-n-iesu-christi-regis": 3,
    "immaculata-conceptio": 4,
    "vigilia-nativitatis": 5,
    "in-octava-nativitatis": 5,
    "dominica-i-adventus": 6,
    "dominica-ii-adventus": 6,
    "dominica-iii-adventus": 6,
    "dominica-iv-adventus": 6,
    "dominica-i-in-quadragesima": 6,
    "dominica-ii-in-quadragesima": 6,
    "dominica-iii-in-quadragesima": 6,
    "dominica-iv-in-quadragesima": 6,
    "dominica-i-passionis": 6,
    "dominica-ii-passionis": 6,
    "dominica-in-albis": 6,
    "vigilia-pentecostes": 9,
}


def _temporal_precedence(day: Dies) -> int:
    """Return the numbered place of a temporal day in the table at n. 91."""

    # n. 91, place 21; nn. 31-33: this named weekday vigil never becomes
    # a Sunday or acquires the first-class vigil precedence.
    if day.formulary == "vigilia-ascensionis":
        if (
            day.position != day.formulary
            or day.dies_class != 2
            or day.season != "paschale"
            or day.when.weekday() != 2
            or day.when != easter(day.when.year) + timedelta(days=38)
        ):
            raise ValueError(
                "calendar: Ascension Vigil requires its own Easter+38 Wednesday of class II"
            )
        return 21
    if day.dies_class == 1:
        if day.formulary not in _FIRST_CLASS_TEMPORAL_PRECEDENCE:
            raise ValueError("calendar: unsupported first-class temporal identity")
        return _FIRST_CLASS_TEMPORAL_PRECEDENCE[day.formulary]
    if day.position.startswith("dominica-"):
        return 15
    # Other second-class temporal days retain the existing place. The named
    # Ascension Vigil has its explicit table place above, not this fallback.
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

        # The temporal cycle already contains the Immaculate Conception when
        # it replaces Advent II. A second entry for that SAME observance is
        # not a collision and must not transfer it again at equal precedence.
        if current is not None and current.formulary == feast.formulary:
            if current.dies_class != feast.dies_class or current_precedence != feast.precedence:
                raise ValueError("calendar: repeated observance has inconsistent class/precedence")
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
