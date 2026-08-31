"""Universal first- and second-class feasts in the current v1 scope.

This is deliberately not a general catalogue of saints.  It is the closed
list of universal Roman observances whose formularies this edition carries
between Trinity Sunday and the Saturday before Advent.  Their relative place
against the temporal cycle comes from the table at General Rubrics n. 91.
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
# 4 Assumption; 8 All Souls; 11 other universal I-class feasts;
# 14 feasts of the Lord II class; 16 other universal II-class feasts.
FESTA = (
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


def occurrences(ending: int) -> list[tuple[date, Festum]]:
    """The fixed observances falling in the civil year that ends the cycle."""

    out: list[tuple[date, Festum]] = []
    for feast in FESTA:
        when = date(ending, feast.month, feast.day)
        if feast.monday_after_sunday and when.weekday() == 6:
            # n. 96 b calls the following Monday its proper transferred seat.
            when += timedelta(days=1)
        out.append((when, feast))
    return out
