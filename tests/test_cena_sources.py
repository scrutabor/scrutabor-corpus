"""Holy Thursday as the approved Benziger printing has it, with the English that names its
historical basis and the interlinear lines that read in English and Polish order.

The Introit's repeated antiphon is a declared expansion of the printed cue, with no Gloria Patri
(Rubricae generales 427–428). The Collect and the Secret complete their *Qui tecum* cue with the
formula of Rubricae generales 115 c, and the Postcommunion its *Per Dóminum nostrum* cue with page
123 and page 226; the witnesses declare each locus. Holy Thursday prints the Gradual of the
Exaltation of the Cross (with a colon after *illum*), the Offertory of the third Sunday after
Epiphany and its own Communion a second time, and uses record each printing. The English revised
from *The Missal for the Laity* (1846) or Husenbeth's *Missal for the Use of the Laity* (1853)
names its basis. *Cena facta* reads "during supper" in both languages, with a word explanation.
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
CE = "proprium.feria-v-in-cena-domini-"
GRADUAL = "proprium.exaltatio-sanctae-crucis-graduale"
OFFERTORY = "proprium.dominica-iii-post-epiphaniam-offertorium"
EPISTLE_OF_THE_CROSS = "proprium.exaltatio-sanctae-crucis-epistola"
TEXTS = [
    CE + "introitus",
    CE + "collecta",
    CE + "epistola",
    GRADUAL,
    CE + "evangelium",
    OFFERTORY,
    CE + "secreta",
    CE + "communio",
    CE + "postcommunio",
]
LAITY = ("edition.the-missal-for-the-laity-1846", "laity1846")
HUSENBETH = ("edition.the-missal-for-the-use-of-the-laity-1853", "husenbeth1853")
SHA = {
    "laity1846": "8e692b256e08350896902e55787f70c171a444d33e754f4d67e84fe000f81dd1",
    "husenbeth1853": "64dda22f4b0753135be1112b8bd36eab7fbb9c92586c2fc2d831c0a4b7f65d8a",
}
PD = {
    CE + "collecta": (HUSENBETH, "p. 281", "scan p. 308", "tuæ propitiatiónis efféctum"),
    CE + "epistola": (LAITY, "pp. 314–315", "scan pp. 330–331", "the new covenant"),
    CE + "evangelium": (LAITY, "pp. 315–316", "scan pp. 331–332", "during supper (cena facta)"),
    CE + "communio": (LAITY, "pp. 316–317", "scan pp. 332–333", "ut et vos ita faciátis"),
}
RG_LITERAL = (
    "Qui tecum vivit et regnat in unitate Spiritus Sancti, Deus, per omnia sæcula sæculorum. Amen;"
)
RG_COMMA = (
    "The comma follows the full formula in RG115c, not the abbreviated proper-page cue. "
    "The digital macro omits it."
)
QUI_TECUM = "[who lives and reigns with You] | in | the unity | [of the Holy Spirit] | God"
CONCLUSION = (
    "Through | [our Lord] | [Jesus Christ] | [Your Son] | [who lives and reigns with You] | in | "
    "the unity | [of the Holy Spirit] | God | [forever and ever]"
)
XVII = (
    "# correction: 2026-10-11 p. xvii (Rubricae generales 115 a, leaf n22) prints this formula "
    "unaccented as Filium tuum, qui tecum vivit: no comma after Christum, but a comma and a "
    "lower-case qui after tuum, so it does not attest the colon form; the colon and the upper-case "
    "Qui of this composite follow p. 123, leaf n202"
)
ACCENT = (
    "The selected accentuation follows the approved Benziger printing. The pinned digital reading "
    "is recorded exactly; the word is the same."
)
SPELLING_PUNCT = (
    "The selected spelling and punctuation follow the approved Benziger printing. The pinned "
    "digital spelling and any accompanying punctuation are recorded exactly; both readings "
    "represent the same word."
)
WORK_NOTE = re.compile(
    r"\b(?:MR|DO)\b|full\d|Do not diagnose|really has|[Rr]etain the|Preserve both"
)
ARCHAIC = re.compile(
    r"\b(thee|thou|thy|thine|hath|doth|ye|unto|saith|shalt|wilt|didst|art|hast|dost|whence|"
    r"knowest|washest|sayest|seest|goest|comest|wouldst|couldst|shouldst|canst|hadst|wast|"
    r"whosoever|for ever|[a-z]+eth)\b",
    re.I,
)
ETH_NAMES = {"nazareth", "elizabeth", "teeth", "seth", "japheth"}
COMPOSITE = (
    "# composite: w001–w020 from pp. 162–163, the body through the cue words Per Dóminum nostrum; "
    "w021–w034 from p. 123, Iesum through Deus.; w035–w039 from p. 226, Per ómnia sǽcula sæculórum "
    "and Amen"
)
EXPANSION = (
    "# expansion: RG 115 a governs the Father-addressed conclusions; the cue on pp. 162–163 is "
    "completed by the printed middle and terminal formulae"
)
ASSEMBLY = (
    "# assembly: printed proper ends Qui tecum. Its abbreviation is replaced by the full formula "
    "explicitly prescribed in RG115c. This is a composite of two loci, not one continuous printed "
    "passage."
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
    return {entry["at"]: entry for entry in load(f"witnesses/{text}/apparatus.json")["adjudicated"]}


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
    return [w for w in ARCHAIC.findall(string or "") if w.lower() not in ETH_NAMES]


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
    CE + "collecta": [f"w{i:03d}" for i in range(43, 48)],
    CE + "secreta": [f"w{i:03d}" for i in range(31, 36)],
    CE + "postcommunio": [f"w{i:03d}" for i in range(25, 30)],
}
# Polish follows its own sentences: the prose of the Secret and of the Postcommunion continues
# at the relative (`…, który z Tobą żyje …`) and keeps the reviewed lowercase caption; the
# Collect's prose opens a new sentence (`… zmartwychwstania. Który z Tobą żyje …`), so its
# caption takes the capital under the plain opening rule, as its English caption does.
POLISH_CONTINUING = (CE + "secreta", CE + "postcommunio")
WHO_LIVES = "who lives and reigns with You"


def conclusion_relative(language, text, index, prev, first, group, gloss):
    """None away from a reviewed conclusion address, or when its Latin context changed (then the
    plain opening rule decides); otherwise whether the caption has the one reviewed shape.
    English: the exact five-word group `who lives and reigns with You` keeps its lower case, and
    any other caption falls back to the plain rule. Polish: where the prose continues the
    sentence (POLISH_CONTINUING), the unaligned relative `Qui` after the Latin colon must read
    `który`, so a capital, another form or a group there is a miss; where the prose opens a new
    sentence, the plain rule decides."""
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
        if text not in POLISH_CONTINUING:
            return None
        return group is None and gloss == "który"
    if language == "en":
        exempt = group is not None and group["words"] == words and gloss == WHO_LIVES
        return True if exempt else None
    return None


def missed_openings(language, text):
    """Latin capitals after a stop (or a segment's first word) whose realized gloss starts lower
    case, except the reviewed conclusion relative (`conclusion_relative`), which must read as
    reviewed in either language."""
    doc, lay, out = core(text), layer(language, text), []
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
            prev, i = last.get("post", ""), i + n
            if gloss is None and reviewed is not False:
                pending = opens
                continue
            pending = False
            if reviewed is False or (reviewed is None and opens and gloss[:1].islower()):
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


def verse(language, text, segment="s01"):
    return layer(language, text)["segments"][segment]["translation"]


def test_the_texts_list_is_complete():
    assert len(TEXTS) == 9
    components = load("formularies/temporale/feria-v-in-cena-domini.json")["components"]
    assert [c["text"] for c in components if c["text"] in TEXTS] == TEXTS


def test_the_introit_declares_its_repetition_without_a_gloria_patri():
    text = CE + "introitus"
    assert (
        "the page prints the repeated antiphon as the cue Nos autem. and no Gloria Patri"
        in witness(text)
    )
    assert record(text)["orthography_profile"] == "page-body-with-declared-house-expansion"
    found = uses(text)
    assert found["introit-expansion.mr1962"]["locator"]["section"] == "Rubricae generales 427–428"
    assert "w039–w062 repeat the antiphon under RG 427, p. xxix, leaf n34" in witness(text)
    dependencies = record(text)["source_dependencies"]
    assert dependencies == {"uses": [f"use.{text}.introit-expansion.mr1962"], "raw_binding": None}
    assert "Glória" not in [w["form"] for w in ordered(core(text))]
    clean(text)


@pytest.mark.parametrize("text", [CE + "collecta", CE + "secreta"])
def test_the_qui_tecum_conclusions_are_declared_composites(text):
    found = uses(text)
    assert found["mr1962"]["decision"] == "RETAIN_WITH_CORRECTION"
    assert found["conclusion-rg115c.mr1962"]["locator"]["printed"] == "p. xviii"
    assert record(text)["orthography_profile"] == "exact-multi-locus-transcription"
    assert bodies(text)[-1].endswith(RG_LITERAL)
    assert "RG115c printed xviii, n23 / PDF24 (supplied full conclusion)" in witness(text)
    assert ASSEMBLY in witness(text).splitlines()
    entries = apparatus(text)
    commas = [e for e in entries.values() if e["ruling"] == RG_COMMA]
    assert [e["ours"] for e in commas] == ["Sancti,", "Deus,"]
    assert [e["witnesses"] for e in entries.values() if e["class"] == "accent"] == [
        {"mr": "unitate"},
        {"mr": "Spiritus"},
        {"mr": "omnia"},
        {"mr": "sæcula"},
        {"mr": "sæculorum."},
    ]
    english = line("en", text)
    assert QUI_TECUM.lower() in english.lower()
    assert "liveth" not in english and "Thee" not in english
    clean(text)


def test_the_collect_concludes_in_a_new_sentence_and_the_secret_in_the_same():
    collect = line("en", CE + "collecta")
    assert collect.endswith(
        "[may He bestow the grace of His resurrection] | "
        "[Who lives and reigns with You] | in | the unity | "
        "[of the Holy Spirit] | God | [forever and ever]"
    )
    assert verse("en", CE + "collecta").endswith(
        "the grace of His resurrection. Who lives and reigns with You in the unity of the Holy "
        "Spirit, God, forever and ever."
    )
    secret = verse("en", CE + "secreta")
    assert secret.endswith(
        "Jesus Christ, Your Son, our Lord, who lives and reigns with You in the unity of the Holy "
        "Spirit, God,"
    )
    assert line("en", CE + "secreta", "s02") == "[forever and ever]"


def test_the_postcommunion_completes_its_cue_from_pages_123_and_226():
    text = CE + "postcommunio"
    found = uses(text)
    assert {key for key in found if "conclusion-" in key} == {
        "conclusion-middle.mr1962",
        "conclusion-rg115a.mr1962",
        "conclusion-terminal.mr1962",
    }
    assert found["conclusion-middle.mr1962"]["address"]["word"] == "w021"
    assert record(text)["orthography_profile"] == "exact-declared-composite"
    assert bodies(text)[-1].endswith(
        "Per Dóminum nostrum Iesum Christum Fílium tuum: Qui tecum vivit et regnat in unitáte "
        "Spíritus Sancti, Deus. Per ómnia sǽcula sæculórum. Amen."
    )
    assert "# location: printed pp. 162–163, xvii, 123, 226; leaves n241–n242" in witness(text)
    assert COMPOSITE in witness(text).splitlines() and EXPANSION in witness(text).splitlines()
    lines = witness(text).splitlines()
    history = next(i for i, x in enumerate(lines) if x.startswith("# historical-recollated: "))
    assert "Rubricae generales p. xvii" in lines[history] and lines[history + 1] == XVII
    assert line("en", text).endswith(CONCLUSION)
    clean(text)


def test_the_holy_thursday_printings_are_recorded():
    gradual = uses(GRADUAL)["cena-domini-reprint.mr1962"]
    assert (gradual["role"], gradual["locator"]["printed"]) == ("direct_approved_print", "p. 158")
    assert "exaltávit illum : et dedit" in gradual["claim"]
    offertory = uses(OFFERTORY)["cena-domini-reprint.mr1962"]
    assert offertory["locator"]["printed"] == "p. 161"
    assert "identical in letters, accents and punctuation to page 46" in offertory["claim"]
    communion = uses(CE + "communio")["lotio-pedum-reprint.mr1962"]
    assert communion["locator"]["printed"] == "p. 159"
    assert "third antiphon" in communion["claim"]
    assert layer("pl", GRADUAL)["about"].endswith(
        "Ten sam śpiew jest używany w formularzu Wielkiego Czwartku."
    )
    assert layer("en", OFFERTORY)["about"].endswith(
        "The same chant is used in the formularies of the Fourth, Fifth and Sixth Sundays after "
        "Epiphany and of Holy Thursday."
    )


@pytest.mark.parametrize(
    "text,pairs", [(CE + "epistola", 2), (CE + "evangelium", 7), (CE + "communio", 1)]
)
def test_the_witnesses_declare_the_quotation_marks_they_omit(text, pairs):
    header = [x for x in witness(text).splitlines() if x.startswith("# normalization: ")]
    assert len(header) == 1 and f"({pairs} pair" in header[0]
    assert not any(mark in "".join(bodies(text)) for mark in '"“”')
    clean(text)


def test_the_rulings_state_the_reading_and_the_decision():
    gospel, epistle = apparatus(CE + "evangelium"), apparatus(CE + "epistola")
    assert gospel["w006"]["ruling"] == SPELLING_PUNCT
    for entry in (gospel["w074"], apparatus(CE + "communio")["w022"]):
        assert (entry["class"], entry["ruling"]) == ("accent", ACCENT)
    for entry in (epistle["w020"], epistle["w177"], apparatus(OFFERTORY)["w004"]):
        assert entry["ruling"] == ACCENT
    for text in TEXTS:
        for entry in apparatus(text).values():
            assert not WORK_NOTE.search(entry["ruling"]), (text, entry["at"])
            if "capital typography" in entry["ruling"]:
                assert entry["ours"][0].isupper(), (text, entry["at"])


def test_the_participle_of_saying_belongs_to_the_main_clause():
    epistle = words(core(CE + "epistola"))
    assert epistle["w099"]["form"] == "dicens"
    assert epistle["w099"]["head"] == epistle["w074"]["head"] == "w065"


def test_cena_facta_reads_during_supper_in_both_languages():
    text = CE + "evangelium"
    assert core(text)["localization"]["explanations"] == {"w031": {}}
    assert "[during supper]" in line("en", text)
    assert "[podczas wieczerzy]" in line("pl", text)
    for language in ("en", "pl"):
        explanation = layer(language, text)["words"]["w031"]["explanation"]
        assert (
            "meal having been prepared and served"
            if language == "en"
            else "przygotowania i podania posiłku"
        ) in explanation
        assert (
            "traditional “after supper” interpretation is also possible"
            if language == "en"
            else "Możliwe jest również tradycyjne odczytanie „po wieczerzy”"
        ) in explanation
    assert "And during supper, when the devil" in verse("en", text)


@pytest.mark.parametrize("text", sorted(PD))
def test_the_revised_english_names_its_historical_basis(text):
    (edition, key), printed, scan, change = PD[text]
    site = provenance("en")[f"{text}.s01.en"]
    assert (site["origin"], site["review"]) == ("public-domain", "working")
    basis = [
        r for r in load("languages/en/translation-basis.json")["records"] if text in r["texts"]
    ]
    assert basis == [{"texts": [text], "segments": ["s01"], "relationship": "revised"}]
    found = [
        u
        for u in load("languages/en/bibliography.json")["uses"]
        if u["id"] == f"use.en.{text}.body.{key}"
    ]
    assert len(found) == 1 and found[0]["edition"] == edition
    assert found[0]["address"] == {"kind": "segment", "text": text, "segment": "s01"}
    assert (found[0]["locator"]["printed"], found[0]["locator"]["scan"]) == (printed, scan)
    assert found[0]["evidence_sha256"] == SHA[key]
    assert change in found[0]["claim"]


@pytest.mark.parametrize("text", TEXTS)
def test_the_english_verses_and_glosses_are_in_the_contemporary_register(text):
    for segment in layer("en", text)["segments"].values():
        assert not archaic(segment.get("translation")), (text, archaic(segment.get("translation")))
    assert not [g for g in glosses("en", text) if archaic(g)], text


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("text", TEXTS)
def test_every_sentence_opening_takes_a_capital(language, text):
    assert missed_openings(language, text) == []


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


def polish_allowance_is_bound(monkeypatch, text, doc, polish, where, index):
    """The reviewed lowercase `który` where the Polish prose continues its sentence: the
    allowance is bound to its language, caption, `…: Qui` context, address and table."""
    segment = doc["segments"][where]
    qui = segment["words"][index]["id"]
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
    # Actual initial: the conclusion served as its own segment opens with `Qui`.
    edited = deepcopy(doc)
    edited["segments"][where]["words"] = segment["words"][index:]
    with monkeypatch.context() as patch:
        served(patch, text, doc=edited)
        assert missed_openings("pl", text) == miss


def polish_opening_takes_the_capital(monkeypatch, text, polish, segment, index):
    """Where the Polish prose opens a new sentence at the relative, the plain opening rule
    decides: the capital passes, and a lowercase relative, another lowercase form, a lowercase
    group or a missing caption that passes the opening to the next caption is a miss."""
    qui, following = segment["words"][index]["id"], segment["words"][index + 1]["id"]
    for wrong in ("który", "którzy"):
        with monkeypatch.context() as patch:
            served(patch, text, pl=caption(polish, qui, wrong))
            assert missed_openings("pl", text) == [(segment["id"], qui, wrong)]
    grouped = deepcopy(polish)
    grouped["segments"][segment["id"]].setdefault("alignments", []).append(
        {"words": [qui, following], "anchor": qui, "gloss": "który"}
    )
    with monkeypatch.context() as patch:
        served(patch, text, pl=grouped)
        assert missed_openings("pl", text) == [(segment["id"], qui, "który")]
    with monkeypatch.context() as patch:
        served(patch, text, pl=caption(polish, qui, None))
        assert missed_openings("pl", text) == [
            (segment["id"], following, polish["words"][following]["gloss"])
        ]


def test_conclusion_relative_allowance_is_context_bound(monkeypatch):
    assert [text for text in CONCLUSION_RELATIVE if text not in POLISH_CONTINUING] == [
        CE + "collecta"
    ]
    for text, words in CONCLUSION_RELATIVE.items():
        qui, doc, polish, english = words[0], core(text), layer("pl", text), layer("en", text)
        (where,) = [
            n for n, s in enumerate(doc["segments"]) if qui in [w["id"] for w in s["words"]]
        ]
        segment = doc["segments"][where]
        index = [w["id"] for w in segment["words"]].index(qui)
        before, word = segment["words"][index - 1 : index + 1]
        assert (before["post"], word["form"], word["lemma"]) == (":", "Qui", "qui")
        continuing = text in POLISH_CONTINUING
        assert polish["words"][qui]["gloss"] == ("który" if continuing else "Który")
        (group,) = [
            a for a in english["segments"][segment["id"]]["alignments"] if qui in a["words"]
        ]
        assert group["words"] == words and group["gloss"].lower() == WHO_LIVES.lower()
        for language in ("pl", "en"):
            assert missed_openings(language, text) == []
        if continuing:
            polish_allowance_is_bound(monkeypatch, text, doc, polish, where, index)
        else:
            polish_opening_takes_the_capital(monkeypatch, text, polish, segment, index)
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
    gospel, site = CE + "evangelium", "w155"
    polish = layer("pl", gospel)
    assert polish["words"][site]["gloss"] == "Kto"
    with monkeypatch.context() as patch:
        served(patch, gospel, pl=caption(polish, site, "kto"))
        assert missed_openings("pl", gospel) == [("s01", site, "kto")]
    assert missed_openings("pl", gospel) == []
    # The same adopted caption at a `: Qui` of a text outside this file's table is a miss here:
    # the allowance is bound to the table, and that text's caption is pinned by the relative suite.
    untabled = "proprium.dominica-ii-passionis-collecta"
    assert layer("pl", untabled)["words"]["w039"] == {"gloss": "który"}
    assert missed_openings("pl", untabled) == [("s01", "w039", "który")]


def test_the_major_line_repairs_read_in_order():
    epistle = line("en", CE + "epistola")
    assert "[Do you not have houses] | for | eating | and | drinking" in epistle
    assert "[But let a man examine himself]" in epistle
    assert "This | chalice | [is the new covenant] | in | My | blood" in epistle
    assert epistle.count("[in commemoration of Me]") == 2
    gospel = line("en", CE + "evangelium")
    assert "[Jesus, knowing] | that | [His hour had come]" in gospel
    assert "that | [the Father had given all things into His hands]" in gospel
    assert "He who | [has bathed] | [needs only to wash his feet]" in gospel
    collect = line("en", CE + "collecta")
    pair = (
        "[both Judas received the punishment of his guilt "
        "and the thief the reward of his confession]"
    )
    assert pair in collect
    assert "[the fruit of Your mercy]" in collect
    assert "abyśmy | [z tym światem nie zostali potępieni]" in line("pl", CE + "epistola")
    assert "[Gdy schodzicie się]" in line("pl", CE + "epistola")
    assert "[działania Twojej łaskawości]" in line("pl", CE + "collecta")


def test_the_words_of_institution_read_as_in_the_passion_sunday_communion():
    english = verse("en", CE + "epistola")
    assert "This chalice is the new covenant in My blood" in english
    assert english.count("in commemoration of Me") == 2
    passion = verse("en", "proprium.dominica-i-passionis-communio")
    assert "the new covenant in My blood" in passion and "in commemoration of Me" in passion


def test_phil_2_8_reads_alike_in_the_gradual_and_the_epistle_of_the_cross():
    phrase = "obedient | [to the point of] | death | [even death] | of the Cross"
    assert phrase in line("en", GRADUAL)
    assert phrase in line("en", EPISTLE_OF_THE_CROSS)


def test_the_polish_introit_gives_in_quo_its_referent():
    polish = verse("pl", CE + "introitus")
    assert polish.count("Jezusa Chrystusa: w Nim jest nasze zbawienie") == 2
    assert "w którym" not in polish
