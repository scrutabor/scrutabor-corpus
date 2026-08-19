"""The temporal cycle: which day of the year's own reckoning a date is.

One liturgical year runs from the First Sunday of Advent to the Saturday before
the next (n. 77 draws exactly that line). `year(n)` builds the one that ENDS in
civil year n, which is how the Missale's own table is arranged.

Every day this returns is a day with a Mass of its own in the temporal cycle:
the Sundays, and the feasts of the Lord that belong to the season rather than to
the sanctoral. Ferias are deliberately absent — in Advent and Lent they have
Masses of their own rather than the Sunday's, so listing them under a Sunday
would be a claim this module has no authority for, and listing them empty would
say nothing the season does not already say.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from kalendarium.computus import advent_i, easter

ROMAN = [
    "",
    "i",
    "ii",
    "iii",
    "iv",
    "v",
    "vi",
    "vii",
    "viii",
    "ix",
    "x",
    "xi",
    "xii",
    "xiii",
    "xiv",
    "xv",
    "xvi",
    "xvii",
    "xviii",
    "xix",
    "xx",
    "xxi",
    "xxii",
    "xxiii",
    "xxiv",
    "xxv",
    "xxvi",
    "xxvii",
    "xxviii",
]

# EVERY formulary of the temporal cycle this module may name, and no others.
#
# A closed list because the alternative was proved useless: a first draft
# checked only that no formulary was said twice in a year, and an off-by-one in
# n. 18's transfer then produced `dominica-vii-post-epiphaniam` -- a Mass the
# Missale does not contain -- once a year for a hundred and forty years without
# a single complaint. Membership is the check that has teeth.
#
# The names are the book's own inscriptions, slugged: DOMINICA I IN
# QUADRAGESIMA, DOMINICA II PASSIONIS SEU IN PALMIS, DOMINICA IN ALBIS.
FORMULARIES = frozenset(
    [f"dominica-{ROMAN[i]}-adventus" for i in range(1, 5)]
    + ["vigilia-nativitatis", "nativitas-domini", "dominica-infra-octavam-nativitatis"]
    + ["sanctissimi-nominis-iesu", "epiphania-domini", "sancta-familia"]
    + [f"dominica-{ROMAN[i]}-post-epiphaniam" for i in range(1, 7)]
    + [f"dominica-in-{n}" for n in ("septuagesima", "sexagesima", "quinquagesima")]
    + [f"dominica-{ROMAN[i]}-in-quadragesima" for i in range(1, 5)]
    + ["dominica-i-passionis", "dominica-ii-passionis"]
    + ["dominica-resurrectionis", "dominica-in-albis"]
    + [f"dominica-{ROMAN[i]}-post-pascha" for i in range(2, 6)]
    + ["ascensio-domini", "dominica-post-ascensionem", "dominica-pentecostes"]
    + ["sanctissimae-trinitatis", "corpus-christi", "d-n-iesu-christi-regis"]
    + [f"dominica-{ROMAN[i]}-post-pentecosten" for i in range(2, 25)]
)

# The seasons, as nn. 71-77 bound them. `natalicium` and `quadragesimale` are
# the law's own umbrella names; the parts it distinguishes inside them are what
# a reader is shown, so those are the values used.
SEASONS = (
    "adventus",
    "nativitas",
    "epiphania",
    "per-annum",
    "septuagesima",
    "quadragesima",
    "passionis",
    "paschale",
)


@dataclass(frozen=True)
class Dies:
    """One day of the temporal cycle that has a Mass of its own."""

    when: date
    #: the formulary said on the day, which is not always the day's own name:
    #: n. 18 sends leftover Sundays after Epiphany to the end of the year, and
    #: n. 17 gives four Sundays to feasts that take their place.
    formulary: str
    #: what the day IS in the year's order. Usually the same string as the
    #: formulary, and deliberately still written out when it is: a field that
    #: is empty when nothing interesting happened makes every reader of it
    #: write the same `or`, and one of them will forget. `transferred` is the
    #: question people actually ask.
    position: str
    season: str
    #: n. 10-12 and n. 8: first or second class. A first-class Sunday yields to
    #: nothing (n. 15), which is what makes this module's answer complete for it.
    dies_class: int

    @property
    def transferred(self) -> bool:
        """True when the Mass said is not the one the day is named for."""
        return self.formulary != self.position


def _sundays(start: date, stop: date) -> list[date]:
    """Every Sunday from `start` up to but not including `stop`."""
    first = start + timedelta(days=(6 - start.weekday()) % 7)
    out = []
    while first < stop:
        out.append(first)
        first += timedelta(days=7)
    return out


def _last_sunday_of_october(y: int) -> date:
    last = date(y, 10, 31)
    return last - timedelta(days=(last.weekday() + 1) % 7)


def year(ending: int) -> list[Dies]:
    """The liturgical year that ends in civil year `ending`, day by day."""
    begins = advent_i(ending - 1)
    pascha = easter(ending)
    next_advent = advent_i(ending)
    days: list[Dies] = []

    def add(when: date, formulary: str, season: str, dies_class: int, position: str = "") -> None:
        days.append(Dies(when, formulary, position or formulary, season, dies_class))

    # ADVENT — n. 71, and all four Sundays are I class (n. 11 a).
    christmas = date(ending - 1, 12, 25)
    for i in range(4):
        when = begins + timedelta(days=7 * i)
        name = f"dominica-{ROMAN[i + 1]}-adventus"
        # n. 30 a: the Vigil of the Nativity, when it falls on the Fourth
        # Sunday, takes its place and no commemoration is made of it.
        if when == christmas - timedelta(days=1):
            add(when, "vigilia-nativitatis", "adventus", 1, name)
        else:
            add(when, name, "adventus", 1)

    # CHRISTMASTIDE — n. 72: from Christmas to 13 January, in two parts.
    add(christmas, "nativitas-domini", "nativitas", 1)
    for when in _sundays(date(ending - 1, 12, 26), date(ending - 1, 12, 32 - 1)):
        # n. 69: the Sunday between 26 and 31 December has its own Office.
        add(when, "dominica-infra-octavam-nativitatis", "nativitas", 2)
    # n. 17 a: the Most Holy Name of Jesus, on the Sunday falling between 2 and
    # 5 January. On a year with no such Sunday it is kept on 2 January, which
    # is a weekday and so outside what this list carries.
    for when in _sundays(date(ending, 1, 2), date(ending, 1, 6)):
        add(when, "sanctissimi-nominis-iesu", "nativitas", 2)
    epiphany = date(ending, 1, 6)
    add(epiphany, "epiphania-domini", "epiphania", 1)

    # THE SUNDAYS AFTER EPIPHANY. The first of them is the Holy Family (n. 17 b)
    # and takes the Sunday's place; the rest are numbered from II, and those
    # Septuagesima cuts off are not lost but moved (n. 18, applied below).
    septuagesima = pascha - timedelta(days=63)
    after_epiphany = _sundays(epiphany + timedelta(days=1), septuagesima)
    for index, when in enumerate(after_epiphany):
        season = "epiphania" if when <= date(ending, 1, 13) else "per-annum"
        if index == 0:
            add(when, "sancta-familia", season, 2, "dominica-i-post-epiphaniam")
        else:
            add(when, f"dominica-{ROMAN[index + 1]}-post-epiphaniam", season, 2)
    used_after_epiphany = len(after_epiphany)

    # SEPTUAGESIMA — n. 73 — and LENT — n. 74.
    for offset, name in ((63, "septuagesima"), (56, "sexagesima"), (49, "quinquagesima")):
        add(pascha - timedelta(days=offset), f"dominica-in-{name}", "septuagesima", 2)
    for i in range(4):
        when = pascha - timedelta(days=42 - 7 * i)
        add(when, f"dominica-{ROMAN[i + 1]}-in-quadragesima", "quadragesima", 1)
    add(pascha - timedelta(days=14), "dominica-i-passionis", "passionis", 1)
    add(pascha - timedelta(days=7), "dominica-ii-passionis", "passionis", 1)

    # EASTERTIDE — n. 76.
    add(pascha, "dominica-resurrectionis", "paschale", 1)
    add(pascha + timedelta(days=7), "dominica-in-albis", "paschale", 1)
    for i in range(2, 6):
        add(pascha + timedelta(days=7 * i), f"dominica-{ROMAN[i]}-post-pascha", "paschale", 2)
    add(pascha + timedelta(days=39), "ascensio-domini", "paschale", 1)
    add(pascha + timedelta(days=42), "dominica-post-ascensionem", "paschale", 2)
    add(pascha + timedelta(days=49), "dominica-pentecostes", "paschale", 1)

    # AFTER PENTECOST. Trinity is the First Sunday after Pentecost (n. 17 c),
    # and the count that decides n. 18's transfer runs from it.
    trinity = pascha + timedelta(days=56)
    positions = _sundays(trinity, next_advent)
    total = len(positions)
    king = _last_sunday_of_october(ending)
    # n. 18: the last Sunday always says the XXIV, and the Sundays between the
    # XXIII and the last say the post-Epiphany formularies Septuagesima cut
    # off, in their own order. `spare` is how many of those there are.
    spare = max(0, total - 24)
    for index, when in enumerate(positions, start=1):
        position = f"dominica-{ROMAN[index]}-post-pentecosten"
        if index == 1:
            formulary, dies_class = "sanctissimae-trinitatis", 1
        elif index == total:
            formulary, dies_class = "dominica-xxiv-post-pentecosten", 2
        elif index > 23:
            formulary = f"dominica-{ROMAN[6 - (spare - (index - 23))]}-post-epiphaniam"
            dies_class = 2
        else:
            formulary, dies_class = position, 2
        # n. 17 d: Christ the King on the last Sunday of October takes the
        # place of the Sunday, which keeps its own position in the count.
        if when == king:
            formulary, dies_class = "d-n-iesu-christi-regis", 1
        add(when, formulary, "per-annum", dies_class, position)
    add(pascha + timedelta(days=60), "corpus-christi", "per-annum", 1)

    unknown = sorted({d.formulary for d in days} - FORMULARIES)
    assert not unknown, f"{ending}: the Missale has no such Mass: {unknown}"
    # A leftover post-Epiphany formulary can only be said once. The Sundays
    # that DID occur used II upwards; the transfer uses VI downwards, and the
    # two must not meet.
    said = [d.formulary for d in days]
    assert len(said) == len(set(said)), f"{ending}: a formulary is said twice"
    assert used_after_epiphany + spare <= 6, (
        f"{ending}: {used_after_epiphany}+{spare} Sundays after Epiphany"
    )

    days.sort(key=lambda d: d.when)
    assert days[0].when == begins
    return days


def sundays_after_pentecost(ending: int) -> int:
    """How many Sundays the year holds after Pentecost, Trinity counted first.

    The Missale prints this number for every year of its own table, which is
    what makes n. 18's transfer checkable rather than merely implemented.
    """
    return len(_sundays(easter(ending) + timedelta(days=56), advent_i(ending)))
