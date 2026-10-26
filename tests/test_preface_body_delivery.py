"""Every verse of every Preface is the celebrant's sung line at a sung Mass.

RG 511 h has the celebrant say the Preface aloud at low Mass; RG 513 a has
him sing it at a solemn Mass, and RG 514 extends that to the Missa cantata.
The low-Mass base stays sacerdos/clara and no participation follows. The rule
is bound to a closed inventory of the Prefaces the formularies select: a
changed Preface is reported, an unknown one is refused, and the same base or
the same words elsewhere take nothing from it. The dialogue before the
Preface has its own rule (tests/test_preface_dialogue_delivery.py).
"""

import json
import shutil
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from common_preface_source_fixture import without_common_preface_source_chain
from preface_delivery_fixture import (
    DATA,
    current_expected_row,
    current_graph_hash,
    current_record_hash,
    current_selected_hash,
    current_source_hash,
    current_witness_hash,
    without_preface_delivery,
)
from witness_header_fixture import before_privacy

from build_reader import bibliography_bindings as bindings
from checks import delivery, participation
from checks.layout import formatted
from checks.orations import check_doc as check_orations
from checks.translation_provenance import canonical_hash, source_payload

CORPUS = Path(__file__).resolve().parent.parent
PREFIX = "ordinarium.praefatio-"
DIALOGUE = PREFIX + "dialogus"
CALL = {"cantu": {"speaker": "sacerdos", "voice": "cantus"}}
UNKNOWN = "preface: this Preface has no row in the closed inventory of sung Prefaces"
SEVEN = ("s02", "s03", "s04", "s05", "s06", "s07", "s08")
# The closed inventory written out by segment, independently of checks/delivery.py.
VERSES: dict[str, dict[str, int]] = {
    "apostolorum": {"s02": 8, "s03": 19, "s04": 12, "s05": 22},
    "ascensionis": {"s02": 70},
    "beatae-mariae-virginis": dict(zip(SEVEN, (15, 6, 12, 20, 10, 9, 12), strict=True)),
    "beatae-mariae-virginis-in-annuntiatione": dict(
        zip(SEVEN, (15, 6, 12, 20, 10, 9, 12), strict=True)
    ),
    "beatae-mariae-virginis-in-assumptione": dict(
        zip(SEVEN, (15, 6, 12, 20, 10, 9, 12), strict=True)
    ),
    "beatae-mariae-virginis-in-conceptione-immaculata": dict(
        zip(SEVEN, (15, 6, 13, 20, 10, 9, 12), strict=True)
    ),
    "beatae-mariae-virginis-in-nativitate": dict(
        zip(SEVEN, (15, 6, 12, 20, 10, 9, 12), strict=True)
    ),
    "beatae-mariae-virginis-in-transfixione": dict(
        zip(SEVEN, (15, 6, 12, 20, 10, 9, 12), strict=True)
    ),
    "beatae-mariae-virginis-in-visitatione": dict(
        zip(SEVEN, (15, 6, 12, 20, 10, 9, 12), strict=True)
    ),
    "communis": {"s02": 15, "s03": 10, "s04": 10, "s05": 9, "s06": 12},
    "d-n-iesu-christi-regis": {"s02": 15, "s03": 6, "s04": 57, "s05": 22},
    "defunctorum": {"s02": 15, "s03": 10, "s04": 18, "s05": 19, "s06": 22},
    "epiphaniae": {"s02": 15, "s03": 6, "s04": 15, "s05": 22},
    "nativitatis": {"s02": 15, "s03": 6, "s04": 24, "s05": 22},
    "paschalis": {"s01": 65},
    "paschalis-in-die": {"s01": 66},
    "paschalis-in-nocte": {"s01": 66},
    "quadragesimae": {"s02": 15, "s03": 6, "s04": 15, "s05": 10, "s06": 9, "s07": 12},
    "sacratissimi-cordis-iesu": {"s02": 15, "s03": 6, "s04": 37, "s05": 22},
    "sanctae-crucis": {"s02": 15, "s03": 6, "s04": 28, "s05": 10, "s06": 9, "s07": 12},
    "sancti-ioseph-in-festivitate": dict(zip(SEVEN, (15, 6, 12, 35, 10, 9, 12), strict=True)),
    "sancti-ioseph-in-solemnitate": dict(zip(SEVEN, (15, 6, 12, 35, 10, 9, 12), strict=True)),
    "sanctissimae-trinitatis": {"s02": 15, "s03": 6, "s04": 24, "s05": 20, "s06": 19, "s07": 17},
    "spiritus-sancti": {"s02": 66},
}
TEXTS = [PREFIX + slug for slug in sorted(VERSES)]
VERSE_CASES = [
    pytest.param(PREFIX + slug, sid, id=f"{slug}-{sid}")
    for slug in sorted(VERSES)
    for sid in VERSES[slug]
]


def slug_of(text_id: str) -> str:
    return text_id.removeprefix(PREFIX)


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


def word_ids(text_id: str, sid: str) -> list[str]:
    rows = VERSES[slug_of(text_id)]
    first = 1 + sum(count for other, count in rows.items() if other < sid)
    return [f"w{number:03d}" for number in range(first, first + rows[sid])]


def selected_prefaces() -> set[str]:
    """The Preface texts the formularies select in their Preface role."""
    found: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, dict):
            if value.get("role") == "praefatio":
                found.add(value["text"])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    for path in sorted((CORPUS / "formularies").rglob("*.json")):
        visit(json.loads(path.read_text(encoding="utf-8")))
    return found


def test_the_inventory_is_every_preface_the_formularies_select():
    assert len(VERSES) == 24
    assert sum(len(rows) for rows in VERSES.values()) == 116
    assert sum(sum(rows.values()) for rows in VERSES.values()) == 1874
    on_disk = {
        "ordinarium." + path.stem
        for path in (CORPUS / "texts" / "ordinarium").glob("praefatio-*.json")
    }
    assert on_disk == {*TEXTS, DIALOGUE}
    assert selected_prefaces() == set(TEXTS)
    assert set(delivery.PREFACE_BODIES) == set(VERSES)
    for slug, rows in VERSES.items():
        first, counts = delivery.PREFACE_BODIES[slug]
        assert [f"s{number:02d}" for number in range(first, first + len(counts))] == list(rows)
        assert counts == tuple(rows.values())


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
def test_each_preface_passes_every_layer_with_one_override_per_verse(text_id):
    doc = text(text_id)
    rows = VERSES[slug_of(text_id)]
    assert [s["id"] for s in verses(doc)] == list(rows)
    assert delivery.check_doc(doc) == ([], len(rows))
    assert participation.check_doc(doc) == ([], 0)
    assert check_orations(doc) == ([], 0)
    rubrics = [s for s in doc["segments"] if s["type"] == "rubric"]
    assert [s["id"] for s in rubrics] == ([] if "s01" in rows else ["s01"])
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
    rows = VERSES[slug_of(text_id)]
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
    for sid in VERSES[slug_of(text_id)]:
        for key, wrong in (("speaker", "minister"), ("voice", "secreto")):
            doc = deepcopy(original)
            segment(doc, sid)[key] = wrong
            errors, overridden = delivery.check_doc(doc)
            assert f"{sid}: preface low-Mass base must be sacerdos/clara" in errors
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
    assert f"{first['id']}: preface verse must hold {ids[0]}-{ids[-1]}" in errors
    assert overridden == 0
    assert all(delivery.derive(doc, s) == {} for s in doc["segments"])
    assert delivery.check_doc(original)[0] == []


def remove(text_id: str, sid: str) -> Callable[[dict[str, Any]], None]:
    return lambda doc: doc["segments"].remove(segment(doc, sid))


def extra(doc: dict[str, Any]) -> None:
    doc["segments"].append({**deepcopy(segment(doc, "s06")), "id": "s07"})


def reorder(doc: dict[str, Any]) -> None:
    segments = doc["segments"]
    segments[2], segments[3] = segments[3], segments[2]


def moved_word(doc: dict[str, Any]) -> None:
    segment(doc, "s03")["words"].insert(0, segment(doc, "s02")["words"].pop())


def paschal_rubric(doc: dict[str, Any]) -> None:
    doc["segments"].insert(0, {"id": "s00", "type": "rubric", "text": "Deinde disiungit manus."})


def split_verse(doc: dict[str, Any]) -> None:
    whole = segment(doc, "s02")
    doc["segments"].append({**deepcopy(whole), "id": "s03", "words": whole["words"][35:]})
    del whole["words"][35:]


def retype(sid: str, kind: str) -> Callable[[dict[str, Any]], None]:
    return lambda doc: segment(doc, sid).update(type=kind)


COMMON = PREFIX + "communis"
COMMON_SEGMENTS = "preface: segments must be the rubric s01 and the verses s02-s06"
BAD_SUBJECTS: dict[str, tuple[str, Callable[[dict[str, Any]], None], str]] = {
    "missing-verse": (COMMON, remove(COMMON, "s04"), COMMON_SEGMENTS),
    "extra-verse": (COMMON, extra, COMMON_SEGMENTS),
    "reordered": (COMMON, reorder, COMMON_SEGMENTS),
    "rubric-made-verse": (COMMON, retype("s01", "verse"), COMMON_SEGMENTS),
    "verse-made-rubric": (
        COMMON,
        retype("s05", "rubric"),
        "s05: preface verse must hold w036-w044",
    ),
    "moved-word": (COMMON, moved_word, "s02: preface verse must hold w001-w015"),
    "paschal-rubric-added": (
        PREFIX + "paschalis",
        paschal_rubric,
        "preface: segments must be the verse s01",
    ),
    "single-verse-split": (
        PREFIX + "ascensionis",
        split_verse,
        "preface: segments must be the rubric s01 and the verse s02",
    ),
    "rubric-dropped": (
        PREFIX + "sanctissimae-trinitatis",
        remove(PREFIX + "sanctissimae-trinitatis", "s01"),
        "preface: segments must be the rubric s01 and the verses s02-s07",
    ),
}


@pytest.mark.parametrize("fault", list(BAD_SUBJECTS))
def test_a_changed_preface_is_reported_not_copied_into_the_sung_form(fault):
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
    assert delivery.check_doc(original) == ([], len(VERSES[slug_of(text_id)]))


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


WRITTEN = [
    PREFIX + "communis",
    PREFIX + "paschalis",
    PREFIX + "ascensionis",
    PREFIX + "sanctissimae-trinitatis",
]


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
    rows = VERSES[slug_of(text_id)]
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
def test_the_writer_refuses_a_changed_preface(tmp_path, monkeypatch, capsys, fault):
    text_id, change, owned = BAD_SUBJECTS[fault]
    (target,) = corpus_copy(tmp_path, monkeypatch, text_id)
    doc = json.loads(target.read_text(encoding="utf-8"))
    change(doc)
    target.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    spoiled = target.read_bytes()
    assert delivery.run(write=True) >= 1
    assert f"delivery: {text_id} {owned}\n" in capsys.readouterr().out
    assert target.read_bytes() == spoiled


def test_an_uninventoried_preface_is_refused_rather_than_left_unmodeled(
    tmp_path, monkeypatch, capsys
):
    doc = text(COMMON)
    doc["id"] = PREFIX + "uninventoried"
    errors, overridden = delivery.check_doc(doc)
    assert errors[0] == UNKNOWN and overridden == 0
    assert all(delivery.derive(doc, s) == {} for s in doc["segments"])
    for seg in verses(doc):
        del seg["delivery"]
    assert delivery.check_doc(doc) == ([UNKNOWN], 0)
    target = tmp_path / "texts" / "ordinarium" / "praefatio-uninventoried.json"
    target.parent.mkdir(parents=True)
    target.write_text(formatted(doc), encoding="utf-8")
    monkeypatch.setattr(delivery, "ROOT", tmp_path)
    unwritten = target.read_bytes()
    assert delivery.run(write=True) == 1
    assert f"delivery: {doc['id']} {UNKNOWN}\n" in capsys.readouterr().out
    assert target.read_bytes() == unwritten


def test_a_preface_under_another_id_takes_nothing():
    doc = text(COMMON)
    doc["id"] = "ordinarium.vere-dignum"
    assert all(delivery.derive(doc, s) == {} for s in doc["segments"])
    for seg in verses(doc):
        del seg["delivery"]
    assert delivery.check_doc(doc) == ([], 0)


# The Last Gospel and the prayers at the foot of the altar repeat the
# dialogue's words; the Sanctus follows the Preface with the same low-Mass
# base; the Canon begins after it. None of them is part of the Preface.
COUNTEREXAMPLES = (
    "ordinarium.evangelium-ultimum",
    "ordinarium.deus-tu-conversus",
    "ordinarium.iudica-me",
    "ordinarium.sanctus",
    "ordinarium.te-igitur",
)


@pytest.mark.parametrize("text_id", COUNTEREXAMPLES)
def test_other_ordinary_texts_take_nothing_from_the_rule(text_id):
    doc = text(text_id)
    # No counterexample inherits the Preface rule. Sanctus instead has its own
    # explicit quiet-priest rule: it is not a sung priestly Preface line.
    assert not doc["id"].startswith(PREFIX)
    expected = {}
    if text_id == "ordinarium.sanctus":
        assert [s["id"] for s in doc["segments"]] == ["s01", "s02", "s03", "s04", "s05", "s06"]
        assert doc["segments"][0]["type"] == "rubric"
        for s in doc["segments"][1:]:
            assert s["type"] == "verse"
            assert (s["speaker"], s["voice"]) == ("sacerdos", "clara")
            expected[s["id"]] = {"cantu": {"voice": "secreto"}}
    for s in doc["segments"]:
        if s["id"] not in expected:
            assert "delivery" not in s
        assert s.get("delivery", {}) == expected.get(s["id"], {})
        assert delivery.derive(doc, s) == expected.get(s["id"], {})
    assert delivery.check_doc(doc) == ([], len(expected))


@pytest.mark.parametrize("text_id", TEXTS)
def test_the_overlay_binds_exactly_the_delivery_additions(text_id):
    doc = text(text_id)
    change = DATA["source"][text_id]
    assert list(change) == list(VERSES[slug_of(text_id)])
    historical = without_preface_delivery(doc)
    assert historical["segments"] == [
        {key: value for key, value in s.items() if key != "delivery"} for s in doc["segments"]
    ]
    assert {key: value for key, value in historical.items() if key != "segments"} == {
        key: value for key, value in doc.items() if key != "segments"
    }
    for seg in verses(doc):
        entry = change[seg["id"]]
        assert entry["delivery"] == seg["delivery"] == CALL
        assert canonical_hash(source_payload(seg)) == entry["after"]
        assert canonical_hash(source_payload(segment(historical, seg["id"]))) == entry["before"]
        assert current_source_hash(text_id, seg["id"], entry["before"]) == entry["after"]
    selected = DATA["selected"][text_id]
    assert bindings.digest(bindings.selected_text(doc)) == selected["after"]
    assert bindings.digest(bindings.selected_text(historical)) == selected["before"]
    assert current_selected_hash(text_id, selected["before"]) == selected["after"]


@pytest.mark.parametrize("language", ("pl", "en"))
def test_every_preface_ledger_row_advances_only_its_source_hash(language):
    ledger = json.loads(
        (CORPUS / "languages" / language / "translation-provenance.json").read_text(
            encoding="utf-8"
        )
    )["sites"]
    rows = [row for row in ledger if row["text"] in DATA["source"]]
    assert len(rows) == 116
    for row in rows:
        change = DATA["source"][row["text"]][row["segment"]]
        previous = {**row, "source_sha256": change["before"]}
        snapshot = deepcopy(row)
        assert current_expected_row(previous) == row
        assert row == snapshot
        assert row["source_sha256"] == change["after"]
    other = next(row for row in ledger if row["text"] not in DATA["source"])
    assert current_expected_row(other) == other


def without_ascension_vigil_preface_occurrence(graph):
    """Assert the exact retained occurrence before recovering the historical subset."""
    expected = {
        "id": "use.ordinarium.praefatio-paschalis.ascension-vigil.selection.mr1962",
        "edition": "edition.missale-romanum.1962-typica",
        "digital_item": "item.missale-romanum.1962-typica.ia",
        "role": "rubric_control",
        "address": {
            "kind": "text",
            "text": "ordinarium.praefatio-paschalis",
        },
        "locator": {
            "printed": "p.344",
            "scan": "leaf n425 / PDF p.426",
            "section": "In vigilia Ascensionis; Praefatio paschalis cue after the Secret",
            "page_url": "https://archive.org/details/missale-romanum-1962/page/n425/mode/1up",
        },
        "claim": (
            "The Ascension Vigil explicitly directs Praefatio paschalis after its "
            "Secret. This establishes Easter Preface selection for this proper. "
            "The complete Preface wording and its performance remain supported by "
            "their separate sources."
        ),
        "verified_on": "2026-10-25",
        "evidence_sha256": "9601a7fc0b8994e3d490e74ecf9745eb3779fe8a6fae5e535d623a1ecf86c46f",
        "decision": "RETAIN",
        "decision_reason": (
            "Benziger p.344 / leaf n425 explicitly directs Praefatio paschalis after the Vigil "
            "Secret. Retain this selection cue only; complete Preface wording and performance "
            "remain dependent on their separate sources."
        ),
    }
    observed = [row for row in graph["uses"] if row["id"] == expected["id"]]
    assert observed == [expected], "current Ascension Vigil Preface occurrence"
    result = deepcopy(graph)
    result["uses"] = [row for row in result["uses"] if row["id"] != expected["id"]]
    return result


def graph_records(graph: dict[str, Any], text_id: str) -> dict[str, list[dict[str, Any]]]:
    return {
        key: [r for r in graph[key] if r.get("text", r.get("address", {}).get("text")) == text_id]
        for key in ("uses", "witnesses", "collations")
    }


def without_apparatus_hash(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "apparatus_sha256"}


def test_the_graph_overlay_is_exactly_the_stored_selected_text_digests():
    graph = json.loads((CORPUS / "bibliography" / "graph.json").read_text(encoding="utf-8"))
    graph = without_common_preface_source_chain(graph)
    graph = without_ascension_vigil_preface_occurrence(graph)
    collations = [row for row in graph["collations"] if row["text"] in DATA["source"]]
    assert len(collations) == 23
    assert sorted(row["id"] for row in collations) == sorted(DATA["collation_records"])
    assert {row["text"] for row in collations} == set(TEXTS) - {COMMON}
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
            assert current_record_hash(current["id"], record["before"]) == record["after"]
    for text_id in TEXTS:
        sets = DATA["graph_sets"][text_id]
        assert bindings.digest(before_privacy(graph_records(graph, text_id))) == sets["after"]
        assert bindings.digest(before_privacy(graph_records(historical, text_id))) == sets["before"]
        assert current_graph_hash(text_id, sets["before"]) == sets["after"]


def test_the_witness_overlay_is_exactly_the_current_and_historical_subjects():
    graph = json.loads((CORPUS / "bibliography" / "graph.json").read_text(encoding="utf-8"))
    graph = without_common_preface_source_chain(graph)
    snapshot = bindings._SourceSnapshot(CORPUS, graph)
    rows = [row for row in graph["witnesses"] if row["text"] in DATA["source"]]
    assert len(rows) == 46
    assert sorted(row["id"] for row in rows) == sorted(DATA["witness_subjects"])
    for row in rows:
        doc = text(row["text"])
        expected = DATA["witness_subjects"][row["id"]]
        current = bindings._witness_subject(CORPUS, row, doc, snapshot, reviewable=False)
        old = bindings._witness_subject(
            CORPUS, row, without_preface_delivery(doc), snapshot, reviewable=False
        )
        assert bindings.digest(before_privacy(current)) == expected["after"]
        assert bindings.digest(before_privacy(old)) == expected["before"]
        assert current_witness_hash(row["id"], expected["before"]) == expected["after"]


STALE: dict[str, tuple[Callable[[], object], str]] = {
    "source-preimage": (
        lambda: current_source_hash(COMMON, "s02", "0" * 64),
        "historical Preface source hash",
    ),
    "source-segment": (
        lambda: current_source_hash(COMMON, "s01", "0" * 64),
        "Preface source segment identity",
    ),
    "row-preimage": (
        lambda: current_expected_row(
            {"site": COMMON + ".s02.pl", "text": COMMON, "segment": "s02", "source_sha256": "0"}
        ),
        "historical Preface source hash",
    ),
    "selected": (
        lambda: current_selected_hash(COMMON, "0" * 64),
        "historical Preface selected hash",
    ),
    "graph": (
        lambda: current_graph_hash(COMMON, "0" * 64),
        "historical Preface graph_sets hash",
    ),
    "record": (
        lambda: current_record_hash(next(iter(DATA["collation_records"])), "0" * 64),
        "historical Preface collation_records hash",
    ),
    "witness": (
        lambda: current_witness_hash(next(iter(DATA["witness_subjects"])), "0" * 64),
        "historical Preface witness_subjects hash",
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
        "current Preface delivery inverse",
        lambda seg: seg["delivery"]["cantu"].update(voice="clara"),
    ),
    "performer": (
        "current Preface delivery inverse",
        lambda seg: seg["delivery"]["cantu"].update(speaker="schola"),
    ),
    "missing": ("current Preface delivery inverse", lambda seg: seg.pop("delivery")),
    "topology": ("current Preface inverse topology", lambda seg: seg.update(type="rubric")),
}


@pytest.mark.parametrize("damage", list(INVERSE_DAMAGE))
def test_the_inverse_refuses_a_preface_that_is_not_exactly_the_recorded_one(damage):
    message, change = INVERSE_DAMAGE[damage]
    original = text(PREFIX + "sanctissimae-trinitatis")
    doc = deepcopy(original)
    change(segment(doc, "s05"))
    with pytest.raises(AssertionError, match=f"^{message}"):
        without_preface_delivery(doc)
    assert without_preface_delivery(original) != original


def test_the_inverse_keeps_every_other_field_and_passes_other_texts_through():
    pristine = deepcopy(DATA)
    doc = text(PREFIX + "sanctissimae-trinitatis")
    segment(doc, "s05")["words"][0]["form"] = "unreviewed"
    doc["editorial"]["notes"] = doc["editorial"].get("notes", "") + " Retained."
    restored = without_preface_delivery(doc)
    assert segment(restored, "s05")["words"][0]["form"] == "unreviewed"
    assert restored["editorial"] == doc["editorial"]
    assert not any("delivery" in s for s in restored["segments"])
    for other in (DIALOGUE, "ordinarium.sanctus", "proprium.nativitas-domini-in-nocte-collecta"):
        current = text(other)
        copy = without_preface_delivery(current)
        assert copy == current and copy is not current
        assert current_selected_hash(other, "unchanged") == "unchanged"
    assert current_source_hash(DIALOGUE, "s02", "unchanged") == "unchanged"
    assert pristine == DATA
