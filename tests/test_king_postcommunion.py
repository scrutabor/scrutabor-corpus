"""The received food, royal service and requested reign remain distinct."""

import json
import shutil
from collections import Counter
from pathlib import Path

import pytest

from build_reader.bibliography_bindings import digest, selected_text, witness_subject
from build_reader.layers import enrich_layer, expand_core
from checks import attribute, interlinear, orthography, polish
from checks.apparatus import derived_summary
from checks.language_packs import check_layer
from checks.raw_binding import BindingError, resolve_binding
from checks.transcription import check_transcriptions
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
NAME = "d-n-iesu-christi-regis-postcommunio"
TEXT = f"proprium.{NAME}"
REGISTRY = "witnesses/raw/bindings.json"
KEY = "king-postcommunion"
GROUPS = [
    ("pl", 8, 13, 13, "szczycimy się służbą pod sztandarami Chrystusa Króla"),
    ("pl", 20, 21, 21, "mogli królować"),
    ("en", 1, 3, 3, "Having received nourishment of immortality"),
    ("en", 9, 11, 11, "the banners of Christ the King"),
    ("en", 12, 13, 13, "glory in serving"),
    ("en", 20, 21, 21, "may reign"),
    ("en", 29, 30, 29, "of the Holy Spirit"),
]
VARIANTS = {
    "w017": ("cælésti", "cœlésti"),
    "w019": ("iúgiter", "júgiter"),
    "w030": ("Sancti,", "Sancti"),
    "w031": ("Deus,", "Deus"),
}


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def layer(language):
    return load(f"languages/{language}/texts/proprium/{NAME}.json")


@pytest.mark.parametrize("language,start,end,anchor,gloss", GROUPS)
def test_complete_construction_has_one_gloss(language, start, end, anchor, gloss):
    data = layer(language)
    words = [f"w{i:03}" for i in range(start, end + 1)]
    assert {"words": words, "anchor": f"w{anchor:03}", "gloss": gloss} in data["segments"][
        "s01"
    ].get("alignments", [])
    assert all("gloss" not in data["words"][word] for word in words)


@pytest.mark.parametrize("language,members,groups,direct", [("pl", 8, 2, 28), ("en", 12, 5, 24)])
def test_complete_realization_and_separate_response(language, members, groups, direct):
    core = load(f"texts/proprium/{NAME}.json")
    data = layer(language)
    assert [len(s["words"]) for s in core["segments"]] == [35, 1]
    assert list(data["words"]) == [f"w{i:03}" for i in range(1, 37)]
    alignments = data["segments"]["s01"].get("alignments", [])
    assert len(alignments) == groups
    assert sum(len(g["words"]) for g in alignments) == members
    assert sum("gloss" in w for w in data["words"].values()) == direct
    assert all("reason" not in g for g in alignments)
    doc, view = expand_core(core), enrich_layer(core, data)
    assert view["lang"] == language
    assert interlinear.check(doc, view) == []
    assert polish.check(doc, view) == []
    assert orthography.check(doc, view) == []
    assert check_layer(core, data, ROOT / f"languages/{language}/texts/proprium/{NAME}.json") == []
    assert data["segments"]["s02"] == {"translation": "Amen."}


def test_polish_prose_and_familiar_conclusion_retained():
    assert layer("pl")["segments"]["s01"]["translation"] == (
        "Dostąpiwszy pożywienia nieśmiertelności, prosimy, Panie, abyśmy my, którzy "
        "chlubimy się, że walczymy pod sztandarami Chrystusa Króla, wraz z Nim mogli "
        "ustawicznie królować w niebieskiej siedzibie. Który z Tobą żyje i króluje "
        "w jedności Ducha Świętego, Bóg, na wieki wieków."
    )


def test_english_plural_banners_location_and_contemporary_conclusion():
    data = layer("en")
    assert data["segments"]["s01"]["translation"] == (
        "We have received the food of eternal life, and we beseech You, O Lord, "
        "that we who are proud to serve under the banners of Christ the King "
        "may forever reign with Him in the heavenly abode. Who lives and reigns "
        "with You in the unity of the Holy Spirit, God, forever and ever."
    )
    expected = {
        "w017": "the heavenly",
        "w022": "who",
        "w023": "with You",
        "w024": "lives",
        "w026": "reigns",
    }
    assert {w: data["words"][w]["gloss"] for w in expected} == expected


@pytest.mark.parametrize("language", ["pl", "en"])
def test_exact_prose_binding_without_new_approval(language):
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
        == "59b91ef7b11869c4f8e9cf7a38b721e90978b90d487342b1c24a6eaa1508df1f"
    )
    editorial = core["editorial"]
    states = {
        w["id"]: editorial["words"]
        .get(w["id"], {})
        .get("analysis", editorial["analysis_defaults_words"])["review"]
        for s in core["segments"]
        for w in s["words"]
    }
    assert Counter(states.values()) == {"accepted": 34, "pending": 2}
    assert sorted(w for w, state in states.items() if state == "pending") == [
        "w003",
        "w007",
    ]


def test_exact_raw_body_reference_expansion_and_four_variants():
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
    assert len(selected) == len(raw) == 36
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
        == {"entries": 4, "classes": ["orthography", "punctuation"]}
    )
    assert check_transcriptions(path.parent) == ([], 1)
    assert result.source["binding"]["reading"] == [
        {"archive": "christ-the-king", "first": 66, "last": 66},
        {"archive": "prayers", "first": 120, "last": 121},
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
    assert uses["mr1962"]["locator"]["printed"] == "p. 714"
    assert (
        uses["mr1962"]["evidence_sha256"]
        == "11254c649bf18357480103d2824f2e1624bb6dc128278742cb564403ec8ae112"
    )
    assert "21-word body" in uses["mr1962"]["claim"]
    assert uses["mr1962"]["verified_on"] == "2026-08-31"
    assert uses["expanded-conclusion.mr1962"]["locator"]["printed"] == "p. xviii"
    assert "119–121" in uses["expanded-conclusion.do44667ff"]["locator"]["section"]
    assert "505" in uses["oration-boundaries.mr1962"]["locator"]["section"]
    witnesses = [w for w in graph["witnesses"] if w["text"] == TEXT]
    assert len(witnesses) == 2 and {w["transcription"] for w in witnesses} == {
        "mr",
        "do",
    }
    for witness in witnesses:
        assert witness["review"] == {"status": "pending"}
        assert witness_subject(ROOT, witness, graph, core)["contract"] == "witness-review-2"
        assert witness["use"] not in witness["source_dependencies"]["uses"]
    collation = next(c for c in graph["collations"] if c["text"] == TEXT)
    assert collation["review"] == {"status": "pending"}
    assert collation["apparatus_sha256"] == digest(load(f"witnesses/{TEXT}/apparatus.json"))
    printed = (ROOT / f"witnesses/{TEXT}/mr.txt").read_text()
    assert "Benziger 1962 (Editio iuxta typicam)" in printed and "unaccented" in printed


@pytest.fixture
def bound_prayer(tmp_path, monkeypatch):
    original = load(REGISTRY)
    registry = {
        "version": original["version"],
        "archives": {k: original["archives"][k] for k in ("christ-the-king", "prayers")},
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
        binding["reading"][1]["last"] = 120
    elif change == "omit-body":
        binding["reading"].pop(0)
    elif change == "wrong-reference":
        binding["references"][0]["text"] = "$Qui vivis"
    elif change == "section":
        binding["evidence"][0]["section_line"] = 1
    else:
        archive = root / registry["archives"]["christ-the-king"]["path"]
        archive.write_bytes(archive.read_bytes() + b"\n")
    (root / REGISTRY).write_text(json.dumps(registry))
    with pytest.raises(BindingError):
        resolve_binding(path, root)
    errors, _ = check_transcriptions(path.parent)
    assert errors
