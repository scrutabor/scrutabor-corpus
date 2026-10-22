"""Saint Mark the Evangelist: word captions, verses, notes, the commemoration conclusion and the
source uses of its referenced and shared bodies.

Finite reviewed addresses and contexts, not general rules. Every outcome is pinned by a positive
check, and each check is shown to reject a named defect (usually the predecessor value).
"""

import json
import re
import unicodedata
from copy import deepcopy
from functools import cache
from pathlib import Path

import pytest

from build_reader import store
from build_reader.bibliography_bindings import digest, selected_text, transcript_digest
from checks import english, interlinear, interlinear_quality
from checks.apparatus import derived_summary
from checks.collate import collate
from checks.language_packs import check_layer
from checks.translation_provenance import canonical_hash, protected, source_payload

ROOT = Path(__file__).resolve().parents[1]
P = "proprium."
MARK = "sancti-marci-evangelistae"
LESSON = P + "sancti-matthaei-apostoli-et-evangelistae-epistola"
GOSPEL = P + "sancti-lucae-evangelistae-evangelium"
PREFACE = "ordinarium.praefatio-apostolorum"
SECRET = P + "dominica-i-passionis-secreta"
LM_C, LM_P = P + "litaniae-maiores-collecta", P + "litaniae-maiores-postcommunio"
MARK_COLLECT = P + MARK + "-collecta"
MARK_SECRET = P + MARK + "-secreta"
MARK_OFFERTORY = P + MARK + "-offertorium"
MARK_ALLELUIA = P + MARK + "-alleluia"
JOACHIM = P + "sancti-ioachim-confessoris-epistola"
VIGIL = P + "vigilia-pentecostes-evangelium"


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


@cache
def _graph():
    return json.loads((ROOT / "bibliography/graph.json").read_text(encoding="utf-8"))


def graph():
    return deepcopy(_graph())


def words(doc):
    return {w["id"]: w for s in doc["segments"] for w in s.get("words", [])}


def grouped(lay):
    return {
        w for s in lay["segments"].values() for g in s.get("alignments", []) for w in g["words"]
    }


def fold(token):
    text = unicodedata.normalize("NFD", token.lower()).replace("æ", "ae")
    return "".join(c for c in text if c.isalpha())


def rejects(check, *args, message):
    """The control: the check raises AssertionError whose first line names the defect."""
    with pytest.raises(AssertionError) as caught:
        check(*args)
    assert str(caught.value).splitlines()[0] == message


# --- word captions (PL-1..PL-10, EN-2..EN-10, EN-13 and the Polish nec sweep) ----------------
# (finding, language, text, word, Latin form, selected caption, predecessor caption)
GLOSSES = [
    ("PL-1", "pl", LESSON, "w002", "vultus", "oblicza", "obliczy"),
    ("PL-2", "pl", LESSON, "w011", "dextris", "prawej stronie", "prawej"),
    ("PL-2", "pl", LESSON, "w012", "ipsórum", "ich", "stronie"),
    ("PL-2", "pl", LESSON, "w018", "sinístris", "lewej stronie", "lewej"),
    ("PL-2", "pl", LESSON, "w019", "ipsórum", "ich", "stronie"),
    ("PL-3", "pl", LESSON, "w034", "duæ", "dwa", "Dwa"),
    ("PL-4", "pl", LESSON, "w050", "ubi", "gdzie", "dokąd"),
    ("PL-5", "pl", LESSON, "w056", "nec", "i nie", "ani"),
    ("PL-5", "pl", JOACHIM, "w014", "nec", "i nie", "ani"),
    ("PL-5", "pl", VIGIL, "w039", "nec", "i nie", "ani"),
    ("PL-7", "pl", GOSPEL, "w103", "dignus", "godzien", "Godzien"),
    ("PL-8", "pl", GOSPEL, "w140", "regnum", "królestwo", "Królestwo"),
    ("PL-9", "pl", MARK_SECRET, "w013", "illum", "go", "jego"),
    ("PL-10", "pl", PREFACE, "w011", "supplíciter", "pokornie", "błagalnie"),
    ("EN-2", "en", LESSON, "w034", "duæ", "two", "Two"),
    ("EN-3", "en", LESSON, "w056", "nec", "nor", "and not"),
    ("EN-3", "en", LESSON, "w057", "revertebántur", "did they turn back", "turn"),
    ("EN-4", "en", LESSON, "w080", "splendor", "the gleam", "The gleam"),
    ("EN-5", "en", GOSPEL, "w006", "et", "also", "and"),
    ("EN-6", "en", GOSPEL, "w016", "suam", "His", "Him"),
    ("EN-7", "en", GOSPEL, "w040", "mittat", "He send forth", "to send forth"),
    ("EN-8", "en", GOSPEL, "w046", "ecce", "behold", "Behold"),
    ("EN-8", "en", GOSPEL, "w093", "autem", "and", "And"),
    ("EN-10", "en", GOSPEL, "w138", "in", "to", "for"),
    ("EN-13", "en", MARK_OFFERTORY, "w011", "sanctórum", "of the saints", "of saints"),
]


def assert_gloss(doc, lay, row):
    finding, _language, _text, wid, form, gloss, _old = row
    assert words(doc)[wid]["form"] == form, f"{finding} Latin context"
    assert wid not in grouped(lay), f"{finding} word caption"
    assert lay["words"][wid].get("gloss") == gloss, f"{finding} caption"
    assert interlinear.check(doc, lay) == [], f"{finding} interlinear line"


@pytest.mark.parametrize("row", GLOSSES, ids=[f"{r[0]}-{r[2]}-{r[3]}" for r in GLOSSES])
def test_selected_caption(row):
    assert_gloss(core(row[2]), layer(row[1], row[2]), row)


@pytest.mark.parametrize("row", GLOSSES, ids=[f"{r[0]}-{r[2]}-{r[3]}" for r in GLOSSES])
def test_predecessor_caption_is_rejected(row):
    doc, lay = core(row[2]), layer(row[1], row[2])
    assert_gloss(doc, lay, row)
    lay["words"][row[3]]["gloss"] = row[6]
    rejects(assert_gloss, doc, lay, row, message=f"{row[0]} caption")


def test_the_same_psalm_phrase_reads_the_same_in_offertory_and_alleluia():
    offertory, alleluia = core(MARK_OFFERTORY), core(MARK_ALLELUIA)
    assert [words(offertory)[w]["form"] for w in ("w009", "w010", "w011")] == [
        "in",
        "ecclésia",
        "sanctórum",
    ]
    assert [words(alleluia)[w]["form"] for w in ("w011", "w012", "w013")] == [
        "in",
        "ecclésia",
        "sanctórum",
    ]
    readings = {
        layer("en", MARK_OFFERTORY)["words"]["w011"]["gloss"],
        layer("en", MARK_ALLELUIA)["words"]["w013"]["gloss"],
    }
    assert readings == {"of the saints"}


# Sweeps bound to their own denominators: no Polish `nec` caption reads `ani` before an
# un-negated verb caption, and the two `in vos` captions match their verbs.
def nec_ani_sites(text, lay=None):
    doc = core(text)
    lay = lay or layer("pl", text)
    out = []
    for segment in doc["segments"]:
        ws = segment.get("words", [])
        for i, word in enumerate(ws[:-1]):
            nxt = ws[i + 1]
            caption = lay["words"].get(nxt["id"], {}).get("gloss") or ""
            if (
                word["lemma"] == "nec"
                and lay["words"].get(word["id"], {}).get("gloss") == "ani"
                and nxt["morph"].get("pos") == "verb"
                and not caption.startswith("nie")
            ):
                out.append((text, word["id"]))
    return out


def polish_texts():
    return [
        f"{path.parent.name}.{path.stem}"
        for path in sorted((ROOT / "texts").glob("*/*.json"))
        if (ROOT / "languages/pl/texts" / path.parent.name / path.name).exists()
    ]


def test_no_polish_nec_reads_ani_before_an_unnegated_verb():
    examined = polish_texts()
    assert len(examined) == 1127
    assert [hit for text in examined for hit in nec_ani_sites(text)] == []
    # Positive control: the predecessor caption at the Lesson is found again.
    bad = layer("pl", LESSON)
    bad["words"]["w056"]["gloss"] = "ani"
    assert nec_ani_sites(LESSON, bad) == [(LESSON, "w056")]


def test_the_two_in_vos_captions_follow_their_verbs():
    lent = P + "dominica-iii-in-quadragesima-evangelium"
    found = []
    for text in (GOSPEL, lent):
        doc, lay = core(text), layer("en", text)
        for segment in doc["segments"]:
            ws = segment.get("words", [])
            for i, word in enumerate(ws[:-1]):
                if word["form"] == "in" and ws[i + 1]["form"].rstrip(",.:;") == "vos":
                    found.append((text, ws[i - 1]["lemma"], lay["words"][word["id"]].get("gloss")))
    assert found == [(GOSPEL, "appropinquo", "to"), (lent, "pervenio", "upon")]


# --- verses (EN-1, PL-6) and the retained speech-opening capital (PL-8) ------------------------
VERSES = [
    ("EN-1", "en", LESSON, "and each of them went straight ahead.", "before its own face"),
    ("PL-6", "pl", GOSPEL, "Idźcie: oto Ja posyłam was", "oto ja posyłam"),
]


def assert_verse(lay, text, row):
    finding, language, _text, present, absent = row
    prose = lay["segments"]["s01"]["translation"]
    assert present in prose and absent not in prose, f"{finding} verse"
    provenance = json.loads(
        (ROOT / f"languages/{language}/translation-provenance.json").read_text(encoding="utf-8")
    )
    (site,) = [s for s in provenance["sites"] if s["site"] == f"{text}.s01.{language}"]
    assert site["target_sha256"] == canonical_hash(prose), f"{finding} provenance"
    assert site["review"] == "working" and not protected(text, language, "s01")


@pytest.mark.parametrize("row", VERSES, ids=[r[0] for r in VERSES])
def test_selected_verse(row):
    assert_verse(layer(row[1], row[2]), row[2], row)


@pytest.mark.parametrize("row", VERSES, ids=[r[0] for r in VERSES])
def test_predecessor_verse_is_rejected(row):
    lay = layer(row[1], row[2])
    prose = lay["segments"]["s01"]["translation"]
    old = {
        "EN-1": "and each of them walked before its own face.",
        "PL-6": "Idźcie: oto ja posyłam was",
    }
    lay["segments"]["s01"]["translation"] = prose.replace(row[3], old[row[0]])
    rejects(assert_verse, lay, row[2], row, message=f"{row[0]} verse")


SPEECH_OPENINGS = ["mówił do nich: Żniwo", "powiedzcie: Pokój", "powiedzcie im: Królestwo Boże"]


def assert_speech_openings(prose):
    """PL-8 keeps the verse's quotation-opening capital; inside a sentence the corpus writes
    królestwo Boże lowercase (the interlinear caption w140 follows that)."""
    for opening in SPEECH_OPENINGS:
        assert opening in prose, "Polish quotation openings"


def test_quotation_openings_keep_their_capital_and_inner_kingdom_is_lowercase():
    prose = layer("pl", GOSPEL)["segments"]["s01"]["translation"]
    assert_speech_openings(prose)
    rejects(
        assert_speech_openings,
        prose.replace("im: Królestwo", "im: królestwo"),
        message="Polish quotation openings",
    )
    inner = []
    for text in polish_texts():
        for segment in layer("pl", text)["segments"].values():
            found = re.findall(
                r"(.{3})([Kk]rólestw\w*) (?:Boż|niebiesk)", segment.get("translation") or ""
            )
            inner += [(text, lead, word) for lead, word in found if not lead.endswith(": ")]
    assert len(inner) == 9 and all(word[0] == "k" for _, _, word in inner)


# --- English interlinear granularity: EN-9 and EN-12 -------------------------------------------
def g(first, last, anchor, gloss):
    return {
        "words": [f"w{i:03d}" for i in range(first, last + 1)],
        "anchor": f"w{anchor:03d}",
        "gloss": gloss,
    }


ALIGNMENTS = {
    (GOSPEL, "s01"): [
        g(99, 102, 102, "what they have"),
        g(103, 106, 103, "for the laborer is worthy"),
    ],
    (LM_C, "s01"): [
        g(8, 9, 8, "our affliction"),
        g(15, 16, 15, "all adversity"),
        g(17, 19, 19, "always by Your protection"),
        g(22, 23, 22, "our Lord"),
        g(26, 27, 26, "Your Son"),
        g(35, 36, 35, "of the Holy Spirit"),
        g(38, 41, 40, "forever and ever"),
    ],
    (LM_P, "s01"): [
        g(1, 2, 1, "Our prayers"),
        g(5, 6, 6, "with loving favor"),
        g(10, 11, 10, "Your gifts"),
        g(16, 17, 16, "our consolation"),
        g(19, 20, 20, "love for You"),
        g(23, 24, 23, "our Lord"),
        g(27, 28, 27, "Your Son"),
        g(36, 37, 36, "of the Holy Spirit"),
        g(39, 42, 41, "forever and ever"),
    ],
    (SECRET, "s01"): [
        g(7, 8, 8, "of our perversity"),
        g(17, 18, 17, "our Lord"),
        g(19, 20, 19, "Jesus Christ"),
        g(21, 22, 21, "Your Son"),
        g(23, 27, 25, "who lives and reigns with You"),
        g(30, 31, 30, "of the Holy Spirit"),
    ],
}
WORD_LINES = {
    LM_C: {
        "w010": "in",
        "w011": "Your",
        "w012": "compassion",
        "w013": "trust",
        "w020": "may be shielded",
    },
    LM_P: {
        "w003": "we pray",
        "w004": "Lord",
        "w007": "attend to",
        "w012": "in",
        "w013": "tribulation",
        "w014": "we receive",
        "w018": "in",
        "w021": "we may grow",
    },
    SECRET: {
        "w003": "we beseech",
        "w004": "Lord",
        "w006": "the bonds",
        "w009": "may loose",
        "w011": "of Your",
        "w012": "for us",
        "w013": "mercy",
        "w014": "the gifts",
        "w015": "may obtain",
    },
    GOSPEL: {},
}


def assert_alignments(doc, lay, text):
    for (owner, segment), expected in ALIGNMENTS.items():
        if owner == text:
            assert lay["segments"][segment]["alignments"] == expected, "English groups"
    for wid, gloss in WORD_LINES[text].items():
        assert lay["words"][wid] == {"gloss": gloss}, "English word captions"
    assert_group_rules(doc, lay, text)


def assert_group_rules(doc, lay, text):
    """Keep short groups and the single complete three-word protection phrase,
    quǽsumus alone, no vocative O, and clean language checks."""
    latin = words(doc)
    body_end = next((w for w, word in latin.items() if word["form"] == "Per"), None)
    for segment in lay["segments"].values():
        for group in segment.get("alignments", []):
            members = [latin[w] for w in group["words"]]
            assert not any(m["lemma"] == "quaeso" for m in members), "quaesumus stands alone"
            assert not re.search(r"(?<![A-Za-z])O (?=[A-Z])", group["gloss"]), "no vocative O"
            if body_end and text != GOSPEL and group["words"][-1] < body_end:
                assert len(group["words"]) <= 2 or (
                    text == LM_C and group == g(17, 19, 19, "always by Your protection")
                ), "smallest natural groups"
    assert interlinear.check(doc, lay) == [], "interlinear line"
    assert english.check(doc, lay) == [] and interlinear_quality.check(doc, lay) == []


@pytest.mark.parametrize("text", [GOSPEL, LM_C, LM_P, SECRET])
def test_english_groups_are_the_smallest_natural_ones(text):
    assert_alignments(core(text), layer("en", text), text)


PREDECESSOR_GROUPS = {
    GOSPEL: (["w099", "w100", "w101", "w102"], None, "English groups"),
    LM_C: (["w010", "w011", "w012", "w013"], "trust in Your compassion", "English groups"),
    LM_P: (
        [f"w{i:03d}" for i in range(1, 8)],
        "Attend to our prayers with loving favor, we pray, Lord",
        "English groups",
    ),
    SECRET: (
        ["w006", "w007", "w008", "w009"],
        "may loose the bonds of our perversity",
        "English groups",
    ),
}


@pytest.mark.parametrize("text", sorted(PREDECESSOR_GROUPS))
def test_predecessor_group_is_rejected(text):
    doc, lay = core(text), layer("en", text)
    members, gloss, message = PREDECESSOR_GROUPS[text]
    seg = lay["segments"]["s01"]
    if gloss is None:  # EN-9: the predecessor captioned each token
        seg["alignments"] = [a for a in seg["alignments"] if a["words"] != members]
        for wid, caption in zip(members, ["what", "with", "they", "have"], strict=True):
            lay["words"][wid] = {"gloss": caption}
    else:
        seg["alignments"] = [a for a in seg["alignments"] if not set(a["words"]) & set(members)]
        seg["alignments"].append({"words": members, "anchor": members[-1], "gloss": gloss})
        seg["alignments"].sort(key=lambda a: a["words"][0])
        for wid in members:
            lay["words"][wid].pop("gloss", None)
    rejects(assert_alignments, doc, lay, text, message=message)


@pytest.mark.parametrize(
    "damage,message",
    [
        ("quaesumus", "quaesumus stands alone"),
        ("particle", "no vocative O"),
        ("clause", "smallest natural groups"),
    ],
)
def test_the_group_rule_rejects_each_named_defect(damage, message):
    doc, lay = core(LM_P), layer("en", LM_P)
    assert_group_rules(doc, lay, LM_P)
    seg = lay["segments"]["s01"]
    if damage == "quaesumus":
        seg["alignments"] = [a for a in seg["alignments"] if a["words"] != ["w001", "w002"]]
        seg["alignments"].insert(0, g(1, 2, 1, "Our prayers"))
        seg["alignments"][0] = {
            "words": ["w001", "w002", "w003"],
            "anchor": "w001",
            "gloss": "our prayers, we pray",
        }
        lay["words"]["w003"] = {}
    elif damage == "particle":
        (group,) = [a for a in seg["alignments"] if a["words"] == ["w005", "w006"]]
        seg["alignments"].remove(group)
        seg["alignments"].insert(
            1,
            {
                "words": ["w004", "w005", "w006"],
                "anchor": "w006",
                "gloss": "O Lord, with loving favor",
            },
        )
        lay["words"]["w004"] = {}
    else:
        (group,) = [a for a in seg["alignments"] if a["words"] == ["w010", "w011"]]
        seg["alignments"].remove(group)
        seg["alignments"].insert(2, g(10, 14, 14, "we receive Your gifts in tribulation"))
        for wid in ("w012", "w013", "w014"):
            lay["words"][wid] = {}
    rejects(assert_group_rules, doc, lay, LM_P, message=message)


# --- about-notes: context-neutral shared bodies and one part-naming convention (SM-ABOUT-1) ---
ABOUT = {
    ("pl", LESSON): (
        "Epistola Ez 1, 10–14, wizja czterech istot, w Mszale Rzymskim z 1962 roku. Czyta się ją "
        "w formularzach „Świętego Mateusza Apostoła i Ewangelisty” i „Świętego Marka Ewangelisty”."
    ),
    ("en", LESSON): (
        "The epistola Ezekiel 1:10–14, the vision of the four living creatures, in the 1962 Roman "
        "Missal. It is read in the formularies “Saint Matthew, Apostle and Evangelist” and "
        "“Saint Mark the Evangelist”."
    ),
    ("pl", GOSPEL): (
        "Evangelium Łk 10, 1–9, rozesłanie siedemdziesięciu dwóch uczniów, w Mszale Rzymskim "
        "z 1962 roku. Czyta się je w formularzach „Świętego Łukasza Ewangelisty” i „Świętego "
        "Marka Ewangelisty”."
    ),
    ("en", GOSPEL): (
        "The evangelium Luke 10:1–9, the sending of the seventy-two, in the 1962 Roman Missal. "
        "It is read in the formularies “Saint Luke the Evangelist” and “Saint Mark the "
        "Evangelist”."
    ),
    ("pl", SECRET): (
        "Secreta „Hæc múnera” w Mszale Rzymskim z 1962 roku. Odmawia się ją w formularzu „1. "
        "Niedziela Męki Pańskiej” i we wspomnieniu Litanii Większych."
    ),
    ("en", SECRET): (
        "The secreta “Hæc múnera” in the 1962 Roman Missal. It is said in the formulary “First "
        "Passion Sunday” and in the commemoration of the Greater Litanies."
    ),
    ("pl", LM_C): "Collecta wspomnienia Litanii Większych w Mszale Rzymskim z 1962 roku.",
    (
        "en",
        LM_C,
    ): "The collecta of the commemoration of the Greater Litanies in the 1962 Roman Missal.",
    ("pl", LM_P): "Postcommunio wspomnienia Litanii Większych w Mszale Rzymskim z 1962 roku.",
    (
        "en",
        LM_P,
    ): "The postcommunio of the commemoration of the Greater Litanies in the 1962 Roman Missal.",
    ("pl", PREFACE): (
        "Prefacja o Apostołach. Prosi wiecznego Pasterza, aby nie opuszczał swej owczarni, lecz "
        "zachowywał ją pod opieką Apostołów."
    ),
    ("en", PREFACE): (
        "The Preface of the Apostles. It asks the eternal Shepherd not to forsake His flock, "
        "but to preserve it under the protection of the Apostles."
    ),
}


@pytest.mark.parametrize("key", sorted(ABOUT), ids=[f"{k[0]}-{k[1]}" for k in sorted(ABOUT)])
def test_selected_about_note(key):
    assert layer(*key)["about"] == ABOUT[key]


def consumers(text):
    """Formularies and commemorations whose components or slots name this text."""
    found = []
    for path in sorted((ROOT / "formularies").glob("*/*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        if any(c.get("text") == text for c in doc.get("components", [])):
            found.append(("formulary", path.parent.name, doc["id"]))
    for path in sorted((ROOT / "commemorationes").glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        if any(s.get("text") == text for s in doc.get("slots", [])):
            found.append(("commemoration", None, doc["id"]))
    return found


def named_uses(language, text, note, found=None):
    """The formulary titles a context-neutral note names must be exactly its consumers'."""
    found = consumers(text) if found is None else found
    titles = set()
    for kind, collection, identifier in found:
        if kind == "formulary":
            localized = ROOT / f"languages/{language}/formularies/{collection}/{identifier}.json"
            titles.add(json.loads(localized.read_text(encoding="utf-8"))["title"])
    quoted = set(re.findall(r"„([^”]+)”" if language == "pl" else r"“([^”]+)”", note))
    quoted -= {"Hæc múnera"}
    assert quoted == titles, "about names every consumer"
    commemorated = any(kind == "commemoration" for kind, _, _ in found)
    phrase = "Litanii Większych" if language == "pl" else "Greater Litanies"
    assert (phrase in note) == commemorated, "about names every consumer"


SHARED_NOTES = [(lang, text) for text in (LESSON, GOSPEL, SECRET) for lang in ("pl", "en")]


@pytest.mark.parametrize("key", SHARED_NOTES, ids=[f"{k[0]}-{k[1]}" for k in SHARED_NOTES])
def test_shared_note_names_its_consumers_not_one_home(key):
    language, text = key
    note = layer(language, text)["about"]
    named_uses(language, text, note)
    assert len(consumers(text)) == 2
    # Control: the predecessor note named only the home formulary.
    home = {
        LESSON: "sancti-matthaei-apostoli-et-evangelistae",
        GOSPEL: "sancti-lucae-evangelistae",
        SECRET: "dominica-i-passionis",
    }[text]
    only_home = [c for c in consumers(text) if c[2] == home]
    rejects(named_uses, language, text, note, only_home, message="about names every consumer")
    # Control: a further consumer must be named once it exists.
    extra = [*consumers(text), ("formulary", "sanctorale", "sancti-thomae-apostoli")]
    rejects(named_uses, language, text, note, extra, message="about names every consumer")


LATIN_PART = {
    "introitus": "introitus",
    "collecta": "collecta",
    "epistola": "epistola",
    "alleluia": "alleluia",
    "evangelium": "evangelium",
    "offertorium": "offertorium",
    "secreta": "secreta",
    "communio": "communio",
    "postcommunio": "postcommunio",
}


def part_name(text, note, language):
    role = text.rsplit("-", 1)[1]
    expected = LATIN_PART[role]
    head = note.split(" ", 2)[1] if language == "en" else note.split(" ", 1)[0]
    assert head.lower() == expected, "Latin part name"


MARK_NOTES = [
    (lang, text)
    for text in [
        P + MARK + "-" + r
        for r in (
            "introitus",
            "collecta",
            "alleluia",
            "offertorium",
            "secreta",
            "communio",
            "postcommunio",
        )
    ]
    + [LESSON, GOSPEL, SECRET, LM_C, LM_P]
    for lang in ("pl", "en")
]


@pytest.mark.parametrize("key", MARK_NOTES, ids=[f"{k[0]}-{k[1]}" for k in MARK_NOTES])
def test_notes_use_the_latin_part_name(key):
    language, text = key
    note = layer(language, text)["about"]
    part_name(text, note, language)
    vernacular = {
        "pl": {"collecta": "Kolekta", "postcommunio": "Modlitwa"},
        "en": {"collecta": "The collect", "postcommunio": "The postcommunion"},
    }[language]
    role = text.rsplit("-", 1)[1]
    if role in vernacular:
        rest = note.split(" ", 2)[2] if language == "en" else note.split(" ", 1)[1]
        wrong = vernacular[role] + " " + rest
        rejects(part_name, text, wrong, language, message="Latin part name")


def test_the_latin_part_name_is_the_corpus_majority():
    roles = (
        "introitus",
        "collecta",
        "epistola",
        "evangelium",
        "secreta",
        "communio",
        "postcommunio",
    )
    vernacular = {
        "pl": re.compile(
            r"^(Introit\b|Antyfona|Kolekta|Epistoła|Lekcja|Ewangelia|Sekreta|Modlitwa|Pokomunia)"
        ),
        "en": re.compile(
            r"^The (?:\w+ )?"
            r"(introit|collect|epistle|lesson|gospel|secret|communion|postcommunion)\b",
            re.I,
        ),
    }
    for language in ("pl", "en"):
        latin = other = 0
        for path in sorted((ROOT / "languages" / language / "texts").glob("*/*.json")):
            doc = json.loads(path.read_text(encoding="utf-8"))
            role = next((r for r in roles if doc["text"].endswith("-" + r)), None)
            if role is None:
                continue
            note = doc.get("about") or ""
            if re.match(rf"^(?:The )?{role}\b", note, re.I):
                latin += 1
            elif vernacular[language].match(note):
                other += 1
        assert latin > 2 * other > 0, (language, latin, other)


# --- the Greater-Litanies conclusion (SM-LAT-1) -----------------------------------------------
def conclusion(doc):
    tokens = [w["form"] + w.get("post", "") for s in doc["segments"] for w in s.get("words", [])]
    return " ".join(tokens[tokens.index("Per") :])


HOUSE = (
    "Per Dóminum nostrum Iesum Christum Fílium tuum: Qui tecum vivit et regnat in unitáte "
    "Spíritus Sancti, Deus, per ómnia sǽcula sæculórum. Amen."
)
LAT = {LM_C: ("w025", "w027", "w028"), LM_P: ("w026", "w028", "w029")}
APPARATUS = {
    LM_C: [
        ("w005", "ut", {"vatican": "ut,"}, "punctuation"),
        ("w025", "Christum", {"vatican": "Christum,"}, "punctuation"),
        ("w027", "tuum:", {"mr": "tuum,", "vatican": "tuum,"}, "punctuation"),
        ("w028", "Qui", {"mr": "qui", "vatican": "qui"}, "capitalization"),
    ],
    LM_P: [
        ("w026", "Christum", {"vatican": "Christum,"}, "punctuation"),
        ("w028", "tuum:", {"mr": "tuum,", "vatican": "tuum,"}, "punctuation"),
        ("w029", "Qui", {"mr": "qui", "vatican": "qui"}, "capitalization"),
    ],
}
LITERAL = {
    "mr": "Iesum Christum Filium tuum, qui tecum",
    "vatican": "Iesum Christum, Fílium tuum, qui tecum",
}


def assert_house_conclusion(doc, text, apparatus, records):
    assert conclusion(doc) == HOUSE == conclusion(core(MARK_COLLECT)), "house conclusion"
    christum, tuum, qui = (words(doc)[w] for w in LAT[text])
    assert (christum["lemma"], tuum["lemma"], qui["lemma"]) == ("Christus", "tuus", "qui")
    present = [(e["at"], e["ours"], e["witnesses"], e["class"]) for e in apparatus["adjudicated"]]
    assert all(entry in present for entry in APPARATUS[text]), "apparatus records RG115a"
    assert apparatus["summary"] == derived_summary(apparatus)
    witnesses, collation = records
    for witness in witnesses:
        path = ROOT / "witnesses" / text / f"{witness['transcription']}.txt"
        transcript = path.read_text(encoding="utf-8")
        assert witness["transcription_sha256"] == transcript_digest(transcript), "witness digest"
        assert LITERAL[witness["transcription"]] in transcript, "literal witness"
        assert witness["review"] == {"status": "pending"}
    assert collation["selected_text_sha256"] == digest(selected_text(doc)), "collation digest"
    assert collation["apparatus_sha256"] == digest(apparatus), "collation digest"
    assert collation["apparatus"] == derived_summary(apparatus)
    assert collation["review"] == {"status": "pending"}
    assert collate(doc, ROOT / "witnesses" / text)[0] == [], "collation"


def records(text):
    data = graph()
    return (
        [w for w in data["witnesses"] if w["text"] == text],
        next(c for c in data["collations"] if c["text"] == text),
    )


def apparatus(text):
    return json.loads((ROOT / f"witnesses/{text}/apparatus.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("text", [LM_C, LM_P])
def test_the_commemoration_conclusion_is_the_house_form(text):
    assert_house_conclusion(core(text), text, apparatus(text), records(text))
    pl, en = layer("pl", text), layer("en", text)
    assert pl["words"][LAT[text][2]] == {"gloss": "który"} and en["words"][LAT[text][2]] == {
        "gloss": "who"
    }
    assert pl["segments"]["s01"]["translation"].endswith(
        "Przez Pana naszego Jezusa Chrystusa, Syna Twojego, który z Tobą żyje i króluje w jedności "
        "Ducha Świętego, Bóg, na wieki wieków."
    )
    assert en["segments"]["s01"]["translation"].endswith(
        "Through our Lord Jesus Christ, Your Son, who lives and reigns with You in the unity "
        "of the Holy Spirit, God, forever and ever."
    )


CONCLUSION_DAMAGE = ["comma", "lowercase", "vatican-comma", "apparatus", "digest"]


@pytest.mark.parametrize("damage", CONCLUSION_DAMAGE)
@pytest.mark.parametrize("text", [LM_C, LM_P])
def test_conclusion_damage_is_rejected(text, damage):
    doc, app, recs = core(text), apparatus(text), records(text)
    christum, tuum, qui = (words(doc)[w] for w in LAT[text])
    message = "house conclusion"
    if damage == "comma":
        tuum["post"] = ","
    elif damage == "lowercase":
        qui["form"] = "qui"
    elif damage == "vatican-comma":
        christum["post"] = ","
    elif damage == "apparatus":
        app["adjudicated"] = [e for e in app["adjudicated"] if e["at"] != LAT[text][2]]
        message = "apparatus records RG115a"
    else:
        recs[1]["selected_text_sha256"] = digest(
            selected_text(core(LM_C if text == LM_P else LM_P))
        )
        message = "collation digest"
    rejects(assert_house_conclusion, doc, text, app, recs, message=message)


# --- source uses of the St Mark and Rogation printings (SM-SRC-1, SM-PROV-1) -------------------
LEAF = {
    592: "use.proprium.sancti-marci-evangelistae-collecta.mr1962",
    593: "use.proprium.sancti-marci-evangelistae-offertorium.mr1962",
}
ROGATION_LEAVES = {
    422: "482df21da0ee49067a251aa8146a8fe5e2eed453f9cfc10b95d3a76451eae3f1",
    423: "a35f08765f9742a9557a20261f9986c814d6a6bc39a75a60472a5cab3136f6a3",
}
USES = {
    f"use.{LESSON}.mark-reprint.mr1962": (
        LESSON,
        "p. 511",
        "leaf n592 / PDF p. 593",
        592,
        ["identical in letters, accents and punctuation to page 678"],
    ),
    f"use.{GOSPEL}.mark-reprint.mr1962": (
        GOSPEL,
        "pp. 511–512",
        "leaves n592–n593 / PDF pp. 593–594",
        592,
        ["dóminum messis ut mittat", "ecce ego mitto", "manéte edéntes", "follows page 705"],
    ),
    f"use.{SECRET}.rogation-reprint.mr1962": (
        SECRET,
        "p. 342",
        "leaf n423 / PDF p. 424",
        423,
        ["Mass of the Rogations", "page 121"],
    ),
    f"use.{SECRET}.mark-commemoration-reprint.mr1962": (
        SECRET,
        "p. 512",
        "leaf n593 / PDF p. 594",
        593,
        ["commemoration of the Rogations", "page 121"],
    ),
    f"use.{LM_C}.rogation-reprint.mr1962": (
        LM_C,
        "p. 341",
        "leaf n422 / PDF p. 423",
        422,
        ["ut, qui", "page 511"],
    ),
}


def assert_use(data, identifier):
    text, printed, scan, leaf, claims = USES[identifier]
    found = [u for u in data["uses"] if u["id"] == identifier]
    assert len(found) == 1, "source use"
    (use,) = found
    assert use["role"] == "direct_approved_print" and use["decision"] == "RETAIN", "source use"
    assert use["edition"] == "edition.missale-romanum.1962-typica", "source use"
    assert use["address"] == {"kind": "text", "text": text}, "source use"
    assert (use["locator"]["printed"], use["locator"]["scan"]) == (printed, scan), "source locator"
    assert use["locator"]["page_url"].endswith(f"/page/n{leaf}/mode/1up"), "source locator"
    expected = (
        ROGATION_LEAVES.get(leaf)
        or next(u for u in data["uses"] if u["id"] == LEAF[leaf])["evidence_sha256"]
    )
    assert use["evidence_sha256"] == expected, "source evidence"
    assert all(claim in use["claim"] for claim in claims), "source claim"
    assert use["verified_on"] == "2026-10-20"


@pytest.mark.parametrize("identifier", sorted(USES))
def test_source_use_of_the_reprint(identifier):
    assert_use(graph(), identifier)


@pytest.mark.parametrize("identifier", sorted(USES))
@pytest.mark.parametrize("damage", ["missing", "leaf", "evidence", "claim"])
def test_source_use_damage_is_rejected(identifier, damage):
    data = graph()
    (use,) = [u for u in data["uses"] if u["id"] == identifier]
    message = {
        "missing": "source use",
        "leaf": "source locator",
        "evidence": "source evidence",
        "claim": "source claim",
    }[damage]
    if damage == "missing":
        data["uses"].remove(use)
    elif damage == "leaf":
        use["locator"]["page_url"] = use["locator"]["page_url"].replace("/page/n", "/page/n1")
    elif damage == "evidence":
        other = 423 if USES[identifier][3] != 423 else 422
        use["evidence_sha256"] = ROGATION_LEAVES[other]
    else:
        use["claim"] = use["claim"].replace(USES[identifier][4][0], "")
    rejects(assert_use, data, identifier, message=message)


# The shared Gospel follows St Luke's page; St Mark's reprint differs in four accidentals only.
MARK_ACCIDENTALS = [
    ("w037", "Dóminum", "dóminum", "Rogáte ergo dóminum messis ut mittat"),
    ("w038", "messis,", "messis", "Rogáte ergo dóminum messis ut mittat"),
    ("w046", "ecce,", "ecce", "Ite: ecce ego mitto"),
    ("w095", "manéte,", "manéte", "manéte edéntes"),
]


def assert_gospel_ruling(doc, note):
    tokens = [
        (w["id"], w["form"] + w.get("post", ""))
        for s in doc["segments"]
        for w in s.get("words", [])
    ]
    transcript = (ROOT / f"witnesses/{GOSPEL}/mr.txt").read_text(encoding="utf-8")
    printed = " ".join(
        line for line in transcript.splitlines() if line and not line.startswith("#")
    ).split()
    assert [t for _, t in tokens] == printed, "follows page 705"
    position = {wid: i for i, (wid, _) in enumerate(tokens)}
    for wid, ours, mark, phrase in MARK_ACCIDENTALS:
        assert tokens[position[wid]][1] == ours, "follows page 705"
        assert fold(ours) == fold(mark) and ours != mark, "accidental only"
        assert phrase in note and mark in phrase.split(), "apparatus ruling"
    assert "follows the St Luke printing on p. 705" in note, "apparatus ruling"
    assert "pp. 511–512" in note, "apparatus ruling"


def test_the_shared_gospel_ruling_lists_the_four_accidentals():
    assert_gospel_ruling(core(GOSPEL), apparatus(GOSPEL)["note"])
    data = graph()
    (collation,) = [c for c in data["collations"] if c["text"] == GOSPEL]
    assert collation["apparatus_sha256"] == digest(apparatus(GOSPEL))
    assert collation["review"] == {"status": "pending"}


@pytest.mark.parametrize("damage", ["ruling", "mark-reading", "selected-token"])
def test_the_gospel_ruling_rejects_damage(damage):
    doc, note = core(GOSPEL), apparatus(GOSPEL)["note"]
    message = "apparatus ruling"
    if damage == "ruling":
        note = note.replace("follows the St Luke printing on p. 705", "follows St Mark")
    elif damage == "mark-reading":
        note = note.replace("(manéte edéntes)", "(manéte, edéntes)")
    else:
        words(doc)["w046"]["post"] = ""  # adopt St Mark's ecce ego
        message = "follows page 705"
    rejects(assert_gospel_ruling, doc, note, message=message)


def test_reviews_stay_pending_for_every_touched_source_record():
    data = graph()
    for text in (LESSON, GOSPEL, SECRET, LM_C, LM_P):
        for section in ("witnesses", "collations"):
            rows = [r for r in data[section] if r["text"] == text]
            assert rows and all(r["review"] == {"status": "pending"} for r in rows)


# --- provenance, protection and every consumer of the shared bodies ----------------------------
CHANGED = {
    "pl": [LESSON, JOACHIM, VIGIL, GOSPEL, PREFACE, MARK_SECRET, LM_C, LM_P, SECRET],
    "en": [LESSON, GOSPEL, PREFACE, MARK_OFFERTORY, LM_C, LM_P, SECRET],
}


def test_changed_sites_are_outside_the_protected_formulas_and_their_provenance_is_current():
    assert protected("orationes.gloria-patri", "pl") and protected("orationes.pater-noster", "pl")
    for language, texts in CHANGED.items():
        provenance = {
            s["site"]: s
            for s in json.loads(
                (ROOT / f"languages/{language}/translation-provenance.json").read_text(
                    encoding="utf-8"
                )
            )["sites"]
        }
        for text in texts:
            doc, lay = core(text), layer(language, text)
            assert (
                check_layer(
                    doc,
                    lay,
                    ROOT / "languages" / language / "texts" / (text.replace(".", "/", 1) + ".json"),
                )
                == []
            )
            for segment in doc["segments"]:
                if segment["type"] != "verse":
                    continue
                assert not protected(text, language, segment["id"]), (text, segment["id"])
                site = provenance[f"{text}.{segment['id']}.{language}"]
                assert site["source_sha256"] == canonical_hash(source_payload(segment))
                assert site["target_sha256"] == canonical_hash(
                    lay["segments"][segment["id"]]["translation"]
                )


CONSUMERS = {
    LESSON: ["sancti-marci-evangelistae", "sancti-matthaei-apostoli-et-evangelistae"],
    GOSPEL: ["sancti-lucae-evangelistae", "sancti-marci-evangelistae"],
    SECRET: ["dominica-i-passionis", "litaniae-maiores"],
    LM_C: ["litaniae-maiores"],
    LM_P: ["litaniae-maiores"],
    PREFACE: [
        "cathedra-sancti-petri",
        "sancti-andreae-apostoli",
        "sancti-bartholomaei-apostoli",
        "sancti-iacobi-apostoli",
        "sancti-lucae-evangelistae",
        "sancti-marci-evangelistae",
        "sancti-matthaei-apostoli-et-evangelistae",
        "sancti-matthiae-apostoli",
        "sancti-petri-et-pauli-apostolorum",
        "sancti-thomae-apostoli",
        "sanctorum-philippi-et-iacobi-apostolorum",
        "sanctorum-simonis-et-iudae-apostolorum",
    ],
}


@pytest.mark.parametrize("text", sorted(CONSUMERS))
def test_every_consumer_reaches_the_one_corrected_body(text):
    assert sorted(c[2] for c in consumers(text)) == CONSUMERS[text]
    for kind, collection, identifier in consumers(text):
        if kind != "formulary":
            continue
        doc = json.loads(
            (ROOT / f"formularies/{collection}/{identifier}.json").read_text(encoding="utf-8")
        )
        for component in doc["components"]:
            body = core(component["text"])
            for language in ("pl", "en"):
                lay = layer(language, component["text"])
                assert interlinear.check(body, lay) == [], (identifier, component["text"], language)
