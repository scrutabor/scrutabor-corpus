"""God's knowledge, human frailty and the petition have distinct roles."""

import json
import shutil
from collections import Counter
from pathlib import Path

import pytest

from build_reader.bibliography import _archive_locator
from build_reader.bibliography_bindings import digest, selected_text, witness_subject
from build_reader.layers import enrich_layer, expand_core
from checks import attribute, english, interlinear, orthography, polish
from checks.apparatus import derived_summary
from checks.language_packs import check_layer
from checks.raw_binding import BindingError, resolve_binding
from checks.transcription import check_transcriptions
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
NAME = "dominica-iv-post-epiphaniam-collecta"
TEXT = f"proprium.{NAME}"
REGISTRY = "witnesses/raw/bindings.json"
KEY = "epiphany-iv-collect"
GROUPS = [
    (
        "pl",
        3,
        14,
        10,
        "wiesz, że my, postawieni pośród tak wielkich niebezpieczeństw, "
        "z powodu ludzkiej słabości nie możemy się ostać",
    ),
    ("pl", 28, 29, 29, "z Twoją pomocą"),
    (
        "en",
        3,
        14,
        10,
        "know that we, placed amid such great dangers, cannot stand firm because of human frailty",
    ),
    ("en", 22, 30, 30, "with Your help we may overcome what we suffer for our sins"),
    ("en", 32, 33, 32, "our Lord"),
    ("en", 36, 37, 36, "Your Son"),
    ("en", 45, 46, 45, "of the Holy Spirit"),
    ("en", 48, 51, 50, "forever and ever"),
]
VARIANTS = {
    "w003": ("nos", "nos,"),
    "w029": ("adiuvánte", "adjuvánte"),
    "w034": ("Iesum", "Jesum"),
    "w035": ("Christum", "Christum,"),
    "w038": ("Qui", "qui"),
    "w046": ("Sancti,", "Sancti"),
}


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def layer(language):
    return load(f"languages/{language}/texts/proprium/{NAME}.json")


@pytest.mark.parametrize("language,start,end,anchor,gloss", GROUPS)
def test_complete_construction_has_one_realization(language, start, end, anchor, gloss):
    data = layer(language)
    words = [f"w{i:03}" for i in range(start, end + 1)]
    assert {"words": words, "anchor": f"w{anchor:03}", "gloss": gloss} in data["segments"][
        "s01"
    ].get("alignments", [])
    assert all("gloss" not in data["words"][word] for word in words)


@pytest.mark.parametrize("language,members,groups,direct", [("pl", 14, 2, 38), ("en", 31, 6, 21)])
def test_complete_realization_and_distinct_response(language, members, groups, direct):
    core = load(f"texts/proprium/{NAME}.json")
    data = layer(language)
    assert [len(s["words"]) for s in core["segments"]] == [51, 1]
    assert list(data["words"]) == [f"w{i:03}" for i in range(1, 53)]
    alignments = data["segments"]["s01"].get("alignments", [])
    assert len(alignments) == groups
    assert sum(len(g["words"]) for g in alignments) == members
    assert sum("gloss" in w for w in data["words"].values()) == direct
    assert all("reason" not in g for g in alignments)
    doc, view = expand_core(core), enrich_layer(core, data)
    assert view["lang"] == language
    for checker in (interlinear, polish, english, orthography):
        assert checker.check(doc, view) == []
    assert check_layer(core, data, ROOT / f"languages/{language}/texts/proprium/{NAME}.json") == []
    assert data["segments"]["s02"] == {"translation": "Amen."}


def test_polish_prose_and_first_person_purpose_retained():
    data = layer("pl")
    assert data["segments"]["s01"]["translation"] == (
        "Boże, który wiesz, że pośród tak wielkich niebezpieczeństw z powodu ludzkiej "
        "słabości nie możemy się ostać, daj nam zdrowie umysłu i ciała, abyśmy przy "
        "Twoim wsparciu przezwyciężyli to, co cierpimy za nasze grzechy. Przez Pana "
        "naszego Jezusa Chrystusa, Syna Twojego, który z Tobą żyje i króluje w jedności "
        "Ducha Świętego, Bóg, na wieki wieków."
    )
    assert data["words"]["w021"]["gloss"] == "abyśmy"
    assert data["words"]["w030"]["gloss"] == "przezwyciężyli"


def test_english_knowledge_purpose_and_contemporary_conclusion():
    assert layer("en")["segments"]["s01"]["translation"] == (
        "O God, You know that amid such great dangers we cannot stand firm because of "
        "human frailty. Grant us health of mind and body, that with Your help we may "
        "overcome those things which we suffer for our sins. Through our Lord Jesus "
        "Christ, Your Son, who lives and reigns with You in the unity of the Holy "
        "Spirit, God, forever and ever."
    )


def test_selected_latin_ritual_and_bounded_annotation_change():
    core = load(f"texts/proprium/{NAME}.json")
    assert (
        digest(selected_text(core))
        == "ee5b04ae897b7b13c323dd69791ea301afd6811a2d579f47345944b72fed1960"
    )
    words = {w["id"]: w for s in core["segments"] for w in s["words"]}
    for word in ("w022", "w023"):
        assert words[word]["morph"] == {"pos": "pron", "case": "acc", "number": "pl", "gender": "n"}
    editorial = core["editorial"]
    states = {
        word: editorial["words"]
        .get(word, {})
        .get("analysis", editorial["analysis_defaults_words"])["review"]
        for word in words
    }
    assert Counter(states.values()) == {"accepted": 44, "pending": 8}
    assert sorted(w for w, state in states.items() if state == "pending") == [
        "w001",
        "w003",
        "w009",
        "w022",
        "w023",
        "w026",
        "w029",
        "w033",
    ]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_both_languages_bind_the_current_source_without_approval(language):
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


def test_exact_original_body_and_shared_conclusion_have_six_variants():
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
    assert len(selected) == len(raw) == 52
    assert {
        f"w{i:03}": (a, b) for i, (a, b) in enumerate(zip(selected, raw, strict=True), 1) if a != b
    } == VARIANTS
    apparatus = load(f"witnesses/{TEXT}/apparatus.json")
    assert {
        v["at"]: (v["ours"], v["witnesses"]["do"]) for v in apparatus["adjudicated"]
    } == VARIANTS
    assert apparatus["summary"] == derived_summary(apparatus)
    assert check_transcriptions(path.parent) == ([], 1)
    assert result.source["binding"]["reading"] == [
        {"archive": "epiphany-iv", "first": 16, "last": 16},
        {"archive": "prayers", "first": 96, "last": 97},
    ]


def test_source_continuation_expansion_and_pending_reviews_remain_distinct():
    graph = load("bibliography/graph.json")
    core = load(f"texts/proprium/{NAME}.json")
    uses = {
        u["id"].removeprefix(f"use.{TEXT}."): u
        for u in graph["uses"]
        if u["address"].get("text") == TEXT
    }
    assert len(uses) == 6
    context = uses["oration-boundaries.mr1962"]
    item = next(i for i in graph["digital_items"] if i["id"] == context["digital_item"])
    errors = []
    _archive_locator(item, context["locator"], context["id"], errors)
    assert errors == []
    assert uses["body-continuation.mr1962"]["locator"]["printed"] == "p. 47"
    assert uses["expanded-conclusion.mr1962"]["locator"]["section"] == "Rubricae generales 115 a"
    assert "95–97" in uses["expanded-conclusion.do44667ff"]["locator"]["section"]
    witnesses = [w for w in graph["witnesses"] if w["text"] == TEXT]
    assert len(witnesses) == 2
    for witness in witnesses:
        assert witness["review"] == {"status": "pending"}
        assert witness_subject(ROOT, witness, graph, core)["contract"] == "witness-review-2"
        assert witness["use"] not in witness["source_dependencies"]["uses"]
    collation = next(c for c in graph["collations"] if c["text"] == TEXT)
    assert collation["review"] == {"status": "pending"}
    assert collation["apparatus_sha256"] == digest(load(f"witnesses/{TEXT}/apparatus.json"))


@pytest.fixture
def bound_prayer(tmp_path, monkeypatch):
    original = load(REGISTRY)
    registry = {
        "version": original["version"],
        "archives": {k: original["archives"][k] for k in ("epiphany-iv", "prayers")},
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
    "change", ["omit-amen", "omit-body", "legacy-coordinates", "wrong-reference", "archive"]
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
    elif change == "legacy-coordinates":
        binding["reading"][1].update(first=97, last=98)
    elif change == "wrong-reference":
        binding["references"][0]["text"] = "$Qui vivis"
    else:
        archive = root / registry["archives"]["epiphany-iv"]["path"]
        archive.write_bytes(archive.read_bytes() + b"\n")
    (root / REGISTRY).write_text(json.dumps(registry))
    with pytest.raises(BindingError):
        resolve_binding(path, root)
    errors, _ = check_transcriptions(path.parent)
    assert errors
