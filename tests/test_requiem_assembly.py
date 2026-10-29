"""Complete recensions and closed assembly, with genuine failing/restored controls."""

import copy
import json
from pathlib import Path

import pytest

from build_reader import emit
from build_reader.dismissal import expected
from build_reader.requiem import verify as verify_assembly
from checks.delivery import check_doc as delivery_check
from checks.lavabo_omissions import errors as assembly_errors
from checks.participation import check_doc as participation_check
from checks.participation_performance import publication_errors
from checks.requiem_dismissal import publication_errors as dismissal_errors

CORPUS = Path(__file__).resolve().parents[1]
MASSES = [
    "commemoratio-omnium-fidelium-defunctorum",
    "commemoratio-omnium-fidelium-defunctorum-missa-ii",
    "commemoratio-omnium-fidelium-defunctorum-missa-iii",
]
OMISSIONS = [
    {"text": "ordinarium.lavabo", "segments": ["s09", "s10"], "reason": "lavabo-doxology"},
    {"text": "ordinarium.iudica-me", "reason": "requiem-iudica"},
    {"text": "ordinarium.qui-dixisti", "reason": "requiem-peace-prayer"},
    {"text": "ordinarium.benedictio", "reason": "requiem-blessing"},
]


def read(name):
    return json.loads((CORPUS / name).read_text())


@pytest.mark.parametrize("mass", MASSES)
def test_actual_three_forms_use_complete_shared_body_and_exact_omissions(mass):
    form = read(f"formularies/sanctorale/{mass}.json")
    before = copy.deepcopy(form)
    assert assembly_errors(form, CORPUS) == []
    assert form["formulary_schema"] == "1.5.0"
    assert form["ordinary_omissions"] == OMISSIONS
    rows = [c for c in form["components"] if c["role"] == "agnus-dei"]
    assert rows == [
        {
            "key": "agnus-dei",
            "role": "agnus-dei",
            "text": "ordinarium.agnus-dei-defunctorum",
            "relation": "shared",
        }
    ]
    assert form == before


@pytest.mark.parametrize(
    "fault",
    [
        "missing-agnus",
        "ordinary-body",
        "reference",
        "omit-introibo",
        "missing-omission",
        "last-gospel",
        "old-version",
    ],
)
def test_actual_assembly_faults_fail_and_exact_source_recovers(fault):
    form = read(f"formularies/sanctorale/{MASSES[0]}.json")
    good = copy.deepcopy(form)
    assert assembly_errors(form, CORPUS) == []
    damaged_input = form
    try:
        agnus = next(c for c in form["components"] if c["role"] == "agnus-dei")
        if fault == "missing-agnus":
            form["components"].remove(agnus)
        elif fault == "ordinary-body":
            agnus["text"] = "ordinarium.agnus-dei"
        elif fault == "reference":
            agnus["relation"] = "reference"
        elif fault == "omit-introibo":
            form["ordinary_omissions"][1]["text"] = "ordinarium.introibo"
        elif fault == "missing-omission":
            form["ordinary_omissions"].pop()
        elif fault == "last-gospel":
            form["ordinary_omissions"].append(
                {"text": "ordinarium.evangelium-ultimum", "reason": "absolution"}
            )
        else:
            form["formulary_schema"] = "1.4.0"
        assert form != good
        assert assembly_errors(form, CORPUS)
    finally:
        form.clear()
        form.update(copy.deepcopy(good))
    assert form is damaged_input
    assert form == good
    assert assembly_errors(form, CORPUS) == []


@pytest.mark.parametrize("slug,count", [("agnus-dei", 25), ("agnus-dei-defunctorum", 28)])
def test_actual_agni_keep_priestly_base_and_independent_schola(slug, count):
    doc = read(f"texts/ordinarium/{slug}.json")
    assert publication_errors(doc) == []
    assert delivery_check(doc)[0] == []
    assert participation_check(doc)[0] == []
    assert len([w for s in doc["segments"] for w in s.get("words", [])]) == count
    for identity in [s["id"] for s in doc["segments"] if s["type"] == "verse"]:
        bad = copy.deepcopy(doc)
        damaged_input = bad
        try:
            row = next(s for s in bad["segments"] if s["id"] == identity)
            assert row["speaker"] == "sacerdos" and row["voice"] == "clara"
            assert row["delivery"] == {"cantu": {"voice": "secreto"}}
            del row["participation"]["cantu"]["performance"]
            assert publication_errors(bad)
        finally:
            bad.clear()
            bad.update(copy.deepcopy(doc))
        assert bad is damaged_input
        assert bad == doc
        assert publication_errors(bad) == []


def test_requiescant_actor_is_form_specific_and_cannot_inherit_participation():
    doc = read("texts/ordinarium/ite-missa-est-defunctorum.json")
    assert dismissal_errors(doc) == []
    assert delivery_check(doc)[0] == []
    assert participation_check(doc)[0] == []
    row = doc["segments"][2]
    assert "speaker" not in row and "voice" not in row and "participation" not in row
    assert row["delivery"] == {
        "lecta": {"speaker": "sacerdos", "voice": "clara"},
        "cantu": {"voice": "cantus"},
    }
    good = copy.deepcopy(doc)
    damaged_input = doc
    try:
        row["speaker"] = "sacerdos"
        row["delivery"]["cantu"]["speaker"] = "sacerdos"
        row["participation"] = {"cantu": {"gradus": 1, "source": "DMS 25 a"}}
        assert dismissal_errors(doc)
    finally:
        doc.clear()
        doc.update(copy.deepcopy(good))
    assert doc is damaged_input
    assert doc == good
    assert dismissal_errors(doc) == []


def test_actual_finite_table_retains_all_pairs_and_explicit_all_souls_choices():
    table = expected(CORPUS)
    assert table["schema_version"] == "1.1.0"
    assert len(table["pairs"]) == 7682
    assert [p["id"] for p in table["profiles"]] == ["ordinary", "paschale", "defunctorum"]
    selected = [row for row in table["pairs"] if row[2] == 2]
    assert len(selected) == 228
    assert {table["masses"][row[1]] for row in selected} == set(MASSES)
    assert all(sum(table["masses"][r[1]] == mass for r in selected) == 76 for mass in MASSES)
    assert sum(row[2] == 1 for row in table["pairs"]) == 152
    assert sum(row[2] == 0 for row in table["pairs"]) == 7302
    assert ["2031-11-03", table["masses"].index(MASSES[0]), 2] in table["pairs"]


def test_full_artifact_guard_rejects_producer_catalogue_corruption_and_recovers(reader_copy):
    manifest = json.loads((reader_copy / "manifest.json").read_text())
    assert verify_assembly(CORPUS, reader_copy, manifest) == []
    target = reader_copy / "formularies.json"
    original = target.read_bytes()
    bad = json.loads(original)
    row = next(r for r in bad["formularies"] if r["id"] == MASSES[0])
    row["ordinary_omissions"].pop()
    try:
        target.write_text(json.dumps(bad))
        assert target.read_bytes() != original
        assert verify_assembly(CORPUS, reader_copy, manifest)
        assert emit.verify(CORPUS, reader_copy)
    finally:
        target.write_bytes(original)
    assert verify_assembly(CORPUS, reader_copy, manifest) == []
    assert emit.verify(CORPUS, reader_copy) == []


def test_complete_inventory_counts_and_registry_append_are_exact():
    docs = [json.loads(p.read_text()) for p in (CORPUS / "texts").glob("*/*.json")]
    assert len(docs) == 1221
    assert sum(len(s.get("words", [])) for doc in docs for s in doc["segments"]) == 66939
    registry = read("build_reader/registry/texts.json")
    assert len(registry) == 1221
    assert set(registry[1219:]) == {
        "ordinarium.agnus-dei-defunctorum",
        "ordinarium.ite-missa-est-defunctorum",
    }
