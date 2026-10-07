"""The Immaculate Conception and St Thomas the Apostle as the approved Benziger printing has them.

Page 436 prints the Gradual with a comma after *tu* and the Gospel's *Gábriel* without the
diaeresis; the pinned digital reading's full stop and *Gábriël* are recorded exactly in the
apparatus. The six orations' expanded conclusions are declared composites of the proper page's
cue and the edition's own full printings (p. 123, p. 226) under Rubricae generales 115 a, and
115 b for the Collect's *Per eúndem*. The two Masses print shared texts in full: the lesson of
the Nativity of the Blessed Virgin, the St James Introit and Offertory, and the St Joachim Tract
with *ei;* where its own page has *ei:*. The Immaculate Conception Offertory is the Ave Maria
verse and is protected as that familiar formula.
"""

import json
from pathlib import Path

import pytest

from checks import transcription, translation_provenance
from checks.collate import collate

ROOT = Path(__file__).resolve().parents[1]
IC = "proprium.immaculata-conceptio-"
ST = "proprium.sancti-thomae-apostoli-"
PARTS = ("collecta", "secreta", "postcommunio")
ORATIONS = [f"{mass}{part}" for mass in (IC, ST) for part in PARTS]
P = "proprium."
PRINTINGS = [
    (
        P + "nativitas-beatae-mariae-virginis-epistola",
        "immaculata",
        "pp. 435–436",
        "immaculata-conceptio",
    ),
    (P + "sancti-iacobi-apostoli-introitus", "thomas", "p. 440", "sancti-thomae-apostoli"),
    (P + "sancti-iacobi-apostoli-offertorium", "thomas", "p. 441", "sancti-thomae-apostoli"),
    (P + "sancti-ioachim-confessoris-tractus", "thomas", "p. 441", "sancti-thomae-apostoli"),
]


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def core(text):
    return load("texts/" + text.replace(".", "/", 1) + ".json")


def layer(language, text):
    return load(f"languages/{language}/texts/" + text.replace(".", "/", 1) + ".json")


def words(doc):
    return {word["id"]: word for segment in doc["segments"] for word in segment.get("words", [])}


def witness(text, name="mr"):
    return (ROOT / "witnesses" / text / f"{name}.txt").read_text(encoding="utf-8")


def body(text, name="mr"):
    lines = witness(text, name).splitlines()
    return " ".join(line for line in lines if line and not line.startswith("#"))


def apparatus(text):
    return load(f"witnesses/{text}/apparatus.json")["adjudicated"]


def graph():
    return load("bibliography/graph.json")


def clean(text):
    directory = ROOT / "witnesses" / text
    assert collate(core(text), directory)[:2] == ([], [])
    assert transcription.check_transcriptions(directory)[0] == []


def test_the_gradual_prints_a_comma_after_tu():
    text = IC + "graduale"
    doc = core(text)
    assert words(doc)["w003"].get("post") == ","
    assert doc["title"].startswith("Benedícta es tu, Virgo María")
    assert body(text).startswith("Benedícta es tu, Virgo María,")
    assert "tu. Virgo" in body(text, "do")
    assert [e["witnesses"] for e in apparatus(text) if e["at"] == "w003"] == [{"do": "tu."}]
    clean(text)


def test_the_gospel_prints_gabriel_without_the_diaeresis():
    text = IC + "evangelium"
    doc = core(text)
    assert words(doc)["w007"]["form"] == "Gábriel"
    assert doc["title"].endswith("Ángelus Gábriel")
    assert "Angelus Gábriel a Deo" in body(text)
    assert "Gábriël" in body(text, "do")
    entries = [e for e in apparatus(text) if e["at"] == "w007"]
    assert [(e["witnesses"], e["class"]) for e in entries] == [({"do": "Gábriël"}, "accent")]
    clean(text)


def test_the_introit_declares_its_expanded_cues():
    text = IC + "introitus"
    assert "(℣. Glória Patri. Gaudens.)" in witness(text)
    collation = next(c for c in graph()["collations"] if c["text"] == text)
    assert collation["recension"].endswith("declared expansions of the printed cues")
    clean(text)


@pytest.mark.parametrize("text", ORATIONS)
def test_the_conclusions_are_declared_composites(text):
    header = witness(text)
    cue = "Per eúndem Dóminum" if text == IC + "collecta" else "Per Dóminum"
    assert f"through the cue words {cue};" in header and "p. 123" in header and "p. 226" in header
    assert body(text).endswith("Deus. Per ómnia sǽcula sæculórum. Amen.")
    uses = {use["id"]: use for use in graph()["uses"]}
    kinds = ["rg115a", "middle", "terminal"] + (["rg115b"] if text == IC + "collecta" else [])
    assert all(f"use.{text}.conclusion-{kind}.mr1962" in uses for kind in kinds)
    assert uses[f"use.{text}.mr1962"]["decision"] == "RETAIN_WITH_CORRECTION"
    record = next(w for w in graph()["witnesses"] if w["id"] == f"witness.{text}.mr1962")
    assert record["orthography_profile"] == "exact-declared-composite"
    seams = sorted(e["witnesses"]["mr"] for e in apparatus(text) if "mr" in e["witnesses"])
    assert seams == ["Deus.", "Per"]
    clean(text)


@pytest.mark.parametrize("text,mass,printed,formulary", PRINTINGS)
def test_the_masses_record_their_printings_of_shared_texts(text, mass, printed, formulary):
    use = next(u for u in graph()["uses"] if u["id"] == f"use.{text}.{mass}-reprint.mr1962")
    assert use["role"] == "direct_approved_print" and use["locator"]["printed"] == printed
    components = load(f"formularies/sanctorale/{formulary}.json")["components"]
    assert any(c["text"] == text and c["relation"] == "reference" for c in components)


def test_the_saint_thomas_printing_of_the_tract_names_its_semicolon():
    text = "proprium.sancti-ioachim-confessoris-tractus"
    use = next(u for u in graph()["uses"] if u["id"] == f"use.{text}.thomas-reprint.mr1962")
    assert "tribuísti ei; et" in use["claim"]
    ei = words(core(text))["w005"]
    assert (ei["form"], ei.get("post")) == ("ei", ":")


def test_the_ave_maria_offertory_is_protected():
    text = IC + "offertorium"
    for language in ("pl", "en"):
        assert translation_provenance.protected(text, language)
        sites = load(f"languages/{language}/translation-provenance.json")["sites"]
        site = next(s for s in sites if s["site"] == f"{text}.s01.{language}")
        assert site["familiar_core"] is True
    assert layer("en", text)["segments"]["s01"]["translation"] == (
        "Hail Mary, full of grace, the Lord is with thee, blessed art thou among women, alleluia."
    )
    assert layer("pl", text)["segments"]["s01"]["translation"] == (
        "Zdrowaś Maryjo, łaski pełna, Pan z Tobą, błogosławionaś Ty między niewiastami, alleluja."
    )


def test_the_tract_reads_eius_of_the_city():
    text = IC + "tractus"
    assert words(core(text))["w002"]["morph"]["gender"] == "f"
    assert layer("pl", text)["words"]["w002"]["gloss"] == "jego"
    groups = [a for s in layer("en", text)["segments"].values() for a in s.get("alignments", [])]
    assert {"words": ["w001", "w002"], "anchor": "w001", "gloss": "Her foundations"} in groups


@pytest.mark.parametrize(
    "text,words_,anchor,gloss",
    [
        (ST + "secreta", ["w022", "w023", "w024"], "w024", "to You sacrifices of praise"),
        (
            IC + "collecta",
            ["w036", "w037", "w038", "w039", "w040"],
            "w037",
            "this same Jesus Christ, our Lord",
        ),
    ],
)
def test_selected_english_line_groups(text, words_, anchor, gloss):
    groups = [a for s in layer("en", text)["segments"].values() for a in s.get("alignments", [])]
    assert {"words": words_, "anchor": anchor, "gloss": gloss} in groups
