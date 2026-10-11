"""Passion Sunday as the approved Benziger printing has it, with the English that names its
historical basis and the interlinear lines that read in English and Polish order.

Page 121 prints the Gradual's respond with a full stop before its verse, *voluntátem tuam.*, and
the Gospel's *et prophétæ: et tu dicis* with a colon. The Introit's repeated antiphon is a declared
expansion of the printed cue; from Passion Sunday to Holy Thursday the Introit has no Gloria
Patri (Rubricae generales 428). Every *Per Dóminum* conclusion is a declared composite of the
proper page, page 123 and page 226 under Rubricae generales 115 a. The English revised from
*The Missal for the Laity* (1846) names its basis. The Precious Blood Epistle prints the same
words as this Epistle, and its lines and verses stay the same. The English tail of the common
preface, printed in eleven proper prefaces as in the common one, names its basis in *The Family
Prayer Book* (1839), as the common preface does. The Offertory reads *vivam, et custódiam* as
futures in both languages, as the edition's parse does, and the Introit's source method says that
the raw binding of its Divinum Officium reading is pending.
"""

import json
import re
from pathlib import Path

import pytest

from checks import transcription
from checks.collate import collate

ROOT = Path(__file__).resolve().parents[1]
PA = "proprium.dominica-i-passionis-"
TWIN = "proprium.pretiosissimi-sanguinis-domini-nostri-iesu-christi-epistola"
ORATIONS = [PA + "collecta", PA + "secreta", PA + "postcommunio"]
PD_LOCATORS = {
    PA + "introitus": ("p. 253", "scan p. 269"),
    PA + "graduale": ("p. 254", "scan p. 270"),
    PA + "tractus": ("p. 254", "scan p. 270"),
    PA + "offertorium": ("p. 255", "scan p. 271"),
    PA + "evangelium": ("pp. 254–255", "scan pp. 270–271"),
}
PD_CLAIMS = {
    PA + "introitus": (
        "Historical English basis of the Introit (the Douay Ps 42:1–3 through this missal), "
        "revised in contemporary language: You are my God, they have led me (deduxérunt), to "
        "Your holy mountain (montem); the repeated antiphon written out."
    ),
    PA + "graduale": (
        "Historical English basis of the Gradual (the Douay Ps 142:9–10 and 17:48–49 through "
        "this missal), revised in contemporary language: O Lord, my deliverer (an address, "
        "Liberátor meus, Dómine), the wrathful nations, those who rise against me."
    ),
    PA + "tractus": (
        "Historical English basis of the Tract (the Douay Ps 128:1–4 through this missal), "
        "revised against the Latin: sinners (peccatóres), their iniquities, has cut (the "
        "Missal prints concídit)."
    ),
    PA + "offertorium": (
        "Historical English basis of the Offertory (the Douay Ps 118:17, 107 through this "
        "missal), revised against the Latin in contemporary language: I will live (vivam), "
        "Your words (sermónes), give me life (vivífica)."
    ),
    PA + "evangelium": (
        "Historical English basis of the Gospel (John 8:46–59), revised against the Latin in "
        "contemporary language: the multitudes (turbis), will convict, a demon for dæmónium, "
        "if anyone keeps, forever, therefore said (Dixérunt ergo)."
    ),
}
CONCLUSION = (
    "Through | [our Lord] | [Jesus Christ] | [Your Son] | [who lives and reigns with You] | in | "
    "the unity | [of the Holy Spirit] | God"
)
ARCHAIC = re.compile(
    r"\b(thee|thou|thy|thine|hath|doth|ye|unto|saith|shalt|wilt|didst|art|hast|dost|whence|"
    r"liveth|reigneth|heareth|seeketh|judgeth|sayest|glorifieth|for ever)\b",
    re.I,
)
TEXTS = ["ordinarium.praefatio-sanctae-crucis", TWIN] + [
    PA + part
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
]
LAITY_SHA = "8e692b256e08350896902e55787f70c171a444d33e754f4d67e84fe000f81dd1"
FPB_SHA = "30ead2ef44af505a94a0fe33b30ac85040af33d444a3472f31f2c53a4868b02d"
TAIL = {
    "ordinarium.praefatio-sanctae-crucis": ("s05", "s06"),
    "ordinarium.praefatio-quadragesimae": ("s05", "s06"),
    "ordinarium.praefatio-sancti-ioseph-in-festivitate": ("s06", "s07"),
    "ordinarium.praefatio-sancti-ioseph-in-solemnitate": ("s06", "s07"),
    "ordinarium.praefatio-beatae-mariae-virginis": ("s06", "s07"),
    "ordinarium.praefatio-beatae-mariae-virginis-in-annuntiatione": ("s06", "s07"),
    "ordinarium.praefatio-beatae-mariae-virginis-in-assumptione": ("s06", "s07"),
    "ordinarium.praefatio-beatae-mariae-virginis-in-conceptione-immaculata": ("s06", "s07"),
    "ordinarium.praefatio-beatae-mariae-virginis-in-nativitate": ("s06", "s07"),
    "ordinarium.praefatio-beatae-mariae-virginis-in-transfixione": ("s06", "s07"),
    "ordinarium.praefatio-beatae-mariae-virginis-in-visitatione": ("s06", "s07"),
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


def uses(text):
    prefix = f"use.{text}."
    return {
        use["id"][len(prefix) :]: use
        for use in load("bibliography/graph.json")["uses"]
        if use["id"].startswith(prefix)
    }


def record(text):
    graph = load("bibliography/graph.json")
    return next(w for w in graph["witnesses"] if w["id"] == f"witness.{text}.mr1962")


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


def test_the_texts_list_is_complete():
    assert len(TEXTS) == 12
    for text in TEXTS:
        assert (ROOT / "texts" / (text.replace(".", "/", 1) + ".json")).exists()


def test_the_gradual_ends_its_respond_with_a_full_stop():
    text = PA + "graduale"
    assert words(core(text))["w011"]["post"] == "."
    assert "voluntátem tuam. Liberátor" in bodies(text)[0]
    entry = next(e for e in apparatus(text) if e["at"] == "w011")
    assert (entry["witnesses"], entry["class"]) == ({"do": "tuam"}, "punctuation")
    assert "| [Your will] | [My deliverer] |" in line("en", text)
    clean(text)


def test_the_gospel_prints_a_colon_after_prophetae():
    text = PA + "evangelium"
    assert words(core(text))["w107"]["post"] == ":"
    assert "et prophétæ: et tu dicis" in bodies(text)[0]
    entry = next(e for e in apparatus(text) if e["at"] == "w107")
    assert (entry["ours"], entry["witnesses"]) == ("prophétæ:", {"do": "Prophétæ;"})
    clean(text)


def test_the_introit_declares_its_repetition_without_a_gloria_patri():
    text = PA + "introitus"
    assert "the page prints the repeated antiphon as the cue Iúdica. only and no Gloria Patri" in (
        witness(text)
    )
    assert record(text)["orthography_profile"] == "page-body-with-declared-house-expansion"
    found = uses(text)
    assert "introit-expansion.mr1962" in found and "expanded-doxology.mr1962" not in found
    assert found["introit-expansion.mr1962"]["locator"]["section"] == "Rubricae generales 427–428"
    assert "Glória" not in [w["form"] for w in ordered(core(text))]
    clean(text)


@pytest.mark.parametrize("text", ORATIONS)
def test_the_per_dominum_conclusions_are_declared_composites(text):
    found = uses(text)
    expected = {f"conclusion-{kind}.mr1962" for kind in ("middle", "rg115a", "terminal")}
    assert {key for key in found if "conclusion-" in key} == expected
    assert found["mr1962"]["decision"] == "RETAIN_WITH_CORRECTION"
    assert record(text)["orthography_profile"] == "exact-declared-composite"
    assert "Deus. Per ómnia sǽcula sæculórum. Amen." in bodies(text)[-1]
    assert CONCLUSION in line("en", text)
    clean(text)


@pytest.mark.parametrize("text", sorted(PD_LOCATORS))
def test_the_revised_english_names_its_historical_basis(text):
    site = f"{text}.s01.en"
    provenance = {s["site"]: s for s in load("languages/en/translation-provenance.json")["sites"]}
    assert provenance[site]["origin"] == "public-domain"
    basis = [
        r for r in load("languages/en/translation-basis.json")["records"] if text in r["texts"]
    ]
    assert basis == [{"texts": [text], "segments": ["s01"], "relationship": "revised"}]
    found = [
        u
        for u in load("languages/en/bibliography.json")["uses"]
        if u["id"] == f"use.en.{text}.body.laity1846"
    ]
    assert len(found) == 1 and found[0]["edition"] == "edition.the-missal-for-the-laity-1846"
    locator = found[0]["locator"]
    assert (locator["printed"], locator["scan"]) == PD_LOCATORS[text]
    assert found[0]["evidence_sha256"] == LAITY_SHA
    assert found[0]["claim"] == PD_CLAIMS[text]


@pytest.mark.parametrize("text", TEXTS)
def test_the_english_verses_are_in_the_contemporary_register(text):
    for segment in layer("en", text)["segments"].values():
        assert not ARCHAIC.findall(segment.get("translation") or "")


def test_the_major_line_repairs_read_in_order():
    epistle = line("en", PA + "epistola")
    assert "a High Priest | [of the good things to come]" in epistle
    assert "Himself | offered | unspotted | to God" in epistle
    assert "[those who are called may receive the promise of the eternal inheritance]" in epistle
    secret = line("en", PA + "secreta")
    assert "both | [may loose the bonds of our perversity] | and" in secret
    assert "[may obtain for us the gifts of Your mercy]" in secret
    assert "[their iniquities] | [the just Lord] | has cut" in line("en", PA + "tractus")
    gospel = line("pl", PA + "evangelium")
    assert "zachowa | śmierci | nie | ujrzy" in gospel
    assert "nie | zakosztuje | śmierci" in gospel
    assert "dowiedzie | Mi | [grzechu]" in gospel
    assert line("en", PA + "evangelium").count("[Jesus answered] | I") == 2
    preface = "ordinarium.praefatio-sanctae-crucis"
    assert "i | ten, który | na | drzewie | zwyciężał" in line("pl", preface, "s04")
    assert "and | he who | by | a tree | conquered" in line("en", preface, "s04")
    assert "przez drzewo też został pokonany" in layer("pl", preface)["about"]


def test_the_precious_blood_epistle_stays_the_twin_of_this_epistle():
    for language in ("en", "pl"):
        twin, passion = layer(language, TWIN), layer(language, PA + "epistola")
        assert twin["segments"] == passion["segments"]
        assert twin["words"] == passion["words"]
        assert line(language, TWIN) == line(language, PA + "epistola")


@pytest.mark.parametrize("text", sorted(TAIL))
def test_the_common_preface_tail_names_its_basis_in_every_preface(text):
    provenance = {s["site"]: s for s in load("languages/en/translation-provenance.json")["sites"]}
    uses = {
        u["id"]: u
        for u in load("languages/en/bibliography.json")["uses"]
        if u.get("address", {}).get("text") == text
    }
    for segment in TAIL[text]:
        assert provenance[f"{text}.{segment}.en"]["origin"] == "public-domain"
        use = uses[f"use.en.{text}.{segment}.fpb1839"]
        assert use["edition"] == "edition.the-family-prayer-book-1839"
        assert use["locator"] == {"printed": "p. 79", "scan": "scan p. 110"}
        assert use["evidence_sha256"] == FPB_SHA
    basis = [
        r for r in load("languages/en/translation-basis.json")["records"] if text in r["texts"]
    ]
    assert basis == [{"texts": [text], "segments": list(TAIL[text]), "relationship": "revised"}]


def test_the_introit_method_states_that_its_raw_binding_is_pending():
    method = core(PA + "introitus")["editorial"]["source"]["method"]
    assert "bound to its raw archive" not in method
    assert "raw binding is pending (its reading divides deduxérunt into two words" in method
    assert "the raw binding is pending" in witness(PA + "introitus", "do")


def test_the_offertory_reads_vivam_as_a_future_in_both_languages():
    text = PA + "offertorium"
    assert words(core(text))["w011"]["morph"]["tense"] == "fut"
    assert "będę żył i strzegł Twoich słów" in layer("pl", text)["segments"]["s01"]["translation"]
    assert "I will live and keep Your words" in layer("en", text)["segments"]["s01"]["translation"]
    assert "| będę żył | i | będę strzegł |" in line("pl", text)
    assert "| I will live | and | I will keep |" in line("en", text)


def test_the_lines_keep_their_objects_and_subjects():
    introit = line("en", PA + "introitus")
    assert "they | [have led and brought me] | to | [Your holy mountain]" in introit
    gospel = line("en", PA + "evangelium")
    assert "are | You | and | [have a demon]" in gospel
    assert "[My day] | he saw | and" in gospel
