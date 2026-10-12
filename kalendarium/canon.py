"""Explicit Canon choices for the Mass/date pairs carried by the edition.

The proper prayers belong to a named Mass or a prescribed date range, not
to its preface or the reader's clock. Missale Romanum (1962), RG 501 and
the proper rubrics on pp. 18, 38, 161, 215, 304–305, 346 and 349 control
these temporal profiles. Episcopal ritual forms are outside this catalogue.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from kalendarium.computus import easter

SCHEMA = "1.0.0"
ROLES = ("communicantes", "hanc-igitur", "qui-pridie")
_ORDINARY = (
    "ordinarium.communicantes",
    "ordinarium.hanc-igitur",
    "ordinarium.qui-pridie",
)
_BAPTISMAL_HANC = "ordinarium.hanc-igitur-paschale"

# The tuple order is the explicit role order above, not a suffix-based guess.
# Ordinary bodies are named positively: missing data never means ordinary.
PROFILES = {
    "ordinary": _ORDINARY,
    "nativitas-in-nocte": (
        "ordinarium.communicantes-in-nativitate-domini-in-nocte",
        _ORDINARY[1],
        _ORDINARY[2],
    ),
    "nativitas-in-die": (
        "ordinarium.communicantes-in-nativitate-domini-in-die",
        _ORDINARY[1],
        _ORDINARY[2],
    ),
    "epiphania": (
        "ordinarium.communicantes-in-epiphania-domini",
        _ORDINARY[1],
        _ORDINARY[2],
    ),
    "in-cena-domini": (
        "ordinarium.communicantes-in-cena-domini",
        "ordinarium.hanc-igitur-in-cena-domini",
        "ordinarium.qui-pridie-in-cena-domini",
    ),
    "pascha-in-nocte": (
        "ordinarium.communicantes-in-nocte-paschae",
        _BAPTISMAL_HANC,
        _ORDINARY[2],
    ),
    "pascha-in-die": (
        "ordinarium.communicantes-in-die-paschae",
        _BAPTISMAL_HANC,
        _ORDINARY[2],
    ),
    "ascensio": (
        "ordinarium.communicantes-in-ascensione-domini",
        _ORDINARY[1],
        _ORDINARY[2],
    ),
    "pentecostes": (
        "ordinarium.communicantes-in-pentecoste",
        _BAPTISMAL_HANC,
        _ORDINARY[2],
    ),
}


def _profile_id(when: date, mass: str) -> str:
    """Source rule for an already validated Mass/date pair.

    Not a resolver for arbitrary requests: the exported table below contains
    only pairs the edition actually represents. In particular, Chrism and
    unspecified ferial/votive/ritual Masses must not be invented by a caller.
    """
    if (when.month == 12 and when.day >= 25) or (when.month == 1 and when.day == 1):
        # p. 18: the first named Nativity Mass alone uses noctem. RG 501
        # extends the day form to other Masses in the prescribed octave.
        return "nativitas-in-nocte" if mass == "nativitas-domini-in-nocte" else "nativitas-in-die"
    if when.month == 1 and when.day == 6:
        # p. 38: feast only; the longer proper-preface period is not this rule.
        return "epiphania"

    offset = (when - easter(when.year)).days
    if offset == -3 and mass == "feria-v-in-cena-domini":
        # The evening Mass, not a date-wide replacement for the Chrism Mass.
        return "in-cena-domini"
    if offset == -1 and mass == "vigilia-paschalis":
        return "pascha-in-nocte"
    if 0 <= offset <= 6:
        # Through Saturday in albis, not Low Sunday (pp. 304–305).
        return "pascha-in-die"
    if offset == 39:
        # p. 346 explicitly excludes subsequent ferial reuse from proper C.
        return "ascensio"
    if 48 <= offset <= 55:
        # Vigil through octave Saturday inclusive; Trinity is outside it.
        return "pentecostes"
    return "ordinary"


def calendar_table(formularies: list[dict], calendar: dict) -> dict:
    """Compile every supported pair, including explicit ordinary decisions.

    Uses the same already computed calendar and authored Mass catalogue as
    the reader. No additional calendar arithmetic is shipped to an app.
    `missa=none` is the reader's separate Ordinary-only choice, never a Mass.
    """
    by_calendar: dict[str, list[str]] = defaultdict(list)
    masses: list[str] = []
    for formulary in formularies:
        mass = formulary["id"]
        if not isinstance(mass, str) or not mass or mass == "none" or mass in masses:
            raise ValueError(f"Invalid or duplicate Mass identity: {mass}")
        masses.append(mass)
        by_calendar[formulary["calendar"]["key"]].append(mass)
    masses.sort()
    mass_index = {mass: index for index, mass in enumerate(masses)}
    profiles = list(PROFILES)
    profile_index = {profile: index for index, profile in enumerate(profiles)}
    pairs: list[list] = []
    seen: set[tuple[str, str]] = set()
    seen_days: set[str] = set()
    keys = calendar["formularies"]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate calendar identity")
    for days in calendar["years"].values():
        for row in days:
            day, key_index = row[:2]
            when = date.fromisoformat(day)
            if when.isoformat() != day:
                raise ValueError(f"Noncanonical civil date: {day}")
            if day in seen_days:
                raise ValueError(f"Duplicate calendar date: {day}")
            seen_days.add(day)
            if type(key_index) is not int or not 0 <= key_index < len(keys):
                raise ValueError(f"Invalid calendar identity index: {key_index}")
            key = keys[key_index]
            if key not in by_calendar:
                raise ValueError(f"No represented Mass for calendar identity: {key}")
            for mass in by_calendar[key]:
                pair = (day, mass)
                if pair in seen:
                    raise ValueError(f"Duplicate Mass/date pair: {pair}")
                seen.add(pair)
                pairs.append([day, mass_index[mass], profile_index[_profile_id(when, mass)]])
    pairs.sort()
    return {
        "schema_version": SCHEMA,
        "roles": list(ROLES),
        "profiles": [
            {"id": key, "texts": dict(zip(ROLES, value, strict=True))}
            for key, value in PROFILES.items()
        ],
        "masses": masses,
        "pairs": pairs,
    }
