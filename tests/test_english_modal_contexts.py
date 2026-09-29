"""Modal renderings retain person, force and the surrounding complement."""

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.layers import enrich_layer, expand_core
from checks.english import check
from checks.interlinear import check as check_interlinear
from checks.language_packs import check_layer
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    (
        "dominica-ii-passionis-evangelium",
        "s08",
        [
            (["w090", "w091"], "w091", "could you not"),
            (["w092", "w093", "w094"], "w094", "watch one hour"),
        ],
        {},
    ),
    (
        "dominica-ii-passionis-evangelium",
        "s20",
        [
            (["w294", "w295"], "w295", "I cannot"),
        ],
        {"w296": "ask"},
    ),
    (
        "dominica-ii-passionis-evangelium",
        "s82",
        [
            (["w1228", "w1229"], "w1229", "cannot"),
        ],
        {},
    ),
    (
        "dominica-iii-post-epiphaniam-epistola",
        "s01",
        [
            (["w024", "w025"], "w025", "it is possible"),
        ],
        {},
    ),
    ("dominica-xxiii-post-pentecosten-epistola", "s01", [], {"w072": "He can"}),
    (
        "dominica-xxiv-post-pentecosten-evangelium",
        "s01",
        [
            (["w134", "w135"], "w135", "it is possible"),
        ],
        {},
    ),
    ("sancti-ioachim-confessoris-epistola", "s01", [], {"w051": "do"}),
    (
        "sancti-stephani-protomartyris-epistola",
        "s01",
        [
            (["w040", "w041"], "w041", "they could not"),
        ],
        {},
    ),
    (
        "septem-dolorum-beatae-mariae-virginis-sequentia",
        "s06",
        [
            (["w053", "w054"], "w054", "would not"),
            (["w056", "w057", "w058"], "w058", "on beholding Christ’s Mother"),
        ],
        {},
    ),
    (
        "vigilia-pentecostes-evangelium",
        "s01",
        [
            (["w032", "w033"], "w033", "cannot"),
        ],
        {},
    ),
]


def load(name):
    core = json.loads((ROOT / f"texts/proprium/{name}.json").read_text())
    path = ROOT / f"languages/en/texts/proprium/{name}.json"
    return core, json.loads(path.read_text()), path


@pytest.mark.parametrize("name,sid,groups,direct", CASES)
def test_contextual_modal_realizations_are_complete(name, sid, groups, direct):
    core, layer, path = load(name)
    alignments = layer["segments"][sid].get("alignments", [])
    for words, anchor, gloss in groups:
        assert {"words": words, "anchor": anchor, "gloss": gloss} in alignments
    assert {wid: layer["words"][wid]["gloss"] for wid in direct} == direct
    words = next(s["words"] for s in core["segments"] if s["id"] == sid)
    coverage = [w["id"] for w in words if "gloss" in layer["words"][w["id"]]]
    coverage += [wid for group in alignments for wid in group["words"]]
    assert Counter(coverage) == Counter(w["id"] for w in words)
    assert not check_layer(core, layer, path)
    doc, glosses = expand_core(core), enrich_layer(core, layer)
    assert not check(doc, glosses)
    assert not check_interlinear(doc, glosses)


def test_sorrows_contemplation_retains_mother_and_son_without_approval():
    name = "septem-dolorum-beatae-mariae-virginis-sequentia"
    core, layer, _ = load(name)
    wording = layer["segments"]["s06"]["translation"]
    assert (
        wording
        == "Who would not be saddened on contemplating Christ’s Mother suffering with her Son?"
    )
    segment = next(s for s in core["segments"] if s["id"] == "s06")
    contemplari = next(w for w in segment["words"] if w["id"] == "w058")
    assert contemplari["lemma"] == "contemplor"
    assert contemplari["morph"]["mood"] == "inf"
    provenance = json.loads((ROOT / "languages/en/translation-provenance.json").read_text())
    site = next(s for s in provenance["sites"] if s["text"] == core["id"] and s["segment"] == "s06")
    assert site["target_sha256"] == canonical_hash(wording)
    assert site["source_sha256"] == canonical_hash(source_payload(segment))
    assert (site["origin"], site["review"]) == ("working-unsettled", "working")


@pytest.mark.parametrize(
    "name,sid,first,second",
    [
        ("dominica-ii-passionis-evangelium", "s82", "w1228", "w1229"),
        ("vigilia-pentecostes-evangelium", "s01", "w032", "w033"),
    ],
)
def test_reintroducing_a_real_duplicate_negation_is_rejected(name, sid, first, second):
    core, layer, path = load(name)
    broken = deepcopy(layer)
    broken["segments"][sid]["alignments"] = [
        g for g in broken["segments"][sid]["alignments"] if g["words"] != [first, second]
    ]
    broken["words"][first]["gloss"] = "not"
    broken["words"][second]["gloss"] = "cannot"
    assert not check_layer(core, broken, path)
    errors = check(expand_core(core), enrich_layer(core, broken))
    assert len(errors) == 1 and f"{first}–{second}" in errors[0]
    assert "negation twice" in errors[0]
    assert not check(expand_core(core), enrich_layer(core, layer))
