"""The proper-page citations distinguish print from supplied common text."""

from pathlib import Path

import pytest

from build_reader import bibliography

ROOT = Path(__file__).resolve().parents[1]
INTROIT_CLAIM = (
    "The cited page prints the proper antiphon and psalm verse of this Introit, "
    "with cues for the common doxology and antiphon reprise. It does not print "
    "those expansions in full. The reader supplies them with its own "
    "accentuation, capitalization and punctuation."
)
ORATION_CLAIM = (
    "The cited page prints this prayer’s proper body and the abbreviated "
    "conclusion “Per Dóminum”. The full common conclusion and Amen are supplied "
    "separately in the reader, with its own accentuation, capitalization and "
    "punctuation."
)


@pytest.fixture(scope="module")
def sources():
    graph, _ = bibliography.load(ROOT)
    evidence = bibliography.public_text_evidence(graph)
    return graph, {record["id"]: record for record in evidence["texts"]}


@pytest.mark.parametrize("sunday", ["iv", "v"])
@pytest.mark.parametrize("part", ["introitus", "collecta", "secreta", "postcommunio"])
def test_proper_page_claim_does_not_imply_full_expansion(sources, sunday, part):
    graph, by_id = sources
    text_id = f"proprium.dominica-{sunday}-post-pascha-{part}"
    use_id = f"use.{text_id}.mr1962"
    uses = [use for use in graph["uses"] if use["id"] == use_id]
    assert len(uses) == 1
    expected = INTROIT_CLAIM if part == "introitus" else ORATION_CLAIM
    assert uses[0]["claim"] == expected
    assert uses[0]["address"] == {"kind": "text", "text": text_id}
    assert uses[0]["role"] == "official_text"
    entries = [
        entry
        for group in by_id[text_id]["source_groups"]
        for entry in group["entries"]
        if entry["id"] == use_id
    ]
    assert len(entries) == 1
    assert entries[0]["claim"] == expected
    assert entries[0]["address"] == {"kind": "text"}
