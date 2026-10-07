"""Romans 6 retains purpose, tense, parallel clauses and exact source boundaries."""

import json
import shutil
from collections import Counter
from pathlib import Path

import pytest

from build_reader.bibliography_bindings import digest, selected_text, transcript_digest
from checks import attribute
from checks.apparatus import derived_summary
from checks.interlinear import check
from checks.language_packs import check_layer
from checks.raw_binding import BindingError, resolve_binding
from checks.transcription import check_transcriptions
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
NAME = "dominica-vi-post-pentecosten-epistola"
TEXT = f"proprium.{NAME}"
REGISTRY = "witnesses/raw/bindings.json"
KEY = "pentecost-vi-epistle"
GROUPS = [
    ("pl", 40, 42, 40, "zostaliśmy razem wszczepieni"),
    ("pl", 48, 49, 49, "będziemy wszczepieni w podobieństwo zmartwychwstania"),
    ("pl", 63, 66, 66, "i abyśmy już nie służyli"),
    ("pl", 70, 71, 70, "umarł"),
    ("pl", 78, 79, 78, "umarliśmy"),
    ("pl", 103, 104, 103, "W tym bowiem, że"),
    ("pl", 105, 106, 105, "umarł"),
    ("pl", 108, 109, 108, "umarł"),
    ("pl", 111, 112, 111, "W tym zaś, że"),
    ("en", 3, 4, 3, "were baptized"),
    ("en", 9, 10, 9, "His death"),
    ("en", 11, 12, 11, "were baptized"),
    ("en", 13, 15, 13, "for we were buried together"),
    ("en", 32, 33, 33, "we too"),
    ("en", 34, 37, 37, "might walk in newness of life"),
    ("en", 38, 39, 39, "for if"),
    ("en", 40, 42, 40, "we have been planted together"),
    ("en", 44, 45, 44, "of His death"),
    ("en", 46, 49, 49, "we will also be united in the likeness of His resurrection"),
    ("en", 50, 52, 51, "we know this:"),
    ("en", 53, 55, 54, "our old self"),
    ("en", 56, 58, 57, "was crucified with Him"),
    ("en", 60, 62, 60, "the body of sin might be destroyed"),
    ("en", 64, 66, 66, "we might no longer serve"),
    ("en", 68, 69, 69, "for whoever"),
    ("en", 70, 71, 70, "has died"),
    ("en", 72, 73, 72, "has been justified"),
    ("en", 76, 77, 77, "but if"),
    ("en", 78, 79, 78, "we have died"),
    ("en", 85, 86, 86, "we will also live"),
    ("en", 95, 96, 95, "no longer"),
    ("en", 99, 102, 102, "will no longer rule over Him"),
    ("en", 103, 104, 103, "for the death"),
    ("en", 105, 106, 105, "He died"),
    ("en", 108, 109, 108, "He died"),
    ("en", 111, 112, 111, "but the life"),
    ("en", 117, 118, 118, "you too"),
    ("en", 121, 123, 121, "to be dead indeed"),
    ("en", 125, 126, 125, "but alive"),
    ("en", 131, 132, 131, "our Lord"),
]
VARIANTS = {
    "w007": ("Iesu,", "Jesu,"),
    "w022": ("ut", "ut,"),
    "w045": ("eius:", "ejus:"),
    "w072": ("iustificátus", "justificátus"),
    "w082": ("crédimus", "crédimus,"),
    "w089": ("sciéntes", "sciéntes,"),
    "w092": ("resúrgens", "resurgens"),
    "w095": ("iam", "jam"),
    "w130": ("Iesu", "Jesu,"),
}


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def layer(language):
    return load(f"languages/{language}/texts/proprium/{NAME}.json")


@pytest.mark.parametrize("language,start,end,anchor,gloss", GROUPS)
def test_complete_construction_has_one_realization(language, start, end, anchor, gloss):
    data = layer(language)
    ids = [f"w{number:03}" for number in range(start, end + 1)]
    assert {"words": ids, "anchor": f"w{anchor:03}", "gloss": gloss} in data["segments"]["s01"].get(
        "alignments", []
    )
    assert all("gloss" not in data["words"][word] for word in ids)


@pytest.mark.parametrize("language,members,direct,zero", [("pl", 21, 110, 1), ("en", 76, 56, 0)])
def test_all_132_words_and_explanation_topology(language, members, direct, zero):
    core = load(f"texts/proprium/{NAME}.json")
    data = layer(language)
    ids = [w["id"] for s in core["segments"] for w in s["words"]]
    assert ids == [f"w{number:03}" for number in range(1, 133)]
    assert set(data["words"]) == set(ids)
    groups = data["segments"]["s01"]["alignments"]
    assert sum(len(g["words"]) for g in groups if "gloss" in g) == members
    assert sum(len(g["words"]) for g in groups if "reason" in g) == zero
    assert sum("gloss" in w for w in data["words"].values()) == direct
    assert check(core, data) == []
    assert check_layer(core, data, ROOT / f"languages/{language}/texts/proprium/{NAME}.json") == []
    assert core["localization"]["explanations"] == {"w040": {}, "w072": {}, "w092": {}}
    assert {w for w, d in data["words"].items() if "explanation" in d} == {"w040", "w072", "w092"}
    if language == "pl":
        assert {"words": ["w123"], "reason": "idiom"} in groups


def test_polish_purpose_and_parallel_predicates():
    data = layer("pl")
    expected = {
        "w022": "abyśmy",
        "w025": "powstał",
        "w037": "postępowali",
        "w059": "aby",
        "w092": "powstawszy",
        "w113": "żyje",
        "w114": "żyje",
    }
    assert {w: data["words"][w]["gloss"] for w in expected} == expected
    assert "abyśmy – jak Chrystus" in data["segments"]["s01"]["translation"]
    assert "uwolnienie spod jego władzy" in data["words"]["w072"]["explanation"]
    assert "imiesłów ma formę teraźniejszą" in data["words"]["w092"]["explanation"]


def test_english_anterior_resurrection_and_parallel_predicates():
    data = layer("en")
    expected = {"w092": "having risen", "w110": "once", "w113": "He lives", "w114": "He lives"}
    assert {w: data["words"][w]["gloss"] for w in expected} == expected
    prose = data["segments"]["s01"]["translation"]
    assert "we will also be united with Him in the likeness of His resurrection" in prose
    assert "we might no longer serve sin" in prose
    assert "the death He died, He died to sin once for all" in prose
    assert "the life He lives, He lives to God" in prose
    assert "release from sin’s claim" in data["words"]["w072"]["explanation"]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_provenance_reflects_current_prose_without_approval(language):
    core = load(f"texts/proprium/{NAME}.json")
    site = next(
        s
        for s in load(f"languages/{language}/translation-provenance.json")["sites"]
        if s["site"] == f"{TEXT}.s01.{language}"
    )
    assert site["source_sha256"] == canonical_hash(source_payload(core["segments"][0]))
    assert (
        site["source_sha256"] == "a0b0ae5d91b28709c725fe56493309adb769ff29bfc92a1d52063a7ddcb497c1"
    )
    assert site["target_sha256"] == canonical_hash(
        layer(language)["segments"]["s01"]["translation"]
    )
    assert (site["origin"], site["review"], site["familiar_core"]) == (
        "working-unsettled",
        "working",
        False,
    )


def test_selected_latin_ritual_and_analysis_states_unchanged():
    core = load(f"texts/proprium/{NAME}.json")
    assert (
        digest(selected_text(core))
        == "b18db5049d48b0f4f321ed7d5f0f08d4d14725f32daa678b8832510e9b23a0f3"
    )
    editorial = core["editorial"]
    defaults = editorial["analysis_defaults_words"]["review"]
    reviews = [
        editorial["words"].get(w["id"], {}).get("analysis", {}).get("review", defaults)
        for s in core["segments"]
        for w in s["words"]
    ]
    assert Counter(reviews) == {"accepted": 103, "pending": 29}


def test_complete_raw_reading_and_all_nine_variant_positions():
    path = ROOT / f"witnesses/{TEXT}/do.txt"
    result = resolve_binding(path, ROOT)
    assert result is not None
    raw = result.text.split()
    core = load(f"texts/proprium/{NAME}.json")
    selected = [
        (w.get("pre", "") + w["form"] + w.get("post", ""))
        for s in core["segments"]
        for w in s["words"]
    ]
    assert len(raw) == len(selected) == 132
    differences = {
        f"w{i:03}": (a, b) for i, (a, b) in enumerate(zip(selected, raw, strict=True), 1) if a != b
    }
    assert differences == VARIANTS
    apparatus = load(f"witnesses/{TEXT}/apparatus.json")
    assert {
        e["at"]: (e["ours"], e["witnesses"]["do"]) for e in apparatus["adjudicated"]
    } == VARIANTS
    assert (
        apparatus["summary"]
        == derived_summary(apparatus)
        == {"entries": 9, "classes": ["accent", "orthography", "punctuation"]}
    )
    assert "ten accidental events" in apparatus["note"]
    assert "comma" in next(e["ruling"] for e in apparatus["adjudicated"] if e["at"] == "w130")
    assert check_transcriptions(path.parent) == ([], 1)
    assert result.source["binding"]["evidence"] == [
        {
            "archive": "pentecost-vi",
            "first": 27,
            "last": 28,
            "section": "Lectio",
            "section_line": 25,
        }
    ]
    assert result.source["binding"]["reading"] == [
        {"archive": "pentecost-vi", "first": 28, "last": 28}
    ]
    assert result.source["binding"]["references"] == []


def test_actual_edition_and_pending_source_states():
    graph = load("bibliography/graph.json")
    uses = [u for u in graph["uses"] if u["address"].get("text") == TEXT]
    assert len(uses) == 2 and all(u["verified_on"] == "2026-08-31" for u in uses)
    mr = next(u for u in uses if u["id"].endswith(".mr1962"))
    assert "Benziger" in mr["claim"] and "without shared expansions" in mr["claim"]
    assert mr["locator"]["printed"] == "p. 379"
    witnesses = [w for w in graph["witnesses"] if w["text"] == TEXT]
    assert len(witnesses) == 2
    for w in witnesses:
        assert w["review"] == {"status": "pending"}
        # The DO witness names its raw binding; the Missal witness has none.
        bound = {"uses": [], "raw_binding": KEY} if w["id"].endswith(".do44667ff") else None
        assert w.get("source_dependencies") == bound
        raw = (ROOT / f"witnesses/{TEXT}/{w['transcription']}.txt").read_text()
        assert w["transcription_sha256"] == transcript_digest(raw)
    collation = next(c for c in graph["collations"] if c["text"] == TEXT)
    assert collation["review"] == {"status": "pending"}
    assert collation["apparatus_sha256"] == digest(load(f"witnesses/{TEXT}/apparatus.json"))
    assert "without shared expansions" in collation["recension"]


@pytest.fixture
def bound_epistle(tmp_path, monkeypatch):
    original = load(REGISTRY)
    registry = {
        "version": original["version"],
        "archives": {"pentecost-vi": original["archives"]["pentecost-vi"]},
        "bindings": {KEY: original["bindings"][KEY]},
    }
    for name in [
        registry["archives"]["pentecost-vi"]["path"],
        registry["bindings"][KEY]["witness"],
    ]:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    (tmp_path / REGISTRY).write_text(json.dumps(registry), encoding="utf-8")
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    return tmp_path, registry


@pytest.mark.parametrize(
    "change", ["title", "omit-body", "next-section", "section-line", "archive-bytes"]
)
def test_bad_reading_boundary_or_archive_cannot_pass(bound_epistle, change):
    root, registry = bound_epistle
    binding = registry["bindings"][KEY]
    path = root / binding["witness"]
    assert resolve_binding(path, root) is not None
    assert check_transcriptions(path.parent) == ([], 1)
    if change == "title":
        binding["reading"][0]["first"] = 26
    elif change == "omit-body":
        binding["reading"][0]["first"] = binding["reading"][0]["last"] = 27
    elif change == "next-section":
        binding["reading"][0]["last"] = 30
    elif change == "section-line":
        binding["evidence"][0]["section_line"] = 21
    else:
        archive = root / registry["archives"]["pentecost-vi"]["path"]
        archive.write_bytes(archive.read_bytes() + b"\n")
    (root / REGISTRY).write_text(json.dumps(registry), encoding="utf-8")
    with pytest.raises(BindingError):
        resolve_binding(path, root)
    errors, count = check_transcriptions(path.parent)
    assert errors and count == 0
