"""The edition's own voice: no semicolons, no hedging.

Both rules were guarded in the reader app, which vendors this corpus — so the
sweep ran against a copy, and only after somebody re-vendored it. A semicolon
planted in an `about` paragraph passed every check this repository had, and the
hedges reached corpus prose in neither repository (census, 2026-08-19).

The exemptions are tested as carefully as the rule: a verse translation carries
the punctuation of the text it translates, and thirty-one of them do.
"""

import pytest

from checks.prose import check, check_lexicon


def a_text(**over):
    doc = {
        "id": "ordinarium.test",
        "about": {"pl": "Hymn anielski.", "en": "The angelic hymn."},
        "segments": [
            {
                "id": "s01",
                "type": "rubric",
                "narrative": {"pl": "Kapłan się pochyla.", "en": "The priest bows."},
            },
            {
                "id": "s02",
                "type": "verse",
                "translation": {"pl": "Chwała Bogu.", "en": "Glory to God."},
                "words": [
                    {
                        "id": "w001",
                        "form": "Glória",
                        "gloss": {"pl": "chwała", "en": "glory"},
                        "explanation": {"pl": "Mianownik.", "en": "Nominative."},
                    }
                ],
            },
        ],
        "editorial": {"notes": "Kept in one document; it is a dialogue."},
    }
    doc.update(over)
    return doc


class TestTheSemicolon:
    def test_a_clean_text_passes(self):
        assert check(a_text()) == []

    def test_one_in_an_about_is_refused(self):
        doc = a_text()
        doc["about"]["en"] = "The angelic hymn; the Church sings it at Mass."
        found = check(doc)
        assert found == [
            "ordinarium.test:about.en: uses a semicolon — this edition's own prose has "
            "none. Use a full stop, or an 'and'"
        ]

    def test_one_in_a_narrative_is_refused(self):
        doc = a_text()
        doc["segments"][0]["narrative"]["pl"] = "Kapłan się pochyla; potem czyta."
        assert any("s01.narrative.pl" in e for e in check(doc))

    def test_one_in_an_explanation_is_refused(self):
        doc = a_text()
        doc["segments"][1]["words"][0]["explanation"]["en"] = "Nominative; the subject."
        assert any("w001.explanation.en" in e for e in check(doc))

    def test_a_verse_translation_keeps_the_punctuation_of_its_own_text(self):
        doc = a_text()
        doc["segments"][1]["translation"]["en"] = "My soul hath hoped in the Lord; and I wait."
        assert check(doc) == []

    def test_the_editorial_block_is_not_a_readers_page(self):
        doc = a_text()
        doc["editorial"]["notes"] = "Two witnesses; both agree."
        assert check(doc) == []


class TestTheHedges:
    def test_the_polish_one_is_refused(self):
        doc = a_text()
        doc["about"]["pl"] = "Hymn odmawia się zależnie od zwyczaju."
        found = check(doc)
        assert len(found) == 1 and "hedges" in found[0]

    def test_the_english_one_is_refused(self):
        doc = a_text()
        doc["segments"][0]["narrative"]["en"] = "The priest bows, as the custom is."
        assert any("hedges" in e for e in check(doc))

    def test_either_hedge_is_refused_in_either_language(self):
        # A phrase translated word for word is the same hedge.
        doc = a_text()
        doc["about"]["en"] = "The rubric is followed zależnie od zwyczaju."
        assert any("hedges" in e for e in check(doc))


class TestTheLexicon:
    def test_a_clean_entry_passes(self):
        assert check_lexicon({"lang": "en", "entries": {"oro": {"derivatives": ["oration"]}}}) == []

    def test_a_semicolon_in_a_derivative_is_refused(self):
        found = check_lexicon(
            {"lang": "en", "entries": {"oro": {"derivatives": ["oration; oratory"]}}}
        )
        assert len(found) == 1 and "derivative" in found[0]

    def test_a_hedge_in_a_sense_is_refused(self):
        found = check_lexicon(
            {"lang": "en", "entries": {"oro": {"senses": ["to pray, as the custom is"]}}}
        )
        assert len(found) == 1 and "sense hedges" in found[0]

    def test_a_hedge_in_a_note_is_refused(self):
        found = check_lexicon(
            {"lang": "pl", "entries": {"oro": {"note": "Używane zależnie od zwyczaju."}}}
        )
        assert len(found) == 1 and "note hedges" in found[0]

    def test_a_semicolon_in_a_sense_is_left_to_the_check_that_already_holds_it(self):
        # checks/lexicon.py reports this one. Two messages for one defect is
        # noise, and the division is stated in both docstrings.
        assert (
            check_lexicon({"lang": "en", "entries": {"oro": {"senses": ["to pray; to beg"]}}}) == []
        )


@pytest.mark.parametrize("field", ["explanation", "note"])
@pytest.mark.parametrize(
    ("lang", "prose"),
    [
        ("pl", "Wydanie analizuje „malo” jako rzeczownik nijaki."),
        ("pl", "Ta edycja przyjmuje malum i zaznacza wątpliwość."),
        ("en", "This edition parses malo as a neuter noun."),
        ("en", "Our edition takes the masculine."),
    ],
)
def test_word_help_cannot_appeal_to_its_own_editorial_authority(field, lang, prose):
    doc = {"text": "orationes.pater-noster", "language": lang, "words": {"w049": {field: prose}}}
    errors = check(doc)
    assert len(errors) == 1
    assert f"w049.{field}.{lang}" in errors[0]
    assert "self-authorizing word help" in errors[0]


def test_joined_word_help_has_the_same_guard():
    doc = a_text()
    doc["segments"][1]["words"][0]["note"] = {"en": "This edition takes the noun."}
    assert any("self-authorizing word help" in error for error in check(doc))


def test_lexicon_notes_do_not_claim_editorial_authority():
    lex = {
        "language": "pl",
        "entries": {"Ioseph": {"note": "Ta edycja pozostawia je nieodmiennym."}},
    }
    assert any("self-authorizing word help" in error for error in check_lexicon(lex))


@pytest.mark.parametrize(
    "prose",
    [
        "The Nova Vulgata reads servabo, an unambiguous future.",
        "The 1962 edition prints this form.",
        "Wydanie typiczne Mszału z 1962 r. zawiera tę modlitwę.",
        "Sama forma może pochodzić od malum albo malus.",
        "The form permits either reading. The context favors a petition.",
        "The Catechism identifies the Evil One as Satan (CCC 2851).",
    ],
)
def test_sources_and_honest_uncertainty_are_not_self_authority(prose):
    assert check({"text": "t.t", "words": {"w001": {"note": prose}}}) == []


def test_edition_coverage_information_is_not_word_help():
    doc = {"text": "t.t", "about": "This edition prints the full prayer."}
    assert check(doc) == []


@pytest.mark.parametrize("prose", ["As at w036.", "As at “ipsum” (w036).", "Jak przy w1000."])
def test_plain_uncertainty_notes_cannot_expose_word_ids(prose):
    errors = check({"text": "t.t", "words": {"w049": {"note": prose}}})
    assert len(errors) == 1 and "bare word-id" in errors[0]


def test_explanations_may_use_the_linked_reference_format():
    doc = {"text": "t.t", "words": {"w049": {"explanation": "Refers to “Verbum” (w001)."}}}
    assert check(doc) == []  # Reference identity and syntax are checked by lint.py.


def test_duplicate_explanation_and_note_are_rejected_in_both_document_shapes():
    doc = {
        "text": "t.t",
        "words": {"w001": {"explanation": "Two readings.", "note": " Two  readings. "}},
    }
    assert any("repeat the same text" in error for error in check(doc))
    joined = a_text()
    joined["segments"][1]["words"][0].update(
        explanation={"pl": "Dwa odczytania."}, note={"pl": "Dwa odczytania."}
    )
    assert any("repeat the same text" in error for error in check(joined))


def test_complementary_explanation_and_uncertainty_note_are_allowed():
    doc = {
        "text": "orationes.pater-noster",
        "words": {
            "w049": {
                "explanation": "The Catechism identifies the Evil One as Satan (CCC 2851).",
                "note": "The Latin form can come from malum or malus.",
            }
        },
    }
    assert check(doc) == []
