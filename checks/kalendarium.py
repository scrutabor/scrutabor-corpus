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
from functools import cache
from pathlib import Path

from kalendarium.computus import easter
from kalendarium.temporale import Dies, year

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


@cache
def _year(ending: int) -> tuple[Dies, ...]:
    return tuple(year(ending))


def _on(days: tuple[Dies, ...], position: str) -> date | None:
    for d in days:
        if d.position == position:
            return d.when
    return None


def computed(y: int) -> list[str]:
    """The same eight values, READ FROM THE TABLE THE READER GETS.

    Until 2026-08-19 this re-derived every value from the computus directly —
    the same functions `year()` is built from, but never `year()` itself — so
    the check printed verified=416 over a shipped table whose Pentecost had
    been moved a whole week (a planted mutation proved it). Seven of the
    eight columns now come out of `year()`'s own days, which is exactly what
    `build_reader` turns into kal.json. Ash Wednesday stays on the computus:
    the shipped table holds no ferias, and that cell verifies the arithmetic
    the year is built on. Column 8 is Advent I of this civil year, which
    OPENS the liturgical year that ends the year after — hence `_year(y + 1)`.
    """
    names = {v: k for k, v in MONTHS.items()}
    days = _year(y)

    def show(when: date | None) -> str:
        return f"{when.day} {names[when.month]}" if when else "(absent from the table)"

    pentecost = _on(days, "dominica-pentecostes")
    after = [d for d in days if pentecost and d.when > pentecost and d.when.weekday() == 6]
    return [
        show(_on(days, "dominica-in-septuagesima")),
        show(easter(y) - timedelta(days=46)),
        show(_on(days, "dominica-resurrectionis")),
        show(_on(days, "ascensio-domini")),
        show(pentecost),
        show(_on(days, "corpus-christi")),
        str(len(after)),
        show(_on(_year(y + 1), "dominica-i-adventus")),
    ]


# Where the module's own citations live. The witness header claims "no rule
# there is asserted that is not printed here", and until 2026-08-19 that was
# false: the code cited n. 69 and the article was nowhere in the file.
CITING = ("kalendarium/temporale.py", "kalendarium/computus.py", "kalendarium/__init__.py")
CHARTER = "witnesses/raw/mr-rubricae-generales-temporale.txt"


def charter(corpus: Path = ROOT) -> list[str]:
    """Every article the calendar cites must be printed in its own witness.

    The check the charter sentence needs in order to be a promise rather than
    an intention. It reads the citations out of the code — `n. 20`, `nn.
    67-69`, `n. 30 a` — and asks the witness for each number.
    """
    printed = {
        line.split(".", 1)[0]
        for line in (corpus / CHARTER).read_text(encoding="utf-8").splitlines()
        if line[:1].isdigit()
    }
    errors = []
    for name in CITING:
        text = (corpus / name).read_text(encoding="utf-8")
        for match in re.finditer(r"\bnn?\.\s*(\d+)(?:\s*-\s*(\d+))?", text):
            first, last = match.group(1), match.group(2) or match.group(1)
            for number in range(int(first), int(last) + 1):
                if str(number) not in printed:
                    errors.append(f"{name} cites n. {number}, which {CHARTER} does not print")
    return sorted(set(errors))


def check(corpus: Path = ROOT) -> tuple[list[str], int, int]:
    """Errors, values compared, and misprints met."""
    errors: list[str] = charter(corpus)
    compared = misprinted = 0
    for anno, cells in rows(corpus):
        if len(cells) != len(COLUMNS):
            errors.append(f"{TABLE}:{anno}: {len(cells)} columns, expected {len(COLUMNS)}")
            continue
        for column, printed, got in zip(COLUMNS, cells, computed(anno), strict=True):
            compared += 1
            if printed == got:
                continue
            if MISPRINTS.get((anno, column)) == printed:
                misprinted += 1
                continue
            errors.append(
                f"{TABLE}:{anno} {column}: the book prints {printed}, this computes {got}"
            )
    if not compared:
        errors.append(f"{TABLE}: no rows were read — the table is the whole verification")
    for anno, _column in MISPRINTS:
        if not any(y == anno for y, _ in rows(corpus)):
            errors.append(f"{TABLE}: {anno} is declared a misprint and is not in the table")
    return errors, compared, misprinted
