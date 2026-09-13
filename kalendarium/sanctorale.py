"""Universal first- and second-class fixed feasts in the current v1 scope.

This is deliberately not a general catalogue of saints. It is the closed
list of universal Roman observances whose formularies this edition carries
throughout the liturgical year. Their relative place against the temporal
cycle comes from the table at General Rubrics n. 91.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class Festum:
    month: int
    day: int
    formulary: str
    dies_class: int
    precedence: int
    #: A first-class feast normally moves when a higher day impedes it (n. 96).
    transferable: bool = False
    #: All Souls has the special Sunday-to-Monday rule at n. 96 b.
    monday_after_sunday: bool = False


# The numbers are the numbered places in n. 91, not invented weights:
# 4 Immaculate Conception and Assumption; 8 All Souls;
# 11 other universal I-class feasts;
# 14 feasts of the Lord II class; 16 other universal II-class feasts.
FESTA = (
    Festum(11, 30, "sancti-andreae-apostoli", 2, 16),
    Festum(12, 8, "immaculata-conceptio", 1, 4, True),
    Festum(12, 21, "sancti-thomae-apostoli", 2, 16),
    Festum(12, 26, "sancti-stephani-protomartyris", 2, 16),
    Festum(12, 27, "sancti-ioannis-apostoli-et-evangelistae", 2, 16),
    Festum(12, 28, "sanctorum-innocentium-martyrum", 2, 16),
    Festum(2, 2, "purificatio-beatae-mariae-virginis", 2, 14),
    Festum(2, 22, "cathedra-sancti-petri", 2, 16),
    Festum(2, 24, "sancti-matthiae-apostoli", 2, 16),
    Festum(3, 19, "sancti-ioseph-sponsi-beatae-mariae-virginis", 1, 11, True),
    Festum(3, 25, "annuntiatio-beatae-mariae-virginis", 1, 11, True),
    Festum(4, 25, "sancti-marci-evangelistae", 2, 16),
    Festum(5, 1, "sancti-ioseph-opificis", 1, 11, True),
    Festum(5, 11, "sanctorum-philippi-et-iacobi-apostolorum", 2, 16),
    Festum(5, 31, "beata-maria-virgo-regina", 2, 16),
    Festum(6, 24, "nativitas-sancti-ioannis-baptistae", 1, 11, True),
    Festum(6, 29, "sancti-petri-et-pauli-apostolorum", 1, 11, True),
    Festum(7, 1, "pretiosissimi-sanguinis-domini-nostri-iesu-christi", 1, 11, True),
    Festum(7, 2, "visitatio-beatae-mariae-virginis", 2, 16),
    Festum(7, 25, "sancti-iacobi-apostoli", 2, 16),
    Festum(7, 26, "sanctae-annae-matris-beatae-mariae-virginis", 2, 16),
    Festum(8, 6, "transfiguratio-domini", 2, 14),
    Festum(8, 10, "sancti-laurentii-martyris", 2, 16),
    Festum(8, 15, "assumptio-beatae-mariae-virginis", 1, 4, True),
    Festum(8, 16, "sancti-ioachim-confessoris", 2, 16),
    Festum(8, 22, "immaculatum-cor-beatae-mariae-virginis", 2, 16),
    Festum(8, 24, "sancti-bartholomaei-apostoli", 2, 16),
    Festum(9, 8, "nativitas-beatae-mariae-virginis", 2, 16),
    Festum(9, 14, "exaltatio-sanctae-crucis", 2, 14),
    Festum(9, 15, "septem-dolorum-beatae-mariae-virginis", 2, 16),
    Festum(9, 21, "sancti-matthaei-apostoli-et-evangelistae", 2, 16),
    Festum(9, 29, "dedicatio-sancti-michaelis-archangeli", 1, 11, True),
    Festum(10, 7, "beatae-mariae-virginis-a-rosario", 2, 16),
    Festum(10, 11, "maternitas-beatae-mariae-virginis", 2, 16),
    Festum(10, 18, "sancti-lucae-evangelistae", 2, 16),
    Festum(10, 28, "sanctorum-simonis-et-iudae-apostolorum", 2, 16),
    Festum(11, 1, "omnium-sanctorum", 1, 11, True),
    Festum(
        11,
        2,
        "commemoratio-omnium-fidelium-defunctorum",
        1,
        8,
        monday_after_sunday=True,
    ),
    Festum(11, 9, "dedicatio-archibasilicae-sanctissimi-salvatoris", 2, 14),
)

FORMULARIES = frozenset(feast.formulary for feast in FESTA)


def _advent_start(civil_year: int) -> date:
    """The Sunday from 27 November through 3 December."""

    latest = date(civil_year, 12, 3)
    return latest - timedelta(days=(latest.weekday() + 1) % 7)


def occurrences(ending: int) -> list[tuple[date, Festum]]:
    """The fixed observances falling inside one complete liturgical year."""

    out: list[tuple[date, Festum]] = []
    start = _advent_start(ending - 1)
    end = _advent_start(ending) - timedelta(days=1)
    for civil_year in (ending - 1, ending):
        for feast in FESTA:
            when = date(civil_year, feast.month, feast.day)
            if feast.monday_after_sunday and when.weekday() == 6:
                # n. 96 b calls the following Monday its proper transferred seat.
                when += timedelta(days=1)
            if start <= when <= end:
                out.append((when, feast))
    return sorted(out, key=lambda row: row[0])
