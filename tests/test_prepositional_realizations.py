"""Contextual relations, complete idioms, and legitimate case realizations."""

import json

import pytest

from build_reader import emit
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear
from checks.layout import CORPUS

DIRECT = (
    ("pl", "sancti-matthiae-apostoli-epistola", "w008", "braci"),
    ("en", "dedicatio-sancti-michaelis-archangeli-evangelium", "w022", "in"),
    ("en", "dedicatio-sancti-michaelis-archangeli-evangelium", "w024", "of them"),
    ("en", "dominica-i-in-quadragesima-postcommunio", "w012", "into"),
    ("en", "dominica-i-in-quadragesima-postcommunio", "w013", "of the mystery"),
    ("en", "dominica-i-in-quadragesima-postcommunio", "w017", "fellowship"),
    ("en", "dominica-pentecostes-offertorium", "w014", "in"),
    ("en", "dominica-resurrectionis-collecta", "w005", "through"),
    ("en", "dominica-resurrectionis-evangelium", "w055", "on"),
    ("en", "dominica-v-post-pentecosten-offertorium", "w014", "at"),
    ("en", "dominica-vii-post-pentecosten-secreta", "w012", "from"),
    ("en", "dominica-xiii-post-pentecosten-epistola", "w018", "of"),
    ("en", "dominica-xiii-post-pentecosten-evangelium", "w010", "through"),
    ("en", "dominica-xix-post-pentecosten-offertorium", "w003", "in"),
    ("en", "epiphania-domini-evangelium", "w005", "in"),
    ("en", "immaculatum-cor-beatae-mariae-virginis-graduale", "w004", "in"),
    ("en", "nativitas-domini-in-aurora-evangelium", "w006", "to"),
    ("en", "nativitas-domini-in-nocte-evangelium", "w181", "in"),
    ("en", "septem-dolorum-beatae-mariae-virginis-sequentia", "w099", "in"),
    ("en", "dominica-in-albis-alleluia", "w023", "of disciples"),
    ("en", "sanctae-annae-matris-beatae-mariae-virginis-evangelium", "w105", "of the just"),
    ("pl", "dedicatio-sancti-michaelis-archangeli-evangelium", "w024", "nich"),
    ("pl", "sancti-matthiae-apostoli-secreta", "w015", "dzięki"),
    ("pl", "sancti-matthiae-apostoli-secreta", "w016", "której"),
    ("pl", "sancti-petri-et-pauli-apostolorum-secreta", "w011", "dzięki"),
    ("pl", "sancti-petri-et-pauli-apostolorum-secreta", "w012", "której"),
)
GROUPS = (
    ("pl", "beatae-mariae-virginis-a-rosario-epistola", "w018 w019", "w019", "od pradawna"),
    ("en", "beatae-mariae-virginis-a-rosario-epistola", "w018 w019", "w019", "of old"),
    ("pl", "nativitas-beatae-mariae-virginis-epistola", "w018 w019", "w019", "od pradawna"),
    ("en", "nativitas-beatae-mariae-virginis-epistola", "w018 w019", "w019", "of old"),
    ("pl", "dedicatio-sancti-michaelis-archangeli-evangelium", "w022 w023", "w023", "pośrodku"),
    ("pl", "sancti-ioseph-opificis-introitus", "w031 w032", "w032", "na próżno"),
    ("en", "dominica-x-post-pentecosten-evangelium", "w065 w066", "w066", "afar"),
    ("pl", "dominica-in-albis-alleluia", "w021 w022", "w022", "pośród"),
    ("pl", "maternitas-beatae-mariae-virginis-evangelium", "w051 w052", "w052", "pośród"),
    ("pl", "sancta-familia-evangelium", "w063 w064", "w064", "pośród"),
    ("pl", "sancti-ioannis-apostoli-et-evangelistae-epistola", "w051 w052", "w052", "pośrodku"),
    ("pl", "sancti-ioannis-apostoli-et-evangelistae-introitus", "w001 w002", "w002", "Pośrodku"),
    ("pl", "sancti-ioannis-apostoli-et-evangelistae-introitus", "w050 w051", "w051", "Pośrodku"),
    ("pl", "sancti-matthaei-apostoli-et-evangelistae-epistola", "w077 w078", "w078", "pośrodku"),
    (
        "pl",
        "sanctae-annae-matris-beatae-mariae-virginis-evangelium",
        "w103 w104",
        "w104",
        "spośród",
    ),
    ("pl", "sancti-matthiae-apostoli-epistola", "w006 w007", "w007", "pośród"),
)
CASES = (
    ("annuntiatio-beatae-mariae-virginis-secreta", "w020"),
    ("dominica-i-in-quadragesima-evangelium", "w052"),
    ("dominica-ii-post-pascha-postcommunio", "w011"),
    ("dominica-vii-post-pentecosten-evangelium", "w009"),
)
LAYERS = sorted({row[:2] for row in (*DIRECT, *GROUPS)})


def load(language, text):
    return json.loads(
        (CORPUS / "languages" / language / "texts/proprium" / (text + ".json")).read_bytes()
    )


def alignments(layer):
    return [
        group for segment in layer["segments"].values() for group in segment.get("alignments", [])
    ]


@pytest.mark.parametrize("language,text,wid,gloss", DIRECT)
def test_prepositional_or_genitive_relation(language, text, wid, gloss):
    layer = load(language, text)
    assert layer["words"][wid].get("gloss") == gloss
    assert not any(wid in group["words"] for group in alignments(layer))


@pytest.mark.parametrize("language,text,words,anchor,gloss", GROUPS)
def test_idiom_includes_the_complete_relation(language, text, words, anchor, gloss):
    layer = load(language, text)
    ids = words.split()
    actual = [group for group in alignments(layer) if set(ids) & set(group["words"])]
    assert actual == [{"words": ids, "anchor": anchor, "gloss": gloss}]
    assert all("gloss" not in layer["words"][wid] for wid in ids)


@pytest.mark.parametrize("text,wid", CASES)
def test_polish_case_can_realize_a_latin_preposition(text, wid):
    core = json.loads((CORPUS / "texts/proprium" / (text + ".json")).read_bytes())
    layer = load("pl", text)
    actual = [group for group in alignments(layer) if wid in group["words"]]
    assert actual == [{"words": [wid], "reason": "inflection"}]
    assert "gloss" not in layer["words"][wid]
    assert not interlinear.check(expand_core(core), enrich_layer(core, layer))


@pytest.mark.parametrize("language,text", LAYERS)
def test_relation_providers_roundtrip_through_the_reader(language, text):
    core = json.loads((CORPUS / "texts/proprium" / (text + ".json")).read_bytes())
    doc = expand_core(core)
    layer = enrich_layer(core, load(language, text))
    assert not interlinear.check(doc, layer)
    parses, analyses, citations = emit.Table(), emit.Table(), emit.Table()
    ca = emit.core_artifact(doc, core, parses, analyses, citations)
    la = emit.language_artifact(doc, layer, citations)
    _, actual = emit.expand(
        ca, la, parses.edition(), analyses.edition(), citations.edition(), citations.edition()
    )
    assert actual["words"] == layer["words"]
    assert actual["segments"] == layer["segments"]
