"""Short dictionary cards retain the ordinary senses needed by their texts."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("lemma", "sense"),
    [
        ("actus", "act, deed, activity"),
        ("aedificatio", "building, construction"),
        ("cathedra", "chair, seat"),
        ("cautio", "bond, written undertaking"),
        ("columna", "column, pillar"),
        ("comparo", "compare, liken"),
        ("concilio", "win favor for, commend"),
        ("concilium", "assembly, council"),
        ("concludo", "enclose, confine"),
        ("congero", "heap up, pile on"),
        ("consisto", "stand, take a position"),
        ("constituo", "appoint, ordain"),
        ("constitutio", "establishment, arrangement"),
        ("consuetudo", "custom, habit"),
        ("continentia", "self-control, restraint"),
        ("contineo", "hold together, sustain"),
        ("contraho", "incur, bring upon oneself"),
        ("contrarius", "opposite, contrary"),
        ("corrumpo", "destroy, ruin"),
        ("cultus", "worship, veneration"),
        ("cura", "care, attention"),
        ("curatio", "healing, medical treatment"),
        ("defensio", "defense, protection"),
        ("delectatio", "delight, pleasure, enjoyment"),
        ("devoro", "devour, swallow"),
        ("fideliter", "faithfully, loyally"),
        ("genus", "race, people, stock"),
        ("idoneus", "suitable, fitting"),
        ("inaestimabilis", "inestimable, beyond measure"),
    ],
)
def test_ordinary_sense_is_not_displaced_by_a_specialized_continuation(lemma, sense):
    entries = json.loads((ROOT / "languages/en/lexicon.json").read_text())["entries"]
    assert sense in entries[lemma]["senses"]


def test_actus_does_not_present_a_linear_length_as_the_entire_land_measure():
    entries = json.loads((ROOT / "languages/en/lexicon.json").read_text())["entries"]
    assert "a Roman land measure" in entries["actus"]["senses"]
    assert not any("120 ft." in sense for sense in entries["actus"]["senses"])


def test_new_senses_have_individually_identified_lexical_evidence():
    graph = json.loads((ROOT / "bibliography/graph.json").read_text())
    for lemma in (
        "actus",
        "aedificatio",
        "cathedra",
        "cautio",
        "columna",
        "comparo",
        "concilio",
        "concilium",
        "concludo",
        "congero",
        "consisto",
        "constituo",
        "constitutio",
        "consuetudo",
        "continentia",
        "contineo",
        "contraho",
        "contrarius",
        "corrumpo",
        "cultus",
        "cura",
        "curatio",
        "defensio",
        "delectatio",
        "devoro",
        "fideliter",
        "genus",
        "idoneus",
        "inaestimabilis",
    ):
        use = next(
            row for row in graph["uses"] if row["id"] == f"use.lemma.{lemma}.lewis-short.1879"
        )
        assert use["role"] == "lexical_support"
        assert use["address"] == {"kind": "lemma", "lemma": lemma}
        assert use["evidence_sha256"]
        assert "Perseus TEI entry" in use["locator"]["section"]
