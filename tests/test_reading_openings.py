"""Keep the temporal reading openings faithful and naturally ordered."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import emit, store
from checks import interlinear, translation_provenance

ROOT = Path(__file__).resolve().parents[1]
OPENINGS = [
    "annuntiatio-beatae-mariae-virginis-epistola",
    "commemoratio-omnium-fidelium-defunctorum-missa-ii-epistola",
    "commemoratio-omnium-fidelium-defunctorum-missa-iii-epistola",
    "dedicatio-archibasilicae-sanctissimi-salvatoris-epistola",
    "dedicatio-sancti-michaelis-archangeli-epistola",
    "omnium-sanctorum-epistola",
    "sancti-matthiae-apostoli-epistola",
    "sancti-petri-et-pauli-apostolorum-epistola",
    "sancti-stephani-protomartyris-epistola",
    "sanctissimi-nominis-iesu-epistola",
    "sanctorum-innocentium-martyrum-epistola",
    "vigilia-pentecostes-epistola",
]
PAIR = {"words": ["w002", "w003"], "anchor": "w002", "gloss": "those days"}


@pytest.mark.parametrize("name", OPENINGS)
def test_polish_opening_keeps_correct_direct_inflection(name):
    text = "proprium." + name
    core = store.core(ROOT, text)
    words = core["segments"][0]["words"][:3]
    assert [w["lemma"] for w in words] == ["in", "dies", "ille"]
    assert words[0]["head"] == "w002"
    assert words[0]["morph"]["governs"] == "abl"
    assert all(words[i]["morph"]["case"] == "abl" for i in (1, 2))
    assert all(words[i]["morph"]["number"] == "pl" for i in (1, 2))
    layer = store.raw_layer(ROOT, "pl", text)
    assert layer["words"]["w001"]["gloss"].lower() == "w"
    assert layer["words"]["w002"]["gloss"] == "dniach"
    assert layer["words"]["w003"]["gloss"] == "owych"
    assert not any(
        set(a["words"]) & {"w001", "w002", "w003"} for a in interlinear.alignments_for(layer, "s01")
    )


@pytest.mark.parametrize("name", OPENINGS)
def test_english_opening_keeps_the_smallest_temporal_pair(name):
    layer = store.raw_layer(ROOT, "en", "proprium." + name)
    assert layer["words"]["w001"]["gloss"].lower() == "in"
    groups = [
        a
        for a in interlinear.alignments_for(layer, "s01")
        if set(a["words"]) & {"w001", "w002", "w003"}
    ]
    assert groups == [PAIR]
    assert all("gloss" not in layer["words"][w] for w in PAIR["words"])


@pytest.mark.parametrize("name", OPENINGS)
@pytest.mark.parametrize("language", ["pl", "en"])
def test_opening_layers_keep_all_providers_transport_and_prose_binding(name, language):
    text = "proprium." + name
    raw = store.core(ROOT, text)
    core, layers = store.load(ROOT, text)
    layer = layers[language]
    assert interlinear.check(core, layer) == []
    p, a, c, local = [emit.Table() for _ in range(4)]
    encoded = emit.core_artifact(core, raw, p, a, c)
    translated = emit.language_artifact(core, layer, local)
    decoded, target = emit.expand(encoded, translated, p.order, a.order, c.order, local.order)
    expected, languages = emit._strip(core, {language: layer})
    assert decoded == expected and target == languages[language]
    ledger = json.loads((ROOT / "languages" / language / "translation-provenance.json").read_text())
    rows = [r for r in ledger["sites"] if r["text"] == text and r["segment"] == "s01"]
    assert len(rows) == 1
    assert rows[0]["source_sha256"] == translation_provenance.canonical_hash(
        translation_provenance.source_payload(core["segments"][0])
    )
    assert rows[0]["target_sha256"] == translation_provenance.canonical_hash(
        layer["segments"]["s01"]["translation"]
    )


def test_exact_opening_inventory_does_not_capture_internal_day_phrases():
    found = []
    for text in store.text_ids(ROOT):
        for segment in store.core(ROOT, text)["segments"]:
            words = segment.get("words", [])
            for i in range(len(words) - 2):
                if [w["lemma"] for w in words[i : i + 3]] == ["in", "dies", "ille"]:
                    assert i == 0 and segment["id"] == "s01"
                    found.append(text)
    assert sorted(found) == sorted("proprium." + name for name in OPENINGS)


@pytest.mark.parametrize(
    "name,language,ids,glosses",
    [
        ("dominica-xxiv-post-pentecosten-evangelium", "pl", [58, 59, 60], ["w", "owe", "dni"]),
        ("dominica-xxiv-post-pentecosten-evangelium", "en", [58, 59, 60], ["in", "those", "days"]),
        ("dominica-v-post-pascha-evangelium", "en", [58, 59, 60], ["On", "that", "day"]),
        ("vigilia-pentecostes-evangelium", "en", [79, 80, 81], ["In", "that", "day"]),
    ],
)
def test_retained_temporal_counterexamples(name, language, ids, glosses):
    layer = store.raw_layer(ROOT, language, "proprium." + name)
    assert [layer["words"][f"w{i:03}"]["gloss"] for i in ids] == glosses


@pytest.mark.parametrize("name", ["omnium-sanctorum-epistola", "vigilia-pentecostes-epistola"])
def test_real_shared_provider_loss_and_duplication_are_rejected(name):
    core, layers = store.load(ROOT, "proprium." + name)
    layer = layers["en"]
    assert interlinear.check(core, layer) == []
    lost = deepcopy(layer)
    lost["segments"]["s01"]["alignments"] = [
        a for a in lost["segments"]["s01"]["alignments"] if a != PAIR
    ]
    assert len([e for e in interlinear.check(core, lost) if "exactly one" in e]) == 2
    doubled = deepcopy(layer)
    doubled["words"]["w003"]["gloss"] = "those"
    assert any("w003" in e and "exactly one" in e for e in interlinear.check(core, doubled))
