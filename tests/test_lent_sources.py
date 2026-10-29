"""The four Sundays of Lent as the approved Benziger printing has them, with the English that
names its historical basis and the interlinear lines that read in English and Polish order.

Page 64 prints the First Sunday's Collect *famíliæ tuæ: ut* and its Gospel *vivit homo: sed*,
with colons; its Tract *ex-/audiam* drops the acute after the line break, and page 65 prints
the Postcommunion's slip *Tuis nos*. Page 93 prints the present *ínvenit* in the Third Sunday's
Gospel, and page 106 the slip *Scríptum* in the Fourth Sunday's Epistle. The Introits' Gloria
Patri and repeated antiphon are declared expansions of the printed cues, and every *Per
Dóminum* conclusion is a declared composite of the proper page, page 123 and page 226 under
Rubricae generales 115 a. The referenced texts the Lent Masses print again in full are
recorded there. The English revised from *The Missal for the Laity* (1846) names its basis.
"""

import json
import re
from pathlib import Path

import pytest

from checks import transcription
from checks.collate import collate

ROOT = Path(__file__).resolve().parents[1]
L1 = "proprium.dominica-i-in-quadragesima-"
L2 = "proprium.dominica-ii-in-quadragesima-"
L3 = "proprium.dominica-iii-in-quadragesima-"
L4 = "proprium.dominica-iv-in-quadragesima-"
TRF = "proprium.transfiguratio-domini-evangelium"
P9OF = "proprium.dominica-ix-post-pentecosten-offertorium"
P18GR = "proprium.dominica-xviii-post-pentecosten-graduale"
EP3SEC = "proprium.dominica-iii-post-epiphaniam-secreta"
INTROITS = [
    (L1 + "introitus", "Invocábit"),
    (L2 + "introitus", "Reminíscere"),
    (L3 + "introitus", "Oculi"),
    (L4 + "introitus", "Lætáre"),
]
ORATIONS = [
    L1 + "collecta",
    L1 + "secreta",
    L1 + "postcommunio",
    L2 + "collecta",
    L2 + "secreta",
    L3 + "collecta",
    L3 + "postcommunio",
    L4 + "collecta",
    L4 + "postcommunio",
]
REPRINTS = [
    (TRF, "lent-ii-reprint", "p. 80"),
    (P9OF, "lent-iii-reprint", "p. 93"),
    (P18GR, "lent-iv-reprint", "p. 106"),
    (L2 + "secreta", "lent-iv-reprint", "p. 107"),
]
BASES = [
    L1 + "graduale",
    L1 + "offertorium",
    L1 + "epistola",
    L1 + "evangelium",
    L2 + "offertorium",
    L2 + "communio",
    L2 + "epistola",
    L2 + "tractus",
    L3 + "introitus",
    L3 + "graduale",
    L3 + "tractus",
    L3 + "communio",
    L3 + "epistola",
    L3 + "evangelium",
    L4 + "offertorium",
    L4 + "communio",
    L4 + "epistola",
    L4 + "evangelium",
    P18GR,
]
CONCLUSION = [
    ["w", "Through"],
    ["g", "our Lord"],
    ["g", "Jesus Christ"],
    ["g", "Your Son"],
    ["g", "who lives and reigns with You"],
    ["w", "in"],
    ["w", "the unity"],
    ["g", "of the Holy Spirit"],
    ["w", "God"],
]
GLORIA = (
    "Glory | to the Father | and | to the Son | and | [to the Holy Spirit] | As | it was | in | "
    "the beginning | and | now | and | ever | and | for | ages | of ages | Amen"
)
ARCHAIC = re.compile(
    r"\b(thee|thou|thy|thine|hath|doth|ye|unto|saith|shalt|wilt|didst|whence|wherein|"
    r"wherewith|thither|liveth|reigneth|cometh|goeth|taketh|becometh|findeth|walketh|keepeth|"
    r"possesseth|gathereth|scattereth|casteth|proceedeth|endureth|dwelleth|dwellest|seest|"
    r"grantest|purifiest|travailest|bearest|feedest|for ever)\b",
    re.I,
)
TEXTS = [
    "ordinarium.praefatio-quadragesimae",
    "proprium.dominica-i-post-epiphaniam-postcommunio",
    EP3SEC,
    TRF,
    P9OF,
    P18GR,
    "proprium.dedicatio-archibasilicae-sanctissimi-salvatoris-tractus",
] + [
    mass + part
    for mass in (L1, L2, L3, L4)
    for part in (
        "introitus",
        "collecta",
        "epistola",
        "graduale",
        "tractus",
        "evangelium",
        "offertorium",
        "secreta",
        "communio",
        "postcommunio",
    )
    if (ROOT / "texts" / (mass + part).replace(".", "/", 1)).with_suffix(".json").exists()
]
REPRINT_LEAVES = {  # leaf -> sha256 of the page image the reprint use cites
    "n159": "d117e505f93954850d06e84ea74c922bff1ba84ca8e9245f42e39854ff607e0d",
    "n172": "873e24b97c4ee2f2ae57abdc8873f74387443e24b03cc3b5b7cc615d8c364103",
    "n185": "d488e370334185fcafd8882ed61df4971f88f6c2cbaaeb298da3d22d97ecd27d",
    "n186": "7e4c16b76eae65c5b647a502ce0ed4c0bd190984ed3b8a51456ba1417406c504",
}
PD_LOCATORS = {
    L1 + "graduale": ("p. 172", "scan p. 188"),
    L1 + "offertorium": ("pp. 173–174", "scan pp. 189–190"),
    L1 + "epistola": ("pp. 171–172", "scan pp. 187–188"),
    L1 + "evangelium": ("p. 173", "scan p. 189"),
    L2 + "offertorium": ("p. 193", "scan p. 209"),
    L2 + "communio": ("p. 193", "scan p. 209"),
    L2 + "epistola": ("pp. 191–192", "scan pp. 207–208"),
    L2 + "tractus": ("p. 192", "scan p. 208"),
    L3 + "introitus": ("pp. 209–210", "scan pp. 225–226"),
    L3 + "graduale": ("p. 210", "scan p. 226"),
    L3 + "tractus": ("pp. 210–211", "scan pp. 226–227"),
    L3 + "communio": ("p. 212", "scan p. 228"),
    L3 + "epistola": ("p. 210", "scan p. 226"),
    L3 + "evangelium": ("pp. 211–212", "scan pp. 227–228"),
    L4 + "offertorium": ("p. 233", "scan p. 249"),
    L4 + "communio": ("p. 233", "scan p. 249"),
    L4 + "epistola": ("pp. 231–232", "scan pp. 247–248"),
    L4 + "evangelium": ("pp. 232–233", "scan pp. 248–249"),
    P18GR: ("p. 232", "scan p. 248"),
}
LAITY_SHA = "8e692b256e08350896902e55787f70c171a444d33e754f4d67e84fe000f81dd1"


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


def line(language, text, segment="s01"):
    """The composed interlinear line as the reader shows it: a group's caption once, bracketed."""
    doc, lay = core(text), layer(language, text)
    seg = next(s for s in doc["segments"] if s["id"] == segment)
    spans = {a["words"][0]: a for a in lay["segments"].get(segment, {}).get("alignments", [])}
    ids, out, i = [w["id"] for w in seg["words"]], [], 0
    while i < len(ids):
        group = spans.get(ids[i])
        if group:
            gloss = group.get("gloss")
            out.append(f"[{gloss}]" if gloss and len(group["words"]) > 1 else gloss or "(0)")
            i += len(group["words"])
            continue
        out.append(lay["words"][ids[i]]["gloss"])
        i += 1
    return " | ".join(out)


def test_the_first_sunday_prints_colons_after_tuae_and_homo():
    for text, wid, form, body in (
        (L1 + "collecta", "w011", "tuæ", "famíliæ tuæ: ut,"),
        (L1 + "evangelium", "w050", "homo", "vivit homo: sed"),
    ):
        word = words(core(text))[wid]
        assert (word["form"], word["post"]) == (form, ":")
        assert body in bodies(text)[0]
        entry = next(e for e in apparatus(text) if e["at"] == wid)
        assert (entry["class"], set(entry["witnesses"])) == ("punctuation", {"do"})
        clean(text)


def test_the_first_sunday_records_its_page_slips():
    tract = L1 + "tractus"
    assert words(core(tract))["w135"]["form"] == "exáudiam"
    assert "et ego exaudiam eum: cum ipso" in bodies(tract)[0]
    entry = next(e for e in apparatus(tract) if e["at"] == "w135" and "mr" in e["witnesses"])
    assert (entry["witnesses"], entry["class"]) == ({"mr": "exaudiam"}, "accent")
    clean(tract)
    postcommunion = L1 + "postcommunio"
    assert words(core(postcommunion))["w001"]["form"] == "Tui"
    assert bodies(postcommunion)[0].startswith("Tuis nos, Dómine,")
    assert "# corrigendum: Tuis -> Tui (" in witness(postcommunion)
    clean(postcommunion)


def test_the_third_sunday_gospel_reads_the_present_invenit():
    text = L3 + "evangelium"
    word = words(core(text))["w179"]
    assert (word["form"], word["morph"]["tense"]) == ("ínvenit", "pres")
    assert "vénerit, ínvenit eam" in bodies(text)[0]
    entry = next(e for e in apparatus(text) if e["at"] == "w179")
    assert (entry["witnesses"], entry["class"]) == ({"do": "invénit"}, "accent")
    assert layer("en", text)["words"]["w179"]["gloss"] == "finds"
    assert layer("pl", text)["words"]["w179"]["gloss"] == "zastaje"
    clean(text)


def test_the_fourth_sunday_epistle_records_the_accented_slip():
    text = L4 + "epistola"
    assert words(core(text))["w002"]["form"] == "Scriptum"
    assert bodies(text)[0].startswith("Fratres: Scríptum est:")
    entry = next(e for e in apparatus(text) if e["at"] == "w002" and "mr" in e["witnesses"])
    assert (entry["witnesses"], entry["class"]) == ({"mr": "Scríptum"}, "accent")
    clean(text)


@pytest.mark.parametrize("text,cue", INTROITS)
def test_the_introits_declare_their_expanded_cues(text, cue):
    assert f"as cues only (℣. Glória Patri. {cue}.);" in witness(text)
    found = record(text)
    assert found["orthography_profile"] == "page-body-with-declared-house-expansion"
    assert {"expanded-doxology.mr1962", "introit-expansion.mr1962"} <= set(uses(text))
    assert GLORIA in line("en", text)
    clean(text)


@pytest.mark.parametrize("text", ORATIONS)
def test_the_per_dominum_conclusions_are_declared_composites(text):
    found = uses(text)
    expected = {f"conclusion-{kind}.mr1962" for kind in ("middle", "rg115a", "terminal")}
    assert {key for key in found if "conclusion-" in key} == expected
    assert found["mr1962"]["decision"] == "RETAIN_WITH_CORRECTION"
    assert record(text)["orthography_profile"] == "exact-declared-composite"
    assert "Deus. Per ómnia sǽcula sæculórum. Amen." in bodies(text)[-1]
    composed = line("en", text)
    expected_line = " | ".join(f"[{g}]" if kind == "g" else g for kind, g in CONCLUSION)
    assert expected_line in composed
    clean(text)


@pytest.mark.parametrize("text,key,printed", REPRINTS)
def test_the_lent_masses_record_their_reprints(text, key, printed):
    use = uses(text)[f"{key}.mr1962"]
    assert (use["role"], use["locator"]["printed"]) == ("direct_approved_print", printed)
    assert "identical in letters, accents and punctuation" in use["claim"]
    leaf = use["locator"]["page_url"].split("/page/")[1].split("/")[0]
    assert use["locator"]["scan"] == f"leaf {leaf} / PDF p. {int(leaf[1:]) + 1}"
    assert use["evidence_sha256"] == REPRINT_LEAVES[leaf]
    assert int(printed[3:]) == int(leaf[1:]) - 79


@pytest.mark.parametrize("text", BASES)
def test_the_revised_english_names_its_historical_basis(text):
    site = f"{text}.s01.en"
    provenance = {s["site"]: s for s in load("languages/en/translation-provenance.json")["sites"]}
    mixed = text == L3 + "introitus"
    assert provenance[site]["origin"] == ("mixed" if mixed else "public-domain")
    basis = [
        r for r in load("languages/en/translation-basis.json")["records"] if text in r["texts"]
    ]
    expected_basis = (
        [] if mixed else [{"texts": [text], "segments": ["s01"], "relationship": "revised"}]
    )
    assert basis == expected_basis
    found = [
        u
        for u in load("languages/en/bibliography.json")["uses"]
        if u["id"] == f"use.en.{text}.body.laity1846"
    ]
    assert len(found) == 1 and found[0]["edition"] == "edition.the-missal-for-the-laity-1846"
    locator = found[0]["locator"]
    assert (locator["printed"], locator["scan"]) == PD_LOCATORS[text]
    assert found[0]["evidence_sha256"] == LAITY_SHA
    if mixed:
        expected = load("tests/fixtures/mixed-translation-origins.json")["corrected_use"]
        assert found[0] == expected["after"]


@pytest.mark.parametrize("text", TEXTS)
def test_the_english_verses_are_in_the_contemporary_register(text):
    for segment in layer("en", text)["segments"].values():
        assert not ARCHAIC.findall(segment.get("translation") or "")


def test_the_major_line_repairs_read_in_order():
    assert "[to His angels] | He has given charge | over | you" in line("en", L1 + "tractus")
    assert "it strives | this | by good | works | it may accomplish" in line("en", L1 + "collecta")
    epistle = line("en", L1 + "epistola")
    assert "sorrowful | [yet always] | rejoicing" in epistle
    assert "needy | [yet enriching many]" in epistle
    assert "[the restriction of bodily food]" in line("en", L1 + "secreta")
    assert "[may cause us to pass into the fellowship of the saving mystery]" in line(
        "en", L1 + "postcommunio"
    )
    assert "[us to be bereft of all strength]" in line("en", L2 + "collecta")
    assert "[that these may eat]" in line("en", L4 + "evangelium")
    assert "[abyś przypadkiem nie] | uraził" in line("pl", L1 + "evangelium")
    assert "[niech sprawi, że dostąpimy udziału w zbawczym misterium]" in line(
        "pl", L1 + "postcommunio"
    )
    assert "abyśmy | od | wszystkich | przeciwności | byli chronieni" in line("pl", L2 + "collecta")


def test_the_referenced_texts_name_their_lent_use():
    for text, sentence in (
        (L1 + "offertorium", "The same chant is also the Communion of this formulary."),
        (TRF, "The same Gospel is read on the Second Sunday of Lent."),
        (P9OF, "The same chant is used in the formulary of the Third Sunday of Lent."),
        (P18GR, "The same chant is used in the formulary of the Fourth Sunday of Lent."),
        (L2 + "secreta", "The same prayer is used in the formulary of the Fourth Sunday of Lent."),
    ):
        assert layer("en", text)["about"].endswith(sentence)
    assert layer("en", EP3SEC)["about"].endswith(
        "The same prayer is used in the formularies of Quinquagesima and the Third Sunday of Lent, "
        "and when the formulary is resumed after Pentecost."
    )
    assert layer("pl", EP3SEC)["about"].endswith(
        "Ta sama modlitwa jest używana w formularzach niedzieli Pięćdziesiątnicy i trzeciej "
        "niedzieli Wielkiego Postu oraz wtedy, gdy formularz powraca po Zesłaniu Ducha Świętego."
    )
    for language in ("en", "pl"):
        assert "115" not in layer(language, EP3SEC)["about"]
    assert (
        "God, who by fasting restrains"
        in layer("en", "ordinarium.praefatio-quadragesimae")["about"]
    )


def test_the_shared_postcommunion_names_the_owning_page():
    entry = next(
        e
        for e in apparatus("proprium.dominica-i-post-epiphaniam-postcommunio")
        if e["at"] == "w006"
    )
    assert entry["ruling"].startswith("The owning page 42 prints ut quos without a comma")
    assert "page 53 and II-Lent page 81 print ut, quos" in entry["ruling"]


def test_the_lateran_tract_stays_the_twin_of_the_fourth_sunday_tract():
    twin = layer("en", "proprium.dedicatio-archibasilicae-sanctissimi-salvatoris-tractus")
    lent = layer("en", L4 + "tractus")
    assert twin["segments"]["s01"]["translation"] == lent["segments"]["s01"]["translation"]
    assert line("en", L4 + "tractus") == line(
        "en", "proprium.dedicatio-archibasilicae-sanctissimi-salvatoris-tractus"
    )
