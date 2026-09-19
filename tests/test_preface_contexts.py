"""Contextual readings shared by prefaces and their biblical quotations."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MARIAN = [
    "praefatio-beatae-mariae-virginis",
    "praefatio-beatae-mariae-virginis-in-annuntiatione",
    "praefatio-beatae-mariae-virginis-in-assumptione",
    "praefatio-beatae-mariae-virginis-in-conceptione-immaculata",
    "praefatio-beatae-mariae-virginis-in-nativitate",
    "praefatio-beatae-mariae-virginis-in-transfixione",
    "praefatio-beatae-mariae-virginis-in-visitatione",
]
JOSEPH = ["praefatio-sancti-ioseph-in-festivitate", "praefatio-sancti-ioseph-in-solemnitate"]
PASCHAL = [
    ("ordinarium/praefatio-paschalis-in-die", 22),
    ("ordinarium/praefatio-paschalis-in-nocte", 22),
    ("proprium/dominica-resurrectionis-alleluia", 3),
    ("proprium/dominica-resurrectionis-communio", 1),
    ("proprium/dominica-resurrectionis-epistola", 13),
]


def words(text):
    doc = json.loads((ROOT / "texts" / f"{text}.json").read_text())
    return {w["id"]: w for s in doc["segments"] for w in s.get("words", [])}


@pytest.mark.parametrize("text,base", PASCHAL)
def test_our_passover_and_sacrificed_christ_have_distinct_agreement(text, base):
    ws = words(text)
    modifier = ws[f"w{base + 1:03d}"]
    assert modifier["morph"] == {"pos": "adj", "case": "nom", "number": "sg", "gender": "n"}
    assert modifier["head"] == f"w{base:03d}"
    assert ws[f"w{base + 2:03d}"]["head"] == f"w{base + 4:03d}"
    assert not modifier.get("substantive")


@pytest.mark.parametrize("text,base", PASCHAL)
@pytest.mark.parametrize(
    "language,gloss", [("pl", "został ofiarowany"), ("en", "has been sacrificed")]
)
def test_sacrifice_is_one_finite_realization(text, base, language, gloss):
    doc = json.loads((ROOT / "languages" / language / "texts" / f"{text}.json").read_text())
    members = [f"w{base + 2:03d}", f"w{base + 3:03d}"]
    matching = [a for a in doc["segments"]["s01"]["alignments"] if a["words"] == members]
    assert len(matching) == 1
    assert matching[0]["gloss"] == gloss
    assert all("gloss" not in doc["words"][wid] for wid in members)


@pytest.mark.parametrize("name", MARIAN + JOSEPH)
def test_te_is_the_object_of_praise_not_an_ablative(name):
    assert words(f"ordinarium/{name}")["w023"]["morph"]["case"] == "acc"


@pytest.mark.parametrize("name", MARIAN)
def test_marian_relative_and_possessive_refer_to_mary_and_her_son(name):
    ws = words(f"ordinarium/{name}")
    offset = int(name.endswith("immaculata"))
    assert ws[f"w{34 + offset:03d}"]["morph"]["gender"] == "f"
    assert ws[f"w{37 + offset:03d}"]["head"] == f"w{36 + offset:03d}"


@pytest.mark.parametrize("name", JOSEPH)
def test_joseph_is_given_to_the_virgin_by_god(name):
    ws = words(f"ordinarium/{name}")
    assert ws["w040"]["morph"]["case"] == "dat"
    assert ws["w039"]["morph"]["case"] == "abl"
    assert ws["w038"]["head"] == "w039"
    assert ws["w044"]["head"] == "w034"
    assert ws["w028"]["morph"]["gender"] == "n"
    assert ws["w028"]["head"] == "w030"


@pytest.mark.parametrize("ending", ["die", "nocte"])
def test_easter_preface_distinguishes_object_time_and_appointed_day(ending):
    ws = words(f"ordinarium/praefatio-paschalis-in-{ending}")
    assert ws["w009"]["morph"]["case"] == "acc"
    assert ws["w012"]["head"] == "w013"
    assert ws["w012"]["morph"]["gender"] == "n"
    assert ws["w015"]["head"] == "w018"
    assert ws["w018"]["morph"]["gender"] == "f"


def test_easter_epistle_has_a_new_batch_and_old_leaven():
    ws = words("proprium/dominica-resurrectionis-epistola")
    assert ws["w007"]["head"] == "w008"
    assert (
        ws["w007"]["morph"]["case"],
        ws["w007"]["morph"]["gender"],
        ws["w007"]["morph"]["number"],
    ) == ("nom", "f", "sg")
    assert ws["w011"]["head"] == "w010"
    assert ws["w023"]["head"] == "w022"
    assert (ws["w023"]["morph"]["case"], ws["w023"]["morph"]["gender"]) == ("abl", "n")


def test_exclusive_possessor_is_not_forced_to_agree_with_the_possessed_noun():
    ws = words("proprium/dominica-xvi-post-pentecosten-communio")
    assert ws["w003"]["morph"]["gender"] == "f"
    assert ws["w005"]["morph"]["case"] == "gen"
    assert ws["w005"]["morph"]["gender"] == "m"
    assert ws["w005"]["substantive"] is True
