"""Polish preface predicates retain the government of their opening abyśmy."""

import json
from copy import deepcopy
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
SITES = [
    (name, f"w{base + int(name.endswith('immaculata')):03d}", lemma)
    for name in MARIAN
    for base, lemma in [(30, "collaudo"), (31, "benedico"), (33, "praedico")]
] + [
    (name, wid, lemma)
    for name in JOSEPH
    for wid, lemma in [("w031", "benedico"), ("w033", "praedico")]
]
FINITE = {
    "collaudo": {"wysławiali"},
    "benedico": {"błogosławili"},
    "praedico": {"głosili", "sławili"},
}
INFINITIVE = {"collaudo": "wysławiać", "benedico": "błogosławić", "praedico": "głosić"}
CONTROLS = [
    ("praefatio-paschalis-in-die", "w020", "praedico", "sławić"),
    ("praefatio-paschalis-in-nocte", "w020", "praedico", "sławić"),
    ("praefatio-apostolorum", "w012", "exoro", "błagać"),
    *[(name, "w029", "magnifico", "uwielbiali") for name in JOSEPH],
]


def load(name):
    core = json.loads((ROOT / "texts/ordinarium" / f"{name}.json").read_text())
    pl = json.loads((ROOT / "languages/pl/texts/ordinarium" / f"{name}.json").read_text())
    return core, pl


def words(core):
    return {w["id"]: w for s in core["segments"] for w in s.get("words", [])}


def assert_finite_site(core, pl, wid, lemma):
    ws = words(core)
    assert ws["w009"]["lemma"] == "nos"
    assert ws["w009"]["morph"]["case"] == "acc"
    assert ws["w009"]["morph"]["number"] == "pl"
    assert pl["words"]["w009"]["gloss"] == "abyśmy"
    assert ws["w015"]["lemma"] == "ago"
    assert pl["words"]["w015"]["gloss"] == "składali"
    clause = next(s for s in core["segments"] if s["id"] == "s04")
    assert wid in {w["id"] for w in clause["words"]}
    assert ws["w023"]["morph"]["case"] == "acc"
    assert ws[wid]["lemma"] == lemma
    assert (ws[wid]["morph"]["mood"], ws[wid]["morph"]["voice"]) == ("inf", "act")
    assert pl["words"][wid]["gloss"] in FINITE[lemma]


def test_coordinated_preface_population_is_complete():
    found = set()
    for path in (ROOT / "texts/ordinarium").glob("praefatio-*.json"):
        core, pl = load(path.stem)
        ws = words(core)
        if ws.get("w009", {}).get("lemma") != "nos":
            continue
        assert pl["words"]["w009"]["gloss"] == "abyśmy"
        for segment in core["segments"]:
            if segment["id"] != "s04":
                continue
            for word in segment.get("words", []):
                if word["lemma"] in FINITE and word["morph"].get("mood") == "inf":
                    found.add((path.stem, word["id"], word["lemma"]))
    assert len(SITES) == 25
    assert len({name for name, _, _ in SITES}) == 9
    assert found == set(SITES)


@pytest.mark.parametrize("name,wid,lemma", SITES)
def test_polish_coordinate_is_finite_under_abysmy(name, wid, lemma):
    core, pl = load(name)
    assert_finite_site(core, pl, wid, lemma)


@pytest.mark.parametrize("name,wid,lemma", SITES)
def test_infinitive_reversion_is_rejected(name, wid, lemma):
    core, pl = load(name)
    pl = deepcopy(pl)
    pl["words"][wid]["gloss"] = INFINITIVE[lemma]
    with pytest.raises(AssertionError):
        assert_finite_site(core, pl, wid, lemma)


@pytest.mark.parametrize("name,wid,lemma,gloss", CONTROLS)
def test_other_preface_constructions_keep_their_forms(name, wid, lemma, gloss):
    core, pl = load(name)
    ws = words(core)
    assert ws[wid]["lemma"] == lemma
    assert ws[wid]["morph"]["mood"] == "inf"
    assert pl["words"][wid]["gloss"] == gloss
    if lemma == "magnifico":
        assert pl["words"]["w009"]["gloss"] == "abyśmy"
    else:
        assert ws["w009"]["lemma"] != "nos"
        assert pl["words"]["w009"]["gloss"] != "abyśmy"


def test_supported_finite_praise_alternative_is_not_rejected():
    core, pl = load(MARIAN[0])
    pl = deepcopy(pl)
    pl["words"]["w033"]["gloss"] = "sławili"
    assert_finite_site(core, pl, "w033", "praedico")
