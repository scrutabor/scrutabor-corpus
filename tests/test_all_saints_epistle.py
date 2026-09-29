"""The complete Apocalypse reading and its translations retain every unit."""

import json
import shutil
from collections import Counter
from pathlib import Path

import pytest

from build_reader.bibliography_bindings import witness_subject
from build_reader.layers import enrich_layer, expand_core
from checks import collate, english, interlinear, polish
from checks.apparatus import derived_summary
from checks.language_packs import check_layer
from checks.raw_binding import BindingError, resolve_binding
from checks.transcription import check_transcriptions
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
NAME = "omnium-sanctorum-epistola"
TEXT = f"proprium.{NAME}"
WD = f"witnesses/{TEXT}"
REGISTRY = "witnesses/raw/bindings.json"
KEY = "all-saints-epistle"


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def layer(language):
    return load(f"languages/{language}/texts/proprium/{NAME}.json")


@pytest.mark.parametrize("language,groups,members,direct", [("pl", 3, 6, 217), ("en", 19, 40, 183)])
def test_each_reading_word_has_exactly_one_realization(language, groups, members, direct):
    core = load(f"texts/proprium/{NAME}.json")
    data = layer(language)
    assert len(core["segments"]) == 1
    words = core["segments"][0]["words"]
    assert len(words) == 223
    assert words[203]["form"] == words[222]["form"] == "Amen"
    alignments = data["segments"]["s01"].get("alignments", [])
    realized_members = [w for g in alignments for w in g["words"]]
    realized_direct = [w for w, v in data["words"].items() if "gloss" in v]
    assert (len(alignments), len(realized_members), len(realized_direct)) == (
        groups,
        members,
        direct,
    )
    assert Counter(realized_members + realized_direct) == Counter(w["id"] for w in words)
    assert all(g.get("gloss") and "reason" not in g for g in alignments)
    doc, view = expand_core(core), enrich_layer(core, data)
    for checker in [interlinear, polish, english]:
        assert checker.check(doc, view) == []
    assert check_layer(core, data, ROOT / f"languages/{language}/texts/proprium/{NAME}.json") == []


def test_polish_negative_concord_government_and_doxology():
    data = layer("pl")
    assert {wid: data["words"][wid]["gloss"] for wid in ["w141", "w159", "w202", "w207"]} == {
        "w141": "nie mógł",
        "w159": "w szaty",
        "w202": "Bogu",
        "w207": "chwała",
    }
    assert {"words": ["w184", "w185"], "anchor": "w185", "gloss": "wokół"} in data["segments"][
        "s01"
    ]["alignments"]
    assert "Błogosławieństwo i chwała," in data["segments"]["s01"]["translation"]


@pytest.mark.parametrize(
    "word,gloss",
    [
        ("w063", "of Judah"),
        ("w069", "of Reuben"),
        ("w075", "of Gad"),
        ("w081", "of Asher"),
        ("w087", "of Naphtali"),
        ("w093", "of Manasseh"),
        ("w099", "of Simeon"),
        ("w105", "of Levi"),
        ("w111", "of Issachar"),
        ("w117", "of Zebulun"),
        ("w123", "of Joseph"),
        ("w129", "of Benjamin"),
    ],
)
def test_each_english_tribal_name_keeps_its_genitive(word, gloss):
    assert layer("en")["words"][word]["gloss"] == gloss


@pytest.mark.parametrize(
    "words,anchor,gloss",
    [
        (["w022", "w023"], "w023", "to four angels"),
        (["w025", "w026"], "w025", "it was granted"),
        (["w032", "w033"], "w032", "Do not harm"),
        (["w139", "w140", "w141"], "w141", "no one could count"),
        (["w159", "w160"], "w159", "in white robes"),
        (["w220", "w221", "w222"], "w221", "forever and ever"),
    ],
)
def test_english_constructions_realize_force_once(words, anchor, gloss):
    data = layer("en")
    assert {"words": words, "anchor": anchor, "gloss": gloss} in data["segments"]["s01"][
        "alignments"
    ]
    assert all("gloss" not in data["words"][word] for word in words)


def test_contextual_gender_changes_do_not_inherit_old_acceptance():
    core = load(f"texts/proprium/{NAME}.json")
    words = {w["id"]: w for w in core["segments"][0]["words"]}
    for word, gender in [("w024", "m"), ("w134", "n")]:
        assert words[word]["morph"]["gender"] == gender
        assert core["editorial"]["words"][word]["analysis"]["review"] == "pending"
    assert Counter(
        core["editorial"]["words"]
        .get(wid, {})
        .get("analysis", core["editorial"]["analysis_defaults_words"])["review"]
        for wid in words
    ) == {
        "accepted": 158,
        "pending": 65,
    }


@pytest.mark.parametrize("language", ["pl", "en"])
def test_current_language_hashes_do_not_promote_working_origin(language):
    core = load(f"texts/proprium/{NAME}.json")
    sites = [
        s
        for s in load(f"languages/{language}/translation-provenance.json")["sites"]
        if s["text"] == TEXT
    ]
    assert len(sites) == 1
    site = sites[0]
    assert site["source_sha256"] == canonical_hash(source_payload(core["segments"][0]))
    assert site["target_sha256"] == canonical_hash(
        layer(language)["segments"]["s01"]["translation"]
    )
    assert site["origin"] == "working-unsettled" and site["review"] == "working"


def test_exact_original_body_and_complete_accidental_apparatus():
    core = load(f"texts/proprium/{NAME}.json")
    path = ROOT / WD / "do.txt"
    result = resolve_binding(path, ROOT)
    assert result is not None and len(result.text.split()) == 223
    assert result.source["binding"]["reading"] == [
        {"archive": "all-saints", "first": 26, "last": 26}
    ]
    assert result.source["binding"]["evidence"] == [
        {
            "archive": "all-saints",
            "first": 25,
            "last": 26,
            "section": "Lectio",
            "section_line": 23,
        }
    ]
    assert result.source["binding"]["references"] == []
    apparatus = load(f"{WD}/apparatus.json")
    selected = [
        w.get("pre", "") + w["form"] + w.get("post", "") for w in core["segments"][0]["words"]
    ]
    actual = {
        f"w{i:03}": (a, b)
        for i, (a, b) in enumerate(zip(selected, result.text.split(), strict=True), 1)
        if a != b
    }
    declared = {v["at"]: (v["ours"], v["witnesses"]["do"]) for v in apparatus["adjudicated"]}
    assert len(actual) == len(declared) == 40 and actual == declared
    assert "w060" not in actual
    assert actual["w129"] == ("Béniamin", "Bénjamin")
    assert sum("mr" in v["witnesses"] for v in apparatus["adjudicated"]) == 4
    assert apparatus["summary"] == derived_summary(apparatus)
    assert check_transcriptions(path.parent) == ([], 1)
    errors, _, stats = collate.collate(expand_core(core), path.parent)
    assert not errors and stats["words"] == 223


def test_two_page_continuation_is_bound_without_source_approval():
    graph = load("bibliography/graph.json")
    core = load(f"texts/proprium/{NAME}.json")
    uses = {u["id"]: u for u in graph["uses"] if u["address"].get("text") == TEXT}
    continuation = f"use.{TEXT}.body-continuation.mr1962"
    assert len(uses) == 3
    assert uses[continuation]["locator"]["printed"] == "p. 719"
    assert (
        uses[continuation]["evidence_sha256"]
        == "20588aa7297835fcc189c0f4c0ee6eacde2ed282f1dfd2f69cdebd36cf7de71a"
    )
    witnesses = [w for w in graph["witnesses"] if w["text"] == TEXT]
    assert len(witnesses) == 2
    for witness in witnesses:
        expected = (
            {"uses": [continuation], "raw_binding": None}
            if witness["transcription"] == "mr"
            else {"uses": [], "raw_binding": KEY}
        )
        assert witness["source_dependencies"] == expected
        assert witness["review"] == {"status": "pending"}
        assert witness_subject(ROOT, witness, graph, core)["contract"] == "witness-review-2"


@pytest.fixture
def bound_reading(tmp_path):
    original = load(REGISTRY)
    registry = {
        "version": original["version"],
        "archives": {"all-saints": original["archives"]["all-saints"]},
        "bindings": {KEY: original["bindings"][KEY]},
    }
    for name in [registry["archives"]["all-saints"]["path"], registry["bindings"][KEY]["witness"]]:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    (tmp_path / REGISTRY).write_text(json.dumps(registry))
    return tmp_path, registry


@pytest.mark.parametrize(
    "change", ["heading", "body", "outside", "archive", "old-normalization", "last-amen"]
)
def test_corrupt_or_incomplete_original_evidence_is_rejected(bound_reading, change):
    root, registry = bound_reading
    binding = registry["bindings"][KEY]
    path = root / binding["witness"]
    assert resolve_binding(path, root) is not None
    if change == "heading":
        binding["reading"][0]["first"] = 24
    elif change == "body":
        binding["reading"].clear()
    elif change == "outside":
        binding["reading"][0]["last"] = 27
    elif change == "archive":
        archive = root / registry["archives"]["all-saints"]["path"]
        archive.write_bytes(archive.read_bytes() + b"\n")
    elif change == "old-normalization":
        path.write_text(path.read_text().replace("Joánnes", "Ioánnes"))
    else:
        text = path.read_text()
        assert text.endswith("Amen.\n")
        path.write_text(text.removesuffix("Amen.\n"))
    (root / REGISTRY).write_text(json.dumps(registry))
    with pytest.raises(BindingError):
        resolve_binding(path, root)
