"""Punctuation mutations and valid cross-segment quotations."""

import pytest

from checks.translation_punctuation import check


def layer(language, *translations):
    return {
        "text": "proprium.example",
        "language": language,
        "segments": {
            f"s{index:02d}": {"translation": text} for index, text in enumerate(translations, 1)
        },
    }


@pytest.mark.parametrize("text", ["((Alleluja.)", "(Alleluja.))", "Resurrection.”", "([)]"])
def test_unmatched_delimiters_fail(text):
    assert check(layer("en", text))


@pytest.mark.parametrize("language,opening", [("pl", "„"), ("en", "“")])
def test_a_quotation_can_continue_across_verses(language, opening):
    assert check(layer(language, opening + "One", "two.”")) == []
    assert check(layer(language, opening + "One", "two."))


def test_apostrophes_nested_parentheses_and_guillemets_are_not_corruption():
    assert check(layer("en", "John’s words, the disciples’ answer: «(Alleluia (twice).)»")) == []


def test_authored_and_enriched_language_keys_agree():
    doc = layer("pl", "„Pokój.”")
    doc["lang"] = doc.pop("language")
    assert check(doc) == []


def test_balanced_but_duplicated_importer_parentheses_fail():
    assert check(layer("pl", "((O. W. Alleluja.))"))
    assert check(layer("pl", "(O. W. Alleluja.)")) == []
    assert check(layer("en", "(A response (twice))")) == []


@pytest.mark.parametrize("separator", [",", ";", ":"])
def test_separator_cannot_lead_a_segment_after_a_rubric(separator):
    assert check(layer("pl", "wszelkie imię", separator + " aby każde kolano"))
    assert check(layer("pl", "wszelkie imię" + separator, "aby każde kolano")) == []
    assert check(layer("en", "… and the following words")) == []
