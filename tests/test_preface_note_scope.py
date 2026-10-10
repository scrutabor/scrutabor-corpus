"""Reader explanations retain secure grammar and qualified lexical senses."""

import hashlib
import json
from copy import deepcopy

import pytest
from preface_note_fixture import restore_note_core, restore_note_layer

from checks.layout import CORPUS, formatted

REL = "texts/ordinarium/praefatio-sanctissimae-trinitatis.json"
BEFORE = {
    "core": "66dc4e76856e31f4d597acf31fb019f36e90c64bcb4e8965b50d017b8af7ca3a",
    "pl": "6649dbb68a59c21042f5478e2a6303a85692688f8b07dd95f5814a89035231b8",
    "en": "b8292183246c06e2bd5e1980ca58240beed0e3703c3dfee6f81d6fce49dc07c1",
}


def load(language):
    return json.loads((CORPUS / REL).read_text()), json.loads(
        (CORPUS / "languages" / language / REL).read_text()
    )


def assert_exact_note_delta(core, layer, language):
    assert hashlib.sha256(formatted(restore_note_core(core)).encode()).hexdigest() == BEFORE["core"]
    assert (
        hashlib.sha256(formatted(restore_note_layer(layer, language)).encode()).hexdigest()
        == BEFORE[language]
    )


@pytest.mark.parametrize("language", ["pl", "en"])
def test_only_the_known_explanation_and_declaration_are_added(language):
    assert_exact_note_delta(*load(language), language)


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize(
    "damage",
    [
        "missing-note",
        "changed-note",
        "wrong-gloss",
        "extra-word-help",
        "word-key-order",
        "missing-declaration",
        "changed-declaration",
        "extra-declaration",
        "declaration-key-order",
        "wrong-case",
        "new-confidence",
        "other-note",
        "other-verse",
        "word-order",
    ],
)
def test_exact_note_inverse_rejects_damaged_payload_after_a_healthy_control(language, damage):
    core, layer = load(language)
    assert_exact_note_delta(core, layer, language)
    core, layer = deepcopy(core), deepcopy(layer)
    word = layer["words"]["w085"]
    declarations = core["localization"]["explanations"]
    neutral_word = next(
        w for s in core["segments"] for w in s.get("words", []) if w["id"] == "w085"
    )
    if damage == "missing-note":
        del word["explanation"]
    elif damage == "changed-note":
        word["explanation"] = "Quam has only one possible antecedent."
    elif damage == "wrong-gloss":
        word["gloss"] = "because"
    elif damage == "extra-word-help":
        word["note"] = "Unexpected."
    elif damage == "word-key-order":
        layer["words"]["w085"] = dict(reversed(list(word.items())))
    elif damage == "missing-declaration":
        del declarations["w085"]
    elif damage == "changed-declaration":
        declarations["w085"]["unexpected"] = True
    elif damage == "extra-declaration":
        declarations["w086"] = {}
    elif damage == "declaration-key-order":
        core["localization"]["explanations"] = dict(reversed(list(declarations.items())))
    elif damage == "wrong-case":
        neutral_word["morph"]["case"] = "nom"
    elif damage == "new-confidence":
        neutral_word["analysis"] = {"confidence": "high"}
    elif damage == "other-note":
        layer["words"]["w064"]["explanation"] += " Changed."
    elif damage == "other-verse":
        layer["segments"]["s07"]["translation"] += " Changed."
    else:
        layer["words"]["w085"] = layer["words"].pop("w085")
    with pytest.raises((AssertionError, KeyError)):
        assert_exact_note_delta(core, layer, language)


def assert_aeternus_card(entry):
    assert entry == {
        "senses": [
            "eternal, everlasting",
            "eternity (used as a noun)",
            "forever (adverbial uses, including in aeternum)",
        ],
        "derivatives": ["eternity"],
    }


def aeternus_card():
    return json.loads((CORPUS / "languages/en/lexicon.json").read_text())["entries"]["aeternus"]


def test_aeternus_keeps_adjectival_nominal_and_adverbial_uses_distinct():
    assert_aeternus_card(aeternus_card())
    neutral = json.loads((CORPUS / "lexicon/lemmata.json").read_text())["entries"]["aeternus"]
    assert neutral["pos"] == "adj"


@pytest.mark.parametrize("damage", ["adjective", "noun-scope", "adverb-scope", "derivative"])
def test_aeternus_scope_regressions_begin_with_a_healthy_card(damage):
    card = aeternus_card()
    assert_aeternus_card(card)
    if damage == "adjective":
        card["senses"][0] = "temporal, passing"
    elif damage == "noun-scope":
        card["senses"][1] = "always a noun meaning eternity"
    elif damage == "adverb-scope":
        card["senses"][2] = "forever (only in the phrase in aeternum)"
    else:
        card["derivatives"] = []
    with pytest.raises(AssertionError):
        assert_aeternus_card(card)
