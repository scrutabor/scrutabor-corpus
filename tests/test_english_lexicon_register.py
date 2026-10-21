"""Shared English word help is contemporary outside named quotations."""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
# Deliberately lexical, not an -est/-eth suffix heuristic: Latin prodest,
# the noun art and modern superlatives are not old English verb forms.
# This finite guard supplements, rather than replaces, contextual review.
OLDER_WORDS = re.compile(
    r"\b(?:thou|thee|thy|thine|thyself|hast|hath|doth|dost|saith|didst|wouldst"
    r"|shouldst|mayst|mayest|mightest|canst|shalt|unto|whence|thence|wherefore|ye)\b",
    re.I,
)
# Exact field values, never entire entries or a prose-dependent inventory.
TRADITIONAL_EXPLANATIONS = {
    ("in", "senses", 1): "into, to (traditional English: unto)",
    ("tu", "senses", 1): "thou (traditional English)",
    ("tuus", "senses", 0): "your (traditional English: thy)",
    ("tuus", "senses", 1): "yours (traditional English: thine)",
    ("venter", "note", None): (
        "In the received English of the Ave María the word is “womb”: “fruit of thy womb.”"
    ),
}


def reader_fields(entries):
    for lemma, entry in entries.items():
        for field in ("senses", "derivatives"):
            for index, value in enumerate(entry.get(field, [])):
                yield (lemma, field, index), value
        if "note" in entry:
            yield (lemma, "note", None), entry["note"]


def older_word_fields(entries):
    return [
        key
        for key, value in reader_fields(entries)
        if OLDER_WORDS.search(value) and TRADITIONAL_EXPLANATIONS.get(key) != value
    ]


def load_entries():
    return json.loads((ROOT / "languages/en/lexicon.json").read_text())["entries"]


def test_all_english_dictionary_fields_use_the_declared_register():
    entries = load_entries()
    assert entries, "the dictionary register check must not pass on zero entries"
    assert not older_word_fields(entries)


def test_traditional_explanations_are_explicit_and_current():
    fields = dict(reader_fields(load_entries()))
    assert TRADITIONAL_EXPLANATIONS
    for key, expected in TRADITIONAL_EXPLANATIONS.items():
        assert fields[key] == expected


@pytest.mark.parametrize(
    "lemma,field,index,value",
    [
        ("exinde", "senses", 1, "thence, from there"),
        ("martyr", "note", None, "A martyr bears witness even unto death."),
        ("per", "senses", 1, "throughout, unto"),
        ("quapropter", "senses", 0, "wherefore"),
        ("sabacthani", "senses", 0, "hast Thou forsaken Me"),
        ("saeculum", "note", None, "unto the ages of ages"),
        ("unde", "senses", 0, "whence, from where"),
        ("unde", "senses", 1, "wherefore, and so"),
        ("tu", "note", None, "Thou is the only form used."),
        ("new-entry", "derivatives", 0, "thence"),
    ],
)
def test_unmarked_old_wording_is_rejected(lemma, field, index, value):
    entry = {field: value if index is None else ["modern"] * index + [value]}
    assert older_word_fields({lemma: entry}) == [(lemma, field, index)]


@pytest.mark.parametrize("key,value", TRADITIONAL_EXPLANATIONS.items())
def test_only_the_exact_traditional_explanation_is_exempt(key, value):
    lemma, field, index = key
    entry = {field: value if index is None else ["modern"] * index + [value]}
    assert older_word_fields({lemma: entry}) == []
    altered = value + " Thou."
    entry[field] = altered if index is None else ["modern"] * index + [altered]
    assert older_word_fields({lemma: entry}) == [key]


@pytest.mark.parametrize("value", ["farthest", "art of healing", "prodest", "forever and ever"])
def test_modern_words_and_latin_examples_are_not_misclassified(value):
    assert older_word_fields({"test": {"senses": [value]}}) == []
