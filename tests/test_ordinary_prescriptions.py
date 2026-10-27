"""Explicit neutral Ordinary branches, never an application-side liturgical table."""

import json
import shutil
from copy import deepcopy
from itertools import product
from pathlib import Path

import pytest

from build_reader.emit import formulary_catalog, language_formulary_catalog
from checks.formularies import SCHEMA, TITLE_SCHEMA, check, ordinary_errors

CORPUS = Path(__file__).resolve().parent.parent
STATES = ("required", "omitted", "unresolved")


def prescriptions(states):
    return {
        "gloria": {"sunday": states[0], "not-sunday": states[1]},
        "credo": {"sunday": states[2], "not-sunday": states[3]},
    }


@pytest.mark.parametrize("states", list(product(STATES, repeat=4)))
def test_all_explicit_branch_combinations_are_valid_without_adding_a_default(states):
    value = prescriptions(states)
    before = deepcopy(value)
    assert ordinary_errors(value) == []
    assert value == before


@pytest.fixture
def catalogue(tmp_path):
    """One genuine form/body/title set, reduced explicitly to one complete component."""
    relative = Path("temporale/dominica-iii-post-pascha.json")
    original = CORPUS / "formularies" / relative
    doc = json.loads(original.read_text(encoding="utf-8"))
    doc["order"] = 0
    doc["components"] = doc["components"][:1]
    target = tmp_path / "formularies" / relative
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    category, slug = doc["components"][0]["text"].split(".", 1)
    text = Path("texts") / category / f"{slug}.json"
    (tmp_path / text).parent.mkdir(parents=True)
    shutil.copyfile(CORPUS / text, tmp_path / text)
    titles = []
    for language in ("pl", "en"):
        title = Path("languages") / language / "formularies" / relative
        (tmp_path / title).parent.mkdir(parents=True)
        shutil.copyfile(CORPUS / title, tmp_path / title)
        titles.append(tmp_path / title)
    assert check(tmp_path)[0] == []
    return tmp_path, target, titles


@pytest.mark.parametrize(
    "fault",
    [
        "absent",
        "null",
        "array",
        "empty",
        "missing-part",
        "extra-part",
        "missing-branch",
        "extra-branch",
        "branch-array",
        "boolean",
        "number",
        "unknown-state",
    ],
)
def test_malformed_neutral_metadata_fails_at_the_real_catalogue_guard_and_restores(
    catalogue, fault
):
    root, target, _ = catalogue
    before = target.read_bytes()
    doc = json.loads(before)
    value = doc["ordinary"]
    if fault == "absent":
        del doc["ordinary"]
    elif fault in {"null", "array", "empty"}:
        doc["ordinary"] = {"null": None, "array": [], "empty": {}}[fault]
    elif fault == "missing-part":
        del value["gloria"]
    elif fault == "extra-part":
        value["sanctus"] = deepcopy(value["gloria"])
    elif fault == "missing-branch":
        del value["gloria"]["not-sunday"]
    elif fault == "extra-branch":
        value["gloria"]["monday"] = "required"
    elif fault == "branch-array":
        value["gloria"] = ["required", "required"]
    else:
        invalid_states = {"boolean": True, "number": 1, "unknown-state": "optional"}
        value["gloria"]["sunday"] = invalid_states[fault]
    target.write_text(json.dumps(doc), encoding="utf-8")
    assert any("ordinary" in error for error in check(root)[0])
    with pytest.raises(ValueError, match="ordinary"):
        formulary_catalog(root)
    target.write_bytes(before)
    assert check(root)[0] == []
    assert target.read_bytes() == before


@pytest.mark.parametrize("language_index", [0, 1])
def test_title_only_language_contract_cannot_become_a_second_editorial_source(
    catalogue, language_index
):
    root, _, titles = catalogue
    target = titles[language_index]
    before = target.read_bytes()
    doc = json.loads(before)
    assert doc["formulary_schema"] == TITLE_SCHEMA == "1.2.0"
    doc["ordinary"] = prescriptions(("required",) * 4)
    target.write_text(json.dumps(doc), encoding="utf-8")
    assert any("ordinary belongs only to the neutral formulary" in e for e in check(root)[0])
    with pytest.raises(ValueError, match="localized formulary title"):
        language_formulary_catalog(root, ("pl", "en")[language_index])
    target.write_bytes(before)
    assert check(root)[0] == []


@pytest.mark.parametrize("language_index", [0, 1])
def test_neutral_version_cannot_be_reused_for_unchanged_localized_titles(catalogue, language_index):
    root, _, titles = catalogue
    target = titles[language_index]
    before = target.read_bytes()
    doc = json.loads(before)
    doc["formulary_schema"] = SCHEMA
    target.write_text(json.dumps(doc), encoding="utf-8")
    assert any("formulary_schema must be 1.2.0" in e for e in check(root)[0])
    with pytest.raises(ValueError, match="localized formulary title"):
        language_formulary_catalog(root, ("pl", "en")[language_index])
    target.write_bytes(before)
    assert check(root)[0] == []


def test_neutral_contract_version_and_required_metadata_cannot_be_silently_omitted(catalogue):
    root, target, _ = catalogue
    before = target.read_bytes()
    doc = json.loads(before)
    assert doc["formulary_schema"] == SCHEMA == "1.3.0"
    doc["formulary_schema"] = "1.2.0"
    target.write_text(json.dumps(doc), encoding="utf-8")
    assert any("formulary_schema must be 1.3.0" in e for e in check(root)[0])
    with pytest.raises(ValueError, match="formulary_schema"):
        formulary_catalog(root)
    target.write_bytes(before)
    assert check(root)[0] == []


def test_every_actual_neutral_form_and_both_title_catalogues_project_without_other_changes():
    authored = [
        json.loads(p.read_text(encoding="utf-8")) for p in (CORPUS / "formularies").glob("*/*.json")
    ]
    assert authored
    expected = []
    for doc in sorted(authored, key=lambda value: value["order"]):
        assert ordinary_errors(doc["ordinary"]) == []
        value = {key: deepcopy(item) for key, item in doc.items() if key != "formulary_schema"}
        for component in value["components"]:
            component["text"] = component["text"].replace(".", "/", 1)
        value.setdefault("ordinary_omissions", [])
        for omission in value["ordinary_omissions"]:
            omission["text"] = omission["text"].replace(".", "/", 1)
        expected.append(value)
    assert formulary_catalog(CORPUS) == {"schema_version": "1.4.0", "formularies": expected}
    for language in ("pl", "en"):
        catalogue = language_formulary_catalog(CORPUS, language)
        assert catalogue["schema_version"] == "1.2.0"
        assert catalogue["language"] == language
        assert {title["id"] for title in catalogue["titles"]} == {doc["id"] for doc in authored}
        assert all(set(title) == {"id", "title"} for title in catalogue["titles"])
