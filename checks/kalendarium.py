"""The computed calendar, held against the table the Missale prints itself.

A calendar is the one layer of this edition a reader will check against their
own parish before they check anything else, and a wrong Sunday is visible to
everyone. So it is not verified against a modern almanac — which would agree
for reasons of its own arithmetic — but against the TABELLA TEMPORARIA FESTORUM
MOBILIUM bound into the 1962 Missale, transcribed at
`witnesses/raw/mr-tabella-temporaria.txt`, which gives fifty-two years of
Septuagesima, Ash Wednesday, Easter, Ascension, Pentecost, Corpus Christi, the
count of Sundays after Pentecost and the First Sunday of Advent.

416 values. One of them is a misprint in the book, recorded as a corrigendum in
the witness and declared here by year rather than skipped quietly.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

from kalendarium.computus import advent_i, easter
from kalendarium.temporale import sundays_after_pentecost

ROOT = Path(__file__).resolve().parent.parent
TABLE = "witnesses/raw/mr-tabella-temporaria.txt"

MONTHS = {
    "ian.": 1,
    "febr.": 2,
    "mart.": 3,
    "apr.": 4,
    "maii": 5,
    "iunii": 6,
    "nov.": 11,
    "dec.": 12,
}

# The 1996 cell of the "Domin. post Pentec." column prints 16, and the count
# cannot fall below 23. Named here so that the check still reads the cell and
# still says what it found, rather than passing over the row in silence.
MISPRINTS = {(1996, "dominicae post Pentecosten"): "16"}

COLUMNS = (
    "Septuagesima",
    "dies cinerum",
    "Pascha",
    "Ascensio",
    "Pentecostes",
    "Corpus Christi",
    "dominicae post Pentecosten",
    "dominica I Adventus",
)


def _day(cell: str, year: int) -> date:
    number, month = cell.split()
    return date(year, MONTHS[month], int(number))


def rows(corpus: Path) -> list[tuple[int, list[str]]]:
    out = []
    for line in (corpus / TABLE).read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        cells = re.split(r"\s{2,}", line.strip())
        out.append((int(cells[0]), cells[1:]))
    return out


def computed(year: int) -> list[str]:
    """The same eight values, from `kalendarium`, spelled as the book spells them."""
    names = {v: k for k, v in MONTHS.items()}
    pascha, advent = easter(year), advent_i(year)

    def show(when: date) -> str:
        return f"{when.day} {names[when.month]}"

    return [
        show(pascha - timedelta(days=63)),
        show(pascha - timedelta(days=46)),
        show(pascha),
        show(pascha + timedelta(days=39)),
        show(pascha + timedelta(days=49)),
        show(pascha + timedelta(days=60)),
        str(sundays_after_pentecost(year)),
        show(advent),
    ]


def check(corpus: Path = ROOT) -> tuple[list[str], int, int]:
    """Errors, values compared, and misprints met."""
    errors: list[str] = []
    compared = misprinted = 0
    for year, cells in rows(corpus):
        if len(cells) != len(COLUMNS):
            errors.append(f"{TABLE}:{year}: {len(cells)} columns, expected {len(COLUMNS)}")
            continue
        for column, printed, got in zip(COLUMNS, cells, computed(year), strict=True):
            compared += 1
            if printed == got:
                continue
            if MISPRINTS.get((year, column)) == printed:
                misprinted += 1
                continue
            errors.append(
                f"{TABLE}:{year} {column}: the book prints {printed}, this computes {got}"
            )
    if not compared:
        errors.append(f"{TABLE}: no rows were read — the table is the whole verification")
    for year, _column in MISPRINTS:
        if not any(y == year for y, _ in rows(corpus)):
            errors.append(f"{TABLE}: {year} is declared a misprint and is not in the table")
    return errors, compared, misprinted
