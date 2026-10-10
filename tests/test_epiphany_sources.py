"""The Epiphany, the Holy Family, the Mass of the First Sunday after the Epiphany and the Baptism
as the approved Benziger printing has them.

Page 37 prints the Epiphany Introit's *Ecce advénit* without a comma (so does page 42). Page 40
prints the Holy Family Secret's *supplíciter deprecántes: ut*; the word takes the text's next
free id. Page 39 prints the Holy Family's own Epistle, 108 words ending *per ipsum*, distinct
from the Fifth Sunday's page-415 printing. The Sunday Introit's repetition ends with the
antiphon's stop, and page 42 prints the Communion's *quærebamus* without its accent. The
Introits' Gloria Patri and repeated antiphon are declared expansions of the printed cues. Every
oration's expanded conclusion is a declared composite: *Qui tecum* takes Rubricae generales
115 c, *Qui vivis* 115 d, *Per Dóminum* and *Per eúndem Dóminum* the edition's own full
printings (p. 123, p. 226) under 115 a, with 115 b for the Epiphany Collect and 116 for the Holy
Family Secret. The pages that print shared texts again are recorded with their differences, and
the English revised from a historical wording names its basis.
"""

import json
from pathlib import Path

import pytest

from checks import transcription
from checks.collate import collate
from checks.raw_binding import resolve_binding

ROOT = Path(__file__).resolve().parents[1]
E = "proprium.epiphania-domini-"
F = "proprium.sancta-familia-"
D = "proprium.dominica-i-post-epiphaniam-"
B = "proprium.commemoratio-baptismatis-domini-"
II = "proprium.dominica-ii-post-epiphaniam-"
EPISTLE = "proprium.sancta-familia-epistola"
FIFTH = "proprium.dominica-v-post-epiphaniam-epistola"
INTROITS = [
    (E + "introitus", "Ecce"),
    (F + "introitus", "Exsúltat"),
    (D + "introitus", "In excélso"),
]
QUI_TECUM = [E + "secreta", B + "collecta", B + "secreta"]
QUI_VIVIS = [F + "collecta", F + "postcommunio"]
PER = {
    E + "collecta": "rg115b",
    E + "postcommunio": None,
    F + "secreta": "rg116",
    D + "collecta": None,
    D + "secreta": None,
    D + "postcommunio": None,
    B + "postcommunio": None,
    II + "secreta": None,
    II + "postcommunio": None,
}
SAME = ("identical in letters, accents and punctuation",)
REPRINTS = [
    (
        F + "evangelium",
        "epiphany-i-reprint",
        "p. 41",
        ("cognátos", "illos", "tuus", "(in his, quæ)", "ecce", "nesciebátis"),
    ),
    (E + "introitus", "baptism-reprint", "p. 42", ("Malach. for Malach", "I Par. for 1 Par.")),
    (E + "epistola", "baptism-reprint", "pp. 42–43", ("illumináre", "tuos")),
    (E + "graduale", "baptism-reprint", "p. 43", SAME),
    (E + "alleluia", "baptism-reprint", "p. 43", SAME),
    (E + "offertorium", "baptism-reprint", "p. 43", ("Arabum",)),
    (E + "communio", "baptism-reprint", "p. 43", ("Oríente",)),
]
BASES = {
    E + "epistola": "husenbeth1853",
    E + "graduale": "husenbeth1853",
    E + "alleluia": "husenbeth1853",
    E + "evangelium": "husenbeth1853",
    E + "offertorium": "laity1846",
    E + "communio": "husenbeth1853",
    F + "introitus": "douay1914",
    F + "graduale": "douay1914",
    F + "alleluia": "douay1914",
    F + "evangelium": "laity1846",
    D + "introitus": "husenbeth1853",
    D + "epistola": "laity1846",
    D + "alleluia": "laity1846",
    D + "offertorium": "laity1846",
}
EDITIONS = {
    "husenbeth1853": "edition.the-missal-for-the-use-of-the-laity-1853",
    "laity1846": "edition.the-missal-for-the-laity-1846",
    "douay1914": "edition.douay-rheims-bible-challoner",
}


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def core(text):
    return load("texts/" + text.replace(".", "/", 1) + ".json")


def layer(language, text):
    return load(f"languages/{language}/texts/" + text.replace(".", "/", 1) + ".json")


def ordered(doc):
    return [word for segment in doc["segments"] for word in segment.get("words", [])]


def words(doc):
    return {word["id"]: word for word in ordered(doc)}


def witness(text, name="mr"):
    return (ROOT / "witnesses" / text / f"{name}.txt").read_text(encoding="utf-8")


def bodies(text, name="mr"):
    return [line for line in witness(text, name).splitlines() if line and not line.startswith("#")]


def apparatus(text):
    return load(f"witnesses/{text}/apparatus.json")["adjudicated"]


def graph():
    return load("bibliography/graph.json")


def uses(text):
    prefix = f"use.{text}."
    return {
        use["id"][len(prefix) :]: use for use in graph()["uses"] if use["id"].startswith(prefix)
    }


def record(text):
    return next(w for w in graph()["witnesses"] if w["id"] == f"witness.{text}.mr1962")


def clean(text):
    directory = ROOT / "witnesses" / text
    assert collate(core(text), directory)[:2] == ([], [])
    assert transcription.check_transcriptions(directory)[0] == []


def test_the_epiphany_introit_prints_ecce_without_a_comma():
    text = E + "introitus"
    found = words(core(text))
    assert [(found[w]["form"], found[w].get("post")) for w in ("w001", "w044")] == [
        ("Ecce", None),
        ("Ecce", None),
    ]
    body = " ".join(bodies(text))
    assert body.count("Ecce advénit") == 2 and "Ecce," not in body
    assert core(text)["title"] == "Ecce advénit dominátor Dóminus: et regnum in"
    entries = [
        (e["at"], e["witnesses"], e["class"]) for e in apparatus(text) if e["ours"] == "Ecce"
    ]
    assert entries == [
        ("w001", {"do": "Ecce,"}, "punctuation"),
        ("w044", {"do": "Ecce,"}, "punctuation"),
    ]
    clean(text)


def test_the_holy_family_secret_has_the_printed_deprecantes():
    text = F + "secreta"
    doc = core(text)
    sequence = [word["form"] for word in ordered(doc)]
    at = sequence.index("supplíciter")
    assert sequence[at + 1 : at + 3] == ["deprecántes", "ut"]
    word = words(doc)["w047"]
    assert (word["form"], word["post"], word["lemma"], word["head"]) == (
        "deprecántes",
        ":",
        "deprecor",
        "w003",
    )
    assert doc["ids"]["next"] == 48
    assert doc["title"].endswith("Dómine, supplíciter deprecántes")
    assert "except the participle deprecántes" in uses(text)["do44667ff"]["claim"]
    assert layer("pl", text)["words"]["w047"]["gloss"] == "prosząc"
    assert layer("en", text)["words"]["w047"]["gloss"] == "beseeching"
    assert "pokornie prosząc, abyś" in layer("pl", text)["segments"]["s01"]["translation"]
    assert "supplíciter deprecántes: ut, per" in bodies(text)[0]
    entry = next(e for e in apparatus(text) if e["at"] == "w047")
    assert (entry["witnesses"], entry["class"]) == ({"do": ""}, "omission")
    clean(text)


def test_the_sunday_introit_repeats_the_antiphon_with_its_stop():
    text = D + "introitus"
    assert words(core(text))["w068"].get("post") == "."
    assert bodies(text)[0].endswith("ecce cuius impérii nomen est in ætérnum.")
    entry = next(e for e in apparatus(text) if e["at"] == "w068")
    assert (entry["witnesses"], entry["class"]) == ({"do": "ætérnum"}, "punctuation")
    clean(text)


def test_the_sunday_communion_records_the_unaccented_misprint():
    text = D + "communio"
    assert words(core(text))["w011"]["form"] == "quærebámus"
    assert "doléntes quærebamus te." in bodies(text)[0]
    entry = next(e for e in apparatus(text) if e["at"] == "w011" and "mr" in e["witnesses"])
    assert (entry["witnesses"], entry["class"]) == ({"mr": "quærebamus"}, "accent")
    clean(text)


def test_the_holy_family_reads_its_own_epistle():
    formulary = load("formularies/temporale/sancta-familia.json")
    epistle = next(c for c in formulary["components"] if c["key"] == "epistola")
    assert epistle == {"key": "epistola", "role": "epistola", "text": EPISTLE, "relation": "proper"}
    sequence = [(w["form"], w.get("post")) for w in ordered(core(EPISTLE))]
    assert len(sequence) == 108 and sequence[-2:] == [("per", None), ("ipsum", ".")]
    assert sequence[74] == ("vosmetípsos", ",") and sequence[76] == ("hymnis", None)
    assert len(ordered(core(FIFTH))) == 111
    assert layer("pl", EPISTLE)["segments"]["s01"]["translation"].endswith("przez Niego.")
    assert layer("en", EPISTLE)["segments"]["s01"]["translation"].endswith("through Him.")
    bound = resolve_binding(ROOT / "witnesses" / EPISTLE / "do.txt", ROOT)
    assert bound is not None and bound.text.endswith("per ipsum.")
    assert len(bound.text.split()) == 108
    assert uses(EPISTLE)["do44667ff"]["decision_reason"].startswith("Exact pinned original")
    clean(EPISTLE)


@pytest.mark.parametrize("text,cue", INTROITS)
def test_the_introits_declare_their_expanded_cues(text, cue):
    assert f"as cues only (℣. Glória Patri. {cue}.);" in witness(text)
    found = record(text)
    assert found["orthography_profile"] == "page-body-with-declared-house-expansion"
    assert found["source_dependencies"]["uses"] == [
        f"use.{text}.expanded-doxology.mr1962",
        f"use.{text}.introit-expansion.mr1962",
    ]
    assert {"expanded-doxology.mr1962", "introit-expansion.mr1962"} <= set(uses(text))
    clean(text)


@pytest.mark.parametrize("text", QUI_TECUM)
def test_the_qui_tecum_conclusions_take_the_rg115c_formula(text):
    assert "# assembly: printed proper ends Qui tecum. Its abbreviation is replaced" in witness(
        text
    )
    assert bodies(text)[-1].endswith(
        "Qui tecum vivit et regnat in unitate Spiritus Sancti, Deus, per omnia sæcula sæculorum. "
        "Amen;"
    )
    assert uses(text)["conclusion-rg115c.mr1962"]["role"] == "official_text"
    assert record(text)["orthography_profile"] == "exact-multi-locus-transcription"
    clean(text)


@pytest.mark.parametrize("text", QUI_VIVIS)
def test_the_qui_vivis_conclusions_take_the_rg115d_formula(text):
    assert "# assembly: printed proper ends Qui vivis. Its abbreviation is replaced" in witness(
        text
    )
    assert bodies(text)[-1].endswith(
        "Qui vivis et regnas cum Deo Patre in unitate Spiritus Sancti, Deus, per omnia sæcula "
        "sæculorum. Amen;"
    )
    assert uses(text)["conclusion-rg115d.mr1962"]["locator"]["section"] == (
        "RG115d full Qui vivis conclusion"
    )
    assert record(text)["orthography_profile"] == "exact-multi-locus-transcription"
    clean(text)


@pytest.mark.parametrize("text", sorted(PER))
def test_the_per_conclusions_are_declared_composites(text):
    found = uses(text)
    expected = {f"conclusion-{kind}.mr1962" for kind in ("middle", "rg115a", "terminal")}
    if PER[text]:
        expected.add(f"conclusion-{PER[text]}.mr1962")
    assert {key for key in found if "conclusion-" in key} == expected
    if PER[text] == "rg116":
        claim = found["conclusion-rg116.mr1962"]["claim"]
        assert "does not name the Son in its opening clause" in claim
    assert found["mr1962"]["decision"] == "RETAIN_WITH_CORRECTION"
    assert record(text)["orthography_profile"] == "exact-declared-composite"
    assert bodies(text)[-1].endswith("Deus. Per ómnia sǽcula sæculórum. Amen.")
    clean(text)


@pytest.mark.parametrize("text", sorted(PER))
def test_the_composite_ranges_meet_at_the_printed_seams(text):
    line = next(x for x in witness(text).splitlines() if x.startswith("# composite: "))
    spans = [part.split(" from ")[0].strip() for part in line[len("# composite: ") :].split("; ")]
    sequence = ordered(core(text))
    position = {word["id"]: k for k, word in enumerate(sequence)}
    ranges = [tuple(position[end] for end in span.split("–")) for span in spans]
    assert [r[0] for r in ranges] == [0] + [r[1] + 1 for r in ranges[:-1]]
    assert ranges[-1][1] == len(sequence) - 1
    body, middle, terminal = ranges
    assert sequence[body[1]]["form"] == "Dóminum"
    assert sequence[middle[0]]["form"] == "nostrum"
    assert sequence[middle[1]]["form"] == "Deus"
    assert sequence[terminal[0]]["form"] == "per"
    assert sequence[terminal[1]]["form"] == "Amen"


@pytest.mark.parametrize("text,key,printed,named", REPRINTS)
def test_the_reprints_are_recorded_with_their_differences(text, key, printed, named):
    use = uses(text)[f"{key}.mr1962"]
    assert (use["role"], use["locator"]["printed"]) == ("direct_approved_print", printed)
    assert all(word in use["claim"] for word in named)


@pytest.mark.parametrize("text", sorted(BASES))
def test_the_revised_english_names_its_historical_basis(text):
    source = BASES[text]
    bibliography = load("languages/en/bibliography.json")
    use = next(u for u in bibliography["uses"] if u["id"] == f"use.en.{text}.body.{source}")
    assert (use["role"], use["edition"]) == ("historical_wording_basis", EDITIONS[source])
    head, _, changes = use["claim"].partition(": ")
    assert "revised" in head and changes
    assert use["address"] == {"kind": "segment", "text": text, "segment": "s01"}
    basis = load("languages/en/translation-basis.json")["records"]
    assert {"texts": [text], "segments": ["s01"], "relationship": "revised"} in basis
    sites = load("languages/en/translation-provenance.json")["sites"]
    assert next(s for s in sites if s["site"] == f"{text}.s01.en")["origin"] == "public-domain"


def test_the_basis_claims_list_only_revisions():
    found = {u["id"]: u["claim"] for u in load("languages/en/bibliography.json")["uses"]}
    assert "for ye" not in found[f"use.en.{D}epistola.body.laity1846"]
    assert "and ye" not in found[f"use.en.{E}evangelium.body.husenbeth1853"]
    introit = found[f"use.en.{D}introitus.body.husenbeth1853"]
    assert "Sing joyfully" not in introit and "the psalm verse's punctuation" in introit


@pytest.mark.parametrize(
    "slug,body,deus,terminal,control,leaf",
    [
        ("secreta", 10, "w027", "w028", "secret-delivery", 59),
        ("postcommunio", 19, "w036", "w037", "postcommunion-mode", 38),
    ],
)
def test_the_second_sunday_conclusions_name_only_their_actual_printed_sources(
    slug, body, deus, terminal, control, leaf
):
    text = II + slug
    found = uses(text)
    assert found["mr1962"]["role"] == "direct_approved_print"
    assert found["mr1962"]["locator"]["printed"] == "p. 45"
    assert f"{body}-word proper body" in found["mr1962"]["claim"]
    expected = {
        "conclusion-rg115a": (
            22,
            "b511f3aa4016b387d2995b5089e15aa62593c04118052ef48dcc09352fcf769c",
        ),
        "conclusion-middle": (
            202,
            "38c3d082c3cf4e7f82f87cf9f87595e62e3765cb625c1305005f1435cc985774",
        ),
        "conclusion-terminal": (
            305,
            "c8a123467dd47ace390100a021fdcdd61752a5c42635583b92d72cd636027f58",
        ),
        "oration-boundaries": (
            39,
            "c03be5250068f8c9c262983bc7689a18d0180b88b0c4476d21fac383c8f07993",
        ),
        control: (
            leaf,
            {
                59: "006ff7776f1693072a9dc6895e6ca7f538b131a3733b7ed0603cf22c34811558",
                38: "a6d9b2554ebb911a8a6ae9ea6e6e5e882307bedeab8e326ae2f7ef602ec2fd7e",
            }[leaf],
        ),
    }
    assert record(text)["source_dependencies"] == {
        "uses": sorted(f"use.{text}.{key}.mr1962" for key in expected),
        "raw_binding": None,
    }
    for key, (n, digest) in expected.items():
        use = found[key + ".mr1962"]
        assert use["locator"]["scan"] == f"leaf n{n} / PDF p. {n + 1}"
        assert use["evidence_sha256"] == digest
    seams = [
        (a["at"], a["ours"], a["witnesses"], a["class"])
        for a in apparatus(text)
        if "mr" in a["witnesses"]
    ]
    assert seams == [
        (deus, "Deus,", {"mr": "Deus."}, "punctuation"),
        (terminal, "per", {"mr": "Per"}, "capitalization"),
    ]
    assert len(apparatus(text)) == 7
    assert record(text)["review"] == {"status": "pending"}
    if slug == "postcommunio":
        assert "direct speaker citation remains pending" in found[control + ".mr1962"]["claim"]
    bound = resolve_binding(ROOT / "witnesses" / text / "do.txt", ROOT)
    assert bound is not None and bound.text.endswith("Amen.")
    clean(text)
