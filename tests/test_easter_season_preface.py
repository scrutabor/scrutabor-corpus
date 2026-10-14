"""Separate Easter night, octave day and the later seasonal Preface."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import store
from build_reader.bibliography_bindings import digest, selected_text
from checks import collate, interlinear, syntax

ROOT = Path(__file__).resolve().parents[1]
TEXT = "ordinarium.praefatio-paschalis"
SUNDAYS = [
    "dominica-in-albis",
    "dominica-ii-post-pascha",
    "dominica-iii-post-pascha",
    "dominica-iv-post-pascha",
    "dominica-v-post-pascha",
]


def test_seasonal_latin_has_no_inserted_day_night_or_tempore():
    core = store.core(ROOT, TEXT)
    words = core["segments"][0]["words"]
    assert len(words) == 65
    assert [w["form"] for w in words[14:19]] == [
        "in",
        "hoc",
        "potíssimum",
        "gloriósius",
        "prædicáre",
    ]
    assert words[15]["morph"] == {
        "pos": "pron",
        "case": "abl",
        "gender": "n",
        "number": "sg",
    }
    assert words[14]["head"] == "w016"
    assert words[-1]["form"] == "dicéntes"
    assert core["segments"][0]["speaker"] == "sacerdos"


@pytest.mark.parametrize("slug", SUNDAYS)
def test_later_sundays_reference_seasonal_not_octave_wording(slug):
    doc = json.loads((ROOT / f"formularies/temporale/{slug}.json").read_text())
    assert [c["text"] for c in doc["components"] if c["role"] == "praefatio"] == [TEXT]


@pytest.mark.parametrize(
    "slug,suffix",
    [("dominica-resurrectionis", "in-die"), ("vigilia-paschalis", "in-nocte")],
)
def test_day_and_night_formularies_keep_their_own_variants(slug, suffix):
    doc = json.loads((ROOT / f"formularies/temporale/{slug}.json").read_text())
    assert [c["text"] for c in doc["components"] if c["role"] == "praefatio"] == [
        TEXT + "-" + suffix
    ]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_both_language_layers_cover_exactly_the_seasonal_words(language):
    core = store.core(ROOT, TEXT)
    layer = store.raw_layer(ROOT, language, TEXT)
    assert len(layer["words"]) == 65
    assert interlinear.check(core, layer) == []
    body = layer["segments"]["s01"]["translation"]
    assert ("w tym czasie" if language == "pl" else "at this time") in body
    assert ("tego dnia" if language == "pl" else "on this day") not in body


def test_both_printed_witnesses_support_the_selected_body():
    core = store.core(ROOT, TEXT)
    errors, warnings, counts = collate.collate(core, ROOT / "witnesses" / TEXT)
    assert errors == warnings == []
    assert counts["words"] == 65 and counts["witnesses"] == 2
    assert counts["substantive_variants"] == 0
    graph = json.loads((ROOT / "bibliography/graph.json").read_text())
    row = next(r for r in graph["collations"] if r["text"] == TEXT)
    assert row["selected_text_sha256"] == digest(selected_text(core))
    assert row["review"] == {"status": "pending"}


def test_wrong_occasion_and_preposition_head_fail_existing_checks():
    core = store.core(ROOT, TEXT)
    folder = ROOT / "witnesses" / TEXT
    assert collate.collate(core, folder)[0] == []
    damaged = deepcopy(core)
    damaged["segments"][0]["words"][15]["form"] = "hac"
    assert collate.collate(damaged, folder)[0]
    damaged = deepcopy(core)
    damaged["segments"][0]["words"][14]["head"] = "w025"
    assert syntax.check(damaged)
    assert syntax.check(core) == []
