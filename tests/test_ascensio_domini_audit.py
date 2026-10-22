"""The Ascension of the Lord: word captions, groups and verses of the Mass and its Preface, the
about notes of the shared Preface and Offertory, the English chant verses held as unsettled
wording, the Liber Usualis comparison and the p. 347 reprint of the Offertory, the Lesson witness
header, three accent rulings, the Polish ulterior card, and the reading of Iubiláte in the
Introits and chants that sing Ps 65:1 and Ps 99:1-2.

Finite reviewed addresses and contexts, not general rules. Every outcome is pinned by a positive
check, and each check is shown to reject a named defect (usually the predecessor value).
"""

import hashlib
import itertools
import json
import re
import shutil
from copy import deepcopy
from functools import cache
from pathlib import Path
from typing import Any

import pytest
from ascension_postcommunion_wording import (
    assert_postcommunion_constructions,
    assert_postcommunion_subject,
    current_regroup_items,
    current_verse_phrase,
    is_current_postcommunion_subject,
)
from provenance_successor_fixture import assert_protection_scope

from build_reader import store
from build_reader.bibliography_bindings import digest, selected_text, transcript_digest
from checks import english, interlinear, interlinear_quality, prose
from checks.apparatus import derived_summary
from checks.collate import collate, load_witness
from checks.language_packs import check_layer
from checks.lexicon import lint_lemmata
from checks.translation_basis import check as check_basis
from checks.translation_provenance import canonical_hash, check, protected, source_payload

ROOT = Path(__file__).resolve().parents[1]
P = "proprium.ascensio-domini-"
ROLES = "introitus collecta epistola alleluia evangelium offertorium secreta communio postcommunio"
PROPERS = [P + role for role in ROLES.split()]
INTROIT, COLLECT, EPISTLE, ALLELUIA, GOSPEL, OFFERTORY, SECRET, COMMUNION, POSTCOMMUNION = PROPERS
PREFACE = "ordinarium.praefatio-ascensionis"
II_EPI_INTROIT = "proprium.dominica-ii-post-epiphaniam-introitus"
I_EPI = "proprium.dominica-i-post-epiphaniam-"
I_EPI_ALLELUIA = I_EPI + "alleluia"
I_EPI_INTROIT = I_EPI + "introitus"
I_EPI_OFFERTORY = I_EPI + "offertorium"
QUINQ_TRACT = "proprium.dominica-in-quinquagesima-tractus"
TEXTS = {role: P + role for role in ROLES.split()} | {
    "praefatio": PREFACE,
    "ii-epiphania-introitus": II_EPI_INTROIT,
    "i-epiphania-alleluia": I_EPI_ALLELUIA,
    "i-epiphania-introitus": I_EPI_INTROIT,
    "i-epiphania-offertorium": I_EPI_OFFERTORY,
    "quinquagesima-tractus": QUINQ_TRACT,
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


def group(members, anchor, gloss):
    return {"words": members, "anchor": anchor, "gloss": gloss}


def clean(doc, lay):
    assert interlinear.check(doc, lay) == []
    if lay["language"] == "en":
        assert english.check(doc, lay) == [] and interlinear_quality.check(doc, lay) == []


def text_id(row):
    return f"{row[1]}-{row[2].split('.')[-1]}-{row[3]}"


# --- word captions ------------------------------------------------------------------------------
# One row per changed caption: "tag | language | role | word | Latin form | selected | predecessor".
CAPTION_TABLE = """
caption case|pl|introitus|w001|Viri|Mężowie|mężowie
caption case|pl|introitus|w049|Viri|Mężowie|mężowie
in hodierna die|pl|collecta|w007|hodiérna|w dzisiejszym|dzisiejszym
subject of wstąpił|pl|collecta|w009|Unigénitum|Jednorodzony|Jednorodzonego
subject of wstąpił|pl|collecta|w010|tuum|Twój|Twojego
subject of wstąpił|pl|collecta|w011|Redemptórem|Odkupiciel|Odkupiciela
subject of wstąpił|pl|collecta|w012|nostrum|nasz|naszego
caption case|pl|epistola|w001|Primum|Pierwsze|pierwsze
relative after wszystkim|pl|epistola|w009|quæ|co|które
caption case|pl|epistola|w049|Et|I|i
government|pl|epistola|w059|promissiónem|obietnicy|obietnicę
government|pl|epistola|w061|quam|którą|której
caption case|pl|epistola|w099|Non|Nie|nie
caption case|pl|epistola|w137|Et|I|i
caption case|pl|epistola|w152|Cumque|A gdy|a gdy
caption case|pl|epistola|w170|Viri|Mężowie|mężowie
caption case|pl|alleluia|w001|Allelúia|Alleluja|alleluja
caption case|pl|alleluia|w003|Ascéndit|Wstąpił|wstąpił
caption case|pl|alleluia|w012|Allelúia|Alleluja|alleluja
caption case|pl|alleluia|w024|Allelúia|Alleluja|alleluja
recumbentibus|pl|evangelium|w004|Recumbéntibus|siedzących za stołem|gdy spoczywali
caption case|pl|evangelium|w025|Et|I|i
caption case|pl|evangelium|w028|Eúntes|Idąc|idąc
caption case|pl|evangelium|w036|Qui|Kto|kto
government|pl|evangelium|w050|eos|tym|tych
caption case|pl|evangelium|w080|Et|I|i
caption case|pl|offertorium|w001|Ascéndit|Wstąpił|wstąpił
caption case|pl|secreta|w001|Súscipe|Przyjmij|przyjmij
caption case|pl|praefatio|w026|Qui|Który|który
caption case|pl|praefatio|w049|Et|I|i
caption case|pl|communio|w001|Psállite|Śpiewajcie|śpiewajcie
caption case|pl|postcommunio|w001|Præsta|Spraw|spraw
caption case|en|introitus|w001|Viri|Men|men
subject|en|introitus|w016|véniet|He will come|will come
caption case|en|introitus|w020|Omnes|All|all
caption case|en|introitus|w036|Sicut|As|as
caption case|en|introitus|w049|Viri|Men|men
subject|en|introitus|w064|véniet|He will come|will come
caption case|en|collecta|w001|Concéde|Grant|grant
caption case|en|collecta|w023|Per|Through|through
caption case|en|epistola|w001|Primum|The first|the first
article|en|epistola|w017|diem|the day|day
subject|en|epistola|w030|prǽbuit|He showed|showed
article|en|epistola|w047|regno|the kingdom|kingdom
caption case|en|epistola|w049|Et|And|and
subject|en|epistola|w051|præcépit|He commanded|commanded
article|en|epistola|w058|exspectárent|wait for|wait
article|en|epistola|w059|promissiónem|the promise|promise
direct question|en|epistola|w093|restítues|will You restore|will restore
article|en|epistola|w094|regnum|the kingdom|kingdom
article|en|epistola|w114|virtútem|the power|power
one upon|en|epistola|w115|superveniéntis|coming|coming upon
caption case|en|epistola|w137|Et|And|and
caption case|en|epistola|w152|Cumque|And while|and while
subject|en|epistola|w153|intueréntur|they were gazing|were gazing
caption case|en|epistola|w170|Viri|Men|men
caption case|en|alleluia|w001|Allelúia|Alleluia|alleluia
caption case|en|alleluia|w012|Allelúia|Alleluia|alleluia
caption case|en|alleluia|w013|Dóminus|The Lord|the Lord
caption case|en|alleluia|w024|Allelúia|Alleluia|alleluia
participle|en|evangelium|w004|Recumbéntibus|reclining at table|as they reclined
caption case|en|evangelium|w025|Et|And|and
subject|en|evangelium|w026|dixit|He said|said
caption case|en|evangelium|w028|Eúntes|Go|go
article|en|evangelium|w033|Evangélium|the Gospel|Gospel
caption case|en|evangelium|w036|Qui|He who|he who
subject|en|evangelium|w059|eiícient|they will cast out|will cast out
subject|en|evangelium|w061|loquéntur|they will speak|will speak
subject|en|evangelium|w064|tollent|they will take up|will take up
subject|en|evangelium|w069|bíberint|they drink|drink
subject|en|evangelium|w076|impónent|they will lay|will lay
caption case|en|evangelium|w080|Et|And|and
caption case|en|secreta|w001|Súscipe|Receive|receive
subject|en|secreta|w018|liberémur|we may be delivered|may be delivered
subject|en|secreta|w022|perveniámus|we may attain|may attain
caption case|en|secreta|w024|Per|Through|through
caption case|en|praefatio|w001|Vere|Truly|truly
caption case|en|praefatio|w026|Qui|Who|who
caption case|en|praefatio|w049|Et|And|and
caption case|en|communio|w001|Psállite|Sing|sing
caption case|en|postcommunio|w001|Præsta|Grant|grant
ablative|en|postcommunio|w010|visibílibus|under visible|visible
subject|en|postcommunio|w015|consequámur|we may obtain|may obtain
caption case|en|postcommunio|w017|Per|Through|through
Iubilate|en|i-epiphania-alleluia|w003|Iubiláte|Shout for joy|Sing joyfully
Iubilate|en|i-epiphania-introitus|w021|Iubiláte|Shout for joy|Sing joyfully
Iubilate|en|i-epiphania-offertorium|w001|Iubiláte|Shout for joy|Sing joyfully
Iubilate|en|quinquagesima-tractus|w001|Iubiláte|Shout for joy|Sing joyfully
"""
CAPTIONS: list[tuple[Any, ...]] = []
for _line in CAPTION_TABLE.strip().splitlines():
    _tag, _language, _role, _wid, _form, _gloss, _old = _line.split("|")
    CAPTIONS.append((_tag, _language, TEXTS[_role], _wid, _form, _gloss, _old))


def assert_caption(doc, lay, row):
    tag, _language, _text, wid, form, gloss, _old = row
    assert words(doc)[wid]["form"] == form, f"{tag} Latin context"
    if is_current_postcommunion_subject(row):
        assert_postcommunion_subject(doc, lay, row)
    else:
        assert not [g for g in alignments(lay) if wid in g["words"]], f"{tag} caption"
        assert lay["words"][wid].get("gloss") == gloss, f"{tag} caption"
    assert interlinear.check(doc, lay) == [], f"{tag} interlinear line"


def test_caption_inventory():
    tally: dict[tuple[str, str], int] = {}
    for row in CAPTIONS:
        key = (row[0], row[1])
        tally[key] = tally.get(key, 0) + 1
    assert tally[("caption case", "pl")] == 22
    assert tally[("caption case", "en")] == 27
    assert len({(r[1], r[2], r[3]) for r in CAPTIONS}) == len(CAPTIONS) == 88


@pytest.mark.parametrize("row", CAPTIONS, ids=[text_id(r) for r in CAPTIONS])
def test_selected_caption(row):
    assert_caption(core(row[2]), layer(row[1], row[2]), row)


@pytest.mark.parametrize("row", CAPTIONS, ids=[text_id(r) for r in CAPTIONS])
def test_predecessor_caption_is_rejected(row):
    doc, lay = core(row[2]), layer(row[1], row[2])
    assert_caption(doc, lay, row)
    pristine = deepcopy(lay)
    if is_current_postcommunion_subject(row):
        selected = [g for g in alignments(lay) if "w015" in g["words"]]
        assert len(selected) == 1, "subject mutation address"
        prior = selected[0]["gloss"]
        selected[0]["gloss"] = prior.replace(row[5], row[6], 1)
        assert selected[0]["gloss"] != prior, "nonvacuous subject mutation"
    else:
        lay["words"][row[3]]["gloss"] = row[6]
    assert lay != pristine, "nonvacuous caption mutation"
    rejects(assert_caption, doc, lay, row, message=f"{row[0]} caption")
    assert layer(row[1], row[2]) == pristine, "caption sibling fixture unchanged"
    assert_caption(doc, pristine, row)


def test_the_polish_collect_reads_its_subject_in_the_nominative():
    lay = layer("pl", COLLECT)
    line = [lay["words"][w]["gloss"] for w in ids(*range(6, 17))]
    assert line == [
        *("którzy", "w dzisiejszym", "dniu", "Jednorodzony", "Twój", "Odkupiciel", "nasz"),
        *("do", "nieba", "wstąpił", "wierzymy"),
    ]
    assert (
        "w dzisiejszym dniu Twój Jednorodzony, Odkupiciel nasz, wstąpił"
        in (lay["segments"]["s01"]["translation"])
    )


# --- realizations: groups made, changed, split or emptied ---------------------------------------
# One entry per address: "tag | language | role | predecessor realization", then the selected
# realization of the same words. Items are separated by "; ": "w013 caption" is a word caption,
# "[w040 w041 @w040] caption" a group, "[w089 ~word-order]" a zero alignment.
REALIZATIONS = """
possessive|en|collecta|w009 Only-begotten; w010 Your
    [w009 w010 @w009] Your Only-begotten
possessive|en|collecta|w011 Redeemer; w012 our
    [w011 w012 @w011] our Redeemer
possessive|en|collecta|w025 Lord; w026 our
    [w025 w026 @w025] our Lord
possessive|en|collecta|w029 Son; w030 Your
    [w029 w030 @w029] Your Son
subject|en|epistola|[w026 w027 @w026] was taken up
    [w026 w027 @w026] He was taken up
possessive|en|epistola|w034 Passion; w035 His
    [w034 w035 @w034] His Passion
possessive|en|epistola|w065 mouth; w066 My
    [w065 w066 @w065] My mouth
direct question|en|epistola|w089 whether
    [w089 ~word-order]
subject|en|epistola|w141 while watching; w142 they
    [w141 w142 @w141] while they looked on
subject|en|epistola|[w143 w144 @w143] was lifted up
    [w143 w144 @w143] He was lifted up
possessive|en|epistola|w150 sight; w151 their
    [w150 w151 @w150] their sight
order|en|epistola|w156 going; w157 Him
    [w156 w157 @w156] as He went
possessive|en|evangelium|w012 unbelief; w013 their
    [w012 w013 @w012] their unbelief
order|en|evangelium|w039 baptized; w040 is
    [w039 w040 @w039] is baptized
possessive|en|evangelium|w056 name; w057 My
    [w056 w057 @w056] My name
possessive|en|secreta|w026 Lord; w027 our
    [w026 w027 @w026] our Lord
possessive|en|secreta|w030 Son; w031 Your
    [w030 w031 @w030] Your Son
sumenda|en|postcommunio|[w012 w013 @w013] we have received
    w012 to be taken; w013 we have received
possessive|en|postcommunio|w018 Lord; w019 our
    [w018 w019 @w018] our Lord
possessive|en|postcommunio|w022 Son; w023 Your
    [w022 w023 @w022] Your Son
"""


def item(spec):
    spec = spec.strip()
    if spec.startswith("["):
        inside, _, caption = spec[1:].partition("]")
        if "~" in inside:
            wid, reason = inside.split(" ~")
            return ("z", [wid], reason)
        listed, anchor = inside.split(" @")
        return ("g", listed.split(), anchor, caption.strip())
    wid, caption = spec.split(" ", 1)
    return ("w", wid, caption)


def members_of(items):
    return [w for i in items for w in ([i[1]] if i[0] == "w" else i[1])]


def parse_realizations(table):
    rows: list[tuple[Any, ...]] = []
    lines = table.strip("\n").split("\n")
    while lines:
        tag, language, role, old = lines.pop(0).split("|")
        selected = lines.pop(0).strip()
        rows.append(
            (
                tag,
                language,
                TEXTS[role],
                [item(s) for s in old.split("; ")],
                [item(s) for s in selected.split("; ")],
            )
        )
    return rows


REGROUPS = parse_realizations(REALIZATIONS)


def regroup_id(row):
    return f"{row[1]}-{row[2].split('.')[-1]}-{members_of(row[4])[0]}"


def assert_realization(doc, lay, row):
    tag, _language, _text, _old, _historical_items = row
    items = current_regroup_items(row)
    members = members_of(items)
    touching = [g for g in alignments(lay) if set(g["words"]) & set(members)]
    expected = [
        {"words": i[1], "reason": i[2]} if i[0] == "z" else group(i[1], i[2], i[3])
        for i in items
        if i[0] != "w"
    ]
    assert touching == expected, f"{tag} realization"
    captions = {i[1]: i[2] for i in items if i[0] == "w"}
    for wid in members:
        assert lay["words"][wid].get("gloss") == captions.get(wid), f"{tag} realization"
    clean(doc, lay)


def test_realization_inventory():
    assert len(REGROUPS) == 20
    assert sum(1 for r in REGROUPS if r[0] == "possessive") == 13
    for row in REGROUPS:
        assert members_of(row[3]) == members_of(row[4])
        order = list(words(core(row[2])))
        found = [order.index(w) for w in members_of(row[4])]
        assert found == list(range(found[0], found[0] + len(found)))


@pytest.mark.parametrize("row", REGROUPS, ids=[regroup_id(r) for r in REGROUPS])
def test_selected_realization(row):
    assert_realization(core(row[2]), layer(row[1], row[2]), row)


@pytest.mark.parametrize("row", REGROUPS, ids=[regroup_id(r) for r in REGROUPS])
def test_predecessor_realization_is_rejected(row):
    doc, lay = core(row[2]), layer(row[1], row[2])
    old = deepcopy(lay)
    members = set(members_of(row[3]))
    for seg in old["segments"].values():
        if "alignments" in seg:
            seg["alignments"] = [g for g in seg["alignments"] if not set(g["words"]) & members]
    sid = next(s["id"] for s in doc["segments"] if any(w["id"] in members for w in s["words"]))
    for wid in members:
        old["words"][wid].pop("gloss", None)
    for i in row[3]:
        if i[0] == "w":
            old["words"][i[1]]["gloss"] = i[2]
        else:
            old["segments"][sid].setdefault("alignments", []).append(group(i[1], i[2], i[3]))
    rejects(assert_realization, doc, old, row, message=f"{row[0]} realization")


# --- the three oration conclusions ----------------------------------------------------------------
CONCLUSIONS = {
    COLLECT: ("w023", ["Through", "the same"]),
    SECRET: ("w024", ["Through", "the same"]),
    POSTCOMMUNION: ("w017", ["Through"]),
}
TAIL = [
    *("our Lord", "Jesus", "Christ", "Your Son", "who", "with You", "lives", "and", "reigns", "in"),
    *("the unity", "of the Holy Spirit", "God"),
]


def conclusion_line(text, lay):
    """The realization units from Per to Deus, one caption per alignment, in order."""
    doc = core(text)
    first, _head = CONCLUSIONS[text]
    order = list(words(doc))
    start = order.index(first)
    stop = next(i for i in range(start, len(order)) if words(doc)[order[i]]["form"] == "Deus")
    starts = {g["words"][0]: g for g in alignments(lay)}
    out, skip = [], set()
    for wid in order[start : stop + 1]:
        if wid in skip:
            continue
        if wid in starts:
            out.append(starts[wid]["gloss"])
            skip.update(starts[wid]["words"])
        else:
            out.append(lay["words"][wid]["gloss"])
    return out


@pytest.mark.parametrize("text", sorted(CONCLUSIONS))
def test_the_conclusions_read_the_corpus_pattern_with_grouped_possessives(text):
    assert conclusion_line(text, layer("en", text)) == [*CONCLUSIONS[text][1], *TAIL]


def test_a_split_possessive_in_a_conclusion_is_rejected():
    bad = layer("en", SECRET)
    bad["segments"]["s01"]["alignments"] = [
        g for g in bad["segments"]["s01"]["alignments"] if g["words"] != ids(26, 27)
    ]
    bad["words"]["w026"]["gloss"], bad["words"]["w027"]["gloss"] = "Lord", "our"
    assert conclusion_line(SECRET, bad) != [*CONCLUSIONS[SECRET][1], *TAIL]


# --- no split possessive is left in the English Mass and its Preface ------------------------------
POSSESSIVES = {"tuus", "suus", "meus", "noster", "vester"}


def split_possessives(doc, lay):
    """Noun and its possessive (adjective, or genitive eius/eorum) captioned as two words."""
    grouped = {w for g in alignments(lay) for w in g["words"]}
    found = []
    for seg in doc["segments"]:
        ws = seg.get("words", [])
        for a, b in itertools.pairwise(ws):
            possessive = b["lemma"] in POSSESSIVES or (
                b["lemma"] == "is" and b["morph"].get("case") == "gen"
            )
            if (
                a["morph"].get("pos") == "noun"
                and possessive
                and b.get("head", a["id"]) == a["id"]
                and not {a["id"], b["id"]} & grouped
            ):
                found.append((a["id"], b["id"]))
    return found


@pytest.mark.parametrize("text", [*PROPERS, PREFACE])
def test_no_split_possessive_is_left_in_the_english_mass(text):
    assert split_possessives(core(text), layer("en", text)) == []


def test_a_split_possessive_is_detected():
    bad = layer("en", GOSPEL)
    bad["segments"]["s01"]["alignments"] = [
        g for g in bad["segments"]["s01"]["alignments"] if g["words"] != ids(56, 57)
    ]
    bad["words"]["w056"]["gloss"], bad["words"]["w057"]["gloss"] = "name", "My"
    assert split_possessives(core(GOSPEL), bad) == [("w056", "w057")]


# --- verses ---------------------------------------------------------------------------------------
# (tag, language, text, selected phrase, predecessor phrase); segment s01.
VERSES = [
    (
        "sumenda",
        "en",
        POSTCOMMUNION,
        "what we have received to be taken under visible mysteries.",
        "what we have received under visible mysteries.",
    ),
    (
        "Iubilate",
        "en",
        II_EPI_INTROIT,
        "Shout for joy to God, all the earth; sing a psalm to His name, give glory to His praise.",
        "Sing joyfully to God, all the earth;",
    ),
    (
        "laudi eius",
        "pl",
        II_EPI_INTROIT,
        "śpiewajcie psalm Jego imieniu, oddajcie chwałę Jego uwielbieniu.",
        "oddajcie chwałę Jego chwale.",
    ),
    *(
        (
            "Iubilate",
            "en",
            text,
            "Shout for joy to God, all the earth; serve the Lord with gladness",
            "Sing joyfully to God, all the earth;",
        )
        for text in (I_EPI_ALLELUIA, I_EPI_INTROIT, I_EPI_OFFERTORY, QUINQ_TRACT)
    ),
]
VERSE_IDS = [f"{r[1]}-{r[2].split('.')[-1]}" for r in VERSES]


def assert_verse(lay, row):
    tag, language, text, _historical_present, absent = row
    present = current_verse_phrase(row)
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
    selected = (
        current_verse_phrase(row)
        if row[0] != "Iubilate"
        else "Shout for joy to God, all the earth;"
    )
    assert target.count(selected) == 1, "verse mutation address"
    lay["segments"]["s01"]["translation"] = target.replace(selected, row[4])
    assert lay["segments"]["s01"]["translation"] != target, "nonvacuous verse mutation"
    rejects(assert_verse, lay, row, message=f"{row[0]} verse")


def test_a_silently_edited_verse_is_rejected():
    """A verse change with its provenance hash left behind is caught by the hash pin."""
    lay = layer("en", POSTCOMMUNION)
    target = lay["segments"]["s01"]["translation"]
    pristine = deepcopy(lay)
    assert_verse(lay, VERSES[0])
    assert target.count("in the unity") == 1, "provenance mutation address"
    lay["segments"]["s01"]["translation"] = target.replace("in the unity", "in unity")
    assert lay["segments"]["s01"]["translation"] != target, "nonvacuous provenance mutation"
    rejects(assert_verse, lay, VERSES[0], message="sumenda provenance")
    lay["segments"]["s01"]["translation"] = target
    assert lay == pristine, "provenance fixture restored"
    assert_verse(lay, VERSES[0])


def test_the_postcommunion_line_renders_the_gerundive():
    lay = layer("en", POSTCOMMUNION)
    line = [lay["words"][w].get("gloss") for w in ids(*range(9, 17))]
    assert line == ["what", "under visible", "mysteries", None, None, None, None, None]
    assert_postcommunion_constructions(core(POSTCOMMUNION), lay)
    assert words(core(POSTCOMMUNION))["w012"]["morph"]["mood"] == "part"


def test_the_lesson_question_is_direct():
    lay = layer("en", EPISTLE)
    line = [lay["words"][w].get("gloss") for w in ids(*range(88, 96))]
    assert line == [
        *("Lord", None, "at", "time", "this", "will You restore", "the kingdom", "to Israel"),
    ]
    assert {"words": ["w089"], "reason": "word-order"} in alignments(lay)
    assert (
        "Lord, will You at this time restore the kingdom to Israel?"
        in (lay["segments"]["s01"]["translation"])
    )
    assert layer("pl", EPISTLE)["words"]["w089"]["gloss"] == "czy"


# --- the about notes of the shared Preface and Offertory ------------------------------------------
ABOUTS = {
    ("pl", PREFACE): (
        "Prefacja o Wniebowstąpieniu Pańskim. Wysławia Chrystusa, który po swoim "
        "zmartwychwstaniu ukazał się wszystkim uczniom i na ich oczach został wzniesiony do nieba, "
        "aby dać nam udział w swojej boskości. W święto Wniebowstąpienia Pańskiego jest prefacją "
        "własną. Od piątku po Wniebowstąpieniu do piątku przed wigilią Zesłania Ducha Świętego "
        "odmawia się ją jako prefację okresu we wszystkich Mszach, które nie mają prefacji "
        "własnej.",
        "Prefacja używana w okresie formularza „Wniebowstąpienie Pańskie” w Mszale Rzymskim z 1962 "
        "roku.",
    ),
    ("en", PREFACE): (
        "The Preface of the Ascension of the Lord. It praises Christ, who after His Resurrection "
        "appeared to all His disciples and was raised up into heaven before their eyes, to make "
        "us partakers of His divinity. It is the proper Preface of the feast of the Ascension. "
        "From the Friday after the Ascension to the Friday before the Vigil of Pentecost it is "
        "said as the Preface of the season in every Mass that has no proper Preface.",
        "The Preface used in the season of the formulary “Ascension of the Lord” in the 1962 Roman "
        "Missal.",
    ),
    ("pl", OFFERTORY): (
        "Offertorium „Ascéndit Deus” (Ps 46, 6) w Mszale Rzymskim z 1962 roku. Należy do Mszy "
        "o Wniebowstąpieniu Pańskim, którą mszał przewiduje także w dni powszednie od piątku po "
        "Wniebowstąpieniu do piątku przed wigilią Zesłania Ducha Świętego. Msza niedzieli po "
        "Wniebowstąpieniu powtarza je w całości.",
        "Offertorium formularza „Wniebowstąpienie Pańskie” w Mszale Rzymskim z 1962 roku.",
    ),
    ("en", OFFERTORY): (
        "The offertorium “Ascéndit Deus” (Psalm 46:6) in the 1962 Roman Missal. It belongs to "
        "the Mass of the Ascension of the Lord, which the Missal also appoints for the weekdays "
        "from the Friday after the Ascension to the Friday before the Vigil of Pentecost. The "
        "Mass of the Sunday after the Ascension repeats it in full.",
        "The offertorium of the formulary “Ascension of the Lord” in the 1962 Roman Missal.",
    ),
}
# Each note names the rubric's use beyond the feast, never one home formulary by its title.
USES = {
    ("pl", PREFACE): ("prefacją własną", "do piątku przed wigilią Zesłania Ducha Świętego"),
    ("en", PREFACE): ("proper Preface of the feast", "to the Friday before the Vigil of Pentecost"),
    ("pl", OFFERTORY): ("niedzieli po Wniebowstąpieniu", "do piątku przed wigilią"),
    ("en", OFFERTORY): ("Sunday after the Ascension", "to the Friday before the Vigil"),
}
ABOUT_IDS = [f"{k[0]}-{k[1].split('.')[-1]}" for k in ABOUTS]


def assert_about(lay, key):
    about = lay["about"]
    assert about == ABOUTS[key][0], "about note"
    assert "formular" not in about and "season of the" not in about, "about note"
    assert all(phrase in about for phrase in USES[key]), "about note"
    assert prose.check(lay) == [], "about note"


@pytest.mark.parametrize("key", list(ABOUTS), ids=ABOUT_IDS)
def test_the_about_note_names_the_rubrics_use(key):
    assert_about(layer(*key), key)


@pytest.mark.parametrize("key", list(ABOUTS), ids=ABOUT_IDS)
def test_the_predecessor_about_note_is_rejected(key):
    lay = layer(*key)
    lay["about"] = ABOUTS[key][1]
    rejects(assert_about, lay, key, message="about note")


def test_the_polish_offertory_note_quotes_with_polish_marks():
    about = layer("pl", OFFERTORY)["about"]
    assert "„Ascéndit Deus”" in about and "“" not in about and "”" in about


# --- the English chant verses held as unsettled wording (corpus commit 62df9860) ------------------
RELABELLED = {
    f"{ALLELUIA}.s01.en": "f514d7d16ff9d9fcec3758ec0e04734b91ff788524c1003d4d1681dec8b0a9ce",
    f"{OFFERTORY}.s01.en": "15599049d282b89377d288ef96e861c5c2776673d511029c5206a81c8f6c6cde",
    f"{COMMUNION}.s01.en": "c084e8892712745c01de95de6945434da6359d14b04ca42706210a180f2316e9",
}


def assert_unsettled(sites, site):
    row = sites[site]
    actual = (row["origin"], row["review"], row["familiar_core"])
    assert actual == ("working-unsettled", "working", False), "English origin"
    assert row["target_sha256"] == RELABELLED[site], "English wording"


@pytest.mark.parametrize("site", sorted(RELABELLED))
def test_the_chant_verse_is_held_as_unsettled_working_wording(site):
    sites = provenance("en")
    assert_unsettled(sites, site)
    text, segment, language = site.rsplit(".", 2)
    target = layer(language, text)["segments"][segment]["translation"]
    assert canonical_hash(target) == RELABELLED[site]
    errors, _tally = check(ROOT)
    assert not [e for e in errors if site in e]


@pytest.mark.parametrize("site", sorted(RELABELLED))
def test_an_own_claim_or_a_wording_change_is_rejected(site):
    sites = provenance("en")
    sites[site]["origin"] = "own"
    rejects(assert_unsettled, sites, site, message="English origin")
    sites = provenance("en")
    sites[site]["target_sha256"] = canonical_hash("Changed.")
    rejects(assert_unsettled, sites, site, message="English wording")


# --- caption case: a caption at a genuine sentence opening follows the target sentence's capital;
# inside a sentence it is lower case. Bounded to this Mass and its Preface (RF6 pattern).
CASE_TEXTS = [*PROPERS, PREFACE]
# Reviewed lower-case captions at a Latin opening whose target sentence continues.
CONTINUATIONS = {
    **{
        (language, text, wid): caption
        for text, wid in ((COLLECT, "w031"), (SECRET, "w032"), (POSTCOMMUNION, "w024"))
        for language, caption in (("pl", "który"), ("en", "who"))
    },
    ("pl", EPISTLE, "w082"): "więc",
    ("pl", EPISTLE, "w096"): "rzekł",
    ("pl", GOSPEL, "w004"): "siedzących za stołem",
    ("pl", GOSPEL, "w048"): "znaki",
    ("pl", GOSPEL, "w055"): "w",
    ("en", EPISTLE, "w082"): "therefore",
    ("en", ALLELUIA, "w003"): "has ascended",
    ("en", OFFERTORY, "w001"): "has ascended",
    ("en", GOSPEL, "w004"): "reclining at table",
    ("en", GOSPEL, "w048"): "signs",
    ("en", GOSPEL, "w055"): "in",
}
# Reviewed capitals on a lower-case Latin word that are not pronouns of God: the reverential
# Bóstwa (precedent in the Trinity preface) and the English vocative O.
REVIEWED_CAPITALS = {("pl", PREFACE, "w044"): "Bóstwa", ("en", EPISTLE, "w007"): "O"}
# Capitals a lower-case Latin word may carry here: words for God, Christ and the Spirit, English I.
NAMED = {
    "pl": {"Mu", "Jego", "Twoim", "Twojego", "Twojej", "Moim", "Mnie", "Ja", "Ci", "Cię", "Go"}
    | {"Mi", "Moich", "Tobie", "Twój"},
    "en": {"He", "Him", "His", "Himself", "I", "Me", "My", "You", "Your"},
}


HISTORICAL_CONTINUATIONS = dict(CONTINUATIONS)
HISTORICAL_REVIEWED_CAPITALS = dict(REVIEWED_CAPITALS)
CONTINUATIONS.pop(("en", OFFERTORY, "w001"))
REVIEWED_CAPITALS.pop(("pl", PREFACE, "w044"))


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
                if (
                    capital
                    and word[0] not in NAMED[language]
                    and REVIEWED_CAPITALS.get(key) != gloss
                ):
                    misses.append((first["id"], gloss))
    return misses, examined


@pytest.mark.parametrize("language", ["pl", "en"])
def test_captions_follow_the_target_sentence_in_this_mass(language):
    total = 0
    for text in CASE_TEXTS:
        misses, examined = caption_case(core(text), layer(language, text))
        assert misses == [], text
        total += examined
    assert total == 48


def test_reviewed_exceptions_are_live_and_bound_to_their_address():
    for table in (CONTINUATIONS, REVIEWED_CAPITALS):
        for (language, text, wid), caption in table.items():
            lay = layer(language, text)
            starting = [g for g in alignments(lay) if g["words"][0] == wid]
            assert (starting[0]["gloss"] if starting else lay["words"][wid]["gloss"]) == caption
    moved = layer("pl", COLLECT)
    moved["words"]["w031"]["gloss"] = "which"
    assert ("w031", "which") in caption_case(core(COLLECT), moved)[0]


@pytest.mark.parametrize("row", [r for r in CAPTIONS if r[0] == "caption case"], ids=text_id)
def test_a_reverted_caption_case_is_caught_by_the_scan(row):
    _tag, language, text, wid, _form, _gloss, old = row
    bad = layer(language, text)
    bad["words"][wid]["gloss"] = old
    assert (wid, old) in caption_case(core(text), bad)[0]


# --- the Liber Usualis comparison of the Offertory and its p. 347 reprint -------------------------
LU_SHA = "a3d5fdb3308dcabc0474eb99d2f8a5509e52c76380ae41ec373ab3aa3e7db6b9"
LU_ENTRY = {"at": "w005", "ours": "et", "lu": "", "class": "omission"}
LU_STATS = {"witnesses": 3, "partial": 0, "substantive_variants": 0, "omissions": 1}


def lu_entry(apparatus):
    found = [
        e for e in apparatus["adjudicated"] if e["at"] == LU_ENTRY["at"] and "lu" in e["witnesses"]
    ]
    assert len(found) == 1, "chant-book reading"
    return found[0]


def assert_lu(doc, folder, graph):
    apparatus = json.loads((folder / "apparatus.json").read_text(encoding="utf-8"))
    entry = lu_entry(apparatus)
    assert entry["ours"] == LU_ENTRY["ours"], "chant-book reading"
    assert entry["witnesses"] == {"lu": LU_ENTRY["lu"]}, "chant-book reading"
    assert entry["class"] == LU_ENTRY["class"], "chant-book reading"
    assert "p. 849" in entry["ruling"] and "Missal" in entry["ruling"], "chant-book reading"
    note = apparatus["note"]
    assert "The witnesses agree" not in note and "Liber Usualis" in note, "chant-book reading"
    method = doc["editorial"]["source"]["method"]
    assert "Liber Usualis" in method and "w005" in method, "chant-book reading"
    meta, body = load_witness(folder / "lu.txt")
    assert body == "Ascéndit Déus in jubilatióne, Dóminus in vóce túbae, allelúia.", "transcription"
    assert meta["path"] == "printed p. 849 / PDF p. 1037", "transcription"
    errors, _warnings, stats = collate(doc, folder)
    assert errors == [], "collation"
    assert {key: stats[key] for key in LU_STATS} == LU_STATS, "collation"
    witness_id = f"witness.{OFFERTORY}.lu1961"
    (witness,) = [w for w in graph["witnesses"] if w["id"] == witness_id]
    assert witness["coverage"] == {"kind": "full"}, "graph"
    assert witness["review"] == {"status": "pending"}, "graph"
    assert witness["role"] == "approved_corroboration", "graph"
    assert witness.get("source_dependencies") == {"uses": [], "raw_binding": None}, "graph"
    transcript = (folder / "lu.txt").read_text(encoding="utf-8")
    assert witness["transcription_sha256"] == transcript_digest(transcript), "graph"
    (use,) = [u for u in graph["uses"] if u["id"] == witness["use"]]
    assert (use["edition"], use["evidence_sha256"]) == ("edition.liber-usualis.1961", LU_SHA), (
        "graph"
    )
    assert use["locator"] == {"printed": "p. 849", "scan": "PDF p. 1037"}, "graph"
    (collation,) = [c for c in graph["collations"] if c["text"] == OFFERTORY]
    assert witness_id in collation["witnesses"], "graph"
    assert collation["apparatus_sha256"] == digest(apparatus), "graph"
    assert collation["apparatus"] == derived_summary(apparatus), "graph"
    assert collation["selected_text_sha256"] == digest(selected_text(doc)), "graph"
    assert collation["review"] == {"status": "pending"}, "graph"


def test_the_chant_book_omission_is_recorded_with_its_witness():
    assert_lu(core(OFFERTORY), ROOT / "witnesses" / OFFERTORY, load("bibliography/graph.json"))


@pytest.mark.parametrize("damage", ["drop-entry", "class", "reviewed", "inventory", "note", "body"])
def test_the_chant_book_record_rejects_damage(damage, tmp_path):
    folder = tmp_path / OFFERTORY
    shutil.copytree(ROOT / "witnesses" / OFFERTORY, folder)
    path = folder / "apparatus.json"
    apparatus = json.loads(path.read_text(encoding="utf-8"))
    graph = load("bibliography/graph.json")
    (witness,) = [w for w in graph["witnesses"] if w["id"] == f"witness.{OFFERTORY}.lu1961"]
    if damage == "drop-entry":
        apparatus["adjudicated"].remove(lu_entry(apparatus))
        apparatus["summary"] = derived_summary(apparatus)
        expected = "chant-book reading"
    elif damage == "class":
        lu_entry(apparatus)["class"] = "orthography"
        apparatus["summary"] = derived_summary(apparatus)
        expected = "chant-book reading"
    elif damage == "reviewed":
        witness["review"] = {"status": "reviewed"}
        expected = "graph"
    elif damage == "inventory":
        del witness["source_dependencies"]
        expected = "graph"
    elif damage == "note":
        apparatus["note"] = "The witnesses agree on the substantive text."
        expected = "chant-book reading"
    else:
        lu = folder / "lu.txt"
        body = lu.read_text(encoding="utf-8")
        lu.write_text(body.replace("ne, Dóminus", "ne, et Dóminus"), encoding="utf-8")
        expected = "transcription"
    path.write_text(json.dumps(apparatus, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rejects(assert_lu, core(OFFERTORY), folder, graph, message=expected)


REPRINT = f"use.{OFFERTORY}.sunday-after-ascension-reprint.mr1962"
LEAF_428 = "1d20acd1bce0b46b4fecb58142b9373df6ba9184bbe420498d84eaccaa24ab25"


def assert_reprint(graph, apparatus):
    uses = {u["id"]: u for u in graph["uses"]}
    assert REPRINT in uses, "reprint use"
    use = uses[REPRINT]
    assert (use["role"], use["decision"]) == ("direct_approved_print", "RETAIN"), "reprint use"
    assert use["address"] == {"kind": "text", "text": OFFERTORY}, "reprint use"
    assert use["locator"]["printed"] == "p. 347", "reprint use"
    assert use["locator"]["scan"] == "leaf n428 / PDF p. 429", "reprint use"
    assert use["evidence_sha256"] == LEAF_428, "reprint use"
    assert "identical in letters, accents and punctuation" in use["claim"], "reprint use"
    sibling = uses["use.proprium.dominica-post-ascensionem-communio.mr1962"]
    assert sibling["evidence_sha256"] == LEAF_428, "reprint use"
    home = uses[f"use.{OFFERTORY}.mr1962"]
    assert home["locator"]["printed"] == "p. 346", "reprint use"
    assert "p. 347" in apparatus["note"] and "Sunday after the Ascension" in apparatus["note"], (
        "reprint use"
    )


def test_the_shared_offertory_records_its_p347_reprint():
    graph = load("bibliography/graph.json")
    assert_reprint(graph, load(f"witnesses/{OFFERTORY}/apparatus.json"))
    formularies = sorted(
        path.stem
        for path in (ROOT / "formularies").glob("*/*.json")
        if any(c["text"] == OFFERTORY for c in json.loads(path.read_text())["components"])
    )
    assert formularies == ["ascensio-domini", "dominica-post-ascensionem"]


@pytest.mark.parametrize("damage", ["missing", "page", "digest"])
def test_a_missing_or_misbound_reprint_is_rejected(damage):
    graph = load("bibliography/graph.json")
    (use,) = [u for u in graph["uses"] if u["id"] == REPRINT]
    if damage == "missing":
        graph["uses"].remove(use)
    elif damage == "page":
        use["locator"]["printed"] = "p. 346"
    else:
        use["evidence_sha256"] = "7ba3cbda913ef676345c1846e4208928954d88a024d5dd750f48f97327f166bf"
    rejects(
        assert_reprint,
        graph,
        load(f"witnesses/{OFFERTORY}/apparatus.json"),
        message="reprint use",
    )


# --- the Lesson witness header and three accent rulings -------------------------------------------
def assert_lesson_header(transcript, graph):
    lines = transcript.splitlines()
    assert not [x for x in lines if x.startswith("# scope-limit:")], "witness header"
    corrections = [x for x in lines if x.startswith("# correction: 2026-10-20")]
    assert len(corrections) == 1 and "scope-limit line" in corrections[0], "witness header"
    assert "around inquit" in corrections[0] and "leaves n426–n427" in corrections[0], (
        "witness header"
    )
    (body,) = [x for x in lines if x and not x.startswith("#")]
    assert "audístis (inquit) per os meum" in body and "ad óculis" in body, "witness header"
    (witness,) = [w for w in graph["witnesses"] if w["id"] == f"witness.{EPISTLE}.mr1962"]
    assert witness["transcription_sha256"] == transcript_digest(transcript), "witness digest"


def test_the_lesson_witness_retires_its_stale_scope_limit():
    transcript = (ROOT / "witnesses" / EPISTLE / "mr.txt").read_text(encoding="utf-8")
    assert_lesson_header(transcript, load("bibliography/graph.json"))
    errors, _warnings, _stats = collate(core(EPISTLE), ROOT / "witnesses" / EPISTLE)
    assert errors == []


def test_a_restored_scope_limit_or_a_stale_digest_is_rejected():
    transcript = (ROOT / "witnesses" / EPISTLE / "mr.txt").read_text(encoding="utf-8")
    graph = load("bibliography/graph.json")
    stale = transcript.replace(
        "# note: headings",
        "# scope-limit: printed (inquit) is not parenthesized\n# note: headings",
    )
    rejects(assert_lesson_header, stale, graph, message="witness header")
    rejects(assert_lesson_header, transcript + "\n", graph, message="witness digest")


TEMPLATE = "the witness's capital typography is recorded exactly"
RULINGS = {(EPISTLE, "w012"): ("fácere", "facere"), (GOSPEL, "w061"): ("loquéntur", "loquentur")}
RULINGS[(GOSPEL, "w063")] = ("serpéntes", "serpentes")


def assert_ruling(apparatus, wid, ours, plain):
    (entry,) = [e for e in apparatus["adjudicated"] if e["at"] == wid]
    assert entry["witnesses"] == {"do": plain} and entry["ours"] == ours, "accent ruling"
    assert TEMPLATE not in entry["ruling"], "accent ruling"
    assert f"({ours})" in entry["ruling"] and f"unaccented ({plain})" in entry["ruling"], (
        "accent ruling"
    )


@pytest.mark.parametrize("key", sorted(RULINGS), ids=lambda k: f"{k[0].split('-')[-1]}-{k[1]}")
def test_the_accent_ruling_says_what_the_witness_prints(key):
    text, wid = key
    apparatus = load(f"witnesses/{text}/apparatus.json")
    assert_ruling(apparatus, wid, *RULINGS[key])
    (collation,) = [c for c in load("bibliography/graph.json")["collations"] if c["text"] == text]
    assert collation["apparatus_sha256"] == digest(apparatus)
    assert collate(core(text), ROOT / "witnesses" / text)[0] == []


@pytest.mark.parametrize("key", sorted(RULINGS), ids=lambda k: f"{k[0].split('-')[-1]}-{k[1]}")
def test_the_template_ruling_is_rejected(key):
    text, wid = key
    apparatus = load(f"witnesses/{text}/apparatus.json")
    (entry,) = [e for e in apparatus["adjudicated"] if e["at"] == wid]
    entry["ruling"] = (
        "The lexical accent is restored in the working text under the edition's house "
        "convention; the witness's capital typography is recorded exactly."
    )
    rejects(assert_ruling, apparatus, wid, *RULINGS[key], message="accent ruling")


# --- the Polish ulterior card ---------------------------------------------------------------------
CONSUMERS_OF_ULTERIOR = [
    EPISTLE,
    "proprium.sanctae-annae-matris-beatae-mariae-virginis-epistola",
    "proprium.vigilia-pentecostes-communio",
]


def assert_card(entries):
    card = entries["ulterior"]
    assert card == {"senses": ["ostatni", "najdalszy", "dalszy"]}, "card senses"
    assert "kraniec" not in card["senses"], "card senses"


def test_the_adjective_card_lists_adjective_senses_and_the_text_keeps_its_noun():
    assert load("lexicon/lemmata.json")["entries"]["ulterior"]["pos"] == "adj"
    assert_card(load("languages/pl/lexicon.json")["entries"])
    found = {}
    for text in CONSUMERS_OF_ULTERIOR:
        hits = [w for w in words(core(text)).values() if w["lemma"] == "ulterior"]
        assert len(hits) == 1, text
        local = layer("pl", text)
        if text == "proprium.vigilia-pentecostes-communio":
            assert {
                "words": ["w001", "w002", "w003"],
                "anchor": "w003",
                "gloss": "W ostatnim dniu święta",
            } in local["segments"]["s01"]["alignments"]
            assert all("gloss" not in local["words"][wid] for wid in ("w001", "w002", "w003"))
            found[text] = (hits[0]["id"], "W ostatnim dniu święta")
        else:
            found[text] = (hits[0]["id"], local["words"][hits[0]["id"]]["gloss"])
        clean(core(text), layer("pl", text))
    assert found[EPISTLE] == ("w135", "kraniec")
    assert words(core(EPISTLE))["w135"].get("substantive") is True


def test_a_noun_sense_on_the_adjective_card_is_rejected():
    entries = deepcopy(load("languages/pl/lexicon.json")["entries"])
    entries["ulterior"]["senses"].append("kraniec")
    rejects(assert_card, entries, message="card senses")
    assert lint_lemmata({"ulterior": load("lexicon/lemmata.json")["entries"]["ulterior"]}) == []


# --- one reading of Iubiláte in the Introits and chants that sing Ps 65:1-2 and Ps 99:1-2 --------
IUBILATE = {
    I_EPI_ALLELUIA: "w003",
    I_EPI_INTROIT: "w021",
    I_EPI_OFFERTORY: "w001",
    QUINQ_TRACT: "w001",
    II_EPI_INTROIT: "w014",
    "proprium.dominica-ii-post-epiphaniam-offertorium": "w001",
    "proprium.dominica-iii-post-pascha-introitus": "w001",
    "proprium.dominica-iv-post-pascha-offertorium": "w001",
    "proprium.dominica-v-post-pascha-introitus": "w018",
}


def assert_iubilate(text, wid, lay):
    doc = core(text)
    forms = [words(doc)[f"w{int(wid[1:]) + k:03d}"]["form"] for k in range(3)]
    assert forms[:2] == ["Iubiláte", "Deo"] and forms[2] in {"omnis", "univérsa"}, "Latin context"
    assert lay["words"][wid].get("gloss") == "Shout for joy", "Iubilate reading"
    target = lay["segments"]["s01"]["translation"]
    assert "Shout for joy to God" in target and "joyfully" not in target, "Iubilate reading"


@pytest.mark.parametrize("text", sorted(IUBILATE))
def test_iubilate_has_one_reading_in_caption_and_verse(text):
    assert_iubilate(text, IUBILATE[text], layer("en", text))
    assert layer("pl", text)["words"][IUBILATE[text]]["gloss"] == "Wykrzykujcie"


@pytest.mark.parametrize("text", [I_EPI_INTROIT, QUINQ_TRACT, II_EPI_INTROIT])
def test_a_returning_sing_joyfully_is_rejected(text):
    lay = layer("en", text)
    lay["segments"]["s01"]["translation"] = lay["segments"]["s01"]["translation"].replace(
        "Shout for joy to God", "Sing joyfully to God"
    )
    rejects(assert_iubilate, text, IUBILATE[text], lay, message="Iubilate reading")


# The three inherited English sites list the revision in their historical-basis claims.
BASIS_CLAIMS = {
    I_EPI_ALLELUIA: "laity1846",
    I_EPI_INTROIT: "husenbeth1853",
    I_EPI_OFFERTORY: "laity1846",
}


def assert_basis_claim(uses, text):
    use = uses[f"use.en.{text}.body.{BASIS_CLAIMS[text]}"]
    assert use["role"] == "historical_wording_basis", "basis claim"
    head, _, changes = use["claim"].partition(": ")
    assert "revised" in head and "Shout for joy (Iubiláte)" in changes, "basis claim"
    assert "Sing joyfully" not in use["claim"], "basis claim"
    assert use["verified_on"] == "2026-10-20", "basis claim"


@pytest.mark.parametrize("text", sorted(BASIS_CLAIMS))
def test_the_revised_basis_names_the_new_reading(text):
    uses = {u["id"]: u for u in load("languages/en/bibliography.json")["uses"]}
    assert_basis_claim(uses, text)
    assert provenance("en")[f"{text}.s01.en"]["origin"] == "public-domain"
    basis = load("languages/en/translation-basis.json")["records"]
    assert {"texts": [text], "segments": ["s01"], "relationship": "revised"} in basis
    assert check_basis(ROOT)[0] == []


@pytest.mark.parametrize("text", sorted(BASIS_CLAIMS))
def test_a_basis_claim_without_the_revision_is_rejected(text):
    uses = {u["id"]: u for u in load("languages/en/bibliography.json")["uses"]}
    use = uses[f"use.en.{text}.body.{BASIS_CLAIMS[text]}"]
    use["claim"] = (
        use["claim"]
        .replace("Shout for joy (Iubiláte), ", "")
        .replace(" Shout for joy (Iubiláte),", "")
    )
    rejects(assert_basis_claim, uses, text, message="basis claim")


# --- the legacy-register fixture keeps the II Sunday after Epiphany Introit verse bound -----------
LEGACY = "tests/fixtures/english-register-legacy.json"
LEGACY_BEFORE = "4143419f38a7dfe1c096efe3a69d5db247e2140176d406aa4407d6803dbbc782"


def assert_legacy_successor(fixture, verse):
    (record,) = [r for r in fixture["records"] if r["text"] == II_EPI_INTROIT]
    (field,) = [f for f in record["fields"] if f["path"] == ["segments", "s01", "translation"]]
    assert field["sha256"] == hashlib.sha256(verse.encode()).hexdigest(), "legacy field"
    predecessor = verse.replace(
        "Shout for joy to God, all the earth;", "Sing joyfully to God, all the earth;"
    )
    assert predecessor != verse, "legacy field"
    assert hashlib.sha256(predecessor.encode()).hexdigest() == LEGACY_BEFORE, "legacy field"
    assert "Holy Ghost" in verse, "legacy field"


def test_the_legacy_field_successor_binds_exactly_the_reviewed_change():
    verse = layer("en", II_EPI_INTROIT)["segments"]["s01"]["translation"]
    assert_legacy_successor(load(LEGACY), verse)
    assert len(load(LEGACY)["records"]) == 54


@pytest.mark.parametrize("damage", ["other-edit", "stale-hash", "refreshed-other-edit"])
def test_the_legacy_field_successor_rejects_other_changes(damage):
    fixture = load(LEGACY)
    verse = layer("en", II_EPI_INTROIT)["segments"]["s01"]["translation"]
    if damage == "other-edit":
        verse = verse.replace("give glory to His praise", "make His praise glorious")
    elif damage == "stale-hash":
        (record,) = [r for r in fixture["records"] if r["text"] == II_EPI_INTROIT]
        record["fields"][0]["sha256"] = LEGACY_BEFORE
    else:
        verse = verse.replace("give glory to His praise", "make His praise glorious")
        (record,) = [r for r in fixture["records"] if r["text"] == II_EPI_INTROIT]
        record["fields"][0]["sha256"] = hashlib.sha256(verse.encode()).hexdigest()
    rejects(assert_legacy_successor, fixture, verse, message="legacy field")


# --- provenance, protection and every consumer ----------------------------------------------------
CHANGED = {
    "pl": [INTROIT, COLLECT, EPISTLE, ALLELUIA, GOSPEL, OFFERTORY, SECRET, PREFACE, COMMUNION],
    "en": [INTROIT, COLLECT, EPISTLE, ALLELUIA, GOSPEL, OFFERTORY, SECRET, PREFACE, COMMUNION],
}
CHANGED["pl"] += [POSTCOMMUNION, II_EPI_INTROIT]
CHANGED["en"] += [POSTCOMMUNION, II_EPI_INTROIT, I_EPI_ALLELUIA, I_EPI_INTROIT, I_EPI_OFFERTORY]
CHANGED["en"].append(QUINQ_TRACT)


# The Polish Communion verse is held as unsettled working wording since the 2026-10-20 relabel
# (second round); only its caption changes here.
REVIEWED_SITES = {f"{COMMUNION}.s01.pl": ("working-unsettled", "working")}


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
                key = f"{text}.{segment['id']}.{language}"
                site = sites[key]
                assert site["familiar_core"] is expected_protection
                if key in REVIEWED_SITES:
                    assert (site["origin"], site["review"]) == REVIEWED_SITES[key]
                else:
                    assert site["review"] == "working"
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


CONSUMED = [(text, {"ascensio-domini"}) for text in PROPERS if text != OFFERTORY]
CONSUMED += [
    (OFFERTORY, {"ascensio-domini", "dominica-post-ascensionem"}),
    (PREFACE, {"ascensio-domini", "dominica-post-ascensionem"}),
    (II_EPI_INTROIT, {"dominica-ii-post-epiphaniam"}),
    (QUINQ_TRACT, {"dominica-in-quinquagesima"}),
]
CONSUMED += [(text, {"dominica-i-post-epiphaniam"}) for text in (I_EPI_ALLELUIA, I_EPI_INTROIT)]
CONSUMED.append((I_EPI_OFFERTORY, {"dominica-i-post-epiphaniam"}))


@pytest.mark.parametrize("text,expected", CONSUMED, ids=[c[0].split(".")[-1] for c in CONSUMED])
def test_every_consumer_of_a_changed_text_reads_cleanly(text, expected):
    found = consumers(text)
    assert {path.stem for path in found} == expected
    for path in found:
        for component in json.loads(path.read_text(encoding="utf-8"))["components"]:
            body = core(component["text"])
            for language in ("pl", "en"):
                lay = layer(language, component["text"])
                assert interlinear.check(body, lay) == [], (component["text"], language)
                assert check_layer(body, lay, layer_path(language, component["text"])) == []
