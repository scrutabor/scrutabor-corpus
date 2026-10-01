"""Protect the Vigil Epistle's contextual reading and direct source boundary."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import emit, store
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, lint, raw_binding, translation_provenance

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.vigilia-pentecostes-epistola"
GROUPS = [
    ("pl", 35, 40, 40, "nawet nie słyszeliśmy, czy Duch Święty istnieje"),
    ("en", 2, 3, 2, "those days"),
    ("en", 24, 27, 27, "Did you receive the Holy Spirit"),
    ("en", 35, 40, 40, "we have not even heard whether there is a Holy Spirit"),
    ("en", 47, 48, 47, "were you baptized"),
    ("en", 54, 56, 54, "Then Paul said"),
    ("en", 70, 71, 71, "they should believe"),
    ("en", 76, 77, 77, "Having heard these things"),
    ("en", 78, 79, 78, "they were baptized"),
    ("en", 86, 89, 86, "Paul had laid hands on them"),
    ("en", 90, 92, 90, "the Holy Spirit came"),
    ("en", 100, 101, 100, "And there were"),
    ("en", 103, 105, 103, "about twelve men"),
    ("en", 106, 107, 106, "And having entered"),
]


def load(path):
    return json.loads((ROOT / path).read_bytes())


def word(core, ident):
    return next(w for s in core["segments"] for w in s.get("words", []) if w["id"] == ident)


@pytest.mark.parametrize("language,first,last,anchor,gloss", GROUPS)
def test_contextual_constructions(language, first, last, anchor, gloss):
    layer = store.raw_layer(ROOT, language, TEXT)
    ids = [f"w{i:03}" for i in range(first, last + 1)]
    assert {"words": ids, "anchor": f"w{anchor:03}", "gloss": gloss} in layer["segments"]["s01"][
        "alignments"
    ]
    assert all("gloss" not in layer["words"][ident] for ident in ids)


@pytest.mark.parametrize(
    "language,ident,gloss",
    [
        ("pl", "w045", "czym"),
        ("en", "w029", "But"),
        ("en", "w030", "they"),
        ("en", "w051", "In"),
        ("en", "w096", "they spoke"),
        ("en", "w060", "of penance"),
        ("en", "w069", "him"),
        ("en", "w108", "into the synagogue"),
        ("pl", "w047", "ochrzczeni"),
        ("pl", "w048", "zostaliście"),
    ],
)
def test_direct_readings_and_retained_alternatives(language, ident, gloss):
    assert store.raw_layer(ROOT, language, TEXT)["words"][ident]["gloss"] == gloss


@pytest.mark.parametrize("language,direct,groups", [("pl", 108, 4), ("en", 79, 15)])
def test_provider_coverage_and_transport(language, direct, groups):
    raw = store.core(ROOT, TEXT)
    core = expand_core(raw)
    layer = enrich_layer(raw, store.raw_layer(ROOT, language, TEXT))
    assert interlinear.check(core, layer) == []
    assert sum("gloss" in row for row in layer["words"].values()) == direct
    assert len(layer["segments"]["s01"]["alignments"]) == groups
    assert all("gloss" in a for a in layer["segments"]["s01"]["alignments"])
    tables = [emit.Table() for _ in range(4)]
    p, a, c, local = tables
    encoded = emit.core_artifact(core, raw, p, a, c)
    translated = emit.language_artifact(core, layer, local)
    decoded, target = emit.expand(encoded, translated, *[t.order for t in tables])
    expected, languages = emit._strip(core, {language: layer})
    assert decoded == expected and target == languages[language]
    assert word(decoded, "w009")["morph"]["case"] == "loc"
    for ident in ("w009", "w019"):
        assert word(decoded, ident)["analysis"]["review"] == "pending"


@pytest.mark.parametrize("ident,key,value", [("w009", "case", "loc"), ("w019", "gender", "m")])
def test_contextual_analysis_keeps_pending_override(ident, key, value):
    raw = store.core(ROOT, TEXT)
    assert word(raw, ident)["morph"][key] == value
    assert raw["editorial"]["words"][ident]["analysis"] == {
        "confidence": "high",
        "sources": ["editorial", "whitakers", "collatinus"],
        "review": "pending",
    }
    assert word(expand_core(raw), ident)["analysis"]["review"] == "pending"
    assert word(raw, "w004")["substantive"] is True
    assert "gender" not in word(raw, "w045")["morph"]


def test_locative_contract_rejects_unknown_case_and_preserves_genuine_genitives():
    core = expand_core(store.core(ROOT, TEXT))
    assert lint.lint_text(core) == ([], 120)
    bad = deepcopy(core)
    word(bad, "w009")["morph"]["case"] = "locale"
    assert lint.lint_text(bad)[0]
    for text, ident in [
        ("proprium.dominica-xi-post-pentecosten-evangelium", "w008"),
        ("proprium.sancti-bartholomaei-apostoli-evangelium", "w089"),
        ("proprium.sancti-bartholomaei-apostoli-evangelium", "w091"),
        ("proprium.sancti-petri-et-pauli-apostolorum-evangelium", "w008"),
        ("proprium.dominica-iv-in-quadragesima-evangelium", "w011"),
    ]:
        assert word(store.core(ROOT, text), ident)["morph"]["case"] == "gen"
    assert core["schema_version"] == "0.21.0"


@pytest.mark.parametrize(
    "phrase",
    [
        "upper regions",
        "Did you receive the Holy Spirit when you came to believe?",
        "We have not even heard whether there is a Holy Spirit.",
        "Him who was to come after him",
        "had laid his hands on them",
        "the Holy Spirit came upon them",
        "for three months",
        "about twelve men",
        "with tongues and prophesied",
        "disputing and persuading",
    ],
)
def test_working_english_prose_preserves_context(phrase):
    assert phrase in store.raw_layer(ROOT, "en", TEXT)["segments"]["s01"]["translation"]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_localized_about_and_current_working_provenance(language):
    core = store.core(ROOT, TEXT)
    layer = store.raw_layer(ROOT, language, TEXT)
    assert ("Epistoła" if language == "pl" else "Epistle") in layer["about"]
    site = next(
        s
        for s in load(f"languages/{language}/translation-provenance.json")["sites"]
        if s["site"] == TEXT + ".s01." + language
    )
    assert (site["origin"], site["review"], site["familiar_core"]) == (
        "working-unsettled",
        "working",
        False,
    )
    assert site["source_sha256"] == translation_provenance.canonical_hash(
        translation_provenance.source_payload(core["segments"][0])
    )
    assert site["target_sha256"] == translation_provenance.canonical_hash(
        layer["segments"]["s01"]["translation"]
    )
    if language == "pl":
        assert (
            site["target_sha256"]
            == "d1997a28b0bff8206933435b4d73ee94781e26da075f77afca09e19e3002af54"
        )


def test_direct_raw_body_has_no_expansion_or_response():
    path = ROOT / "witnesses" / TEXT / "do.txt"
    bound = raw_binding.resolve_binding(path, ROOT)
    assert bound is not None
    plan = bound.source["binding"]
    assert plan["references"] == []
    assert plan["evidence"] == [
        {
            "archive": "pentecost-vigil-epistle",
            "first": 29,
            "last": 29,
            "section": "Lectio",
            "section_line": 26,
        }
    ]
    assert plan["reading"] == [{"archive": "pentecost-vigil-epistle", "first": 29, "last": 29}]
    original = (ROOT / "witnesses/raw/do-Tempora-Pasc6-6r.txt").read_text().splitlines()
    assert original[25] == "[Lectio]"
    assert bound.text == " ".join(original[28].split())
    assert len(bound.text.split()) == 120
    assert bound.text.endswith("de regno Dei.") and "Deo gratias" not in bound.text


def test_precise_source_scope_and_pending_records():
    graph = load("bibliography/graph.json")
    uses = {
        u["id"].rsplit(".", 1)[-1]: u
        for u in graph["uses"]
        if u.get("address", {}).get("text") == TEXT
    }
    assert set(uses) == {"mr1962", "do44667ff"}
    assert uses["mr1962"]["role"] == "direct_approved_print"
    assert uses["mr1962"]["locator"]["printed"] == "p. 348"
    assert "Benziger" in uses["mr1962"]["claim"] and "without" in uses["mr1962"]["claim"]
    assert "body line 29" in uses["do44667ff"]["locator"]["section"]
    witnesses = [w for w in graph["witnesses"] if w["text"] == TEXT]
    assert len(witnesses) == 2
    assert {w["id"] for w in witnesses} == {f"witness.{TEXT}.mr1962", f"witness.{TEXT}.do44667ff"}
    for w in graph["witnesses"]:
        if w["text"] == TEXT:
            assert w["review"] == {"status": "pending"}
            assert w["coverage"] == {"kind": "full"}
            assert w["source_dependencies"] == {
                "uses": [],
                "raw_binding": "pentecost-vigil-epistle" if w["transcription"] == "do" else None,
            }
            if w["transcription"] == "mr":
                assert "has been checked directly" in w["independence_basis"]
    collation = next(c for c in graph["collations"] if c["text"] == TEXT)
    assert collation["review"] == {"status": "pending"}
    assert (
        collation["selected_text_sha256"]
        == "7bb7946d63cc6a311938a62eb9242647e0be4fd3e1f924d46b4f80361fcb5f81"
    )
    core = store.core(ROOT, TEXT)
    assert "Benziger" in core["editorial"]["notes"]
    assert "Benziger" in core["editorial"]["source"]["method"]
    assert "Deo gratias" in core["editorial"]["notes"]


def test_exact_accidentals_preserve_both_ephesum_differences():
    apparatus = load(f"witnesses/{TEXT}/apparatus.json")
    rows = apparatus["adjudicated"]
    assert len(rows) == 12
    triples = [(r["at"], r["ours"], r["witnesses"]) for r in rows]
    assert triples == [
        ("w011", "Paulus", {"do": "Paulus,"}),
        ("w014", "pártibus", {"do": "pártibus,"}),
        ("w016", "Éphesum,", {"do": "Ephesum"}),
        ("w016", "Éphesum,", {"mr": "Ephesum,"}),
        ("w035", "neque", {"do": "neque,"}),
        ("w052", "Ioánnis", {"do": "Joannis"}),
        ("w057", "Ioánnes", {"do": "Joánnes"}),
        ("w060", "pæniténtiæ", {"do": "pœniténtiæ"}),
        ("w073", "est,", {"do": "est"}),
        ("w075", "Iesum.", {"do": "Jesum."}),
        ("w083", "Iesu.", {"do": "Jesu."}),
        ("w115", "dísputans,", {"do": "dísputans"}),
    ]
    assert "accent" in rows[2]["ruling"] and "comma" in rows[2]["ruling"]


def test_locked_reader_registry_accepts_contextual_locative():
    raw = store.core(ROOT, TEXT)
    core = expand_core(raw)
    tables = [
        emit.Table(emit._registry_records(name), locked=True, label=name)
        for name in ("morphology", "analysis", "citations")
    ]
    artifact = emit.core_artifact(core, raw, *tables)
    assert len(artifact["seg"][0]["w"]) == 120
