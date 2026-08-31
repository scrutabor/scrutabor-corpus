"""The supported 1962 Roman calendar, computed once so that no app has to.

Decision #6 of this project says the calendar is built here and shipped as data:
"apps never implement movable-feast logic". There are three readers coming — the
web, Android, iOS — and a rule implemented three times is a rule that will
eventually be three different rules.

WHAT THIS KNOWS is exactly what `witnesses/raw/mr-rubricae-generales-temporale
.txt` and `witnesses/raw/mr-rubricae-generales-occurrence.txt` print, and
nothing else. Every function below names the article it
obeys: n. 20 for the First Sunday of Advent, n. 30 for the two vigils of the
first class, n. 18 for the Sundays after Epiphany that Septuagesima cuts off,
n. 17 for the four feasts that may fall on a Sunday and take its place, nn.
67-69 for the octave of the Nativity and the Sunday inside it, nn. 71-77 for
the bounds of every season.

THE SANCTORAL IS DELIBERATELY BOUNDED. It carries the universal first- and
second-class observances from 31 May through 9 November whose formularies are
in the current Sundays-and-major-feasts scope. It does not pretend to be the
complete General Roman Calendar. The Immaculate Conception remains in the
temporal computation because n. 15 states its exceptional precedence over an
Advent Sunday there.

WHAT IT DOES NOT KNOW, said plainly because a calendar that quietly guesses is
worse than one that stops:

- SANCTORAL OBSERVANCES OUTSIDE THE DECLARED V1 RANGE, including local and
  particular calendars and universal feasts of the third class.
- THE FERIAS. They have no entry, and the reason differs by season: in Lent
  the Missale prints a Mass for every day of the week, and in Advent it prints
  none between one Sunday and the next. Naming the week is true of both;
  naming a formulary would need the first and would be wrong about the second.
- THE SUNDAY WITHIN THE OCTAVE WHEN CHRISTMAS IS A SUNDAY. n. 69 governs the
  Sunday that occurs between 26 and 31 December, and in ten years of this
  window none does. The Mass is then said on 30 December, by a rule n. 70
  sends to "rubricis Breviarii et Missalis" — the Missale's own rubrics for
  the octave, which this edition has not transcribed. Ten years are therefore
  short one day: 2033, 2039, 2044, 2050, 2061, 2067, 2072, 2078, 2089, 2095.
- 13 JANUARY, the Commemoration of the Baptism of the Lord, which closes the
  season n. 72 b bounds and which no article transcribed here assigns.

ONE CONCLUSION IS DERIVED RATHER THAN PRINTED, and is flagged here because a
reviewer should be able to challenge it. n. 18 puts a leftover Sunday after
Epiphany at the twenty-fourth place after Pentecost; n. 17 d puts Christ the
King on the last Sunday of October; in a long year those are the same Sunday,
and n. 14 — "Officium et Missa dominicae impeditae nec anticipantur nec
resumuntur" — settles which survives. So in fourteen years of the hundred and
forty computed, one post-Epiphany Mass is not said at all. Nothing states this
in so many words; it follows from the three articles together.

VERIFIED AGAINST THE BOOK: the Missale prints its own TABELLA TEMPORARIA
FESTORUM MOBILIUM for 1960-2011, and `checks/kalendarium.py` holds this
computation against all 52 rows of it — Septuagesima, Ash Wednesday, Easter,
Ascension, Pentecost, Corpus Christi, the count of Sundays after Pentecost and
the First Sunday of Advent. 415 of the 416 values agree, and the one that does
not is a misprint in the table, recorded in the witness and named in the
check.
"""
