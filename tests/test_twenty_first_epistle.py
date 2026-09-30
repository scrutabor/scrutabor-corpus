"""Ephesians 6 preserves negative possession, clothing and complete witnesses."""

import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.bibliography_bindings import digest, selected_text, transcript_digest
from build_reader.emit import Table, core_artifact, expand, language_artifact
from build_reader.layers import enrich_layer, expand_core
from checks import attribute, interlinear
from checks.language_packs import check_layer
from checks.raw_binding import resolve_binding
from checks.transcription import check_transcriptions
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
NAME = "dominica-xxi-post-pentecosten-epistola"
TEXT = f"proprium.{NAME}"
RAW = "witnesses/raw/do-44667ff/missa/Latin/Tempora/Pent21-0.txt"
GROUPS = [
    ("pl", ["w021", "w022", "w023", "w024"], "w024", "nie toczymy walki"),
    ("pl", ["w064", "w065"], "w065", "prawdą"),
    ("pl", ["w082", "w083"], "w083", "którą"),
    ("en", ["w021", "w022", "w023", "w024"], "w024", "our struggle is not"),
]
VARIANTS = {
    "w004": ("Dómino,", "Dómino"),
    "w009": ("eius.", "ejus."),
    "w015": ("possítis", "póssitis"),
    "w031": ("príncipes,", "príncipes"),
    "w043": ("cæléstibus.", "cœléstibus."),
    "w049": ("possítis", "póssitis"),
    "w053": ("malo,", "malo"),
    "w069": ("iustítiæ,", "justítiæ,"),
    "w084": ("possítis", "póssitis"),
}


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def layer(language):
    return load(f"languages/{language}/texts/proprium/{NAME}.json")


@pytest.mark.parametrize("language,ids,anchor,gloss", GROUPS)
def test_reviewed_predicate_has_one_provider(language, ids, anchor, gloss):
    data = layer(language)
    assert {"words": ids, "anchor": anchor, "gloss": gloss} in data["segments"]["s01"]["alignments"]
    assert all(data["words"][wid] == {} for wid in ids)


@pytest.mark.parametrize("language,members,direct", [("pl", 8, 92), ("en", 4, 96)])
def test_all_100_tokens_remain_present(language, members, direct):
    core = load(f"texts/proprium/{NAME}.json")
    data = layer(language)
    ids = [w["id"] for w in core["segments"][0]["words"]]
    assert ids == [f"w{n:03}" for n in range(1, 101)]
    assert set(ids) == set(data["words"])
    groups = data["segments"]["s01"]["alignments"]
    assert sum(len(g["words"]) for g in groups) == members
    assert all("gloss" in g and "reason" not in g for g in groups)
    assert sum("gloss" in w for w in data["words"].values()) == direct
    assert interlinear.check(expand_core(core), enrich_layer(core, data)) == []
    assert check_layer(core, data, ROOT / f"languages/{language}/texts/proprium/{NAME}.json") == []


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("wid", ["w021", "w022", "w023", "w024"])
def test_missing_or_duplicate_negative_predicate_member_is_rejected(language, wid):
    core = load(f"texts/proprium/{NAME}.json")
    data = layer(language)
    missing = deepcopy(data)
    missing["segments"]["s01"]["alignments"][0]["words"].remove(wid)
    assert interlinear.check(expand_core(core), enrich_layer(core, missing))
    duplicate = deepcopy(data)
    duplicate["words"][wid]["gloss"] = "duplicate"
    assert interlinear.check(expand_core(core), enrich_layer(core, duplicate))


def test_polish_personal_perfection_and_instrumental_shield():
    data = layer("pl")
    assert data["about"].startswith("Epistoła formularza")
    assert data["words"]["w057"]["gloss"] == "doskonali"
    assert data["words"]["w067"]["gloss"] == "przywdziawszy"
    assert data["words"]["w077"]["gloss"] == "we"
    assert data["words"]["w078"]["gloss"] == "wszystkim"
    assert data["words"]["w084"]["gloss"] == "moglibyście"
    prose = data["segments"]["s01"]["translation"]
    assert "i ostać się, doskonali we wszystkim" in prose
    assert "abyście nią mogli ugasić" in prose


def test_english_clothing_and_personal_perfection():
    data = layer("en")
    assert data["about"].startswith("The Epistle")
    assert data["words"]["w010"]["gloss"] == "Clothe"
    assert data["words"]["w011"]["gloss"] == "yourselves"
    assert data["words"]["w012"]["gloss"] == "with armor"
    assert data["words"]["w057"]["gloss"] == "perfect"
    assert "the rulers of this world of darkness" in data["segments"]["s01"]["translation"]


def reader_analysis(core, wid):
    doc = expand_core(core)
    data = enrich_layer(core, layer("en"))
    parses, analyses, shared, local = Table(), Table(), Table(), Table()
    neutral = core_artifact(doc, core, parses, analyses, shared)
    localized = language_artifact(doc, data, local)
    decoded, _ = expand(neutral, localized, parses.order, analyses.order, shared.order, local.order)
    word = next(w for w in decoded["segments"][0]["words"] if w["id"] == wid)
    state = (
        word.get("analysis")
        or decoded.get("analysis_defaults_words")
        or decoded.get("analysis_defaults")
    )
    return word, state


def test_relative_gender_does_not_inherit_old_approval():
    core = load(f"texts/proprium/{NAME}.json")
    word, state = reader_analysis(core, "w083")
    assert word["morph"]["gender"] == "n"
    assert state == {
        "confidence": "high",
        "sources": ["editorial", "whitakers", "collatinus"],
        "review": "pending",
    }
    other, other_state = reader_analysis(core, "w097")
    assert other["morph"]["gender"] == "n"
    assert other_state["review"] == "pending"
    missing = deepcopy(core)
    del missing["editorial"]["words"]["w083"]
    assert reader_analysis(missing, "w083")[1]["review"] == "accepted"


@pytest.mark.parametrize("language", ["pl", "en"])
def test_current_provenance_without_new_approval(language):
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


def test_selected_latin_and_all_witness_variants():
    core = load(f"texts/proprium/{NAME}.json")
    assert (
        digest(selected_text(core))
        == "b117dd2bd7bbf26afaade90a98576b24550b6a3c8efdbca32e28e9af3275da17"
    )
    selected = [
        w.get("pre", "") + w["form"] + w.get("post", "") for w in core["segments"][0]["words"]
    ]
    path = ROOT / f"witnesses/{TEXT}/do.txt"
    bound = resolve_binding(path, ROOT)
    assert bound is not None
    digital = bound.text.split()
    assert len(digital) == len(selected) == 100
    assert {
        f"w{n:03}": (a, b)
        for n, (a, b) in enumerate(zip(selected, digital, strict=True), 1)
        if a != b
    } == VARIANTS
    apparatus = load(f"witnesses/{TEXT}/apparatus.json")
    assert len(apparatus["adjudicated"]) == 10
    assert {
        a["at"]: (a["ours"], a["witnesses"]["do"])
        for a in apparatus["adjudicated"]
        if "do" in a["witnesses"]
    } == VARIANTS
    mr = (path.parent / "mr.txt").read_text(encoding="utf-8")
    body = next(line for line in mr.splitlines() if line.startswith("Fratres:")).split()
    assert {
        f"w{n:03}": (a, b) for n, (a, b) in enumerate(zip(selected, body, strict=True), 1) if a != b
    } == {"w085": ("ómnia", "ómnis")}
    assert check_transcriptions(path.parent) == ([], 1)
    assert bound.source["binding"]["reading"] == [
        {"archive": "pentecost-xxi", "first": 28, "last": 28}
    ]
    assert bound.source["binding"]["references"] == []


def test_two_page_dependency_and_pending_subjects():
    graph = load("bibliography/graph.json")
    continuation = f"use.{TEXT}.body-continuation.mr1962"
    uses = [u for u in graph["uses"] if u["address"].get("text") == TEXT]
    assert len(uses) == 3
    image_use = next(u for u in uses if u["id"] == continuation)
    assert (
        image_use["evidence_sha256"]
        == "aef571577f959c0315070218b1e8ded22a3abf2f0002c07b6df0bc9f94c7c693"
    )
    witnesses = [w for w in graph["witnesses"] if w["text"] == TEXT]
    assert len(witnesses) == 2
    for witness in witnesses:
        transcription = witness["transcription"]
        assert witness["review"] == {"status": "pending"}
        assert witness["source_dependencies"] == {
            "uses": [continuation] if transcription == "mr" else [],
            "raw_binding": "pentecost-xxi-epistle" if transcription == "do" else None,
        }
        assert witness["transcription_sha256"] == transcript_digest(
            (ROOT / f"witnesses/{TEXT}/{transcription}.txt").read_text()
        )
    collation = next(c for c in graph["collations"] if c["text"] == TEXT)
    assert collation["review"] == {"status": "pending"}
    assert collation["apparatus_sha256"] == digest(load(f"witnesses/{TEXT}/apparatus.json"))


def test_new_archive_is_not_discovered_as_a_legacy_source(tmp_path, monkeypatch):
    archive = load("witnesses/raw/bindings.json")["archives"]["pentecost-xxi"]
    assert archive["path"] == RAW
    destination = tmp_path / RAW
    destination.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / RAW, destination)
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    assert attribute._raw_archive_for(archive["upstream"]) is None
    assert attribute.marked_lines("proprium.unbound-control") == []
    top_level = tmp_path / "witnesses/raw/do-Tempora-Pent21-0.txt"
    shutil.copyfile(destination, top_level)
    assert attribute._raw_archive_for(archive["upstream"]) == top_level
    assert attribute.marked_lines("proprium.unbound-control")
