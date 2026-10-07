"""Protect Saint Andrew's exact digital readings, page loci, shared texts and conclusions."""

import json
from pathlib import Path

import pytest

from checks import raw_binding, transcription
from checks.collate import collate

ROOT = Path(__file__).resolve().parents[1]
ANDREW = "proprium.sancti-andreae-apostoli-"
INTROIT = "proprium.sancti-iacobi-apostoli-introitus"
GRADUAL = "proprium.sancti-bartholomaei-apostoli-graduale"
OFFERTORY = "proprium.sancti-bartholomaei-apostoli-offertorium"
# text -> (binding, exact digital spellings kept, apparatus entries)
BOUND = {
    ANDREW + "collecta": ("saint-andrew-collect", ["Majestátem", "Jesum", "Christum,", "qui"], 7),
    ANDREW + "alleluia": ("saint-andrew-alleluia", ["Allelúja,", "allelúja.", "Allelúja."], 3),
    ANDREW + "secreta": (
        "saint-andrew-secret",
        ["Sacrificium", "cujus", "sollémniter", "ejus", "Jesum"],
        10,
    ),
    ANDREW + "postcommunio": ("saint-andrew-postcommunion", ["Jesum", "Christum,", "qui"], 7),
    INTROIT: ("saint-james-introit", ["Glória", "Patri,"], 2),
    GRADUAL: ("saint-bartholomew-gradual", ["patribus"], 1),
    OFFERTORY: ("saint-bartholomew-offertory", ["Mihi"], 0),
}


def load(path):
    return json.loads((ROOT / path).read_bytes())


def core(text):
    return load("texts/" + text.replace(".", "/", 1) + ".json")


def layer(language, text):
    return load(f"languages/{language}/texts/" + text.replace(".", "/", 1) + ".json")


def graph():
    return load("bibliography/graph.json")


@pytest.mark.parametrize("text", sorted(BOUND))
def test_digital_witness_is_the_exact_bound_reading(text):
    binding, spellings, entries = BOUND[text]
    directory = ROOT / "witnesses" / text
    bound = raw_binding.resolve_binding(directory / "do.txt", ROOT)
    assert bound is not None and bound.source["binding_id"] == binding
    tokens = bound.text.split()
    assert all(spelling in tokens for spelling in spellings)
    assert transcription.check_transcriptions(directory)[0] == []
    assert collate(core(text), directory)[:2] == ([], [])
    apparatus = load(f"witnesses/{text}/apparatus.json")
    assert apparatus["summary"]["entries"] == len(apparatus["adjudicated"]) == entries
    witness = next(w for w in graph()["witnesses"] if w["id"] == f"witness.{text}.do44667ff")
    assert witness["source_dependencies"]["raw_binding"] == binding
    assert "typical edition" not in json.dumps(apparatus)


@pytest.mark.parametrize(
    "text,page,leaf",
    [(ANDREW + "alleluia", "p. 426", "n507"), (OFFERTORY, "p. 650", "n731")],
)
def test_corrected_page_loci(text, page, leaf):
    use = next(u for u in graph()["uses"] if u["id"] == f"use.{text}.mr1962")
    assert use["locator"]["printed"] == page and use["locator"]["scan"].startswith(f"leaf {leaf} ")
    assert use["decision"] == "RETAIN_WITH_CORRECTION"
    header = (ROOT / "witnesses" / text / "mr.txt").read_text()
    assert f"# location: printed {page}; leaf {leaf} " in header


@pytest.mark.parametrize("text", [INTROIT, GRADUAL, OFFERTORY])
def test_shared_texts_record_saint_andrews_printing(text):
    use = next(u for u in graph()["uses"] if u["id"] == f"use.{text}.andrew-reprint.mr1962")
    assert use["role"] == "direct_approved_print"
    assert use["locator"]["printed"] == "p. 426" and use["locator"]["scan"].startswith("leaf n507 ")
    formulary = load("formularies/sanctorale/sancti-andreae-apostoli.json")
    assert any(c["text"] == text and c["relation"] == "reference" for c in formulary["components"])


@pytest.mark.parametrize("part", ["collecta", "secreta", "postcommunio"])
def test_conclusion_is_a_declared_composite(part):
    text = ANDREW + part
    header = (ROOT / "witnesses" / text / "mr.txt").read_text()
    assert "# composite: " in header and "p. 123" in header and "p. 226" in header
    assert "Deus. Per ómnia sǽcula sæculórum. Amen." in header
    ids = {u["id"] for u in graph()["uses"]}
    for kind in (
        "conclusion-macro.do44667ff",
        "conclusion-rg115a.mr1962",
        "conclusion-middle.mr1962",
        "conclusion-terminal.mr1962",
    ):
        assert f"use.{text}.{kind}" in ids
    groups = [
        a["gloss"] for s in layer("en", text)["segments"].values() for a in s.get("alignments", [])
    ]
    assert {
        "our Lord",
        "Jesus Christ",
        "Your Son",
        "who lives and reigns with You",
        "of the Holy Spirit",
        "forever and ever",
    } <= set(groups)


def test_the_same_latin_reads_the_same_in_gospel_and_communion():
    for language, phrase in (("pl", "że staniecie się"), ("en", "I will make you fishers of men")):
        gospel = layer(language, ANDREW + "evangelium")
        communion = layer(language, ANDREW + "communio")
        if language == "pl":
            for data, words in ((gospel, ["w035", "w036"]), (communion, ["w005", "w006"])):
                alignments = data["segments"]["s01"]["alignments"]
                assert {"words": words, "anchor": words[1], "gloss": phrase} in alignments
        else:
            assert phrase in gospel["segments"]["s01"]["translation"]
            assert phrase in communion["segments"]["s01"]["translation"]
