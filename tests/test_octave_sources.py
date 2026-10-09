"""The Christmas octave as the approved Benziger printing has it.

Pages 26 and 28 end the St John Gradual's respond and the Innocents Tract's first verse with a
full stop before the next verse, where the Divinum Officium source has a comma. The Introits'
Gloria Patri and repeated antiphon are declared expansions of the printed cues. Every oration's
expanded conclusion is a declared composite: a *Qui tecum* cue takes the formula of Rubricae
generales 115 c, a *Per Dóminum* cue the edition's own full printings (p. 123, p. 226) under
115 a. The Octave Day Postcommunion prints *Per eúndem Dóminum* although it does not name the Son
at its beginning; 116 keeps such a conclusion, and the page controls. The octave pages print nine
referenced texts in full, two of them with their own punctuation. The English chants, readings
and orations revised from a historical wording name that basis, and the Divinum Officium
witnesses transcribe their pinned readings exactly, bound to the raw archives where the binding
contract can follow them.
"""

import json
from pathlib import Path

import pytest

from checks import transcription
from checks.collate import collate

ROOT = Path(__file__).resolve().parents[1]
ST = "proprium.sancti-stephani-protomartyris-"
IO = "proprium.sancti-ioannis-apostoli-et-evangelistae-"
IN = "proprium.sanctorum-innocentium-martyrum-"
DO = "proprium.dominica-infra-octavam-nativitatis-"
OC = "proprium.in-octava-nativitatis-"
INTROITS = [
    (ST + "introitus", "Sedérunt"),
    (IO + "introitus", "In médio"),
    (IN + "introitus", "Ex ore"),
    (DO + "introitus", "Dum"),
]
QUI_TECUM = [ST + "collecta", DO + "collecta", OC + "collecta"]
PER = [
    ST + "secreta",
    ST + "postcommunio",
    IO + "collecta",
    IO + "secreta",
    IO + "postcommunio",
    IN + "collecta",
    IN + "secreta",
    IN + "postcommunio",
    DO + "secreta",
    DO + "postcommunio",
    OC + "secreta",
    OC + "postcommunio",
]
REPRINTS = [
    ("proprium.sancti-ioachim-confessoris-tractus", "stephen-reprint", "p. 24", None),
    (
        "proprium.nativitas-sancti-ioannis-baptistae-offertorium",
        "john-evangelist-reprint",
        "p. 26",
        None,
    ),
    ("proprium.nativitas-domini-in-aurora-alleluia", "sunday-octave-reprint", "p. 22", None),
    ("proprium.nativitas-domini-in-aurora-offertorium", "sunday-octave-reprint", "p. 23", None),
    ("proprium.nativitas-domini-in-die-introitus", "octave-day-reprint", "p. 33", "novum: quia"),
    ("proprium.nativitas-domini-in-nocte-epistola", "octave-day-reprint", "p. 33", None),
    (
        "proprium.nativitas-domini-in-die-graduale",
        "octave-day-reprint",
        "p. 33",
        "nostri; iubiláte",
    ),
    ("proprium.nativitas-domini-in-die-offertorium", "octave-day-reprint", "p. 33", None),
    ("proprium.nativitas-domini-in-die-communio", "octave-day-reprint", "p. 34", None),
]
HISTORICAL = [
    (IO + "introitus", "husenbeth1853", "pp. 70–71"),
    (IN + "tractus", "husenbeth1853", "p. 74"),
    (DO + "introitus", "laity1846", "p. 123"),
    (ST + "collecta", "laity1846", "p. 116"),
    (IN + "collecta", "laity1846", "pp. 119–120"),
    (DO + "collecta", "husenbeth1853", "p. 77"),
    (DO + "epistola", "laity1846", "p. 124"),
    (DO + "evangelium", "laity1846", "pp. 124–125"),
    (DO + "secreta", "husenbeth1853", "p. 79"),
    (OC + "collecta", "laity1846", "p. 126"),
    (OC + "alleluia", "laity1846", "p. 126"),
]
EDITIONS = {
    "husenbeth1853": "edition.the-missal-for-the-use-of-the-laity-1853",
    "laity1846": "edition.the-missal-for-the-laity-1846",
}
BOUND = [
    ST + "evangelium",
    IO + "introitus",
    "proprium.nativitas-sancti-ioannis-baptistae-offertorium",
]
PENDING = [
    IN + "tractus",
    IO + "postcommunio",
    OC + "secreta",
    OC + "postcommunio",
    DO + "graduale",
]


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def core(text):
    return load("texts/" + text.replace(".", "/", 1) + ".json")


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


def record(text, name="mr1962"):
    return next(w for w in graph()["witnesses"] if w["id"] == f"witness.{text}.{name}")


def clean(text):
    directory = ROOT / "witnesses" / text
    assert collate(core(text), directory)[:2] == ([], [])
    assert transcription.check_transcriptions(directory)[0] == []


@pytest.mark.parametrize(
    "text,word,printed,do",
    [
        (IO + "graduale", "w015", "Non móritur. Sed:", "móritur,"),
        (IN + "tractus", "w008", "circúitu Ierúsalem. Et", "Jerúsalem,"),
    ],
)
def test_the_respond_ends_with_the_printed_full_stop_before_the_verse(text, word, printed, do):
    assert words(core(text))[word].get("post") == "."
    assert printed in bodies(text)[0]
    entries = [e for e in apparatus(text) if e["at"] == word]
    assert [e["witnesses"] for e in entries] == [{"do": do}]
    clean(text)


@pytest.mark.parametrize("text,cue", INTROITS)
def test_the_introits_declare_their_expanded_cues(text, cue):
    assert f"as cues only (℣. Glória Patri. {cue}.);" in witness(text)
    assert "# orthography: printed proper body with explicitly declared house-expanded" in witness(
        text
    )
    assert record(text)["orthography_profile"] == "page-body-with-declared-house-expansion"
    assert record(text)["source_dependencies"] == {
        "uses": [f"use.{text}.expanded-doxology.mr1962", f"use.{text}.introit-expansion.mr1962"],
        "raw_binding": None,
    }
    collation = next(c for c in graph()["collations"] if c["text"] == text)
    assert collation["recension"].endswith("declared expansions of the printed cues")
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
    commas = [e for e in apparatus(text) if e["witnesses"].get("do") in ("Sancti", "Deus")]
    assert len(commas) == 2 and all("RG115c" in e["ruling"] for e in commas)
    clean(text)


@pytest.mark.parametrize("text", PER)
def test_the_per_conclusions_are_declared_composites(text):
    header = witness(text)
    cue = "Per eúndem Dóminum" if text == OC + "postcommunio" else "Per Dóminum"
    assert f"through the cue words {cue};" in header
    assert "p. 123" in header and "p. 226" in header
    assert bodies(text)[0].endswith("Deus. Per ómnia sǽcula sæculórum. Amen.")
    rule = "rg116" if text == OC + "postcommunio" else "rg115a"
    found = {key for key in uses(text) if "conclusion-" in key}
    expected = {f"conclusion-{kind}.mr1962" for kind in ("middle", "terminal", "rg115a")}
    assert found == expected | {f"conclusion-{rule}.mr1962"}
    assert uses(text)["mr1962"]["decision"] == "RETAIN_WITH_CORRECTION"
    assert record(text)["orthography_profile"] == "exact-declared-composite"
    seams = sorted(
        e["witnesses"]["mr"]
        for e in apparatus(text)
        if e["witnesses"].get("mr") in ("Deus.", "Per")
    )
    assert seams == ["Deus.", "Per"]
    clean(text)


def test_the_octave_day_postcommunion_keeps_its_printed_per_eundem_under_rg116():
    text = OC + "postcommunio"
    header = witness(text)
    assert "RG 116 keeps the conclusion the book prints, Per eúndem Dóminum." in header
    assert "115 a–b" not in header
    use = uses(text)["conclusion-rg116.mr1962"]
    assert use["locator"]["printed"] == "p. xviii"
    assert "Page 34 prints Per eúndem Dóminum." in use["claim"]
    assert "names neither the Son nor His birth in its opening clause" in use["claim"]
    assert "Rubricae generales 115 a and 116" in core(text)["editorial"]["notes"]


@pytest.mark.parametrize("text", PER)
def test_the_composite_ranges_meet_at_the_printed_seams(text):
    line = next(x for x in witness(text).splitlines() if x.startswith("# composite: "))
    spans = [part.split(" from ")[0].strip() for part in line[len("# composite: ") :].split("; ")]
    ranges = [tuple(int(end[1:]) for end in span.split("–")) for span in spans]
    words_ = forms(core(text))
    assert [r[0] for r in ranges] == [1] + [r[1] + 1 for r in ranges[:-1]]
    assert ranges[-1][1] == len(words_) and len(ranges) == 3
    body, middle, terminal = ranges
    assert words_[body[1] - 1].rstrip(".") == "Dóminum"
    assert words_[middle[0] - 1] == "nostrum"
    assert words_[middle[1] - 1].startswith("Deus")
    assert words_[terminal[0] - 1] == "per"
    assert words_[terminal[1] - 1] == "Amen"


@pytest.mark.parametrize("text,key,printed,difference", REPRINTS)
def test_the_octave_pages_record_the_texts_they_print_in_full(text, key, printed, difference):
    use = uses(text)[f"{key}.mr1962"]
    assert use["role"] == "direct_approved_print"
    assert use["locator"]["printed"] == printed
    if difference is None:
        assert "identical in letters, accents and punctuation" in use["claim"]
    else:
        assert difference in use["claim"]


@pytest.mark.parametrize("text,source,printed", HISTORICAL)
def test_the_revised_english_names_its_historical_basis(text, source, printed):
    bibliography = load("languages/en/bibliography.json")
    use = next(u for u in bibliography["uses"] if u["id"] == f"use.en.{text}.body.{source}")
    assert use["role"] == "historical_wording_basis"
    assert use["edition"] == EDITIONS[source]
    assert use["locator"]["printed"] == printed
    assert use["address"] == {"kind": "segment", "text": text, "segment": "s01"}
    basis = load("languages/en/translation-basis.json")["records"]
    assert {"texts": [text], "segments": ["s01"], "relationship": "revised"} in basis
    sites = load("languages/en/translation-provenance.json")["sites"]
    assert next(s for s in sites if s["site"] == f"{text}.s01.en")["origin"] == "public-domain"


def test_the_st_john_postcommunion_conclusion_follows_its_page():
    bibliography = load("languages/en/bibliography.json")
    use = next(
        u
        for u in bibliography["uses"]
        if u["id"] == "use.en.saint-john-postcommunion.conclusion.husenbeth1853"
    )
    assert "God stands after the Holy Spirit, as on this page" in use["claim"]


@pytest.mark.parametrize("text", BOUND)
def test_the_bound_divinum_officium_witnesses_read_their_archives_exactly(text):
    header = witness(text, "do")
    binding = "do-" + text.replace(".", "-")
    assert f"# raw-binding: {binding}" in header
    assert record(text, "do44667ff")["source_dependencies"]["raw_binding"] == binding
    if text == ST + "evangelium":
        assert "# corrigendum: quóies -> quóties" in header
        assert "quóies vólui" in bodies(text, "do")[0]
    clean(text)


@pytest.mark.parametrize("text", PENDING)
def test_the_unbound_divinum_officium_witnesses_say_why(text):
    header = witness(text, "do")
    assert "# raw-binding:" not in header
    assert "the raw binding is pending because" in header
    assert (
        "# orthography: exact source spelling, accents, capitalization, and punctuation" in header
    )
    assert "this body has not been verified" not in header
    clean(text)


def test_the_polish_card_gives_natalitium_its_martyrs_sense():
    senses = load("languages/pl/lexicon.json")["entries"]["natalitium"]["senses"]
    assert senses == ["uroczystość narodzin", "narodziny dla nieba"]
    gloss = load("languages/pl/texts/proprium/sancti-stephani-protomartyris-collecta.json")
    assert gloss["words"]["w015"]["gloss"] == "narodziny dla nieba"


@pytest.mark.parametrize(
    "text,word",
    [
        (DO + "graduale", "w004"),
        (DO + "graduale", "w008"),
        (DO + "secreta", "w016"),
        (DO + "postcommunio", "w007"),
        (OC + "collecta", "w010"),
        (OC + "collecta", "w011"),
    ],
)
def test_a_printed_lower_case_accent_is_ruled_as_an_accent(text, word):
    entry = next(e for e in apparatus(text) if e["at"] == word)
    assert entry["class"] == "accent"
    assert entry["ruling"].startswith("The selected accentuation follows the approved Benziger")


def test_the_sunday_gospel_writes_mother_in_lower_case_as_the_missal_prints_it():
    data = load(f"languages/en/texts/{DO.replace('.', '/', 1)}evangelium.json")
    assert data["words"]["w008"]["gloss"] == "the mother"
    group = {"words": ["w025", "w026"], "anchor": "w025", "gloss": "His mother"}
    assert group in data["segments"]["s01"]["alignments"]
    verse = data["segments"]["s01"]["translation"]
    assert "Mary, the mother of Jesus" in verse and "Mary His mother" in verse
