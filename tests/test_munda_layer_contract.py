"""Munda keeps complete language topology and readable explanatory prose."""

import copy
import json
from pathlib import Path

import pytest

from build_reader import store
from checks.language_packs import check_layer
from checks.prose import check as check_prose

ROOT = Path(__file__).resolve().parents[1]
TEXT = "ordinarium.munda-cor-meum"


def subject(language):
    core = store.core(ROOT, TEXT)
    layer = store.raw_layer(ROOT, language, TEXT)
    filename = store.layer_path(ROOT, language, TEXT)
    return core, layer, filename


@pytest.mark.parametrize("language", ["pl", "en"])
def test_complete_munda_language_shape_and_help(language):
    core, layer, filename = subject(language)
    assert len(layer["words"]) == 34
    assert check_layer(core, layer, filename) == []
    assert check_prose(layer) == []


@pytest.mark.parametrize(
    "language,wid,key,phrase",
    [
        ("pl", "w015", "note", "imiesłowowej. W obu"),
        ("pl", "w019", "explanation", "proszącemu. Nie oznacza"),
        ("en", "w015", "note", "either reading. The phrase"),
        ("en", "w021", "explanation", "to cleanse. It does not"),
    ],
)
def test_actual_word_help_rejects_semicolon_and_accepts_restoration(language, wid, key, phrase):
    _, layer, _ = subject(language)
    assert check_prose(layer) == []
    before = layer["words"][wid][key]
    assert phrase in before
    layer["words"][wid][key] = before.replace(phrase, phrase.replace(". ", "; "))
    errors = check_prose(layer)
    assert any(f"{wid}.{key}.{language}" in error and "semicolon" in error for error in errors)
    layer["words"][wid][key] = before
    assert check_prose(layer) == []


@pytest.mark.parametrize("language", ["pl", "en"])
def test_grouped_members_still_require_their_empty_language_record(language):
    core, layer, filename = subject(language)
    assert check_layer(core, layer, filename) == []
    assert layer["words"]["w002"] == {}
    before = copy.deepcopy(layer["words"])
    del layer["words"]["w002"]
    assert any("word coverage or order" in error for error in check_layer(core, layer, filename))
    layer["words"] = before
    assert check_layer(core, layer, filename) == []


@pytest.mark.parametrize("language", ["pl", "en"])
def test_munda_stays_in_the_neutral_manifest_position(language):
    manifest = json.loads((ROOT / "languages" / language / "manifest.json").read_bytes())
    texts = manifest["texts"]
    assert texts.count(TEXT) == 1
    expected = [tid for tid in store.text_ids(ROOT) if tid in set(texts)]
    assert texts == expected
    moved = [tid for tid in texts if tid != TEXT] + [TEXT]
    assert moved != expected
    moved.remove(TEXT)
    moved.insert(expected.index(TEXT), TEXT)
    assert moved == expected


def assert_isaiah_witness_scope(explanation):
    assert explanation.startswith("The Latin text of Isaiah 6:6–7"), "Latin witness scope"
    for detail in ("seraph", "stone from the altar with tongs", "touching the prophet’s lips"):
        assert detail in explanation


def test_isaiah_explanation_distinguishes_the_latin_witness():
    _, target, _ = subject("en")
    assert_isaiah_witness_scope(target["words"]["w013"]["explanation"])


def test_isaiah_scope_control_rejects_unqualified_account_and_accepts_restoration():
    _, target, _ = subject("en")
    before = target["words"]["w013"]["explanation"]
    assert_isaiah_witness_scope(before)
    changed = before.removeprefix("The Latin text of ")
    assert changed != before
    with pytest.raises(AssertionError, match="Latin witness scope"):
        assert_isaiah_witness_scope(changed)
    assert_isaiah_witness_scope(before)
