"""Bounded Holy Innocents reading and source contracts, not universal gloss rules."""

import copy
import json
from pathlib import Path

import pytest

from build_reader import bibliography_bindings as bb
from build_reader import store
from checks import english, interlinear, raw_binding
from checks.collate import collate, load_witness
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.sanctorum-innocentium-martyrum-evangelium"
BINDING = "holy-innocents-gospel"
MORPH = {
    "case": "nom",
    "gender": "n",
    "mood": "part",
    "number": "sg",
    "pos": "verb",
    "tense": "fut",
    "voice": "act",
}
PAIRS = [
    (["w016", "w017"], "w016", "His mother"),
    (["w044", "w045"], "w044", "His mother"),
    (["w071", "w072"], "w071", "My Son"),
    (["w096", "w097"], "w096", "its territory"),
    (["w125", "w126"], "w125", "loud lamentation"),
    (["w129", "w130"], "w129", "her children"),
]


def phrase(layer, ids):
    by_word = interlinear.alignment_by_word(layer)
    seen, pieces = set(), []
    for wid in ids:
        if wid in by_word:
            group = by_word[wid]
            assert set(group["words"]) <= set(ids)
            key = tuple(group["words"])
            if key not in seen and "gloss" in group:
                pieces.append(group["gloss"])
            seen.add(key)
        else:
            pieces.append(layer["words"][wid]["gloss"])
    return " / ".join(pieces)


@pytest.mark.parametrize("ids,anchor,gloss", PAIRS)
def test_selected_nominal_order_is_shared_once(ids, anchor, gloss):
    layer = store.raw_layer(ROOT, "en", TEXT)
    groups = [a for a in layer["segments"]["s01"]["alignments"] if set(ids) & set(a["words"])]
    assert groups == [{"words": ids, "anchor": anchor, "gloss": gloss}]
    assert all("gloss" not in layer["words"][wid] for wid in ids)


def test_relative_completion_keeps_both_finite_predicates():
    layer = store.raw_layer(ROOT, "en", TEXT)
    # Keep the following by/through attribution beside spoken, not fulfilled.
    assert phrase(layer, [f"w{n:03d}" for n in range(58, 63)]) in {
        "that / might be fulfilled / what / was spoken",
        "that / there might be fulfilled / what / was spoken",
    }
    assert [layer["words"][f"w{n:03d}"]["gloss"] for n in range(63, 68)] == [
        "by",
        "the Lord",
        "through",
        "the prophet",
        "saying",
    ]


@pytest.mark.parametrize("expletive", [False, True])
def test_smaller_complete_relative_clause_remains_provider_valid(expletive):
    doc, layers = store.load(ROOT, TEXT)
    layer = copy.deepcopy(layers["en"])
    ids = {f"w{n:03d}" for n in range(58, 63)}
    layer["segments"]["s01"]["alignments"] = [
        a for a in layer["segments"]["s01"]["alignments"] if not ids & set(a["words"])
    ]
    for wid, gloss in {
        "w058": "that",
        "w059": "there might be fulfilled" if expletive else "might be fulfilled",
        "w060": "what",
    }.items():
        layer["words"][wid]["gloss"] = gloss
    for wid in ["w061", "w062"]:
        layer["words"][wid].pop("gloss", None)
    layer["segments"]["s01"]["alignments"].append(
        {"words": ["w061", "w062"], "anchor": "w061", "gloss": "was spoken"}
    )
    layer["segments"]["s01"]["alignments"].sort(key=lambda a: a["words"][0])
    assert interlinear.check(doc, layer) == []
    assert english.check(doc, layer) == []


def test_embedded_predicates_keep_their_subject():
    layer = store.raw_layer(ROOT, "en", TEXT)
    assert phrase(layer, ["w077", "w078"]) == "he had been tricked"
    assert layer["words"]["w105"]["gloss"] == "he had carefully ascertained"


@pytest.mark.parametrize("lang,gloss", [("pl", "ich nie ma"), ("en", "they are no more")])
def test_final_existential_negation_has_one_complete_provider(lang, gloss):
    layer = store.raw_layer(ROOT, lang, TEXT)
    ids = ["w135", "w136"]
    matches = [a for a in layer["segments"]["s01"]["alignments"] if set(ids) & set(a["words"])]
    assert matches == [{"words": ids, "anchor": "w136", "gloss": gloss}]
    assert all("gloss" not in layer["words"][wid] for wid in ids)


@pytest.mark.parametrize(
    "wid,gloss",
    [
        ("w066", "proroka"),
        ("w096", "okolicach"),
        ("w098", "w wieku"),
        ("w104", "o którym"),
        ("w105", "dokładnie się dowiedział"),
        ("w120", "Ramie"),
    ],
)
def test_selected_polish_direct_realizations(wid, gloss):
    # Pins this contextual choice; does not ban other grammatical translations.
    assert store.raw_layer(ROOT, "pl", TEXT)["words"][wid]["gloss"] == gloss


def test_complete_partition_retains_zero_and_unchanged_frames():
    doc, layers = store.load(ROOT, TEXT)
    assert len(doc["segments"]) == 1 and len(doc["segments"][0]["words"]) == 136
    for language, direct, grouped in [("pl", 125, 10), ("en", 104, 31)]:
        layer = layers[language]
        assert interlinear.check(doc, layer) == []
        assert sum("gloss" in w for w in layer["words"].values()) == direct
        alignments = layer["segments"]["s01"]["alignments"]
        assert sum(len(a["words"]) for a in alignments if "gloss" in a) == grouped
        assert [a for a in alignments if "reason" in a] == [{"words": ["w026"], "reason": "idiom"}]
    pl = layers["pl"]["words"]
    assert [pl[w]["gloss"] for w in ["w094", "w095", "w097", "w106"]] == [
        "we",
        "wszystkich",
        "jego",
        "od",
    ]
    en = layers["en"]
    assert phrase(en, ["w029", "w030", "w031"]) == "For it will happen"
    assert phrase(en, ["w109", "w110"]) == "was fulfilled"
    assert phrase(en, ["w112", "w113"]) == "was spoken"


def test_future_participle_keeps_impersonal_flag_and_pending_disagreement():
    raw = store.core(ROOT, TEXT)
    doc, _ = store.load(ROOT, TEXT)
    word = raw["segments"][0]["words"][28]
    assert word["lemma"] == "sum" and word["morph"] == MORPH
    assert word["substantive"] is True and "head" not in word
    assert doc["segments"][0]["words"][28]["analysis"] == {
        "confidence": "high",
        "sources": ["editorial", "collatinus"],
        "review": "pending",
    }
    assert raw["segments"][0]["words"][26]["morph"]["tense"] == "fut"
    assert raw["segments"][0]["words"][26]["morph"]["mood"] == "ind"
    assert raw["segments"][0]["words"][127]["morph"]["mood"] == "part"
    rows = json.loads((ROOT / "build_reader/registry/morphology.json").read_bytes())
    assert rows.count(MORPH) == 1


@pytest.mark.parametrize(
    "text,wid,head",
    [
        ("litaniae.sanctissimi-nominis-iesu", "w084", "w085"),
        ("proprium.dominica-in-albis-postcommunio", "w021", "w017"),
        ("proprium.purificatio-beatae-mariae-virginis-postcommunio", "w026", "w022"),
    ],
)
def test_attributive_future_adjectives_are_not_mechanically_reparsed(text, wid, head):
    words = [w for s in store.core(ROOT, text)["segments"] for w in s.get("words", [])]
    word = next(w for w in words if w["id"] == wid)
    assert word["lemma"] == "futurus" and word["morph"]["pos"] == "adj" and word["head"] == head


@pytest.mark.parametrize(
    "language,prefix", [("pl", "Ewangelia formularza"), ("en", "The Gospel of")]
)
def test_prose_provenance_is_current_but_still_working(language, prefix):
    raw = store.core(ROOT, TEXT)
    layer = store.raw_layer(ROOT, language, TEXT)
    assert layer["about"].startswith(prefix)
    sites = json.loads((ROOT / f"languages/{language}/translation-provenance.json").read_bytes())[
        "sites"
    ]
    sites = [s for s in sites if s["text"] == TEXT]
    assert len(sites) == 1
    site = sites[0]
    assert site["source_sha256"] == canonical_hash(source_payload(raw["segments"][0]))
    assert site["target_sha256"] == canonical_hash(layer["segments"]["s01"]["translation"])
    assert (site["origin"], site["review"], site["familiar_core"]) == (
        "working-unsettled",
        "working",
        False,
    )
    if language == "pl":
        assert (
            site["target_sha256"]
            == "1000dddfac276ad205da19d9b7a32b9bfe5f1e734704f267b848206ef533ced4"
        )
    else:
        prose = layer["segments"]["s01"]["translation"]
        assert "the time he had carefully ascertained from the Magi" in prose
        assert "Out of Egypt I have called My Son" in prose
        assert (
            "Rachel wept for her children, and she refused to be consoled, because they are no more"
            in prose
        )


def test_selected_latin_ritual_and_complete_boundary_are_unchanged():
    raw = store.core(ROOT, TEXT)
    assert (
        bb.digest(bb.selected_text(raw))
        == "35c4347aecbc738d59659f48e7c1d847b941d9014c2f56a27847dc9476dd3f3e"
    )
    assert (raw["segments"][0]["speaker"], raw["segments"][0]["voice"], raw["sung"]) == (
        "sacerdos",
        "clara",
        False,
    )


def test_raw_gospel_is_exact_direct_line_61_not_its_framing():
    bound = raw_binding.resolve_binding(ROOT / "witnesses" / TEXT / "do.txt", ROOT)
    assert bound is not None
    source = bound.source
    assert source["binding_id"] == BINDING
    assert source["binding"]["evidence"] == [
        {"archive": BINDING, "first": 61, "last": 61, "section": "Evangelium", "section_line": 58}
    ]
    assert source["binding"]["reading"] == [{"archive": BINDING, "first": 61, "last": 61}]
    assert source["binding"]["references"] == []
    assert source["archives"] == {
        BINDING: {
            "upstream": "web/www/missa/Latin/Sancti/12-28.txt",
            "revision": "44667ff518b8ff1439780470828b39714f5306a2",
            "path": "witnesses/raw/do-12-28.txt",
            "sha256": "28f4f262a6e8471df524e2905b681b7b3a59485e37fea5c69060e34764533cd5",
        }
    }
    tokens = bound.text.split()
    assert len(tokens) == 136
    assert {i: tokens[i - 1] for i in [4, 9, 17, 45, 97, 115, 116]} == {
        4: "Angelus",
        9: "Joseph,",
        17: "ejus,",
        45: "ejus",
        97: "ejus,",
        115: "Jeremíam",
        116: "Prophetam",
    }


def test_apparatus_records_seven_restored_accidentals_and_all_previous_readings():
    directory = ROOT / "witnesses" / TEXT
    app = json.loads((directory / "apparatus.json").read_bytes())
    readings = {
        (e["at"], name): value for e in app["adjudicated"] for name, value in e["witnesses"].items()
    }
    assert readings == {
        ("w004", "mr"): "Angelus",
        ("w004", "do"): "Angelus",
        ("w009", "do"): "Joseph,",
        ("w014", "do"): "Púerum",
        ("w016", "do"): "Matrem",
        ("w017", "do"): "ejus,",
        ("w024", "do"): "ibi,",
        ("w035", "do"): "Púerum",
        ("w042", "do"): "Púerum",
        ("w044", "do"): "Matrem",
        ("w045", "do"): "ejus",
        ("w075", "do"): "videns,",
        ("w092", "do"): "Béthlehem",
        ("w097", "do"): "ejus,",
        ("w103", "do"): "tempus,",
        ("w110", "do"): "est,",
        ("w115", "do"): "Jeremíam",
        ("w116", "do"): "Prophetam",
        ("w123", "do"): "plorátus",
    }
    assert app["summary"] == {
        "entries": 18,
        "classes": ["capital-accent", "capitalization", "orthography", "punctuation"],
    }
    assert collate(store.load(ROOT, TEXT)[0], directory)[0] == []
    assert all(
        len(load_witness(directory / f"{name}.txt")[1].split()) == 136 for name in ["mr", "do"]
    )


def test_local_source_identity_is_current_comparison_not_historical_genesis():
    graph = json.loads((ROOT / "bibliography/graph.json").read_bytes())
    uses = [u for u in graph["uses"] if u.get("address", {}).get("text") == TEXT]
    witnesses = [w for w in graph["witnesses"] if w["text"] == TEXT]
    cols = [c for c in graph["collations"] if c["text"] == TEXT]
    assert (len(uses), len(witnesses), len(cols)) == (2, 2, 1)
    mr = next(u for u in uses if u["id"].endswith(".mr1962"))
    do = next(u for u in uses if u["id"].endswith(".do44667ff"))
    assert mr["role"] == "direct_approved_print" and do["role"] == "derived_digital_collation_aid"
    assert mr["locator"]["printed"] == "p. 28" and mr["locator"]["scan"] == "leaf n107 / PDF p. 108"
    assert "Benziger 1962" in mr["claim"] and "No conclusion is expanded" in mr["claim"]
    assert "direct body line 61" in do["locator"]["section"]
    for witness in witnesses:
        assert witness["review"] == {"status": "pending"}
        assert witness["coverage"] == {"kind": "full"}
        raw = (ROOT / "witnesses" / TEXT / (witness["transcription"] + ".txt")).read_text()
        assert witness["transcription_sha256"] == bb.transcript_digest(raw)
        if witness["transcription"] == "mr":
            assert "Benziger" in raw and "Editio iuxta typicam" in raw
            assert (
                "does not establish the historical transcription" in witness["independence_basis"]
            )
            assert "# transcribed: 2026-08-31" in raw and "# recollated: 2026-09-25" in raw
    app = json.loads((ROOT / "witnesses" / TEXT / "apparatus.json").read_bytes())
    assert cols[0]["apparatus_sha256"] == bb.digest(app)
    assert cols[0]["review"] == {"status": "pending"}
    core = store.core(ROOT, TEXT)
    for text in [core["editorial"]["notes"], core["editorial"]["source"]["method"]]:
        assert "Benziger" in text and "typical-edition" not in text
