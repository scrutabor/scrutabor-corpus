"""Reverse only the exact reviewed Quam explanation, never arbitrary notes."""

from copy import deepcopy

QUAM_GLOSSES = {"pl": "którą", "en": "which"}
QUAM_NOTES = {
    "pl": "Quam nawiązuje do poprzednich słów: może odnosić się do wspomnianej równości "
    "majestatu albo do Bóstwa. Oba łacińskie rzeczowniki — aequalitas i Deitas — są "
    "rodzaju żeńskiego.",
    "en": "Quam links this praise to what precedes. It may refer to the equality in "
    "majesty just mentioned or to the earlier Godhead: both aequalitas and Deitas "
    "are feminine nouns.",
}


def restore_note_layer(layer, language):
    result = deepcopy(layer)
    assert result["text"] == "ordinarium.praefatio-sanctissimae-trinitatis"
    assert result["language"] == language
    word = result["words"]["w085"]
    assert list(word) == ["gloss", "explanation"]
    assert word == {"gloss": QUAM_GLOSSES[language], "explanation": QUAM_NOTES[language]}
    del word["explanation"]
    return result


def restore_note_core(core):
    result = deepcopy(core)
    assert result["id"] == "ordinarium.praefatio-sanctissimae-trinitatis"
    declarations = result["localization"]["explanations"]
    assert list(declarations) == ["w064", "w085"]
    assert declarations["w085"] == {}
    del declarations["w085"]
    return result
