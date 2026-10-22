"""The five shared deponent notes describe the usual finite-form pattern."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEMMAS = ("laetor", "mereor", "miseror", "pervagor", "suspicor")
EXPECTED = {
    "pl": (
        "Czasownik deponens: formy osobowe zwykle mają postać bierną, "
        "lecz znaczenie czynne lub zwrotne."
    ),
    "en": (
        "A deponent verb: its finite forms normally have passive endings "
        "with an active or reflexive meaning."
    ),
}


@pytest.mark.parametrize("language", ("pl", "en"))
@pytest.mark.parametrize("lemma", LEMMAS)
def test_deponent_lemma_note_qualifies_the_finite_form_pattern(language, lemma):
    entries = json.loads((ROOT / "languages" / language / "lexicon.json").read_text())["entries"]
    assert entries[lemma]["note"] == EXPECTED[language]
    neutral = json.loads((ROOT / "lexicon" / "lemmata.json").read_text())["entries"]
    assert neutral[lemma]["localization"]["note"] is True
