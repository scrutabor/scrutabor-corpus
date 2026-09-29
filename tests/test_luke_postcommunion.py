"""The received gift, intercession and requested safety retain their relations."""

import json
import shutil
from collections import Counter
from pathlib import Path

import pytest

from build_reader.bibliography_bindings import digest, selected_text, witness_subject
from checks import attribute
from checks.apparatus import derived_summary
from checks.interlinear import check
from checks.language_packs import check_layer
from checks.raw_binding import BindingError, resolve_binding
from checks.transcription import check_transcriptions
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
NAME = "sancti-lucae-evangelistae-postcommunio"
TEXT = f"proprium.{NAME}"
REGISTRY = "witnesses/raw/bindings.json"
KEY = "luke-postcommunion"
GROUPS = [
    ("pl", 20, 24, 24, "byśmy przez to mogli być bezpieczni"),
    ("en", 7, 11, 11, "we have received from Your holy altar"),
    ("en", 13, 15, 14, "of Your blessed evangelist"),
    ("en", 18, 19, 18, "our souls"),
    ("en", 20, 21, 21, "and through it"),
    ("en", 22, 24, 24, "we may be safe"),
    ("en", 26, 27, 26, "our Lord"),
    ("en", 30, 31, 30, "Your Son"),
    ("en", 39, 40, 39, "of the Holy Spirit"),
    ("en", 42, 45, 44, "forever and ever"),
]
VARIANTS = {
    "w016": ("Lucæ", "Lucæ,"),
    "w028": ("Iesum", "Jesum"),
    "w029": ("Christum", "Christum,"),
    "w032": ("Qui", "qui"),
    "w040": ("Sancti,", "Sancti"),
}


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def layer(language):
    return load(f"languages/{language}/texts/proprium/{NAME}.json")


@pytest.mark.parametrize("language,start,end,anchor,gloss", GROUPS)
def test_complete_construction_has_one_gloss(language, start, end, anchor, gloss):
    data = layer(language)
    ids = [f"w{number:03}" for number in range(start, end + 1)]
    assert {"words": ids, "anchor": f"w{anchor:03}", "gloss": gloss} in data["segments"]["s01"].get(
        "alignments", []
    )
    assert all("gloss" not in data["words"][word] for word in ids)


@pytest.mark.parametrize("language,members,groups,direct", [("pl", 5, 1, 41), ("en", 25, 9, 21)])
def test_all_words_realized_and_response_separate(language, members, groups, direct):
    core = load(f"texts/proprium/{NAME}.json")
    data = layer(language)
    ids = [w["id"] for s in core["segments"] for w in s["words"]]
    assert ids == [f"w{number:03}" for number in range(1, 47)]
    assert set(data["words"]) == set(ids)
    alignments = data["segments"]["s01"].get("alignments", [])
    assert len(alignments) == groups
    assert sum(len(g["words"]) for g in alignments) == members
    assert sum("gloss" in w for w in data["words"].values()) == direct
    assert all("reason" not in g for g in alignments)
    assert check(core, data) == []
    assert check_layer(core, data, ROOT / f"languages/{language}/texts/proprium/{NAME}.json") == []
    assert data["segments"]["s02"] == {"translation": "Amen."}


def test_polish_prose_and_conclusion_retained():
    data = layer("pl")
    assert data["segments"]["s01"]["translation"] == (
        "Spraw, prosimy, wszechmogący Boże, aby to, co otrzymaliśmy z Twojego "
        "świętego ołtarza, dzięki prośbom Twojego świętego Ewangelisty Łukasza "
        "uświęciło nasze dusze, byśmy przez to mogli być bezpieczni. Przez Pana "
        "naszego Jezusa Chrystusa, Syna Twojego, który z Tobą żyje i króluje "
        "w jedności Ducha Świętego, Bóg, na wieki wieków."
    )
    assert data["words"]["w011"]["gloss"] == "przyjęliśmy"
    assert data["words"]["w017"]["gloss"] == "uświęciło"


def test_english_reception_intercession_safety_and_consistent_register():
    data = layer("en")
    assert data["segments"]["s01"]["translation"] == (
        "Grant, we pray, almighty God, that what we have received from Your holy "
        "altar may, through the prayers of Your blessed evangelist Luke, sanctify "
        "our souls, so that through it we may be safe. Through our Lord Jesus "
        "Christ, Your Son, who lives and reigns with You in the unity of the "
        "Holy Spirit, God, forever and ever."
    )
    expected = {
        "w017": "may sanctify",
        "w032": "who",
        "w033": "with You",
        "w034": "lives",
        "w036": "reigns",
    }
    assert {w: data["words"][w]["gloss"] for w in expected} == expected


@pytest.mark.parametrize("language", ["pl", "en"])
def test_provenance_bound_without_new_approval(language):
    core = load(f"texts/proprium/{NAME}.json")
    sites = [
        s
        for s in load(f"languages/{language}/translation-provenance.json")["sites"]
        if s["text"] == TEXT
    ]
    assert len(sites) == 2
    for segment, site in zip(core["segments"], sites, strict=True):
        assert site["segment"] == segment["id"]
        assert site["source_sha256"] == canonical_hash(source_payload(segment))
        assert site["target_sha256"] == canonical_hash(
            layer(language)["segments"][segment["id"]]["translation"]
        )
        assert site["review"] == "working" and site["familiar_core"] is False
    assert [s["origin"] for s in sites] == ["working-unsettled", "trivial"]


def test_selected_latin_ritual_and_analysis_states_unchanged():
    core = load(f"texts/proprium/{NAME}.json")
    assert (
        digest(selected_text(core))
        == "da6331dad4d9be25979d214e8104d8a2e9c30818df1df23a9fe0c8dc3de71c84"
    )
    editorial = core["editorial"]
    states = {
        w["id"]: editorial["words"]
        .get(w["id"], {})
        .get("analysis", editorial["analysis_defaults_words"])["review"]
        for s in core["segments"]
        for w in s["words"]
    }
    assert Counter(states.values()) == {"accepted": 39, "pending": 7}
    assert sorted(w for w, state in states.items() if state == "pending") == [
        "w003",
        "w004",
        "w007",
        "w008",
        "w015",
        "w022",
        "w027",
    ]


def test_exact_complete_raw_reading_and_five_variants():
    path = ROOT / f"witnesses/{TEXT}/do.txt"
    result = resolve_binding(path, ROOT)
    assert result is not None
    core = load(f"texts/proprium/{NAME}.json")
    selected = [
        w.get("pre", "") + w["form"] + w.get("post", "")
        for s in core["segments"]
        for w in s["words"]
    ]
    raw = result.text.split()
    assert len(selected) == len(raw) == 46
    assert {
        f"w{i:03}": (a, b) for i, (a, b) in enumerate(zip(selected, raw, strict=True), 1) if a != b
    } == VARIANTS
    apparatus = load(f"witnesses/{TEXT}/apparatus.json")
    assert {
        e["at"]: (e["ours"], e["witnesses"]["do"]) for e in apparatus["adjudicated"]
    } == VARIANTS
    assert (
        apparatus["summary"]
        == derived_summary(apparatus)
        == {"entries": 5, "classes": ["capitalization", "orthography", "punctuation"]}
    )
    assert check_transcriptions(path.parent) == ([], 1)
    assert result.source["binding"]["reading"] == [
        {"archive": "saint-luke", "first": 48, "last": 48},
        {"archive": "prayers", "first": 96, "last": 97},
    ]


def test_source_body_expansion_and_pending_states_distinct():
    graph = load("bibliography/graph.json")
    core = load(f"texts/proprium/{NAME}.json")
    uses = {
        u["id"].removeprefix(f"use.{TEXT}."): u
        for u in graph["uses"]
        if u["address"].get("text") == TEXT
    }
    assert len(uses) == 5
    assert all(";" not in use["claim"] for use in uses.values())
    assert uses["mr1962"]["locator"]["printed"] == "p. 706"
    assert (
        uses["mr1962"]["evidence_sha256"]
        == "4341129416c2a262e403888f9e938773bbe199c65a5b0072b7d5c86329c28d2a"
    )
    assert "24-word body" in uses["mr1962"]["claim"]
    assert uses["mr1962"]["verified_on"] == "2026-08-31"
    assert uses["expanded-conclusion.mr1962"]["locator"]["printed"] == "p. xvii"
    assert "95–97" in uses["expanded-conclusion.do44667ff"]["locator"]["section"]
    witnesses = [w for w in graph["witnesses"] if w["text"] == TEXT]
    assert {w["transcription"] for w in witnesses} == {"mr", "do"}
    assert len(witnesses) == 2
    for witness in witnesses:
        assert witness["review"] == {"status": "pending"}
        subject = witness_subject(ROOT, witness, graph, core)
        assert subject["contract"] == "witness-review-2"
        assert witness["use"] not in witness["source_dependencies"]["uses"]
    collation = next(c for c in graph["collations"] if c["text"] == TEXT)
    assert collation["review"] == {"status": "pending"}
    assert collation["apparatus_sha256"] == digest(load(f"witnesses/{TEXT}/apparatus.json"))
    printed = (ROOT / f"witnesses/{TEXT}/mr.txt").read_text()
    assert "Benziger 1962 (Editio iuxta typicam)" in printed
    assert "unaccented" in printed and "tuum, qui" in printed


@pytest.fixture
def bound_prayer(tmp_path, monkeypatch):
    original = load(REGISTRY)
    registry = {
        "version": original["version"],
        "archives": {k: original["archives"][k] for k in ("saint-luke", "prayers")},
        "bindings": {KEY: original["bindings"][KEY]},
    }
    for name in [a["path"] for a in registry["archives"].values()] + [
        registry["bindings"][KEY]["witness"]
    ]:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    (tmp_path / REGISTRY).write_text(json.dumps(registry))
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    return tmp_path, registry


@pytest.mark.parametrize(
    "change", ["omit-amen", "omit-body", "wrong-reference", "section", "archive"]
)
def test_incomplete_or_corrupt_raw_evidence_fails(bound_prayer, change):
    root, registry = bound_prayer
    binding = registry["bindings"][KEY]
    path = root / binding["witness"]
    assert resolve_binding(path, root) is not None
    assert check_transcriptions(path.parent) == ([], 1)
    if change == "omit-amen":
        binding["reading"][1]["last"] = 96
    elif change == "omit-body":
        binding["reading"].pop(0)
    elif change == "wrong-reference":
        binding["references"][0]["text"] = "$Qui vivis"
    elif change == "section":
        binding["evidence"][0]["section_line"] = 1
    else:
        archive = root / registry["archives"]["saint-luke"]["path"]
        archive.write_bytes(archive.read_bytes() + b"\n")
    (root / REGISTRY).write_text(json.dumps(registry))
    with pytest.raises(BindingError):
        resolve_binding(path, root)
    errors, _ = check_transcriptions(path.parent)
    assert errors
