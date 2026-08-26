"""One edition, one spelling — and a table every entry of which fires.

The module had a guard written for *enrol* inside *enroll*: skip a match that
begins with any American form. Read that way it silently exempted the three
entries whose American twin is their own PREFIX, so `_hits('dialogue')` came
back empty and catalogue and programme with it — declared, and unenforceable,
for as long as they had been declared (census, 2026-08-19).

So the table is tested WHOLE. Every British form must be caught, and no
American form may be, which is the assertion that would have failed the day
the guard was written.
"""

import pytest

from checks.orthography import BRITISH, _hits, check, check_lexicon


@pytest.mark.parametrize("british", sorted(BRITISH))
def test_every_declared_british_form_is_caught(british):
    assert _hits(british) == [(british, british)]


@pytest.mark.parametrize("american", sorted(set(BRITISH.values())))
def test_and_no_american_form_is(american):
    assert _hits(american) == []


class TestThePrefixPairs:
    def test_a_british_form_inside_its_american_twin_is_not_a_hit(self):
        # enrol inside enroll: the exemption this rule was written for
        assert _hits("enroll me in that number") == []
        assert _hits("instill and fulfill") == []

    def test_but_the_british_form_itself_still_is(self):
        assert [b for _, b in _hits("enrol me")] == ["enrol"]

    def test_a_shared_inflection_belongs_to_neither(self):
        # American English writes "enrolled" too
        assert _hits("enrolled among them") == []

    def test_an_american_form_inside_its_british_twin_does_not_exempt_it(self):
        # dialog inside dialogue, the case the old guard read backwards
        assert [b for _, b in _hits("a dialogue, a catalogue and a programme")] == [
            "dialogue",
            "catalogue",
            "programme",
        ]

    def test_toward_is_not_towards(self):
        assert _hits("toward the altar") == []
        assert [b for _, b in _hits("towards the altar")] == ["towards"]


class TestWhatTheSweepFound:
    @pytest.mark.parametrize(
        ("written", "american"),
        [
            ("worshipper", "worshiper"),
            ("acknowledgement", "acknowledgment"),
            ("towards", "toward"),
            ("judgement", "judgment"),
        ],
    )
    def test_the_pairs_added_after_the_census(self, written, american):
        assert BRITISH[written] == american
        assert _hits(f"and {written} again") == [(written, written)]


def gloss(**over):
    doc = {"lang": "en", "words": {}, "segments": {}}
    doc.update(over)
    return doc


TEXT = {"id": "ordinarium.test"}


class TestWhereItReads:
    def test_a_british_spelling_in_an_about_is_refused(self):
        found = check(TEXT, gloss(about="The dialogue before the preface."))
        assert len(found) == 1
        assert found[0] == (
            "ordinarium.test:about: 'dialogue' is British, and this edition writes "
            "American — 'dialog'"
        )

    def test_and_in_a_gloss_and_a_function_note(self):
        doc = gloss(words={"w001": {"gloss": "honour", "explanation": "Towards the altar."}})
        assert len(check(TEXT, doc)) == 2

    def test_a_quoted_verse_keeps_the_spelling_of_the_source(self):
        cited = gloss(
            segments={
                "s01": {
                    "translation": "Vessel of honour.",
                    "translation_citations": [{"title": "Thesaurus Precum Latinarum"}],
                }
            }
        )
        assert check(TEXT, cited) == []

    def test_but_our_own_verse_does_not(self):
        ours = gloss(segments={"s01": {"translation": "Vessel of honour."}})
        assert any("is British" in e for e in check(TEXT, ours))

    def test_the_polish_layer_is_not_swept_for_english_spelling(self):
        assert check(TEXT, gloss(lang="pl", about="Dialogue przed prefacją.")) == []

    def test_the_lexicon_answers_to_the_same_rule(self):
        found = check_lexicon({"centrum": {"senses": ["centre"], "derivatives": ["theatre"]}})
        assert len(found) == 2
