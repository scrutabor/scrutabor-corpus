"""Keep neuter quidquid explicit without conflating subject and object."""

import copy
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("dominica-xxiii-post-pentecosten-communio", "w004", "acc"),
    ("dominica-xxiv-post-pentecosten-postcommunio", "w011", "nom"),
    ("commemoratio-omnium-fidelium-defunctorum-missa-i-sequentia", "w058", "nom"),
]


def document(slug):
    return json.loads((ROOT / f"texts/proprium/{slug}.json").read_text())


def neuter_contract(doc, wid, case):
    word = next(w for s in doc["segments"] for w in s["words"] if w["id"] == wid)
    assert word["form"].lower() == "quidquid" and word["lemma"] == "quisquis"
    assert word["morph"] == {"pos": "pron", "case": case, "number": "sg", "gender": "n"}


@pytest.mark.parametrize("slug,wid,case", CASES)
def test_quidquid_has_explicit_neuter_and_contextual_case(slug, wid, case):
    neuter_contract(document(slug), wid, case)


@pytest.mark.parametrize("slug,wid,case", CASES)
@pytest.mark.parametrize("damage", ["missing-gender", "masculine", "wrong-case", "plural"])
def test_quidquid_rejects_incomplete_or_wrong_declension(slug, wid, case, damage):
    doc = document(slug)
    neuter_contract(doc, wid, case)
    bad = copy.deepcopy(doc)
    morph = next(w for s in bad["segments"] for w in s["words"] if w["id"] == wid)["morph"]
    if damage == "missing-gender":
        del morph["gender"]
    elif damage == "masculine":
        morph["gender"] = "m"
    elif damage == "wrong-case":
        morph["case"] = "nom" if case == "acc" else "acc"
    else:
        morph["number"] = "pl"
    with pytest.raises(AssertionError):
        neuter_contract(bad, wid, case)


@pytest.mark.parametrize("slug,wid,case", CASES[:2])
def test_completed_quidquid_analysis_does_not_inherit_old_acceptance(slug, wid, case):
    doc = document(slug)
    neuter_contract(doc, wid, case)
    assert doc["editorial"]["words"][wid]["analysis"] == {
        "confidence": "high",
        "sources": ["editorial", "whitakers", "collatinus"],
        "review": "pending",
    }
