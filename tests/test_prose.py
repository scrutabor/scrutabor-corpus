"""The edition's own voice: no semicolons, no hedging.

Both rules were guarded in the reader app, which vendors this corpus — so the
sweep ran against a copy, and only after somebody re-vendored it. A semicolon
planted in an `about` paragraph passed every check this repository had, and the
hedges reached corpus prose in neither repository (census, 2026-08-19).

The exemptions are tested as carefully as the rule: a verse translation carries
the punctuation of the text it translates, and thirty-one of them do.
"""

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
                        "function": {"pl": "Mianownik.", "en": "Nominative."},
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

    def test_one_in_a_function_note_is_refused(self):
        doc = a_text()
        doc["segments"][1]["words"][0]["function"]["en"] = "Nominative; the subject."
        assert any("w001.function.en" in e for e in check(doc))

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
