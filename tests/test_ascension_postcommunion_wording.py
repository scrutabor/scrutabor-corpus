"""The current Ascension Postcommunion's finite group and contextual guarantees."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from ascension_postcommunion_wording import (
    POSTCOMMUNION,
    POSTCOMMUNION_HELP,
    alignments,
    assert_postcommunion_constructions,
    ids,
    words,
)

from build_reader import store
from checks import english, interlinear, interlinear_quality
from checks.language_packs import check_layer
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]


def core(text):
    return store.core(ROOT, text)


def layer(language, text):
    return store.raw_layer(ROOT, language, text)


def layer_path(language, text):
    return store.layer_path(ROOT, language, text)


def provenance(language):
    rows = json.loads((ROOT / "languages" / language / "translation-provenance.json").read_text())
    return {row["site"]: row for row in rows["sites"]}


def clean(doc, lay):
    assert interlinear.check(doc, lay) == []
    if lay["language"] == "en":
        assert english.check(doc, lay) == []
        assert interlinear_quality.check(doc, lay) == []


def rejects(check_fn, *args, message):
    with pytest.raises(AssertionError) as caught:
        check_fn(*args)
    assert str(caught.value).splitlines()[0] == message


@pytest.mark.parametrize("language", ["pl", "en"])
def test_postcommunion_current_groups_preserve_complete_membership(language):
    doc, lay = core(POSTCOMMUNION), layer(language, POSTCOMMUNION)
    assert_postcommunion_constructions(doc, lay)
    assert len(words(doc)) == 38
    clean(doc, lay)
    assert check_layer(doc, lay, layer_path(language, POSTCOMMUNION)) == []


@pytest.mark.parametrize(
    "damage,diagnostic",
    [
        ("missing-member", "postcommunion membership"),
        ("duplicate-direct", "postcommunion membership"),
        ("wrong-anchor", "postcommunion constructions"),
        ("lost-purpose", "postcommunion constructions"),
        ("lost-subject", "postcommunion constructions"),
        ("altered-efficacy", "postcommunion constructions"),
    ],
    ids=[
        "missing-member",
        "duplicate-direct",
        "wrong-anchor",
        "lost-purpose",
        "lost-subject",
        "altered-efficacy",
    ],
)
def test_postcommunion_groups_reject_owned_damage_and_restore(damage, diagnostic):
    doc, lay = core(POSTCOMMUNION), layer("en", POSTCOMMUNION)
    pristine = deepcopy((doc, lay))
    assert_postcommunion_constructions(doc, lay)
    bad = deepcopy(lay)
    purpose = [g for g in alignments(bad) if g["words"] == ids(12, 13)]
    efficacy = [g for g in alignments(bad) if g["words"] == ids(14, 15, 16)]
    assert len(purpose) == len(efficacy) == 1, "postcommunion mutation addresses"
    if damage == "missing-member":
        purpose[0]["words"].remove("w012")
    elif damage == "duplicate-direct":
        bad["words"]["w014"]["gloss"] = "unseen"
    elif damage == "wrong-anchor":
        efficacy[0]["anchor"] = "w016"
    elif damage == "lost-purpose":
        purpose[0]["gloss"] = "we have received"
    elif damage == "lost-subject":
        efficacy[0]["gloss"] = "may obtain through unseen efficacy"
    else:
        efficacy[0]["gloss"] = "we may obtain unseen fruit"
    assert bad != lay, "nonvacuous postcommunion mutation"
    rejects(assert_postcommunion_constructions, doc, bad, message=diagnostic)
    assert (doc, lay) == pristine, "postcommunion sibling fixtures unchanged"
    assert_postcommunion_constructions(doc, lay)
    clean(doc, lay)


def test_postcommunion_effectu_help_and_accusative_object_remain_distinct():
    doc, en, pl = core(POSTCOMMUNION), layer("en", POSTCOMMUNION), layer("pl", POSTCOMMUNION)
    actual_words = words(doc)
    assert actual_words["w009"]["morph"] == {
        "pos": "pron",
        "case": "acc",
        "number": "pl",
        "gender": "n",
    }
    assert actual_words["w012"]["head"] == "w009"
    assert actual_words["w014"]["head"] == "w016"
    assert actual_words["w016"]["morph"]["case"] == "abl"
    assert en["words"]["w009"]["gloss"] == "what"
    assert doc["localization"]["explanations"]["w016"] == {"languages": ["en"]}
    assert en["words"]["w016"]["explanation"] == POSTCOMMUNION_HELP
    assert "explanation" not in pl["words"]["w016"]
    for language, lay in (("pl", pl), ("en", en)):
        assert check_layer(doc, lay, layer_path(language, POSTCOMMUNION)) == []
        source = provenance(language)[f"{POSTCOMMUNION}.s01.{language}"]
        assert source["source_sha256"] == canonical_hash(source_payload(doc["segments"][0]))
        assert (source["origin"], source["review"], source["familiar_core"]) == (
            "working-unsettled",
            "working",
            False,
        )
    assert provenance("en")[f"{POSTCOMMUNION}.s01.en"]["target_sha256"] == (
        "6198a5df5d824f51389e9cd4b1b940cc49c5c8de2ec9e5fc3004dae5c64ea8a1"
    )
