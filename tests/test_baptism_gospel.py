"""John 1 preserves identification, testimony and exact Gospel boundaries."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.bibliography_bindings import digest, selected_text, transcript_digest
from build_reader.layers import enrich_layer, expand_core
from checks import english, interlinear
from checks.language_packs import check_layer
from checks.raw_binding import resolve_binding
from checks.transcription import check_transcriptions
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
NAME = "commemoratio-baptismatis-domini-evangelium"
TEXT = f"proprium.{NAME}"
GROUPS = [
    ("pl", 20, 21, 20, "To jest Ten"),
    ("pl", 32, 33, 32, "stanął"),
    ("pl", 97, 98, 98, "Duchem"),
    ("en", 20, 21, 20, "This is the One"),
    ("en", 32, 33, 32, "was placed"),
    ("en", 48, 49, 48, "I came"),
    ("en", 54, 55, 55, "bore witness"),
    ("en", 98, 99, 98, "the Holy Spirit"),
    ("en", 104, 105, 105, "bore witness"),
]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def layer(language, name=NAME):
    return load(f"languages/{language}/texts/proprium/{name}.json")


@pytest.mark.parametrize("language,start,end,anchor,gloss", GROUPS)
def test_minimal_construction_has_one_provider(language, start, end, anchor, gloss):
    data = layer(language)
    ids = [f"w{n:03}" for n in range(start, end + 1)]
    assert {"words": ids, "anchor": f"w{anchor:03}", "gloss": gloss} in data["segments"]["s01"][
        "alignments"
    ]
    assert all(data["words"][wid] == {} for wid in ids)


@pytest.mark.parametrize("language,members,direct", [("pl", 7, 103), ("en", 15, 95)])
def test_all_110_tokens_remain_accounted_for(language, members, direct):
    core = load(f"texts/proprium/{NAME}.json")
    data = layer(language)
    ids = [w["id"] for w in core["segments"][0]["words"]]
    assert ids == [f"w{n:03}" for n in range(1, 111)]
    assert set(ids) == set(data["words"])
    groups = data["segments"]["s01"]["alignments"]
    assert sum(len(g["words"]) for g in groups) == members
    zeros = [g for g in groups if "gloss" not in g]
    assert zeros == [{"words": ["w058"], "reason": "punctuation"}]
    assert all("gloss" in g and "reason" not in g for g in groups if g not in zeros)
    assert sum("gloss" in w for w in data["words"].values()) == direct
    assert interlinear.check(expand_core(core), enrich_layer(core, data)) == []
    assert check_layer(core, data, ROOT / f"languages/{language}/texts/proprium/{NAME}.json") == []


def test_polish_explicit_subject_and_predicative_cases():
    data = layer("pl")
    expected = {"w048": "przyszedłem", "w049": "ja", "w095": "Tym, który", "w109": "Synem"}
    assert {wid: data["words"][wid]["gloss"] for wid in expected} == expected
    assert data["words"]["w059"]["gloss"] == "Ujrzałem"
    assert (
        "Ten, nad kim zobaczysz Ducha zstępującego i pozostającego na Nim, jest Tym, "
        "który chrzci w Duchu Świętym."
    ) in data["segments"]["s01"]["translation"]


def test_english_relative_clause_and_precedence():
    data = layer("en")
    expected = {
        "w028": "a man",
        "w036": "me",
        "w086": "you see",
        "w095": "the One who",
        "w109": "the Son",
    }
    assert {wid: data["words"][wid]["gloss"] for wid in expected} == expected
    prose = data["segments"]["s01"]["translation"]
    assert "has been placed ahead of me, because He existed before me" in prose
    assert "The One upon whom you see the Spirit descending and remaining is the One who" in prose
    assert "And I saw and bore witness that this is the Son of God." in prose


@pytest.mark.parametrize(
    "name,subject,verb,gloss",
    [
        (NAME, "w039", "w040", "did not know"),
        (NAME, "w071", "w072", "did not know"),
        (NAME, "w101", "w102", "saw"),
        ("corporis-christi-evangelium", "w040", "w041", "live"),
        ("dominica-ii-post-pascha-evangelium", "w074", "w075", "know"),
        ("sanctorum-simonis-et-iudae-apostolorum-evangelium", "w054", "w055", "have spoken"),
        ("septem-dolorum-beatae-mariae-virginis-sequentia", "w135", "w136", "live"),
    ],
)
def test_explicit_subject_is_realized_once_and_restoration_fails(name, subject, verb, gloss):
    core = load(f"texts/proprium/{name}.json")
    data = layer("en", name)
    assert data["words"][subject]["gloss"] == "I"
    assert data["words"][verb]["gloss"] == gloss
    doc = expand_core(core)
    assert english.check(doc, enrich_layer(core, data)) == []
    changed = deepcopy(data)
    changed["words"][verb]["gloss"] = "I " + gloss
    errors = english.check(doc, enrich_layer(core, changed))
    assert len(errors) == 1 and verb in errors[0] and "subject twice" in errors[0]


def test_restoring_separate_duplicated_witness_fails():
    core = load(f"texts/proprium/{NAME}.json")
    data = layer("en")
    data["segments"]["s01"]["alignments"] = [
        g for g in data["segments"]["s01"]["alignments"] if "w104" not in g["words"]
    ]
    data["words"]["w104"] = {"gloss": "witness"}
    data["words"]["w105"] = {"gloss": "bore witness"}
    doc, enriched = expand_core(core), enrich_layer(core, data)
    assert interlinear.check(doc, enriched) == []
    errors = english.check(doc, enriched)
    assert len(errors) == 1 and "w104–w105" in errors[0] and "object twice" in errors[0]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_provenance_binds_current_words_without_new_approval(language):
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


def test_selected_latin_and_all_six_witness_variants():
    core = load(f"texts/proprium/{NAME}.json")
    assert (
        digest(selected_text(core))
        == "80fbc0510b62dd01d55dbe1608e27ce74e54eeb8699ce6b5efde7c959835e509"
    )
    selected = [
        w.get("pre", "") + w["form"] + w.get("post", "") for w in core["segments"][0]["words"]
    ]
    path = ROOT / f"witnesses/{TEXT}/do.txt"
    bound = resolve_binding(path, ROOT)
    assert bound is not None
    raw = bound.text.split()
    assert len(raw) == len(selected) == 110
    differences = {
        f"w{i:03}": (a, b) for i, (a, b) in enumerate(zip(selected, raw, strict=True), 1) if a != b
    }
    assert differences == {
        "w005": ("Ioánnes", "Joánnes"),
        "w006": ("Iesum", "Jesum"),
        "w015": ("ecce", "ecce,"),
        "w056": ("Ioánnes,", "Joánnes,"),
        "w065": ("cælo,", "coelo,"),
        "w105": ("perhíbui", "perhíbui,"),
    }
    apparatus = load(f"witnesses/{TEXT}/apparatus.json")
    assert {
        a["at"]: (a["ours"], a["witnesses"]["do"]) for a in apparatus["adjudicated"]
    } == differences
    assert bound.source["binding"]["reading"] == [{"archive": "baptism", "first": 29, "last": 29}]
    assert bound.source["binding"]["references"] == []
    assert check_transcriptions(path.parent) == ([], 1)


def test_exact_edition_metadata_does_not_renew_source_acceptance():
    graph = load("bibliography/graph.json")
    uses = [u for u in graph["uses"] if u["address"].get("text") == TEXT]
    assert {u["id"].rsplit(".", 1)[1]: u["verified_on"] for u in uses} == {
        "mr1962": "2026-09-25",
        "do44667ff": "2026-09-12",
    }
    witnesses = [w for w in graph["witnesses"] if w["text"] == TEXT]
    assert len(witnesses) == 2
    for w in witnesses:
        assert w["review"] == {"status": "pending"}
        assert w["source_dependencies"] == {
            "uses": [],
            "raw_binding": "baptism-gospel" if w["transcription"] == "do" else None,
        }
        raw = (ROOT / f"witnesses/{TEXT}/{w['transcription']}.txt").read_text()
        assert w["transcription_sha256"] == transcript_digest(raw)
    collation = next(c for c in graph["collations"] if c["text"] == TEXT)
    assert collation["review"] == {"status": "pending"}
    assert collation["apparatus_sha256"] == digest(load(f"witnesses/{TEXT}/apparatus.json"))
    assert "Benziger 1962" in collation["recension"]
