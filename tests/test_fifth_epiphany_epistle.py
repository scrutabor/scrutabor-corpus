"""Colossians 3 keeps clothing, human subjects and complete source readings."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.bibliography_bindings import digest, selected_text, transcript_digest
from build_reader.emit import Table, core_artifact, expand, language_artifact
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear
from checks.raw_binding import resolve_binding
from checks.transcription import check_transcriptions
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
NAME = "dominica-v-post-epiphaniam-epistola"
TEXT = f"proprium.{NAME}"
GROUPS = [
    ("pl", ["w010", "w011"], "w010", "w serdeczne miłosierdzie"),
    ("en", ["w052", "w053"], "w053", "in which peace"),
    ("en", ["w055", "w056"], "w055", "you were called"),
    ("en", ["w088", "w089"], "w089", "Whatever"),
    ("en", ["w102", "w103"], "w103", "giving thanks"),
]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def layer(language):
    return load(f"languages/{language}/texts/proprium/{NAME}.json")


@pytest.mark.parametrize("language,ids,anchor,gloss", GROUPS)
def test_minimal_constructions_have_one_provider(language, ids, anchor, gloss):
    core = load(f"texts/proprium/{NAME}.json")
    data = layer(language)
    assert {"words": ids, "anchor": anchor, "gloss": gloss} in data["segments"]["s01"]["alignments"]
    assert all(data["words"][wid] == {} for wid in ids)
    assert interlinear.check(expand_core(core), enrich_layer(core, data)) == []
    for wid in ids:
        duplicate = deepcopy(data)
        duplicate["words"][wid]["gloss"] = "duplicate"
        assert interlinear.check(expand_core(core), enrich_layer(core, duplicate))
        missing = deepcopy(data)
        group = next(g for g in missing["segments"]["s01"]["alignments"] if wid in g["words"])
        group["words"].remove(wid)
        assert interlinear.check(expand_core(core), enrich_layer(core, missing))


@pytest.mark.parametrize("language,direct", [("pl", 100), ("en", 78)])
def test_all_111_words_and_construction_notes_reach_reader(language, direct):
    core, data = load(f"texts/proprium/{NAME}.json"), layer(language)
    doc, gloss = expand_core(core), enrich_layer(core, data)
    p, a, s, local = Table(), Table(), Table(), Table()
    neutral = core_artifact(doc, core, p, a, s)
    localized = language_artifact(doc, gloss, local)
    decoded, target = expand(neutral, localized, p.order, a.order, s.order, local.order)
    assert decoded["segments"][0]["words"] == doc["segments"][0]["words"]
    assert len(decoded["segments"][0]["words"]) == len(data["words"]) == 111
    assert sum("gloss" in w for w in data["words"].values()) == direct
    assert target["segments"]["s01"] == gloss["segments"]["s01"]
    for wid, reference in [("w072", "(w063)"), ("w074", "(w072)"), ("w083", "(w072)")]:
        assert target["words"][wid]["explanation"] == data["words"][wid]["explanation"]
        assert reference in target["words"][wid]["explanation"]
    assert (decoded["segments"][0]["speaker"], decoded["segments"][0]["voice"]) == (
        "sacerdos",
        "clara",
    )


def test_english_clothing_jussive_and_human_subject():
    data = layer("en")
    for wid, value in {
        "w002": "Clothe",
        "w003": "yourselves",
        "w010": "with a heart",
        "w011": "of mercy",
    }.items():
        assert data["words"][wid]["gloss"] == value
    assert {
        "words": ["w063", "w064", "w065"],
        "anchor": "w065",
        "gloss": "May Christ’s word dwell",
    } in data["segments"]["s01"]["alignments"]
    assert all("gloss" not in data["words"][wid] for wid in ("w063", "w064", "w065"))
    assert "as you teach and admonish one another" in data["segments"]["s01"]["translation"]
    assert data["about"].startswith("The Epistle")
    assert layer("pl")["about"].startswith("Epistoła")


@pytest.mark.parametrize("wid,gender", [("w024", "m"), ("w038", "n"), ("w089", "n")])
def test_explicit_gender_is_pending_not_inherited_approval(wid, gender):
    core = load(f"texts/proprium/{NAME}.json")
    doc = expand_core(core)
    word = next(w for w in doc["segments"][0]["words"] if w["id"] == wid)
    assert word["morph"]["gender"] == gender
    assert word["analysis"] == {
        "confidence": "high",
        "sources": ["editorial", "whitakers", "collatinus"],
        "review": "pending",
    }
    absent = deepcopy(core)
    del absent["editorial"]["words"][wid]
    decoded = expand_core(absent)
    no_override = next(w for w in decoded["segments"][0]["words"] if w["id"] == wid)
    assert "analysis" not in no_override
    assert decoded["analysis_defaults_words"]["review"] == "accepted"


@pytest.mark.parametrize("language", ["pl", "en"])
def test_current_provenance_remains_working(language):
    core = load(f"texts/proprium/{NAME}.json")
    site = next(
        s
        for s in load(f"languages/{language}/translation-provenance.json")["sites"]
        if s["site"] == f"{TEXT}.s01.{language}"
    )
    assert site["source_sha256"] == canonical_hash(source_payload(core["segments"][0]))
    assert site["target_sha256"] == canonical_hash(
        layer(language)["segments"]["s01"]["translation"]
    )
    assert (site["origin"], site["review"], site["familiar_core"]) == (
        "working-unsettled",
        "working",
        False,
    )


def test_complete_inherited_reading_and_declared_ending():
    core = load(f"texts/proprium/{NAME}.json")
    assert (
        digest(selected_text(core))
        == "e2dc3ac1ddd55d4aa06620c8d8a9126e867f2eae283f7761c810ee66e20622d6"
    )
    directory = ROOT / f"witnesses/{TEXT}"
    bound = resolve_binding(directory / "do.txt", ROOT)
    assert bound is not None and len(bound.text.split()) == 108
    assert bound.text.endswith("per ipsum.") and "Dómini Jesu Christi" in bound.text
    binding = bound.source["binding"]
    assert binding["reading"] == [{"archive": "holy-family", "first": 35, "last": 35}]
    assert binding["references"] == [
        {"archive": "epiphany-v", "line": 20, "text": "@Tempora/Epi1-0", "target": 1}
    ]
    assert check_transcriptions(directory) == ([], 1)
    apparatus = load(f"witnesses/{TEXT}/apparatus.json")
    assert len(apparatus["adjudicated"]) == 8
    ending = next(a for a in apparatus["adjudicated"] if a["class"] == "substantive-span")
    assert (
        ending["at"],
        ending["through"],
        ending["ours"],
        ending["witnesses"]["do"],
    ) == ("w108", "w111", "Iesum Christum Dóminum nostrum.", "ipsum.")
    graph = load("bibliography/graph.json")
    witnesses = [w for w in graph["witnesses"] if w["text"] == TEXT]
    assert len(witnesses) == 2
    for witness in witnesses:
        name = witness["transcription"]
        assert witness["transcription_sha256"] == transcript_digest(
            (directory / f"{name}.txt").read_text()
        )
        assert witness["review"] == {"status": "pending"}
        assert witness["source_dependencies"] == {
            "uses": [],
            "raw_binding": "epiphany-v-epistle" if name == "do" else None,
        }
    collation = next(c for c in graph["collations"] if c["text"] == TEXT)
    assert collation["review"] == {"status": "pending"}
    assert collation["apparatus_sha256"] == digest(apparatus)
