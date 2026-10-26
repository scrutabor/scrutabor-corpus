"""Rosary Postcommunion source boundaries and contextual captions."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import bibliography, store
from build_reader.bibliography_bindings import digest, selected_text, transcript_digest
from checks.collate import collate

ROOT = Path(__file__).resolve().parents[1]
TID = "proprium.beatae-mariae-virginis-a-rosario-postcommunio"
USE = "use." + TID + "."


def load():
    return (
        store.core(ROOT, TID),
        store.raw_layer(ROOT, "pl", TID),
        store.raw_layer(ROOT, "en", TID),
        json.loads((ROOT / "bibliography/graph.json").read_text()),
        (ROOT / "witnesses" / TID / "mr.txt").read_text(),
        json.loads((ROOT / "witnesses" / TID / "apparatus.json").read_text()),
    )


def validate(core, pl, en, graph, mr, apparatus):
    words = [w for s in core["segments"] for w in s["words"]]
    assert [w["id"] for w in words] == [f"w{i:03d}" for i in range(1, 41)]
    assert (words[0]["form"], words[0]["lemma"]) == ("Sanctíssimæ", "sanctus")
    assert words[0]["head"] == "w002"
    assert words[0]["morph"] == {
        "pos": "adj",
        "case": "gen",
        "degree": "sup",
        "gender": "f",
        "number": "sg",
    }
    assert core["editorial"]["words"]["w001"]["analysis"] == {
        "confidence": "high",
        "sources": ["editorial", "whitakers", "collatinus"],
        "review": "pending",
    }
    assert pl["words"]["w010"]["gloss"] == "abyśmy byli wspomożeni"
    assert pl["words"]["w020"]["gloss"] == "które"
    assert pl["words"]["w024"]["gloss"] == "Który"
    assert pl["words"]["w017"]["gloss"] == "została otrzymana"
    assert pl["words"]["w022"]["gloss"] == "został osiągnięty"
    # These exact source-order captions preserve subject and passive force.
    for wid, expected in {
        "w006": "we honor",
        "w010": "may we be helped",
        "w017": "may be received",
        "w022": "may be obtained",
    }.items():
        assert en["words"][wid]["gloss"] == expected
    assert en["words"]["w024"]["gloss"] == "You"
    groups = en["segments"]["s01"]["alignments"]
    assert groups == [
        {"words": ["w001", "w002", "w003"], "anchor": "w002", "gloss": "Of Your most holy Mother"},
        {"words": ["w033", "w034"], "anchor": "w033", "gloss": "of the Holy Spirit"},
    ]
    assert all(en["words"][wid] == {} for wid in ("w001", "w002", "w003", "w033", "w034"))
    uses = {u["id"]: u for u in graph["uses"]}
    proper = uses[USE + "mr1962"]
    assert proper["role"] == "direct_approved_print"
    assert "23-word" in proper["claim"] and "two-word" in proper["claim"]
    assert "not fully printed" in proper["claim"]
    formula = uses[USE + "conclusion-rg115d.mr1962"]
    assert formula["role"] == "direct_approved_print"
    assert formula["address"] == {"kind": "word", "text": TID, "word": "w024"}
    assert formula["locator"]["printed"] == "p. xviii"
    assert formula["locator"]["scan"] == "leaf n23 / PDF p. 24"
    assert (
        formula["evidence_sha256"]
        == "db99d725287dbdb233ff9c22c94cd027ec6b5105f2f64817ec828778805ff132"
    )
    assert "# proper-literal: Sanctíssimæ" in mr
    assert "efféctus: Qui vivis.\n" in mr
    assert (
        "# conclusion-literal: Qui vivis et regnas cum Deo Patre in unitate Spiritus Sancti, "
        "Deus, per omnia sæcula sæculorum. Amen;\n" in mr
    )
    assert "# expansion:" in mr and "42 physically attested" in mr
    assert "exact printed accents" not in mr
    first = next(e for e in apparatus["adjudicated"] if e["at"] == "w001")
    assert first["class"] == "substantive"
    assert first["ours"] == "Sanctíssimæ" and first["witnesses"] == {"do": "Sacratíssimæ"}
    assert apparatus["summary"] == {
        "entries": 4,
        "classes": ["orthography", "punctuation", "substantive"],
    }
    witnesses = [w for w in graph["witnesses"] if w["text"] == TID]
    assert len(witnesses) == 2 and all(w["review"] == {"status": "pending"} for w in witnesses)
    witness = next(w for w in witnesses if w["transcription"] == "mr")
    assert witness["transcription_sha256"] == transcript_digest(mr)
    assert witness["source_dependencies"] == {"uses": [formula["id"]], "raw_binding": None}
    assert witness["orthography_profile"] == "page-body-with-declared-common-expansion"
    collation = next(c for c in graph["collations"] if c["text"] == TID)
    assert collation["selected_text_sha256"] == digest(selected_text(core))
    assert collation["apparatus_sha256"] == digest(apparatus)
    assert collation["apparatus"] == apparatus["summary"]
    assert collation["review"] == {"status": "pending"}


def test_rosary_exact_source_and_caption_successor():
    validate(*load())


@pytest.mark.parametrize(
    "damage",
    [
        "first-form",
        "first-lemma",
        "provider",
        "pl-number",
        "pl-subject",
        "en-relative",
        "en-subject",
        "en-percipiatur",
        "en-obtineatur",
        "en-possessive",
        "scope",
        "formula-page",
        "dependency",
        "digital-variant",
        "false-full-print",
        "approval",
    ],
)
def test_rosary_in_memory_defects_reject(damage):
    subject = list(deepcopy(load()))
    core, pl, en, graph, mr, apparatus = subject
    first = core["segments"][0]["words"][0]
    if damage == "first-form":
        first["form"] = "Sacratíssimæ"
    elif damage == "first-lemma":
        first["lemma"] = "sacratus"
    elif damage == "provider":
        core["editorial"]["words"]["w001"]["analysis"]["sources"].remove("collatinus")
    elif damage == "pl-number":
        pl["words"]["w020"]["gloss"] = "który"
    elif damage == "pl-subject":
        pl["words"]["w010"]["gloss"] = "zostali wspomożeni"
    elif damage.startswith("en-") and damage != "en-possessive":
        wid, value = {
            "en-relative": ("w006", "honor"),
            "en-subject": ("w010", "may be helped"),
            "en-percipiatur": ("w017", "may derive"),
            "en-obtineatur": ("w022", "may obtain"),
        }[damage]
        en["words"][wid]["gloss"] = value
    elif damage == "en-possessive":
        en["segments"]["s01"]["alignments"][0]["words"].pop()
    elif damage == "scope":
        next(u for u in graph["uses"] if u["id"] == USE + "mr1962")["claim"] = (
            "The page prints the complete selected prayer."
        )
    elif damage == "formula-page":
        next(u for u in graph["uses"] if u["id"] == USE + "conclusion-rg115d.mr1962")["locator"][
            "printed"
        ] = "p. 694"
    elif damage == "dependency":
        next(w for w in graph["witnesses"] if w["text"] == TID and w["transcription"] == "mr")[
            "source_dependencies"
        ]["uses"] = []
    elif damage == "digital-variant":
        next(e for e in apparatus["adjudicated"] if e["at"] == "w001")["witnesses"]["do"] = (
            "Sanctíssimæ"
        )
    elif damage == "false-full-print":
        subject[4] = mr.replace("# expansion:", "# note:")
    elif damage == "approval":
        next(c for c in graph["collations"] if c["text"] == TID)["review"] = {
            "status": "reviewed",
            "sha256": "0" * 64,
        }
    with pytest.raises(AssertionError):
        validate(*subject)


def test_rosary_literal_collation_and_pending_projection():
    # Run the ordinary collation and projection in addition to source-specific pins.
    result = collate(store.core(ROOT, TID), ROOT / "witnesses" / TID)
    assert result[:2] == ([], [])
    graph = load()[3]
    evidence = next(e for e in bibliography.public_text_evidence(graph)["texts"] if e["id"] == TID)
    assert evidence["witnesses"] == [] and "collation" not in evidence
