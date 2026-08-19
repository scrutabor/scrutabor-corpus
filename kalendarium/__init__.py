"""The temporal cycle of the 1962 Roman rite, computed once so that no app has to.

Decision #6 of this project says the calendar is built here and shipped as data:
"apps never implement movable-feast logic". There are three readers coming — the
web, Android, iOS — and a rule implemented three times is a rule that will
eventually be three different rules.

WHAT THIS KNOWS is exactly what `witnesses/raw/mr-rubricae-generales-temporale
.txt` prints, and nothing else. Every function below names the article it obeys:
n. 20 for the First Sunday of Advent, n. 30 a for the Vigil that displaces the
Fourth, n. 18 for the Sundays after Epiphany that Septuagesima cuts off, n. 17
for the four feasts that may fall on a Sunday and take its place, nn. 71-77 for
the bounds of every season.

WHAT IT DOES NOT KNOW, said plainly because a calendar that quietly guesses is
worse than one that stops: the sanctoral. A feast of the first class falling on
a Sunday of the second class takes that Sunday's place (n. 16 a), and this
module carries no list of feasts to check. So its answer is right for every
Sunday of Advent, Lent, Passiontide and Eastertide — first class, which n. 15
says yields to nothing — and is the TEMPORAL answer elsewhere, which is what a
reader is told it is.

It also does not carry the ferias. In Advent and Lent they have Masses of their
own rather than the preceding Sunday's, so naming the week is honest and naming
a formulary would not be.

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
the First Sunday of Advent. 416 of the 416 values agree. The one cell that does
not is a misprint in the table, recorded in the witness.
"""
