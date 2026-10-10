"""Contextual connective readings, not a universal prohibition of English but."""

from pathlib import Path

import pytest

from build_reader import store
from checks import interlinear

ROOT = Path(__file__).resolve().parents[1]
DIRECT = [
    ("ordinarium.lavabo", "s07", "w054"),
    ("proprium.ascensio-domini-epistola", "s01", "w073"),
    ("proprium.dominica-i-passionis-evangelium", "s01", "w071"),
    ("proprium.dominica-i-passionis-evangelium", "s01", "w166"),
    ("proprium.dominica-ii-passionis-tractus", "s01", "w032"),
    ("proprium.dominica-ii-passionis-tractus", "s01", "w062"),
    ("proprium.dominica-ii-post-epiphaniam-evangelium", "s01", "w137"),
    ("proprium.dominica-iii-in-quadragesima-evangelium", "s01", "w044"),
    ("proprium.dominica-iii-post-pascha-evangelium", "s01", "w105"),
    ("proprium.dominica-in-albis-evangelium", "s01", "w105"),
    ("proprium.dominica-ix-post-pentecosten-evangelium", "s01", "w103"),
    ("proprium.dominica-xii-post-pentecosten-evangelium", "s01", "w105"),
    ("proprium.nativitas-domini-in-die-epistola", "s01", "w162"),
    ("proprium.nativitas-domini-in-die-epistola", "s01", "w177"),
    ("proprium.sancti-iacobi-apostoli-epistola", "s01", "w026"),
    ("proprium.sancti-iacobi-apostoli-epistola", "s01", "w033"),
    ("proprium.sancti-iacobi-apostoli-epistola", "s01", "w038"),
    ("proprium.sancti-laurentii-martyris-evangelium", "s01", "w024"),
    ("proprium.sancti-petri-et-pauli-apostolorum-evangelium", "s01", "w041"),
    ("proprium.sancti-thomae-apostoli-evangelium", "s01", "w026"),
    ("proprium.vigilia-pentecostes-evangelium", "s01", "w043"),
    ("proprium.vigilia-pentecostes-evangelium", "s01", "w070"),
]
GROUPS = [
    ("proprium.ascensio-domini-evangelium", "s01", ["w097", "w098"]),
    ("proprium.dominica-in-septuagesima-evangelium", "s01", ["w064", "w065"]),
]


@pytest.mark.parametrize("text,sid,wid", DIRECT)
def test_reviewed_postpositive_contrast(text, sid, wid):
    doc, layers = store.load(ROOT, text)
    en = layers["en"]
    word = next(w for s in doc["segments"] if s["id"] == sid for w in s["words"] if w["id"] == wid)
    assert word["lemma"] == "autem"
    assert en["words"][wid]["gloss"] == "however"
    assert all(wid not in g["words"] for g in en["segments"][sid].get("alignments", []))
    assert not interlinear.check(doc, en)


@pytest.mark.parametrize("text,sid,ids", GROUPS)
def test_narrative_subject_and_connective(text, sid, ids):
    doc, layers = store.load(ROOT, text)
    en = layers["en"]
    segment = next(s for s in doc["segments"] if s["id"] == sid)
    words = segment["words"]
    positions = [next(i for i, w in enumerate(words) if w["id"] == wid) for wid in ids]
    assert positions[1] == positions[0] + 1
    assert [words[i]["lemma"] for i in positions] == ["ille", "autem"]
    groups = [g for g in en["segments"][sid].get("alignments", []) if set(g["words"]) & set(ids)]
    assert groups == [{"words": ids, "anchor": ids[0], "gloss": "And they"}]
    assert all("gloss" not in en["words"][wid] for wid in ids)
    assert not interlinear.check(doc, en)


def verify_septuagesima_crown_contrast(doc, en):
    ids = ["w037", "w038", "w039"]
    segment = next(s for s in doc["segments"] if s["id"] == "s01")
    assert [w["lemma"] for w in segment["words"] if w["id"] in ids] == [
        "nos",
        "autem",
        "incorruptus",
    ]
    selected = [
        g for g in en["segments"]["s01"].get("alignments", []) if set(g["words"]) & set(ids)
    ]
    assert selected == [
        {"words": ids, "anchor": "w039", "gloss": "but we do so to receive an imperishable one"}
    ]
    assert all("gloss" not in en["words"][wid] for wid in ids)
    assert not interlinear.check(doc, en)


def test_septuagesima_crown_purpose_keeps_its_contrast():
    doc, layers = store.load(ROOT, "proprium.dominica-in-septuagesima-epistola")
    verify_septuagesima_crown_contrast(doc, layers["en"])


@pytest.mark.parametrize("damage", ["meaning", "anchor", "member", "duplicate"])
def test_septuagesima_crown_contrast_controls(damage):
    from copy import deepcopy

    doc, layers = store.load(ROOT, "proprium.dominica-in-septuagesima-epistola")
    target = layers["en"]
    verify_septuagesima_crown_contrast(doc, target)
    bad = deepcopy(target)
    group = next(g for g in bad["segments"]["s01"]["alignments"] if "w038" in g["words"])
    if damage == "meaning":
        group["gloss"] = "and they receive a perishable crown"
    elif damage == "anchor":
        group["anchor"] = "w037"
    elif damage == "member":
        group["words"].remove("w038")
    else:
        bad["segments"]["s01"]["alignments"].append(deepcopy(group))
    with pytest.raises(AssertionError):
        verify_septuagesima_crown_contrast(doc, bad)
    verify_septuagesima_crown_contrast(doc, target)


def verify_quinquagesima_created_people_contrast(doc, en):
    ids = ["w028", "w029", "w030", "w031"]
    segment = next(s for s in doc["segments"] if s["id"] == "s01")
    assert [w["lemma"] for w in segment["words"] if w["id"] in ids] == [
        "nos",
        "autem",
        "populus",
        "is",
    ]
    selected = [
        g for g in en["segments"]["s01"].get("alignments", []) if set(g["words"]) & set(ids)
    ]
    assert selected == [{"words": ids, "anchor": "w028", "gloss": "but we are His people"}]
    assert all("gloss" not in en["words"][wid] for wid in ids)
    assert not interlinear.check(doc, en)


def test_quinquagesima_created_people_keep_their_contrast():
    doc, layers = store.load(ROOT, "proprium.dominica-in-quinquagesima-tractus")
    verify_quinquagesima_created_people_contrast(doc, layers["en"])


@pytest.mark.parametrize("damage", ["meaning", "anchor", "member", "duplicate"])
def test_quinquagesima_created_people_contrast_controls(damage):
    from copy import deepcopy

    doc, layers = store.load(ROOT, "proprium.dominica-in-quinquagesima-tractus")
    target = layers["en"]
    verify_quinquagesima_created_people_contrast(doc, target)
    bad = deepcopy(target)
    group = next(g for g in bad["segments"]["s01"]["alignments"] if "w029" in g["words"])
    if damage == "meaning":
        group["gloss"] = "and we made ourselves"
    elif damage == "anchor":
        group["anchor"] = "w029"
    elif damage == "member":
        group["words"].remove("w029")
    else:
        bad["segments"]["s01"]["alignments"].append(deepcopy(group))
    with pytest.raises(AssertionError):
        verify_quinquagesima_created_people_contrast(doc, bad)
    verify_quinquagesima_created_people_contrast(doc, target)
