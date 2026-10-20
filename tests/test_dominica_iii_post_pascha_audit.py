"""III Sunday after Easter: word captions, source witness and their bounded successors.

Finite reviewed addresses and contexts, not general rules. Every outcome is pinned by a
positive check, and each check is shown to reject a named defect.
"""

import json
import re
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import store
from build_reader.bibliography_bindings import transcript_digest
from checks import collate, interlinear
from checks.language_packs import check_layer
from checks.translation_provenance import canonical_hash, protected, source_payload

ROOT = Path(__file__).resolve().parents[1]
III = "proprium.dominica-iii-post-pascha-"
V_INTROIT = "proprium.dominica-v-post-pascha-introitus"
PREFACE = "ordinarium.praefatio-paschalis"


def core(text):
    return store.core(ROOT, text)


def layer(language, text):
    return store.raw_layer(ROOT, language, text)


def layer_path(language, text):
    return ROOT / "languages" / language / "texts" / (text.replace(".", "/", 1) + ".json")


def words(doc):
    return {w["id"]: w for s in doc["segments"] for w in s.get("words", [])}


def ids(first, count):
    return [f"w{first + offset:03d}" for offset in range(count)]


def touching(lay, members, segment="s01"):
    return [
        g for g in lay["segments"][segment].get("alignments", []) if set(g["words"]) & set(members)
    ]


# Polish Introit: the word layer glosses date glóriam laudi eius word by word, exactly as the
# V Sunday Introit does for the identical Latin (w026–w029); the verse keeps its wording.
INTROIT_FIRSTS = (11, 64)
INTROIT_TOKENS = ["oddajcie", "chwałę", "uwielbieniu", "Jego"]


def assert_introit(doc, lay, v_doc, v_lay):
    v_ids = ids(26, 4)
    assert [v_lay["words"][w].get("gloss") for w in v_ids] == INTROIT_TOKENS
    note = v_lay["words"]["w028"]["explanation"]
    assert v_doc["localization"]["explanations"]["w028"] == {"languages": ["pl"]}
    latin, v_latin = words(doc), words(v_doc)
    for first in INTROIT_FIRSTS:
        members = ids(first, 4)
        assert [(latin[w]["lemma"], latin[w]["morph"]) for w in members] == [
            (v_latin[w]["lemma"], v_latin[w]["morph"]) for w in v_ids
        ]
        assert latin[members[2]]["morph"]["case"] == "dat"
        assert not touching(lay, members)
        assert [lay["words"][w].get("gloss") for w in members] == INTROIT_TOKENS
        assert lay["words"][members[2]].get("explanation") == note
        assert doc["localization"]["explanations"][members[2]] == {"languages": ["pl"]}
    assert lay["segments"]["s01"]["translation"].count("oddajcie Mu chwałę, wysławiając Go") == 2
    assert check_layer(doc, lay, layer_path("pl", doc["id"])) == []


def introit_subject():
    return (
        core(III + "introitus"),
        layer("pl", III + "introitus"),
        core(V_INTROIT),
        layer("pl", V_INTROIT),
    )


def test_polish_introit_glosses_words_like_the_fifth_sunday():
    assert_introit(*introit_subject())


@pytest.mark.parametrize("damage", ["regroup", "paraphrase", "note", "fifth-sunday"])
def test_polish_introit_damage_is_rejected(damage):
    doc, lay, v_doc, v_lay = introit_subject()
    assert_introit(doc, lay, v_doc, v_lay)
    bad, v_bad = deepcopy(lay), deepcopy(v_lay)
    members = ids(64, 4)
    if damage == "regroup":
        for wid in members:
            bad["words"][wid].pop("gloss")
        bad["segments"]["s01"]["alignments"] = [
            {"words": members, "anchor": members[0], "gloss": "oddajcie Mu chwałę, wysławiając Go"}
        ]
    elif damage == "paraphrase":
        bad["words"]["w013"]["gloss"] = "wysławiając Go"
    elif damage == "note":
        bad["words"]["w066"].pop("explanation")
    else:
        v_bad["words"]["w028"]["gloss"] = "wysławiając Go"
    with pytest.raises(AssertionError):
        assert_introit(doc, bad, v_doc, v_bad)
    assert_introit(doc, lay, v_doc, v_lay)


# Polish Postcommunion: corporálibus … auxíliis stays an adjective with its instrumental noun.
POSTCOMMUNION_TOKENS = ["cielesną", "niech chronią", "pomocą"]


def assert_postcommunion(doc, lay):
    members = ids(12, 3)
    latin = words(doc)
    assert [(latin[w]["lemma"], latin[w]["morph"]["pos"]) for w in members] == [
        ("corporalis", "adj"),
        ("tueor", "verb"),
        ("auxilium", "noun"),
    ]
    assert latin["w012"]["morph"]["case"] == latin["w014"]["morph"]["case"] == "abl"
    assert not touching(lay, members)
    assert [lay["words"][w].get("gloss") for w in members] == POSTCOMMUNION_TOKENS
    assert [g["words"] for g in lay["segments"]["s01"]["alignments"]] == [ids(7, 4)]
    assert "jak i chronią nas, niosąc pomoc ciału" in lay["segments"]["s01"]["translation"]
    assert interlinear.check(doc, lay) == []


def test_polish_postcommunion_keeps_the_adjective():
    assert_postcommunion(core(III + "postcommunio"), layer("pl", III + "postcommunio"))


@pytest.mark.parametrize("damage", ["regroup", "noun", "participle"])
def test_polish_postcommunion_damage_is_rejected(damage):
    doc, lay = core(III + "postcommunio"), layer("pl", III + "postcommunio")
    assert_postcommunion(doc, lay)
    bad = deepcopy(lay)
    if damage == "regroup":
        for wid in ids(12, 3):
            bad["words"][wid].pop("gloss")
        bad["segments"]["s01"]["alignments"].append(
            {
                "words": ids(12, 3),
                "anchor": "w013",
                "gloss": "niech chronią nas, niosąc pomoc ciału",
            }
        )
    elif damage == "noun":
        bad["words"]["w012"]["gloss"] = "ciału"
    else:
        bad["words"]["w014"]["gloss"] = "niosąc pomoc"
    with pytest.raises(AssertionError):
        assert_postcommunion(doc, bad)
    assert_postcommunion(doc, lay)


# Paschal Prefaces, Polish: the predicate instrumental is explained once, on verus, in the
# seasonal preface and in its Easter-day and Easter-night twins (one word later there).
PREFACES = [PREFACE, PREFACE + "-in-die", PREFACE + "-in-nocte"]
VERUS = {PREFACE: 28, PREFACE + "-in-die": 29, PREFACE + "-in-nocte": 29}


def assert_one_instrumental_note(doc, lay):
    verus, est, agnus = ids(VERUS[doc["id"]], 3)
    latin = words(doc)
    assert [latin[w]["form"] for w in (verus, est, agnus)] == ["verus", "est", "Agnus"]
    explained = [w for w in (verus, agnus) if "explanation" in lay["words"][w]]
    assert explained == [verus]
    assert "„prawdziwym Barankiem”" in lay["words"][verus]["explanation"]
    assert [lay["words"][w]["gloss"] for w in (verus, est, agnus)] == [
        "prawdziwym",
        "jest",
        "Barankiem",
    ]
    declared = doc["localization"]["explanations"]
    assert declared[verus] == {"languages": ["pl"]} and agnus not in declared
    assert check_layer(doc, lay, layer_path("pl", doc["id"])) == []


@pytest.mark.parametrize("text", PREFACES)
def test_preface_explains_the_polish_instrumental_once(text):
    assert_one_instrumental_note(core(text), layer("pl", text))


@pytest.mark.parametrize("text", PREFACES)
@pytest.mark.parametrize("damage", ["second", "none"])
def test_preface_note_damage_is_rejected(text, damage):
    doc, lay = core(text), layer("pl", text)
    assert_one_instrumental_note(doc, lay)
    bad_doc, bad = deepcopy(doc), deepcopy(lay)
    verus, _, agnus = ids(VERUS[text], 3)
    if damage == "second":
        bad["words"][agnus]["explanation"] = (
            "Agnus jest łacińskim mianownikiem. W polskim orzeczeniu „jest Barankiem” "
            "używamy narzędnika."
        )
        bad_doc["localization"]["explanations"][agnus] = {"languages": ["pl"]}
    else:
        bad["words"][verus].pop("explanation")
    with pytest.raises(AssertionError):
        assert_one_instrumental_note(bad_doc, bad)
    assert_one_instrumental_note(doc, lay)


# Gospel, English: De hoc quǽritis inter vos, quia dixi — the clause says what they ask about.
GOSPEL = III + "evangelium"
GOSPEL_CLAUSE = "You are asking one another about this, that I said: A little while"


def provenance_record(language, text, segment="s01"):
    sites = json.loads((ROOT / "languages" / language / "translation-provenance.json").read_text())
    (record,) = [r for r in sites["sites"] if r["site"] == f"{text}.{segment}.{language}"]
    return record


def assert_gospel_relation(doc, lay, record):
    latin = words(doc)
    assert [latin[w]["form"] for w in ids(74, 7)] == [
        "De",
        "hoc",
        "quǽritis",
        "inter",
        "vos",
        "quia",
        "dixi",
    ]
    assert latin["w079"]["lemma"] == "quia"
    assert lay["words"]["w079"]["gloss"] == "that"
    text = lay["segments"]["s01"]["translation"]
    assert text.count(GOSPEL_CLAUSE) == 1 and "because I said" not in text
    segment = next(s for s in doc["segments"] if s["id"] == "s01")
    assert record["source_sha256"] == canonical_hash(source_payload(segment))
    assert record["target_sha256"] == canonical_hash(text)
    assert (record["origin"], record["review"], record["familiar_core"]) == (
        "working-unsettled",
        "working",
        False,
    )
    assert interlinear.check(doc, lay) == []


def test_english_gospel_states_what_they_ask_about():
    assert_gospel_relation(core(GOSPEL), layer("en", GOSPEL), provenance_record("en", GOSPEL))


@pytest.mark.parametrize("damage", ["verse", "gloss", "stale-target", "promoted"])
def test_english_gospel_damage_is_rejected(damage):
    doc, lay, record = core(GOSPEL), layer("en", GOSPEL), provenance_record("en", GOSPEL)
    assert_gospel_relation(doc, lay, record)
    bad, bad_record = deepcopy(lay), deepcopy(record)
    if damage == "verse":
        text = bad["segments"]["s01"]["translation"]
        bad["segments"]["s01"]["translation"] = text.replace("that I said:", "because I said:")
        bad_record["target_sha256"] = canonical_hash(bad["segments"]["s01"]["translation"])
    elif damage == "gloss":
        bad["words"]["w079"]["gloss"] = "because"
    elif damage == "stale-target":
        bad_record["target_sha256"] = (
            "345a9c9e1f293e0e70c06ede54f34725d9602a6ad98e52433a10030dfdeaedd8"
        )
    else:
        bad_record["origin"] = "own"
    with pytest.raises(AssertionError):
        assert_gospel_relation(doc, bad, bad_record)
    assert_gospel_relation(doc, lay, record)


# English group captions render words; the vocative particle O renders none (2026-08-17).
VOCATIVE_GROUPS = [
    ("proprium.dominica-ii-passionis-postcommunio", 2, 5, 4, "Lord, the working of this mystery"),
    (
        "proprium.dominica-iii-post-epiphaniam-postcommunio",
        1,
        6,
        4,
        "We, whom You graciously allow, Lord, to partake of such great mysteries,",
    ),
    (
        "proprium.dominica-iii-post-epiphaniam-secreta",
        1,
        5,
        1,
        "May this Victim, Lord, we beseech You, cleanse",
    ),
    (III + "secreta", 1, 5, 5, "By these mysteries, Lord, may it be granted to us"),
    (
        "proprium.dominica-in-septuagesima-collecta",
        1,
        7,
        7,
        "We beseech You, Lord, graciously hear the prayers of Your people",
    ),
    (
        "proprium.dominica-in-septuagesima-postcommunio",
        1,
        7,
        7,
        "May Your faithful, God, be strengthened by Your gifts",
    ),
    (
        "proprium.dominica-infra-octavam-nativitatis-postcommunio",
        2,
        5,
        4,
        "Lord, the working of this mystery",
    ),
    (
        "proprium.dominica-iv-post-epiphaniam-postcommunio",
        3,
        8,
        8,
        "may free us, God, from earthly delights",
    ),
    (
        "proprium.dominica-vi-post-epiphaniam-postcommunio",
        1,
        4,
        3,
        "Nourished by heavenly delights, Lord,",
    ),
    (
        "proprium.dominica-vi-post-epiphaniam-secreta",
        1,
        6,
        5,
        "May this offering, God, we beseech You, cleanse us",
    ),
    (
        "proprium.in-octava-nativitatis-postcommunio",
        1,
        5,
        5,
        "May this Communion, Lord, cleanse us",
    ),
    (
        "proprium.litaniae-maiores-postcommunio",
        1,
        7,
        7,
        "Attend to our prayers with loving favor, we pray, Lord",
    ),
    (
        "proprium.nativitas-domini-in-aurora-postcommunio",
        1,
        8,
        8,
        "May the newness of the birth of this Sacrament ever renew us, Lord",
    ),
    ("proprium.nativitas-domini-in-die-secreta", 1, 3, 3, "The offered gifts, Lord,"),
    (
        "proprium.sanctorum-innocentium-martyrum-secreta",
        1,
        8,
        7,
        "May the gracious prayer of Your saints not fail us, Lord",
    ),
]
PARTICLE = re.compile(r"(?<![A-Za-z])O (?=[A-Z])")


def vocative_particles(doc, lay):
    """English captions of a Latin vocative that carry O, unless a Latin O is captioned too."""
    found = []
    for segment in doc["segments"]:
        latin = {w["id"]: w for w in segment.get("words", [])}
        for group in lay["segments"].get(segment["id"], {}).get("alignments", []):
            members = [latin[w] for w in group["words"]]
            if any(m.get("lemma") == "o" for m in members):
                continue
            vocative = any(m.get("morph", {}).get("case") == "voc" for m in members)
            if vocative and PARTICLE.search(group.get("gloss") or ""):
                found.append((doc["id"], group["words"][0], group["gloss"]))
        for wid, word in latin.items():
            gloss = (lay["words"].get(wid) or {}).get("gloss") or ""
            if word.get("morph", {}).get("case") == "voc" and PARTICLE.search(gloss):
                found.append((doc["id"], wid, gloss))
    return found


def assert_vocative_group(doc, lay, site):
    _, first, last, anchor, gloss = site
    members = ids(first, last - first + 1)
    latin = words(doc)
    assert [latin[w]["morph"].get("case") for w in members].count("voc") == 1
    assert touching(lay, members) == [
        {"words": members, "anchor": f"w{anchor:03d}", "gloss": gloss}
    ]
    assert all("gloss" not in lay["words"][w] for w in members)
    assert re.search(r"\b(Lord|God)\b", gloss)
    assert vocative_particles(doc, lay) == []
    assert interlinear.check(doc, lay) == []


@pytest.mark.parametrize("site", VOCATIVE_GROUPS, ids=[s[0] for s in VOCATIVE_GROUPS])
def test_english_vocative_group_has_no_particle(site):
    assert_vocative_group(core(site[0]), layer("en", site[0]), site)


@pytest.mark.parametrize("site", VOCATIVE_GROUPS, ids=[s[0] for s in VOCATIVE_GROUPS])
def test_restored_particle_is_rejected(site):
    doc, lay = core(site[0]), layer("en", site[0])
    assert_vocative_group(doc, lay, site)
    bad = deepcopy(lay)
    first = f"w{site[1]:03d}"
    (group,) = [g for g in bad["segments"]["s01"]["alignments"] if g["words"][0] == first]
    group["gloss"] = re.sub(r"\b(Lord|God)\b", r"O \1", group["gloss"], count=1)
    assert vocative_particles(doc, bad) == [(site[0], first, group["gloss"])]
    with pytest.raises(AssertionError):
        assert_vocative_group(doc, bad, site)
    assert_vocative_group(doc, lay, site)


def english_texts():
    for path in sorted((ROOT / "texts").glob("*/*.json")):
        text = f"{path.parent.name}.{path.stem}"
        if layer_path("en", text).exists():
            yield text


def test_no_english_vocative_caption_carries_the_particle():
    examined = list(english_texts())
    assert len(examined) == 1127
    found = [hit for text in examined for hit in vocative_particles(core(text), layer("en", text))]
    assert found == []
    # Positive control: a Latin O captioned with its vocative is a real word, not the particle.
    doc = {
        "id": "x",
        "segments": [
            {
                "id": "s01",
                "words": [
                    {"id": "w001", "form": "O", "lemma": "o", "morph": {"pos": "intj"}},
                    {"id": "w002", "form": "Dómine", "lemma": "dominus", "morph": {"case": "voc"}},
                ],
            }
        ],
    }
    group = {"words": ["w001", "w002"], "anchor": "w002", "gloss": "O Lord"}
    lay = {"segments": {"s01": {"alignments": [group]}}, "words": {"w001": {}, "w002": {}}}
    assert vocative_particles(doc, lay) == []
    group["words"], lay["words"]["w001"] = ["w002"], {"gloss": "O"}
    assert vocative_particles(doc, lay) == [("x", "w002", "O Lord")]


# Paschal Preface, English: the opening clause is captioned word by word in all three variants.
SPLIT = {
    PREFACE: (
        [
            "Te",
            "quidem",
            "Dómine",
            "omni",
            "témpore",
            "sed",
            "in",
            "hoc",
            "potíssimum",
            "gloriósius",
            "prædicáre",
        ],
        [
            "You",
            "indeed",
            "Lord",
            "at every",
            "time",
            "but",
            "at",
            "this",
            "especially",
            "more gloriously",
            "to praise",
        ],
    ),
    PREFACE + "-in-die": (
        [
            "Te",
            "quidem",
            "Dómine",
            "omni",
            "témpore",
            "sed",
            "in",
            "hac",
            "potíssimum",
            "die",
            "gloriósius",
            "prædicáre",
        ],
        [
            "You",
            "indeed",
            "Lord",
            "at every",
            "time",
            "but",
            "on",
            "this",
            "especially",
            "day",
            "more gloriously",
            "to praise",
        ],
    ),
    PREFACE + "-in-nocte": (
        [
            "Te",
            "quidem",
            "Dómine",
            "omni",
            "témpore",
            "sed",
            "in",
            "hac",
            "potíssimum",
            "nocte",
            "gloriósius",
            "prædicáre",
        ],
        [
            "You",
            "indeed",
            "Lord",
            "at every",
            "time",
            "but",
            "on",
            "this",
            "especially",
            "night",
            "more gloriously",
            "to praise",
        ],
    ),
}


# The note no longer repeats what the caption of gloriósius now says.
WHEN_NOTES = {
    PREFACE: "Omni tempore and in hoc potissimum both describe when God is praised. "
    "Hoc refers to the present time.",
    PREFACE + "-in-die": "Omni tempore and hac potissimum die both describe when God is praised.",
    PREFACE + "-in-nocte": "Omni tempore and hac potissimum nocte both describe when God is "
    "praised.",
}


def assert_split(doc, lay, forms, tokens):
    members = ids(9, len(forms))
    latin = words(doc)
    assert [latin[w]["form"] for w in members] == forms
    assert not touching(lay, members)
    assert [lay["words"][w].get("gloss") for w in members] == tokens
    assert lay["words"][members[-1]]["explanation"] == WHEN_NOTES[doc["id"]]
    assert all("Gloriosius" not in (lay["words"][w].get("explanation") or "") for w in members)
    verse = "to praise You, Lord, at all times, but more gloriously especially "
    assert verse in lay["segments"]["s01"]["translation"]
    assert interlinear.check(doc, lay) == []


@pytest.mark.parametrize("text", sorted(SPLIT))
def test_preface_opening_clause_is_captioned_word_by_word(text):
    assert_split(core(text), layer("en", text), *SPLIT[text])


def captions(text):
    lay = layer("en", text)
    return [lay["words"][w].get("gloss") for w in ids(9, len(SPLIT[text][0]))]


def test_preface_variants_share_their_word_captions():
    seasonal = captions(PREFACE)
    for variant, noun in (("-in-die", "day"), ("-in-nocte", "night")):
        expected = [*seasonal[:6], "on", "this", "especially", noun, *seasonal[9:]]
        assert captions(PREFACE + variant) == expected


@pytest.mark.parametrize("text", sorted(SPLIT))
@pytest.mark.parametrize("damage", ["regroup", "missing", "drift", "restated-note"])
def test_preface_split_damage_is_rejected(text, damage):
    doc, lay = core(text), layer("en", text)
    forms, tokens = SPLIT[text]
    assert_split(doc, lay, forms, tokens)
    bad = deepcopy(lay)
    members = ids(9, len(forms))
    if damage == "regroup":
        for wid in members:
            bad["words"][wid].pop("gloss")
        bad["segments"]["s01"]["alignments"].append(
            {
                "words": members,
                "anchor": members[-1],
                "gloss": "indeed to praise You, Lord, at all times",
            }
        )
    elif damage == "missing":
        bad["words"][members[4]].pop("gloss")
    elif damage == "drift":
        bad["words"][members[4]]["gloss"] = "times"
    else:
        bad["words"][members[-1]]["explanation"] += " Gloriosius means “more gloriously”."
    with pytest.raises(AssertionError):
        assert_split(doc, bad, forms, tokens)
    assert_split(doc, lay, forms, tokens)


# Caption case: a caption at a genuine sentence or quotation opening follows the target
# sentence's capital; inside a sentence it is lower case. Bounded to the ten texts of this Mass.
CASE_TEXTS = [
    III + role
    for role in (
        "introitus",
        "collecta",
        "epistola",
        "alleluia",
        "evangelium",
        "offertorium",
        "secreta",
        "communio",
        "postcommunio",
    )
] + [PREFACE]
WHO_LIVES = "who lives and reigns with You"
# Reviewed lower-case captions at a Latin opening whose target sentence continues.
CONTINUATIONS = {
    ("pl", III + "collecta", "w041"): "który",
    ("pl", III + "secreta", "w020"): "który",
    ("pl", III + "postcommunio", "w022"): "który",
    ("en", III + "collecta", "w041"): WHO_LIVES,
    ("en", III + "secreta", "w020"): WHO_LIVES,
    ("en", III + "postcommunio", "w022"): WHO_LIVES,
    ("en", III + "epistola", "w096"): "fear God",
    ("en", GOSPEL, "w004"): "said",
    ("en", GOSPEL, "w060"): "a little while",
}
# Reviewed capitals at a Latin lower-case word where the target opens a new sentence.
OPENED = {
    ("pl", GOSPEL, "w061"): "Nie wiemy",
    ("en", GOSPEL, "w061"): "We do not know",
}
# Capitals a lower-case Latin word may carry anywhere here: words for God and Christ, English I.
NAMED = {
    "pl": {"Ci", "Go", "Jego", "Mnie", "Twoi", "Twoje", "Twojego", "Twojej"},
    "en": {"He", "His", "I", "Me", "Your"},
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
                if gloss[:1].islower() and CONTINUATIONS.get(key) != gloss:
                    misses.append((first["id"], gloss))
            elif first["form"][:1].islower():
                word = re.search(r"[^\W\d_]+", gloss)
                capital = word is not None and word[0][:1].isupper()
                if capital and word[0] not in NAMED[language] and OPENED.get(key) != gloss:
                    misses.append((first["id"], gloss))
    return misses, examined


@pytest.mark.parametrize("language", ["pl", "en"])
def test_captions_follow_the_target_sentence_in_this_mass(language):
    total = 0
    for text in CASE_TEXTS:
        misses, examined = caption_case(core(text), layer(language, text))
        assert misses == [], text
        total += examined
    assert total == 52


@pytest.mark.parametrize("text", PREFACES[1:])
@pytest.mark.parametrize("language", ["pl", "en"])
def test_captions_follow_the_target_sentence_in_the_easter_twins(text, language):
    assert caption_case(core(text), layer(language, text)) == ([], 5)


def test_reviewed_exceptions_are_live_and_bound_to_their_context():
    for table, opening in ((CONTINUATIONS, True), (OPENED, False)):
        for (language, text, wid), caption in table.items():
            doc, lay = core(text), layer(language, text)
            assert caption_at(lay, wid) == caption
            assert latin_opening(doc, wid) is opening


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


CAP_SITES = [
    ("pl", GOSPEL, "w008", "Chwila", "uczniów: ", "Mała chwila"),
    ("pl", GOSPEL, "w037", "Chwila", "co nam mówi: ", "Mała chwila"),
    ("pl", GOSPEL, "w060", "Chwila", "co mówi: ", "Mała chwila?"),
    ("pl", GOSPEL, "w081", "Chwila", "powiedziałem: ", "Mała chwila"),
    ("pl", III + "communio", "w001", "Chwila", "", "Mała chwila, a nie"),
    ("pl", PREFACE, "w035", "Który", "grzechy świata. ", "On, umierając"),
    ("pl", PREFACE, "w044", "I", "przywrócił życie. ", "I dlatego"),
    ("en", III + "alleluia", "w003", "The Lord sent redemption", "alleluia. ", "The Lord sent"),
    (
        "en",
        III + "epistola",
        "w043",
        "Therefore be subject",
        "visitation. ",
        "Be subject, therefore,",
    ),
    ("en", GOSPEL, "w008", "A little while", "His disciples: ", "A little while"),
    ("en", GOSPEL, "w037", "A little while", "says to us: “", "A little while"),
    ("en", GOSPEL, "w064", "But Jesus knew", "He is saying. ", "Jesus knew"),
    ("en", GOSPEL, "w081", "A little while", "that I said: ", "A little while"),
    ("en", III + "communio", "w001", "A little while", "", "A little while, and you"),
    ("en", PREFACE, "w035", "Who", "sins of the world. ", "He has destroyed"),
    ("en", PREFACE, "w044", "And", "rising again. ", "And therefore"),
    ("en", III + "epistola", "w067", "for", "those who do good; ", "for such is"),
] + [
    site
    for twin in PREFACES[1:]
    for site in (
        ("pl", twin, "w036", "Który", "grzechy świata. ", "On, umierając"),
        ("pl", twin, "w045", "I", "przywrócił życie. ", "I dlatego"),
        ("en", twin, "w036", "Who", "sins of the world. ", "He has destroyed"),
        ("en", twin, "w045", "And", "rising again. ", "And therefore"),
    )
]


def site_id(site):
    return f"{site[0]}-{site[1].split('.', 1)[1]}-{site[2]}"


def assert_caption_site(doc, lay, site):
    language, _, wid, caption, before, opening = site
    assert lay["language"] == language
    target = lay["segments"]["s01"]["translation"]
    if before:
        assert target.count(before + opening) == 1, "target sentence context"
    else:
        assert target.startswith(opening), "target sentence context"
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
    wrong = recased(site[3])
    bad = with_caption(lay, site[2], wrong)
    assert caption_case(doc, bad)[0] == [(site[2], wrong)]
    with pytest.raises(AssertionError):
        assert_caption_site(doc, bad, (*site[:3], wrong, *site[4:]))
    assert_caption_site(doc, lay, site)


@pytest.mark.parametrize("damage", ["latin-comma", "target-continues", "wrong-language", "moved"])
def test_caption_rule_is_bound_to_latin_and_target_context(damage):
    site = CAP_SITES[0]
    doc, lay = core(GOSPEL), layer("pl", GOSPEL)
    assert_caption_site(doc, lay, site)
    if damage == "latin-comma":
        bad_doc = deepcopy(doc)
        segment = bad_doc["segments"][0]
        order = [w["id"] for w in segment["words"]]
        segment["words"][order.index("w008") - 1]["post"] = ","
        with pytest.raises(AssertionError, match="Latin and target boundary"):
            assert_caption_site(bad_doc, lay, site)
    elif damage == "target-continues":
        bad = deepcopy(lay)
        text = bad["segments"]["s01"]["translation"]
        bad["segments"]["s01"]["translation"] = text.replace("uczniów: Mała", "uczniów: mała")
        with pytest.raises(AssertionError, match="target sentence context"):
            assert_caption_site(doc, bad, site)
    elif damage == "wrong-language":
        # The English continuation 'a little while' at w060 never covers a Polish caption.
        polish = with_caption(lay, "w060", "a little while")
        assert ("w060", "a little while") in caption_case(doc, polish)[0]
        english = deepcopy(layer("pl", III + "collecta"))
        english["language"] = "en"
        assert ("w041", "który") in caption_case(core(III + "collecta"), english)[0]
    else:
        # The reviewed continuation is bound to its address: lower case one quotation earlier fails.
        english = layer("en", GOSPEL)
        bad = with_caption(english, "w037", "a little while")
        assert caption_case(doc, bad)[0] == [("w037", "a little while")]
    assert_caption_site(doc, lay, site)


# Paschal Preface witness: the transcription reproduces the page's slip and declares it.
WITNESS = ROOT / "witnesses" / PREFACE
PREDECESSOR_DIGEST = "f33b0ab7fbf7732d559e5a6940f726e765141012d2711553bb72040be01f28e8"


def assert_witness(doc, folder, graph):
    transcript = (folder / "mr.txt").read_text(encoding="utf-8")
    meta, body = collate.load_witness(folder / "mr.txt")
    assert body.startswith("Vere dignum et iustem est, æquum et salutáre: Te quidem")
    assert body.count("iust") == 1
    assert len(meta["corrigenda"]) == 1, "one declared corrigendum"
    ((printed, emended, reason),) = meta["corrigenda"]
    assert (printed, emended) == ("iustem", "iustum")
    assert "Dignum et iustum est" in reason and "vatican" in reason
    assert meta["location"].startswith("printed p. 291; leaf n370")
    assert meta["orthography"].startswith("exact printed accents")
    assert collate.load_witness(folder / "vatican.txt")[1].startswith("Vere dignum et iustum est,")
    errors, warnings, counts = collate.collate(doc, folder)
    assert errors == warnings == []
    assert (counts["witnesses"], counts["corrigenda"], counts["substantive_variants"]) == (2, 1, 0)
    (witness,) = [w for w in graph["witnesses"] if w["id"] == f"witness.{PREFACE}.mr1962"]
    assert witness["transcription"] == "mr" and witness["orthography_profile"] == "exact-page-image"
    assert witness["transcription_sha256"] == transcript_digest(transcript)
    assert witness["review"] == {"status": "pending"}


def graph():
    return json.loads((ROOT / "bibliography/graph.json").read_text(encoding="utf-8"))


def test_preface_witness_prints_the_slip_and_declares_it():
    assert_witness(core(PREFACE), WITNESS, graph())


@pytest.mark.parametrize("damage", ["emended", "undeclared", "no-reason", "stale-digest"])
def test_preface_witness_damage_is_rejected(damage, tmp_path):
    doc, data = core(PREFACE), graph()
    assert_witness(doc, WITNESS, data)
    folder = tmp_path / PREFACE
    shutil.copytree(WITNESS, folder)
    path = folder / "mr.txt"
    transcript = path.read_text(encoding="utf-8")
    line = next(x for x in transcript.splitlines() if x.startswith("# corrigendum: iustem"))
    if damage == "emended":
        path.write_text(transcript.replace("et iustem est", "et iustum est"), encoding="utf-8")
    elif damage == "undeclared":
        path.write_text(transcript.replace(line + "\n", ""), encoding="utf-8")
    elif damage == "no-reason":
        path.write_text(
            transcript.replace(line, "# corrigendum: iustem -> iustum"), encoding="utf-8"
        )
    else:
        (witness,) = [w for w in data["witnesses"] if w["id"] == f"witness.{PREFACE}.mr1962"]
        witness["transcription_sha256"] = PREDECESSOR_DIGEST
    if damage != "stale-digest":
        (witness,) = [w for w in data["witnesses"] if w["id"] == f"witness.{PREFACE}.mr1962"]
        witness["transcription_sha256"] = transcript_digest(path.read_text(encoding="utf-8"))
        assert collate.collate(doc, folder)[0]
    with pytest.raises(AssertionError):
        assert_witness(doc, folder, data)
    assert_witness(doc, WITNESS, graph())


# None of the changed sites is a protected familiar formula.
CHANGED = {
    "pl": [III + "introitus", III + "postcommunio", GOSPEL, III + "communio", *PREFACES],
    "en": [text for text, *_ in VOCATIVE_GROUPS if text != III + "secreta"]
    + [III + "secreta", III + "alleluia", III + "epistola", GOSPEL, III + "communio", *SPLIT],
}


def test_changed_sites_are_outside_the_protected_formulas():
    assert protected("orationes.gloria-patri", "pl") and protected("orationes.pater-noster", "pl")
    assert protected("ordinarium.iube-domne-benedicere", "en", "s03")
    assert sum(len(texts) for texts in CHANGED.values()) == 29
    for language, texts in CHANGED.items():
        assert len(set(texts)) == len(texts)
        for text in texts:
            for segment in layer(language, text)["segments"]:
                assert not protected(text, language, segment), (text, segment)
