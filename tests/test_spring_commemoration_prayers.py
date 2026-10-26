"""Complete April orations and the contextual constructions they preserve."""

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

from checks import delivery, language_packs, orations, participation, prose

ROOT = Path(__file__).resolve().parent.parent
TEXTS = (
    "proprium.sancti-petri-martyris-collecta",
    "proprium.sancti-petri-martyris-secreta",
    "proprium.sancti-petri-martyris-postcommunio",
    "proprium.sanctae-catharinae-senensis-collecta",
    "proprium.sanctae-catharinae-senensis-secreta",
    "proprium.sanctae-catharinae-senensis-postcommunio",
)
LANGUAGES = ("en", "pl")
WORD_COUNTS = (44, 41, 40, 43, 39, 39)


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def core(text):
    return read(f"texts/{text.replace('.', '/', 1)}.json")


def layer(text, language):
    return read(f"languages/{language}/texts/{text.replace('.', '/', 1)}.json")


def check(doc, target):
    path = ROOT / f"languages/{target['language']}/texts/{doc['id'].replace('.', '/', 1)}.json"
    return language_packs.check_layer(doc, target, path)


def words(doc):
    return {word["id"]: word for segment in doc["segments"] for word in segment["words"]}


@pytest.mark.parametrize("text, count", zip(TEXTS, WORD_COUNTS, strict=True))
def test_complete_core_boundaries_and_roles(text, count):
    doc = core(text)
    assert len(words(doc)) == count
    assert list(words(doc)) == [f"w{i:03d}" for i in range(1, count + 1)]
    assert language_packs.check_core(doc) == []
    assert orations.check_doc(doc) == ([], 1)
    assert delivery.check_doc(doc)[0] == []
    assert participation.check_doc(doc)[0] == []
    assert len(doc["segments"]) == (3 if text.endswith("secreta") else 2)
    assert [word["form"] for word in doc["segments"][-1]["words"]] == ["Amen"]
    assert doc["segments"][-1]["speaker"] == "minister"


@pytest.mark.parametrize("text", TEXTS)
@pytest.mark.parametrize("language", LANGUAGES)
def test_complete_language_and_own_prose(text, language):
    doc, target = core(text), layer(text, language)
    assert check(doc, target) == []
    assert prose.check(target) == []
    assert not any("note" in item for item in target["words"].values())
    assert set(target) == {"schema_version", "language", "text", "about", "segments", "words"}


@pytest.mark.parametrize("text", TEXTS)
@pytest.mark.parametrize("language", LANGUAGES)
def test_missing_introduction_is_rejected_and_original_recovers(text, language):
    doc, healthy = core(text), layer(text, language)
    assert check(doc, healthy) == []
    bad = deepcopy(healthy)
    del bad["about"]
    assert check(doc, bad) == [f"{language}:{text}: about is required and must be nonempty"]
    assert check(doc, healthy) == []


@pytest.mark.parametrize("text", TEXTS)
@pytest.mark.parametrize("language", LANGUAGES)
def test_private_wrapper_fields_are_not_language_document_fields(text, language):
    doc, healthy = core(text), layer(text, language)
    assert check(doc, healthy) == []
    bad = deepcopy(healthy)
    bad["status"] = "working"
    assert check(doc, bad) == [f"{language}:{text}: unknown document keys ['status']"]
    assert check(doc, healthy) == []


@pytest.mark.parametrize("text", TEXTS)
@pytest.mark.parametrize("language", LANGUAGES)
def test_required_contextual_explanation_cannot_disappear(text, language):
    doc, healthy = core(text), layer(text, language)
    assert check(doc, healthy) == []
    bad = deepcopy(healthy)
    word = next(key for key, value in bad["words"].items() if "explanation" in value)
    del bad["words"][word]["explanation"]
    assert check(doc, bad) == [
        f"{language}:{text}: explanation topology differs — missing=['{word}'] extra=[]"
    ]
    assert check(doc, healthy) == []


@pytest.mark.parametrize("language", LANGUAGES)
def test_shared_note_topology_cannot_hide_language_asymmetry(language):
    text = TEXTS[4]
    doc, healthy = core(text), layer(text, language)
    assert check(doc, healthy) == []
    bad = deepcopy(healthy)
    if language == "en":
        bad["words"]["w005"]["note"] = (
            "The plural relative cannot refer to the singular offering alone."
        )
        expected = "missing=[] extra=['w005']"
    else:
        doc = deepcopy(doc)
        doc["localization"]["notes"] = ["w005"]
        expected = "missing=['w005'] extra=[]"
    assert check(doc, bad) == [f"{language}:{text}: note topology differs — {expected}"]
    assert check(core(text), healthy) == []


@pytest.mark.parametrize(
    "language, groups, members, direct", (("en", 65, 185, 61), ("pl", 20, 68, 178))
)
def test_all_positions_are_realized_once_in_short_contiguous_phrases(
    language, groups, members, direct
):
    observed = Counter()
    for text in TEXTS:
        doc, target = core(text), layer(text, language)
        assert check(doc, target) == []
        for segment in doc["segments"]:
            ids = [word["id"] for word in segment["words"]]
            positions = {word: index for index, word in enumerate(ids)}
            realized = [word for word in ids if "gloss" in target["words"][word]]
            observed["direct"] += len(realized)
            for group in target["segments"][segment["id"]].get("alignments", []):
                assert 2 <= len(group["words"]) <= 5
                assert group["anchor"] in group["words"]
                indices = [positions[word] for word in group["words"]]
                assert indices == list(range(indices[0], indices[0] + len(indices)))
                realized.extend(group["words"])
                observed.update(groups=1, members=len(group["words"]))
            assert Counter(realized) == Counter(ids)
    assert observed == {"groups": groups, "members": members, "direct": direct}


@pytest.mark.parametrize("text", TEXTS)
@pytest.mark.parametrize("language", LANGUAGES)
def test_missing_realized_gloss_is_not_treated_as_an_empty_translation(text, language):
    doc, healthy = core(text), layer(text, language)
    assert check(doc, healthy) == []
    bad = deepcopy(healthy)
    word = next(key for key, value in bad["words"].items() if "gloss" in value)
    del bad["words"][word]["gloss"]
    errors = check(doc, bad)
    assert any(
        word in error and "expected exactly one direct gloss or alignment" in error
        for error in errors
    )
    assert check(doc, healthy) == []


@pytest.mark.parametrize("text", TEXTS)
@pytest.mark.parametrize("language", LANGUAGES)
def test_grouped_member_cannot_be_realized_twice(text, language):
    doc, healthy = core(text), layer(text, language)
    assert check(doc, healthy) == []
    bad = deepcopy(healthy)
    group = next(
        group for segment in bad["segments"].values() for group in segment.get("alignments", [])
    )
    word = group["words"][0]
    bad["words"][word]["gloss"] = "duplicate"
    errors = check(doc, bad)
    assert any(
        word in error and "expected exactly one direct gloss or alignment" in error
        for error in errors
    )
    assert check(doc, healthy) == []


@pytest.mark.parametrize("text", TEXTS)
@pytest.mark.parametrize("language", LANGUAGES)
def test_own_prose_punctuation_does_not_rewrite_prayer_translation(text, language):
    healthy = layer(text, language)
    assert prose.check(healthy) == []
    bad = deepcopy(healthy)
    bad["about"] += ";"
    assert any("about" in error and "semicolon" in error for error in prose.check(bad))
    translated = deepcopy(healthy)
    translated["segments"]["s01"]["translation"] += ";"
    assert prose.check(translated) == []
    assert prose.check(healthy) == []


def assert_constructions(peter, catherine_secret, catherine_postcommunion):
    p, s, c = words(peter), words(catherine_secret), words(catherine_postcommunion)
    assert (p["w001"]["morph"]["case"], p["w002"]["morph"]["case"]) == ("acc", "acc"), (
        "faithful people are objects"
    )
    assert p["w005"]["morph"]["case"] == "nom", "sacraments are the grammatical subject"
    assert s["w005"]["head"] == "w011" and s["w005"]["morph"]["number"] == "pl", (
        "selected preces antecedent retained"
    )
    assert (c["w005"]["head"], c["w010"]["head"]) == ("w008", "w008"), (
        "both relatives refer to the table"
    )


def test_specific_constructions_and_lossless_contextual_help():
    assert_constructions(core(TEXTS[2]), core(TEXTS[4]), core(TEXTS[5]))
    english = layer(TEXTS[2], "en")
    assert next(
        group for group in english["segments"]["s01"]["alignments"] if group["anchor"] == "w004"
    ) == {
        "words": ["w004", "w005", "w006", "w007"],
        "anchor": "w004",
        "gloss": "may the sacraments we have received guard",
    }
    help_text = layer(TEXTS[4], "en")["words"]["w005"]
    assert help_text == {
        "gloss": "which",
        "explanation": (
            "The prayers are offered on Catherine’s feast, and the saving offering joins them "
            "in rising to God. The plural relative can refer to the prayers or to the prayers "
            "and the offering together. It cannot refer to the singular offering alone."
        ),
    }


@pytest.mark.parametrize(
    "mutation, message",
    (
        ("object", "faithful people are objects"),
        ("subject", "sacraments are the grammatical subject"),
        ("antecedent", "selected preces antecedent retained"),
        ("table", "both relatives refer to the table"),
    ),
)
def test_same_length_semantic_regressions_fail_explicit_construction_oracles(mutation, message):
    healthy = (core(TEXTS[2]), core(TEXTS[4]), core(TEXTS[5]))
    assert_constructions(*healthy)
    bad = deepcopy(healthy)
    if mutation == "object":
        words(bad[0])["w001"]["morph"]["case"] = "nom"
    elif mutation == "subject":
        words(bad[0])["w005"]["morph"]["case"] = "acc"
    elif mutation == "antecedent":
        words(bad[1])["w005"]["head"] = "w013"
    else:
        words(bad[2])["w010"]["head"] = "w012"
    with pytest.raises(AssertionError, match=message):
        assert_constructions(*bad)
    assert_constructions(*healthy)
