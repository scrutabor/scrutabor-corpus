"""Saint Joseph the Worker: word captions, groups, verses, notes, the Gospel's printed quotation
marks, the English provenance of the Introit and Communion, and the dominatio card.

Finite reviewed addresses and contexts, not general rules. Every outcome is pinned by a positive
check, and each check is shown to reject a named defect (usually the predecessor value). The
Preface of St Joseph exists twice with identical wording apart from its feast word
(Solemnitáte for 1 May, Festivitáte for 19 March); both bodies carry the same corrections.
"""

import json
import re
import shutil
from copy import deepcopy
from functools import cache
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest
from provenance_successor_fixture import assert_protection_scope

from build_reader import store
from build_reader.bibliography_bindings import digest, selected_text, transcript_digest
from checks import english, interlinear, interlinear_quality, prose
from checks.apparatus import derived_summary
from checks.collate import collate
from checks.language_packs import check_layer
from checks.translation_provenance import canonical_hash, check, protected, source_payload

ROOT = Path(__file__).resolve().parents[1]
J = "proprium.sancti-ioseph-opificis-"
INTROIT, COLLECT, EPISTLE, ALLELUIA = (
    J + "introitus",
    J + "collecta",
    J + "epistola",
    J + "alleluia",
)
GOSPEL, OFFERTORY, SECRET = J + "evangelium", J + "offertorium", J + "secreta"
COMMUNION, POSTCOMMUNION = J + "communio", J + "postcommunio"
PREFACE = "ordinarium.praefatio-sancti-ioseph-in-solemnitate"
TWIN = "ordinarium.praefatio-sancti-ioseph-in-festivitate"
PREFACES = (PREFACE, TWIN)
PROPERS = [INTROIT, COLLECT, EPISTLE, ALLELUIA, GOSPEL, OFFERTORY, SECRET, COMMUNION, POSTCOMMUNION]


@cache
def _core(text):
    return store.core(ROOT, text)


@cache
def _layer(language, text):
    return store.raw_layer(ROOT, language, text)


def core(text):
    return deepcopy(_core(text))


def layer(language, text):
    return deepcopy(_layer(language, text))


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def words(doc):
    return {w["id"]: w for s in doc["segments"] for w in s.get("words", [])}


def grouped(lay):
    return {
        w for s in lay["segments"].values() for g in s.get("alignments", []) for w in g["words"]
    }


def layer_path(language, text):
    return ROOT / "languages" / language / "texts" / (text.replace(".", "/", 1) + ".json")


def provenance(language):
    return {
        s["site"]: s for s in load(f"languages/{language}/translation-provenance.json")["sites"]
    }


def rejects(check_fn, *args, message):
    """The control: the check raises AssertionError whose first line names the defect."""
    with pytest.raises(AssertionError) as caught:
        check_fn(*args)
    assert str(caught.value).splitlines()[0] == message


def ids(*numbers):
    return [f"w{n:03d}" for n in numbers]


# --- word captions ------------------------------------------------------------------------------
# (finding, language, text, word, Latin form, selected caption, predecessor caption)
GLOSSES: list[tuple[Any, ...]] = [
    ("XL-CAP-1", "pl", INTROIT, "w025", "Allelúia", "Alleluja", "alleluja"),
    ("XL-CAP-1", "pl", INTROIT, "w081", "Allelúia", "Alleluja", "alleluja"),
    ("XL-CAP-1", "pl", OFFERTORY, "w019", "Allelúia", "Alleluja", "alleluja"),
    ("XL-CAP-1", "pl", COLLECT, "w001", "Rerum", "Wszechrzeczy", "wszechrzeczy"),
    ("XL-CAP-1", "pl", GOSPEL, "w004", "Véniens", "przyszedłszy", "Przyszedłszy"),
    ("PL-SCAND-1", "pl", GOSPEL, "w060", "in", "z powodu", "z"),
    ("XL-INTERP-1", "pl", SECRET, "w012", "interpósito", "przedłożonym", "za"),
    ("PL-ET-1", "pl", POSTCOMMUNION, "w010", "et", "zarówno", "oraz"),
    ("XL-CAP-1", "en", INTROIT, "w025", "Allelúia", "Alleluia", "alleluia"),
    ("XL-CAP-1", "en", INTROIT, "w081", "Allelúia", "Alleluia", "alleluia"),
    ("XL-CAP-1", "en", COLLECT, "w001", "Rerum", "Of all things", "of all things"),
    ("XL-CAP-1", "en", COLLECT, "w027", "Per", "Through", "through"),
    ("XL-CAP-1", "en", COLLECT, "w034", "Qui", "who", "Who"),
    ("EN-OPEN-1", "en", EPISTLE, "w001", "Fratres", "Brethren", "Brothers"),
    ("XL-CAP-1", "en", EPISTLE, "w002", "Caritátem", "Charity", "charity"),
    ("XL-CAP-1", "en", EPISTLE, "w003", "habéte", "have", "Have"),
    ("XL-CAP-1", "en", EPISTLE, "w008", "et", "and", "And"),
    ("XL-CAP-1", "en", EPISTLE, "w047", "Quodcúmque", "Whatever", "whatever"),
    ("XL-CAP-1", "en", EPISTLE, "w064", "Dómino", "The Lord", "the Lord"),
    ("XL-CAP-1", "en", EPISTLE, "w066", "servíte", "serve", "Serve"),
    ("EN-HYP-1", "en", ALLELUIA, "w019", "innócuam", "blameless", "a blameless"),
    ("EN-HYP-1", "en", ALLELUIA, "w022", "vitam", "a life", "life"),
    ("XL-CAP-1", "en", GOSPEL, "w063", "autem", "but", "But"),
    ("XL-GRP-1", "en", GOSPEL, "w068", "prophéta", "a prophet", None),
    ("EN-ARCH-1", "en", GOSPEL, "w071", "nisi", "except", "save"),
    ("XL-INTERP-1", "en", SECRET, "w012", "interpósito", "interposed", "with"),
    ("XL-CAP-1", "en", SECRET, "w020", "Per", "Through", "through"),
    ("XL-CAP-1", "en", SECRET, "w027", "Qui", "who", "Who"),
    ("XL-CAP-1", "en", POSTCOMMUNION, "w017", "Per", "Through", "through"),
    ("XL-CAP-1", "en", POSTCOMMUNION, "w024", "Qui", "who", "Who"),
] + [
    row
    for text in PREFACES
    for row in (
        ("PL-SPONS-1", "pl", text, "w042", "Sponsus", "za Oblubieńca", "Oblubieńcem"),
        ("PL-UNIG-1", "pl", text, "w056", "Unigénitum", "Jednorodzonego", "jednorodzonego"),
        ("PL-OBUMB-1", "pl", text, "w060", "obumbratióne", "przez ocienienie", "za sprawą"),
        (
            "EN-DUP-1",
            "en",
            text,
            "w060",
            "obumbratióne",
            "by the overshadowing",
            "by the overshadowing of",
        ),
        ("XL-CAP-1", "en", text, "w001", "Vere", "Truly", "truly"),
        ("XL-CAP-1", "en", text, "w069", "Per", "Through", "through"),
        ("XL-CAP-1", "en", text, "w079", "Cæli", "The heavens", "the heavens"),
    )
]


def gloss_id(row):
    return f"{row[0]}-{row[1]}-{row[2].split('.', 1)[1]}-{row[3]}"


def assert_gloss(doc, lay, row):
    finding, _language, _text, wid, form, gloss, _old = row
    assert words(doc)[wid]["form"] == form, f"{finding} Latin context"
    assert wid not in grouped(lay), f"{finding} word caption"
    assert lay["words"][wid].get("gloss") == gloss, f"{finding} caption"
    assert interlinear.check(doc, lay) == [], f"{finding} interlinear line"


def test_caption_inventory():
    findings = [row[0] for row in GLOSSES]
    # 5 Polish and 19 English caption sites of this Mass, plus the 3 twin English sites.
    assert [r[1] for r in GLOSSES if r[0] == "XL-CAP-1" and r[2] != TWIN].count("pl") == 5
    assert [r[1] for r in GLOSSES if r[0] == "XL-CAP-1" and r[2] != TWIN].count("en") == 19
    assert len(GLOSSES) == 44 and findings.count("XL-CAP-1") == 27
    assert len({(r[1], r[2], r[3]) for r in GLOSSES}) == len(GLOSSES)


@pytest.mark.parametrize("row", GLOSSES, ids=[gloss_id(r) for r in GLOSSES])
def test_selected_caption(row):
    assert_gloss(core(row[2]), layer(row[1], row[2]), row)


@pytest.mark.parametrize("row", GLOSSES, ids=[gloss_id(r) for r in GLOSSES])
def test_predecessor_caption_is_rejected(row):
    doc, lay = core(row[2]), layer(row[1], row[2])
    assert_gloss(doc, lay, row)
    if row[6] is None:
        lay["words"][row[3]].pop("gloss")
    else:
        lay["words"][row[3]]["gloss"] = row[6]
    rejects(assert_gloss, doc, lay, row, message=f"{row[0]} caption")


@pytest.mark.parametrize("language", ["pl", "en"])
def test_the_ablative_absolute_participle_is_captioned_as_a_participle(language):
    doc, lay = core(SECRET), layer(language, SECRET)
    participle, noun = words(doc)["w012"], words(doc)["w013"]
    assert (participle["lemma"], participle["morph"]["mood"], participle["morph"]["case"]) == (
        "interpono",
        "part",
        "abl",
    )
    assert participle["head"] == "w013" and noun["lemma"] == "suffragium"
    caption = lay["words"]["w012"]["gloss"]
    assert caption == {"pl": "przedłożonym", "en": "interposed"}[language]
    assert caption not in {"za", "with", "through", "by"}
    assert (
        lay["words"]["w013"]["gloss"] == {"pl": "wstawiennictwem", "en": "intercession"}[language]
    )


# --- English groups: EN-POSS-1, EN-DAT-1 and the Gospel's own clause group (XL-GRP-1) ------------
# (finding, text, members, anchor, caption, predecessor: word captions or the predecessor group)
GROUPS: list[tuple[Any, ...]] = [
    ("EN-POSS-1", INTROIT, ids(5, 6), "w005", "of their labors", ["of labors", "their"]),
    ("EN-POSS-1", INTROIT, ids(61, 62), "w061", "of their labors", ["of labors", "their"]),
    ("EN-DAT-1", COLLECT, ids(7, 8), "w008", "for the human race", ["human", "race"]),
    ("EN-POSS-1", COLLECT, ids(28, 29), "w028", "our Lord", ["Lord", "our"]),
    ("EN-POSS-1", COLLECT, ids(32, 33), "w032", "Your Son", ["Son", "Your"]),
    ("EN-POSS-1", EPISTLE, ids(13, 14), "w013", "your hearts", ["hearts", "your"]),
    ("EN-POSS-1", ALLELUIA, ids(13, 14), "w013", "their protector", ["protector", "their"]),
    ("EN-POSS-1", GOSPEL, ids(7, 8), "w007", "His own country", ["country", "His own"]),
    (
        "XL-GRP-1",
        GOSPEL,
        ids(66, 67),
        "w067",
        "Is not",
        {"words": ids(66, 67, 68), "anchor": "w067", "gloss": "A prophet is not"},
    ),
    ("EN-POSS-1", OFFERTORY, ids(3, 4), "w003", "our God", ["of God", "our"]),
    ("EN-POSS-1", OFFERTORY, ids(10, 11), "w010", "of our hands", ["of hands", "our"]),
    ("EN-POSS-1", OFFERTORY, ids(16, 17), "w016", "of our hands", ["of hands", "our"]),
    ("EN-POSS-1", SECRET, ids(6, 7), "w006", "of our hands", ["of hands", "our"]),
    ("EN-POSS-1", SECRET, ids(21, 22), "w021", "our Lord", ["Lord", "our"]),
    ("EN-POSS-1", SECRET, ids(25, 26), "w025", "Your Son", ["Son", "Your"]),
    ("EN-POSS-1", POSTCOMMUNION, ids(11, 12), "w011", "our work", ["work", "our"]),
    ("EN-POSS-1", POSTCOMMUNION, ids(18, 19), "w018", "our Lord", ["Lord", "our"]),
    ("EN-POSS-1", POSTCOMMUNION, ids(22, 23), "w022", "Your Son", ["Son", "Your"]),
]


def group_id(row):
    return f"{row[0]}-{row[1].split('.', 1)[1]}-{row[2][0]}"


def assert_group(doc, lay, row):
    finding, _text, members, anchor, caption, _old = row
    expected = {"words": members, "anchor": anchor, "gloss": caption}
    touching = [
        g
        for s in lay["segments"].values()
        for g in s.get("alignments", [])
        if set(g["words"]) & set(members)
    ]
    assert touching == [expected], f"{finding} group"
    assert all("gloss" not in lay["words"][w] for w in members), f"{finding} group"
    assert interlinear.check(doc, lay) == [], f"{finding} interlinear line"
    assert english.check(doc, lay) == [], f"{finding} English line"
    assert interlinear_quality.check(doc, lay) == [], f"{finding} English line"


def test_group_inventory():
    assert len(GROUPS) == 18
    # The ledger's EN-POSS-1 list: 16 pairs, 32 tokens.
    assert sum(len(r[2]) for r in GROUPS if r[0] == "EN-POSS-1") == 32


@pytest.mark.parametrize("row", GROUPS, ids=[group_id(r) for r in GROUPS])
def test_selected_group(row):
    assert_group(core(row[1]), layer("en", row[1]), row)


@pytest.mark.parametrize("row", GROUPS, ids=[group_id(r) for r in GROUPS])
def test_predecessor_split_or_group_is_rejected(row):
    doc, lay = core(row[1]), layer("en", row[1])
    assert_group(doc, lay, row)
    seg = lay["segments"]["s01"]
    seg["alignments"] = [g for g in seg["alignments"] if g["words"] != row[2]]
    if isinstance(row[5], dict):
        seg["alignments"].append(deepcopy(row[5]))
        seg["alignments"].sort(key=lambda g: g["words"][0])
        lay["words"]["w068"].pop("gloss")
    else:
        for wid, caption in zip(row[2], row[5], strict=True):
            lay["words"][wid]["gloss"] = caption
    rejects(assert_group, doc, lay, row, message=f"{row[0]} group")


POSSESSIVES = {"noster", "tuus", "suus", "vester", "meus"}
# Postposed genitive pronouns the audit reviewed and kept as word captions (its ledger's KEEP):
# recorded unchanged counterexamples, not part of the accepted EN-POSS-1 list.
COUNTEREXAMPLES = {
    (GOSPEL, "w012"): ("synagógis eórum", "synagogues", "their"),
    (GOSPEL, "w031"): ("mater eius", "mother", "His"),
    (GOSPEL, "w036"): ("fratres eius", "brethren", "His"),
    (GOSPEL, "w046"): ("soróres eius", "sisters", "His"),
    (GOSPEL, "w086"): ("incredulitátem illórum", "unbelief", "their"),
    (COMMUNION, "w013"): ("mater eius", "mother", "His"),
}


def possessive_pairs(text, lay=None):
    """Noun + postposed possessive (adjective or genitive pronoun) in one segment, as
    (noun id, Latin phrase, grouped caption or the two word captions)."""
    doc, lay = core(text), lay or layer("en", text)
    out = []
    for segment in doc["segments"]:
        ws = segment.get("words", [])
        groups = lay["segments"].get(segment["id"], {}).get("alignments", [])
        for a, b in pairwise(ws):
            genitive = b["lemma"] in {"is", "ille"} and b["morph"].get("case") == "gen"
            if a["morph"].get("pos") != "noun" or a.get("post"):
                continue
            if b["lemma"] not in POSSESSIVES and not genitive:
                continue
            phrase = f"{a['form']} {b['form']}"
            together = [g for g in groups if a["id"] in g["words"] and b["id"] in g["words"]]
            if together:
                out.append((a["id"], phrase, together[0]["gloss"]))
            else:
                out.append(
                    (
                        a["id"],
                        phrase,
                        (lay["words"][a["id"]]["gloss"], lay["words"][b["id"]]["gloss"]),
                    )
                )
    return out


def test_every_postposed_possessive_adjective_is_grouped_and_the_counterexamples_are_recorded():
    split, together = {}, 0
    for text in [*PROPERS, *PREFACES]:
        for wid, phrase, caption in possessive_pairs(text):
            if isinstance(caption, tuple):
                split[(text, wid)] = (phrase, *caption)
            else:
                together += 1
    assert split == COUNTEREXAMPLES
    assert together == 24
    damaged = layer("en", SECRET)
    damaged["segments"]["s01"]["alignments"] = [
        g for g in damaged["segments"]["s01"]["alignments"] if g["words"] != ids(21, 22)
    ]
    damaged["words"]["w021"]["gloss"], damaged["words"]["w022"]["gloss"] = "Lord", "our"
    assert ("w021", "Dóminum nostrum", ("Lord", "our")) in possessive_pairs(SECRET, damaged)


FORMULA = "forever and ever"


def long_groups(text, language, lay=None):
    lay = lay or layer(language, text)
    return [
        (s, g)
        for s, seg in lay["segments"].items()
        for g in seg.get("alignments", [])
        if len(g["words"]) >= 3
    ]


def assert_bounded_groups(text, language, lay=None):
    local_phrase = {
        "words": ids(24, 25, 26, 27),
        "anchor": "w026",
        "gloss": {
            "pl": "zawsze bezpieczne pod twoją opieką",
            "en": "always safe under your protection",
        }[language],
    }
    for segment, group in long_groups(text, language, lay):
        assert group["gloss"] == FORMULA or (
            text == ALLELUIA and segment == "s01" and group == local_phrase
        ), "no clause-sized group"


@pytest.mark.parametrize("language", ["pl", "en"])
def test_the_proper_texts_keep_no_clause_sized_group(language):
    found = {text: long_groups(text, language) for text in PROPERS}
    for text in found:
        assert_bounded_groups(text, language)
    expected = {"pl": 1, "en": 5}[language]
    assert sum(len(groups) for groups in found.values()) == expected
    bad = layer("en", GOSPEL)
    seg = bad["segments"]["s01"]
    seg["alignments"] = [g for g in seg["alignments"] if g["words"] != ids(66, 67)]
    seg["alignments"].append(
        {"words": ids(66, 67, 68), "anchor": "w067", "gloss": "A prophet is not"}
    )
    rejects(assert_bounded_groups, GOSPEL, "en", bad, message="no clause-sized group")


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("damage", ["members", "anchor", "caption", "whole-clause"])
def test_the_local_protective_phrase_is_an_exact_exception(language, damage):
    original = layer(language, ALLELUIA)
    assert_bounded_groups(ALLELUIA, language, original)
    bad = deepcopy(original)
    group = next(g for g in bad["segments"]["s01"]["alignments"] if g["anchor"] == "w026")
    if damage == "members":
        group["words"] = ids(23, 24, 25, 26)
    elif damage == "anchor":
        group["anchor"] = "w024"
    elif damage == "caption":
        group["gloss"] += " always"
    else:
        group["words"] = ids(23, 24, 25, 26, 27)
        group["gloss"] = "and may it always be safe under your protection"
    rejects(assert_bounded_groups, ALLELUIA, language, bad, message="no clause-sized group")
    assert_bounded_groups(ALLELUIA, language, original)


def segment_shape(doc, lay, segment):
    """The alignment pattern of one segment by word position, captions included."""
    order = {w["id"]: i for i, w in enumerate(segment["words"])}
    return [
        ([order[w] for w in g["words"]], order.get(g.get("anchor", ""), None), g.get("gloss"))
        for g in lay["segments"][segment["id"]].get("alignments", [])
    ]


@pytest.mark.parametrize("text", PREFACES)
@pytest.mark.parametrize("language", ["pl", "en"])
def test_shared_preface_formulas_keep_the_common_preface_groups(text, language):
    """The groups of the formulas shared with the Common Preface (its s02, s04–s06, among them
    the Cum quibus petition) are left to the corpus-wide preface-granularity unit: this Mass
    does not make one preface diverge from the others with identical Latin."""
    common, common_lay = (
        core("ordinarium.praefatio-communis"),
        layer(language, "ordinarium.praefatio-communis"),
    )
    shared = {
        tuple(w["form"] for w in s["words"]): segment_shape(common, common_lay, s)
        for s in common["segments"]
        if s.get("words")
    }
    doc, lay = core(text), layer(language, text)
    matched = 0
    for segment in doc["segments"]:
        key = tuple(w["form"] for w in segment.get("words", []))
        if key in shared:
            assert segment_shape(doc, lay, segment) == shared[key], segment["id"]
            matched += 1
    assert matched == 4


# --- verses -------------------------------------------------------------------------------------
# (finding, language, text, segment, selected phrase, predecessor phrase)
VERSES = [
    *[
        (
            "PL-OBUMB-1",
            "pl",
            text,
            "s05",
            "poczętego przez ocienienie Ducha Świętego",
            "poczętego za sprawą Ducha Świętego",
        )
        for text in PREFACES
    ],
    ("EN-OPEN-1", "en", EPISTLE, "s01", "Brethren: Have charity", "Brothers: Have charity"),
    (
        "EN-ADD-1",
        "en",
        POSTCOMMUNION,
        "s01",
        "and confirm the rewards.",
        "and confirm its rewards.",
    ),
]


def assert_verse(lay, row):
    finding, language, text, segment, present, absent = row
    target = lay["segments"][segment]["translation"]
    assert present in target and absent not in target, f"{finding} verse"
    site = provenance(language)[f"{text}.{segment}.{language}"]
    assert site["target_sha256"] == canonical_hash(target), f"{finding} provenance"
    assert site["review"] == "working"
    assert_protection_scope(text, language, segment, target)


@pytest.mark.parametrize("row", VERSES, ids=[f"{r[0]}-{r[2].split('.', 1)[1]}" for r in VERSES])
def test_selected_verse(row):
    assert_verse(layer(row[1], row[2]), row)


@pytest.mark.parametrize("row", VERSES, ids=[f"{r[0]}-{r[2].split('.', 1)[1]}" for r in VERSES])
def test_predecessor_verse_is_rejected(row):
    lay = layer(row[1], row[2])
    target = lay["segments"][row[3]]["translation"]
    lay["segments"][row[3]]["translation"] = target.replace(row[4], row[5])
    rejects(assert_verse, lay, row, message=f"{row[0]} verse")


def test_the_overshadowing_reads_as_in_the_marian_prefaces():
    marian = layer("pl", "ordinarium.praefatio-beatae-mariae-virginis")["segments"]["s05"]
    assert "przez ocienienie Ducha Świętego" in marian["translation"]
    for text in PREFACES:
        assert words(core(text))["w060"]["lemma"] == "obumbratio"
        assert (
            "przez ocienienie Ducha Świętego" in layer("pl", text)["segments"]["s05"]["translation"]
        )
        assert (
            "by the overshadowing of the Holy Spirit"
            in (layer("en", text)["segments"]["s05"]["translation"])
        )


def test_english_epistles_open_with_the_house_brethren():
    lay = layer("en", EPISTLE)
    assert lay["segments"]["s01"]["translation"].startswith("Brethren: ")
    assert "Brothers" not in json.dumps(lay)


# --- about-notes (XL-ABOUT-1) --------------------------------------------------------------------
ABOUTS = {
    ("pl", PREFACE): (
        "Prefacja o świętym Józefie z formułą „Solemnitáte”. Wysławia Boga w uroczystość świętego "
        "Józefa, sprawiedliwego Oblubieńca Bogarodzicy, wiernego opiekuna Świętej Rodziny i "
        "ziemskiego stróża Syna Bożego."
    ),
    ("pl", TWIN): (
        "Prefacja o świętym Józefie z formułą „Festivitáte”. Wysławia Boga w święto świętego "
        "Józefa, sprawiedliwego Oblubieńca Bogarodzicy, wiernego opiekuna Świętej Rodziny i "
        "ziemskiego stróża Syna Bożego."
    ),
    ("en", PREFACE): (
        "The Preface of Saint Joseph with the formula “Solemnitáte.” It praises God on the "
        "Solemnity of Saint Joseph, the just spouse of the Mother of God, faithful guardian of the "
        "Holy Family, and earthly protector of the Son of God."
    ),
    ("en", TWIN): (
        "The Preface of Saint Joseph with the formula “Festivitáte.” It praises God on the Feast "
        "of Saint Joseph, the just spouse of the Mother of God, faithful guardian of the Holy "
        "Family, and earthly protector of the Son of God."
    ),
}
PRAISE = {"pl": "Wysławia Boga w ", "en": "It praises God on the "}
# The predecessor notes said the preface praises Joseph (and the Polish one used guillemets).
PREDECESSOR_ABOUTS = {
    "pl": (
        "Prefacja o świętym Józefie z formułą «{f}». Wysławia sprawiedliwego Oblubieńca "
        "Bogarodzicy, wiernego opiekuna Świętej Rodziny i ziemskiego stróża Syna Bożego."
    ),
    "en": (
        "The Preface of Saint Joseph with the formula “{f}.” It praises the just spouse of the "
        "Mother of God, faithful guardian of the Holy Family, and earthly protector of the Son "
        "of God."
    ),
}


def assert_about(lay, language, text):
    about = lay["about"]
    assert about == ABOUTS[(language, text)], "XL-ABOUT-1 note"
    assert PRAISE[language] in about, "XL-ABOUT-1 note"
    assert "«" not in about and "»" not in about, "XL-ABOUT-1 note"
    assert prose.check(lay) == [], "XL-ABOUT-1 prose"


@pytest.mark.parametrize("language,text", sorted(ABOUTS))
def test_the_preface_note_says_it_praises_god(language, text):
    assert_about(layer(language, text), language, text)


@pytest.mark.parametrize("language,text", sorted(ABOUTS))
@pytest.mark.parametrize("damage", ["predecessor", "guillemets"])
def test_the_preface_note_damage_is_rejected(language, text, damage):
    lay = layer(language, text)
    if damage == "predecessor":
        lay["about"] = PREDECESSOR_ABOUTS[language].format(f=FEAST[text][language][0])
    elif language == "pl":
        lay["about"] = lay["about"].replace("„", "«").replace("”", "»")
    else:
        lay["about"] = lay["about"].replace("“", "«").replace("”", "»")
    assert lay["about"] != ABOUTS[(language, text)]
    rejects(assert_about, lay, language, text, message="XL-ABOUT-1 note")


# --- the two St Joseph prefaces stay identical apart from their feast word -----------------------
FEAST = {
    PREFACE: {"pl": ("Solemnitáte", "uroczystość"), "en": ("Solemnitáte", "Solemnity")},
    TWIN: {"pl": ("Festivitáte", "święto"), "en": ("Festivitáte", "Feast")},
}


def normalized(lay, text, language):
    formula, word = FEAST[text][language]
    out = deepcopy(lay)
    out.pop("text")
    out["about"] = out["about"].replace(formula, "<F>").replace(f" {word} ", " <W> ")
    out["segments"]["s04"]["translation"] = out["segments"]["s04"]["translation"].replace(
        f" {word} ", " <W> "
    )
    assert out["words"]["w025"] == {"gloss": word}
    out["words"]["w025"] = {"gloss": "<W>"}
    return out


@pytest.mark.parametrize("language", ["pl", "en"])
def test_both_st_joseph_prefaces_carry_the_same_corrections(language):
    one = normalized(layer(language, PREFACE), PREFACE, language)
    two = normalized(layer(language, TWIN), TWIN, language)
    assert one == two
    damaged = layer(language, TWIN)
    damaged["words"]["w060"]["gloss"] = {"pl": "za sprawą", "en": "by the overshadowing of"}[
        language
    ]
    assert normalized(damaged, TWIN, language) != one


# --- caption case (XL-CAP-1): a caption at a genuine sentence or quotation opening follows the
# target sentence's capital; inside a sentence it is lower case. Bounded to this Mass and the
# 19 March twin of its preface (RF6 / III Sunday pattern).
CASE_TEXTS = [*PROPERS, *PREFACES]
# Reviewed lower-case captions at a Latin opening whose target sentence continues.
CONTINUATIONS = {
    ("pl", COLLECT, "w034"): "który",
    ("pl", SECRET, "w027"): "który",
    ("pl", POSTCOMMUNION, "w024"): "który",
    ("en", COLLECT, "w034"): "who",
    ("en", SECRET, "w027"): "who",
    ("en", POSTCOMMUNION, "w024"): "who",
    ("pl", GOSPEL, "w004"): "przyszedłszy",
    ("en", GOSPEL, "w004"): "coming",
    **{
        (language, text, "w022"): caption
        for text in PREFACES
        for language, caption in (("pl", "i"), ("en", "and"))
    },
}
# Lower-case opening captions outside the accepted XL-CAP-1 list (the audit kept them; reported).
RESIDUAL = {("pl", EPISTLE, "w002"): "miłość"}
# Capitals a lower-case Latin word may carry here: words for God and Christ, English I, and the
# divine title of the Collect's address (cónditor). Me/Mnie is the open speaker question XL-SPK-1.
NAMED = {
    "pl": {"Ciebie", "Jego", "Mnie", "Mu", "Niego", "Stwórco", "Tobie", "Twoją", "Twojego", "Twój"},
    "en": {"Creator", "He", "Him", "His", "I", "Me", "You", "Your"},
}


def caption_case(doc, lay):
    """Lower-case captions at a Latin opening and capitals at a Latin lower-case continuation,
    except the reviewed address-and-caption pairs above; with the number of openings examined."""
    language, misses, examined = lay["language"], [], 0
    for segment in doc["segments"]:
        ws = segment.get("words", [])
        spans = {
            a["words"][0]: a for a in lay["segments"].get(segment["id"], {}).get("alignments", [])
        }
        prev, pending, i = ".", False, 0
        while i < len(ws):
            group = spans.get(ws[i]["id"])
            n = len(group["words"]) if group else 1
            first, last = ws[i], ws[i + n - 1]
            opens = pending or (
                prev.rstrip().endswith((".", ":", "?", "!")) and first["form"][:1].isupper()
            )
            gloss = group.get("gloss") if group else lay["words"][first["id"]].get("gloss")
            prev, i = last.get("post", ""), i + n
            if gloss is None:
                pending = opens
                continue
            pending = False
            key = (language, doc["id"], first["id"])
            if opens:
                examined += 1
                reviewed = CONTINUATIONS.get(key) == gloss or RESIDUAL.get(key) == gloss
                if gloss[:1].islower() and not reviewed:
                    misses.append((first["id"], gloss))
            elif first["form"][:1].islower():
                word = re.search(r"[^\W\d_]+", gloss)
                capital = word is not None and word[0][:1].isupper()
                if capital and word[0] not in NAMED[language]:
                    misses.append((first["id"], gloss))
    return misses, examined


@pytest.mark.parametrize("language", ["pl", "en"])
def test_captions_follow_the_target_sentence_in_this_mass(language):
    total = 0
    for text in CASE_TEXTS:
        misses, examined = caption_case(core(text), layer(language, text))
        assert misses == [], text
        total += examined
    assert total == 61


def caption_at(lay, wid):
    groups = [g for s in lay["segments"].values() for g in s.get("alignments", [])]
    starting = [g for g in groups if g["words"][0] == wid]
    return starting[0].get("gloss") if starting else lay["words"][wid].get("gloss")


def latin_opening(doc, wid):
    for segment in doc["segments"]:
        ws = segment.get("words", [])
        order = [w["id"] for w in ws]
        if wid in order:
            index = order.index(wid)
            prev = ws[index - 1].get("post", "") if index else "."
            return prev.rstrip().endswith((".", ":", "?", "!")) and ws[index]["form"][:1].isupper()
    raise KeyError(wid)


def test_reviewed_exceptions_are_live_and_bound_to_their_context():
    for table in (CONTINUATIONS, RESIDUAL):
        for (language, text, wid), caption in table.items():
            doc, lay = core(text), layer(language, text)
            assert caption_at(lay, wid) == caption
            assert latin_opening(doc, wid) is True


# (language, text, segment, word, caption, target text before the opening, target opening, where)
CAP_SITES = [
    ("pl", INTROIT, "s01", "w025", "Alleluja", "przez noc. ", "Alleluja, alleluja. Jeśli", "once"),
    ("pl", INTROIT, "s01", "w081", "Alleluja", "przez noc. ", "Alleluja, alleluja.", "end"),
    ("pl", OFFERTORY, "s01", "w019", "Alleluja", "pomyślnie. ", "Alleluja.", "end"),
    ("pl", COLLECT, "s01", "w001", "Wszechrzeczy", "", "Stwórco wszystkich rzeczy", "start"),
    ("en", INTROIT, "s01", "w025", "Alleluia", "by night. ", "Alleluia, alleluia. Unless", "once"),
    ("en", INTROIT, "s01", "w081", "Alleluia", "by night. ", "Alleluia, alleluia.", "end"),
    ("en", COLLECT, "s01", "w001", "Of all things", "", "O God, Creator of all things", "start"),
    ("en", COLLECT, "s01", "w027", "Through", "You promise. ", "Through our Lord", "once"),
    ("en", EPISTLE, "s01", "w002", "Charity", "Brethren: ", "Have charity", "once"),
    ("en", EPISTLE, "s01", "w047", "Whatever", "through Him. ", "Whatever you do, do it", "once"),
    ("en", EPISTLE, "s01", "w064", "The Lord", "inheritance. ", "Serve the Lord Christ.", "end"),
    ("en", SECRET, "s01", "w020", "Through", "for us. ", "Through our Lord", "once"),
    ("en", POSTCOMMUNION, "s01", "w017", "Through", "the rewards. ", "Through our Lord", "once"),
] + [
    site
    for text in PREFACES
    for site in (
        ("en", text, "s02", "w001", "Truly", "", "Truly it is right", "start"),
        ("en", text, "s06", "w069", "Through", "", "Through Him the Angels", "start"),
        ("en", text, "s07", "w079", "The heavens", "", "The heavens, the heavenly", "start"),
    )
]


def site_id(site):
    return f"{site[0]}-{site[1].split('.', 1)[1]}-{site[3]}"


def assert_caption_site(doc, lay, site):
    language, _, segment, wid, caption, before, opening, where = site
    assert lay["language"] == language
    target = lay["segments"][segment]["translation"]
    context = before + opening
    if where == "once":
        assert target.count(context) == 1, "target sentence context"
    elif where == "end":
        assert target.endswith(context), "target sentence context"
    else:
        assert not before and target.startswith(opening), "target sentence context"
    assert latin_opening(doc, wid) is opening[:1].isupper(), "Latin and target boundary disagree"
    assert caption_at(lay, wid) == caption
    assert caption[:1].isupper() is opening[:1].isupper(), "caption case follows the target"
    assert (wid, caption) not in caption_case(doc, lay)[0]


@pytest.mark.parametrize("site", CAP_SITES, ids=[site_id(s) for s in CAP_SITES])
def test_caption_at_an_opening_follows_the_target_sentence(site):
    assert_caption_site(core(site[1]), layer(site[0], site[1]), site)


def recased(caption):
    return caption[:1].swapcase() + caption[1:]


def with_caption(lay, wid, caption):
    bad = deepcopy(lay)
    starting = [g for s in bad["segments"].values() for g in s.get("alignments", [])]
    starting = [g for g in starting if g["words"][0] == wid]
    if starting:
        starting[0]["gloss"] = caption
    else:
        bad["words"][wid]["gloss"] = caption
    return bad


@pytest.mark.parametrize("site", CAP_SITES, ids=[site_id(s) for s in CAP_SITES])
def test_wrong_caption_case_is_rejected_by_both_guards(site):
    doc, lay = core(site[1]), layer(site[0], site[1])
    assert_caption_site(doc, lay, site)
    wrong = recased(site[4])
    bad = with_caption(lay, site[3], wrong)
    assert caption_case(doc, bad)[0] == [(site[3], wrong)]
    with pytest.raises(AssertionError):
        assert_caption_site(doc, bad, (*site[:4], wrong, *site[5:]))


# Captions that the rule keeps lower case inside a sentence, although the English verse opens a
# sentence there or the Polish verse starts its participle with a capital.
INNER = [
    ("en", EPISTLE, "w003", "have"),
    ("en", EPISTLE, "w008", "and"),
    ("en", EPISTLE, "w066", "serve"),
    ("en", GOSPEL, "w063", "but"),
]


@pytest.mark.parametrize("site", INNER, ids=[f"{s[0]}-{s[2]}" for s in INNER])
def test_inner_captions_are_lower_case_and_a_capital_is_rejected(site):
    language, text, wid, caption = site
    doc, lay = core(text), layer(language, text)
    assert caption_at(lay, wid) == caption and latin_opening(doc, wid) is False
    bad = with_caption(lay, wid, recased(caption))
    assert caption_case(doc, bad)[0] == [(wid, recased(caption))]


@pytest.mark.parametrize("damage", ["latin-comma", "target-continues", "wrong-language", "moved"])
def test_caption_rule_is_bound_to_latin_and_target_context(damage):
    site = CAP_SITES[8]  # the English Epistle opening after Fratres:
    doc, lay = core(EPISTLE), layer("en", EPISTLE)
    assert_caption_site(doc, lay, site)
    if damage == "latin-comma":
        bad_doc = deepcopy(doc)
        segment = bad_doc["segments"][0]
        assert segment["words"][0]["id"] == "w001"
        segment["words"][0]["post"] = ","
        rejects(
            assert_caption_site, bad_doc, lay, site, message="Latin and target boundary disagree"
        )
    elif damage == "target-continues":
        bad = deepcopy(lay)
        text = bad["segments"]["s01"]["translation"]
        bad["segments"]["s01"]["translation"] = text.replace("Brethren: Have", "Brethren, have")
        rejects(assert_caption_site, doc, bad, site, message="target sentence context")
    elif damage == "wrong-language":
        # The English continuation 'who' never covers a Polish caption, nor 'który' an English one.
        polish = with_caption(layer("pl", COLLECT), "w034", "who")
        assert ("w034", "who") in caption_case(core(COLLECT), polish)[0]
        english_layer = layer("pl", COLLECT)
        english_layer["language"] = "en"
        assert ("w034", "który") in caption_case(core(COLLECT), english_layer)[0]
    else:
        # The reviewed continuation is bound to its address: lower case at another opening fails.
        bad = with_caption(layer("en", GOSPEL), "w066", "is not")
        assert caption_case(core(GOSPEL), bad)[0] == [("w066", "is not")]


# --- the Gospel's printed quotation marks (F-SRC-2) ----------------------------------------------
WITNESS = ROOT / "witnesses" / GOSPEL
QUOTED = [
    ("w019", "Unde", "“Unde", "dícerent: “Unde huic"),
    ("w057", "ista?", "ista?”", "ómnia ista?” Et"),
    ("w066", "Non", "“Non", "dixit eis: “Non est"),
    ("w078", "sua.", "sua.”", "in domo sua.” Et non"),
]
CORRECTION = (
    "# correction: 2026-10-20 the page prints quotation marks around both direct speeches "
    "(“Unde … ista?” and “Non … sua.”, p. 518, leaf n599, read at full resolution), which the "
    "earlier body omitted"
)


def assert_quotation_marks(doc, folder):
    transcript = (folder / "mr.txt").read_text(encoding="utf-8")
    lines = transcript.splitlines()
    body = " ".join(line for line in lines if line and not line.startswith("#"))
    assert lines.count(CORRECTION) == 1, "printed quotation marks"
    assert body.count("“") == 2 and body.count("”") == 2, "printed quotation marks"
    for _wid, _ours, _printed, context in QUOTED:
        assert body.count(context) == 1, "printed quotation marks"
    apparatus = json.loads((folder / "apparatus.json").read_text(encoding="utf-8"))
    quoted = [e for e in apparatus["adjudicated"] if e["class"] == "punctuation"]
    assert [(e["at"], e["ours"], e["witnesses"]) for e in quoted] == [
        (wid, ours, {"mr": printed}) for wid, ours, printed, _ in QUOTED
    ], "quotation apparatus"
    for entry in quoted:
        assert entry["witnesses"]["mr"] in entry["ruling"] and entry["ours"] in entry["ruling"]
    assert apparatus["summary"] == derived_summary(apparatus), "quotation apparatus"
    tokens = {w["id"]: w["form"] + w.get("post", "") for w in words(doc).values()}
    assert all(tokens[wid] == ours for wid, ours, _, _ in QUOTED), "selected text"
    errors, _warnings, stats = collate(doc, folder)
    assert errors == [], "collation"
    assert stats["variants_adjudicated"] == 4, "collation"


def test_the_gospel_witness_prints_the_quotation_marks_and_the_apparatus_records_them():
    assert_quotation_marks(core(GOSPEL), WITNESS)


def test_the_graph_binds_the_corrected_witness_and_apparatus():
    graph = load("bibliography/graph.json")
    (witness,) = [w for w in graph["witnesses"] if w["id"] == f"witness.{GOSPEL}.mr1962"]
    transcript = (WITNESS / "mr.txt").read_text(encoding="utf-8")
    assert witness["transcription_sha256"] == transcript_digest(transcript)
    (collation,) = [c for c in graph["collations"] if c["text"] == GOSPEL]
    apparatus = load(f"witnesses/{GOSPEL}/apparatus.json")
    assert collation["apparatus_sha256"] == digest(apparatus)
    assert collation["apparatus"] == derived_summary(apparatus)
    assert collation["selected_text_sha256"] == digest(selected_text(core(GOSPEL)))
    assert witness["review"] == collation["review"] == {"status": "pending"}
    unquoted = transcript.replace(CORRECTION + "\n", "").replace("“", "").replace("”", "")
    assert witness["transcription_sha256"] != transcript_digest(unquoted)


@pytest.mark.parametrize(
    "damage", ["opening-dropped", "entry-dropped", "header-dropped", "adopted"]
)
def test_the_quotation_record_rejects_damage(damage, tmp_path):
    folder = tmp_path / GOSPEL
    shutil.copytree(WITNESS, folder)
    doc = core(GOSPEL)
    message = "printed quotation marks"
    if damage == "opening-dropped":
        mr = folder / "mr.txt"
        mr.write_text(
            mr.read_text(encoding="utf-8").replace("eis: “Non", "eis: Non"), encoding="utf-8"
        )
        errors, _, _ = collate(doc, folder)
        assert any("w066" in error and "stale ruling" in error for error in errors)
    elif damage == "entry-dropped":
        path = folder / "apparatus.json"
        apparatus = json.loads(path.read_text(encoding="utf-8"))
        apparatus["adjudicated"] = [e for e in apparatus["adjudicated"] if e["at"] != "w057"]
        apparatus["summary"] = derived_summary(apparatus)
        path.write_text(
            json.dumps(apparatus, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        errors, _, _ = collate(doc, folder)
        assert any("UNADJUDICATED variant at w057" in error for error in errors)
        message = "quotation apparatus"
    elif damage == "header-dropped":
        mr = folder / "mr.txt"
        mr.write_text(
            mr.read_text(encoding="utf-8").replace(CORRECTION + "\n", ""), encoding="utf-8"
        )
    else:
        # The selected text silently adopts the page's quotation mark.
        segment = doc["segments"][0]
        (word,) = [w for w in segment["words"] if w["id"] == "w057"]
        word["post"] = "?”"
        message = "selected text"
    rejects(assert_quotation_marks, doc, folder, message=message)


# --- English provenance of the Introit and the Communion (EN-PROV-2) -----------------------------
RELABELLED = [f"{INTROIT}.s01.en", f"{COMMUNION}.s01.en"]


def assert_relabelled(sites):
    for site in RELABELLED:
        row = sites[site]
        assert (row["origin"], row["review"], row["familiar_core"]) == (
            "working-unsettled",
            "working",
            False,
        ), "EN-PROV-2 origin"
    # The Communion repeats the Gospel's English wording, so the two share one origin.
    assert sites[f"{GOSPEL}.s01.en"]["origin"] == sites[f"{COMMUNION}.s01.en"]["origin"], (
        "EN-PROV-2 origin"
    )


def test_the_introit_and_communion_no_longer_claim_own_wording():
    assert_relabelled(provenance("en"))
    communion = layer("en", COMMUNION)["segments"]["s01"]["translation"]
    gospel = layer("en", GOSPEL)["segments"]["s01"]["translation"]
    sentences = [s.strip().rstrip("?") for s in re.findall(r"[^?]+\?", communion)]
    assert len(sentences) == 3 and all(sentence in gospel for sentence in sentences)
    errors, _tally = check(ROOT)
    assert not [e for e in errors if any(site in e for site in RELABELLED)]


@pytest.mark.parametrize("site", RELABELLED)
def test_the_own_claim_is_rejected(site):
    sites = provenance("en")
    sites[site]["origin"] = "own"
    rejects(assert_relabelled, sites, message="EN-PROV-2 origin")


# --- the dominatio card (PL-CARD-1) and every consumer --------------------------------------------
CARD = ["Panowania", "Państwa", "panowanie"]


def dominatio_captions():
    found = []
    for path in sorted((ROOT / "texts").glob("*/*.json")):
        text = f"{path.parent.name}.{path.stem}"
        doc = json.loads(path.read_text(encoding="utf-8"))
        for wid, word in words(doc).items():
            if word["lemma"] == "dominatio":
                lay = layer("pl", text)
                assert wid not in grouped(lay), (text, wid)
                found.append((text, word["morph"]["case"], lay["words"][wid]["gloss"]))
    return found


def assert_card(card, captions):
    assert card["senses"][0] == "Panowania", "PL-CARD-1 first sense"
    assert card["senses"] == CARD, "PL-CARD-1 senses"
    for _text, case, caption in captions:
        assert caption == {"nom": "Panowania", "abl": "Panowaniami"}[case], "PL-CARD-1 consumers"


def test_the_dominatio_card_leads_with_its_consumers_reading():
    captions = dominatio_captions()
    assert len(captions) == 23 and sum(case == "nom" for _, case, _ in captions) == 13
    assert_card(load("languages/pl/lexicon.json")["entries"]["dominatio"], captions)


def test_the_predecessor_card_order_is_rejected():
    card = deepcopy(load("languages/pl/lexicon.json")["entries"]["dominatio"])
    card["senses"] = ["Państwa", "Panowania", "panowanie"]
    rejects(assert_card, card, dominatio_captions(), message="PL-CARD-1 first sense")


# --- provenance, protection and every consumer of the two preface bodies -------------------------
CHANGED = {
    "pl": [INTROIT, COLLECT, GOSPEL, OFFERTORY, SECRET, POSTCOMMUNION, PREFACE, TWIN],
    "en": [
        INTROIT,
        COLLECT,
        EPISTLE,
        ALLELUIA,
        GOSPEL,
        OFFERTORY,
        SECRET,
        POSTCOMMUNION,
        PREFACE,
        TWIN,
        COMMUNION,
    ],
}


def test_changed_sites_preserve_fixed_formula_scope_and_current_provenance():
    assert protected("orationes.gloria-patri", "pl") and protected("orationes.pater-noster", "pl")
    for language, texts in CHANGED.items():
        sites = provenance(language)
        for text in texts:
            doc, lay = core(text), layer(language, text)
            assert check_layer(doc, lay, layer_path(language, text)) == []
            assert prose.check(lay) == []
            for segment in doc["segments"]:
                if segment["type"] != "verse":
                    continue
                expected_protection = assert_protection_scope(
                    text, language, segment["id"], lay["segments"][segment["id"]]["translation"]
                )
                site = sites[f"{text}.{segment['id']}.{language}"]
                assert site["familiar_core"] is expected_protection and site["review"] == "working"
                assert site["source_sha256"] == canonical_hash(source_payload(segment))
                assert site["target_sha256"] == canonical_hash(
                    lay["segments"][segment["id"]]["translation"]
                )


def consumers(text):
    found = []
    for path in sorted((ROOT / "formularies").glob("*/*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        if any(c["text"] == text for c in doc["components"]):
            found.append(doc)
    return found


@pytest.mark.parametrize(
    "text,expected",
    [
        (PREFACE, ["sancti-ioseph-opificis"]),
        (TWIN, ["sancti-ioseph-sponsi-beatae-mariae-virginis"]),
    ],
)
def test_every_consumer_of_the_corrected_preface_reads_cleanly(text, expected):
    found = consumers(text)
    assert [doc["id"] for doc in found] == expected
    for formulary in found:
        for component in formulary["components"]:
            body = core(component["text"])
            for language in ("pl", "en"):
                lay = layer(language, component["text"])
                assert interlinear.check(body, lay) == [], (component["text"], language)
                assert check_layer(body, lay, layer_path(language, component["text"])) == []
