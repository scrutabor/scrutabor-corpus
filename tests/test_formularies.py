"""The formulary layer is the canonical assembly, not an app-side guess."""

import json
import shutil
from pathlib import Path

from checks.formularies import check

CORPUS = Path(__file__).resolve().parent.parent


def test_every_formulary_component_and_language_title_is_accounted_for():
    errors, counts = check(CORPUS)
    assert errors == []
    assert counts == {
        "formularies": 86,
        "observances": 82,
        "components": 953,
        "proper_texts": 784,
        "proper_uses": 872,
        "shared_uses": 81,
        "reference_uses": 88,
    }


def test_a_missing_component_text_fails_with_its_formulary(tmp_path):
    root = tmp_path / "corpus"
    shutil.copytree(CORPUS / "formularies", root / "formularies")
    shutil.copytree(CORPUS / "languages", root / "languages")
    shutil.copytree(CORPUS / "texts", root / "texts")
    path = root / "formularies/temporale/dominica-v-post-epiphaniam.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["components"][0]["text"] = "proprium.no-such-introitus"
    path.write_text(json.dumps(value), encoding="utf-8")
    errors, _counts = check(root)
    assert any("dominica-v-post-epiphaniam:introitus: missing text" in error for error in errors)


def test_an_unassembled_proper_fails_instead_of_becoming_an_orphan(tmp_path):
    root = tmp_path / "corpus"
    shutil.copytree(CORPUS / "formularies", root / "formularies")
    shutil.copytree(CORPUS / "languages", root / "languages")
    shutil.copytree(CORPUS / "texts", root / "texts")
    path = root / "formularies/temporale/dominica-ii-post-pentecosten.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["components"] = [
        component for component in value["components"] if component["role"] != "collecta"
    ]
    path.write_text(json.dumps(value), encoding="utf-8")
    errors, _counts = check(root)
    assert any("proprium.dominica-ii-post-pentecosten-collecta" in error for error in errors)


def test_two_calendar_defaults_for_one_observance_fail(tmp_path):
    root = tmp_path / "corpus"
    shutil.copytree(CORPUS / "formularies", root / "formularies")
    shutil.copytree(CORPUS / "languages", root / "languages")
    shutil.copytree(CORPUS / "texts", root / "texts")
    path = root / ("formularies/sanctorale/commemoratio-omnium-fidelium-defunctorum-missa-ii.json")
    value = json.loads(path.read_text(encoding="utf-8"))
    value["calendar"]["default"] = True
    path.write_text(json.dumps(value), encoding="utf-8")
    errors, _counts = check(root)
    assert any("has defaults" in error and "expected one" in error for error in errors)


def test_vigil_alleluia_is_conditioned_on_sunday():
    path = CORPUS / "formularies/temporale/vigilia-nativitatis.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    alleluia = next(
        component for component in value["components"] if component["role"] == "alleluia"
    )
    assert alleluia["condition"] == {"weekday": "sunday"}


def test_unknown_component_condition_fails(tmp_path):
    root = tmp_path / "corpus"
    shutil.copytree(CORPUS / "formularies", root / "formularies")
    shutil.copytree(CORPUS / "languages", root / "languages")
    shutil.copytree(CORPUS / "texts", root / "texts")
    path = root / "formularies/temporale/vigilia-nativitatis.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["components"][4]["condition"] = {"weekday": "monday"}
    path.write_text(json.dumps(value), encoding="utf-8")
    errors, _counts = check(root)
    assert any("unknown component condition" in error for error in errors)
