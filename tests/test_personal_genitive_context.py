"""Regression coverage for contextual possessives and personal genitives."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = [
    (
        "proprium.assumptio-beatae-mariae-virginis-epistola.w083",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w082",
        False,
    ),
    (
        "proprium.assumptio-beatae-mariae-virginis-epistola.w093",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w092",
        False,
    ),
    (
        "proprium.cathedra-sancti-petri-epistola.w038",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w037",
        False,
    ),
    (
        "proprium.cathedra-sancti-petri-epistola.w117",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w116",
        False,
    ),
    (
        "proprium.dominica-i-post-epiphaniam-epistola.w029",
        "vester",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w028",
        False,
    ),
    (
        "proprium.dominica-ii-in-quadragesima-introitus.w017",
        "noster",
        {"pos": "adj", "case": "nom", "number": "pl", "gender": "m"},
        "w016",
        False,
    ),
    (
        "proprium.dominica-ii-in-quadragesima-introitus.w075",
        "noster",
        {"pos": "adj", "case": "nom", "number": "pl", "gender": "m"},
        "w074",
        False,
    ),
    (
        "proprium.dominica-ii-passionis-tractus.w042",
        "noster",
        {"pos": "adj", "case": "nom", "number": "pl", "gender": "m"},
        "w041",
        False,
    ),
    (
        "proprium.dominica-iii-in-quadragesima-evangelium.w089",
        "vester",
        {"pos": "adj", "case": "nom", "number": "pl", "gender": "m"},
        "w088",
        False,
    ),
    (
        "proprium.dominica-iii-in-quadragesima-tractus.w028",
        "noster",
        {"pos": "adj", "case": "nom", "number": "pl", "gender": "m"},
        "w027",
        False,
    ),
    (
        "proprium.dominica-in-septuagesima-epistola.w077",
        "noster",
        {"pos": "adj", "case": "nom", "number": "pl", "gender": "m"},
        "w076",
        False,
    ),
    (
        "proprium.dominica-in-sexagesima-epistola.w190",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w189",
        False,
    ),
    (
        "proprium.dominica-in-sexagesima-introitus.w035",
        "noster",
        {"pos": "adj", "case": "nom", "number": "pl", "gender": "m"},
        "w034",
        False,
    ),
    (
        "proprium.dominica-iv-post-pentecosten-epistola.w084",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "n"},
        "w083",
        False,
    ),
    (
        "proprium.dominica-viii-post-pentecosten-alleluia.w011",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w010",
        False,
    ),
    (
        "proprium.dominica-viii-post-pentecosten-introitus.w033",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w032",
        False,
    ),
    (
        "proprium.dominica-xvi-post-pentecosten-epistola.w024",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w023",
        False,
    ),
    (
        "proprium.dominica-xviii-post-pentecosten-epistola.w052",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w051",
        False,
    ),
    (
        "proprium.dominica-xviii-post-pentecosten-epistola.w068",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w067",
        False,
    ),
    (
        "proprium.dominica-xx-post-pentecosten-epistola.w064",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w063",
        False,
    ),
    (
        "proprium.dominica-xx-post-pentecosten-secreta.w011",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "n"},
        "w012",
        False,
    ),
    (
        "proprium.exaltatio-sanctae-crucis-introitus.w008",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w007",
        False,
    ),
    (
        "proprium.exaltatio-sanctae-crucis-introitus.w066",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w065",
        False,
    ),
    (
        "proprium.exaltatio-sanctae-crucis-secreta.w004",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w003",
        False,
    ),
    (
        "proprium.feria-v-in-cena-domini-introitus.w008",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w007",
        False,
    ),
    (
        "proprium.feria-v-in-cena-domini-introitus.w046",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w045",
        False,
    ),
    (
        "proprium.immaculata-conceptio-graduale.w024",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w023",
        False,
    ),
    (
        "proprium.nativitas-domini-in-aurora-epistola.w007",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w006",
        False,
    ),
    (
        "proprium.nativitas-domini-in-die-communio.w007",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w006",
        False,
    ),
    (
        "proprium.nativitas-domini-in-die-graduale.w007",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w006",
        False,
    ),
    (
        "proprium.nativitas-domini-in-nocte-epistola.w006",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w005",
        False,
    ),
    (
        "proprium.nativitas-domini-in-nocte-epistola.w036",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w035",
        False,
    ),
    (
        "proprium.nativitas-domini-in-nocte-postcommunio.w011",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w010",
        False,
    ),
    (
        "proprium.omnium-sanctorum-epistola.w043",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w042",
        False,
    ),
    (
        "proprium.purificatio-beatae-mariae-virginis-graduale.w028",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w027",
        False,
    ),
    (
        "proprium.sacratissimi-cordis-iesu-epistola.w073",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w072",
        False,
    ),
    (
        "proprium.sancti-ioachim-confessoris-postcommunio.w022",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w021",
        False,
    ),
    (
        "proprium.sancti-ioseph-opificis-offertorium.w004",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w003",
        False,
    ),
    (
        "proprium.sancti-ioseph-sponsi-beatae-mariae-virginis-introitus.w017",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w016",
        False,
    ),
    (
        "proprium.sancti-ioseph-sponsi-beatae-mariae-virginis-introitus.w065",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w064",
        False,
    ),
    (
        "proprium.sancti-ioseph-sponsi-beatae-mariae-virginis-secreta.w020",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w019",
        False,
    ),
    (
        "proprium.sancti-lucae-evangelistae-epistola.w126",
        "noster",
        {"pos": "adj", "case": "nom", "number": "pl", "gender": "m"},
        "w125",
        False,
    ),
    (
        "proprium.sanctissimi-nominis-iesu-epistola.w040",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w039",
        False,
    ),
    (
        "proprium.sanctissimi-nominis-iesu-postcommunio.w024",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w023",
        False,
    ),
    (
        "proprium.sanctissimi-nominis-iesu-secreta.w021",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w020",
        False,
    ),
    (
        "proprium.septem-dolorum-beatae-mariae-virginis-alleluia.w014",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w013",
        False,
    ),
    (
        "proprium.septem-dolorum-beatae-mariae-virginis-epistola.w074",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w073",
        False,
    ),
    (
        "proprium.vigilia-nativitatis-communio.w010",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w009",
        False,
    ),
    (
        "proprium.vigilia-nativitatis-epistola.w048",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w047",
        False,
    ),
    (
        "proprium.vigilia-nativitatis-epistola.w073",
        "noster",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        "w072",
        False,
    ),
    (
        "proprium.assumptio-beatae-mariae-virginis-epistola.w092",
        "populus",
        {"case": "gen", "decl": 2, "gender": "m", "number": "sg", "pos": "noun"},
        None,
        False,
    ),
    (
        "proprium.dominica-i-post-epiphaniam-epistola.w028",
        "sensus",
        {"case": "gen", "decl": 4, "gender": "m", "number": "sg", "pos": "noun"},
        None,
        False,
    ),
    (
        "proprium.sancti-lucae-evangelistae-epistola.w125",
        "frater",
        {"case": "nom", "decl": 3, "gender": "m", "number": "pl", "pos": "noun"},
        None,
        False,
    ),
    (
        "proprium.sancti-lucae-evangelistae-epistola.w127",
        "apostolus",
        {"pos": "noun", "case": "nom", "gender": "m", "number": "pl", "decl": 2},
        None,
        False,
    ),
    (
        "proprium.dominica-in-septuagesima-epistola.w078",
        "omnis",
        {"pos": "adj", "case": "nom", "number": "pl", "gender": "m"},
        "w076",
        False,
    ),
    (
        "proprium.vigilia-nativitatis-epistola.w044",
        "mortuus",
        {"case": "gen", "gender": "m", "number": "pl", "pos": "adj"},
        None,
        True,
    ),
]
PERSONAL = [
    ("orationes.te-deum.w173", "nos"),
    ("orationes.te-deum.w176", "nos"),
    ("ordinarium.misereatur.w002", "vos"),
    ("ordinarium.praefatio-sacratissimi-cordis-iesu.w047", "nos"),
    ("proprium.corporis-christi-sequentia.w252", "nos"),
    ("proprium.dominica-ii-in-quadragesima-tractus.w030", "nos"),
    ("proprium.dominica-iii-in-quadragesima-tractus.w035", "nos"),
    ("proprium.dominica-vi-post-epiphaniam-epistola.w077", "nos"),
    ("proprium.dominica-xiii-post-pentecosten-evangelium.w036", "nos"),
    ("proprium.exaltatio-sanctae-crucis-introitus.w027", "nos"),
    ("proprium.exaltatio-sanctae-crucis-introitus.w038", "nos"),
    ("proprium.feria-v-in-cena-domini-introitus.w027", "nos"),
    ("proprium.feria-v-in-cena-domini-introitus.w038", "nos"),
]
COMPOUNDS = [
    "proprium.dominica-i-passionis-evangelium.w143",
    "proprium.dominica-iv-adventus-epistola.w037",
    "proprium.exaltatio-sanctae-crucis-evangelium.w028",
    "proprium.vigilia-pentecostes-evangelium.w125",
]


def read_json(path):
    return json.loads((ROOT / path).read_text())


def word(ref):
    tid, wid = ref.rsplit(".", 1)
    doc = read_json("texts/" + tid.replace(".", "/", 1) + ".json")
    return doc, next(w for s in doc["segments"] for w in s.get("words", []) if w["id"] == wid)


@pytest.mark.parametrize("ref,lemma,morph,head,substantive", EXPECTED, ids=[r[0] for r in EXPECTED])
def test_contextual_parse(ref, lemma, morph, head, substantive):
    _, actual = word(ref)
    assert actual["lemma"] == lemma
    assert actual["morph"] == morph
    assert actual.get("head") == head
    assert actual.get("substantive", False) == substantive


@pytest.mark.parametrize("ref,lemma", PERSONAL, ids=[r[0] for r in PERSONAL])
def test_personal_genitive_is_not_forced_to_possessive(ref, lemma):
    _, actual = word(ref)
    assert actual["lemma"] == lemma
    assert actual["morph"] == {"pos": "pron", "case": "gen", "number": "pl"}
    assert "head" not in actual
    assert "substantive" not in actual


@pytest.mark.parametrize("ref", COMPOUNDS)
def test_compound_keeps_its_printed_form_and_editorial_evidence(ref):
    doc, actual = word(ref)
    assert actual["form"] == "meípsum"
    assert actual["lemma"] == "meipse"
    assert actual["morph"] == {"pos": "pron", "case": "acc", "number": "sg", "gender": "m"}
    editorial = doc["editorial"]
    analysis = editorial.get("words", {}).get(actual["id"], {}).get("analysis")
    if analysis is None:
        analysis = editorial.get("analysis_defaults_words") or editorial["analysis_defaults"]
    assert analysis["sources"] == ["editorial"]


def test_emphatic_compound_uses_personal_components_not_adjective_paradigm():
    entry = read_json("lexicon/lemmata.json")["entries"]["meipse"]
    assert entry == {"head": "ego ipse", "pos": "pron"}


def test_compound_components_have_precise_dictionary_evidence():
    graph = read_json("bibliography/graph.json")
    uses = [u for u in graph["uses"] if u["id"] == "use.lemma.meipse.lewis-short.1879"]
    assert len(uses) == 1
    assert uses[0]["address"] == {"kind": "lemma", "lemma": "meipse"}
    assert uses[0]["role"] == "lexical_support"
    assert uses[0]["digital_item"] == "item.lewis-short.perseus.40038e4.eng1"
