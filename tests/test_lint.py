"""What the gloss layer refuses to say to a reader.

The terminology contract (TERMINOLOGY.md) is not style advice: `ablatiw` is
a Polonized spelling this edition does not use, and an agreement claim has
one wording so that fifty of them read alike. The rules were applied to
every gloss and every translation — and not to `about`, which is the
paragraph the app puts behind the "about this prayer" button and therefore
the most read prose in the layer.
"""

from typing import ClassVar

from checks.lint import lint_citations, lint_gloss, lint_notes, lint_parity

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
