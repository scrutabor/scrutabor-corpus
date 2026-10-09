"""The four Christmas Masses as the approved Benziger printing has them.

Page 15 prints the Vigil Gradual's *Ephraïm* with the diaeresis on the i; the house orthography
writes the diaeresis on e only and restores the capital's accent, so the reading text keeps
*Éphraim* and the Missal witness records the page exactly. The Vigil Alleluia's rubric stands
after its verse in the page's own words, and the Dawn Gospel prints *festinántes:*. The
commemoration of St Anastasia is announced once, as page 19 prints it, and its Secret and
Postcommunion carry the printed labels. The Introits' Gloria Patri and repeated antiphon are
declared expansions of the printed cues. Every oration's expanded conclusion is a declared
composite: a *Qui tecum* cue takes the formula of Rubricae generales 115 c, a *Per Dóminum* or
*Per eúndem Dóminum* cue the edition's own full printings (p. 123, p. 226) under 115 a, with
115 b for *Per eúndem*. The English chants and readings revised from a historical wording name
that basis, The Missal for the Laity (1846).
"""

import json
from pathlib import Path

import pytest

from checks import transcription
from checks.collate import collate

ROOT = Path(__file__).resolve().parents[1]
V = "proprium.vigilia-nativitatis-"
N = "proprium.nativitas-domini-in-nocte-"
A = "proprium.nativitas-domini-in-aurora-"
D = "proprium.nativitas-domini-in-die-"
QUI_TECUM = [
    (V + "collecta", "Qui tecum."),
    (V + "secreta", "Qui tecum."),
    (N + "collecta", "Qui tecum."),
    (N + "secreta", "Qui tecum."),
    (N + "postcommunio", "Qui tecum vivit et regnat."),
    (D + "postcommunio", "Qui tecum."),
]
PER_EUNDEM = [V + "postcommunio", D + "collecta", D + "secreta"]
ANASTASIA = [A + "collecta", A + "secreta", A + "postcommunio"]
INTROITS = [(V + "introitus", "Hódie"), (N + "introitus", "Dóminus"), (A + "introitus", "Lux")]
LAITY_1846 = [
    V + "introitus",
    V + "graduale",
    V + "evangelium",
    V + "offertorium",
    N + "introitus",
    N + "epistola",
    N + "graduale",
    N + "alleluia",
    N + "evangelium",
    N + "offertorium",
    N + "communio",
    A + "introitus",
    A + "epistola",
    A + "graduale",
    A + "alleluia",
    A + "evangelium",
    A + "offertorium",
    D + "introitus",
    D + "graduale",
    D + "offertorium",
    D + "secreta",
]


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def core(text):
    return load("texts/" + text.replace(".", "/", 1) + ".json")


def layer(language, text):
    return load(f"languages/{language}/texts/" + text.replace(".", "/", 1) + ".json")


def words(doc):
    return {word["id"]: word for segment in doc["segments"] for word in segment.get("words", [])}


def forms(doc):
    return [word["form"] for segment in doc["segments"] for word in segment.get("words", [])]


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


def test_the_vigil_gradual_records_the_printed_diaeresis_on_the_i():
    text = V + "graduale"
    word = words(core(text))["w029"]
    assert (word["form"], word.get("post")) == ("Éphraim", ",")
    assert "appáre coram Ephraïm, Béniamin" in " ".join(bodies(text))
    assert "Ephraim," in " ".join(bodies(text, "do"))
    entries = sorted(
        (sorted(e["witnesses"].items()), e["class"]) for e in apparatus(text) if e["at"] == "w029"
    )
    assert entries == [
        ([("do", "Ephraim,")], "capital-accent"),
        ([("mr", "Ephraïm,")], "capital-accent"),
    ]
    clean(text)


def test_the_vigil_alleluia_prints_its_rubric_after_the_verse():
    text = V + "alleluia"
    segments = core(text)["segments"]
    assert [s["id"] for s in segments] == ["s02", "s01"]
    assert segments[1]["type"] == "rubric"
    assert segments[1]["text"] == (
        "Non dicitur Allelúia cum sequenti versu, nisi hæc vigilia venerit in dominica."
    )
    for language in ("pl", "en"):
        assert list(layer(language, text)["segments"]) == ["s02", "s01"]
    clean(text)


def test_the_dawn_gospel_prints_a_colon_after_festinantes():
    text = A + "evangelium"
    word = words(core(text))["w024"]
    assert (word["form"], word.get("post")) == ("festinántes", ":")
    assert "Et venérunt festinántes: et invenérunt" in " ".join(bodies(text))
    entries = [(e["witnesses"], e["class"]) for e in apparatus(text) if e["at"] == "w024"]
    assert entries == [({"do": "festinántes,"}, "punctuation")]
    clean(text)


def test_the_commemoration_of_st_anastasia_is_announced_as_printed():
    rubrics = {
        text: [s["text"] for s in core(text)["segments"] if s["type"] == "rubric"]
        for text in ANASTASIA
    }
    assert rubrics == {
        A + "collecta": ["Et fit Commemoratio S. Anastasiæ Martyris, etiam in Missis in cantu."],
        A + "secreta": ["Pro S. Anastasia."],
        A + "postcommunio": ["Pro S. Anastasia."],
    }
    header = witness(A + "postcommunio", "do")
    assert "@Commune/C6b:Postcommunio" in header
    assert "Commune/C6a.txt [Postcommunio], line 89" in header


@pytest.mark.parametrize("text,cue", INTROITS)
def test_the_introits_declare_their_expanded_cues(text, cue):
    assert f"as cues only (℣. Glória Patri. {cue}.);" in witness(text)
    assert "explicitly declared house-expanded formula" in witness(text)
    assert record(text)["orthography_profile"] == "page-body-with-declared-house-expansion"
    assert record(text)["source_dependencies"] == {
        "uses": [f"use.{text}.expanded-doxology.mr1962", f"use.{text}.introit-expansion.mr1962"],
        "raw_binding": None,
    }
    collation = next(c for c in graph()["collations"] if c["text"] == text)
    assert collation["recension"].endswith("declared expansions of the printed cues")
    assert {"expanded-doxology.mr1962", "introit-expansion.mr1962"} <= set(uses(text))
    clean(text)


@pytest.mark.parametrize("text,cue", QUI_TECUM)
def test_the_qui_tecum_conclusions_take_the_rg115c_formula(text, cue):
    assert f"# assembly: printed proper ends {cue} Its abbreviation is replaced" in witness(text)
    assert bodies(text)[-1].endswith(
        "Qui tecum vivit et regnat in unitate Spiritus Sancti, Deus, per omnia sæcula sæculorum. "
        "Amen;"
    )
    assert uses(text)["conclusion-rg115c.mr1962"]["role"] == "official_text"
    assert record(text)["orthography_profile"] == "exact-multi-locus-transcription"
    clean(text)


@pytest.mark.parametrize("text", PER_EUNDEM + ANASTASIA)
def test_the_per_conclusions_are_declared_composites(text):
    header = witness(text)
    two = text in ANASTASIA
    assert "through the cue words Per eúndem Dóminum;" in header
    assert ("through the cue words Per Dóminum;" in header) is two
    assert "p. 123" in header and "p. 226" in header
    texts = bodies(text)
    assert len(texts) == (2 if two else 1)
    assert all(b.endswith("Deus. Per ómnia sǽcula sæculórum. Amen.") for b in texts)
    found = uses(text)
    kinds = ["middle", "rg115a", "terminal"]
    expected = {f"conclusion-{kind}.mr1962" for kind in [*kinds, "rg115b"]}
    if two:
        expected |= {f"commemoration-conclusion-{kind}.mr1962" for kind in kinds}
    if text in (A + "secreta", A + "postcommunio"):
        expected.add("conclusion-rg116.mr1962")
    assert {key for key in found if "conclusion-" in key} == expected
    assert found["mr1962"]["decision"] == "RETAIN_WITH_CORRECTION"
    assert record(text)["orthography_profile"] == "exact-declared-composite"
    seams = sorted(
        e["witnesses"]["mr"]
        for e in apparatus(text)
        if e["witnesses"].get("mr") in ("Deus.", "Per")
    )
    assert seams == (["Deus.", "Deus.", "Per", "Per"] if two else ["Deus.", "Per"])
    clean(text)


@pytest.mark.parametrize("text", PER_EUNDEM + ANASTASIA)
def test_the_composite_ranges_meet_at_the_printed_seams(text):
    line = next(x for x in witness(text).splitlines() if x.startswith("# composite: "))
    spans = [part.split(" from ")[0].strip() for part in line[len("# composite: ") :].split("; ")]
    ranges = [tuple(int(end[1:]) for end in span.split("–")) for span in spans]
    words_ = forms(core(text))
    assert [r[0] for r in ranges] == [1] + [r[1] + 1 for r in ranges[:-1]]
    assert ranges[-1][1] == len(words_)
    assert len(ranges) % 3 == 0
    for body, middle, terminal in zip(ranges[::3], ranges[1::3], ranges[2::3], strict=True):
        assert words_[body[1] - 1].rstrip(".") == "Dóminum"
        assert words_[middle[0] - 1] == "nostrum"
        assert words_[middle[1] - 1].startswith("Deus")
        assert words_[terminal[0] - 1] == "per"
        assert words_[terminal[1] - 1] == "Amen"


@pytest.mark.parametrize("text", LAITY_1846)
def test_the_revised_english_names_its_historical_basis(text):
    bibliography = load("languages/en/bibliography.json")
    use = next(u for u in bibliography["uses"] if u["id"] == f"use.en.{text}.body.laity1846")
    assert use["role"] == "historical_wording_basis"
    assert use["edition"] == "edition.the-missal-for-the-laity-1846"
    assert use["address"] == {"kind": "segment", "text": text, "segment": "s01"}
    basis = load("languages/en/translation-basis.json")["records"]
    assert {"texts": [text], "segments": ["s01"], "relationship": "revised"} in basis
    sites = load("languages/en/translation-provenance.json")["sites"]
    assert next(s for s in sites if s["site"] == f"{text}.s01.en")["origin"] == "public-domain"


@pytest.mark.parametrize("text", [A + "secreta", A + "postcommunio"])
def test_the_dawn_per_eundem_cues_name_rg116_beside_rg115b(text):
    found = uses(text)
    assert {"conclusion-rg115b.mr1962", "conclusion-rg116.mr1962"} <= set(found)
    use = found["conclusion-rg116.mr1962"]
    assert use["locator"]["printed"] == "p. xviii"
    assert use["evidence_sha256"] == found["conclusion-rg115b.mr1962"]["evidence_sha256"]
    assert "page 20 prints Per eúndem Dóminum., and the printed cue controls" in use["claim"]
