"""Fifth Sunday after Easter: word captions, groups, the English Gospel of Jn 16:25 and 16:29, the
Introit psalm verse shared with two other Introits, oration conclusions, a lexicon card head, and
the Liber Usualis comparison of the Introit and Communion.

Finite reviewed addresses and contexts, not general rules. Every outcome is pinned by a positive
check, and each check is shown to reject a named defect (usually the predecessor value).
"""

import json
import re
import shutil
from copy import deepcopy
from functools import cache
from pathlib import Path
from typing import Any

import pytest
from provenance_successor_fixture import assert_protection_scope

from build_reader import store
from build_reader.bibliography_bindings import (
    collation_subject,
    digest,
    selected_text,
    transcript_digest,
    witness_subject,
)
from checks import english, interlinear, interlinear_quality, prose
from checks.apparatus import derived_summary
from checks.collate import collate
from checks.language_packs import check_layer
from checks.lexicon import lint_lemmata
from checks.translation_provenance import canonical_hash, check, protected, source_payload

ROOT = Path(__file__).resolve().parents[1]
P = "proprium.dominica-v-post-pascha-"
ROLES = "introitus collecta epistola alleluia evangelium offertorium secreta communio postcommunio"
PROPERS = [P + role for role in ROLES.split()]
INTROIT, COLLECT, EPISTLE, ALLELUIA, GOSPEL, OFFERTORY, SECRET, COMMUNION, POSTCOMMUNION = PROPERS
PREFACE = "ordinarium.praefatio-paschalis"
III_INTROIT = "proprium.dominica-iii-post-pascha-introitus"
EPIPHANY_INTROIT = "proprium.dominica-ii-post-epiphaniam-introitus"
TEXTS = {role: P + role for role in ROLES.split()} | {
    "iii-introitus": III_INTROIT,
    "ii-epiphania-introitus": EPIPHANY_INTROIT,
}


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


def alignments(lay):
    return [g for s in lay["segments"].values() for g in s.get("alignments", [])]


def layer_path(language, text):
    return ROOT / "languages" / language / "texts" / (text.replace(".", "/", 1) + ".json")


def provenance(language):
    rows = load(f"languages/{language}/translation-provenance.json")["sites"]
    return {s["site"]: s for s in rows}


def rejects(check_fn, *args, message):
    """The control: the check raises AssertionError whose first line names the defect."""
    with pytest.raises(AssertionError) as caught:
        check_fn(*args)
    assert str(caught.value).splitlines()[0] == message


def ids(*numbers):
    return [f"w{n:03d}" for n in numbers]


def span(first, last):
    return ids(*range(first, last + 1))


def group(members, anchor, gloss):
    return {"words": members, "anchor": anchor, "gloss": gloss}


def clean(doc, lay):
    assert interlinear.check(doc, lay) == []
    if lay["language"] == "en":
        assert english.check(doc, lay) == [] and interlinear_quality.check(doc, lay) == []


def text_id(row):
    return f"{row[1]}-{row[2].split('.')[-1]}-{row[3]}"


# --- word captions ------------------------------------------------------------------------------
# (tag, language, text, word, Latin form, selected caption, predecessor caption)
CAPTIONS: list[tuple[Any, ...]] = [
    ("caption case", "pl", GOSPEL, "w004", "Dixit", "powiedział", "Powiedział"),
    ("caption case", "pl", EPISTLE, "w029", "considerávit", "obejrzał", "Obejrzał"),
    ("caption case", "pl", OFFERTORY, "w023", "benedíctus", "błogosławiony", "Błogosławiony"),
    ("government", "pl", POSTCOMMUNION, "w001", "Tríbue", "Daj", "Udziel"),
    ("Gloria Patri", "en", INTROIT, "w042", "nunc", "now", "is now"),
    ("Ecce", "en", GOSPEL, "w109", "Ecce", "Behold", "See"),
    ("palam", "en", GOSPEL, "w111", "palam", "openly", "plainly"),
    ("Iubilate", "en", EPIPHANY_INTROIT, "w014", "Iubiláte", "Shout for joy", "Sing joyfully"),
    (
        "Iubilate",
        "pl",
        EPIPHANY_INTROIT,
        "w014",
        "Iubiláte",
        "Wykrzykujcie",
        "Wykrzykujcie radośnie",
    ),
]


def assert_caption(doc, lay, row):
    tag, _language, _text, wid, form, gloss, _old = row
    assert words(doc)[wid]["form"] == form, f"{tag} Latin context"
    assert not [g for g in alignments(lay) if wid in g["words"]], f"{tag} caption"
    assert lay["words"][wid].get("gloss") == gloss, f"{tag} caption"
    assert interlinear.check(doc, lay) == [], f"{tag} interlinear line"


@pytest.mark.parametrize("row", CAPTIONS, ids=[text_id(r) for r in CAPTIONS])
def test_selected_caption(row):
    assert_caption(core(row[2]), layer(row[1], row[2]), row)


@pytest.mark.parametrize("row", CAPTIONS, ids=[text_id(r) for r in CAPTIONS])
def test_predecessor_caption_is_rejected(row):
    doc, lay = core(row[2]), layer(row[1], row[2])
    assert_caption(doc, lay, row)
    lay["words"][row[3]]["gloss"] = row[6]
    rejects(assert_caption, doc, lay, row, message=f"{row[0]} caption")


# --- realizations: word captions and minimal groups replacing a predecessor group ---------------
# One entry per predecessor group: "tag | language | text | [members @anchor] predecessor caption",
# then the selected realization of the same words, items separated by "; ". A member list is a
# range (w013-w015) or single ids; "[w040 w041 @w040] I have spoken" is a group.
REALIZATIONS = """
Gospel|en|evangelium|[w013-w015 @w014] you ask the Father for anything
    w013 anything; w014 you ask; w015 the Father
Gospel|en|evangelium|[w037-w041 @w040] I have spoken these things in figures of speech
    w037 These things; w038 in; w039 veiled sayings; [w040 w041 @w040] I have spoken
Gospel|en|evangelium|[w046-w050 @w050] I will no longer speak in figures of speech
    [w046 w047 @w046] no longer; w048 in; w049 veiled sayings; w050 I will speak
Gospel|en|evangelium|[w053-w057 @w056] I will tell you plainly about the Father
    w053 openly; w054 about; w055 the Father; w056 I will tell; w057 you
Gospel|en|evangelium|[w088-w090 @w090] came forth from God
    w088 from; w089 God; w090 came forth
Gospel|en|evangelium|[w105-w108 @w105] His disciples say to Him
    w105 Say; w106 to Him; [w107 w108 @w107] His disciples
Gospel|en|evangelium|[w114-w116 @w116] You use no figure of speech
    [w114-w116 @w116] You use no veiled saying
Gospel|en|evangelium|[w135-w137 @w137] You came forth from God
    w135 from; w136 God; w137 You came forth
Introit|en|introitus|[w001-w003 @w003] Proclaim the joyful news
    w001 The voice; w002 of joy; w003 proclaim
Introit|en|introitus|[w050-w052 @w052] Proclaim the joyful news
    w050 The voice; w051 of joy; w052 proclaim
psalm verse|en|introitus|[w026-w029 @w026] make His praise glorious
    w026 give; w027 glory; [w028 w029 @w028] to His praise
psalm verse|en|iii-introitus|[w011-w014 @w011] make His praise glorious
    w011 give; w012 glory; [w013 w014 @w013] to His praise
psalm verse|en|iii-introitus|[w064-w067 @w064] make His praise glorious
    w064 give; w065 glory; [w066 w067 @w066] to His praise
Epistle|en|epistola|[w051-w054 @w054] having become not a forgetful hearer
    w051 not; w052 a hearer; w053 forgetful; w054 having become
Epistle|en|epistola|[w059-w063 @w063] will be blessed in his deed
    w059 blessed; w060 in; [w061 w062 @w061] his deed; w063 will be
Epistle|en|epistola|[w083-w086 @w083] Pure and undefiled religion
    w083 Religion; w084 pure; w085 and; w086 undefiled
Offertory|en|offertorium|[w012-w016 @w012] has kept me alive
    w012 has kept; [w013 w014 @w013] my soul; w015 in; w016 life
Secret|en|secreta|[w014-w017 @w017] we may pass to heavenly glory
    w014 to; w015 heavenly; w016 glory; w017 we may pass over
PC|en|postcommunio|[w001-w003 @w001] Lord, grant us
    w001 Grant; w002 us; w003 Lord
PC|en|postcommunio|[w004-w007 @w007] having been filled with the strength of the heavenly table
    [w004-w007 @w007] filled with the strength of the heavenly table
psalm verse|pl|ii-epiphania-introitus|[w018-w019 @w019] śpiewajcie psalm
    w018 psalm; w019 śpiewajcie
psalm verse|pl|ii-epiphania-introitus|[w020-w021 @w020] Jego imieniu
    w020 imieniu; w021 Jego
psalm verse|pl|ii-epiphania-introitus|[w024-w025 @w024] Jego chwale
    w024 uwielbieniu; w025 Jego
"""
# The oration conclusions take the corpus's majority realization of each part (Qui … vivit split).
CONCLUSION_QUI = {COLLECT: 29, SECRET: 25, POSTCOMMUNION: 23}


def members_of(spec):
    if "-" in spec:
        first, last = spec.split("-")
        return span(int(first[1:]), int(last[1:]))
    return spec.split()


def item(spec):
    spec = spec.strip()
    if spec.startswith("["):
        inside, caption = spec[1:].split("] ", 1)
        listed, anchor = inside.split(" @")
        return ("g", members_of(listed), anchor, caption)
    wid, caption = spec.split(" ", 1)
    return ("w", wid, caption)


def parse_realizations(table):
    rows: list[tuple[Any, ...]] = []
    lines = [line for line in table.strip("\n").split("\n")]
    while lines:
        tag, language, role, old = lines.pop(0).split("|")
        selected = []
        while lines and lines[0].startswith("    "):
            selected.append(lines.pop(0).strip())
        old_item = item(old)
        rows.append(
            (
                tag,
                language,
                TEXTS[role],
                group(*old_item[1:]),
                [item(s) for s in " ".join(selected).split("; ")],
            )
        )
    for text, qui in CONCLUSION_QUI.items():
        members = span(qui, qui + 2)
        rows.append(
            (
                "conclusion",
                "en",
                text,
                group(members, members[0], "who lives with You"),
                [
                    ("w", members[0], "who"),
                    ("w", members[1], "with You"),
                    ("w", members[2], "lives"),
                ],
            )
        )
    return rows


REGROUPS = parse_realizations(REALIZATIONS)


def regroup_id(row):
    return f"{row[1]}-{row[2].split('.')[-1]}-{row[3]['words'][0]}"


def assert_regroup(doc, lay, row):
    tag, _language, _text, old, items = row
    members = old["words"]
    touching = [g for g in alignments(lay) if set(g["words"]) & set(members)]
    assert touching == [group(i[1], i[2], i[3]) for i in items if i[0] == "g"], f"{tag} realization"
    captions = {i[1]: i[2] for i in items if i[0] == "w"}
    for wid in members:
        assert lay["words"][wid].get("gloss") == captions.get(wid), f"{tag} realization"
    clean(doc, lay)


def test_realization_inventory():
    assert len(REGROUPS) == 26
    assert len({(r[1], r[2], r[3]["words"][0]) for r in REGROUPS}) == len(REGROUPS)
    for row in REGROUPS:
        covered = [w for i in row[4] for w in ([i[1]] if i[0] == "w" else i[1])]
        assert covered == row[3]["words"] and row[3]["anchor"] in covered


@pytest.mark.parametrize("row", REGROUPS, ids=[regroup_id(r) for r in REGROUPS])
def test_selected_realization(row):
    assert_regroup(core(row[2]), layer(row[1], row[2]), row)


@pytest.mark.parametrize("row", REGROUPS, ids=[regroup_id(r) for r in REGROUPS])
def test_predecessor_group_is_rejected(row):
    doc, lay = core(row[2]), layer(row[1], row[2])
    old = row[3]
    for seg in lay["segments"].values():
        if "alignments" in seg:
            seg["alignments"] = [
                g for g in seg["alignments"] if not set(g["words"]) & set(old["words"])
            ]
    lay["segments"]["s01"].setdefault("alignments", []).append(deepcopy(old))
    for wid in old["words"]:
        lay["words"][wid].pop("gloss", None)
    rejects(assert_regroup, doc, lay, row, message=f"{row[0]} realization")
    if row[1] == "en" and row[2] == POSTCOMMUNION and old["words"] == span(4, 7):
        # Also reject the actual split-caption predecessor, not only the
        # historical group with a different, semantically faithful caption.
        original = layer("en", POSTCOMMUNION)
        split = deepcopy(original)
        split["segments"]["s01"]["alignments"] = [
            g for g in alignments(split) if not set(g["words"]) & set(span(4, 7))
        ]
        captions = ("of the heavenly", "table", "with the strength", "having been filled")
        for wid, caption in zip(span(4, 7), captions, strict=True):
            split["words"][wid]["gloss"] = caption
        rejects(assert_regroup, doc, split, row, message=f"{row[0]} realization")
        assert_regroup(doc, original, row)


# --- the three oration conclusions ----------------------------------------------------------------
SEQUENCE = [
    *("Per", "Dóminum", "nostrum", "Iesum", "Christum", "Fílium", "tuum", "Qui", "tecum"),
    *("vivit", "et", "regnat", "in", "unitáte", "Spíritus", "Sancti", "Deus"),
]
CONCLUSION = [
    *("Through", "our Lord", "Jesus", "Christ", "Your Son", "who", "with You", "lives", "and"),
    *("reigns", "in", "the unity", "of the Holy Spirit", "God"),
]


def conclusion_line(text, lay=None):
    """The captions of the 17 Latin words Per Dóminum … Deus, one per alignment, in order."""
    doc, lay = core(text), lay or layer("en", text)
    first = CONCLUSION_QUI[text] - 7
    members = span(first, first + 16)
    assert [words(doc)[w]["form"] for w in members] == SEQUENCE
    starts = {g["words"][0]: g for g in alignments(lay)}
    out, skip = [], set()
    for wid in members:
        if wid in skip:
            continue
        if wid in starts:
            out.append(starts[wid]["gloss"])
            skip.update(starts[wid]["words"])
        else:
            out.append(lay["words"][wid]["gloss"])
    return out


@pytest.mark.parametrize("text", sorted(CONCLUSION_QUI))
def test_the_three_conclusions_share_one_realization(text):
    assert conclusion_line(text) == CONCLUSION


def test_a_regrouped_conclusion_is_rejected():
    bad = layer("en", COLLECT)
    seg = bad["segments"]["s01"]
    seg["alignments"].append(group(span(29, 31), "w029", "who lives with You"))
    for wid in span(29, 31):
        bad["words"][wid].pop("gloss", None)
    assert conclusion_line(COLLECT, bad) != CONCLUSION
    assert conclusion_line(COLLECT, bad)[5] == "who lives with You"


def test_the_conclusion_pattern_follows_the_corpus_majority_of_each_part():
    """Per, Iesum Christum, Qui … regnat and in unitáte are word captions in most of the corpus's
    conclusions; Dóminum nostrum and Fílium tuum take the owner's grouped possessive."""
    parts = {"per": (0, 1), "iesus": (3, 5), "qui": (7, 12), "unity": (12, 14)}
    tally = {f"{key}{kind}": 0 for key in parts for kind in ("", "-g")}
    occurrences = 0
    for path in sorted((ROOT / "texts").glob("*/*.json")):
        if not (ROOT / "languages/en/texts" / path.parent.name / path.name).exists():
            continue
        text = f"{path.parent.name}.{path.stem}"
        grouped = {w for g in alignments(layer("en", text)) for w in g["words"]}
        ws = [w for s in core(text)["segments"] for w in s.get("words", [])]
        for i in range(len(ws) - 16):
            if [w["form"] for w in ws[i : i + 17]] != SEQUENCE:
                continue
            occurrences += 1
            found = [w["id"] for w in ws[i : i + 17]]
            for key, (lo, hi) in parts.items():
                tally[key if not set(found[lo:hi]) & grouped else key + "-g"] += 1
    assert occurrences >= 200
    for key in parts:
        assert tally[key] > tally[key + "-g"], (key, tally)


# --- the Introit psalm verse: one reading of the identical Latin in three Introits ----------------
# Iubiláte Deo, omnis terra, psalmum dícite nómini eius: date glóriam laudi eius (Ps 65:1-2).
PSALM_VERSE = {
    INTROIT: span(18, 29),
    EPIPHANY_INTROIT: span(14, 25),
    III_INTROIT: [*span(1, 4), *span(6, 9), *span(11, 14)],
}
III_REPRISE = [*span(54, 57), *span(59, 62), *span(64, 67)]
PSALM_LINE = {
    "en": [
        *("Shout for joy", "to God", "all", "the earth", "sing a psalm", "to His name", "give"),
        *("glory", "to His praise"),
    ],
    "pl": [
        *("Wykrzykujcie", "Bogu", "cała", "ziemio", "psalm", "śpiewajcie", "imieniu", "Jego"),
        *("oddajcie", "chwałę", "uwielbieniu", "Jego"),
    ],
}


def psalm_line(text, members, lay):
    """(Latin forms, realization units) of the psalm verse; a unit is (member ids, caption)."""
    doc = core(text)
    forms = [words(doc)[w]["form"].replace("Jubiláte", "Iubiláte") for w in members]
    by_word = {w: g for g in alignments(lay) for w in g["words"]}
    units, seen = [], set()
    for wid in members:
        if wid in seen:
            continue
        found = by_word.get(wid)
        if found:
            assert set(found["words"]) <= set(members), "psalm verse unit"
            seen.update(found["words"])
            units.append((len(found["words"]), found["gloss"]))
        else:
            seen.add(wid)
            units.append((1, lay["words"][wid]["gloss"]))
    return forms, units


@pytest.mark.parametrize("language", ["en", "pl"])
def test_the_three_introits_read_the_psalm_verse_alike(language):
    lines = {
        text: psalm_line(text, members, layer(language, text))
        for text, members in PSALM_VERSE.items()
    }
    lines["reprise"] = psalm_line(III_INTROIT, III_REPRISE, layer(language, III_INTROIT))
    forms = {tuple(f) for f, _ in lines.values()}
    assert len(forms) == 1
    units = {tuple(u) for _, u in lines.values()}
    assert len(units) == 1
    assert [caption for _, caption in next(iter(units))] == PSALM_LINE[language]
    bad = layer(language, EPIPHANY_INTROIT)
    bad["words"]["w014"]["gloss"] = {"en": "Sing joyfully", "pl": "Wykrzykujcie radośnie"}[language]
    assert psalm_line(EPIPHANY_INTROIT, PSALM_VERSE[EPIPHANY_INTROIT], bad)[1] != list(
        next(iter(units))
    )


def test_the_introit_verses_keep_their_wording():
    assert "make His praise glorious" in layer("en", INTROIT)["segments"]["s01"]["translation"]
    epiphany = layer("en", EPIPHANY_INTROIT)["segments"]["s01"]["translation"]
    # Ascension audit successor (2026-10-20): V-RES-1 aligns this verse with its
    # caption (Iubiláte, Shout for joy).
    assert "Shout for joy to God, all the earth;" in epiphany
    assert "Sing joyfully" not in epiphany
    assert "give glory to His praise" in epiphany
    assert (
        "oddajcie Mu chwałę, wysławiając Go"
        in layer("pl", INTROIT)["segments"]["s01"]["translation"]
    )


# --- verses ---------------------------------------------------------------------------------------
# (tag, language, text, selected phrase, predecessor phrase); segment s01.
VERSES = [
    (
        "Gospel",
        "en",
        GOSPEL,
        "These things I have spoken to you in veiled sayings. The hour is coming when I will no "
        "longer speak to you in veiled sayings, but will tell you openly about the Father.",
        "These things I have spoken to you in proverbs. The hour is coming when I will no longer "
        "speak to you in proverbs, but will tell you openly of the Father.",
    ),
    (
        "Gospel",
        "en",
        GOSPEL,
        "His disciples say to Him: Behold, now You speak openly and use no veiled saying.",
        "His disciples say to Him: Behold, now You speak openly, and say no proverb.",
    ),
]
VERSE_IDS = [f"{r[1]}-{r[2].split('-')[-1]}-{i}" for i, r in enumerate(VERSES)]


def assert_verse(lay, row):
    tag, language, text, present, absent = row
    target = lay["segments"]["s01"]["translation"]
    assert target.count(present) == 1 and absent not in target, f"{tag} verse"
    site = provenance(language)[f"{text}.s01.{language}"]
    assert site["target_sha256"] == canonical_hash(target), f"{tag} provenance"
    assert site["review"] == "working"
    assert_protection_scope(text, language, "s01", target)


@pytest.mark.parametrize("row", VERSES, ids=VERSE_IDS)
def test_selected_verse(row):
    assert_verse(layer(row[1], row[2]), row)


@pytest.mark.parametrize("row", VERSES, ids=VERSE_IDS)
def test_predecessor_verse_is_rejected(row):
    lay = layer(row[1], row[2])
    target = lay["segments"]["s01"]["translation"]
    lay["segments"]["s01"]["translation"] = target.replace(row[3], row[4])
    rejects(assert_verse, lay, row, message=f"{row[0]} verse")


@pytest.mark.parametrize("row", VERSES[:1], ids=VERSE_IDS[:1])
def test_a_silently_edited_verse_is_rejected(row):
    """A verse change with its provenance hash left behind is caught by the hash pin."""
    lay = layer(row[1], row[2])
    target = lay["segments"]["s01"]["translation"]
    lay["segments"]["s01"]["translation"] = target.replace("openly about", "openly of")
    rejects(assert_verse, lay, row, message=f"{row[0]} verse")


KEPT = (
    "At that time, Jesus said to His disciples: Amen, amen, I say to you: if you ask the Father "
    "for anything in My name, He will give it to you.",
    "Until now you have asked nothing in My name.",
    "Ask, and you will receive, so that your joy may be full.",
    "On that day you will ask in My name; and I do not say to you that I will entreat the Father "
    "for you, for the Father Himself loves you, since you have loved Me and have believed that I "
    "came forth from God.",
    "I came forth from the Father and came into the world; again I leave the world and go to the "
    "Father.",
    "Now we know that You know all things, and that You have no need for anyone to question You.",
    "By this we believe that You came forth from God.",
)


def test_the_gospel_keeps_its_other_sentences():
    gospel = layer("en", GOSPEL)["segments"]["s01"]["translation"]
    for sentence in KEPT:
        assert gospel.count(sentence) == 1, sentence
    assert gospel.startswith(KEPT[0]) and gospel.endswith(KEPT[-1])


def test_the_alleluia_sings_the_gospel_sentence_alike():
    sentence = KEPT[4]
    assert sentence in layer("en", ALLELUIA)["segments"]["s01"]["translation"]
    latin_a, latin_g = words(core(ALLELUIA)), words(core(GOSPEL))
    pairs = list(zip(span(13, 26), span(91, 104), strict=True))
    assert all(latin_a[a]["form"] == latin_g[g]["form"] for a, g in pairs)
    a, g = layer("en", ALLELUIA), layer("en", GOSPEL)
    assert [a["words"][x]["gloss"] for x, _ in pairs] == [g["words"][y]["gloss"] for _, y in pairs]


# --- the word note on provérbiis ------------------------------------------------------------------
NOTE = (
    "The sayings convey their meaning indirectly. Jesus contrasts this veiled speech with "
    "speaking openly about the Father."
)


def assert_note(lay):
    entry = lay["words"]["w039"]
    assert entry.get("gloss") == "veiled sayings" and entry.get("explanation") == NOTE, (
        "proverbs note"
    )


def test_the_proverbs_note_explains_the_selected_word():
    assert words(core(GOSPEL))["w039"]["lemma"] == "proverbium"
    assert core(GOSPEL)["localization"]["explanations"]["w039"] == {}
    assert_note(layer("en", GOSPEL))
    assert prose.check(layer("en", GOSPEL)) == []


def test_the_predecessor_note_is_rejected():
    bad = layer("en", GOSPEL)
    bad["words"]["w039"]["explanation"] = (
        "Jesus contrasts these sayings with speaking plainly about the Father. Here “figures of "
        "speech” conveys language whose meaning is not stated directly, rather than simply "
        "familiar maxims."
    )
    rejects(assert_note, bad, message="proverbs note")


# --- a bounded idiom regression check, not an authorship or rights detector ----------------------
REPLACED = ("speak openly, and say no proverb",)


def english_strings(lay):
    out = [lay.get("about", "")]
    for seg in lay["segments"].values():
        out.append(seg.get("translation") or "")
        out += [g.get("gloss", "") for g in seg.get("alignments", [])]
    for entry in lay["words"].values():
        out += [entry.get("gloss", ""), entry.get("explanation", "")]
    return [s for s in out if s]


def replaced_wording(lay):
    """Each replaced phrase found in a field or across the joined caption line."""
    joined = " ".join(english_strings(lay)).casefold()
    return sorted(phrase for phrase in REPLACED if phrase in joined)


@pytest.mark.parametrize("text", [GOSPEL])
def test_no_english_layer_of_this_mass_carries_the_replaced_wording(text):
    assert replaced_wording(layer("en", text)) == []


@pytest.mark.parametrize("phrase", REPLACED)
def test_a_reintroduced_phrase_is_detected(phrase):
    bad = layer("en", GOSPEL)
    first, _, rest = phrase.partition(" ")
    bad["words"]["w037"]["gloss"], bad["words"]["w038"]["gloss"] = first, rest
    assert phrase in replaced_wording(bad)


def test_a_dictionary_sense_is_not_treated_as_copying():
    candidate = layer("en", GOSPEL)
    candidate["words"]["w039"]["explanation"] = "A figure of speech can convey meaning indirectly."
    assert replaced_wording(candidate) == []


# --- provenance of the English Gospel ------------------------------------------------------------
REVISED = f"{GOSPEL}.s01.en"


def assert_revised(sites):
    row = sites[REVISED]
    actual = (row["origin"], row["review"], row["familiar_core"])
    assert actual == ("public-domain", "working", False), "English origin"


def test_the_gospel_has_a_revised_historical_basis():
    assert_revised(provenance("en"))
    errors, _tally = check(ROOT)
    assert not [e for e in errors if REVISED in e]


def test_an_own_claim_is_rejected():
    sites = provenance("en")
    sites[REVISED]["origin"] = "own"
    rejects(assert_revised, sites, message="English origin")


# --- no clause-sized group remains in the nine proper texts ---------------------------------------
# Every group of three or more words left in this Mass, with its caption.
LONG_GROUPS = {
    ("pl", GOSPEL): [("w114", "nic nie mówisz w przenośni")],
    ("en", INTROIT): [("w046", "forever and ever")],
    ("en", COLLECT): [("w014", "what is right"), ("w039", "forever and ever")],
    ("en", EPISTLE): [
        ("w024", "his natural face"),
        ("w044", "the perfect law of liberty"),
        ("w068", "himself to be religious"),
        ("w079", "this man’s religion is vain"),
        ("w101", "to keep oneself unspotted"),
    ],
    ("en", GOSPEL): [
        ("w075", "for the Father Himself"),
        ("w114", "You use no veiled saying"),
        ("w123", "You have no need"),
    ],
    ("en", OFFERTORY): [("w020", "my feet to falter")],
    ("en", SECRET): [("w010", "these duties of pious devotion"), ("w035", "forever and ever")],
    ("en", POSTCOMMUNION): [
        ("w004", "filled with the strength of the heavenly table"),
        ("w010", "what is right"),
        ("w033", "forever and ever"),
    ],
}


def long_groups(lay):
    return [(g["words"][0], g["gloss"]) for g in alignments(lay) if len(g["words"]) >= 3]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_only_the_reviewed_longer_groups_remain(language):
    for text in PROPERS:
        assert long_groups(layer(language, text)) == LONG_GROUPS.get((language, text), []), text
    bad = layer("en", EPISTLE)
    seg = bad["segments"]["s01"]
    seg["alignments"] = [g for g in seg["alignments"] if not set(g["words"]) & set(span(83, 86))]
    seg["alignments"].append(group(span(83, 86), "w083", "Pure and undefiled religion"))
    assert ("w083", "Pure and undefiled religion") in long_groups(bad)


# --- caption case: a caption at a genuine sentence opening follows the target sentence's capital;
# inside a sentence it is lower case. Bounded to this Mass and its Preface (RF6 pattern).
CASE_TEXTS = [*PROPERS, PREFACE]
# Reviewed lower-case captions at a Latin opening whose target sentence continues.
CONTINUATIONS = {
    **{
        (language, text, wid): caption
        for text, wid in ((COLLECT, "w029"), (SECRET, "w025"), (POSTCOMMUNION, "w023"))
        for language, caption in (("pl", "który"), ("en", "who"))
    },
    ("pl", EPISTLE, "w093"): "nawiedzać",
    ("pl", GOSPEL, "w004"): "powiedział",
    ("en", EPISTLE, "w093"): "to visit",
}
# A reviewed English sentence opening ("… falter. Blessed be the Lord").
# The Polish sentence continues there, so its caption is lower case.
RESIDUAL = {("en", OFFERTORY, "w023"): "Blessed be"}
# Capitals a lower-case Latin word may carry here: words for God, Christ and the Spirit, English I.
NAMED = {
    "pl": {"Mu", "Jego", "Twoim", "Twojego", "Twojej", "Moim", "Mnie", "Ja", "Ci", "Cię"},
    "en": {"He", "Him", "His", "Himself", "I", "Me", "My", "You", "Your"},
}


def caption_case(doc, lay):
    language, misses, examined = lay["language"], [], 0
    for segment in doc["segments"]:
        ws = segment.get("words", [])
        spans = {
            a["words"][0]: a for a in lay["segments"].get(segment["id"], {}).get("alignments", [])
        }
        prev, pending, i = ".", False, 0
        while i < len(ws):
            grp = spans.get(ws[i]["id"])
            n = len(grp["words"]) if grp else 1
            first, last = ws[i], ws[i + n - 1]
            ends = prev.rstrip().endswith((".", ":", "?", "!"))
            opens = pending or (ends and first["form"][:1].isupper())
            gloss = grp.get("gloss") if grp else lay["words"][first["id"]].get("gloss")
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
                if capital and word[0] not in NAMED[language] and RESIDUAL.get(key) != gloss:
                    misses.append((first["id"], gloss))
    return misses, examined


@pytest.mark.parametrize("language", ["pl", "en"])
def test_captions_follow_the_target_sentence_in_this_mass(language):
    total = 0
    for text in CASE_TEXTS:
        misses, examined = caption_case(core(text), layer(language, text))
        assert misses == [], text
        total += examined
    assert total == 49


def caption_at(lay, wid):
    starting = [g for g in alignments(lay) if g["words"][0] == wid]
    return starting[0].get("gloss") if starting else lay["words"][wid].get("gloss")


def with_caption(lay, wid, caption):
    bad = deepcopy(lay)
    starting = [g for g in alignments(bad) if g["words"][0] == wid]
    if starting:
        starting[0]["gloss"] = caption
    else:
        bad["words"][wid]["gloss"] = caption
    return bad


# (language, text, word, caption, target text before the opening, target opening)
CAP_SITES = [
    ("en", INTROIT, "w050", "The voice", "Amen. ", "Proclaim the joyful news"),
    ("en", EPISTLE, "w083", "Religion", "religion is vain. ", "Religion pure and undefiled"),
    ("en", GOSPEL, "w037", "These things", "may be full. ", "These things I have spoken"),
    ("en", GOSPEL, "w105", "Say", "go to the Father. ", "His disciples say to Him"),
    ("en", POSTCOMMUNION, "w001", "Grant", "", "Grant, O Lord,"),
]
CAP_IDS = [f"{s[0]}-{s[1].split('-')[-1]}-{s[2]}" for s in CAP_SITES]


def assert_caption_site(doc, lay, site):
    _language, _text, wid, caption, before, opening = site
    assert lay["segments"]["s01"]["translation"].count(before + opening) == 1, "target context"
    assert caption_at(lay, wid) == caption
    assert caption[:1].isupper() is opening[:1].isupper(), "caption case follows the target"
    assert (wid, caption) not in caption_case(doc, lay)[0]


@pytest.mark.parametrize("site", CAP_SITES, ids=CAP_IDS)
def test_caption_at_an_opening_follows_the_target_sentence(site):
    assert_caption_site(core(site[1]), layer(site[0], site[1]), site)


@pytest.mark.parametrize("site", CAP_SITES, ids=CAP_IDS)
def test_a_lower_case_opening_caption_is_rejected(site):
    doc, lay = core(site[1]), layer(site[0], site[1])
    wrong = site[3][:1].lower() + site[3][1:]
    assert caption_case(doc, with_caption(lay, site[2], wrong))[0] == [(site[2], wrong)]
    with pytest.raises(AssertionError):
        assert_caption_site(doc, with_caption(lay, site[2], wrong), (*site[:3], wrong, *site[4:]))


@pytest.mark.parametrize(
    "text,wid,capital", [(EPISTLE, "w029", "Obejrzał"), (OFFERTORY, "w023", "Błogosławiony")]
)
def test_a_polish_capital_inside_the_sentence_is_rejected(text, wid, capital):
    doc = core(text)
    assert words(doc)[wid]["form"][:1].islower()
    assert caption_case(doc, with_caption(layer("pl", text), wid, capital))[0] == [(wid, capital)]


def test_reviewed_exceptions_are_live_and_bound_to_their_address():
    for table in (CONTINUATIONS, RESIDUAL):
        for (language, text, wid), caption in table.items():
            assert caption_at(layer(language, text), wid) == caption
    assert "falter. Blessed be the Lord" in layer("en", OFFERTORY)["segments"]["s01"]["translation"]
    assert "stopy; błogosławiony Pan" in layer("pl", OFFERTORY)["segments"]["s01"]["translation"]
    polish = with_caption(layer("pl", COLLECT), "w029", "who")
    assert ("w029", "who") in caption_case(core(COLLECT), polish)[0]
    moved = with_caption(layer("en", SECRET), "w014", "To")
    assert caption_case(core(SECRET), moved)[0] == [("w014", "To")]


# --- the lexicon card of vosmetipse ---------------------------------------------------------------
CONSUMERS_OF_VOSMETIPSE = [
    "proprium.dominica-iii-post-epiphaniam-epistola",
    "proprium.dominica-post-ascensionem-epistola",
    "proprium.dominica-v-post-epiphaniam-epistola",
    EPISTLE,
    "proprium.dominica-xx-post-pentecosten-epistola",
    "proprium.sancta-familia-epistola",
]


def assert_card(entries):
    card = entries["vosmetipse"]
    assert card == {"head": "vosmetípsi", "pos": "pron"}, "card head"
    assert entries["nosmetipse"]["head"] == "nosmetípsi", "card head"
    assert lint_lemmata({"vosmetipse": card}) == [], "card head"


def test_the_card_head_is_the_lemma_and_the_text_keeps_its_attested_form():
    entries = load("lexicon/lemmata.json")["entries"]
    assert_card(entries)
    attested = set()
    for text in CONSUMERS_OF_VOSMETIPSE:
        found = [w for w in words(core(text)).values() if w["lemma"] == "vosmetipse"]
        assert found, text
        attested |= {w["form"] for w in found}
    assert "vosmetípsos" in attested and "vobismetípsis" in attested
    assert words(core(EPISTLE))["w010"]["form"] == "vosmetípsos"


def test_an_oblique_card_head_is_rejected():
    entries = deepcopy(load("lexicon/lemmata.json")["entries"])
    entries["vosmetipse"]["head"] = "vobismetípsis"
    rejects(assert_card, entries, message="card head")


# --- the Liber Usualis comparison of the Introit antiphon and the Communion -----------------------
LU_SHA = "a3d5fdb3308dcabc0474eb99d2f8a5509e52c76380ae41ec373ab3aa3e7db6b9"
LU: dict[str, dict[str, Any]] = {
    INTROIT: {
        "entry": {"at": "w007", "ours": "annuntiáte", "lu": "nuntiáte", "class": "substantive"},
        "coverage": {"kind": "words", "words": span(1, 17)},
        "stats": {"witnesses": 2, "partial": 1, "substantive_variants": 1, "omissions": 0},
    },
    COMMUNION: {
        "entry": {"at": "w006", "ours": "et", "lu": "", "class": "omission"},
        "coverage": {"kind": "full"},
        "stats": {"witnesses": 3, "partial": 0, "substantive_variants": 0, "omissions": 1},
    },
}


def lu_entry(apparatus, text):
    spec = LU[text]["entry"]
    found = [
        e for e in apparatus["adjudicated"] if e["at"] == spec["at"] and "lu" in e["witnesses"]
    ]
    assert len(found) == 1, "chant-book reading"
    return found[0]


def assert_lu(doc, folder, graph):
    text = doc["id"]
    spec = LU[text]
    apparatus = json.loads((folder / "apparatus.json").read_text(encoding="utf-8"))
    entry = lu_entry(apparatus, text)
    assert entry["ours"] == spec["entry"]["ours"], "chant-book reading"
    assert entry["witnesses"] == {"lu": spec["entry"]["lu"]}, "chant-book reading"
    assert entry["class"] == spec["entry"]["class"], "chant-book reading"
    assert spec["entry"]["ours"] in entry["ruling"] and "Missal" in entry["ruling"], (
        "chant-book reading"
    )
    note = apparatus["note"]
    assert "The witnesses agree" not in note and "Liber Usualis" in note, "chant-book reading"
    method = doc["editorial"]["source"]["method"]
    assert "Liber Usualis" in method and spec["entry"]["at"] in method, "chant-book reading"
    errors, _warnings, stats = collate(doc, folder)
    assert errors == [], "collation"
    assert {key: stats[key] for key in spec["stats"]} == spec["stats"], "collation"
    witness_id = f"witness.{text}.lu1961"
    (witness,) = [w for w in graph["witnesses"] if w["id"] == witness_id]
    assert witness["coverage"] == spec["coverage"], "graph"
    assert witness["review"] == {"status": "pending"}, "graph"
    assert witness["role"] == "approved_corroboration", "graph"
    assert witness.get("source_dependencies") == {"uses": [], "raw_binding": None}, "graph"
    transcript = (folder / "lu.txt").read_text(encoding="utf-8")
    assert witness["transcription_sha256"] == transcript_digest(transcript), "graph"
    (use,) = [u for u in graph["uses"] if u["id"] == witness["use"]]
    assert (use["edition"], use["evidence_sha256"]) == ("edition.liber-usualis.1961", LU_SHA), (
        "graph"
    )
    (collation,) = [c for c in graph["collations"] if c["text"] == text]
    assert witness_id in collation["witnesses"], "graph"
    assert collation["apparatus_sha256"] == digest(apparatus), "graph"
    assert collation["apparatus"] == derived_summary(apparatus), "graph"
    assert collation["selected_text_sha256"] == digest(selected_text(doc)), "graph"
    assert collation["review"] == {"status": "pending"}, "graph"
    rows = [w for w in graph["witnesses"] if w["text"] == text]
    subjects = {w["id"]: witness_subject(ROOT, w, graph, doc) for w in rows}
    assert all(s["contract"] == "witness-review-2" for s in subjects.values()), "graph"
    assert collation_subject(ROOT, collation, doc, subjects)["contract"] == "collation-review-2", (
        "graph"
    )


@pytest.mark.parametrize("text", sorted(LU))
def test_the_chant_book_reading_is_recorded_with_its_witness(text):
    assert_lu(core(text), ROOT / "witnesses" / text, load("bibliography/graph.json"))


@pytest.mark.parametrize("text", sorted(LU))
@pytest.mark.parametrize("damage", ["drop-entry", "class", "reviewed", "inventory", "note"])
def test_the_chant_book_record_rejects_damage(text, damage, tmp_path):
    folder = tmp_path / text
    shutil.copytree(ROOT / "witnesses" / text, folder)
    path = folder / "apparatus.json"
    apparatus = json.loads(path.read_text(encoding="utf-8"))
    graph = load("bibliography/graph.json")
    if damage == "drop-entry":
        apparatus["adjudicated"].remove(lu_entry(apparatus, text))
        apparatus["summary"] = derived_summary(apparatus)
        expected = "chant-book reading"
    elif damage == "class":
        lu_entry(apparatus, text)["class"] = "orthography"
        apparatus["summary"] = derived_summary(apparatus)
        expected = "chant-book reading"
    elif damage == "reviewed":
        (witness,) = [w for w in graph["witnesses"] if w["id"] == f"witness.{text}.lu1961"]
        witness["review"] = {"status": "reviewed"}
        expected = "graph"
    elif damage == "inventory":
        (witness,) = [w for w in graph["witnesses"] if w["id"] == f"witness.{text}.lu1961"]
        del witness["source_dependencies"]
        expected = "graph"
    else:
        apparatus["note"] = "The witnesses agree on the substantive text."
        expected = "chant-book reading"
    path.write_text(json.dumps(apparatus, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rejects(assert_lu, core(text), folder, graph, message=expected)
    if damage == "drop-entry":
        errors, _, _ = collate(core(text), folder)
        assert errors and all("lu" in e or "stale" in e for e in errors)


# --- provenance, protection and every consumer ----------------------------------------------------
CHANGED = {
    "pl": [EPISTLE, OFFERTORY, POSTCOMMUNION, EPIPHANY_INTROIT],
    "en": [INTROIT, COLLECT, EPISTLE, GOSPEL, OFFERTORY, SECRET, POSTCOMMUNION, III_INTROIT],
}
CHANGED["en"].append(EPIPHANY_INTROIT)


def test_changed_sites_preserve_fixed_formula_scope_and_current_provenance():
    assert protected("orationes.gloria-patri", "pl") and protected("orationes.pater-noster", "pl")
    for language, texts in CHANGED.items():
        sites = provenance(language)
        for text in texts:
            doc, lay = core(text), layer(language, text)
            assert check_layer(doc, lay, layer_path(language, text)) == []
            assert prose.check(lay) == []
            clean(doc, lay)
            for segment in doc["segments"]:
                if segment["type"] != "verse":
                    continue
                expected_protection = assert_protection_scope(
                    text, language, segment["id"], lay["segments"][segment["id"]]["translation"]
                )
                site = sites[f"{text}.{segment['id']}.{language}"]
                assert site["familiar_core"] is expected_protection and site["review"] == "working"
                assert site["source_sha256"] == canonical_hash(source_payload(segment))
                target = lay["segments"][segment["id"]]["translation"]
                assert site["target_sha256"] == canonical_hash(target)


def consumers(text):
    found = []
    for path in sorted((ROOT / "formularies").glob("*/*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        if any(c["text"] == text for c in doc["components"]):
            found.append(path)
    return found


CONSUMED = [(text, "dominica-v-post-pascha") for text in PROPERS]
CONSUMED += [
    (III_INTROIT, "dominica-iii-post-pascha"),
    (EPIPHANY_INTROIT, "dominica-ii-post-epiphaniam"),
]


@pytest.mark.parametrize("text,expected", CONSUMED)
def test_every_consumer_of_a_changed_text_reads_cleanly(text, expected):
    vigil_references = {
        P + role
        for role in (
            "introitus",
            "collecta",
            "alleluia",
            "offertorium",
            "secreta",
            "communio",
            "postcommunio",
        )
    }
    expected_consumers = [expected]
    if text in vigil_references:
        expected_consumers.append("vigilia-ascensionis")
    found = consumers(text)
    assert [path.stem for path in found] == expected_consumers
    for path in found:
        for component in json.loads(path.read_text(encoding="utf-8"))["components"]:
            body = core(component["text"])
            for language in ("pl", "en"):
                lay = layer(language, component["text"])
                assert interlinear.check(body, lay) == [], (component["text"], language)
                assert check_layer(body, lay, layer_path(language, component["text"])) == []


def test_removing_the_historical_origin_is_rejected():
    sites = provenance("en")
    sites[REVISED]["origin"] = "working-unsettled"
    rejects(assert_revised, sites, message="English origin")
