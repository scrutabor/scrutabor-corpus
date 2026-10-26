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

from checks import participation_performance, ritual
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

# The Gospel. RG 511 e lists the Gospel among what the celebrant says clara
# voce at low Mass, and Ritus servandus VI, 2 has him read it there. At a
# sung Mass the Gospel is sung: by the deacon at a solemn Mass (Ritus
# servandus VI, 5), and at a Missa cantata by the celebrant, who must sing
# the parts proper to the sacred ministers (RG 514); RG 473 has the
# celebrant omit what a minister sings by his own office. The two Mass
# forms of this edition do not distinguish the solemn Mass from the Missa
# cantata, so every verse of a Gospel is the celebrant's in both forms:
# sacerdos/clara at low Mass, and sacerdos/cantus when the Mass is sung. The
# rule adds no participation of the faithful. The Passion keeps its own three
# parts above.
#
# As with the Prefaces, the rule is bound to a closed inventory, never to
# words. Each row gives, segment by segment from s01, the word count of a
# verse, or 0 for a rubric; the word ids of the verses run on from w001
# without a gap. A stored Gospel that differs from its row is reported and
# receives no override, and a Gospel id without a row is reported rather
# than left unmodeled in silence. Other texts take nothing from this rule,
# whatever their words.
GOSPEL_PREFIX = "proprium."
GOSPEL_SUFFIX = "-evangelium"
GOSPEL_BODIES: dict[str, tuple[int, ...]] = {
    "annuntiatio-beatae-mariae-virginis": (189,),
    "ascensio-domini": (108, 0),
    "assumptio-beatae-mariae-virginis": (114,),
    "beata-maria-virgo-regina": (112,),
    "beatae-mariae-virginis-a-rosario": (189,),
    "commemoratio-baptismatis-domini": (110,),
    "commemoratio-omnium-fidelium-defunctorum-missa-i": (84,),
    "commemoratio-omnium-fidelium-defunctorum-missa-ii": (91,),
    "commemoratio-omnium-fidelium-defunctorum-missa-iii": (90,),
    "corporis-christi": (18, 15, 19, 7, 9, 7),
    "d-n-iesu-christi-regis": (108,),
    "dedicatio-archibasilicae-sanctissimi-salvatoris": (138,),
    "dedicatio-sancti-michaelis-archangeli": (196,),
    "dominica-i-adventus": (40, 13, 13, 20, 13, 11, 9),
    "dominica-i-in-quadragesima": (170,),
    "dominica-i-passionis": (237,),
    "dominica-ii-adventus": (17, 8, 12, 21, 18, 7, 8, 12, 21),
    "dominica-ii-post-epiphaniam": (160,),
    "dominica-ii-post-pascha": (109,),
    "dominica-ii-post-pentecosten": (150,),
    "dominica-iii-adventus": (15, 3, 14, 8, 10, 17, 13, 7, 18, 15, 22, 11),
    "dominica-iii-in-quadragesima": (240,),
    "dominica-iii-post-epiphaniam": (213,),
    "dominica-iii-post-pascha": (159,),
    "dominica-iii-post-pentecosten": (160,),
    "dominica-in-albis": (243,),
    "dominica-in-quinquagesima": (160,),
    "dominica-in-septuagesima": (240,),
    "dominica-in-sexagesima": (208,),
    "dominica-infra-octavam-nativitatis": (143,),
    "dominica-iv-adventus": (42, 56),
    "dominica-iv-in-quadragesima": (222,),
    "dominica-iv-post-epiphaniam": (76,),
    "dominica-iv-post-pascha": (146,),
    "dominica-iv-post-pentecosten": (187,),
    "dominica-ix-post-pentecosten": (113,),
    "dominica-pentecostes": (163,),
    "dominica-post-ascensionem": (85,),
    "dominica-resurrectionis": (97,),
    "dominica-v-post-epiphaniam": (122,),
    "dominica-v-post-pascha": (137,),
    "dominica-v-post-pentecosten": (100,),
    "dominica-vi-post-epiphaniam": (102,),
    "dominica-vi-post-pentecosten": (126,),
    "dominica-vii-post-pentecosten": (107,),
    "dominica-viii-post-pentecosten": (164,),
    "dominica-x-post-pentecosten": (104,),
    "dominica-xi-post-pentecosten": (104,),
    "dominica-xii-post-pentecosten": (251,),
    "dominica-xiii-post-pentecosten": (115,),
    "dominica-xiv-post-pentecosten": (183,),
    "dominica-xix-post-pentecosten": (197,),
    "dominica-xv-post-pentecosten": (102,),
    "dominica-xvi-post-pentecosten": (167,),
    "dominica-xvii-post-pentecosten": (140,),
    "dominica-xviii-post-pentecosten": (114,),
    "dominica-xx-post-pentecosten": (128,),
    "dominica-xxi-post-pentecosten": (212,),
    "dominica-xxii-post-pentecosten": (101,),
    "dominica-xxiii-post-pentecosten": (133,),
    "dominica-xxiv-post-pentecosten": (306,),
    "epiphania-domini": (170, 0, 32),
    "exaltatio-sanctae-crucis": (98,),
    "feria-v-in-cena-domini": (245,),
    "immaculata-conceptio": (45,),
    "immaculatum-cor-beatae-mariae-virginis": (50,),
    "in-octava-nativitatis": (25,),
    "maternitas-beatae-mariae-virginis": (133,),
    "nativitas-domini-in-aurora": (91,),
    "nativitas-domini-in-die": (151, 0, 22),
    "nativitas-domini-in-nocte": (190,),
    "nativitas-sancti-ioannis-baptistae": (156,),
    "omnium-sanctorum": (111,),
    "pretiosissimi-sanguinis-domini-nostri-iesu-christi": (93,),
    "purificatio-beatae-mariae-virginis": (153,),
    "sacratissimi-cordis-iesu": (28, 15, 27, 20, 21),
    "sancta-familia": (167,),
    "sanctae-annae-matris-beatae-mariae-virginis": (144,),
    "sancti-andreae-apostoli": (81,),
    "sancti-bartholomaei-apostoli": (122,),
    "sancti-iacobi-apostoli": (85,),
    "sancti-ioachim-confessoris": (200,),
    "sancti-ioannis-apostoli-et-evangelistae": (106,),
    "sancti-ioseph-opificis": (87,),
    "sancti-laurentii-martyris": (71,),
    "sancti-lucae-evangelistae": (141,),
    "sancti-matthaei-apostoli-et-evangelistae": (83,),
    "sancti-matthiae-apostoli": (98,),
    "sancti-petri-et-pauli-apostolorum": (127,),
    "sancti-stephani-protomartyris": (122,),
    "sancti-thomae-apostoli": (126,),
    "sanctissimae-trinitatis": (17, 22, 11),
    "sanctorum-innocentium-martyrum": (136,),
    "sanctorum-philippi-et-iacobi-apostolorum": (219,),
    "sanctorum-simonis-et-iudae-apostolorum": (154,),
    "septem-dolorum-beatae-mariae-virginis": (50,),
    "transfiguratio-domini": (148,),
    "vigilia-ascensionis": (20, 15, 16, 12, 16, 19, 10, 23, 17, 14, 16),
    "vigilia-nativitatis": (80,),
    "vigilia-paschalis": (110,),
    "vigilia-pentecostes": (125,),
    "visitatio-beatae-mariae-virginis": (112,),
}
assert all(any(counts) for counts in GOSPEL_BODIES.values())
assert GOSPEL_PREFIX + "dominica-ii-passionis" + GOSPEL_SUFFIX == PALM_PASSION
assert "dominica-ii-passionis" not in GOSPEL_BODIES


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


def is_gospel_body(doc: dict[str, Any]) -> bool:
    """A Proper Gospel other than the solemn Passion."""
    text_id = doc.get("id", "")
    return (
        text_id.startswith(GOSPEL_PREFIX)
        and text_id.endswith(GOSPEL_SUFFIX)
        and text_id != PALM_PASSION
    )


def gospel_body_errors(doc: dict[str, Any]) -> list[str]:
    """Where a stored Gospel differs from its row of the closed inventory."""
    if not is_gospel_body(doc):
        return []
    slug = doc["id"].removeprefix(GOSPEL_PREFIX).removesuffix(GOSPEL_SUFFIX)
    row = GOSPEL_BODIES.get(slug)
    if row is None:
        return ["gospel: this Gospel has no row in the closed inventory of sung Gospels"]
    segments = doc.get("segments", [])
    expected = [f"s{number:02d}" for number in range(1, len(row) + 1)]
    if [s.get("id") for s in segments] != expected:
        span = expected[0] if len(expected) == 1 else f"{expected[0]}-{expected[-1]}"
        return [f"gospel: segments must be {span}"]
    errors: list[str] = []
    word = 1
    for seg, count in zip(segments, row, strict=True):
        if count == 0:
            if seg.get("type") != "rubric":
                errors.append(f"{seg['id']}: gospel segment must be a rubric")
            continue
        ids = [f"w{number:03d}" for number in range(word, word + count)]
        word += count
        if seg.get("type") != "verse" or [w.get("id") for w in seg.get("words", [])] != ids:
            errors.append(f"{seg['id']}: gospel verse must hold {ids[0]}-{ids[-1]}")
        if (seg.get("speaker"), seg.get("voice")) != ("sacerdos", "clara"):
            errors.append(f"{seg['id']}: gospel low-Mass base must be sacerdos/clara")
    return errors


def gospel_body_delivery(doc: dict[str, Any], seg: dict[str, Any]) -> dict[str, Any]:
    """The sung-Mass delivery of one segment of an intact, inventoried Gospel."""
    if not is_gospel_body(doc) or gospel_body_errors(doc) or seg.get("type") != "verse":
        return {}
    return {"cantu": {"speaker": "sacerdos", "voice": "cantus"}}


def derive(doc: dict[str, Any], seg: dict[str, Any]) -> dict[str, Any]:
    """Return the form-specific override required by this segment."""
    if doc.get("id") == participation_performance.TEXT:
        return participation_performance.priestly_delivery(doc, seg)
    if doc.get("id") in ritual.TEXTS:
        return ritual.delivery(doc, seg)
    if is_office(doc):
        return office_delivery(doc, seg)
    if doc.get("id") == PREFACE_DIALOGUE:
        return preface_dialogue_delivery(doc, seg)
    if doc.get("id", "").startswith(PREFACE_PREFIX):
        return preface_body_delivery(doc, seg)
    if is_gospel_body(doc):
        return gospel_body_delivery(doc, seg)
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
    errors = (
        base_errors(doc)
        + ritual.base_errors(doc)
        + preface_errors(doc)
        + gospel_body_errors(doc)
        + participation_performance.base_errors(doc)
    )
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
        invalid_base = (
            base_errors(doc)
            + ritual.base_errors(doc)
            + preface_errors(doc)
            + gospel_body_errors(doc)
            + participation_performance.base_errors(doc)
        )
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
