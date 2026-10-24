"""Short, complete constructions in the eighteenth Sunday's Epistle."""

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.layers import expand_core
from checks import interlinear, language_packs

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.dominica-xviii-post-pentecosten-epistola"
RELATIVE = TEXT.replace(".", "/", 1) + ".json"
GROUPS = (
    (("w002", "w003"), "w003", "I give thanks"),
    (("w004", "w005"), "w004", "to my God"),
    (("w013", "w014"), "w013", "was given"),
    (("w022", "w023", "w024"), "w023", "you have been made rich"),
    (("w037", "w038"), "w037", "was confirmed"),
    (("w043", "w044", "w045"), "w045", "you lack nothing"),
    (("w051", "w052"), "w051", "of our Lord"),
    (("w059", "w060"), "w060", "until"),
    (("w067", "w068"), "w067", "of our Lord"),
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def assert_english(layer):
    expected = [
        dict(words=list(words), anchor=anchor, gloss=gloss) for words, anchor, gloss in GROUPS
    ]
    require(
        layer["segments"]["s01"]["alignments"] == expected, "Epistle short complete constructions"
    )
    require(
        layer["words"]["w049"].get("gloss") == "while you await",
        "Epistle dative-controlled expectation",
    )
    require(
        layer["words"]["w057"].get("gloss") == "will confirm", "Epistle ordinary predictive future"
    )
    require(layer["words"]["w055"].get("gloss") == "who", "Epistle continuing relative")
    require(
        [layer["words"][word].get("gloss") for word in ("w046", "w047", "w048")]
        == ["in", "any", "grace"],
        "Epistle retained gift complement",
    )


def assert_polish(layer):
    require(
        layer["words"]["w049"].get("gloss") == "gdy oczekujecie",
        "Epistle dative-controlled expectation",
    )
    require(layer["words"]["w055"].get("gloss") == "który", "Epistle continuing relative")


@pytest.mark.parametrize("language", ("pl", "en"))
def test_actual_captions_account_for_all70_positions(language):
    core = read("texts/" + RELATIVE)
    path = f"languages/{language}/texts/{RELATIVE}"
    layer = read(path)
    (assert_polish if language == "pl" else assert_english)(layer)
    expected = Counter(f"w{i:03}" for i in range(1, 71))
    realized = Counter(word for word, value in layer["words"].items() if "gloss" in value)
    realized.update(
        word for group in layer["segments"]["s01"].get("alignments", []) for word in group["words"]
    )
    assert realized == expected
    assert interlinear.check(expand_core(core), layer) == []
    assert language_packs.check_layer(core, layer, ROOT / path) == []
    by_id = {word["id"]: word for word in core["segments"][0]["words"]}
    assert by_id["w049"]["morph"]["case"] == "dat"
    assert by_id["w049"]["morph"]["number"] == "pl"
    assert by_id["w049"]["head"] == "w044"
    assert by_id["w057"]["morph"]["tense"] == "fut"
    for key in ("w023", "w037"):
        assert by_id[key]["morph"]["tense"] == "perf"
        assert by_id[key]["morph"]["voice"] == "pass"


@pytest.mark.parametrize("index", range(len(GROUPS)))
def test_each_group_rejects_reversal_wrong_agency_and_duplicate_member(index):
    core = read("texts/" + RELATIVE)
    layer = read("languages/en/texts/" + RELATIVE)
    assert_english(layer)
    assert interlinear.check(expand_core(core), layer) == []
    for field, value in (
        ("gloss", "a different predicate"),
        ("words", list(reversed(GROUPS[index][0]))),
    ):
        bad = deepcopy(layer)
        bad["segments"]["s01"]["alignments"][index][field] = value
        assert bad != layer
        with pytest.raises(AssertionError, match=r"^Epistle short complete constructions$"):
            assert_english(bad)
        assert_english(layer)
    bad = deepcopy(layer)
    member = GROUPS[index][0][0]
    bad["words"][member]["gloss"] = "duplicate"
    diagnostic = f"{TEXT}:{member}:en: expected exactly one direct gloss or alignment"
    assert diagnostic in interlinear.check(expand_core(core), bad)
    assert interlinear.check(expand_core(core), layer) == []


@pytest.mark.parametrize(
    "language,word,value,diagnostic",
    (
        ("pl", "w049", "oczekując", "dative-controlled expectation"),
        ("en", "w049", "awaiting", "dative-controlled expectation"),
        ("en", "w057", "shall confirm", "ordinary predictive future"),
        ("pl", "w055", "Który", "continuing relative"),
        ("en", "w055", "Who", "continuing relative"),
        ("en", "w046", "without", "retained gift complement"),
        ("en", "w047", "no", "retained gift complement"),
        ("en", "w048", "blame", "retained gift complement"),
    ),
)
def test_contextual_captions_cannot_regress(language, word, value, diagnostic):
    layer = read(f"languages/{language}/texts/{RELATIVE}")
    check = assert_polish if language == "pl" else assert_english
    check(layer)
    bad = deepcopy(layer)
    bad["words"][word]["gloss"] = value
    assert bad != layer
    with pytest.raises(AssertionError, match="^Epistle " + diagnostic + "$"):
        check(bad)
    check(layer)


def assert_source(row):
    require(row["role"] == "direct_approved_print", "Epistle actual approved printing")
    require(
        row["locator"]["printed"] == "p. 405"
        and row["locator"]["scan"] == "leaf n486 / PDF p. 487"
        and row["evidence_sha256"]
        == "b57e0775846832e423c12242e0a75ce4021ae7ec306ea36940f2460ff28b0af5",
        "Epistle actual source location",
    )


@pytest.mark.parametrize(
    "field,value,diagnostic",
    (
        ("role", "official_text", "actual approved printing"),
        ("evidence_sha256", "0" * 64, "actual source location"),
    ),
)
def test_source_keeps_its_printing_and_actual_page(field, value, diagnostic):
    graph = read("bibliography/graph.json")
    (row,) = [entry for entry in graph["uses"] if entry["id"] == f"use.{TEXT}.mr1962"]
    assert_source(row)
    bad = deepcopy(row)
    bad[field] = value
    with pytest.raises(AssertionError, match="^Epistle " + diagnostic + "$"):
        assert_source(bad)
    assert_source(row)
