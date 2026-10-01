"""Protect Saint Andrew's complete bodies and contextual reading."""

import json
from pathlib import Path

import pytest

from build_reader import bibliography
from checks import interlinear, raw_binding, transcription, translation_provenance
from checks.collate import collate

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "proprium.sancti-andreae-apostoli-"
GROUPS = [
    ("pl", "w035", "w036", "w036", "że staniecie się"),
    ("en", "w004", "w005", "w004", "As Jesus was walking"),
    ("en", "w018", "w019", "w018", "his brother"),
    ("en", "w024", "w025", "w024", "for they were"),
    ("en", "w058", "w059", "w058", "his brother"),
    ("en", "w064", "w065", "w064", "their father"),
    ("en", "w067", "w068", "w067", "their nets"),
]
ACCIDENTALS = [
    ("w004", "Ámbulans", {"mr": "Ambulans", "do": "Ambulans"}, "capital-accent"),
    ("w005", "Iesus", {"do": "Jesus"}, "orthography"),
    ("w006", "iuxta", {"do": "juxta"}, "orthography"),
    ("w019", "eius,", {"do": "ejus,"}, "orthography"),
    ("w024", "(erant", {"do": "erant"}, "punctuation"),
    ("w026", "piscatóres),", {"do": "piscatóres"}, "punctuation"),
    ("w054", "Iacóbum", {"do": "Jacóbum"}, "orthography"),
    ("w055", "Zebedǽi,", {"do": "Zebedæi"}, "accent"),
    ("w057", "Ioánnem", {"do": "Joánnem,"}, "orthography"),
    ("w059", "eius", {"do": "ejus,"}, "orthography"),
    ("w063", "Zebedǽo", {"do": "Zebedæo"}, "accent"),
    ("w065", "eórum,", {"do": "eórum"}, "punctuation"),
    ("w074", "statim", {"do": "statim,"}, "punctuation"),
]


def load(path):
    return json.loads((ROOT / path).read_bytes())


def core(kind):
    return load("texts/" + (PREFIX + kind).replace(".", "/", 1) + ".json")


def layer(language, kind="evangelium"):
    return load(f"languages/{language}/texts/" + (PREFIX + kind).replace(".", "/", 1) + ".json")


@pytest.mark.parametrize("language,first,last,anchor,gloss", GROUPS)
def test_minimal_contextual_groups(language, first, last, anchor, gloss):
    data = layer(language)
    assert {"words": [first, last], "anchor": anchor, "gloss": gloss} in data["segments"]["s01"][
        "alignments"
    ]
    assert all("gloss" not in data["words"][word] for word in (first, last))


@pytest.mark.parametrize(
    "language,word,gloss",
    [
        ("pl", "w014", "jest zwany"),
        ("pl", "w015", "Piotrem"),
        ("pl", "w034", "sprawię"),
        ("en", "w039", "And"),
        ("en", "w040", "they"),
        ("en", "w051", "another"),
        ("en", "w052", "two"),
    ],
)
def test_direct_contextual_readings(language, word, gloss):
    assert layer(language)["words"][word]["gloss"] == gloss


@pytest.mark.parametrize(
    "language,kind,direct,groups",
    [
        ("pl", "evangelium", 75, 3),
        ("pl", "communio", 14, 1),
        ("en", "evangelium", 65, 8),
        ("en", "communio", 14, 1),
    ],
)
def test_complete_provider_coverage_and_retained_perfects(language, kind, direct, groups):
    data = layer(language, kind)
    assert interlinear.check(core(kind), data) == []
    assert sum("gloss" in row for row in data["words"].values()) == direct
    alignments = data["segments"]["s01"]["alignments"]
    assert len(alignments) == groups and all("gloss" in row for row in alignments)
    pairs = [("w044", "w045"), ("w079", "w080")] if kind == "evangelium" else [("w014", "w015")]
    for first, second in pairs:
        assert any(row["words"] == [first, second] for row in alignments)


@pytest.mark.parametrize(
    "kind,section,heading,body,count,page",
    [("evangelium", "Evangelium", 36, 39, 81, 426), ("communio", "Communio", 48, 50, 16, 427)],
)
def test_exact_direct_source_boundary(kind, section, heading, body, count, page):
    directory = ROOT / "witnesses" / (PREFIX + kind)
    bound = raw_binding.resolve_binding(directory / "do.txt", ROOT)
    assert bound is not None
    binding = bound.source["binding"]
    assert binding["references"] == []
    assert binding["evidence"] == [
        {
            "archive": "saint-andrew",
            "first": body,
            "last": body,
            "section": section,
            "section_line": heading,
        }
    ]
    assert binding["reading"] == [{"archive": "saint-andrew", "first": body, "last": body}]
    original = (ROOT / "witnesses/raw/do-Sancti-11-30.txt").read_text().splitlines()[body - 1]
    assert bound.text == " ".join(original.split())
    assert sum(any(c.isalpha() for c in token) for token in bound.text.split()) == count
    transcript = (directory / "do.txt").read_text()
    assert "\n" + original + "\n" in transcript
    if kind == "evangelium":
        assert bound.text.split().count("-") == 2
    assert transcription.check_transcriptions(directory) == ([], 1)
    assert collate(core(kind), directory)[:2] == ([], [])
    for description in (
        core(kind)["editorial"]["notes"],
        core(kind)["editorial"]["source"]["method"],
    ):
        assert "Benziger 1962 Editio iuxta typicam" in description
        assert f"page {page}" in description and f"{count}-word" in description
        assert "no shared conclusion or response expansion" in description


@pytest.mark.parametrize("word,ours,witnesses,kind", ACCIDENTALS)
def test_all_gospel_accidentals(word, ours, witnesses, kind):
    apparatus = load(f"witnesses/{PREFIX}evangelium/apparatus.json")
    assert apparatus["summary"]["entries"] == 13
    rows = {row["at"]: row for row in apparatus["adjudicated"]}
    assert set(rows) == {row[0] for row in ACCIDENTALS}
    assert (rows[word]["ours"], rows[word]["witnesses"], rows[word]["class"]) == (
        ours,
        witnesses,
        kind,
    )


def test_communion_punctuation_and_explicit_lord():
    apparatus = load(f"witnesses/{PREFIX}communio/apparatus.json")
    assert len(apparatus["adjudicated"]) == 1
    row = apparatus["adjudicated"][0]
    assert (row["at"], row["ours"], row["witnesses"], row["class"]) == (
        "w008",
        "hóminum:",
        {"do": "hóminum;"},
        "punctuation",
    )
    assert layer("pl", "communio")["words"]["w016"]["gloss"] == "Panem"
    assert layer("en", "communio")["words"]["w016"]["gloss"] == "the Lord"


@pytest.mark.parametrize("kind", ["evangelium", "communio"])
def test_current_conformity_not_historical_genesis_or_approval(kind):
    graph = load("bibliography/graph.json")
    text = PREFIX + kind
    uses = {row["id"]: row for row in graph["uses"]}
    assert uses[f"use.{text}.mr1962"]["role"] == "direct_approved_print"
    witnesses = {row["transcription"]: row for row in graph["witnesses"] if row["text"] == text}
    assert witnesses["mr"]["source_dependencies"] == {"uses": [], "raw_binding": None}
    assert "checked directly" in witnesses["mr"]["independence_basis"]
    assert "not the original transcription workflow" in witnesses["mr"]["independence_basis"]
    assert witnesses["do"]["source_dependencies"] == {
        "uses": [],
        "raw_binding": "saint-andrew-" + ("gospel" if kind == "evangelium" else "communion"),
    }
    assert all(row["review"] == {"status": "pending"} for row in witnesses.values())
    collation = next(row for row in graph["collations"] if row["text"] == text)
    assert collation["review"] == {"status": "pending"}
    projected = next(
        row for row in bibliography.public_text_evidence(graph)["texts"] if row["id"] == text
    )
    assert projected["witnesses"] == [] and "collation" not in projected


@pytest.mark.parametrize(
    "language,kind,about",
    [
        ("pl", "evangelium", "Ewangelia"),
        ("pl", "communio", "Antyfona na Komunię"),
        ("en", "evangelium", "The Gospel"),
        ("en", "communio", "The Communion antiphon"),
    ],
)
def test_localized_about_and_exact_working_provenance(language, kind, about):
    data = layer(language, kind)
    assert data["about"].startswith(about)
    row = next(
        row
        for row in load(f"languages/{language}/translation-provenance.json")["sites"]
        if row["site"] == PREFIX + kind + ".s01." + language
    )
    assert (row["origin"], row["review"], row["familiar_core"]) == (
        "working-unsettled",
        "working",
        False,
    )
    assert row["target_sha256"] == translation_provenance.canonical_hash(
        data["segments"]["s01"]["translation"]
    )
    assert row["source_sha256"] == translation_provenance.canonical_hash(
        translation_provenance.source_payload(core(kind)["segments"][0])
    )


def test_only_scoped_divine_pronoun_casing_in_prose():
    assert "Come after Me," in layer("en")["segments"]["s01"]["translation"]
    assert "za Mną:" in layer("pl", "communio")["segments"]["s01"]["translation"]
