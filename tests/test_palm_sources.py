"""Palm Sunday as the approved Benziger printing has it, with the English that names its
historical basis and the interlinear lines that read in English and Polish order.

Page 141 prints the Passion's *Tu víderis.*, a future perfect. The Introit's repeated antiphon
is a declared expansion of the printed cue, with no Gloria Patri (Rubricae generales 427–428).
The Collect's *Per eúndem* conclusion (Rubricae generales 115 b) and the *Per Dóminum*
conclusions of the Secret and Postcommunion are declared composites of the proper page, page 123
and page 226, and their witnesses state what page xvii prints. Page 138 prints the Epistle of the
Exaltation of the Cross in full with three different commas, which a use records. The English
revised from *The Missal for the Laity* (1846) or Husenbeth's *Missal for the Use of the Laity*
(1853) names its basis. The Postcommunion stays the twin of the Christmas-octave Postcommunion,
the Introit and the Tract render Psalm 21 alike in Polish, and the Communion renders Matthew
26:42 as the Passion does; its changed verses no longer claim the earlier internal review, and
the Polish Communion shares the unsettled origin of the Passion verse whose wording it carries.
The intensive *autem* of Philippians 2:8 reads as *even death* in the Epistle of the Cross.
"""

import json
import re
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from checks import transcription
from checks.collate import collate

ROOT = Path(__file__).resolve().parents[1]
PA = "proprium.dominica-ii-passionis-"
EPISTLE = "proprium.exaltatio-sanctae-crucis-epistola"
TWIN = "proprium.dominica-infra-octavam-nativitatis-postcommunio"
ORATIONS = [PA + "collecta", PA + "secreta", PA + "postcommunio"]
EXPECTED_TEXTS = (
    EPISTLE,
    *(
        PA + part
        for part in (
            "introitus",
            "collecta",
            "graduale",
            "tractus",
            "evangelium",
            "offertorium",
            "secreta",
            "communio",
            "postcommunio",
        )
    ),
)
TEXTS = list(EXPECTED_TEXTS)
LAITY = ("edition.the-missal-for-the-laity-1846", "laity1846")
HUSENBETH = ("edition.the-missal-for-the-use-of-the-laity-1853", "husenbeth1853")
SHA = {
    "laity1846": "8e692b256e08350896902e55787f70c171a444d33e754f4d67e84fe000f81dd1",
    "husenbeth1853": "64dda22f4b0753135be1112b8bd36eab7fbb9c92586c2fc2d831c0a4b7f65d8a",
}
PD = {
    PA + "introitus": (HUSENBETH, "pp. 249–250", "scan pp. 276–277", "ne longe fácias"),
    PA + "graduale": (LAITY, "p. 283", "scan p. 299", "pacem peccatórum videns"),
    PA + "tractus": (HUSENBETH, "p. 251", "scan p. 278", "the third speravérunt"),
    PA + "offertorium": (LAITY, "p. 292", "scan p. 308", "consolántem me quæsívi"),
    PA + "evangelium": (LAITY, "pp. 285–292", "scan pp. 301–308", "the elders (senióres)"),
}
CONCLUSION = (
    "Through | [our Lord] | [Jesus Christ] | [Your Son] | [who lives and reigns with You] | in | "
    "the unity | [of the Holy Spirit] | God"
)
SAME_LORD = (
    "Through | [this same Jesus Christ, our Lord] | [Your Son] | [who lives and reigns with You] | "
    "in | the unity | [of the Holy Spirit] | God | [forever and ever]"
)
XVII = (
    "# correction: 2026-10-11 p. xvii (Rubricae generales 115 a, leaf n22) prints this formula "
    "unaccented as Filium tuum, qui tecum vivit: no comma after Christum, but a comma and a "
    "lower-case qui after tuum, so it does not attest the colon form; the colon and the upper-case "
    "Qui of this composite follow p. 123, leaf n202"
)
WORK_NOTE = re.compile(
    r"\b(?:MR|DO)\b|full\d|Do not diagnose|really has|[Rr]etain the|Preserve both"
)
ARCHAIC = re.compile(
    r"\b(thee|thou|thy|thine|hath|doth|ye|unto|saith|shalt|wilt|didst|art|hast|dost|whence|"
    r"knowest|sayest|seest|goest|comest|answerest|destroyest|dwellest|thinkest|givest|"
    r"wouldst|couldst|shouldst|canst|hadst|wast|well-nigh|"
    r"for ever|[a-z]+eth)\b",
    re.I,
)
MODERN_ETH = {
    "nazareth",
    "elizabeth",
    "teeth",
    "seth",
    "japheth",
    "twentieth",
    "thirtieth",
    "fortieth",
    "fiftieth",
    "sixtieth",
    "seventieth",
    "eightieth",
    "ninetieth",
    "umptieth",
}
SECOND_PERSON_OLD = re.compile(r"\b(?:you|thou)\s+([a-z]+(?:est|st))\b", re.I)
# Modern lexical words sharing the suffix are not second-person inflections.
# This is a scoped register guard, not a comprehensive English morphology parser.
MODERN_EST_ST = {
    "best",
    "greatest",
    "latest",
    "oldest",
    "newest",
    "lowest",
    "highest",
    "smallest",
    "first",
    "last",
    "just",
    "must",
    "least",
    "most",
    "honest",
    "forest",
    "harvest",
    "manifest",
    "interest",
    "trust",
    "rest",
    "test",
    "vest",
    "nest",
    "quest",
    "jest",
    "guest",
    "host",
    "cost",
    "lost",
    "frost",
    "boost",
    "roast",
    "toast",
    "coast",
    "boast",
    "ghost",
    "list",
    "feast",
    "beast",
    "breast",
    "invest",
    "divest",
    "protest",
    "contest",
    "detest",
    "arrest",
    "attest",
    "request",
    "suggest",
    "ingest",
    "digest",
    "infest",
    "assist",
    "consist",
    "desist",
    "insist",
    "persist",
    "resist",
    "twist",
    "exist",
    "adjust",
    "post",
    "thrust",
    "burst",
    "oust",
    "crest",
    "crust",
    "wrist",
    "waist",
    "heist",
    "midst",
    "cast",
    "past",
    "fast",
    "whilst",
    "against",
    "artist",
    "baptist",
    "atheist",
}
SPELLING_PUNCT = (
    "The selected spelling and punctuation follow the approved Benziger printing. The pinned "
    "digital spelling and any accompanying punctuation are recorded exactly; both readings "
    "represent the same word."
)


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


def provenance(language):
    return {
        s["site"]: s for s in load(f"languages/{language}/translation-provenance.json")["sites"]
    }


def archaic(string):
    string = string or ""
    hits = [w for w in ARCHAIC.findall(string) if w.lower() not in MODERN_ETH]
    return hits + [w for w in SECOND_PERSON_OLD.findall(string) if w.lower() not in MODERN_EST_ST]


def glosses(language, text):
    lay = layer(language, text)
    out = [w.get("gloss") or "" for w in lay["words"].values()]
    return out + [
        a.get("gloss") or "" for s in lay["segments"].values() for a in s.get("alignments", [])
    ]


# The oration conclusion `… Fílium tuum: Qui tecum vivit et regnat …`: the relative `Qui`
# after the Latin colon continues the sentence. Finite reviewed addresses (the exact English
# groups; the Polish sentence-internal `który` of 2026-10-16, pinned by
# test_polish_relative_captions), not a rule for every Latin colon or every `który`.
CONCLUSION_RELATIVE = {
    PA + "collecta": [f"w{i:03d}" for i in range(39, 44)],
    PA + "secreta": [f"w{i:03d}" for i in range(27, 32)],
    PA + "postcommunio": [f"w{i:03d}" for i in range(21, 26)],
}
WHO_LIVES = "who lives and reigns with You"


def conclusion_relative(language, text, index, prev, first, group, gloss):
    """None away from a reviewed conclusion address, or when its Latin context changed (then the
    plain opening rule decides); otherwise whether the caption has the one reviewed shape.
    English: the exact five-word group `who lives and reigns with You` keeps its lower case, and
    any other caption falls back to the plain rule. Polish: the unaligned relative `Qui` after the
    Latin colon must read `który`, so a capital, another form or a group there is a miss."""
    words = CONCLUSION_RELATIVE.get(text)
    if words is None or first["id"] != words[0]:
        return None
    bound = (
        index > 0
        and prev.rstrip().endswith(":")
        and first["form"] == "Qui"
        and first["lemma"] == "qui"
    )
    if not bound:
        return None
    if language == "pl":
        return group is None and gloss == "który"
    if language == "en":
        exempt = group is not None and group["words"] == words and gloss == WHO_LIVES
        return True if exempt else None
    return None


def tract_continuation(language, text, ws, index, group, gloss):
    """The translated clause continues with the recipient after Latin `eius. Pópulo`.

    This exact continuation does not make every Latin full stop optional in a caption.
    The complete translated sentence is pinned by the Tract's caption fixture.
    """
    expected = {"pl": "ludowi", "en": "to the people"}.get(language)
    if text != PA + "tractus" or expected is None or index == 0:
        return None
    context = [
        (w["id"], w["form"], w["lemma"], w.get("post", "")) for w in ws[index - 1 : index + 1]
    ]
    if context != [("w141", "eius", "is", "."), ("w142", "Pópulo", "populus", ",")]:
        return None
    return group is None and gloss == expected


def opening_check(language, text):
    """Latin capitals after a stop (or a segment's first word) whose realized gloss starts lower
    case, except the reviewed conclusion relative (`conclusion_relative`), which must read as
    reviewed in either language."""
    doc, lay, out, examined = core(text), layer(language, text), [], 0
    for seg in doc["segments"]:
        ws = seg.get("words", [])
        spans = {a["words"][0]: a for a in lay["segments"].get(seg["id"], {}).get("alignments", [])}
        prev, pending, i = ".", False, 0
        while i < len(ws):
            group = spans.get(ws[i]["id"])
            n = len(group["words"]) if group else 1
            first, last = ws[i], ws[i + n - 1]
            opens = pending or (
                prev.rstrip().endswith((".", ":", "?", "!")) and first["form"][:1].isupper()
            )
            gloss = group.get("gloss") if group else lay["words"][first["id"]].get("gloss")
            reviewed = conclusion_relative(language, text, i, prev, first, group, gloss)
            if reviewed is None:
                reviewed = tract_continuation(language, text, ws, i, group, gloss)
            prev, i = last.get("post", ""), i + n
            if gloss is None and reviewed is not False:
                pending = opens
                continue
            pending = False
            if opens:
                examined += 1
            if reviewed is False or (reviewed is None and opens and gloss[:1].islower()):
                out.append((seg["id"], first["id"], gloss))
    return out, examined


def missed_openings(language, text):
    return opening_check(language, text)[0]


REVERSE_NAMED = {
    ("pl", PA + "tractus", "w036"): "Chwało",
    ("pl", PA + "evangelium", "w171"): "Człowieka",
    ("pl", PA + "evangelium", "w482"): "Człowieka",
    ("pl", PA + "evangelium", "w190"): "Dwunastu",
    ("pl", PA + "evangelium", "w759"): "Pole",
    ("pl", PA + "evangelium", "w760"): "Krwi",
    ("pl", PA + "evangelium", "w219"): "Ten",
    ("pl", PA + "evangelium", "w1418"): "Ten",
    # Reviewed first-person possessives/pronoun in Jesus' direct speech.
    ("pl", PA + "evangelium", "w040"): "Moja",
    ("pl", PA + "evangelium", "w060"): "Mój",
    ("pl", PA + "evangelium", "w118"): "Mój",
    ("pl", PA + "evangelium", "w298"): "Mego",
    ("pl", PA + "evangelium", "w301"): "Mi",
    ("pl", PA + "evangelium", "w1298"): "Mój",
    ("pl", PA + "evangelium", "w1300"): "Mój",
}


def tract_divine_group(language, text, ws, index, group):
    """Polish `Panu` realizes the complete `in Dómino`, whose head names the Lord."""
    return (
        language == "pl"
        and text == PA + "tractus"
        and group == {"words": ["w086", "w087"], "anchor": "w087", "gloss": "Panu"}
        and [(w["id"], w["form"], w["lemma"]) for w in ws[index : index + 2]]
        == [("w086", "in", "in"), ("w087", "Dómino", "dominus")]
    )


def reverse_capitals(language, text):
    """Scope R-4 to lower-case Latin non-openings, not divine/name capitals."""
    doc, lay, out = core(text), layer(language, text), []
    allowed = (
        {
            "I",
            "He",
            "His",
            "Him",
            "Himself",
            "Me",
            "My",
            "You",
            "Your",
            "Yours",
            "Yourself",
            "God",
            "Lord",
            "Jesus",
            "Christ",
            "Judas",
            "Elijah",
        }
        if language == "en"
        else {
            "Ja",
            "On",
            "Jego",
            "Go",
            "Mu",
            "Nim",
            "Sam",
            "Ty",
            "Cię",
            "Ciebie",
            "Mnie",
            "Niego",
            "Tobie",
            "Twój",
            "Twoja",
            "Twoje",
            "Twoich",
            "Twojej",
            "Twojego",
            "Bóg",
            "Boga",
            "Pan",
            "Pana",
            "Jezus",
            "Chrystus",
        }
    )
    for seg in doc["segments"]:
        ws = seg.get("words", [])
        spans = {a["words"][0]: a for a in lay["segments"].get(seg["id"], {}).get("alignments", [])}
        prev, pending, i = ".", False, 0
        while i < len(ws):
            group = spans.get(ws[i]["id"])
            n = len(group["words"]) if group else 1
            first, last = ws[i], ws[i + n - 1]
            opens = pending or (
                prev.rstrip().endswith((".", ":", "?", "!")) and first["form"][:1].isupper()
            )
            gloss = group.get("gloss") if group else lay["words"][first["id"]].get("gloss")
            divine_group = tract_divine_group(language, text, ws, i, group)
            prev, i = last.get("post", ""), i + n
            if gloss is None:
                pending = opens
                continue
            pending = False
            if not opens and first["form"][:1].islower() and gloss:
                start = re.search(r"[^\W\d_]+", gloss, re.UNICODE)
                named = REVERSE_NAMED.get((language, text, first["id"])) == gloss
                if (
                    start
                    and start[0][:1].isupper()
                    and start[0] not in allowed
                    and not named
                    and not divine_group
                ):
                    out.append((seg["id"], first["id"], gloss))
    return out


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
    assert len(TEXTS) == len(set(TEXTS)) == 10
    assert set(TEXTS) == set(EXPECTED_TEXTS)
    for text in TEXTS:
        assert (ROOT / "texts" / (text.replace(".", "/", 1) + ".json")).exists()


def test_the_passion_reads_the_future_perfect_videris():
    text = PA + "evangelium"
    word = words(core(text))["w711"]
    assert (word["form"], word["post"], word["morph"]["tense"]) == ("víderis", ".", "futperf")
    assert "Quid ad nos? Tu víderis." in bodies(text)
    assert "# correction: 2026-10-11 the page prints Tu víderis. (p. 141" in witness(text)
    entry = next(e for e in apparatus(text) if e["at"] == "w711")
    assert (entry["ours"], entry["witnesses"], entry["class"]) == (
        "víderis.",
        {"do": "vidéris."},
        "accent",
    )
    clean(text)


def test_the_introit_declares_its_repetition_without_a_gloria_patri():
    text = PA + "introitus"
    assert (
        "the page prints the repeated antiphon as the cue Dómine, ne longe. and no Gloria Patri"
        in witness(text)
    )
    assert record(text)["orthography_profile"] == "page-body-with-declared-house-expansion"
    found = uses(text)
    assert "introit-expansion.mr1962" in found and "expanded-doxology.mr1962" not in found
    assert found["introit-expansion.mr1962"]["locator"]["section"] == "Rubricae generales 427–428"
    assert "Glória" not in [w["form"] for w in ordered(core(text))]
    clean(text)


@pytest.mark.parametrize("text", ORATIONS)
def test_the_conclusions_are_declared_composites(text):
    found = uses(text)
    kinds = ("middle", "rg115a", "terminal") + (("rg115b",) if text.endswith("collecta") else ())
    assert {key for key in found if "conclusion-" in key} == {
        f"conclusion-{kind}.mr1962" for kind in kinds
    }
    assert found["mr1962"]["decision"] == "RETAIN_WITH_CORRECTION"
    assert record(text)["orthography_profile"] == "exact-declared-composite"
    assert "Deus. Per ómnia sǽcula sæculórum. Amen." in bodies(text)[-1]
    lines = witness(text).splitlines()
    history = next(i for i, x in enumerate(lines) if x.startswith("# historical-recollated: "))
    assert "Rubricae generales p. xvii" in lines[history] and lines[history + 1] == XVII
    assert not any(x.startswith("# recollated: 2026-09-25 the Missal prints") for x in lines)
    assert (SAME_LORD if text.endswith("collecta") else CONCLUSION) in line("en", text)
    clean(text)


def test_the_collect_concludes_through_the_same_lord():
    text = PA + "collecta"
    assert line("en", text).endswith(SAME_LORD)
    claim = uses(text)["conclusion-rg115b.mr1962"]["claim"]
    assert "Salvatórem nostrum carnem súmere" in claim
    assert "Per eúndem Dóminum nostrum Iesum Christum" in bodies(text)[0]


def test_the_palm_sunday_printing_of_the_epistle_is_recorded():
    use = uses(EPISTLE)["palm-sunday-reprint.mr1962"]
    assert (use["role"], use["decision"]) == ("direct_approved_print", "RETAIN")
    assert use["locator"]["printed"] == "p. 138"
    assert use["locator"]["scan"] == "leaf n217 / PDF p. 218"
    for reading in ("exinanívit, formam", "flectátur cæléstium", "confiteátur quia"):
        assert reading in use["claim"]
    assert "hic genuflectitur in the line without parentheses" in use["claim"]
    assert layer("pl", EPISTLE)["about"].endswith(
        "Ta sama lekcja jest czytana w Niedzielę Palmową."
    )
    assert layer("en", EPISTLE)["about"].endswith("The same Epistle is read on Palm Sunday.")


def test_the_rulings_state_the_reading_and_the_decision():
    tract = next(e for e in apparatus(PA + "tractus") if e["at"] == "w100")
    assert tract["ruling"].startswith("The approved Benziger printing reads inspexérunt (p. 139)")
    for text in TEXTS:
        for entry in apparatus(text):
            assert not WORK_NOTE.search(entry["ruling"]), (text, entry["at"])
    gospel = {e["at"]: e for e in apparatus(PA + "evangelium")}
    for wid in ("w163", "w187", "w248", "w627", "w1169"):
        assert gospel[wid]["ruling"] == SPELLING_PUNCT


@pytest.mark.parametrize("text", sorted(PD))
def test_the_revised_english_names_its_historical_basis(text):
    (edition, key), printed, scan, change = PD[text]
    gospel = text.endswith("evangelium")
    sites = [s for s in provenance("en").values() if s["text"] == text]
    segments = [s["id"] for s in core(text)["segments"] if s["type"] == "verse"]
    assert sorted(s["segment"] for s in sites) == sorted(segments)
    assert all(s["origin"] == "public-domain" for s in sites)
    basis = [
        r for r in load("languages/en/translation-basis.json")["records"] if text in r["texts"]
    ]
    assert basis == [{"texts": [text], "segments": segments, "relationship": "revised"}]
    found = [
        u
        for u in load("languages/en/bibliography.json")["uses"]
        if u["id"] == f"use.en.{text}.body.{key}"
    ]
    assert len(found) == 1 and found[0]["edition"] == edition
    assert (found[0]["role"], found[0]["decision"]) == ("historical_wording_basis", "RETAIN")
    assert found[0]["address"] == (
        {"kind": "text", "text": text}
        if gospel
        else {"kind": "segment", "text": text, "segment": "s01"}
    )
    assert (found[0]["locator"]["printed"], found[0]["locator"]["scan"]) == (printed, scan)
    assert found[0]["evidence_sha256"] == SHA[key]
    assert change in found[0]["claim"]
    assert len(segments) == (94 if gospel else 1)


@pytest.mark.parametrize("text", TEXTS)
def test_the_english_verses_and_glosses_are_in_the_contemporary_register(text):
    for segment in layer("en", text)["segments"].values():
        assert not archaic(segment.get("translation")), (text, archaic(segment.get("translation")))
    assert not [g for g in glosses("en", text) if archaic(g)], text


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("text", TEXTS)
def test_every_sentence_opening_takes_a_capital(language, text):
    misses, examined = opening_check(language, text)
    assert examined > 0, (language, text, "no realized openings examined")
    assert misses == []


def served(monkeypatch, text, doc=None, **layers):
    """Serve edited copies of one text's documents in place of its files."""
    module, real_core, real_layer = sys.modules[__name__], core, layer
    monkeypatch.setattr(
        module, "core", lambda t: doc if doc is not None and t == text else real_core(t)
    )
    monkeypatch.setattr(
        module,
        "layer",
        lambda lang, t: layers[lang] if t == text and lang in layers else real_layer(lang, t),
    )


def caption(lay, word, value):
    edited = deepcopy(lay)
    edited["words"][word]["gloss"] = value
    return edited


def test_conclusion_relative_allowance_is_context_bound(monkeypatch):
    for text, words in CONCLUSION_RELATIVE.items():
        qui, doc, polish, english = words[0], core(text), layer("pl", text), layer("en", text)
        (where,) = [
            n for n, s in enumerate(doc["segments"]) if qui in [w["id"] for w in s["words"]]
        ]
        segment = doc["segments"][where]
        index = [w["id"] for w in segment["words"]].index(qui)
        before, word = segment["words"][index - 1 : index + 1]
        assert (before["post"], word["form"], word["lemma"]) == (":", "Qui", "qui")
        assert polish["words"][qui]["gloss"] == "który"
        (group,) = [
            a for a in english["segments"][segment["id"]]["alignments"] if qui in a["words"]
        ]
        assert group["words"] == words and group["gloss"].lower() == WHO_LIVES.lower()
        for language in ("pl", "en"):
            assert missed_openings(language, text) == []
        miss = [(segment["id"], qui, "który")]
        # Wrong language: the Polish allowance never covers an English caption.
        with monkeypatch.context() as patch:
            served(patch, text, en=polish)
            assert missed_openings("en", text) == miss
        # Identity: a capital or another relative form at the address is a miss.
        for wrong in ("Który", "którzy"):
            with monkeypatch.context() as patch:
                served(patch, text, pl=caption(polish, qui, wrong))
                assert missed_openings("pl", text) == [(segment["id"], qui, wrong)]
        # Clause boundary and changed Latin context: the reviewed context is `…: Qui`.
        for field, value, at in (
            ("post", ".", index - 1),
            ("form", "Quae", index),
            ("lemma", "quis", index),
        ):
            edited = deepcopy(doc)
            edited["segments"][where]["words"][at][field] = value
            with monkeypatch.context() as patch:
                served(patch, text, doc=edited)
                assert missed_openings("pl", text) == miss
        # Identity: the allowance never leaves its address. A Polish group or a missing caption
        # there is a miss; so is `który` at a `: Qui` one word later or in an untabled text.
        grouped = deepcopy(polish)
        following = segment["words"][index + 1]["id"]
        grouped["segments"][segment["id"]].setdefault("alignments", []).append(
            {"words": [qui, following], "anchor": qui, "gloss": "który"}
        )
        with monkeypatch.context() as patch:
            served(patch, text, pl=grouped)
            assert missed_openings("pl", text) == [(segment["id"], qui, "który")]
        with monkeypatch.context() as patch:
            served(patch, text, pl=caption(polish, qui, None))
            assert missed_openings("pl", text) == [(segment["id"], qui, None)]
        shifted = deepcopy(doc)
        shifted["segments"][where]["words"][index]["post"] = ":"
        shifted["segments"][where]["words"][index + 1].update({"form": "Qui", "lemma": "qui"})
        with monkeypatch.context() as patch:
            served(patch, text, doc=shifted, pl=caption(polish, following, "który"))
            assert missed_openings("pl", text) == [(segment["id"], following, "który")]
        unaligned = deepcopy(english)
        unaligned["segments"][segment["id"]]["alignments"] = [
            a for a in unaligned["segments"][segment["id"]]["alignments"] if a["words"][0] != qui
        ]
        for member, gloss in zip(
            words, (WHO_LIVES, "with You", "lives", "and", "reigns"), strict=True
        ):
            unaligned["words"][member] = {"gloss": gloss}
        with monkeypatch.context() as patch:
            served(patch, text, en=unaligned)
            assert missed_openings("en", text) == [(segment["id"], qui, WHO_LIVES)]
        # Actual initial: the conclusion served as its own segment opens with `Qui`.
        edited = deepcopy(doc)
        edited["segments"][where]["words"] = segment["words"][index:]
        with monkeypatch.context() as patch:
            served(patch, text, doc=edited)
            assert missed_openings("pl", text) == miss
        # English binding: only the exact group with the exact caption keeps its lower case.
        for shape in ("words", "gloss"):
            edited = deepcopy(english)
            (grp,) = [
                a for a in edited["segments"][segment["id"]]["alignments"] if a["words"][0] == qui
            ]
            grp["gloss"] = WHO_LIVES
            if shape == "words":
                grp["words"] = [*words, segment["words"][index + 5]["id"]]
            else:
                grp["gloss"] = WHO_LIVES.replace("You", "you")
            with monkeypatch.context() as patch:
                served(patch, text, en=edited)
                assert missed_openings("en", text) == [(segment["id"], qui, grp["gloss"])]
    # Identity across texts: a colon-initial direct speech elsewhere keeps its capital caption.
    gospel, site = PA + "evangelium", "w002"
    polish = layer("pl", gospel)
    assert polish["words"][site]["gloss"] == "Przyszedł"
    with monkeypatch.context() as patch:
        served(patch, gospel, pl=caption(polish, site, "przyszedł"))
        assert missed_openings("pl", gospel) == [("s01", site, "przyszedł")]
    assert missed_openings("pl", gospel) == []
    # The same adopted caption at a `: Qui` of a text outside this file's table is a miss here:
    # the allowance is bound to the table, and that text's caption is pinned by the relative suite.
    untabled = TWIN
    assert layer("pl", untabled)["words"]["w021"] == {"gloss": "który"}
    assert missed_openings("pl", untabled) == [("s01", "w021", "który")]


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("text", TEXTS)
def test_lower_case_latin_nonopenings_have_no_unwarranted_capital(language, text):
    assert reverse_capitals(language, text) == []


def test_divine_reverse_capital_exception_is_context_bound(monkeypatch):
    text = PA + "evangelium"
    assert reverse_capitals("pl", text) == []
    # Removing this one contextual allowance must expose the actual caption.
    # A global allowance for every Polish possessive would mask this control.
    with monkeypatch.context() as patch:
        patch.delitem(REVERSE_NAMED, ("pl", text, "w040"))
        assert reverse_capitals("pl", text) == [("s04", "w040", "Moja")]
    assert reverse_capitals("pl", text) == []


def test_tract_target_continuation_keeps_its_exact_context(monkeypatch):
    text, doc = PA + "tractus", core(PA + "tractus")
    for language, expected in (("pl", "ludowi"), ("en", "to the people")):
        lay = layer(language, text)
        assert missed_openings(language, text) == []
        for wrong in (expected.capitalize(), "another"):
            with monkeypatch.context() as patch:
                served(patch, text, **{language: caption(lay, "w142", wrong)})
                assert missed_openings(language, text) == [("s01", "w142", wrong)]
        for at, field, value in (
            (140, "post", ":"),
            (141, "form", "Pópulus"),
            (141, "lemma", "alius"),
        ):
            edited = deepcopy(doc)
            edited["segments"][0]["words"][at][field] = value
            with monkeypatch.context() as patch:
                served(patch, text, doc=edited)
                assert missed_openings(language, text) == [("s01", "w142", expected)]
        grouped = deepcopy(lay)
        grouped["segments"]["s01"]["alignments"].append(
            {"words": ["w142", "w143"], "anchor": "w142", "gloss": expected}
        )
        with monkeypatch.context() as patch:
            served(patch, text, **{language: grouped})
            assert missed_openings(language, text) == [("s01", "w142", expected)]
        initial = deepcopy(doc)
        initial["segments"][0]["words"] = initial["segments"][0]["words"][141:]
        with monkeypatch.context() as patch:
            served(patch, text, doc=initial)
            assert missed_openings(language, text) == [("s01", "w142", expected)]
        assert missed_openings(language, text) == []


def test_tract_divine_group_keeps_its_head_and_members(monkeypatch):
    text, doc = PA + "tractus", core(PA + "tractus")
    polish = layer("pl", text)
    assert reverse_capitals("pl", text) == []
    for at, field, value in ((85, "lemma", "ad"), (86, "form", "dómino"), (86, "lemma", "homo")):
        edited = deepcopy(doc)
        edited["segments"][0]["words"][at][field] = value
        with monkeypatch.context() as patch:
            served(patch, text, doc=edited)
            assert reverse_capitals("pl", text) == [("s01", "w086", "Panu")]
    for field, value in (
        ("anchor", "w086"),
        ("words", ["w086", "w087", "w088"]),
        ("gloss", "Ludowi"),
    ):
        edited = deepcopy(polish)
        (group,) = [g for g in edited["segments"]["s01"]["alignments"] if g["words"][0] == "w086"]
        group[field] = value
        with monkeypatch.context() as patch:
            served(patch, text, pl=edited)
            assert reverse_capitals("pl", text) == [("s01", "w086", group["gloss"])]
    assert reverse_capitals("pl", text) == []


def test_the_major_line_repairs_read_in_order():
    collect = line("en", PA + "collecta")
    assert "who | [for the human race] | to | imitate | [the example of humility]" in collect
    assert "[caused our Savior to take flesh and to undergo the Cross]" in collect
    epistle = line("en", EPISTLE)
    assert "but | [emptied Himself] | [taking the form of a servant]" in epistle
    assert "the Lord | Jesus | Christ | [is in the glory of God the Father]" in line(
        "en", EPISTLE, "s03"
    )
    offertory = line("en", PA + "offertorium")
    assert offertory.startswith("[My heart has expected reproach]")
    assert offertory.endswith("[they gave me vinegar to drink]")
    secret = line("en", PA + "secreta")
    assert "both | [may obtain for us the grace of devotion] | and" in secret
    assert "[may gain the fruit of blessed eternity]" in secret
    gospel = {s: line("en", PA + "evangelium", s) for s in ("s07", "s45", "s57", "s61", "s73")}
    assert gospel["s07"].endswith("and | says | to Peter")
    assert "[took counsel]" in gospel["s45"]
    assert "[Judas, who betrayed Him, seeing]" in gospel["s45"]
    assert "[to release to the people]" in gospel["s57"]
    assert "they should ask for | Barabbas | [but destroy Jesus]" in gospel["s61"]
    assert gospel["s73"].startswith("[But Pilate, seeing]")
    s77 = line("en", PA + "evangelium", "s77")
    assert "Jesus | however | scourged | he delivered" in s77
    assert "[bowing the knee]" in s77
    assert "[sprawiłeś, że nasz Zbawiciel przyjął ciało i poniósł krzyż]" in line(
        "pl", PA + "collecta"
    )
    assert (
        "[byli godni zarówno czerpać naukę z Jego cierpliwości, "
        "jak i uczestniczyć w Jego zmartwychwstaniu]"
    ) in line("pl", PA + "collecta")
    assert line("pl", PA + "introitus").count("[nie oddalaj daleko]") == 2
    assert "aby | prosił o | Barabasza" in line("pl", PA + "evangelium", "s61")
    assert "(0) | krwi | sprawiedliwego" in line("pl", PA + "evangelium", "s74")


def test_the_postcommunion_stays_the_twin_of_the_christmas_octave_postcommunion():
    for language in ("en", "pl"):
        twin, palm = layer(language, TWIN), layer(language, PA + "postcommunio")
        assert twin["segments"] == palm["segments"]
        assert twin["words"] == palm["words"]
        assert line(language, TWIN) == line(language, PA + "postcommunio")


def test_the_passion_names_elijah_and_jeremiah_and_the_elders():
    english = layer("en", PA + "evangelium")
    verses = " ".join(s.get("translation") or "" for s in english["segments"].values())
    glosses = [w.get("gloss") or "" for w in english["words"].values()] + [
        a.get("gloss") or "" for s in english["segments"].values() for a in s.get("alignments", [])
    ]
    for old in ("Elias", "Jeremias", "Caiphas", "ancients", "monument"):
        assert old not in verses and not any(old in g for g in glosses)
    assert "Jeremiah" in english["segments"]["s51"]["translation"]
    assert line("en", PA + "evangelium", "s88") == "[This man calls Elijah]"
    assert "[Elijah will come]" in line("en", PA + "evangelium", "s90")


def test_the_same_latin_reads_alike_in_polish():
    introit = layer("pl", PA + "introitus")["segments"]["s01"]["translation"]
    tract = layer("pl", PA + "tractus")["segments"]["s01"]["translation"]
    for phrase in (
        "Boże, Boże mój, wejrzyj na mnie",
        "czemuś mnie opuścił? Daleko od mego wybawienia są słowa grzechów moich.",
        "a od rogów jednorożców moje uniżenie",
    ):
        assert phrase in introit and phrase in tract
    communion = layer("pl", PA + "communio")["segments"]["s01"]["translation"]
    passion = layer("pl", PA + "evangelium")["segments"]["s10"]["translation"]
    assert communion.startswith("Ojcze, ")
    assert passion == "Ojcze Mój, " + communion.removeprefix("Ojcze, ")


def test_the_changed_communion_verses_withdraw_the_earlier_review():
    for language in ("en", "pl"):
        site = provenance(language)[f"{PA}communio.s01.{language}"]
        assert site["review"] == "working"


COMPOSITES = {
    PA + "collecta": (
        "# composite: w001–w033 from p. 138, the body through the cue words Per eúndem Dóminum; "
        "w034–w048 from p. 123, nostrum through Deus.; w049–w053 from p. 226, Per ómnia sǽcula "
        "sæculórum and Amen",
        "# expansion: RG 115 a–b governs the Father-addressed conclusions; the cues on p. 138 are "
        "completed by the printed middle and terminal formulae",
    ),
    PA + "secreta": (
        "# composite: w001–w021 from p. 143, the body through the cue words Per Dóminum; w022–w036 "
        "from p. 123, nostrum through Deus.; w037–w041 from p. 226, Per ómnia sǽcula sæculórum and "
        "Amen",
        "# expansion: RG 115 a governs the Father-addressed conclusions; the cues on p. 143 are "
        "completed by the printed middle and terminal formulae",
    ),
    PA + "postcommunio": (
        "# composite: w001–w015 from p. 143, the body through the cue words Per Dóminum; w016–w030 "
        "from p. 123, nostrum through Deus.; w031–w035 from p. 226, Per ómnia sǽcula sæculórum and "
        "Amen",
        "# expansion: RG 115 a governs the Father-addressed conclusions; the cues on p. 143 are "
        "completed by the printed middle and terminal formulae",
    ),
}


@pytest.mark.parametrize("text", ORATIONS)
def test_the_composite_seams_are_declared_word_by_word(text):
    lines = witness(text).splitlines()
    for expected in COMPOSITES[text]:
        assert expected in lines, (text, expected[:40])


def test_the_introit_declares_the_range_of_its_repetition():
    text = PA + "introitus"
    assert "w040–w062 repeat the antiphon under RG 427, p. xxix, leaf n34" in witness(text)
    dependencies = record(text)["source_dependencies"]
    assert dependencies == {"uses": [f"use.{text}.introit-expansion.mr1962"], "raw_binding": None}


def test_the_reverse_cases_zeros_and_openings_of_the_repairs_stay():
    for language, expected in (("pl", "daleko"), ("en", "far")):
        assert layer(language, PA + "introitus")["words"]["w033"]["gloss"] == expected
    gospel = {lang: layer(lang, PA + "evangelium") for lang in ("pl", "en")}
    for language in ("pl", "en"):
        zeros = [
            a for a in gospel[language]["segments"]["s43"]["alignments"] if a["words"] == ["w597"]
        ]
        assert zeros == [{"words": ["w597"], "reason": "punctuation"}], language
    for wid in ("w512", "w563", "w704", "w939"):
        assert gospel["pl"]["words"][wid]["gloss"] == "A", wid
    for language in ("pl", "en"):
        assert [
            a for a in gospel[language]["segments"]["s82"]["alignments"] if a["words"] == ["w1253"]
        ] == [{"words": ["w1253"], "reason": "punctuation"}]
    assert "[przykładu pokory]" in line("pl", PA + "collecta")
    assert line("en", PA + "graduale").startswith("You have held | [my right hand]")


def test_the_challenge_repairs_stay():
    assert (
        "my steps had almost slipped"
        in layer("en", PA + "graduale")["segments"]["s01"]["translation"]
    )
    tract = layer("en", PA + "tractus")["segments"]["s01"]["translation"]
    assert "But they themselves considered and looked closely at me" in tract
    gospel = layer("en", PA + "evangelium")["segments"]
    assert gospel["s46"]["translation"] == "I have sinned in betraying righteous blood."
    assert line("en", PA + "evangelium", "s46").endswith("[righteous blood]")
    assert "hanged himself with a noose" in gospel["s49"]["translation"]
    assert layer("en", PA + "evangelium")["words"]["w1243"]["gloss"] == "He trusts"
    assert layer("en", PA + "tractus")["words"]["w019"]["gloss"] == "I will cry"
    assert layer("en", EPISTLE)["words"]["w072"]["gloss"] == "should be bent"
    phrase = "obedient | [to the point of] | death | [even death] | of the Cross"
    assert phrase in line("en", EPISTLE)
    origins = {
        lang: provenance(lang)[f"{PA}communio.s01.{lang}"]["origin"] for lang in ("en", "pl")
    }
    # Held as unsettled working wording since the 2026-10-20 relabel (second round).
    assert origins["en"] == "working-unsettled"
    assert origins["pl"] == provenance("pl")[f"{PA}evangelium.s10.pl"]["origin"]


@pytest.mark.parametrize("old", ["answerest", "destroyest", "dwellest", "thinkest", "givest"])
def test_the_named_second_person_inflections_are_detected(old):
    assert archaic(old)
    assert archaic("You " + old)


@pytest.mark.parametrize(
    "modern",
    [*sorted(MODERN_ETH), "You trust", "You harvest", "You manifest", "You are the greatest"],
)
def test_modern_words_with_similar_suffixes_are_not_archaisms(modern):
    assert not archaic(modern)


def test_the_only_shall_gloss_is_the_deliberative_question():
    found = []
    for text in TEXTS:
        lay = layer("en", text)
        for wid, word in lay["words"].items():
            if re.search(r"\bshall\b", word.get("gloss") or "", re.I):
                found.append((text, wid, word["gloss"]))
        for sid, segment in lay["segments"].items():
            for group in segment.get("alignments", []):
                if re.search(r"\bshall\b", group.get("gloss") or "", re.I):
                    found.append((text, sid, group["gloss"]))
    assert found == [(PA + "evangelium", "w948", "shall I do")]


MR_LEAVES = {
    "n22": (
        "p. xvii",
        "leaf n22 / PDF p. 23",
        "b511f3aa4016b387d2995b5089e15aa62593c04118052ef48dcc09352fcf769c",
    ),
    "n23": (
        "p. xviii",
        "leaf n23 / PDF p. 24",
        "db99d725287dbdb233ff9c22c94cd027ec6b5105f2f64817ec828778805ff132",
    ),
    "n34": (
        "p. xxix",
        "leaf n34 / PDF p. 35",
        "7f1d0a363ab6d032183595433acb393de3e473dc34e95135467e0c7c1d5c9786",
    ),
    "n202": (
        "p. 123",
        "leaf n202 / PDF p. 203",
        "38c3d082c3cf4e7f82f87cf9f87595e62e3765cb625c1305005f1435cc985774",
    ),
    "n217": (
        "p. 138",
        "leaf n217 / PDF p. 218",
        "208d04db09fd578f7fcd747a546f0f11391554052aea4ae35a1381a07b74d9d3",
    ),
    "n222": (
        "p. 143",
        "leaf n222 / PDF p. 223",
        "347dd33f84415852a4e6ce5ed13928fde842752025ce60d4d0f57362b7df8abd",
    ),
    "n305": (
        "p. 226",
        "leaf n305 / PDF p. 306",
        "c8a123467dd47ace390100a021fdcdd61752a5c42635583b92d72cd636027f58",
    ),
}
MIDDLE_CLAIM = (
    "This separate Postcommunion prints the accented conclusion with no comma after Christum "
    "and the colon and uppercase Qui after tuum, ending with Deus. The composite uses the "
    "passage from nostrum through “Deus.”; the cue words {cue} come from p. {page}, and this "
    "page supplies neither the final duration nor Amen."
)


def mr_binding(text, key, leaf, word=None):
    use = uses(text)[key]
    assert use["address"] == (
        {"kind": "text", "text": text}
        if word is None
        else {"kind": "word", "text": text, "word": word}
    )
    printed, scan, digest = MR_LEAVES[leaf]
    assert (use["locator"]["printed"], use["locator"]["scan"], use["evidence_sha256"]) == (
        printed,
        scan,
        digest,
    )
    assert (
        use["locator"]["page_url"]
        == f"https://archive.org/details/missale-romanum-1962/page/{leaf}/mode/1up"
    )
    return use


@pytest.mark.parametrize(
    "part,middle,rg,terminal",
    [
        ("collecta", "w034", "w031", "w049"),
        ("secreta", "w022", "w020", "w037"),
        ("postcommunio", "w016", "w014", "w031"),
    ],
)
def test_the_declared_conclusion_uses_bind_their_actual_loci(part, middle, rg, terminal):
    text = PA + part
    collect = part == "collecta"
    mr_binding(text, "mr1962", "n217" if collect else "n222")
    use = mr_binding(text, "conclusion-middle.mr1962", "n202", middle)
    # A literal bounded regression for the visually adjudicated claim, not an
    # automated inference that arbitrary source prose is true.
    assert use["claim"] == MIDDLE_CLAIM.format(
        cue="Per eúndem Dóminum" if collect else "Per Dóminum", page="138" if collect else "143"
    )
    mr_binding(text, "conclusion-rg115a.mr1962", "n22", rg)
    mr_binding(text, "conclusion-terminal.mr1962", "n305", terminal)
    if collect:
        mr_binding(text, "conclusion-rg115b.mr1962", "n23", rg)


def test_the_other_added_print_uses_bind_their_actual_loci():
    mr_binding(PA + "introitus", "introit-expansion.mr1962", "n34")
    mr_binding(EPISTLE, "palm-sunday-reprint.mr1962", "n217")


@pytest.mark.parametrize(
    "text,segment,start,end,anchor",
    [
        (PA + "communio", "s01", 3, 7, 4),
        (PA + "evangelium", "s10", 120, 124, 121),
    ],
)
def test_the_conditional_chalice_predicate_is_not_inverted(text, segment, start, end, anchor):
    group = next(
        a
        for a in layer("en", text)["segments"][segment]["alignments"]
        if a["words"] == [f"w{i:03d}" for i in range(start, end + 1)]
    )
    assert group["anchor"] == f"w{anchor:03d}"
    assert group["gloss"] == "this chalice cannot pass away"


def test_the_collect_complete_coordinated_predicate_stays():
    for language, expected in (
        ("en", "we may be worthy both to learn from His patience and to share in His resurrection"),
        (
            "pl",
            "byli godni zarówno czerpać naukę z Jego cierpliwości, "
            "jak i uczestniczyć w Jego zmartwychwstaniu",
        ),
    ):
        group = next(
            a
            for a in layer(language, PA + "collecta")["segments"]["s01"]["alignments"]
            if a["words"] == [f"w{i:03d}" for i in range(22, 31)]
        )
        assert (group["anchor"], group["gloss"]) == ("w030", expected)


def test_the_polish_communion_origin_tracks_its_passion_twin():
    # Settlement can change this common value; changing only one twin cannot.
    sites = provenance("pl")
    assert sites[f"{PA}communio.s01.pl"]["origin"] == sites[f"{PA}evangelium.s10.pl"]["origin"]
