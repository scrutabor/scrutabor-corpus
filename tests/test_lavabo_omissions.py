"""Closed Lavabo doxology prescriptions and complete-body source boundaries."""

import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.emit import formulary_catalog, language_formulary_catalog
from checks.formularies import check
from checks.lavabo_omissions import DESCRIPTOR, errors

CORPUS = Path(__file__).resolve().parents[1]
CASES = [
    ("quadragesima", "dominica-iv-in-quadragesima", False),
    ("passion-sunday", "dominica-i-passionis", True),
    ("annunciation", "annuntiatio-beatae-mariae-virginis", False),
    ("palm-sunday", "dominica-ii-passionis", True),
    ("holy-thursday", "feria-v-in-cena-domini", True),
    ("easter-vigil", "vigilia-paschalis", False),
    ("easter-day", "dominica-resurrectionis", False),
    ("all-souls-i", "commemoratio-omnium-fidelium-defunctorum", True),
    ("all-souls-ii", "commemoratio-omnium-fidelium-defunctorum-missa-ii", True),
    ("all-souls-iii", "commemoratio-omnium-fidelium-defunctorum-missa-iii", True),
]
OMITTED = {mass for _, mass, omitted in CASES if omitted}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def actual_form(mass):
    (path,) = list((CORPUS / "formularies").glob(f"*/{mass}.json"))
    return path


def copied_mass(root, mass="dominica-i-passionis"):
    """Copy one actual form, every named component, the target and both titles."""
    path = actual_form(mass)
    relative = path.relative_to(CORPUS)
    form = read(path)
    form["order"] = 0
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    write(target, form)
    bodies = {component["text"] for component in form["components"]} | {"ordinarium.lavabo"}
    for text in bodies:
        category, slug = text.split(".", 1)
        name = Path("texts") / category / f"{slug}.json"
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CORPUS / name, root / name)
    for language in ("pl", "en"):
        name = Path("languages") / language / relative
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CORPUS / name, root / name)
    assert check(root)[0] == []
    assert formulary_catalog(root)["formularies"][0]["id"] == mass
    return target


def test_complete_catalogue_keeps_all_texts_and_explicit_retention_rows():
    assert len(list((CORPUS / "texts").glob("*/*.json"))) == 1221
    authored = [read(path) for path in (CORPUS / "formularies").glob("*/*.json")]
    catalogue = formulary_catalog(CORPUS)
    assert catalogue["schema_version"] == "1.5.0"
    assert len(authored) == len(catalogue["formularies"]) == 114
    assert {row["id"] for row in authored if row.get("ordinary_omissions")} == OMITTED
    assert {row["id"] for row in catalogue["formularies"] if row["ordinary_omissions"]} == OMITTED
    for original, emitted in zip(
        sorted(authored, key=lambda row: row["order"]), catalogue["formularies"], strict=True
    ):
        assert emitted["ordinary"] == original["ordinary"]
        # Compare only the historical Lavabo seam on a fresh list. The new
        # full All Souls prescriptions are independently covered in test_requiem_assembly.
        lavabo = [
            row for row in emitted["ordinary_omissions"] if row["reason"] == "lavabo-doxology"
        ]
        assert lavabo == (
            [{**DESCRIPTOR, "text": "ordinarium/lavabo"}] if original["id"] in OMITTED else []
        )
        assert original["formulary_schema"] == (
            "1.5.0"
            if original["observance"] == "commemoratio-omnium-fidelium-defunctorum"
            else "1.4.0"
            if original["id"] in OMITTED
            else "1.3.0"
        )
        if original["id"] not in OMITTED:
            assert "ordinary_omissions" not in original
    for language in ("pl", "en"):
        titles = language_formulary_catalog(CORPUS, language)
        assert titles["schema_version"] == "1.2.0"
        assert len(titles["titles"]) == 114
        assert all(set(title) == {"id", "title"} for title in titles["titles"])


@pytest.mark.parametrize("name,mass,omitted", CASES, ids=[row[0] for row in CASES])
def test_actual_mass_classification_preserves_the_source_exceptions(name, mass, omitted):
    form = read(actual_form(mass))
    saved = deepcopy(form)
    assert errors(form, CORPUS) == []
    assert bool(form.get("ordinary_omissions")) is omitted
    if name == "holy-thursday":
        assert set(form["ordinary"]["gloria"].values()) == {"required"}
    if name == "annunciation":
        assert form["collection"] == "sanctorale"
    assert form == saved


DECLARATION_FAULTS = [
    "missing",
    "empty",
    "null",
    "wrong-text",
    "wrong-reason",
    "one-segment",
    "extra-segment",
    "reversed",
    "duplicate",
    "psalm",
    "whole-prayer",
    "extra-key",
    "version",
]


@pytest.mark.parametrize("fault", DECLARATION_FAULTS)
def test_actual_source_checker_and_emitter_reject_bad_declarations_and_recover(tmp_path, fault):
    target = copied_mass(tmp_path)
    before = target.read_bytes()
    form = read(target)
    descriptor = form["ordinary_omissions"][0]
    if fault == "missing":
        del form["ordinary_omissions"]
    elif fault in {"empty", "null"}:
        form["ordinary_omissions"] = [] if fault == "empty" else None
    elif fault == "wrong-text":
        descriptor["text"] = "ordinarium.gloria"
    elif fault == "wrong-reason":
        descriptor["reason"] = "gloria-hymn"
    elif fault == "extra-key":
        descriptor["season"] = "passionis"
    elif fault == "version":
        form["formulary_schema"] = "1.3.0"
    else:
        descriptor["segments"] = {
            "one-segment": ["s09"],
            "extra-segment": ["s08", "s09", "s10"],
            "reversed": ["s10", "s09"],
            "duplicate": ["s09", "s09"],
            "psalm": ["s02", "s03"],
            "whole-prayer": [f"s{i:02}" for i in range(1, 11)],
        }[fault]
    try:
        write(target, form)
        assert target.read_bytes() != before
        assert any("ordinary_omissions" in e or "formulary_schema" in e for e in check(tmp_path)[0])
        with pytest.raises(ValueError, match=r"ordinary_omissions|formulary_schema"):
            formulary_catalog(tmp_path)
    finally:
        target.write_bytes(before)
        assert target.read_bytes() == before
        assert check(tmp_path)[0] == []
        assert formulary_catalog(tmp_path)["formularies"][0]["ordinary_omissions"]


@pytest.mark.parametrize("mass", ["annuntiatio-beatae-mariae-virginis", "vigilia-paschalis"])
def test_retained_actual_forms_cannot_acquire_an_omission(tmp_path, mass):
    target = copied_mass(tmp_path, mass)
    before = target.read_bytes()
    form = read(target)
    form["formulary_schema"] = "1.4.0"
    form["ordinary_omissions"] = [deepcopy(DESCRIPTOR)]
    try:
        write(target, form)
        assert target.read_bytes() != before
        assert any("ordinary_omissions is not prescribed" in e for e in check(tmp_path)[0])
        with pytest.raises(ValueError, match="ordinary_omissions is not prescribed"):
            formulary_catalog(tmp_path)
    finally:
        target.write_bytes(before)
        assert check(tmp_path)[0] == []
        assert formulary_catalog(tmp_path)["formularies"][0]["ordinary_omissions"] == []


@pytest.mark.parametrize("language", ["pl", "en"])
def test_language_title_cannot_author_the_neutral_rule(tmp_path, language):
    target = copied_mass(tmp_path)
    title = tmp_path / "languages" / language / target.relative_to(tmp_path)
    before = title.read_bytes()
    value = read(title)
    value["ordinary_omissions"] = [deepcopy(DESCRIPTOR)]
    try:
        write(title, value)
        assert title.read_bytes() != before
        assert any(
            "ordinary belongs only to the neutral formulary" in e for e in check(tmp_path)[0]
        )
        with pytest.raises(ValueError, match="localized formulary title"):
            language_formulary_catalog(tmp_path, language)
    finally:
        title.write_bytes(before)
        assert check(tmp_path)[0] == []
        assert len(language_formulary_catalog(tmp_path, language)["titles"]) == 1


TARGET_FAULTS = [
    "missing-segment",
    "reordered-segments",
    "duplicate-segment",
    "missing-word",
    "reordered-words",
    "foreign-word-id",
    "wrong-form",
    "wrong-speaker",
    "wrong-voice",
    "wrong-rubric",
    "wrong-text-id",
]


@pytest.mark.parametrize("fault", TARGET_FAULTS)
def test_complete_lavabo_target_is_checked_before_the_projection(tmp_path, fault):
    copied_mass(tmp_path)
    target = tmp_path / "texts/ordinarium/lavabo.json"
    before = target.read_bytes()
    body = read(target)
    segments = body["segments"]
    if fault == "missing-segment":
        segments.pop()
    elif fault == "reordered-segments":
        segments.reverse()
    elif fault == "duplicate-segment":
        segments[-1]["id"] = "s09"
    elif fault == "missing-word":
        segments[-1]["words"].pop()
    elif fault == "reordered-words":
        segments[-1]["words"].reverse()
    elif fault == "foreign-word-id":
        segments[-1]["words"][-1]["id"] = "w095"
    elif fault == "wrong-form":
        segments[-1]["words"][-1]["form"] = "Changed"
    elif fault == "wrong-speaker":
        segments[-1]["speaker"] = "minister"
    elif fault == "wrong-voice":
        segments[-1]["voice"] = "clara"
    elif fault == "wrong-rubric":
        segments[0]["type"] = "verse"
    else:
        body["id"] = "ordinarium.gloria"
    try:
        write(target, body)
        assert target.read_bytes() != before
        assert any("ordinary_omissions target" in e for e in check(tmp_path)[0])
        with pytest.raises(ValueError, match="ordinary_omissions target"):
            formulary_catalog(tmp_path)
    finally:
        target.write_bytes(before)
        assert target.read_bytes() == before
        assert check(tmp_path)[0] == []
        assert formulary_catalog(tmp_path)["formularies"][0]["ordinary_omissions"]
