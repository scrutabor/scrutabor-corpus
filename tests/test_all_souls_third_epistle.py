"""The third All Souls reading keeps its complete body and coherent realizations."""

import json
from pathlib import Path

import pytest

from build_reader import bibliography_bindings as bb
from build_reader import store
from checks import english, interlinear, raw_binding
from checks.collate import collate, load_witness
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.commemoratio-omnium-fidelium-defunctorum-missa-iii-epistola"
BINDING = "all-souls-third-epistle"
RAW_SHA = "5df3f33ec73be46350101304e0438d8d71d2864a08bbb2d7799fd01c61de60df"
GROUPS = [
    (["w002", "w003"], "w002", "those days"),
    (["w024", "w025"], "w024", "their labors"),
    (["w026", "w027", "w028"], "w026", "for their works"),
]


@pytest.mark.parametrize(
    "wid,gloss", [("w005", "a voice"), ("w011", "blessed are"), ("w022", "they may rest")]
)
def test_direct_english_predicates(wid, gloss):
    assert store.raw_layer(ROOT, "en", TEXT)["words"][wid]["gloss"] == gloss


@pytest.mark.parametrize("ids,anchor,gloss", GROUPS)
def test_exact_minimal_english_groups(ids, anchor, gloss):
    layer = store.raw_layer(ROOT, "en", TEXT)
    groups = [g for g in layer["segments"]["s01"]["alignments"] if set(ids) & set(g["words"])]
    assert groups == [{"words": ids, "anchor": anchor, "gloss": gloss}]
    assert all("gloss" not in layer["words"][wid] for wid in ids)


def test_complete_partition_and_retained_direct_frames():
    doc, layers = store.load(ROOT, TEXT)
    assert len(doc["segments"]) == 1 and len(doc["segments"][0]["words"]) == 30
    for language, direct, grouped in [("pl", 30, 0), ("en", 23, 7)]:
        layer = layers[language]
        assert interlinear.check(doc, layer) == []
        assert sum(bool(e.get("gloss")) for e in layer["words"].values()) == direct
        alignments = interlinear.alignments_for(layer, "s01")
        assert sum(len(a["words"]) for a in alignments) == grouped
        assert all(a.get("gloss") for a in alignments)
    en = layers["en"]["words"]
    for wid, gloss in {
        "w012": "the dead",
        "w017": "henceforth",
        "w018": "now",
        "w019": "says",
        "w020": "the Spirit",
        "w021": "that",
        "w023": "from",
        "w029": "follow",
        "w030": "them",
    }.items():
        assert en[wid]["gloss"] == gloss
    pl = layers["pl"]["words"]
    for wid, gloss in {
        "w008": "mówiący",
        "w021": "aby",
        "w022": "odpoczywali",
        "w029": "idą za",
        "w030": "nimi",
    }.items():
        assert pl[wid]["gloss"] == gloss


def test_original_dependent_hybrid_is_rejected_by_ordinary_dispatch():
    doc, layers = store.load(ROOT, TEXT)
    assert english.check(doc, layers["en"]) == []
    layers["en"]["words"]["w022"]["gloss"] = "let them rest"
    assert any("dependent glosses" in error for error in english.check(doc, layers["en"]))


def test_contextual_gender_stays_pending_in_actual_expanded_reader():
    raw = store.core(ROOT, TEXT)
    doc, _ = store.load(ROOT, TEXT)
    assert raw["segments"][0]["words"][27]["morph"] == {
        "pos": "pron",
        "case": "gen",
        "number": "pl",
        "gender": "m",
    }
    assert doc["segments"][0]["words"][27]["analysis"] == {
        "confidence": "high",
        "sources": ["editorial", "whitakers", "collatinus"],
        "review": "pending",
    }


@pytest.mark.parametrize(
    "language,prefix,target_hash",
    [
        (
            "pl",
            "Epistoła formularza",
            "aa326fcd482cc111d25756af24e18c884ecda7f9d20278d6eeeadbaaf05a44aa",
        ),
        (
            "en",
            "The Epistle of",
            "9091b0f213745bf71b9495961c4bca6bffc38912ea02208160dfd960f02fbb33",
        ),
    ],
)
def test_localized_about_unchanged_prose_and_working_provenance(language, prefix, target_hash):
    raw = store.core(ROOT, TEXT)
    layer = store.raw_layer(ROOT, language, TEXT)
    assert layer["about"].startswith(prefix)
    assert canonical_hash(layer["segments"]["s01"]["translation"]) == target_hash
    sites = json.loads((ROOT / f"languages/{language}/translation-provenance.json").read_bytes())[
        "sites"
    ]
    sites = [s for s in sites if s["text"] == TEXT]
    assert len(sites) == 1
    site = sites[0]
    assert site["source_sha256"] == canonical_hash(source_payload(raw["segments"][0]))
    assert site["target_sha256"] == target_hash
    assert (site["origin"], site["review"], site["familiar_core"]) == (
        "working-unsettled",
        "working",
        False,
    )


def test_selected_latin_and_ritual_are_unchanged():
    raw = store.core(ROOT, TEXT)
    assert (
        bb.digest(bb.selected_text(raw))
        == "98f711c12135370788efc8b90d1ccebdb24becc544706b5de43b15026d9ecb53"
    )
    assert (raw["segments"][0]["speaker"], raw["segments"][0]["voice"], raw["sung"]) == (
        "sacerdos",
        "clara",
        False,
    )


def test_exact_inline_raw_source_excludes_framing_and_inheritance():
    witness = ROOT / "witnesses" / TEXT / "do.txt"
    bound = raw_binding.resolve_binding(witness, ROOT)
    assert bound is not None
    source = bound.source
    assert source["binding_id"] == BINDING
    assert source["binding"]["evidence"] == [
        {"archive": BINDING, "first": 19, "last": 19, "section": "Lectio", "section_line": 16}
    ]
    assert source["binding"]["reading"] == [{"archive": BINDING, "first": 19, "last": 19}]
    assert source["binding"]["references"] == []
    assert len(source["archives"]) == 1
    archive = source["archives"][BINDING]
    assert archive == {
        "upstream": "web/www/missa/Latin/Sancti/11-02m3.txt",
        "revision": "44667ff518b8ff1439780470828b39714f5306a2",
        "path": "witnesses/raw/do-11-02m3.txt",
        "sha256": RAW_SHA,
    }
    tokens = bound.text.split()
    assert len(tokens) == 30
    assert (tokens[6], tokens[16], tokens[17]) == ("cœlo,", "Amodo", "jam")


def test_exact_witness_differences_and_collation():
    directory = ROOT / "witnesses" / TEXT
    app = json.loads((directory / "apparatus.json").read_bytes())
    readings = {
        (e["at"], witness): value
        for e in app["adjudicated"]
        for witness, value in e["witnesses"].items()
    }
    assert readings == {
        ("w007", "do"): "cœlo,",
        ("w017", "mr"): "Amodo",
        ("w017", "do"): "Amodo",
        ("w018", "do"): "jam",
    }
    assert app["summary"] == {"entries": 3, "classes": ["capital-accent", "orthography"]}
    assert collate(store.load(ROOT, TEXT)[0], directory)[0] == []
    for name in ["do", "mr"]:
        _, body = load_witness(directory / f"{name}.txt")
        assert len(body.split()) == 30


def test_current_source_claims_and_pending_scope_are_complete():
    graph = json.loads((ROOT / "bibliography/graph.json").read_bytes())
    uses = [u for u in graph["uses"] if u.get("address", {}).get("text") == TEXT]
    witnesses = [w for w in graph["witnesses"] if w["text"] == TEXT]
    collations = [c for c in graph["collations"] if c["text"] == TEXT]
    assert (len(uses), len(witnesses), len(collations)) == (2, 2, 1)
    mr = next(u for u in uses if u["id"].endswith(".mr1962"))
    do = next(u for u in uses if u["id"].endswith(".do44667ff"))
    assert mr["role"] == "direct_approved_print" and do["role"] == "derived_digital_collation_aid"
    assert (
        mr["locator"]["printed"] == "p. 726" and mr["locator"]["scan"] == "leaf n807 / PDF p. 808"
    )
    assert "Benziger" in mr["claim"] and "no shared expansion" in mr["claim"]
    assert "direct body line 19" in do["locator"]["section"]
    for witness in witnesses:
        assert witness["review"] == {"status": "pending"}
        assert witness["coverage"] == {"kind": "full"}
        name = witness["transcription"]
        raw = (ROOT / "witnesses" / TEXT / f"{name}.txt").read_text()
        assert witness["transcription_sha256"] == bb.transcript_digest(raw)
        if name == "mr":
            assert (
                "Benziger" in raw
                and "does not establish the historical transcription"
                in witness["independence_basis"]
            )
            assert "# transcribed: 2026-08-31" in raw and "# recollated: 2026-09-25" in raw
    app = json.loads((ROOT / "witnesses" / TEXT / "apparatus.json").read_bytes())
    assert collations[0]["apparatus_sha256"] == bb.digest(app)
    assert collations[0]["review"] == {"status": "pending"}
    core = store.core(ROOT, TEXT)
    for text in [core["editorial"]["notes"], core["editorial"]["source"]["method"]]:
        assert "Benziger 1962" in text and "typical-edition" not in text
