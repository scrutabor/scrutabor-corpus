"""Source-bounded oration splits, with no canonical fixture migration."""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from checks import attribute, delivery, orations, participation

ROOT = Path(__file__).resolve().parent.parent
NIGHT = "proprium.nativitas-domini-in-nocte-"
DAWN = orations.DAWN


def text(text_id):
    category, name = text_id.split(".", 1)
    return json.loads((ROOT / "texts" / category / f"{name}.json").read_text())


def verses(doc):
    return [s for s in doc["segments"] if s["type"] == "verse"]


def corrected(text_id):
    """Split the existing words in memory, allocating only new segment IDs."""
    doc = text(text_id)
    if not orations.structure(doc)[0]:
        return doc
    sequence = [w for s in verses(doc) for w in s["words"]]
    piece = orations.genus(doc)
    rebuilt = []

    def new(words):
        number = doc["ids"]["segments"]["next"]
        doc["ids"]["segments"]["next"] += 1
        return {"id": f"s{number:02d}", "type": "verse", "words": words}

    for seg in doc["segments"]:
        if seg["type"] != "verse" or (text_id == DAWN + "secreta" and seg["id"] == "s01"):
            rebuilt.append(seg)
            continue
        words = seg["words"]
        assert orations.tokens(seg)[-5:] == (*orations.TAIL, "amen")
        seg["words"] = words[:-5] if piece == "secreta" else words[:-1]
        rebuilt.append(seg)
        if piece == "secreta":
            rebuilt.append(new(words[-5:-1]))
        rebuilt.append(new(words[-1:]))
    doc["segments"] = rebuilt
    attrs = orations.base_attributes(doc)
    assert attrs
    for seg in verses(doc):
        seg.update(attrs[seg["id"]])
        for field, derive in (
            ("delivery", delivery.derive),
            ("participation", participation.derive),
        ):
            value = derive(doc, seg)
            if value:
                seg[field] = value
            else:
                seg.pop(field, None)
    assert [w for s in verses(doc) for w in s["words"]] == sequence
    return doc


@pytest.mark.parametrize("prefix", [NIGHT, DAWN])
@pytest.mark.parametrize("piece", ["collecta", "postcommunio", "secreta"])
def test_corrected_complete_boundaries_and_derived_fields(prefix, piece):
    doc = corrected(prefix + piece)
    assert orations.check_doc(doc) == ([], 1)
    assert delivery.check_doc(doc)[0] == []
    assert participation.check_doc(doc)[0] == []


@pytest.mark.parametrize("piece", ["collecta", "postcommunio"])
def test_priest_sings_body_but_schola_and_people_answer(piece):
    doc = corrected(NIGHT + piece)
    body, response = verses(doc)
    assert body["delivery"] == {"cantu": {"speaker": "sacerdos", "voice": "cantus"}}
    assert participation.derive(doc, body) == {}
    assert response["speaker"] == "minister"
    assert response["voice"] == "clara"
    assert response["delivery"] == {"cantu": {"speaker": "schola", "voice": "cantus"}}
    assert response["participation"] == {
        "lecta": {"gradus": 1, "source": "DMS 31 a"},
        "cantu": {"gradus": 1, "source": "DMS 25 a"},
    }


def test_only_the_final_secret_has_an_audible_tail():
    doc = corrected(DAWN + "secreta")
    nonfinal, body, tail, response = verses(doc)
    assert nonfinal["words"][-1]["id"] == "w054"
    assert nonfinal["speaker"] == "sacerdos" and nonfinal["voice"] == "secreto"
    assert delivery.derive(doc, nonfinal) == participation.derive(doc, nonfinal) == {}
    assert body["voice"] == "secreto"
    assert [w["id"] for w in tail["words"]] == ["w091", "w092", "w093", "w094"]
    assert tail["speaker"] == "sacerdos" and tail["voice"] == "clara"
    assert tail["delivery"] == {"cantu": {"speaker": "sacerdos", "voice": "cantus"}}
    assert participation.derive(doc, tail) == {}
    assert response["words"][0]["id"] == "w095"


@pytest.mark.parametrize("piece", ["collecta", "postcommunio", "secreta"])
def test_reabsorbed_amen_fails_without_receiving_new_derived_labels(piece):
    doc = corrected(NIGHT + piece)
    previous, response = verses(doc)[-2:]
    previous["words"] += response["words"]
    doc["segments"].remove(response)
    errors, count = orations.check_doc(doc)
    assert count == 1 and any("absorbed" in e for e in errors)
    assert orations.base_attributes(doc) == {}
    for seg in verses(doc):
        assert delivery.derive(doc, seg) == participation.derive(doc, seg) == {}


@pytest.mark.parametrize(
    "position,field,value,message",
    [
        (0, "speaker", "schola", "speaker must be sacerdos"),
        (0, "voice", "secreto", "voice must be clara"),
        (-1, "speaker", "sacerdos", "speaker must be minister"),
        (-1, "voice", "secreto", "voice must be clara"),
    ],
)
def test_wrong_low_mass_role_or_voice_is_rejected(position, field, value, message):
    doc = corrected(NIGHT + "collecta")
    seg = verses(doc)[position]
    seg[field] = value
    seg.pop("participation", None)
    errors, _ = orations.check_doc(doc)
    assert any(message in e for e in errors)
    if position == -1:
        assert any("participation must be" in e for e in errors)


@pytest.mark.parametrize(
    "field,value",
    [
        ("delivery", {}),
        ("delivery", {"cantu": {"speaker": "sacerdos", "voice": "cantus"}}),
        ("participation", {}),
    ],
)
def test_response_requires_correct_sung_delivery_and_participation(field, value):
    doc = corrected(NIGHT + "collecta")
    verses(doc)[-1][field] = value
    assert any(f"{field} must be" in e for e in orations.check_doc(doc)[0])


def test_wrong_secret_tail_volume_and_extra_word_fail():
    doc = corrected(NIGHT + "secreta")
    tail = verses(doc)[1]
    tail["voice"] = "secreto"
    assert any("voice must be clara" in e for e in orations.check_doc(doc)[0])
    tail["words"].insert(0, {"id": "w999", "form": "Deus"})
    assert any("exactly Per omnia" in e for e in orations.check_doc(doc)[0])
    assert delivery.derive(doc, tail) == {}


def test_nonfinal_dawn_amen_cannot_be_split_into_a_response():
    doc = corrected(DAWN + "secreta")
    first = verses(doc)[0]
    response = {
        "id": "s99",
        "type": "verse",
        "speaker": "minister",
        "voice": "clara",
        "words": [first["words"].pop()],
    }
    doc["segments"].insert(1, response)
    assert any("Dawn nonfinal" in e for e in orations.check_doc(doc)[0])
    assert participation.derive(doc, response) == delivery.derive(doc, response) == {}


def test_dawn_exception_requires_actual_following_prayer_and_identity():
    doc = corrected(DAWN + "secreta")
    doc["segments"] = doc["segments"][:1]
    assert any("Dawn nonfinal" in e for e in orations.check_doc(doc)[0])
    doc = corrected(DAWN + "secreta")
    verses(doc)[1]["words"][0]["form"] = "Alienum"
    assert any("Dawn nonfinal" in e for e in orations.check_doc(doc)[0])
    doc = corrected(DAWN + "secreta")
    doc["id"] = "proprium.other-secreta"
    assert any("absorbed" in e for e in orations.check_doc(doc)[0])


def test_nonfinal_dawn_keeps_priest_role_even_when_labels_are_changed():
    doc = corrected(DAWN + "secreta")
    verses(doc)[0].update(speaker="minister", voice="clara")
    errors, _ = orations.check_doc(doc)
    assert any("speaker must be sacerdos" in e for e in errors)
    assert any("voice must be secreto" in e for e in errors)
    assert participation.derive(doc, verses(doc)[0]) == {}


@pytest.mark.parametrize("piece", ["collecta", "postcommunio", "secreta"])
def test_attribute_proposes_correct_split_roles_not_genus_wide_silence(piece, monkeypatch):
    doc = corrected(DAWN + piece)
    # Isolate the general-rubric rule, not a claimed new textual collation.
    monkeypatch.setattr(attribute, "marked_lines", lambda *_a, **_k: [])
    monkeypatch.setattr(attribute, "span_covers", lambda _d: True)
    for seg in verses(doc):
        seg.pop("speaker", None)
        seg.pop("voice", None)
    assert attribute.propose(doc) == orations.base_attributes(doc)


def test_attribute_does_not_override_stale_witness_safety(monkeypatch):
    doc = corrected(NIGHT + "secreta")
    monkeypatch.setattr(attribute, "marked_lines", lambda *_a, **_k: [])
    monkeypatch.setattr(attribute, "span_covers", lambda _d: False)
    proposed = attribute.propose(doc)
    assert all(p.get("speaker") != "minister" for p in proposed.values())
    assert proposed[verses(doc)[1]["id"]].get("voice") != "clara"


def test_attribute_reports_the_actual_boundary_ruling_against_a_secret_rubric(monkeypatch):
    doc = corrected(NIGHT + "secreta")
    doc["segments"].insert(0, {"id": "s99", "type": "rubric", "text": "Secreto"})
    monkeypatch.setattr(attribute, "marked_lines", lambda *_a, **_k: [])
    monkeypatch.setattr(attribute, "span_covers", lambda _d: True)
    disagreements = []
    attribute.propose(doc, disagreements)
    assert len(disagreements) == 2
    assert all("RG 480–481" in message for message in disagreements)


@pytest.mark.parametrize(
    "text_id,sid",
    [
        ("ordinarium.misereatur-tui", "s03"),
        ("ordinarium.orate-fratres", "s06"),
        ("ordinarium.pater-noster", "s14"),
    ],
)
def test_ordinary_priestly_amens_are_not_reclassified(text_id, sid):
    doc = text(text_id)
    seg = next(s for s in doc["segments"] if s["id"] == sid)
    assert orations.check_doc(doc) == ([], 0)
    assert orations.base_attributes(doc) == {}
    assert delivery.derive(doc, seg) == {}
    if text_id.endswith("pater-noster"):
        assert participation.derive(doc, seg) == {
            "lecta": {"source": "DMS 32", "conditional": True}
        }
    else:
        assert participation.derive(doc, seg) == {}


def test_preface_cannot_duplicate_final_secret_transition():
    doc = text(orations.PREFACE)
    assert orations.check_doc(doc) == ([], 1)
    transition = copy.deepcopy(verses(corrected(NIGHT + "secreta"))[1:])
    doc["segments"] = transition + doc["segments"]
    assert any("duplicates" in e for e in orations.check_doc(doc)[0])


def test_normal_corpus_gate_checks_oration_boundaries_without_an_opt_in():
    # Execute the real entry point with an in-memory mutation. Nothing is
    # written to the canonical fixture, and other validators remain enabled.
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
from copy import deepcopy
from unittest.mock import patch
import run_checks

tid = 'proprium.dominica-iii-adventus-collecta'
assert run_checks.main(tid) == 0
doc, layers = run_checks.store.load(run_checks.CORPUS, tid)
changed = deepcopy(doc)
changed['segments'][-1]['speaker'] = 'sacerdos'
with patch.object(run_checks.store, 'load', return_value=(changed, layers)):
    assert run_checks.main(tid) == 1
""",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "VERDICT OK" in result.stdout
    assert "oration_boundaries=1" in result.stdout
    assert "oration speaker must be minister" in result.stdout
    assert "VERDICT FAIL" in result.stdout


def test_existing_ordinary_minister_response_keeps_first_degree():
    doc = text("ordinarium.per-ipsum")
    seg = next(s for s in doc["segments"] if s["id"] == "s09")
    assert participation.derive(doc, seg)["lecta"]["gradus"] == 1
    assert participation.derive(doc, seg)["cantu"]["gradus"] == 1
    assert orations.check_doc(doc) == ([], 0)


@pytest.mark.parametrize("ending", ["Per Dóminum", "Qui tecum", "Qui vivis", "Per eúndem Dóminum"])
@pytest.mark.parametrize("piece", ["collecta", "postcommunio", "secreta"])
def test_abbreviated_endings_fail_explicitly_without_new_labels(ending, piece):
    doc = {
        "id": "proprium.test-" + piece,
        "category": "proprium",
        "segments": [
            {
                "id": "s01",
                "type": "verse",
                "speaker": "sacerdos",
                "voice": "secreto" if piece == "secreta" else "clara",
                "words": [
                    {"id": f"w{i:03d}", "form": form}
                    for i, form in enumerate(("Concéde " + ending).split(), 1)
                ],
            }
        ],
    }
    assert any("abbreviated conclusion" in e for e in orations.check_doc(doc)[0])
    assert orations.base_attributes(doc) == {}
    assert all(delivery.derive(doc, s) == {} for s in verses(doc))


@pytest.mark.parametrize("piece", ["collecta", "postcommunio", "secreta"])
def test_unsplit_legacy_shape_is_compatible_but_not_boundary_approved(piece):
    doc = corrected(NIGHT + piece)
    old = {
        "id": "s01",
        "type": "verse",
        "speaker": "sacerdos",
        "voice": "secreto" if piece == "secreta" else "clara",
        "words": [w for s in verses(doc) for w in s["words"]],
    }
    doc["segments"] = [old]
    assert orations.check_doc(doc)[0]
    assert orations.base_attributes(doc) == {}
    assert delivery.check_doc(doc)[0] == participation.check_doc(doc)[0] == []


def test_opt_in_catalogue_runner_really_calls_boundary_validation(tmp_path, capsys):
    directory = tmp_path / "texts" / "proprium"
    directory.mkdir(parents=True)
    doc = corrected(NIGHT + "collecta")
    path = directory / "example.json"
    path.write_text(json.dumps(doc))
    assert orations.run(tmp_path) == 0
    assert "checked 1 Proper orations" in capsys.readouterr().out
    body, response = verses(doc)
    body["words"] += response["words"]
    doc["segments"].remove(response)
    path.write_text(json.dumps(doc))
    assert orations.run(tmp_path) > 0
    assert "absorbed" in capsys.readouterr().out
    path.write_text(json.dumps(corrected(NIGHT + "collecta")))
    assert orations.run(tmp_path) == 0


def test_empty_catalogue_fails_instead_of_claiming_a_pass(tmp_path, capsys):
    assert orations.run(tmp_path) == 1
    assert "no Proper orations examined" in capsys.readouterr().out
