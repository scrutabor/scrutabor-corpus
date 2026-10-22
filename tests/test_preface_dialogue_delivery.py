"""The Preface dialogue is sung at a sung Mass, by a rule for its six verses.

RG 513 a and 514 have the celebrant sing his three calls; DMS 16 b, 25 a and
26 have the schola and people sing the three answers. The low-Mass base and
the DMS participation stay as they are, and the same words elsewhere in the
Ordinary take nothing from the rule.
"""

import json
import shutil
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from checks import delivery, participation
from checks.orations import check_doc as check_orations
from checks.orations import sung_delivery, tokens

CORPUS = Path(__file__).resolve().parent.parent
DIALOGUE = "ordinarium.praefatio-dialogus"
CALL = {"cantu": {"speaker": "sacerdos", "voice": "cantus"}}
ANSWER = {"cantu": {"speaker": "schola", "voice": "cantus"}}
SUNG = {"s02": CALL, "s03": ANSWER, "s04": CALL, "s05": ANSWER, "s06": CALL, "s07": ANSWER}
BASE = {
    "s02": "sacerdos",
    "s03": "minister",
    "s04": "sacerdos",
    "s05": "minister",
    "s06": "sacerdos",
    "s07": "minister",
}
DMS = {"lecta": {"gradus": 1, "source": "DMS 31 a"}, "cantu": {"gradus": 1, "source": "DMS 25 a"}}
TOPOLOGY = "preface dialogue: segments must be the rubric s01 and the six verses s02-s07"


def path_of(text_id: str) -> Path:
    category, name = text_id.split(".", 1)
    return CORPUS / "texts" / category / f"{name}.json"


def text(text_id: str) -> dict[str, Any]:
    return json.loads(path_of(text_id).read_text(encoding="utf-8"))


def segment(doc: dict[str, Any], sid: str) -> dict[str, Any]:
    matches = [s for s in doc["segments"] if s["id"] == sid]
    assert len(matches) == 1
    return matches[0]


@pytest.mark.parametrize("sid", list(SUNG))
def test_each_verse_carries_its_sung_override(sid):
    doc = text(DIALOGUE)
    seg = segment(doc, sid)
    assert seg["delivery"] == SUNG[sid]
    assert delivery.derive(doc, seg) == SUNG[sid]


def test_the_dialogue_passes_every_layer_with_six_overrides():
    doc = text(DIALOGUE)
    assert delivery.check_doc(doc) == ([], 6)
    assert participation.check_doc(doc) == ([], 3)
    assert check_orations(doc) == ([], 1)
    rubric = segment(doc, "s01")
    assert rubric["type"] == "rubric"
    assert delivery.derive(doc, rubric) == {}
    assert not {"delivery", "speaker", "voice", "participation"} & set(rubric)


def test_the_answers_take_the_model_of_an_orations_sung_amen():
    assert sung_delivery("response") == ANSWER
    assert sung_delivery("body") == CALL
    amen = segment(text("proprium.nativitas-domini-in-nocte-collecta"), "s02")
    assert tokens(amen) == ("amen",)
    dialogue = text(DIALOGUE)
    for sid in ("s03", "s05", "s07"):
        answer = segment(dialogue, sid)
        for key in ("speaker", "voice", "delivery", "participation"):
            assert answer[key] == amen[key]


def test_the_low_mass_base_words_and_participation_are_unchanged():
    doc = text(DIALOGUE)
    verses = [s for s in doc["segments"] if s["type"] == "verse"]
    assert [s["id"] for s in verses] == list(SUNG)
    for seg in verses:
        assert (seg["speaker"], seg["voice"]) == (BASE[seg["id"]], "clara")
        assert set(seg["delivery"]) == {"cantu"}
        if BASE[seg["id"]] == "minister":
            assert seg["participation"] == DMS
        else:
            assert "participation" not in seg
        assert participation.derive(doc, seg) == seg.get("participation", {})
    assert [w["id"] for s in verses for w in s["words"]] == [f"w{i:03d}" for i in range(1, 21)]
    assert [" ".join(tokens(s)) for s in verses] == [
        "dominus vobiscum",
        "et cum spiritu tuo",
        "sursum corda",
        "habemus ad dominum",
        "gratias agamus domino deo nostro",
        "dignum et iustum est",
    ]


def spoil(seg: dict[str, Any], fault: str) -> None:
    if fault == "removed":
        del seg["delivery"]
    elif fault == "wrong-voice":
        seg["delivery"]["cantu"]["voice"] = "clara"
    else:
        seg["delivery"]["cantu"]["speaker"] = "schola" if BASE[seg["id"]] == "sacerdos" else "omnes"


FAULTS = ("removed", "wrong-voice", "wrong-performer")


@pytest.mark.parametrize("fault", FAULTS)
@pytest.mark.parametrize("sid", list(SUNG))
def test_a_missing_or_wrong_override_fails_with_its_own_diagnostic(sid, fault):
    original = text(DIALOGUE)
    pristine = deepcopy(original)
    doc = deepcopy(original)
    seg = segment(doc, sid)
    spoil(seg, fault)
    have = seg.get("delivery") or "absent"
    assert delivery.check_doc(doc) == (
        [f"{sid}: delivery {have} — the Mass forms require {SUNG[sid]}"],
        6,
    )
    assert delivery.derive(doc, seg) == SUNG[sid]
    assert original == pristine
    assert delivery.check_doc(original) == ([], 6)


@pytest.fixture
def tmp_dialogue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A one-text corpus holding a copy of the committed dialogue."""
    target = tmp_path / "texts" / "ordinarium" / "praefatio-dialogus.json"
    target.parent.mkdir(parents=True)
    shutil.copyfile(path_of(DIALOGUE), target)
    monkeypatch.setattr(delivery, "ROOT", tmp_path)
    return target


def rewrite(path: Path, change: Callable[[dict[str, Any]], object]) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    change(doc)
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return doc


@pytest.mark.parametrize("fault", FAULTS)
@pytest.mark.parametrize("sid", list(SUNG))
def test_a_spoiled_copy_fails_and_the_writer_restores_the_committed_bytes(
    tmp_dialogue, capsys, sid, fault
):
    committed = tmp_dialogue.read_bytes()
    doc = rewrite(tmp_dialogue, lambda d: spoil(segment(d, sid), fault))
    have = segment(doc, sid).get("delivery") or {}
    assert delivery.run() == 1
    out = capsys.readouterr().out
    assert out == (
        f"delivery: {DIALOGUE} {sid} carries {have!r}, the Mass forms require {SUNG[sid]!r}\n"
        "delivery: FAIL 5 form-specific segment overrides\n"
    )
    assert delivery.run(write=True) == 0
    assert tmp_dialogue.read_bytes() == committed
    capsys.readouterr()
    assert delivery.run() == 0
    assert capsys.readouterr().out == "delivery: OK 6 form-specific segment overrides\n"


def reorder(doc: dict[str, Any]) -> None:
    segments = doc["segments"]
    segments[3], segments[4] = segments[4], segments[3]


def extra(doc: dict[str, Any]) -> None:
    doc["segments"].append({**deepcopy(segment(doc, "s07")), "id": "s08"})


def word(doc: dict[str, Any], sid: str, index: int) -> dict[str, Any]:
    return segment(doc, sid)["words"][index]


BAD_SUBJECTS: dict[str, tuple[Callable[[dict[str, Any]], object], str]] = {
    "base-actor": (
        lambda d: segment(d, "s03").update(speaker="sacerdos"),
        "s03: preface dialogue low-Mass base must be minister/clara",
    ),
    "base-voice": (
        lambda d: segment(d, "s02").update(voice="cantus"),
        "s02: preface dialogue low-Mass base must be sacerdos/clara",
    ),
    "missing-segment": (lambda d: d["segments"].remove(segment(d, "s05")), TOPOLOGY),
    "extra-segment": (extra, TOPOLOGY),
    "reordered": (reorder, TOPOLOGY),
    "rubric-made-verse": (lambda d: segment(d, "s01").update(type="verse"), TOPOLOGY),
    "changed-response": (
        lambda d: word(d, "s03", 3).update(form="meo"),
        "s03: preface dialogue verse must read 'et cum spiritu tuo' as w003-w006",
    ),
    "renumbered-word": (
        lambda d: word(d, "s07", 0).update(id="w099"),
        "s07: preface dialogue verse must read 'dignum et iustum est' as w017-w020",
    ),
}


@pytest.mark.parametrize("fault", list(BAD_SUBJECTS))
def test_a_changed_subject_is_reported_not_copied_into_the_sung_form(fault):
    change, owned = BAD_SUBJECTS[fault]
    original = text(DIALOGUE)
    pristine = deepcopy(original)
    doc = deepcopy(original)
    change(doc)
    errors, overridden = delivery.check_doc(doc)
    assert owned in errors
    assert overridden == 0
    assert all(delivery.derive(doc, s) == {} for s in doc["segments"])
    assert original == pristine
    assert delivery.check_doc(original) == ([], 6)


@pytest.mark.parametrize("fault", list(BAD_SUBJECTS))
def test_the_writer_refuses_a_changed_subject(tmp_dialogue, capsys, fault):
    change, owned = BAD_SUBJECTS[fault]
    rewrite(tmp_dialogue, change)
    spoiled = tmp_dialogue.read_bytes()
    assert delivery.run(write=True) >= 1
    assert f"delivery: {DIALOGUE} {owned}\n" in capsys.readouterr().out
    assert tmp_dialogue.read_bytes() == spoiled


COUNTEREXAMPLES = (
    ("ordinarium.evangelium-ultimum", "s02", ("dominus", "vobiscum")),
    ("ordinarium.evangelium-ultimum", "s03", ("et", "cum", "spiritu", "tuo")),
    ("ordinarium.deus-tu-conversus", "s08", ("dominus", "vobiscum")),
    ("ordinarium.deus-tu-conversus", "s09", ("et", "cum", "spiritu", "tuo")),
    ("ordinarium.aufer-a-nobis", "s02", ("oremus",)),
)


@pytest.mark.parametrize(("text_id", "sid", "said"), COUNTEREXAMPLES)
def test_the_same_words_elsewhere_take_nothing_from_the_rule(text_id, sid, said):
    doc = text(text_id)
    seg = segment(doc, sid)
    assert tokens(seg) == said
    assert "delivery" not in seg
    assert delivery.derive(doc, seg) == {}
    assert delivery.check_doc(doc) == ([], 0)


@pytest.mark.parametrize("text_id", ("ordinarium.evangelium-ultimum", "ordinarium.ite-missa-est"))
def test_an_identical_segment_in_another_text_takes_nothing(text_id):
    dialogue = text(DIALOGUE)
    other = text(text_id)
    for sid in ("s02", "s03"):
        same = {key: value for key, value in segment(dialogue, sid).items() if key != "delivery"}
        assert segment(other, sid) == same
        assert delivery.derive(other, segment(other, sid)) == {}


def test_no_other_ordinary_text_is_modeled_by_implication():
    modeled: set[str] = set()
    for path in sorted((CORPUS / "texts" / "ordinarium").glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        if any(delivery.derive(doc, s) for s in doc["segments"]):
            modeled.add(doc["id"])
    assert modeled == {DIALOGUE, "ordinarium.ite-missa-est-paschale"}
