"""Quinquagesima constructions retain participants, predicates and source limits."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from checks import interlinear
from checks.language_packs import check_layer

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "proprium.dominica-in-quinquagesima-"
GROUPS = [
    ("introitus", "pl", 26, 28, 26, "będziesz mi przewodnikiem"),
    ("introitus", "en", 15, 21, 15, "You are my support and my refuge"),
    ("introitus", "en", 63, 66, 63, "and forever and ever"),
    ("collecta", "pl", 12, 16, 12, "strzeż nas od wszelkiej przeciwności"),
    (
        "collecta",
        "en",
        8,
        16,
        8,
        "guard us, released from the bonds of sins, from all adversity",
    ),
    ("epistola", "pl", 8, 11, 8, "a nie miał miłości"),
    ("epistola", "en", 83, 85, 83, "does not seek prestige"),
    ("epistola", "en", 86, 90, 86, "does not seek its own interests"),
    ("epistola", "en", 93, 95, 93, "does not harbor evil thoughts"),
    (
        "epistola",
        "en",
        114,
        116,
        114,
        "if there are prophecies, they will be made void",
    ),
    ("epistola", "en", 117, 119, 117, "if there are tongues, they will cease"),
    ("epistola", "en", 120, 122, 120, "if there is knowledge, it will be destroyed"),
    ("epistola", "en", 131, 136, 131, "But when what is perfect comes"),
    ("epistola", "en", 137, 141, 137, "what is partial will be done away"),
    ("epistola", "en", 187, 190, 187, "faith, hope and love remain"),
    ("epistola", "en", 193, 197, 193, "but the greatest of these is love"),
    ("graduale", "en", 8, 13, 8, "You have made Your power known among the nations"),
    ("tractus", "pl", 28, 31, 28, "my zaś jesteśmy Jego ludem"),
    ("tractus", "en", 24, 27, 24, "and we did not make ourselves"),
    ("tractus", "en", 28, 31, 28, "but we are His people"),
    ("evangelium", "pl", 15, 18, 15, "wszystko, co zostało napisane"),
    ("evangelium", "pl", 126, 128, 126, "chcesz, abym ci uczynił"),
    ("evangelium", "en", 65, 66, 65, "that a certain blind man"),
    ("evangelium", "en", 111, 114, 111, "And Jesus stood still and commanded"),
    ("evangelium", "en", 142, 144, 142, "has made you well"),
    ("offertorium", "en", 1, 2, 1, "Blessed are You"),
    ("communio", "pl", 7, 11, 7, "Pan spełnił im ich pragnienie"),
    ("communio", "en", 7, 11, 7, "the Lord granted them their desire"),
    ("postcommunio", "pl", 4, 8, 4, "abyśmy, przyjąwszy niebieskie pokarmy,"),
    ("postcommunio", "en", 5, 8, 5, "we who have received heavenly food"),
    ("postcommunio", "en", 9, 10, 9, "through it"),
    ("postcommunio", "en", 11, 14, 11, "may be protected against all adversity"),
]
FEATURES = [
    ("epistola", "w005", {"mood": "subj", "tense": "pres"}, "medium"),
    ("epistola", "w133", {"mood": "ind", "tense": "futperf"}, "medium"),
    ("evangelium", "w035", {"mood": "ind", "tense": "futperf"}, "medium"),
    ("tractus", "w027", {"case": "acc"}, "medium"),
    ("epistola", "w195", {"gender": "n"}, "high"),
    ("evangelium", "w045", {"gender": "n"}, "high"),
    ("evangelium", "w050", {"gender": "n"}, "high"),
    ("evangelium", "w053", {"gender": "m"}, "high"),
    ("evangelium", "w066", {"gender": "m"}, "high"),
    ("communio", "w010", {"gender": "m"}, "high"),
]


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def documents(slug, language):
    relative = f"texts/proprium/dominica-in-quinquagesima-{slug}.json"
    return load(relative), load(f"languages/{language}/{relative}")


def exact_group(layer, lo, hi, anchor, caption):
    ids = [f"w{n:03d}" for n in range(lo, hi + 1)]
    groups = [
        g
        for s in layer["segments"].values()
        for g in s.get("alignments", [])
        if set(g["words"]) & set(ids)
    ]
    assert groups == [{"words": ids, "anchor": f"w{anchor:03d}", "gloss": caption}]
    assert all("gloss" not in layer["words"][wid] for wid in ids)


@pytest.mark.parametrize("slug,language,lo,hi,anchor,caption", GROUPS)
def test_complete_construction_has_one_exact_provider(slug, language, lo, hi, anchor, caption):
    core, layer = documents(slug, language)
    exact_group(layer, lo, hi, anchor, caption)
    assert interlinear.check(core, layer) == []
    path = ROOT / f"languages/{language}/texts/proprium/dominica-in-quinquagesima-{slug}.json"
    assert check_layer(core, layer, path) == []
    for n in range(lo, hi + 1):
        duplicate = deepcopy(layer)
        duplicate["words"][f"w{n:03d}"]["gloss"] = "duplicate"
        assert interlinear.check(core, duplicate)


@pytest.mark.parametrize("slug,wid,fields,confidence", FEATURES)
def test_local_parse_and_uncertainty_are_not_new_acceptance(slug, wid, fields, confidence):
    core, _ = documents(slug, "en")
    word = next(w for s in core["segments"] for w in s["words"] if w["id"] == wid)
    assert all(word["morph"].get(k) == v for k, v in fields.items())
    ed = core["editorial"]
    analysis = ed["words"][wid]["analysis"]
    assert analysis == {
        "sources": ["editorial", "whitakers", "collatinus"],
        "confidence": confidence,
        "review": "pending",
    }


@pytest.mark.parametrize(
    "slug,wid",
    [
        ("epistola", "w005"),
        ("epistola", "w022"),
        ("epistola", "w133"),
        ("tractus", "w027"),
        ("evangelium", "w035"),
    ],
)
def test_bilingual_grammar_notes_have_neutral_topology(slug, wid):
    core, pl = documents(slug, "pl")
    _, en = documents(slug, "en")
    assert core["localization"]["explanations"][wid] == {}
    for language, layer in [("pl", pl), ("en", en)]:
        note = layer["words"][wid]["explanation"]
        assert note.strip()
        path = ROOT / f"languages/{language}/texts/proprium/dominica-in-quinquagesima-{slug}.json"
        assert check_layer(core, layer, path) == []


@pytest.mark.parametrize(
    "slug,first",
    [
        ("introitus", "Printed p. 54 supplies"),
        ("collecta", "Printed p. 54 supplies"),
        ("postcommunio", "Printed p. 55 supplies"),
    ],
)
def test_composite_witness_does_not_claim_one_complete_proper_page(slug, first):
    tid = PREFIX + slug
    graph = load("bibliography/graph.json")
    use = next(r for r in graph["uses"] if r["id"] == f"use.{tid}.mr1962")
    assert use["claim"].startswith(first)
    assert "cue" in use["claim"]
    assert "suppl" in use["claim"] or "comes from" in use["claim"]
    witness = next(r for r in graph["witnesses"] if r["id"] == f"witness.{tid}.mr1962")
    assert witness["orthography_profile"] == "printed-body-composite-expansion"
    assert witness["review"] == {"status": "pending"}
    assert witness["source_dependencies"]["uses"]
    raw = (ROOT / f"witnesses/{tid}/mr.txt").read_text(encoding="utf-8")
    assert "# coverage: " + use["claim"] in raw
    assert "# orthography: exact printed" not in raw
    digital = next(r for r in graph["uses"] if r["id"] == f"use.{tid}.do44667ff")
    assert (
        digital["evidence_sha256"]
        == "089dedaf240816aaba4ba9bf1714f384aea26c4ec36ff982688c7bbf7de9ffe8"
    )
    assert "Prayers.txt" in digital["locator"]["section"]


def test_communion_declares_digital_corrigendum_without_rewriting_it():
    tid = PREFIX + "communio"
    raw = (ROOT / f"witnesses/{tid}/do.txt").read_text(encoding="utf-8")
    assert "saturári" in raw and "# corrigendum:" in raw
    core, _ = documents("communio", "en")
    assert core["segments"][0]["words"][2]["form"] == "saturáti"
    assert core["segments"][0]["words"][2]["morph"]["mood"] == "part"
    app = load(f"witnesses/{tid}/apparatus.json")
    assert "saturári" in app["note"] and "corrigendum" in app["note"]
    assert app["adjudicated"] == []
    graph = load("bibliography/graph.json")
    use = next(r for r in graph["uses"] if r["id"] == f"use.{tid}.do44667ff")
    assert "saturári" in use["claim"] and "letter error" in use["claim"]


@pytest.mark.parametrize("slug", ["collecta", "postcommunio"])
def test_response_comparator_does_not_claim_a_proper_response_marker(slug):
    graph = load("bibliography/graph.json")
    tid = PREFIX + slug
    use = next(r for r in graph["uses"] if r["id"] == f"use.{tid}.prayer-response.lu1961")
    assert use["edition"] == "edition.liber-usualis.1961"
    assert "not the controlling 1962" in use["claim"]
    assert "proper page does not print" in use["claim"]
    witness = next(r for r in graph["witnesses"] if r["id"] == f"witness.{tid}.mr1962")
    assert use["id"] not in witness["source_dependencies"]["uses"]
