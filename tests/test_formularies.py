"""The formulary layer is the canonical assembly, not an app-side guess."""

import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

from checks.formularies import check

CORPUS = Path(__file__).resolve().parent.parent


def test_every_formulary_component_and_language_title_is_accounted_for():
    errors, counts = check(CORPUS)
    assert errors == []
    assert counts == {
        "formularies": 109,
        "observances": 105,
        "components": 1209,
        "proper_texts": 991,
        "proper_uses": 1103,
        "shared_uses": 106,
        "reference_uses": 112,
        "gradual_tract_pairs": 33,
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


def test_christmas_vigil_prefaces_follow_the_printed_sunday_exception():
    value = json.loads(
        (CORPUS / "formularies/temporale/vigilia-nativitatis.json").read_text(encoding="utf-8")
    )
    prefaces = [part for part in value["components"] if part["role"] == "praefatio"]
    assert [(part["text"], part["condition"]) for part in prefaces] == [
        ("ordinarium.praefatio-communis", {"weekday": "not-sunday"}),
        ("ordinarium.praefatio-sanctissimae-trinitatis", {"weekday": "sunday"}),
    ]


@pytest.mark.parametrize("condition", [None, {"weekday": "sunday"}])
def test_repeated_roles_cannot_overlap(tmp_path, condition):
    root = tmp_path / "corpus"
    for directory in ("formularies", "languages", "texts"):
        shutil.copytree(CORPUS / directory, root / directory)
    path = root / "formularies/temporale/vigilia-nativitatis.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    preface = next(part for part in value["components"] if part["key"] == "praefatio")
    preface["condition"] = condition
    path.write_text(json.dumps(value), encoding="utf-8")
    errors, _counts = check(root)
    assert any("repeated role requires complementary conditions" in error for error in errors)


@pytest.fixture
def chant_catalogue(tmp_path):
    """A corrected gradual/tract pair in a complete, minimal catalogue."""
    root = tmp_path / "corpus"
    relative = Path("sanctorale/dedicatio-archibasilicae-sanctissimi-salvatoris.json")
    doc = json.loads((CORPUS / "formularies" / relative).read_text(encoding="utf-8"))
    doc["order"] = 0
    doc["components"] = [
        part for part in doc["components"] if part["role"] in ("graduale", "tractus")
    ]
    target = root / "formularies" / relative
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(doc), encoding="utf-8")
    paths = {}
    for part in doc["components"]:
        category, slug = part["text"].split(".", 1)
        text_path = Path("texts") / category / f"{slug}.json"
        (root / text_path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CORPUS / text_path, root / text_path)
        paths[part["role"]] = root / text_path
    for language in ("pl", "en"):
        title_path = Path("languages") / language / "formularies" / relative
        (root / title_path).parent.mkdir(parents=True)
        shutil.copyfile(CORPUS / title_path, root / title_path)
    return root, paths


def test_correct_tract_passes_catalogue_boundary_check(chant_catalogue):
    root, _paths = chant_catalogue
    errors, counts = check(root)
    assert errors == []
    assert counts["gradual_tract_pairs"] == 1


@pytest.mark.parametrize("mode", ["prefix", "identical", "normalized-prefix"])
def test_full_gradual_contamination_fails_catalogue_validation(chant_catalogue, mode):
    root, paths = chant_catalogue
    assert check(root)[0] == []
    gradual = json.loads(paths["graduale"].read_text(encoding="utf-8"))
    original = paths["tractus"].read_text(encoding="utf-8")
    tract = json.loads(original)
    contaminated = deepcopy(gradual["segments"])
    if mode == "normalized-prefix":
        for segment in contaminated:
            for word in segment.get("words") or []:
                word["form"] = word["form"].replace("inæstimábile", "INAESTIMABILE")
        assert any(
            word["form"] == "INAESTIMABILE"
            for segment in contaminated
            for word in segment.get("words") or []
        )
    if mode != "identical":
        contaminated.extend(tract["segments"])
    tract["segments"] = contaminated
    paths["tractus"].write_text(json.dumps(tract), encoding="utf-8")

    errors, counts = check(root)
    assert counts["gradual_tract_pairs"] == 1
    assert len(errors) == 1
    assert errors[0].startswith("dedicatio-archibasilicae-sanctissimi-salvatoris:tractus:")
    assert "repeats the entire gradual" in errors[0]
    paths["tractus"].write_text(original, encoding="utf-8")
    assert check(root)[0] == []


def test_partial_shared_incipit_does_not_fail_catalogue_validation(chant_catalogue):
    root, paths = chant_catalogue
    assert check(root)[0] == []
    gradual = json.loads(paths["graduale"].read_text(encoding="utf-8"))
    tract = json.loads(paths["tractus"].read_text(encoding="utf-8"))
    tract["segments"][0]["words"][:0] = deepcopy(gradual["segments"][0]["words"][:2])
    paths["tractus"].write_text(json.dumps(tract), encoding="utf-8")

    errors, counts = check(root)
    assert errors == []
    assert counts["gradual_tract_pairs"] == 1


@pytest.fixture
def seasonal_catalogue(chant_catalogue):
    """Two complete proper recensions, not a partially hidden chant."""
    root, paths = chant_catalogue
    path = next((root / "formularies").glob("*/*.json"))
    doc = json.loads(path.read_text(encoding="utf-8"))
    gradual = doc["components"][0]
    assert gradual["role"] == "graduale"
    gradual["condition"] = {"season": "paschale"}
    alternate = deepcopy(gradual)
    alternate.update(
        key="graduale-non-paschale",
        text=gradual["text"].removesuffix("-graduale") + "-non-paschale-graduale",
        recension="non-paschale",
        condition={"season": "not-paschale"},
    )
    doc["components"].insert(1, alternate)
    text = json.loads(paths["graduale"].read_text(encoding="utf-8"))
    text["id"] = alternate["text"]
    alternate_path = root / "texts" / (alternate["text"].replace(".", "/", 1) + ".json")
    alternate_path.write_text(json.dumps(text), encoding="utf-8")
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert check(root)[0] == []
    return root, path, doc


def test_complementary_complete_seasonal_recensions_pass(seasonal_catalogue):
    root, _path, _doc = seasonal_catalogue
    errors, counts = check(root)
    assert errors == []
    assert counts["components"] == 3
    assert counts["proper_uses"] == 3


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("recension", "unknown", "recension requires its matching season"),
        ("recension", ["non-paschale"], "recension requires its matching season"),
        ("recension", "paschale", "recension requires its matching season"),
        ("condition", None, "recension requires its matching season"),
        ("condition", {"season": "paschale"}, "repeated role requires complementary"),
        (
            "condition",
            {"season": "not-paschale", "weekday": "sunday"},
            "unknown component condition",
        ),
        ("relation", "reference", "recension requires its matching season"),
        (
            "text",
            "proprium.dedicatio-archibasilicae-sanctissimi-salvatoris-graduale",
            "proper relation must address",
        ),
    ],
)
def test_seasonal_recensions_cannot_bypass_identity_or_conditions(
    seasonal_catalogue, field, value, message
):
    root, path, doc = seasonal_catalogue
    doc["components"][1][field] = value
    path.write_text(json.dumps(doc), encoding="utf-8")
    errors, _counts = check(root)
    assert any(message in error for error in errors), errors
