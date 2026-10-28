"""Every verse of every Gospel but the solemn Passion is the celebrant's sung line at a sung Mass.

RG 511 e has the celebrant say the Gospel aloud at low Mass; at a sung Mass the Gospel is
sung, by the deacon at a solemn Mass (Ritus servandus VI, 5) and by the celebrant at a
Missa cantata, who sings the sacred ministers' parts (RG 514; RG 473). The low-Mass base
stays sacerdos/clara and no participation follows. The rule is bound to a closed inventory
of the Gospels the formularies select: a changed Gospel is reported, an unknown one is
refused, and the same base or the same words elsewhere take nothing from it. The solemn
Passion keeps its three parts (tests/test_delivery.py). The announcement before the Gospel
is sung with it (ordo/introductiones.json), so a sung announcement never precedes a spoken
body.
"""

import json
import shutil
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from gospel_delivery_fixture import (
    DATA,
    current_gospel_expected_row,
    current_gospel_graph_hash,
    current_gospel_record_hash,
    current_gospel_selected_hash,
    current_gospel_source_hash,
    current_gospel_witness_hash,
    current_sung_expected_row,
    current_sung_selected_hash,
    current_sung_source_hash,
    without_gospel_delivery,
    without_sung_delivery,
)
from iste_gender_fixture import before_iste_gender, current_iste_source_hash
from michael_gospel_fixture import predecessor_core, predecessor_row
from michael_gospel_source_fixture import before_michael_records
from rosary_gospel_source_fixture import before_rosary_records
from witness_header_fixture import before_privacy

from build_reader import bibliography_bindings as bindings
from checks import delivery, participation
from checks.layout import formatted
from checks.orations import check_doc as check_orations
from checks.translation_provenance import canonical_hash, source_payload

CORPUS = Path(__file__).resolve().parent.parent
PREFIX = "proprium."
SUFFIX = "-evangelium"
PASSION = PREFIX + "dominica-ii-passionis" + SUFFIX
CALL = {"cantu": {"speaker": "sacerdos", "voice": "cantus"}}
UNKNOWN = "gospel: this Gospel has no row in the closed inventory of sung Gospels"
RUBRIC = 0
# The closed inventory written out by segment, independently of checks/delivery.py: the word
# count of each verse, RUBRIC for a rubric.
VERSES: dict[str, dict[str, int]] = {
    "annuntiatio-beatae-mariae-virginis": {"s01": 189},
    "ascensio-domini": {"s01": 108, "s02": RUBRIC},
    "assumptio-beatae-mariae-virginis": {"s01": 114},
    "beata-maria-virgo-regina": {"s01": 112},
    "beatae-mariae-virginis-a-rosario": {"s01": 189},
    "commemoratio-baptismatis-domini": {"s01": 110},
    "commemoratio-omnium-fidelium-defunctorum-missa-i": {"s01": 84},
    "commemoratio-omnium-fidelium-defunctorum-missa-ii": {"s01": 91},
    "commemoratio-omnium-fidelium-defunctorum-missa-iii": {"s01": 90},
    "corporis-christi": {"s01": 18, "s02": 15, "s03": 19, "s04": 7, "s05": 9, "s06": 7},
    "d-n-iesu-christi-regis": {"s01": 108},
    "dedicatio-archibasilicae-sanctissimi-salvatoris": {"s01": 138},
    "dedicatio-sancti-michaelis-archangeli": {"s01": 196},
    "dominica-i-adventus": {
        "s01": 40,
        "s02": 13,
        "s03": 13,
        "s04": 20,
        "s05": 13,
        "s06": 11,
        "s07": 9,
    },
    "dominica-i-in-quadragesima": {"s01": 170},
    "dominica-i-passionis": {"s01": 237},
    "dominica-ii-adventus": {
        "s01": 17,
        "s02": 8,
        "s03": 12,
        "s04": 21,
        "s05": 18,
        "s06": 7,
        "s07": 8,
        "s08": 12,
        "s09": 21,
    },
    "dominica-ii-post-epiphaniam": {"s01": 160},
    "dominica-ii-post-pascha": {"s01": 109},
    "dominica-ii-post-pentecosten": {"s01": 150},
    "dominica-iii-adventus": {
        "s01": 15,
        "s02": 3,
        "s03": 14,
        "s04": 8,
        "s05": 10,
        "s06": 17,
        "s07": 13,
        "s08": 7,
        "s09": 18,
        "s10": 15,
        "s11": 22,
        "s12": 11,
    },
    "dominica-iii-in-quadragesima": {"s01": 240},
    "dominica-iii-post-epiphaniam": {"s01": 213},
    "dominica-iii-post-pascha": {"s01": 159},
    "dominica-iii-post-pentecosten": {"s01": 160},
    "dominica-in-albis": {"s01": 243},
    "dominica-in-quinquagesima": {"s01": 160},
    "dominica-in-septuagesima": {"s01": 240},
    "dominica-in-sexagesima": {"s01": 208},
    "dominica-infra-octavam-nativitatis": {"s01": 143},
    "dominica-iv-adventus": {"s01": 42, "s02": 56},
    "dominica-iv-in-quadragesima": {"s01": 222},
    "dominica-iv-post-epiphaniam": {"s01": 76},
    "dominica-iv-post-pascha": {"s01": 146},
    "dominica-iv-post-pentecosten": {"s01": 187},
    "dominica-ix-post-pentecosten": {"s01": 113},
    "dominica-pentecostes": {"s01": 163},
    "dominica-post-ascensionem": {"s01": 85},
    "dominica-resurrectionis": {"s01": 97},
    "dominica-v-post-epiphaniam": {"s01": 122},
    "dominica-v-post-pascha": {"s01": 137},
    "dominica-v-post-pentecosten": {"s01": 100},
    "dominica-vi-post-epiphaniam": {"s01": 102},
    "dominica-vi-post-pentecosten": {"s01": 126},
    "dominica-vii-post-pentecosten": {"s01": 107},
    "dominica-viii-post-pentecosten": {"s01": 164},
    "dominica-x-post-pentecosten": {"s01": 104},
    "dominica-xi-post-pentecosten": {"s01": 104},
    "dominica-xii-post-pentecosten": {"s01": 251},
    "dominica-xiii-post-pentecosten": {"s01": 115},
    "dominica-xiv-post-pentecosten": {"s01": 183},
    "dominica-xix-post-pentecosten": {"s01": 197},
    "dominica-xv-post-pentecosten": {"s01": 102},
    "dominica-xvi-post-pentecosten": {"s01": 167},
    "dominica-xvii-post-pentecosten": {"s01": 140},
    "dominica-xviii-post-pentecosten": {"s01": 114},
    "dominica-xx-post-pentecosten": {"s01": 128},
    "dominica-xxi-post-pentecosten": {"s01": 212},
    "dominica-xxii-post-pentecosten": {"s01": 101},
    "dominica-xxiii-post-pentecosten": {"s01": 133},
    "dominica-xxiv-post-pentecosten": {"s01": 306},
    "epiphania-domini": {"s01": 170, "s02": RUBRIC, "s03": 32},
    "exaltatio-sanctae-crucis": {"s01": 98},
    "feria-v-in-cena-domini": {"s01": 245},
    "immaculata-conceptio": {"s01": 45},
    "immaculatum-cor-beatae-mariae-virginis": {"s01": 50},
    "in-octava-nativitatis": {"s01": 25},
    "maternitas-beatae-mariae-virginis": {"s01": 133},
    "nativitas-domini-in-aurora": {"s01": 91},
    "nativitas-domini-in-die": {"s01": 151, "s02": RUBRIC, "s03": 22},
    "nativitas-domini-in-nocte": {"s01": 190},
    "nativitas-sancti-ioannis-baptistae": {"s01": 156},
    "omnium-sanctorum": {"s01": 111},
    "pretiosissimi-sanguinis-domini-nostri-iesu-christi": {"s01": 93},
    "purificatio-beatae-mariae-virginis": {"s01": 153},
    "sacratissimi-cordis-iesu": {"s01": 28, "s02": 15, "s03": 27, "s04": 20, "s05": 21},
    "sancta-familia": {"s01": 167},
    "sanctae-annae-matris-beatae-mariae-virginis": {"s01": 144},
    "sancti-andreae-apostoli": {"s01": 81},
    "sancti-bartholomaei-apostoli": {"s01": 122},
    "sancti-iacobi-apostoli": {"s01": 85},
    "sancti-ioachim-confessoris": {"s01": 200},
    "sancti-ioannis-apostoli-et-evangelistae": {"s01": 106},
    "sancti-ioseph-opificis": {"s01": 87},
    "sancti-laurentii-martyris": {"s01": 71},
    "sancti-lucae-evangelistae": {"s01": 141},
    "sancti-matthaei-apostoli-et-evangelistae": {"s01": 83},
    "sancti-matthiae-apostoli": {"s01": 98},
    "sancti-petri-et-pauli-apostolorum": {"s01": 127},
    "sancti-stephani-protomartyris": {"s01": 122},
    "sancti-thomae-apostoli": {"s01": 126},
    "sanctissimae-trinitatis": {"s01": 17, "s02": 22, "s03": 11},
    "sanctorum-innocentium-martyrum": {"s01": 136},
    "sanctorum-philippi-et-iacobi-apostolorum": {"s01": 219},
    "sanctorum-simonis-et-iudae-apostolorum": {"s01": 154},
    "septem-dolorum-beatae-mariae-virginis": {"s01": 50},
    "transfiguratio-domini": {"s01": 148},
    "vigilia-ascensionis": {
        "s01": 20,
        "s02": 15,
        "s03": 16,
        "s04": 12,
        "s05": 16,
        "s06": 19,
        "s07": 10,
        "s08": 23,
        "s09": 17,
        "s10": 14,
        "s11": 16,
    },
    "vigilia-nativitatis": {"s01": 80},
    "vigilia-paschalis": {"s01": 110},
    "vigilia-pentecostes": {"s01": 125},
    "visitatio-beatae-mariae-virginis": {"s01": 112},
}
TEXTS = [PREFIX + slug + SUFFIX for slug in sorted(VERSES)]
# The source-hash inverse records only the 101 bodies that already existed.
HISTORICAL_TEXTS = sorted(DATA["source"])
VERSE_CASES = [
    pytest.param(PREFIX + slug + SUFFIX, sid, id=f"{slug}-{sid}")
    for slug in sorted(VERSES)
    for sid, count in VERSES[slug].items()
    if count != RUBRIC
]


def slug_of(text_id: str) -> str:
    return text_id.removeprefix(PREFIX).removesuffix(SUFFIX)


def path_of(text_id: str) -> Path:
    category, name = text_id.split(".", 1)
    return CORPUS / "texts" / category / f"{name}.json"


def text(text_id: str) -> dict[str, Any]:
    return json.loads(path_of(text_id).read_text(encoding="utf-8"))


def segment(doc: dict[str, Any], sid: str) -> dict[str, Any]:
    matches = [s for s in doc["segments"] if s["id"] == sid]
    assert len(matches) == 1
    return matches[0]


def verses(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return [s for s in doc["segments"] if s["type"] == "verse"]


def verse_ids(text_id: str) -> list[str]:
    return [sid for sid, count in VERSES[slug_of(text_id)].items() if count != RUBRIC]


def word_ids(text_id: str, sid: str) -> list[str]:
    rows = VERSES[slug_of(text_id)]
    first = 1 + sum(count for other, count in rows.items() if other < sid)
    return [f"w{number:03d}" for number in range(first, first + rows[sid])]


def selected_gospels() -> set[str]:
    """The Gospel texts the formularies select in their Gospel role, the Passion apart."""
    found: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, dict):
            if value.get("role") == "evangelium":
                found.add(value["text"])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    for path in sorted((CORPUS / "formularies").rglob("*.json")):
        visit(json.loads(path.read_text(encoding="utf-8")))
    return found - {PASSION}


def test_the_inventory_is_every_gospel_the_formularies_select():
    assert len(VERSES) == 102
    assert sum(count != RUBRIC for rows in VERSES.values() for count in rows.values()) == 151
    assert sum(count == RUBRIC for rows in VERSES.values() for count in rows.values()) == 3
    assert sum(sum(rows.values()) for rows in VERSES.values()) == 13992
    assert len(HISTORICAL_TEXTS) == 101
    assert set(TEXTS) - set(HISTORICAL_TEXTS) == {PREFIX + "vigilia-ascensionis" + SUFFIX}
    on_disk = {
        PREFIX + path.stem for path in (CORPUS / "texts" / "proprium").glob("*" + SUFFIX + ".json")
    }
    assert on_disk == {*TEXTS, PASSION}
    assert selected_gospels() == set(TEXTS)
    assert set(delivery.GOSPEL_BODIES) == set(VERSES)
    for slug, rows in VERSES.items():
        assert list(rows) == [f"s{number:02d}" for number in range(1, len(rows) + 1)]
        assert delivery.GOSPEL_BODIES[slug] == tuple(rows.values())
    assert delivery.is_gospel_body(text(TEXTS[0]))
    assert not delivery.is_gospel_body(text(PASSION))


@pytest.mark.parametrize(("text_id", "sid"), VERSE_CASES)
def test_each_verse_is_the_celebrants_sung_line(text_id, sid):
    doc = text(text_id)
    seg = segment(doc, sid)
    assert seg["type"] == "verse"
    assert [w["id"] for w in seg["words"]] == word_ids(text_id, sid)
    assert (seg["speaker"], seg["voice"]) == ("sacerdos", "clara")
    assert seg["delivery"] == CALL
    assert delivery.derive(doc, seg) == CALL
    assert "participation" not in seg
    assert participation.derive(doc, seg) == {}


@pytest.mark.parametrize("text_id", TEXTS)
def test_each_gospel_passes_every_layer_with_one_override_per_verse(text_id):
    doc = text(text_id)
    rows = verse_ids(text_id)
    assert [s["id"] for s in verses(doc)] == rows
    assert delivery.check_doc(doc) == ([], len(rows))
    assert participation.check_doc(doc) == ([], 0)
    assert check_orations(doc) == ([], 0)
    rubrics = [s for s in doc["segments"] if s["type"] == "rubric"]
    assert [s["id"] for s in rubrics] == [
        sid for sid, count in VERSES[slug_of(text_id)].items() if count == RUBRIC
    ]
    for rubric in rubrics:
        assert delivery.derive(doc, rubric) == {}
        assert not {"delivery", "speaker", "voice", "participation"} & set(rubric)


def spoil(seg: dict[str, Any], fault: str) -> None:
    if fault == "removed":
        del seg["delivery"]
    elif fault == "wrong-voice":
        seg["delivery"]["cantu"]["voice"] = "clara"
    else:
        seg["delivery"]["cantu"]["speaker"] = "schola"


FAULTS = ("removed", "wrong-voice", "wrong-performer")


@pytest.mark.parametrize("text_id", TEXTS)
@pytest.mark.parametrize("fault", FAULTS)
def test_a_missing_or_wrong_override_fails_with_its_own_diagnostic(fault, text_id):
    original = text(text_id)
    pristine = deepcopy(original)
    rows = verse_ids(text_id)
    for sid in rows:
        doc = deepcopy(original)
        seg = segment(doc, sid)
        spoil(seg, fault)
        have = seg.get("delivery") or "absent"
        assert delivery.check_doc(doc) == (
            [f"{sid}: delivery {have} — the Mass forms require {CALL}"],
            len(rows),
        )
        assert delivery.derive(doc, seg) == CALL
    assert original == pristine
    assert delivery.check_doc(original) == ([], len(rows))


@pytest.mark.parametrize("text_id", TEXTS)
def test_a_changed_low_mass_base_is_reported_and_nothing_is_derived(text_id):
    original = text(text_id)
    pristine = deepcopy(original)
    for sid in verse_ids(text_id):
        for key, wrong in (("speaker", "diaconus"), ("voice", "submissa")):
            doc = deepcopy(original)
            segment(doc, sid)[key] = wrong
            errors, overridden = delivery.check_doc(doc)
            assert f"{sid}: gospel low-Mass base must be sacerdos/clara" in errors
            assert overridden == 0
            assert all(delivery.derive(doc, s) == {} for s in doc["segments"])
    assert original == pristine
    assert delivery.check_doc(original)[0] == []


@pytest.mark.parametrize("text_id", TEXTS)
def test_a_renumbered_word_is_reported_and_nothing_is_derived(text_id):
    original = text(text_id)
    doc = deepcopy(original)
    first = verses(doc)[0]
    first["words"][0]["id"] = "w999"
    ids = word_ids(text_id, first["id"])
    errors, overridden = delivery.check_doc(doc)
    assert f"{first['id']}: gospel verse must hold {ids[0]}-{ids[-1]}" in errors
    assert overridden == 0
    assert all(delivery.derive(doc, s) == {} for s in doc["segments"])
    assert delivery.check_doc(original)[0] == []


def remove(sid: str) -> Callable[[dict[str, Any]], None]:
    return lambda doc: doc["segments"].remove(segment(doc, sid))


def extra(doc: dict[str, Any]) -> None:
    last = doc["segments"][-1]
    doc["segments"].append({**deepcopy(last), "id": f"s{len(doc['segments']) + 1:02d}"})


def reorder(doc: dict[str, Any]) -> None:
    segments = doc["segments"]
    segments[1], segments[2] = segments[2], segments[1]


def moved_word(doc: dict[str, Any]) -> None:
    segment(doc, "s02")["words"].insert(0, segment(doc, "s01")["words"].pop())


def rubric_added(doc: dict[str, Any]) -> None:
    doc["segments"].append({"id": "s02", "type": "rubric", "text": "Credo."})


def split_verse(doc: dict[str, Any]) -> None:
    whole = segment(doc, "s01")
    doc["segments"].append({**deepcopy(whole), "id": "s02", "words": whole["words"][40:]})
    del whole["words"][40:]


def retype(sid: str, kind: str) -> Callable[[dict[str, Any]], None]:
    return lambda doc: segment(doc, sid).update(type=kind)


ADVENT = PREFIX + "dominica-i-adventus" + SUFFIX
ADVENT_SEGMENTS = "gospel: segments must be s01-s07"
EPIPHANY = PREFIX + "epiphania-domini" + SUFFIX
SINGLE = PREFIX + "dominica-in-sexagesima" + SUFFIX
BAD_SUBJECTS: dict[str, tuple[str, Callable[[dict[str, Any]], None], str]] = {
    "missing-verse": (ADVENT, remove("s04"), ADVENT_SEGMENTS),
    "extra-verse": (ADVENT, extra, ADVENT_SEGMENTS),
    "reordered": (ADVENT, reorder, ADVENT_SEGMENTS),
    "verse-made-rubric": (ADVENT, retype("s05", "rubric"), "s05: gospel verse must hold w087-w099"),
    "moved-word": (ADVENT, moved_word, "s01: gospel verse must hold w001-w040"),
    "rubric-made-verse": (EPIPHANY, retype("s02", "verse"), "s02: gospel segment must be a rubric"),
    "rubric-dropped": (EPIPHANY, remove("s02"), "gospel: segments must be s01-s03"),
    "rubric-added": (SINGLE, rubric_added, "gospel: segments must be s01"),
    "single-verse-split": (SINGLE, split_verse, "gospel: segments must be s01"),
}


@pytest.mark.parametrize("fault", list(BAD_SUBJECTS))
def test_a_changed_gospel_is_reported_not_copied_into_the_sung_form(fault):
    text_id, change, owned = BAD_SUBJECTS[fault]
    original = text(text_id)
    pristine = deepcopy(original)
    doc = deepcopy(original)
    change(doc)
    errors, overridden = delivery.check_doc(doc)
    assert owned in errors
    assert overridden == 0
    assert all(delivery.derive(doc, s) == {} for s in doc["segments"])
    assert original == pristine
    assert delivery.check_doc(original) == ([], len(verse_ids(text_id)))


def corpus_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *text_ids: str) -> list[Path]:
    """A small corpus holding copies of the committed texts, for the writer."""
    targets = []
    for text_id in text_ids:
        target = tmp_path / path_of(text_id).relative_to(CORPUS)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path_of(text_id), target)
        targets.append(target)
    monkeypatch.setattr(delivery, "ROOT", tmp_path)
    return targets


WRITTEN = [ADVENT, EPIPHANY, SINGLE, PREFIX + "corporis-christi" + SUFFIX]


@pytest.mark.parametrize("text_id", WRITTEN)
def test_a_stripped_copy_fails_and_the_writer_restores_the_committed_bytes(
    tmp_path, monkeypatch, capsys, text_id
):
    (target,) = corpus_copy(tmp_path, monkeypatch, text_id)
    committed = target.read_bytes()
    doc = json.loads(committed)
    for seg in verses(doc):
        del seg["delivery"]
    target.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    rows = verse_ids(text_id)
    assert delivery.run() == len(rows)
    assert capsys.readouterr().out == (
        "".join(
            f"delivery: {text_id} {sid} carries {{}}, the Mass forms require {CALL!r}\n"
            for sid in rows
        )
        + "delivery: FAIL 0 form-specific segment overrides\n"
    )
    assert delivery.run(write=True) == 0
    assert target.read_bytes() == committed
    capsys.readouterr()
    assert delivery.run() == 0
    assert capsys.readouterr().out == f"delivery: OK {len(rows)} form-specific segment overrides\n"


@pytest.mark.parametrize("fault", list(BAD_SUBJECTS))
def test_the_writer_refuses_a_changed_gospel(tmp_path, monkeypatch, capsys, fault):
    text_id, change, owned = BAD_SUBJECTS[fault]
    (target,) = corpus_copy(tmp_path, monkeypatch, text_id)
    doc = json.loads(target.read_text(encoding="utf-8"))
    change(doc)
    target.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    spoiled = target.read_bytes()
    assert delivery.run(write=True) >= 1
    assert f"delivery: {text_id} {owned}\n" in capsys.readouterr().out
    assert target.read_bytes() == spoiled


def test_an_uninventoried_gospel_is_refused_rather_than_left_unmodeled(
    tmp_path, monkeypatch, capsys
):
    doc = text(SINGLE)
    doc["id"] = PREFIX + "feria-uninventoried" + SUFFIX
    errors, overridden = delivery.check_doc(doc)
    assert errors[0] == UNKNOWN and overridden == 0
    assert all(delivery.derive(doc, s) == {} for s in doc["segments"])
    for seg in verses(doc):
        del seg["delivery"]
    assert delivery.check_doc(doc) == ([UNKNOWN], 0)
    target = tmp_path / "texts" / "proprium" / "feria-uninventoried-evangelium.json"
    target.parent.mkdir(parents=True)
    target.write_text(formatted(doc), encoding="utf-8")
    monkeypatch.setattr(delivery, "ROOT", tmp_path)
    unwritten = target.read_bytes()
    assert delivery.run(write=True) == 1
    assert f"delivery: {doc['id']} {UNKNOWN}\n" in capsys.readouterr().out
    assert target.read_bytes() == unwritten


def test_a_gospel_under_another_id_takes_nothing():
    for identity in (
        "proprium.dominica-in-sexagesima-lectio",
        "ordinarium.dominica-in-sexagesima-evangelium",
    ):
        doc = text(SINGLE)
        doc["id"] = identity
        assert not delivery.is_gospel_body(doc)
        assert all(delivery.derive(doc, s) == {} for s in doc["segments"])
        for seg in verses(doc):
            del seg["delivery"]
        assert delivery.check_doc(doc) == ([], 0)


def test_the_solemn_passion_keeps_its_own_three_parts():
    doc = text(PASSION)
    assert not delivery.is_gospel_body(doc)
    assert delivery.gospel_body_errors(doc) == []
    sung = {delivery.derive(doc, s)["cantu"]["speaker"] for s in verses(doc)}
    assert sung == {"chronista", "christus", "synagoga"}
    assert delivery.check_doc(doc) == ([], 94)
    assert PASSION not in DATA["source"]
    assert without_gospel_delivery(doc) == doc


# The Epistles and chants of the same Masses, the Last Gospel of the Ordinary, its
# announcement, and the reading announcements that precede the Gospels are not Gospel
# bodies, whatever their words or names.
COUNTEREXAMPLES = (
    "proprium.dominica-i-adventus-epistola",
    "proprium.sancti-matthaei-apostoli-et-evangelistae-epistola",
    "proprium.sancti-lucae-evangelistae-alleluia",
    "ordinarium.evangelium-ultimum",
    "ordinarium.sequentia-sancti-evangelii-secundum-lucam",
    "ordinarium.initium-sancti-evangelii-secundum-matthaeum",
    "ordinarium.passio-domini-nostri-iesu-christi-secundum-matthaeum",
)


@pytest.mark.parametrize("text_id", COUNTEREXAMPLES)
def test_other_texts_take_nothing_from_the_rule(text_id):
    doc = text(text_id)
    assert not delivery.is_gospel_body(doc)
    assert delivery.gospel_body_errors(doc) == []
    assert all(delivery.gospel_body_delivery(doc, s) == {} for s in doc["segments"])
    assert delivery.check_doc(doc)[0] == []
    assert without_gospel_delivery(doc) == doc
    assert current_gospel_selected_hash(text_id, "unchanged") == "unchanged"


@pytest.mark.parametrize("text_id", HISTORICAL_TEXTS)
def test_the_overlay_binds_exactly_the_delivery_additions(text_id):
    doc = text(text_id)
    change = DATA["source"][text_id]
    assert list(change) == verse_ids(text_id)
    assert delivery.check_doc(doc) == ([], len(verse_ids(text_id)))
    assert participation.check_doc(doc) == ([], 0)
    comparison = before_iste_gender(predecessor_core(doc))
    historical = without_gospel_delivery(comparison)
    assert historical["segments"] == [
        {key: value for key, value in s.items() if key != "delivery"}
        for s in comparison["segments"]
    ]
    assert {key: value for key, value in historical.items() if key != "segments"} == {
        key: value for key, value in comparison.items() if key != "segments"
    }
    for seg in verses(comparison):
        entry = change[seg["id"]]
        assert entry["delivery"] == seg["delivery"] == CALL
        assert canonical_hash(source_payload(seg)) == entry["after"]
        assert canonical_hash(source_payload(segment(historical, seg["id"]))) == entry["before"]
        expected = current_iste_source_hash(text_id, seg["id"], entry["after"])
        assert current_gospel_source_hash(text_id, seg["id"], entry["before"]) == expected
        assert current_sung_source_hash(text_id, seg["id"], entry["before"]) == expected
    selected = DATA["selected"][text_id]
    assert bindings.digest(bindings.selected_text(doc)) == selected["after"]
    assert bindings.digest(bindings.selected_text(historical)) == selected["before"]
    assert current_gospel_selected_hash(text_id, selected["before"]) == selected["after"]
    assert current_sung_selected_hash(text_id, selected["before"]) == selected["after"]
    assert without_sung_delivery(comparison) == historical


@pytest.mark.parametrize("language", ("pl", "en"))
def test_every_gospel_ledger_row_advances_only_its_source_hash(language):
    ledger = json.loads(
        (CORPUS / "languages" / language / "translation-provenance.json").read_text(
            encoding="utf-8"
        )
    )["sites"]
    rows = [row for row in ledger if row["text"] in DATA["source"]]
    assert len(rows) == 140
    for row in rows:
        snapshot = deepcopy(row)
        observed = text(row["text"])
        assert delivery.check_doc(observed) == ([], len(verse_ids(row["text"])))
        assert row["source_sha256"] == canonical_hash(
            source_payload(segment(observed, row["segment"]))
        )
        comparison = predecessor_row(row)
        change = DATA["source"][row["text"]][row["segment"]]
        previous = {**comparison, "source_sha256": change["before"]}
        assert current_gospel_expected_row(previous) == comparison
        assert current_sung_expected_row(previous) == comparison
        assert row == snapshot
        assert comparison["source_sha256"] == current_iste_source_hash(
            row["text"], row["segment"], change["after"]
        )
    other = next(row for row in ledger if row["text"] not in DATA["source"])
    assert current_gospel_expected_row(other) == other


def graph_records(graph: dict[str, Any], text_id: str) -> dict[str, list[dict[str, Any]]]:
    return {
        key: [r for r in graph[key] if r.get("text", r.get("address", {}).get("text")) == text_id]
        for key in ("uses", "witnesses", "collations")
    }


def without_apparatus_hash(row: dict[str, Any]) -> dict[str, Any]:
    comparison = before_michael_records(before_rosary_records(row))
    return {key: value for key, value in comparison.items() if key != "apparatus_sha256"}


def test_the_graph_overlay_is_exactly_the_stored_selected_text_digests():
    graph = json.loads((CORPUS / "bibliography" / "graph.json").read_text(encoding="utf-8"))
    assert bindings.validate_bindings(CORPUS, graph) == []
    collations = [row for row in graph["collations"] if row["text"] in DATA["source"]]
    assert len(collations) == 98
    assert sorted(row["id"] for row in collations) == sorted(DATA["collation_records"])
    uncollated = {
        PREFIX + slug + SUFFIX
        for slug in ("dominica-ii-adventus", "dominica-iii-adventus", "dominica-iv-adventus")
    }
    assert {row["text"] for row in collations} == set(HISTORICAL_TEXTS) - uncollated
    historical = deepcopy(graph)
    for row in historical["collations"]:
        if row["text"] in DATA["source"]:
            assert row["review"] == {"status": "pending"}
            assert row["selected_text_sha256"] == DATA["selected"][row["text"]]["after"]
            row["selected_text_sha256"] = DATA["selected"][row["text"]]["before"]
    for current, old in zip(graph["collations"], historical["collations"], strict=True):
        if current["text"] in DATA["source"]:
            record = DATA["collation_records"][current["id"]]
            assert bindings.digest(without_apparatus_hash(current)) == record["after"]
            assert bindings.digest(without_apparatus_hash(old)) == record["before"]
            assert current_gospel_record_hash(current["id"], record["before"]) == record["after"]
    for text_id in HISTORICAL_TEXTS:
        sets = DATA["graph_sets"][text_id]
        assert bindings.digest(before_privacy(graph_records(graph, text_id))) == sets["after"]
        assert bindings.digest(before_privacy(graph_records(historical, text_id))) == sets["before"]
        assert current_gospel_graph_hash(text_id, sets["before"]) == sets["after"]


def test_the_witness_overlay_is_exactly_the_current_and_historical_subjects():
    graph = json.loads((CORPUS / "bibliography" / "graph.json").read_text(encoding="utf-8"))
    snapshot = bindings._SourceSnapshot(CORPUS, graph)
    rows = [row for row in graph["witnesses"] if row["text"] in DATA["source"]]
    assert len(rows) == 196
    assert sorted(row["id"] for row in rows) == sorted(DATA["witness_subjects"])
    for row in rows:
        doc = text(row["text"])
        expected = DATA["witness_subjects"][row["id"]]
        current = bindings._witness_subject(CORPUS, row, doc, snapshot, reviewable=False)
        old = bindings._witness_subject(
            CORPUS, row, without_gospel_delivery(doc), snapshot, reviewable=False
        )
        assert bindings.digest(before_privacy(current)) == expected["after"]
        assert bindings.digest(before_privacy(old)) == expected["before"]
        assert current_gospel_witness_hash(row["id"], expected["before"]) == expected["after"]


STALE: dict[str, tuple[Callable[[], object], str]] = {
    "source-preimage": (
        lambda: current_gospel_source_hash(SINGLE, "s01", "0" * 64),
        "historical Gospel source hash",
    ),
    "source-segment": (
        lambda: current_gospel_source_hash(EPIPHANY, "s02", "0" * 64),
        "Gospel source segment identity",
    ),
    "row-preimage": (
        lambda: current_gospel_expected_row(
            {"site": SINGLE + ".s01.pl", "text": SINGLE, "segment": "s01", "source_sha256": "0"}
        ),
        "historical Gospel source hash",
    ),
    "row-identity": (
        lambda: current_gospel_expected_row(
            {"site": SINGLE + ".s01.pl", "text": ADVENT, "segment": "s01", "source_sha256": "0"}
        ),
        "Gospel ledger row identity",
    ),
    "selected": (
        lambda: current_gospel_selected_hash(SINGLE, "0" * 64),
        "historical Gospel selected hash",
    ),
    "graph": (
        lambda: current_gospel_graph_hash(SINGLE, "0" * 64),
        "historical Gospel graph_sets hash",
    ),
    "record": (
        lambda: current_gospel_record_hash(next(iter(DATA["collation_records"])), "0" * 64),
        "historical Gospel collation_records hash",
    ),
    "witness": (
        lambda: current_gospel_witness_hash(next(iter(DATA["witness_subjects"])), "0" * 64),
        "historical Gospel witness_subjects hash",
    ),
    "sung-source": (
        lambda: current_sung_source_hash(SINGLE, "s01", "0" * 64),
        "historical Gospel source hash",
    ),
}


@pytest.mark.parametrize("name", list(STALE))
def test_a_stale_historical_value_is_refused_by_the_overlay(name):
    call, message = STALE[name]
    pristine = deepcopy(DATA)
    with pytest.raises(AssertionError, match=f"^{message}"):
        call()
    assert pristine == DATA


INVERSE_DAMAGE: dict[str, tuple[str, Callable[[dict[str, Any]], object]]] = {
    "voice": (
        "current Gospel delivery inverse",
        lambda seg: seg["delivery"]["cantu"].update(voice="clara"),
    ),
    "performer": (
        "current Gospel delivery inverse",
        lambda seg: seg["delivery"]["cantu"].update(speaker="schola"),
    ),
    "missing": ("current Gospel delivery inverse", lambda seg: seg.pop("delivery")),
    "topology": ("current Gospel inverse topology", lambda seg: seg.update(type="rubric")),
}


@pytest.mark.parametrize("damage", list(INVERSE_DAMAGE))
def test_the_inverse_refuses_a_gospel_that_is_not_exactly_the_recorded_one(damage):
    message, change = INVERSE_DAMAGE[damage]
    original = text(ADVENT)
    doc = deepcopy(original)
    change(segment(doc, "s05"))
    with pytest.raises(AssertionError, match=f"^{message}"):
        without_gospel_delivery(doc)
    assert without_gospel_delivery(original) != original


def test_the_inverse_keeps_every_other_field_and_passes_other_texts_through():
    pristine = deepcopy(DATA)
    doc = text(ADVENT)
    segment(doc, "s05")["words"][0]["form"] = "unreviewed"
    doc["editorial"]["notes"] = doc["editorial"].get("notes", "") + " Retained."
    restored = without_gospel_delivery(doc)
    assert segment(restored, "s05")["words"][0]["form"] == "unreviewed"
    assert restored["editorial"] == doc["editorial"]
    assert not any("delivery" in s for s in restored["segments"])
    for other in (
        PASSION,
        "ordinarium.praefatio-communis",
        "proprium.nativitas-domini-in-nocte-collecta",
    ):
        current = text(other)
        copy = without_gospel_delivery(current)
        assert copy == current and copy is not current
        assert current_gospel_selected_hash(other, "unchanged") == "unchanged"
    assert current_gospel_source_hash(PASSION, "s01", "unchanged") == "unchanged"
    assert pristine == DATA
