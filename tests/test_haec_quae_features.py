"""Bounded paradigm checks keep contextual plural alternatives open."""

import copy
import json
from pathlib import Path

import pytest

from checks.lint import HAEC_QUAE_LEMMAS, lint_text
from checks.normalize import fold_ligatures, strip_accents

NEW_CONTEXTS = {
    ("proprium.haec-hostia-secreta", "w001"): {
        "pos": "pron",
        "case": "nom",
        "number": "sg",
        "gender": "f",
    },
    ("proprium.refecti-cibo-potuque-postcommunio", "w013"): {
        "pos": "pron",
        "case": "acc",
        "number": "pl",
        "gender": "n",
    },
    ("proprium.sanctae-catharinae-senensis-postcommunio", "w010"): {
        "pos": "pron",
        "case": "nom",
        "number": "sg",
        "gender": "f",
    },
    ("proprium.sancti-athanasii-secreta", "w018"): {
        "pos": "pron",
        "case": "acc",
        "number": "pl",
        "gender": "n",
    },
    ("proprium.sancti-augustini-cantuariensis-secreta", "w017"): {
        "pos": "pron",
        "case": "nom",
        "number": "pl",
        "gender": "f",
    },
    ("proprium.sancti-bedae-venerabilis-secreta", "w013"): {
        "pos": "pron",
        "case": "nom",
        "number": "sg",
        "gender": "f",
    },
    ("proprium.sancti-gregorii-nazianzeni-secreta", "w013"): {
        "pos": "pron",
        "case": "nom",
        "number": "sg",
        "gender": "f",
    },
    ("proprium.sancti-petri-martyris-postcommunio", "w006"): {
        "pos": "pron",
        "case": "acc",
        "number": "pl",
        "gender": "n",
    },
    ("proprium.sancti-philippi-nerii-postcommunio", "w017"): {
        "pos": "pron",
        "case": "acc",
        "number": "pl",
        "gender": "n",
    },
    ("proprium.sancti-roberti-bellarmino-postcommunio", "w002"): {
        "pos": "pron",
        "case": "acc",
        "number": "pl",
        "gender": "n",
    },
    ("proprium.sancti-stanislai-postcommunio", "w001"): {
        "pos": "pron",
        "case": "nom",
        "number": "sg",
        "gender": "f",
    },
    ("proprium.sanctorum-nerei-achillei-domitillae-et-pancratii-postcommunio", "w015"): {
        "pos": "pron",
        "case": "acc",
        "number": "pl",
        "gender": "n",
    },
    ("proprium.sanctorum-nerei-achillei-domitillae-et-pancratii-secreta", "w015"): {
        "pos": "pron",
        "case": "nom",
        "number": "sg",
        "gender": "f",
    },
    ("proprium.super-has-hostias-secreta", "w009"): {
        "pos": "pron",
        "case": "nom",
        "number": "sg",
        "gender": "f",
    },
    ("proprium.vigilia-ascensionis-evangelium", "w036"): {
        "pos": "pron",
        "case": "nom",
        "number": "sg",
        "gender": "f",
    },
    ("proprium.vigilia-ascensionis-evangelium", "w103"): {
        "pos": "pron",
        "case": "acc",
        "number": "pl",
        "gender": "n",
    },
    ("proprium.vigilia-ascensionis-evangelium", "w111"): {
        "pos": "pron",
        "case": "acc",
        "number": "pl",
        "gender": "n",
    },
}


PAIRS = [("hæc", "hic"), ("quæ", "qui")]
READINGS = [
    ("nom", "sg", "f"),
    ("acc", "pl", "n"),
    ("nom", "pl", "f"),
    ("nom", "pl", "n"),
    ("nom", "pl", None),
]


def errors(form, lemma, morph):
    doc = {
        "segments": [
            {"id": "s01", "words": [{"id": "w001", "form": form, "lemma": lemma, "morph": morph}]}
        ]
    }
    found, count = lint_text(doc)
    assert count == 1
    return [error for error in found if "haec/quae form" in error]


def morph(case, number, gender):
    out = {"pos": "pron", "case": case, "number": number}
    if gender is not None:
        out["gender"] = gender
    return out


def test_named_pairs_do_not_shrink_with_the_guard():
    assert HAEC_QUAE_LEMMAS == {"haec": "hic", "quae": "qui"}


@pytest.mark.parametrize(("form", "lemma"), PAIRS)
@pytest.mark.parametrize(("case", "number", "gender"), READINGS)
def test_each_supported_reading_accepts_healthy_rejects_corruption_and_restores(
    form, lemma, case, number, gender
):
    healthy = morph(case, number, gender)
    assert not errors(form, lemma, healthy)
    changes = [("gender", "m"), ("case", None), ("case", "gen"), ("number", None)]
    if (case, number) == ("nom", "sg"):
        # Feminine nominative plural is valid, not an impossible-number case.
        changes += [("gender", None), ("gender", "n")]
    elif case == "acc":
        changes += [("gender", None), ("gender", "f"), ("number", "sg")]
    elif gender != "f":
        changes += [("number", "sg")]
    for field, value in changes:
        bad = copy.deepcopy(healthy)
        if value is None:
            bad.pop(field, None)
        else:
            bad[field] = value
        assert errors(form, lemma, bad), (form, healthy, field, value)
        assert not errors(form, lemma, healthy)


@pytest.mark.parametrize(("form", "lemma"), [("Hǽc", "hic"), ("Quáe", "qui")])
@pytest.mark.parametrize("pos", ["pron", "adj"])
def test_accents_ligatures_and_adjectival_use_do_not_hide_the_guard(form, lemma, pos):
    good = {**morph("acc", "pl", "n"), "pos": pos}
    assert not errors(form, lemma, good)
    assert errors(form, lemma, {**good, "gender": "f"})


@pytest.mark.parametrize(
    ("form", "lemma", "pos"),
    [
        ("quæ", "quis", "pron"),
        ("quæ", "quae", "conj"),
        ("hic", "hic", "adv"),
        ("hæc", "hic", "adv"),
        ("qui", "qui", "pron"),
        ("cuius", "qui", "pron"),
    ],
)
def test_unowned_lemma_surface_and_pos_are_not_forced(form, lemma, pos):
    assert not errors(form, lemma, {"pos": pos})


def test_actual_corpus_class_and_local_ambiguity_are_not_silently_neuter():
    root = Path(__file__).resolve().parent.parent
    count = 0
    new_seen = set()
    for path in sorted((root / "texts").rglob("*.json")):
        doc = json.loads(path.read_text())
        for segment in doc["segments"]:
            for word in segment.get("words", []):
                found = errors(word["form"], word["lemma"], word["morph"])
                assert not found, (doc["id"], word["id"], found)
                surface = fold_ligatures(strip_accents(word["form"])).lower()
                if HAEC_QUAE_LEMMAS.get(surface) == word["lemma"]:
                    count += 1
                    site = (doc["id"], word["id"])
                    if site in NEW_CONTEXTS:
                        assert word["morph"] == NEW_CONTEXTS[site]
                        new_seen.add(site)
                    if (doc["id"], word["id"]) != (
                        "proprium.dominica-iv-in-quadragesima-epistola",
                        "w035",
                    ):
                        assert word["morph"].get("gender") in {"f", "n"}
    assert count == 351
    assert new_seen == set(NEW_CONTEXTS)
    doc = json.loads(
        (root / "texts/proprium/dominica-iv-in-quadragesima-epistola.json").read_text()
    )
    word = next(w for s in doc["segments"] for w in s.get("words", []) if w["id"] == "w035")
    assert word["morph"] == {"pos": "pron", "case": "nom", "number": "pl"}
    analysis = doc["editorial"]["words"]["w035"]["analysis"]
    assert analysis["confidence"] == "medium" and analysis["review"] == "pending"
    assert not errors(word["form"], word["lemma"], word["morph"])


def test_named_cuius_choice_is_qualified_not_a_universal_rule():
    root = Path(__file__).resolve().parent.parent
    doc = json.loads(
        (root / "texts/proprium/dominica-v-post-epiphaniam-postcommunio.json").read_text()
    )
    words = {w["id"]: w for s in doc["segments"] for w in s.get("words", [])}
    assert words["w006"]["lemma"] == "salutare"
    assert words["w009"]["morph"] == {"pos": "pron", "case": "gen", "number": "sg", "gender": "n"}
    analysis = doc["editorial"]["words"]["w009"]["analysis"]
    assert analysis["confidence"] == "medium" and analysis["review"] == "pending"
    assert set(analysis["sources"]) == {"editorial", "whitakers", "collatinus"}


@pytest.mark.parametrize(
    ("name", "wid"),
    [
        ("commemoratio-omnium-fidelium-defunctorum-missa-iii-collecta", "w018"),
        ("dedicatio-sancti-michaelis-archangeli-epistola", "w051"),
        ("dominica-i-passionis-epistola", "w086"),
        ("dominica-ii-in-quadragesima-epistola", "w066"),
        ("dominica-ii-in-quadragesima-introitus", "w008"),
        ("dominica-ii-in-quadragesima-introitus", "w066"),
        ("dominica-ii-passionis-evangelium", "w1426"),
        ("dominica-ii-post-pascha-evangelium", "w088"),
        ("dominica-v-post-pentecosten-collecta", "w024"),
        ("dominica-xxiii-post-pentecosten-epistola", "w109"),
        ("pretiosissimi-sanguinis-domini-nostri-iesu-christi-epistola", "w086"),
        ("sancti-iacobi-apostoli-secreta", "w013"),
    ],
)
def test_read_feminine_plural_referents_are_not_replaced_with_neuter(name, wid):
    root = Path(__file__).resolve().parent.parent
    doc = json.loads((root / f"texts/proprium/{name}.json").read_text())
    word = next(w for s in doc["segments"] for w in s.get("words", []) if w["id"] == wid)
    assert word["morph"] == {"pos": "pron", "case": "nom", "number": "pl", "gender": "f"}
    assert not errors(word["form"], word["lemma"], word["morph"])
