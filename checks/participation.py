"""Which lines the faithful themselves make, and at what degree.

The Missale assigns every answering line at low Mass to ONE person, the
minister, and says nothing at all about the people: `speaker` records that,
and it is right. It is also not what a reader in the pew needs to know. The
law that speaks to them is the Instruction *De musica sacra et sacra
liturgia* (Sacra Rituum Congregatio, 3 September 1958), transcribed in
`witnesses/raw/scr-de-musica-sacra-1958.txt`, which grades the participation
of the faithful and names the parts belonging to each degree.

Two forms of Mass, graded separately, because they are not the same event:

  * `lecta` — low Mass, n. 31. Four degrees: (a) the easier responses, by
    their own text; (b) the parts which by the rubrics are the SERVER's —
    which is exactly what `speaker: minister` records, so that degree is
    structural rather than a list; (c) the Ordinary recited with the
    celebrant; (d) the Proper, which this corpus does not carry yet.
    n. 32 adds the whole Pater noster, in Latin, with the Amen by all.
  * `cantu` — sung Mass, n. 25, extended verbatim to the Missa cantata by
    n. 26 ("eadem prorsus valent etiam pro Missa cantata"), which is the
    form most people meet: n. 26 asks that the parish Mass on Sundays and
    feasts be sung. Three degrees, and the first is NOT the same list as
    n. 31 a — it does not carry Laus tibi, Christe.

Derived here, never remembered in the files: every attribution is computed
from the text a segment prints and the speaker the witnesses gave it, and
`--check` fails if what a file carries is not what this module derives.

WHY THE SPEAKER IS PART OF THE TEST, and not the text alone: the corpus
holds eight segments reading Amen and three of them are the priest's. Two
take nothing from n. 31 a — the Amen he answers the server's Misereatur
with, and the one he says submissa voce after the Suscipiat. A rule that
read the enumeration as a list of strings would have handed the people both.
The third, the Amen closing the Pater noster, IS theirs — not by n. 31 a but
by n. 32, which gives them the whole prayer and says the Amen is added by
all. The law enumerates RESPONSES, and a response is a line answering the
celebrant, which in this corpus is a line he does not say himself.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

from checks.layout import formatted

ROOT = Path(__file__).resolve().parent.parent
LAW = "witnesses/raw/scr-de-musica-sacra-1958.txt"

# The instruction, cited the way checks/attribute.py cites the Rubricae
# generales: the document, the article, the letter.
DMS = "DMS"

# n. 31 a — "faciliora responsa liturgica", low Mass, first degree.
LECTA_I = (
    "Amen",
    "Et cum spiritu tuo",
    "Deo gratias",
    "Gloria tibi, Domine",
    "Laus tibi, Christe",
    "Habemus ad Dominum",
    "Dignum et iustum est",
    "Sed libera nos a malo",
)

# n. 25 a — the same degree at a sung Mass, and deliberately a different
# list: the instruction does not name Laus tibi, Christe among the responses
# sung by all. Reproduced as printed rather than harmonised with n. 31 a.
CANTU_I = (
    "Amen",
    "Et cum spiritu tuo",
    "Gloria tibi, Domine",
    "Habemus ad Dominum",
    "Dignum et iustum est",
    "Sed libera nos a malo",
    "Deo gratias",
)

# n. 25 b — "partes quoque ex Ordinario Missae decantant". The Kyrie stands
# here and NOT in n. 31 c: at a low Mass the people's title to it is that it
# is the server's part (n. 31 b), which its own segments already carry.
CANTU_II = (
    "ordinarium.kyrie",
    "ordinarium.gloria",
    "ordinarium.credo",
    "ordinarium.sanctus",
    "ordinarium.agnus-dei",
)

# n. 31 c — "una cum sacerdote celebrante recitant", low Mass, third degree.
LECTA_III = (
    "ordinarium.gloria",
    "ordinarium.credo",
    "ordinarium.sanctus",
    "ordinarium.agnus-dei",
)

# n. 32 — the whole Pater noster with the celebrant, at a low Mass, in Latin
# only. TOTUM Pater noster: the prayer itself, s05 to s11, and the Amen that
# n. 32 says is added by all — not Orémus and not the Præceptis salutaribus,
# which introduce the prayer and are not it. The response Sed libera nos a
# malo (s12) is the people's already, by n. 31 a.
PATER = ("ordinarium.pater-noster", ("s05", "s06", "s07", "s08", "s09", "s10", "s11", "s14"))

# The instruction legislates for the Mass. The devotional prayers this corpus
# also carries — the Leonine prayers after low Mass, the Marian antiphons —
# are outside nn. 25 and 31, and take no attribution from it: an absent
# `participation` says the sources have not been read for that segment, which
# is true of them.
MASS_CATEGORIES = {"ordinarium", "proprium"}

# n. 31 d — the fourth degree at low Mass names these four parts of the
# Proper. The Alleluia belongs to the sung third degree instead, exactly as
# n. 25 c enumerates the Proper sung by all.
LECTA_IV_PROPER = {"introitus", "graduale", "offertorium", "communio"}


def fold(text: str) -> str:
    """The corpus's own normalization: ligatures apart, accents off, j to i."""
    text = text.replace("æ", "ae").replace("Æ", "Ae").replace("œ", "oe").replace("Œ", "Oe")
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("j", "i").replace("J", "I")
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z ]", " ", text)).strip().lower()


def segment_text(seg: dict[str, Any]) -> str:
    return " ".join(w["form"] + w.get("post", "") for w in seg.get("words", []))


LECTA_I_FOLDED = {fold(x) for x in LECTA_I}
CANTU_I_FOLDED = {fold(x) for x in CANTU_I}


def derive(doc: dict[str, Any], seg: dict[str, Any]) -> dict[str, Any]:
    """What the law gives the faithful in this segment. Empty if nothing."""
    if doc.get("category") not in MASS_CATEGORIES or seg.get("type") == "rubric":
        return {}
    text_id, speaker = doc["id"], seg.get("speaker")
    said = fold(segment_text(seg))
    out: dict[str, Any] = {}

    if doc.get("category") == "proprium":
        piece = text_id.rsplit("-", 1)[-1]
        if piece in LECTA_IV_PROPER:
            out["lecta"] = {"gradus": 4, "source": f"{DMS} 31 d"}
        if doc.get("sung"):
            out["cantu"] = {"gradus": 3, "source": f"{DMS} 25 c"}
        return out

    if speaker == "minister":
        # n. 31 b covers every part the rubrics give the server; n. 31 a
        # names some of them individually, and those are the ones a reader
        # meets at every Mass, so the finer citation wins where it applies.
        if said in LECTA_I_FOLDED:
            out["lecta"] = {"gradus": 1, "source": f"{DMS} 31 a"}
        else:
            out["lecta"] = {"gradus": 2, "source": f"{DMS} 31 b"}
        if said in CANTU_I_FOLDED:
            out["cantu"] = {"gradus": 1, "source": f"{DMS} 25 a"}
        elif text_id in CANTU_II:
            out["cantu"] = {"gradus": 2, "source": f"{DMS} 25 b"}

    elif speaker == "sacerdos":
        # The celebrant's own lines are the people's only where the law says
        # they say them WITH him.
        if text_id in LECTA_III:
            out["lecta"] = {"gradus": 3, "source": f"{DMS} 31 c"}
        elif text_id == PATER[0] and seg["id"] in PATER[1]:
            # n. 32 is a faculty, not one of the four degrees, so it carries
            # no gradus: the corpus does not invent a rank the law withholds.
            out["lecta"] = {"source": f"{DMS} 32"}
        if text_id in CANTU_II:
            out["cantu"] = {"gradus": 2, "source": f"{DMS} 25 b"}

    return out


def _texts() -> list[Path]:
    return sorted(ROOT.glob("texts/*/*.json"))


def run(write: bool = False) -> int:
    """Report — or write — the participation layer. Returns a failure count."""
    if not (ROOT / LAW).exists():
        print(f"participation: FATAL the law is not archived at {LAW}")
        return 1

    problems, written, carried = 0, 0, 0
    for path in _texts():
        doc = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        for seg in doc.get("segments", []):
            want, have = derive(doc, seg), seg.get("participation")
            if want == (have or {}):
                carried += 1 if want else 0
                continue
            if write:
                if want:
                    seg["participation"] = want
                else:
                    seg.pop("participation", None)
                changed, written = True, written + 1
            else:
                problems += 1
                print(
                    f"participation: {doc['id']} {seg['id']} carries {have!r}, "
                    f"the law gives {want!r}"
                )
        if changed:
            # The corpus's own layout, not json.dumps: a text is read in
            # diffs, and one word to a line is what makes that readable
            # (checks/layout.py, which fails the suite if this drifts).
            path.write_text(formatted(doc), encoding="utf-8")

    if write:
        print(f"participation: wrote {written} segments")
        return 0
    print(f"participation: OK {carried} segments attributed, derived from {LAW}")
    return problems


if __name__ == "__main__":
    sys.exit(1 if run(write="--write" in sys.argv) else 0)


def check_doc(doc: dict[str, Any]) -> tuple[list[str], int]:
    """For run_checks: what this text carries against what the law gives."""
    errors, attributed = [], 0
    for seg in doc.get("segments", []):
        want, have = derive(doc, seg), seg.get("participation") or {}
        if want != have:
            errors.append(
                f"{seg['id']}: participation {have or 'absent'} — "
                f"the law gives {want or 'none'} (see {LAW})"
            )
        if want:
            attributed += 1
    return errors, attributed
