"""Fourth Sunday after Easter: word captions, groups, verses, oration conclusions, the English
Communion and the Gospel verses it shares, provenance, and the Communion apparatus.

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

from build_reader import store
from build_reader.bibliography_bindings import digest, selected_text
from checks import english, interlinear, interlinear_quality, prose
from checks.apparatus import derived_summary
from checks.collate import collate
from checks.language_packs import check_layer
from checks.translation_provenance import canonical_hash, check, protected, source_payload

ROOT = Path(__file__).resolve().parents[1]
P = "proprium.dominica-iv-post-pascha-"
ROLES = "introitus collecta epistola alleluia evangelium offertorium secreta communio postcommunio"
PROPERS = [P + role for role in ROLES.split()]
INTROIT, COLLECT, EPISTLE, ALLELUIA, GOSPEL, OFFERTORY, SECRET, COMMUNION, POSTCOMMUNION = PROPERS
PREFACE = "ordinarium.praefatio-paschalis"
EPIPHANY_OFFERTORY = "proprium.dominica-ii-post-epiphaniam-offertorium"
XVIII_SECRET = "proprium.dominica-xviii-post-pentecosten-secreta"
TEXTS = {role: P + role for role in ROLES.split()} | {
    "ii-epiphania-offertorium": EPIPHANY_OFFERTORY
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
    return f"{row[1]}-{row[2].split('-')[-1]}-{row[3] if isinstance(row[3], str) else row[3][0]}"


# --- word captions ------------------------------------------------------------------------------
# (tag, language, text, word, Latin form, selected caption, predecessor caption)
CAPTIONS: list[tuple[Any, ...]] = [
    ("salvation", "pl", INTROIT, "w020", "Salvávit", "Zbawiła", "przyniosła zwycięstwo"),
    ("caption case", "pl", GOSPEL, "w004", "Dixit", "powiedział", "Powiedział"),
    ("correlative", "pl", POSTCOMMUNION, "w012", "et", "i", None),
    *[("Communion", "en", COMMUNION, w, "de", "concerning", "of") for w in ids(9, 12, 15)],
    ("Gospel", "en", GOSPEL, "w032", "Sed", "But", "Yet"),
    *[("Gospel", "en", GOSPEL, w, "de", "concerning", "of") for w in ids(64, 67, 70)],
    ("Gospel", "en", GOSPEL, "w072", "De", "Concerning", "Of"),
    ("Gospel", "en", GOSPEL, "w145", "annuntiábit", "will announce it", "will declare it"),
    ("Iubilate", "en", EPIPHANY_OFFERTORY, "w001", "Iubiláte", "Shout for joy", "Sing joyfully"),
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
    if row[6] is None:
        # The predecessor recorded a zero realization for the first member of et … et.
        lay["words"][row[3]].pop("gloss")
        zero = {"words": [row[3]], "reason": "idiom"}
        lay["segments"]["s01"].setdefault("alignments", []).append(zero)
    else:
        lay["words"][row[3]]["gloss"] = row[6]
    rejects(assert_caption, doc, lay, row, message=f"{row[0]} caption")


# --- realizations: word captions and minimal groups replacing a predecessor group ---------------
# One entry per predecessor group: "tag | language | text | [members @anchor] predecessor caption",
# then the selected realization of the same words, items separated by "; ". A member list is a
# range (w002-w005) or single ids; "[w025 w026 @w025] I have spoken" is a group.
REALIZATIONS = """
Communion|en|communio|[w002-w005 @w002] the Paraclete, the Spirit of truth, comes
    w002 comes; w003 the Paraclete; w004 the Spirit; w005 of truth
Communion|en|communio|[w007-w008 @w007] will prove the world wrong
    [w007 w008 @w007] will expose the world’s error
Gospel|en|evangelium|[w024-w027 @w025] I have spoken these things to you
    w024 these things; [w025 w026 @w025] I have spoken; w027 to you
Gospel|en|evangelium|[w037-w038 @w037] it is for your good
    [w037 w038 @w037] it is to your advantage
Gospel|en|evangelium|[w062-w063 @w062] He will prove the world wrong
    [w062 w063 @w062] He will expose the world’s error
Gospel|en|evangelium|[w114-w117 @w114] He, the Spirit of truth, comes
    [w114 w115 @w114] He comes; w116 the Spirit; w117 of truth
Gospel|en|evangelium|[w128-w130 @w130] He will speak whatever He hears
    w128 whatever; w129 He hears; w130 He will speak
Gospel|en|evangelium|[w132-w136 @w135] He will declare to you the things that are to come
    w132 the things that; [w133 w134 @w133] are to come; w135 He will announce; w136 to you
Gospel|en|evangelium|[w141-w143 @w143] He will receive from what is Mine
    w141 from; w142 what is Mine; w143 He will receive
groups|en|introitus|[w006-w009 @w008] for the Lord has done wonders
    w006 for; w007 wonders; [w008 w009 @w008] the Lord has done
groups|en|introitus|[w053-w056 @w055] for the Lord has done wonders
    w053 for; w054 wonders; [w055 w056 @w055] the Lord has done
salvation|en|introitus|[w020-w027 @w020] His right hand and His holy arm have won Him victory
    w020 Has worked salvation; w021 for Him; [w022 w023 @w022] His right hand; w024 and;
    [w025 w026 w027 @w025] His holy arm
Gloria Patri|en|introitus|[w039-w040 @w040] so it is now
    w039 and; w040 now
Collect|en|collecta|[w002-w007 @w006] who brings the minds of the faithful into one accord
    w002 who; [w003 w004 @w004] the minds of the faithful; [w005 w006 w007 @w006] make of one will
Collect|en|collecta|[w011-w014 @w012] may love what You command
    [w011 w012 @w012] may love that; w013 which; w014 You command
Collect|en|collecta|[w015-w018 @w016] and desire what You promise
    [w015 w016 @w016] desire that; w017 which; w018 You promise
Collect|en|collecta|[w023-w027 @w025] our hearts may be fixed there
    w023 there; [w024 w025 w026 w027 @w025] our hearts may be fixed
Collect|en|collecta|[w028-w031 @w030] where true joys are
    w028 where; [w029 w030 w031 @w030] true joys are
Epistle|en|epistola|[w039-w043 @w039] and let every man be swift
    [w039 w040 @w039] And let; w041 every; w042 man; w043 be swift
Epistle|en|epistola|[w057-w060 @w060] does not work God’s justice
    w057 the justice; w058 of God; [w059 w060 @w060] does not work
Offertory|en|offertorium|[w014-w018 @w014] all of you who fear God
    w014 you; w015 all you; w016 who; w017 fear; w018 God
Offertory|en|offertorium|[w019-w021 @w020] what great things the Lord has done
    w019 what great things; [w020 w021 @w020] the Lord has done
Secret|en|secreta|[w002-w003 @w002] by whom we
    w002 who; w003 us
Secret|en|secreta|[w005-w008 @w008] the venerable exchange of this sacrifice
    w005 of this; w006 sacrifice; w007 venerable; w008 exchanges
Secret|en|secreta|[w009-w013 @w013] have been made partakers of the one supreme Godhead
    w009 of the one; w010 supreme; w011 Godhead; w012 partakers; w013 have made
Secret|en|secreta|[w018-w020 @w019] we know Your truth
    w018 Your; w019 we know; w020 truth
Secret|en|secreta|[w021-w025 @w025] so we may attain it by worthy conduct
    w021 so; w022 it; w023 by worthy; w024 conduct; w025 we may attain
Postcommunion|en|postcommunio|[w007-w011 @w011] by these things which we have faithfully received
    w007 by; w008 these things; w009 which; w010 faithfully; w011 we have received
Secret|pl|secreta|[w005-w008 @w008] godną czci wymianę tej ofiary
    w005 tej; w006 ofiary; w007 czcigodne; w008 wymiany
"""
# The oration conclusions take the corpus's majority realization of each part.
CONCLUSION_STARTS = {COLLECT: 32, SECRET: 26, POSTCOMMUNION: 21}
CONCLUSION_SPECS = [
    ("[p0-p2 @p1] Through our Lord", "p0 Through; [p1 p2 @p1] our Lord"),
    ("[p7-p9 @p9] who lives with You", "p7 who; p8 with You; p9 lives"),
    (
        "[p12-p15 @p13] in the unity of the Holy Spirit",
        "p12 in; p13 the unity; [p14 p15 @p14] of the Holy Spirit",
    ),
]


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
    for text, per in CONCLUSION_STARTS.items():
        for old, new in CONCLUSION_SPECS:

            def at(spec, per=per):
                return re.sub(r"p(\d+)", lambda m: f"w{per + int(m[1]):03d}", spec)

            rows.append(
                (
                    "conclusion",
                    "en",
                    text,
                    group(*item(at(old))[1:]),
                    [item(s) for s in at(new).split("; ")],
                )
            )
    return rows


REGROUPS = parse_realizations(REALIZATIONS)


def regroup_id(row):
    return f"{row[1]}-{row[2].split('-')[-1]}-{row[3]['words'][0]}"


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
    assert len(REGROUPS) == 38
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


# --- selected minimal groups and their contextual captions --------------------------------------
# (tag, text, first member, last member, anchor, selected, predecessor)
GROUP_CAPTIONS = [
    ("Gospel", GOSPEL, 51, 53, "w053", "but if I go away", "but if I go"),
    ("Gospel", GOSPEL, 80, 82, "w081", "but concerning justice", "but of justice"),
    ("Gospel", GOSPEL, 92, 94, "w093", "and concerning judgment", "and of judgment"),
    ("source of speech", GOSPEL, 125, 126, "w126", "on His own authority", "from Himself"),
    ("caption case", GOSPEL, 112, 113, "w112", "But when", "but when"),
    ("caption case", EPISTLE, 2, 4, "w003", "Every excellent gift", "every excellent gift"),
    ("caption case", ALLELUIA, 3, 4, "w003", "The Lord’s right hand", "the Lord’s right hand"),
]
GROUP_IDS = [f"{r[1].split('-')[-1]}-w{r[2]:03d}" for r in GROUP_CAPTIONS]


def assert_group_caption(doc, lay, row):
    tag, _text, first, last, anchor, gloss, _old = row
    members = span(first, last)
    touching = [g for g in alignments(lay) if set(g["words"]) & set(members)]
    assert touching == [group(members, anchor, gloss)], f"{tag} group caption"
    assert all("gloss" not in lay["words"][w] for w in members), f"{tag} group caption"
    clean(doc, lay)


@pytest.mark.parametrize("row", GROUP_CAPTIONS, ids=GROUP_IDS)
def test_selected_group_caption(row):
    assert_group_caption(core(row[1]), layer("en", row[1]), row)


@pytest.mark.parametrize("row", GROUP_CAPTIONS, ids=GROUP_IDS)
def test_predecessor_group_caption_is_rejected(row):
    doc, lay = core(row[1]), layer("en", row[1])
    (target,) = [g for g in alignments(lay) if g["words"] == span(row[2], row[3])]
    target["gloss"] = row[6]
    rejects(assert_group_caption, doc, lay, row, message=f"{row[0]} group caption")


def test_the_source_of_speech_has_one_minimal_realization():
    doc, lay = core(GOSPEL), layer("en", GOSPEL)
    assert [words(doc)[w]["form"] for w in ids(125, 126)] == ["a", "semetípso"]
    row = next(r for r in GROUP_CAPTIONS if r[0] == "source of speech")
    assert_group_caption(doc, lay, row)
    # The preceding negative predicate remains a separate complete unit.
    assert group(ids(122, 123, 124), "w124", "For He will not speak") in alignments(lay)
    bad = deepcopy(lay)
    bad["segments"]["s01"]["alignments"] = [
        g for g in alignments(bad) if not set(g["words"]) & set(ids(125, 126))
    ]
    bad["words"]["w125"]["gloss"] = "from"
    bad["words"]["w126"]["gloss"] = "Himself"
    rejects(assert_group_caption, doc, bad, row, message="source of speech group caption")


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
    members = span(CONCLUSION_STARTS[text], CONCLUSION_STARTS[text] + 16)
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


@pytest.mark.parametrize("text", sorted(CONCLUSION_STARTS))
def test_the_three_conclusions_share_one_realization(text):
    assert conclusion_line(text) == CONCLUSION


def test_a_regrouped_conclusion_is_rejected():
    bad = layer("en", SECRET)
    seg = bad["segments"]["s01"]
    seg["alignments"] = [g for g in seg["alignments"] if not set(g["words"]) & set(span(33, 35))]
    seg["alignments"].append(group(span(33, 35), "w035", "who lives with You"))
    for wid in span(33, 35):
        bad["words"][wid].pop("gloss", None)
    assert conclusion_line(SECRET, bad) != CONCLUSION
    assert conclusion_line(SECRET, bad)[5] == "who lives with You"


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


# --- the Secret shares its body with the Secret of the XVIII Sunday after Pentecost ---------------
@pytest.mark.parametrize("language", ["pl", "en"])
def test_the_secret_reads_the_shared_words_as_the_xviii_sunday_does(language):
    mine_doc, other_doc = words(core(SECRET)), words(core(XVIII_SECRET))
    expected = [other_doc[w]["form"].replace("éfficis", "effecísti") for w in span(1, 25)]
    assert [mine_doc[w]["form"] for w in span(1, 25)] == expected
    mine, theirs = layer(language, SECRET), layer(language, XVIII_SECRET)
    shared = span(5, 8) if language == "pl" else [w for w in span(1, 25) if w != "w013"]
    assert_shared(mine, theirs, shared)
    bad = deepcopy(mine)
    bad["words"][shared[-1]]["gloss"] = "arbitrary"
    rejects(assert_shared, bad, theirs, shared, message="shared Secret caption")


def assert_shared(mine, theirs, shared):
    for wid in shared:
        assert mine["words"][wid]["gloss"] == theirs["words"][wid]["gloss"], "shared Secret caption"
    assert not [g for g in alignments(mine) if set(g["words"]) & set(shared)], "shared Secret group"


def test_the_secret_keeps_the_active_perfect_of_effecisti():
    verb = words(core(SECRET))["w013"]
    morph = verb["morph"]
    assert (verb["lemma"], morph["tense"], morph["voice"], morph["person"]) == (
        "efficio",
        "perf",
        "act",
        2,
    )
    lay = layer("en", SECRET)
    assert lay["words"]["w013"]["gloss"] == "have made" and lay["words"]["w003"]["gloss"] == "us"
    assert layer("en", XVIII_SECRET)["words"]["w013"]["gloss"] == "make"
    assert "You have made us partakers" in lay["segments"]["s01"]["translation"]


# --- verses ---------------------------------------------------------------------------------------
# (tag, language, text, selected phrase, predecessor phrase); segment s01 throughout.
VERSES = [
    (
        "Communion",
        "en",
        COMMUNION,
        "When the Paraclete, the Spirit of truth, comes, He will expose the world’s error "
        "concerning sin, and concerning justice, and concerning judgment, alleluia, alleluia.",
        "When the Paraclete comes, the Spirit of truth, He will convict the world of sin, and of "
        "justice, and of judgment, alleluia, alleluia.",
    ),
    (
        "Gospel",
        "en",
        GOSPEL,
        "But I tell you the truth: it is to your advantage that I go; for if I do not go away, "
        "the Paraclete will not come to you; but if I go away, I will send Him to you.",
        "But I tell you the truth: it is expedient for you that I go; for if I do not go away, "
        "the Paraclete will not come to you; but if I go away, I will send Him to you.",
    ),
    (
        "Gospel",
        "en",
        GOSPEL,
        "And when He comes, He will expose the world’s error concerning sin, and concerning "
        "justice, and concerning judgment. Concerning sin, because they have not believed in Me; "
        "concerning justice, because I go to the Father, and you will see Me no longer; and "
        "concerning judgment, because the prince of this world has already been judged.",
        "And when He comes, He will convict the world of sin, and of justice, and of judgment. Of "
        "sin, because they have not believed in Me; of justice, because I go to the Father, and "
        "you will see Me no longer; and of judgment, because the prince of this world has already "
        "been judged.",
    ),
    (
        "Gospel",
        "en",
        GOSPEL,
        "For He will not speak on His own authority, but whatever He hears, He will speak; "
        "and the things that are to come He will announce to you.",
        "For He will not speak from Himself, but whatever He hears, He will speak; and the "
        "things that are to come He will announce to you.",
    ),
    (
        "Gospel",
        "en",
        GOSPEL,
        "He will glorify Me, because He will receive from what is Mine and will announce it to "
        "you.",
        "He will glorify Me, because He will receive from what is Mine and will declare it to you.",
    ),
    (
        "salvation",
        "en",
        INTROIT,
        "His right hand and His holy arm have worked salvation for Him.",
        "His right hand and His holy arm have won Him victory.",
    ),
    (
        "salvation",
        "pl",
        INTROIT,
        "Jego prawica i Jego święte ramię przyniosły Mu zbawienie.",
        "Jego prawica i Jego święte ramię przyniosły Mu zwycięstwo.",
    ),
    (
        "Iubilate",
        "en",
        EPIPHANY_OFFERTORY,
        "Shout for joy to God, all the earth;",
        "Sing joyfully to God, all the earth;",
    ),
]
VERSE_IDS = [f"{r[1]}-{r[2].split('-')[-1]}-{i}" for i, r in enumerate(VERSES)]


def assert_verse(lay, row):
    tag, language, text, present, absent = row
    target = lay["segments"]["s01"]["translation"]
    assert target.count(present) == 1 and absent not in target, f"{tag} verse"
    site = provenance(language)[f"{text}.s01.{language}"]
    assert site["target_sha256"] == canonical_hash(target), f"{tag} provenance"
    assert site["review"] == "working" and not protected(text, language, "s01")


@pytest.mark.parametrize("row", VERSES, ids=VERSE_IDS)
def test_selected_verse(row):
    assert_verse(layer(row[1], row[2]), row)


@pytest.mark.parametrize("row", VERSES, ids=VERSE_IDS)
def test_predecessor_verse_is_rejected(row):
    lay = layer(row[1], row[2])
    target = lay["segments"]["s01"]["translation"]
    lay["segments"]["s01"]["translation"] = target.replace(row[3], row[4])
    rejects(assert_verse, lay, row, message=f"{row[0]} verse")


def test_the_gospel_keeps_its_other_sentences():
    gospel = layer("en", GOSPEL)["segments"]["s01"]["translation"]
    assert gospel.startswith(
        "At that time, Jesus said to His disciples: I go to Him who sent Me, and none of you asks "
        "Me: Where are You going? But because I have spoken these things to you, sorrow has filled "
        "your heart. But I tell you the truth:"
    )
    for sentence in (
        "I have yet many things to say to you, but you cannot bear them now.",
        "But when He, the Spirit of truth, comes, He will teach you all truth.",
    ):
        assert gospel.count(sentence) == 1
    assert gospel.endswith("will announce it to you.")


# --- a bounded regression check, not an authorship or rights detector ---------------------------
REPLACED = ("convict the world of sin, and of justice, and of judgment",)


def english_strings(lay):
    out = [lay.get("about", "")]
    for seg in lay["segments"].values():
        out.append(seg.get("translation") or "")
        out += [g.get("gloss", "") for g in seg.get("alignments", [])]
    for entry in lay["words"].values():
        out += [entry.get("gloss", ""), entry.get("explanation", "")]
    return [s for s in out if s]


def replaced_renderings(lay):
    """Each replaced rendering found in a field or across the joined caption line."""
    joined = " ".join(english_strings(lay)).casefold()
    return sorted(phrase for phrase in REPLACED if phrase in joined)


@pytest.mark.parametrize("text", [COMMUNION, GOSPEL])
def test_no_english_layer_of_this_mass_carries_the_replaced_renderings(text):
    assert replaced_renderings(layer("en", text)) == []


@pytest.mark.parametrize("phrase", REPLACED)
def test_a_reintroduced_rendering_is_detected(phrase):
    bad = layer("en", GOSPEL)
    words_of = phrase.split()
    first, rest = words_of[0], " ".join(words_of[1:])
    bad["words"]["w062"]["gloss"], bad["words"]["w063"]["gloss"] = first, rest
    assert phrase in replaced_renderings(bad)


def test_common_english_phrases_are_not_treated_as_copying():
    candidate = layer("en", GOSPEL)
    candidate["words"]["w126"]["explanation"] = "The phrase concerns speaking on His own authority."
    assert replaced_renderings(candidate) == []


def test_the_communion_and_gospel_render_the_shared_clause_alike():
    communion, gospel = layer("en", COMMUNION), layer("en", GOSPEL)
    clause = (
        "He will expose the world’s error concerning sin, and concerning justice, "
        "and concerning judgment"
    )
    assert clause in communion["segments"]["s01"]["translation"]
    assert clause in gospel["segments"]["s01"]["translation"]
    latin_c, latin_g = words(core(COMMUNION)), words(core(GOSPEL))
    pairs = list(zip(span(7, 16), span(62, 71), strict=True))
    assert all(latin_c[c]["lemma"] == latin_g[g]["lemma"] for c, g in pairs)

    def captions(lay, side):
        return [lay["words"][pair[side]]["gloss"] for pair in pairs[2:]]

    assert captions(communion, 0) == captions(gospel, 1)
    for lay, members, gloss in (
        (communion, ids(7, 8), "will expose the world’s error"),
        (gospel, ids(62, 63), "He will expose the world’s error"),
    ):
        assert [g for g in alignments(lay) if set(g["words"]) & set(members)] == [
            group(members, members[0], gloss)
        ]
        assert all("gloss" not in lay["words"][wid] for wid in members)
        clean(core(lay["text"]), lay)
    bad = deepcopy(gospel)
    bad["words"]["w064"]["gloss"] = "about"
    assert captions(communion, 0) != captions(bad, 1)


# --- provenance of the English Communion and Gospel -----------------------------------------------
UNSETTLED = [f"{COMMUNION}.s01.en", f"{GOSPEL}.s01.en"]


def assert_unsettled(sites):
    for site in UNSETTLED:
        row = sites[site]
        actual = (row["origin"], row["review"], row["familiar_core"])
        assert actual == ("working-unsettled", "working", False), "English origin"


def test_the_communion_and_gospel_are_held_as_unsettled_working_wording():
    assert_unsettled(provenance("en"))
    errors, _tally = check(ROOT)
    assert not [e for e in errors if any(site in e for site in UNSETTLED)]


@pytest.mark.parametrize("site", UNSETTLED)
def test_an_own_claim_is_rejected(site):
    sites = provenance("en")
    sites[site]["origin"] = "own"
    rejects(assert_unsettled, sites, message="English origin")


# --- the salvation of the Introit (salvávit sibi) ------------------------------------------------
@pytest.mark.parametrize("language", ["pl", "en"])
def test_the_introit_renders_salvation_not_victory(language):
    verb = words(core(INTROIT))["w020"]
    assert (verb["lemma"], verb["morph"]["tense"]) == ("salvo", "perf")
    lay = layer(language, INTROIT)
    noun, other = {"pl": ("zbawieni", "zwycięst"), "en": ("salvation", "victory")}[language]
    assert noun in lay["segments"]["s01"]["translation"]
    assert other not in json.dumps(lay, ensure_ascii=False)
    assert (
        lay["words"]["w020"]["gloss"] == {"pl": "Zbawiła", "en": "Has worked salvation"}[language]
    )
    assert lay["words"]["w021"]["gloss"] == {"pl": "Mu", "en": "for Him"}[language]


# --- the Iubiláte of the two identical Offertories ------------------------------------------------
def test_the_two_jubilate_offertories_read_alike():
    assert [w["form"] for w in words(core(OFFERTORY)).values()] == [
        w["form"] for w in words(core(EPIPHANY_OFFERTORY)).values()
    ]
    a, b = layer("en", OFFERTORY), layer("en", EPIPHANY_OFFERTORY)
    assert a["words"]["w001"]["gloss"] == b["words"]["w001"]["gloss"] == "Shout for joy"
    for lay in (a, b):
        assert lay["segments"]["s01"]["translation"].startswith(
            "Shout for joy to God, all the earth;"
        )
    for wid in span(13, 19):
        assert a["words"][wid]["gloss"] == b["words"][wid]["gloss"], wid
    pair = [g for g in alignments(a) if g["words"] == ids(20, 21)]
    assert pair and pair == [g for g in alignments(b) if g["words"] == ids(20, 21)]


# --- no clause-sized group remains in the nine proper texts ---------------------------------------
# Every group of three or more words left in this Mass, with its caption.
LONG_GROUPS = {
    ("pl", GOSPEL): [("w122", "Nie będzie bowiem mówił")],
    ("en", INTROIT): [("w025", "His holy arm"), ("w044", "forever and ever")],
    ("pl", COLLECT): [("w005", "jednoczysz w jednej woli")],
    ("en", COLLECT): [
        ("w005", "make of one will"),
        ("w024", "our hearts may be fixed"),
        ("w029", "true joys are"),
        ("w049", "forever and ever"),
    ],
    ("en", EPISTLE): [
        ("w002", "Every excellent gift"),
        ("w006", "every perfect gift"),
        ("w036", "my dearest brothers"),
    ],
    ("en", ALLELUIA): [("w016", "dies no more"), ("w020", "will no longer have dominion over Him")],
    ("en", GOSPEL): [
        ("w001", "At that time"),
        ("w051", "but if I go away"),
        ("w080", "but concerning justice"),
        ("w084", "I go to the Father"),
        ("w088", "you will no longer see"),
        ("w092", "and concerning judgment"),
        ("w096", "the prince of this world"),
        ("w099", "has already been judged"),
        ("w102", "Yet I have many things"),
        ("w122", "For He will not speak"),
    ],
    ("en", SECRET): [("w043", "forever and ever")],
    ("en", POSTCOMMUNION): [("w017", "delivered from all dangers"), ("w038", "forever and ever")],
}


def long_groups(lay):
    return [(g["words"][0], g["gloss"]) for g in alignments(lay) if len(g["words"]) >= 3]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_only_the_reviewed_longer_groups_remain(language):
    for text in PROPERS:
        assert long_groups(layer(language, text)) == LONG_GROUPS.get((language, text), []), text
    bad = layer("en", GOSPEL)
    seg = bad["segments"]["s01"]
    seg["alignments"] = [g for g in seg["alignments"] if not set(g["words"]) & set(span(128, 130))]
    seg["alignments"].append(group(span(128, 130), "w130", "He will speak whatever He hears"))
    assert ("w128", "He will speak whatever He hears") in long_groups(bad)


# --- caption case: a caption at a genuine sentence opening follows the target sentence's capital;
# inside a sentence it is lower case. Bounded to this Mass and its Preface (RF6 pattern).
CASE_TEXTS = [*PROPERS, PREFACE]
# Reviewed lower-case captions at a Latin opening whose target sentence continues.
CONTINUATIONS = {
    **{
        (language, text, wid): caption
        for text, wid in ((COLLECT, "w039"), (SECRET, "w033"), (POSTCOMMUNION, "w028"))
        for language, caption in (("pl", "który"), ("en", "who"))
    },
    ("pl", GOSPEL, "w004"): "powiedział",
}
# A reviewed target-language sentence opening, independent of the Latin punctuation.
RESIDUAL = {("pl", GOSPEL, "w042"): "Jeśli"}
# Capitals a lower-case Latin word may carry here: words for God, Christ and the Spirit, English I.
NAMED = {
    "pl": {"Mu", "Jego", "Twoim", "Twojego", "Tego", "Mnie", "Ja", "Go", "On", "Prawdy", "Siebie"}
    | {"Bóstwa", "Twoją", "Twojej"},
    "en": {"He", "Him", "His", "Himself", "I", "Me", "You", "Your", "Godhead"},
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
    ("pl", INTROIT, "w020", "Zbawiła", "alleluja, alleluja. ", "Jego prawica"),
    ("en", INTROIT, "w020", "Has worked salvation", "alleluia, alleluia. ", "His right hand"),
    ("en", EPISTLE, "w002", "Every excellent gift", "Dearly beloved: ", "Every excellent gift"),
    ("en", EPISTLE, "w039", "And let", "my dearest brothers. ", "And let every man"),
    ("en", ALLELUIA, "w003", "The Lord’s right hand", "alleluia. ", "The right hand of the Lord"),
    ("en", GOSPEL, "w072", "Concerning", "concerning judgment. ", "Concerning sin, because"),
    ("en", GOSPEL, "w112", "But when", "bear them now. ", "But when He"),
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


def test_reviewed_exceptions_are_live_and_bound_to_their_address():
    for table in (CONTINUATIONS, RESIDUAL):
        for (language, text, wid), caption in table.items():
            assert caption_at(layer(language, text), wid) == caption
    bad = with_caption(layer("en", GOSPEL), "w072", "of")
    assert caption_case(core(GOSPEL), bad)[0] == [("w072", "of")]
    polish = with_caption(layer("pl", COLLECT), "w039", "who")
    assert ("w039", "who") in caption_case(core(COLLECT), polish)[0]
    inner = with_caption(layer("en", GOSPEL), "w042", "For if")
    assert caption_case(core(GOSPEL), inner)[0] == [("w042", "For if")]


# --- the Communion apparatus at w013 names both differences ---------------------------------------
WITNESS = ROOT / "witnesses" / COMMUNION
RULING = (
    "The approved Benziger printing’s spelling and comma are retained (iustítia,). The witness "
    "reading (justítia) is the same word in another editorial spelling and has no comma after it."
)


def assert_comma_entry(doc, folder):
    apparatus = json.loads((folder / "apparatus.json").read_text(encoding="utf-8"))
    (entry,) = [e for e in apparatus["adjudicated"] if e["at"] == "w013"]
    assert entry["ours"] == "iustítia," and entry["witnesses"] == {"do": "justítia"}, "comma entry"
    assert entry["ruling"] == RULING, "comma entry"
    assert entry["ours"] in RULING and entry["witnesses"]["do"] in RULING, "comma entry"
    assert entry["class"] == "orthography", "comma entry"
    assert apparatus["summary"] == derived_summary(apparatus), "comma entry"
    errors, _warnings, stats = collate(doc, folder)
    assert errors == [] and stats["orthographic"] == 4, "collation"


def test_the_communion_apparatus_records_the_comma_and_the_spelling():
    assert_comma_entry(core(COMMUNION), WITNESS)
    (collation,) = [
        c for c in load("bibliography/graph.json")["collations"] if c["text"] == COMMUNION
    ]
    apparatus = load(f"witnesses/{COMMUNION}/apparatus.json")
    assert collation["apparatus_sha256"] == digest(apparatus)
    assert collation["apparatus"] == derived_summary(apparatus)
    assert collation["selected_text_sha256"] == digest(selected_text(core(COMMUNION)))
    assert collation["review"] == {"status": "pending"}


@pytest.mark.parametrize("damage", ["old-ruling", "punctuation-class"])
def test_the_comma_entry_rejects_damage(damage, tmp_path):
    folder = tmp_path / COMMUNION
    shutil.copytree(WITNESS, folder)
    path = folder / "apparatus.json"
    apparatus = json.loads(path.read_text(encoding="utf-8"))
    (entry,) = [e for e in apparatus["adjudicated"] if e["at"] == "w013"]
    if damage == "old-ruling":
        entry["ruling"] = (
            "The approved Benziger printing's spelling is retained under the house orthography. "
            "The witness reading is the same word in another editorial spelling."
        )
    else:
        # The letters differ (iustítia / justítia), so an accidental class cannot settle it.
        entry["class"] = "punctuation"
        apparatus["summary"] = derived_summary(apparatus)
    path.write_text(json.dumps(apparatus, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if damage == "punctuation-class":
        errors, _, _ = collate(core(COMMUNION), folder)
        assert any("SUBSTANTIVE divergence" in e and "w013" in e for e in errors)
    rejects(assert_comma_entry, core(COMMUNION), folder, message="comma entry")


# --- provenance, protection and every consumer ----------------------------------------------------
CHANGED = {"pl": [INTROIT, GOSPEL, SECRET, POSTCOMMUNION], "en": [*PROPERS, EPIPHANY_OFFERTORY]}


def test_changed_sites_are_outside_the_protected_formulas_and_their_provenance_is_current():
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
                assert not protected(text, language, segment["id"]), (text, segment["id"])
                site = sites[f"{text}.{segment['id']}.{language}"]
                assert site["familiar_core"] is False and site["review"] == "working"
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


CONSUMED = [*[(text, "dominica-iv-post-pascha") for text in PROPERS]]
CONSUMED.append((EPIPHANY_OFFERTORY, "dominica-ii-post-epiphaniam"))


@pytest.mark.parametrize("text,expected", CONSUMED)
def test_every_consumer_of_a_changed_text_reads_cleanly(text, expected):
    found = consumers(text)
    assert [path.stem for path in found] == [expected]
    for component in json.loads(found[0].read_text(encoding="utf-8"))["components"]:
        body = core(component["text"])
        for language in ("pl", "en"):
            lay = layer(language, component["text"])
            assert interlinear.check(body, lay) == [], (component["text"], language)
            assert check_layer(body, lay, layer_path(language, component["text"])) == []
