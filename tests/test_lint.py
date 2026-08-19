"""What the gloss layer refuses to say to a reader.

The terminology contract (TERMINOLOGY.md) is not style advice: `ablatiw` is
a Polonized spelling this edition does not use, and an agreement claim has
one wording so that fifty of them read alike. The rules were applied to
every gloss and every translation — and not to `about`, which is the
paragraph the app puts behind the "about this prayer" button and therefore
the most read prose in the layer.
"""

from copy import deepcopy
from typing import ClassVar

from checks.lint import (
    STRESS_EXEMPT,
    check_analysis,
    lint_citations,
    lint_gloss,
    lint_notes,
    lint_nulls,
    lint_parity,
    lint_text,
    stress_position,
)

TEXT = {
    "id": "orationes.test",
    "segments": [
        {
            "id": "s01",
            "type": "verse",
            "words": [{"id": "w001", "form": "Salve", "lemma": "salveo", "morph": {"pos": "verb"}}],
        }
    ],
}

CITATION = {
    "title": "Catechismus Catholicae Ecclesiae",
    "locator": "n. 1449",
    "url": "https://www.vatican.va/archive/catechism_lt/p2s2c2a4_lt.htm",
}


def gloss(**over):
    g = {
        "schema_version": "0.9.0",
        "text": "orationes.test",
        "lang": "pl",
        "status": "working-edition",
        "analysis_defaults": {"confidence": "high", "sources": ["editorial"], "review": "pending"},
        "segments": {"s01": {"translation": "Witaj."}},
        "words": {"w001": {"gloss": "witaj"}},
    }
    g.update(over)
    return g


class TestTheIntroduction:
    def test_a_clean_one_passes(self):
        assert lint_gloss(gloss(about="Antyfona maryjna okresu wielkanocnego."), TEXT) == []

    def test_a_banned_term_in_it_is_refused(self):
        found = lint_gloss(gloss(about="Rzeczownik stoi w ablatiwie."), TEXT)
        assert any("banned terminology" in e for e in found)

    def test_and_the_approved_spelling_passes(self):
        assert lint_gloss(gloss(about="Rzeczownik stoi w ablativie."), TEXT) == []

    def test_a_layer_with_no_introduction_at_all_is_fine(self):
        # `about` arrived in 0.8.0 and is optional; a missing one must not
        # be read as an empty string that fails some other rule.
        assert lint_gloss(gloss(), TEXT) == []


class TestNoteReferences:
    def test_a_multiword_range_names_every_token(self):
        text = {
            **TEXT,
            "notes": "DÓMINO DEO NOSTRO at w001-w003 is a dative phrase.",
            "segments": [
                {
                    "id": "s01",
                    "type": "verse",
                    "words": [
                        {"id": "w001", "form": "Dómino"},
                        {"id": "w002", "form": "Deo"},
                        {"id": "w003", "form": "nostro"},
                    ],
                }
            ],
        }
        assert lint_notes(text) == []

    def test_a_multiword_phrase_cannot_hide_behind_one_token(self):
        text = {
            **TEXT,
            "notes": "DÓMINO DEO NOSTRO at w003-w003 is a dative phrase.",
            "segments": [
                {
                    "id": "s01",
                    "type": "verse",
                    "words": [{"id": "w003", "form": "nostro"}],
                }
            ],
        }
        assert any("those tokens are nostro" in e for e in lint_notes(text))

    def test_one_form_may_name_two_occurrences(self):
        text = {
            **TEXT,
            "notes": "FRATRES at w001 and w003 is vocative at both places.",
            "segments": [
                {
                    "id": "s01",
                    "type": "verse",
                    "words": [
                        {"id": "w001", "form": "fratres"},
                        {"id": "w003", "form": "fratres"},
                    ],
                }
            ],
        }
        assert lint_notes(text) == []

    def test_two_named_forms_may_use_two_separate_ids(self):
        text = {
            **TEXT,
            "notes": "CORPUS and SANGUIS at w001 and w003 are nominative.",
            "segments": [
                {
                    "id": "s01",
                    "type": "verse",
                    "words": [
                        {"id": "w001", "form": "Corpus"},
                        {"id": "w003", "form": "Sanguis"},
                    ],
                }
            ],
        }
        assert lint_notes(text) == []

    def test_analysis_status_claims_must_match_the_words(self):
        text = deepcopy(TEXT)
        text["notes"] = "SALVE at w001 has medium confidence and marks the token disputed."
        text["analysis_defaults"] = {
            "confidence": "high",
            "sources": ["editorial"],
            "review": "accepted",
        }
        found = lint_notes(text)
        assert any("no word has that confidence" in e for e in found)
        assert any("no word is marked disputed" in e for e in found)

        text["segments"][0]["words"][0]["analysis"] = {
            "confidence": "medium",
            "sources": ["editorial"],
            "review": "disputed",
        }
        assert lint_notes(text) == []


class TestReaderFacingCitations:
    def test_a_source_with_an_exact_locator_passes(self):
        g = gloss(about="Modlitwa błagalna.", about_citations=[CITATION])
        assert lint_gloss(g, TEXT) == []

    def test_a_source_cannot_float_without_the_comment_it_supports(self):
        found = lint_gloss(gloss(about_citations=[CITATION]), TEXT)
        assert any("citations without an about paragraph" in e for e in found)

    def test_a_function_source_requires_a_function_note(self):
        g = gloss(words={"w001": {"gloss": "witaj", "function_citations": [CITATION]}})
        found = lint_gloss(g, TEXT)
        assert any("citations without a function note" in e for e in found)

    def test_a_narrative_source_requires_a_narrative(self):
        text = {"id": "orationes.test", "segments": [{"id": "s01", "type": "rubric"}]}
        g = gloss(segments={"s01": {"narrative_citations": [CITATION]}}, words={})
        found = lint_gloss(g, text)
        assert any("citations without a narrative" in e for e in found)

    def test_a_translation_source_requires_a_translation(self):
        found = lint_gloss(gloss(segments={"s01": {"translation_citations": [CITATION]}}), TEXT)
        assert any("citations without a translation" in e for e in found)

    def test_translation_sources_are_language_specific(self):
        pl = gloss(segments={"s01": {"translation": "Witaj.", "translation_citations": [CITATION]}})
        en = gloss(lang="en", segments={"s01": {"translation": "Hail."}})
        assert lint_parity([pl, en]) == []

    def test_a_locator_is_mandatory(self):
        found = lint_citations([{"title": "A work"}], "en:about")
        assert any("locator must be a nonempty string" in e for e in found)

    def test_a_link_must_be_public_https(self):
        found = lint_citations(
            [{"title": "A work", "locator": "p. 1", "url": "http://localhost/source"}],
            "en:about",
        )
        assert any("absolute HTTPS" in e for e in found)

    def test_duplicate_sources_are_refused(self):
        found = lint_citations([CITATION, CITATION], "en:about")
        assert any("duplicate citation" in e for e in found)

    def test_bibliographic_metadata_has_exact_language_parity(self):
        pl = gloss(about="Modlitwa błagalna.", about_citations=[CITATION])
        en = gloss(
            lang="en",
            about="A prayer of petition.",
            about_citations=[{**CITATION, "locator": "paragraph 1449"}],
        )
        found = lint_parity([pl, en])
        assert any("citations differ" in e for e in found)


class TestWhereTheRulesAlreadyApplied:
    def test_a_banned_term_in_a_function_note_is_still_refused(self):
        g = gloss(words={"w001": {"gloss": "witaj", "function": "Stoi w ablatiwie."}})
        assert any("banned terminology" in e for e in lint_gloss(g, TEXT))

    def test_and_in_a_translation(self):
        g = gloss(segments={"s01": {"translation": "Witaj w ablatiwie."}})
        assert any("banned terminology" in e for e in lint_gloss(g, TEXT))


class TestContextualReadings:
    def test_a_gloss_cannot_choose_what_its_note_leaves_unresolved(self):
        g = gloss(
            words={
                "w001": {
                    "gloss": "będę szukał",
                    "function": (
                        "Forma może mieć dwa odczytania. Wydanie nie rozstrzyga tej dwuznaczności."
                    ),
                }
            }
        )
        found = lint_gloss(g, TEXT)
        assert any("leaves the edition unresolved" in e for e in found)

    def test_a_finite_verb_must_record_the_chosen_mood_and_tense(self):
        text = {
            **TEXT,
            "segments": [
                {
                    **TEXT["segments"][0],
                    "words": [
                        {
                            **TEXT["segments"][0]["words"][0],
                            "morph": {
                                "pos": "verb",
                                "person": 2,
                                "number": "sg",
                                "voice": "act",
                            },
                        }
                    ],
                }
            ],
        }
        found, count = lint_text(text)
        assert count == 1
        assert any("missing morph.mood" in e for e in found)

        text["segments"][0]["words"][0]["morph"]["mood"] = "imp"
        found, count = lint_text(text)
        assert count == 1
        assert any("missing morph.tense" in e for e in found)

        text["segments"][0]["words"][0]["morph"]["tense"] = "pres"
        found, count = lint_text(text)
        assert count == 1
        assert found == []

    def test_a_formal_ambiguity_may_be_explained_with_the_adopted_reading(self):
        g = gloss(
            words={
                "w001": {
                    "gloss": "będę szukał",
                    "function": "Forma może mieć dwa odczytania. Przekład przyjmuje futurum.",
                }
            }
        )
        assert lint_gloss(g, TEXT) == []

    def test_an_english_left_unclaimed_note_is_refused(self):
        g = gloss(
            lang="en",
            words={
                "w001": {
                    "gloss": "be put to shame",
                    "function": "Tense and mood are left unclaimed.",
                }
            },
        )
        found = lint_gloss(g, TEXT)
        assert any("leaves the edition unresolved" in e for e in found)


class TestPossessiveAbsorption:
    TEXT2: ClassVar[dict] = {
        "id": "orationes.test",
        "segments": [
            {
                "id": "s01",
                "type": "verse",
                "words": [
                    {"id": "w001", "form": "manus", "lemma": "manus", "morph": {"pos": "noun"}},
                    {"id": "w002", "form": "meas", "lemma": "meus", "morph": {"pos": "adj"}},
                ],
            }
        ],
    }

    def base(self, g1, g2, lang="en"):
        g = gloss(lang=lang, segments={"s01": {"translation": "x."}})
        g["words"] = {"w001": {"gloss": g1}, "w002": {"gloss": g2}}
        return g

    def test_an_absorbed_possessive_is_an_error(self):
        found = lint_gloss(self.base("my hands", "my"), self.TEXT2)
        assert any("absorbs the possessive" in e for e in found)

    def test_the_separated_pair_passes(self):
        assert lint_gloss(self.base("hands", "my"), self.TEXT2) == []

    def test_the_of_form_is_caught_too(self):
        found = lint_gloss(self.base("of Thy glory", "Thy"), self.TEXT2)
        assert any("absorbs the possessive" in e for e in found)

    def test_a_fused_token_with_no_possessive_neighbor_passes(self):
        assert lint_gloss(self.base("with you", "and"), self.TEXT2) == []

    def test_polish_absorption_is_an_error(self):
        found = lint_gloss(self.base("ręce moje", "moje", lang="pl"), self.TEXT2)
        assert any("absorbs the possessive" in e for e in found)

    def test_an_absorbed_conjunction_is_an_error(self):
        found = lint_gloss(self.base("and truth", "and"), self.TEXT2)
        assert any("absorbs the conjunction" in e for e in found)

    def test_a_fused_enclitic_may_gloss_its_own_conjunction(self):
        # mihíque et ómnibus: the -que is inside the first token and the et
        # is a second conjunction. "and for me" beside "and" is correct.
        text = {
            "id": "ordinarium.test",
            "segments": [
                {
                    "id": "s01",
                    "type": "verse",
                    "words": [
                        {"id": "w001", "form": "mihíque", "lemma": "ego", "morph": {"pos": "pron"}},
                        {"id": "w002", "form": "et", "lemma": "et", "morph": {"pos": "conj"}},
                    ],
                }
            ],
        }
        assert lint_gloss(self.base("and for me", "and"), text) == []


class TestHoles:
    """A null and an emptied string, at the depth the document actually has.

    The rule read one level while the document had grown nested by language,
    and a census of unguarded mutations (2026-08-19) walked through the gap
    three ways: `translation.pl = null` passed, `gloss.pl = null` came back as
    a TypeError from a check downstream, and an emptied translation passed
    beside an empty gloss that was refused.
    """

    def stored(self, **over):
        doc = {
            "id": "orationes.test",
            "title": "Ave María",
            "about": {"pl": "Antyfona.", "en": "An antiphon."},
            "segments": [
                {
                    "id": "s01",
                    "type": "verse",
                    "translation": {"pl": "Witaj.", "en": "Hail."},
                    "words": [
                        {
                            "id": "w001",
                            "form": "Ave",
                            "gloss": {"pl": "witaj", "en": "hail"},
                        }
                    ],
                }
            ],
        }
        doc.update(over)
        return doc

    def test_a_clean_document_passes(self):
        assert lint_nulls(self.stored()) == []

    def test_a_null_translation_in_one_language_is_reported(self):
        doc = self.stored()
        doc["segments"][0]["translation"]["pl"] = None
        found = lint_nulls(doc)
        assert found == [
            "orationes.test:segments.s01.translation.pl: is null — a key that carries "
            "nothing is removed, not left for a reader to interpret"
        ]

    def test_a_null_gloss_is_reported_rather_than_raised(self):
        doc = self.stored()
        doc["segments"][0]["words"][0]["gloss"]["pl"] = None
        found = lint_nulls(doc)
        assert len(found) == 1 and "segments.s01.words.w001.gloss.pl" in found[0]

    def test_a_null_about_is_reported(self):
        doc = self.stored()
        doc["about"]["en"] = None
        assert any("about.en" in e for e in lint_nulls(doc))

    def test_an_emptied_translation_is_a_hole_like_an_empty_gloss(self):
        doc = self.stored()
        doc["segments"][0]["translation"]["en"] = ""
        found = lint_nulls(doc)
        assert len(found) == 1 and "translation is empty" in found[0]

    def test_whitespace_is_not_prose(self):
        doc = self.stored()
        doc["segments"][0]["words"][0]["gloss"]["pl"] = "   "
        assert any("gloss is empty" in e for e in lint_nulls(doc))

    def test_an_emptied_title_is_a_hole(self):
        assert any("title is empty" in e for e in lint_nulls(self.stored(title="")))

    def test_a_field_no_reader_sees_may_be_empty(self):
        # `variant` is metadata, not prose. The emptiness rule is about the
        # page, and the null rule above already covers the rest.
        assert lint_nulls(self.stored(variant="")) == []


class TestTheVoicesThatMayConfirm:
    def test_a_declared_analyzer_passes(self):
        assert (
            check_analysis(
                {
                    "confidence": "high",
                    "sources": ["whitakers", "collatinus"],
                    "review": "accepted",
                },
                "w001",
            )
            == []
        )

    def test_a_witness_siglum_passes(self):
        assert (
            check_analysis(
                {"confidence": "high", "sources": ["editorial", "do"], "review": "pending"}, "s01"
            )
            == []
        )

    def test_an_analyzer_this_edition_does_not_run_is_refused(self):
        # Well-formed, and answered only by CI's network-clone agreement run
        # until the vocabulary was read locally (census, 2026-08-19).
        found = check_analysis(
            {"confidence": "high", "sources": ["morfeusz-for-latin"], "review": "pending"}, "w001"
        )
        assert len(found) == 1 and "not a voice this edition knows" in found[0]

    def test_a_malformed_name_is_still_caught_first(self):
        found = check_analysis(
            {"confidence": "high", "sources": ["Whitakers"], "review": "pending"}, "w001"
        )
        assert len(found) == 1 and "malformed" in found[0]


class TestStressPosition:
    """Latin stress reaches the antepenult and no further."""

    def test_the_penult_and_the_antepenult_pass(self):
        assert stress_position("w001: 'Dóminus'", "Dóminus") == []
        assert stress_position("w001: 'Ioánnes'", "Ioánnes") == []

    def test_a_fourth_from_last_accent_is_refused(self):
        found = stress_position("w001: 'pérhibeo'", "pérhibeo")
        assert len(found) == 1
        assert found[0] == (
            "w001: 'pérhibeo' accents the syllable 4 from the end — Latin stress "
            "reaches the antepenult and no further"
        )

    def test_an_unaccented_form_says_nothing(self):
        assert stress_position("w001: 'Pater'", "Pater") == []

    def test_the_au_diphthong_is_one_syllable_even_under_the_mark(self):
        # páuperum is pau-pe-rum, the accent on the antepenult. Reading the
        # letter before the u without reading past the mark made it four.
        assert stress_position("w001: 'páuperum'", "páuperum") == []
        assert stress_position("w001: 'exáudi'", "exáudi") == []

    def test_the_exemption_table_is_empty_and_an_entry_would_be_deliberate(self):
        # Its one candidate ever, indúimini, was a transcription error the
        # rule itself exposed: the 600 dpi page image prints induímini, the
        # accent on the antepenult. The empty table is the record, and a
        # violating form is an error unless someone names its page here.
        assert STRESS_EXEMPT == {}
        assert stress_position("w054: 'indúimini'", "indúimini") != []
