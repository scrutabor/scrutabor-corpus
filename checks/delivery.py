"""Form-specific ritual delivery of a segment.

The corpus stores the low-Mass delivery in ``speaker`` and ``voice``. Proper
chants are the systematic exception at a sung Mass: the schola sings what the
celebrant reads aloud at low Mass. This module derives that exception from the
liturgical genus, so individual formularies cannot drift between the two
models.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from checks import ritual
from checks.layout import formatted
from checks.office import base_errors, is_office
from checks.office import sung_delivery as office_delivery
from checks.orations import PREFACE as PREFACE_DIALOGUE
from checks.orations import structure, sung_delivery, tokens
from checks.participation import CANTU_III_PROPER, proper_genus

ROOT = Path(__file__).resolve().parent.parent

# The Preface dialogue. RG 511 h gives the Preface an audible low-Mass base:
# the celebrant says his three calls and the server answers, all clara.
# RG 513 a has the celebrant sing the Preface at a solemn Mass and RG 514
# extends that to the Missa cantata; DMS 16 b has the schola and people
# answer him in the prescribed melody, and DMS 25 a and 26 name these three
# answers among those sung by all the faithful. The answers take the actor
# an oration's sung Amen has (checks.orations.sung_delivery), schola, and
# the faithful's part stays in their separately derived DMS participation.
#
# The rule is bound to this one text and its printed six verses, never to
# their words. Dominus vobiscum and Et cum spiritu tuo stand elsewhere too,
# among other places at the foot of the altar (the versicles RG 513 a
# excepts), at the dismissal and before the Last Gospel, and an Oremus opens
# Aufer a nobis: none of them takes anything from this rule. Each row is the
# segment, its low-Mass speaker, its sung performer and its printed words;
# the word ids run on from w001 without a gap. A stored text that differs
# from these rows in any of them is reported and receives no override,
# rather than having its labels copied into the sung form.
PREFACE_DIALOGUE_VERSES: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("s02", "sacerdos", "sacerdos", ("dominus", "vobiscum")),
    ("s03", "minister", "schola", ("et", "cum", "spiritu", "tuo")),
    ("s04", "sacerdos", "sacerdos", ("sursum", "corda")),
    ("s05", "minister", "schola", ("habemus", "ad", "dominum")),
    ("s06", "sacerdos", "sacerdos", ("gratias", "agamus", "domino", "deo", "nostro")),
    ("s07", "minister", "schola", ("dignum", "et", "iustum", "est")),
)

# The Preface itself. RG 511 h lists the Preface among what the celebrant
# says clara voce at low Mass; RG 513 a has him sing the Per omnia saecula
# saeculorum with the Preface at a solemn Mass, and RG 514 extends that to
# the Missa cantata. Every verse of every Preface the formularies select is
# therefore the celebrant's in both forms: sacerdos/clara at low Mass, and
# sacerdos/cantus when the Mass is sung. The rule adds no participation of
# the faithful.
#
# As with the dialogue, the rule is bound to a closed inventory, never to
# words. Each row gives the number of the first verse segment and the word
# count of every verse; the verse segments follow one another, and their
# word ids run on from w001 without a gap. A Preface whose verses begin at
# s02 opens with the hand rubric s01; the three Paschal Prefaces carry no
# such rubric, and their single verse is s01. A stored Preface that differs
# from its row is reported and receives no override, and a Preface id
# without a row is reported rather than left unmodeled in silence. Other
# texts take nothing from this rule, whatever their words.
PREFACE_PREFIX = "ordinarium.praefatio-"
PREFACE_BODIES: dict[str, tuple[int, tuple[int, ...]]] = {
    "apostolorum": (2, (8, 19, 12, 22)),
    "ascensionis": (2, (70,)),
    "beatae-mariae-virginis": (2, (15, 6, 12, 20, 10, 9, 12)),
    "beatae-mariae-virginis-in-annuntiatione": (2, (15, 6, 12, 20, 10, 9, 12)),
    "beatae-mariae-virginis-in-assumptione": (2, (15, 6, 12, 20, 10, 9, 12)),
    "beatae-mariae-virginis-in-conceptione-immaculata": (2, (15, 6, 13, 20, 10, 9, 12)),
    "beatae-mariae-virginis-in-nativitate": (2, (15, 6, 12, 20, 10, 9, 12)),
    "beatae-mariae-virginis-in-transfixione": (2, (15, 6, 12, 20, 10, 9, 12)),
    "beatae-mariae-virginis-in-visitatione": (2, (15, 6, 12, 20, 10, 9, 12)),
    "communis": (2, (15, 10, 10, 9, 12)),
    "d-n-iesu-christi-regis": (2, (15, 6, 57, 22)),
    "defunctorum": (2, (15, 10, 18, 19, 22)),
    "epiphaniae": (2, (15, 6, 15, 22)),
    "nativitatis": (2, (15, 6, 24, 22)),
    "paschalis": (1, (65,)),
    "paschalis-in-die": (1, (66,)),
    "paschalis-in-nocte": (1, (66,)),
    "quadragesimae": (2, (15, 6, 15, 10, 9, 12)),
    "sacratissimi-cordis-iesu": (2, (15, 6, 37, 22)),
    "sanctae-crucis": (2, (15, 6, 28, 10, 9, 12)),
    "sancti-ioseph-in-festivitate": (2, (15, 6, 12, 35, 10, 9, 12)),
    "sancti-ioseph-in-solemnitate": (2, (15, 6, 12, 35, 10, 9, 12)),
    "sanctissimae-trinitatis": (2, (15, 6, 24, 20, 19, 17)),
    "spiritus-sancti": (2, (66,)),
}
assert all(first in (1, 2) and counts for first, counts in PREFACE_BODIES.values())

# The solemn Passion has three traditional parts.  The printed role sequence
# is fixed here independently of the text files, just as the chant genera
# below are fixed independently of their stored overrides.  At low Mass the
# celebrant reads every part, which remains the base ``speaker`` in the text.
PALM_PASSION = "proprium.dominica-ii-passionis-evangelium"
PALM_PASSION_ROLES = (
    "CXCXCXCXCXCXCSCSCXCXCXCSCSCSCXCSCSCSCSCSCSCSCSCSCSCSCXCSCSCSCSCSCSCSCSCSCSCSCSCSCSCXCXCSCSCCSC"
)
PALM_PASSION_SEGMENTS = tuple(f"s{number:02d}" for number in range(1, 96) if number != 92)
assert len(PALM_PASSION_ROLES) == len(PALM_PASSION_SEGMENTS)
PALM_PASSION_DELIVERY = {
    segment: {"C": "chronista", "X": "christus", "S": "synagoga"}[role]
    for segment, role in zip(PALM_PASSION_SEGMENTS, PALM_PASSION_ROLES, strict=True)
}


def preface_dialogue_errors(doc: dict[str, Any]) -> list[str]:
    """Where the stored Preface dialogue differs from its six printed verses."""
    if doc.get("id") != PREFACE_DIALOGUE:
        return []
    segments = doc.get("segments", [])
    expected = ["s01", *(row[0] for row in PREFACE_DIALOGUE_VERSES)]
    if [s.get("id") for s in segments] != expected or segments[0].get("type") != "rubric":
        return ["preface dialogue: segments must be the rubric s01 and the six verses s02-s07"]
    errors: list[str] = []
    first = 1
    for seg, (sid, speaker, _performer, said) in zip(
        segments[1:], PREFACE_DIALOGUE_VERSES, strict=True
    ):
        ids = [f"w{number:03d}" for number in range(first, first + len(said))]
        first += len(said)
        if (
            seg.get("type") != "verse"
            or tokens(seg) != said
            or [w.get("id") for w in seg.get("words", [])] != ids
        ):
            errors.append(
                f"{sid}: preface dialogue verse must read {' '.join(said)!r} as {ids[0]}-{ids[-1]}"
            )
        if (seg.get("speaker"), seg.get("voice")) != (speaker, "clara"):
            errors.append(f"{sid}: preface dialogue low-Mass base must be {speaker}/clara")
    return errors


def preface_dialogue_delivery(doc: dict[str, Any], seg: dict[str, Any]) -> dict[str, Any]:
    """The sung-Mass performer of one verse of the intact Preface dialogue."""
    if preface_dialogue_errors(doc):
        return {}
    for row in PREFACE_DIALOGUE_VERSES:
        if seg.get("id") == row[0]:
            return {"cantu": {"speaker": row[2], "voice": "cantus"}}
    return {}


def preface_body_errors(doc: dict[str, Any]) -> list[str]:
    """Where a stored Preface differs from its row of the closed inventory."""
    text_id = doc.get("id", "")
    if not text_id.startswith(PREFACE_PREFIX) or text_id == PREFACE_DIALOGUE:
        return []
    row = PREFACE_BODIES.get(text_id.removeprefix(PREFACE_PREFIX))
    if row is None:
        return ["preface: this Preface has no row in the closed inventory of sung Prefaces"]
    first, counts = row
    verses = [f"s{number:02d}" for number in range(first, first + len(counts))]
    segments = doc.get("segments", [])
    rubric = ["s01"] if first == 2 else []
    if [s.get("id") for s in segments] != rubric + verses or (
        rubric and segments[0].get("type") != "rubric"
    ):
        named = f"verses {verses[0]}-{verses[-1]}" if len(verses) > 1 else f"verse {verses[0]}"
        opening = "the rubric s01 and " if rubric else ""
        return [f"preface: segments must be {opening}the {named}"]
    errors: list[str] = []
    word = 1
    for seg, count in zip(segments[len(rubric) :], counts, strict=True):
        ids = [f"w{number:03d}" for number in range(word, word + count)]
        word += count
        if seg.get("type") != "verse" or [w.get("id") for w in seg.get("words", [])] != ids:
            errors.append(f"{seg['id']}: preface verse must hold {ids[0]}-{ids[-1]}")
        if (seg.get("speaker"), seg.get("voice")) != ("sacerdos", "clara"):
            errors.append(f"{seg['id']}: preface low-Mass base must be sacerdos/clara")
    return errors


def preface_body_delivery(doc: dict[str, Any], seg: dict[str, Any]) -> dict[str, Any]:
    """The sung-Mass delivery of one segment of an intact, inventoried Preface."""
    if preface_body_errors(doc) or seg.get("type") != "verse":
        return {}
    return {"cantu": {"speaker": "sacerdos", "voice": "cantus"}}


def preface_errors(doc: dict[str, Any]) -> list[str]:
    """Where a stored Preface or its dialogue differs from its closed rule."""
    return preface_dialogue_errors(doc) + preface_body_errors(doc)


def derive(doc: dict[str, Any], seg: dict[str, Any]) -> dict[str, Any]:
    """Return the form-specific override required by this segment."""
    if doc.get("id") in ritual.TEXTS:
        return ritual.delivery(doc, seg)
    if is_office(doc):
        return office_delivery(doc, seg)
    if doc.get("id") == PREFACE_DIALOGUE:
        return preface_dialogue_delivery(doc, seg)
    if doc.get("id", "").startswith(PREFACE_PREFIX):
        return preface_body_delivery(doc, seg)
    _, orations = structure(doc)
    if seg.get("id") in orations:
        return sung_delivery(orations[seg["id"]])
    if doc.get("id") == PALM_PASSION and seg.get("id") in PALM_PASSION_DELIVERY:
        return {
            "cantu": {
                "speaker": PALM_PASSION_DELIVERY[seg["id"]],
                "voice": "cantus",
            }
        }
    if (
        doc.get("category") == "proprium"
        and seg.get("type") == "verse"
        and seg.get("words")
        and proper_genus(doc["id"]) in CANTU_III_PROPER
    ):
        return {"cantu": {"speaker": "schola", "voice": "cantus"}}
    return {}


def check_doc(doc: dict[str, Any]) -> tuple[list[str], int]:
    """Compare stored delivery with the derived liturgical role."""
    errors = base_errors(doc) + ritual.base_errors(doc) + preface_errors(doc)
    overridden = 0
    for seg in doc.get("segments", []):
        want, have = derive(doc, seg), seg.get("delivery") or {}
        if want != have:
            errors.append(
                f"{seg['id']}: delivery {have or 'absent'} — "
                f"the Mass forms require {want or 'none'}"
            )
        if want:
            overridden += 1
    return errors, overridden


def run(write: bool = False) -> int:
    problems, written, carried = 0, 0, 0
    for path in sorted(ROOT.glob("texts/*/*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        invalid_base = base_errors(doc) + ritual.base_errors(doc) + preface_errors(doc)
        if invalid_base:
            problems += len(invalid_base)
            for error in invalid_base:
                print(f"delivery: {doc['id']} {error}")
            # An unknown Office performer cannot be repaired by guessing.
            # Refuse the document in write mode as well as in check mode.
            continue
        changed = False
        for seg in doc.get("segments", []):
            want, have = derive(doc, seg), seg.get("delivery") or {}
            if want == have:
                carried += 1 if want else 0
                continue
            if write:
                if want:
                    seg["delivery"] = want
                else:
                    seg.pop("delivery", None)
                changed, written = True, written + 1
            else:
                problems += 1
                print(
                    f"delivery: {doc['id']} {seg['id']} carries {have!r}, "
                    f"the Mass forms require {want!r}"
                )
        if changed:
            path.write_text(formatted(doc), encoding="utf-8")

    if write:
        print(f"delivery: wrote {written} segments")
        return problems
    verdict = "FAIL" if problems else "OK"
    print(f"delivery: {verdict} {carried} form-specific segment overrides")
    return problems


if __name__ == "__main__":
    sys.exit(1 if run(write="--write" in sys.argv) else 0)
