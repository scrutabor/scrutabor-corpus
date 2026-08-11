"""What the dictionary layer refuses.

Most of these rules exist because something got past them once. The head
spelling rule is the clearest case: eight heads sat in the j-form after the
orthography was reversed, two of them half-converted, and nothing
complained — so it is checked here on a head of two words, which is the
shape that hid them.
"""

from checks.lexicon import (
    check_orphans,
    check_text_against_lexicon,
    lint_lemmata,
    lint_sense_parity,
    lint_senses,
)


def a_lemma(**over):
    entry = {"head": "pater, patris", "pos": "noun", "gender": "m", "decl": 3}
    entry.update(over)
    return {"pater": entry}


def errors_for(**over):
    return lint_lemmata(a_lemma(**over))


class TestALemmaEntry:
    def test_a_good_entry_passes(self):
        assert errors_for() == []

    def test_zero_entries_is_a_failure_not_a_pass(self):
        # a gate that checks nothing must not pass
        assert lint_lemmata({}) != []

    def test_an_unknown_key_is_refused(self):
        assert any("unknown keys" in e for e in errors_for(colour="red"))

    def test_a_missing_head_is_refused(self):
        assert any("missing head" in e for e in lint_lemmata({"pater": {"pos": "noun"}}))

    def test_the_part_of_speech_must_be_in_the_enum(self):
        assert any("not in enum" in e for e in errors_for(pos="substantive"))

    def test_a_declension_outside_the_five_is_refused(self):
        assert any("out of range" in e for e in errors_for(decl=7))

    def test_a_conjugation_outside_the_four_is_refused(self):
        assert any("out of range" in e for e in errors_for(pos="verb", decl=None, conj=9))


class TestTheHeadIsSpelledLikeTheText:
    def test_a_head_may_not_spell_the_consonant_with_j(self):
        found = lint_lemmata({"iesus": {"head": "Jesus", "pos": "noun"}})
        assert any("spells the consonant with j" in e for e in found)

    def test_including_when_only_one_token_of_it_does(self):
        # majéstas, maiestátis — the shape that hid eight of these
        found = lint_lemmata({"maiestas": {"head": "majéstas, maiestátis", "pos": "noun"}})
        assert any("spells the consonant with j" in e for e in found)

    def test_a_head_of_three_syllables_or_more_carries_its_accent(self):
        found = lint_lemmata({"dominus": {"head": "dominus, domini", "pos": "noun"}})
        assert any("no accent" in e for e in found)

    def test_and_a_head_of_two_does_not(self):
        found = lint_lemmata({"pater": {"head": "páter", "pos": "noun"}})
        assert any("carries an accent" in e for e in found)

    def test_one_accent_to_a_word(self):
        found = lint_lemmata({"dominus": {"head": "Dóminús", "pos": "noun"}})
        assert any("accents" in e for e in found)


class TestSenses:
    def test_a_good_entry_passes(self):
        assert lint_senses("pl", {"pater": {"senses": ["ojciec"]}}, {"pater": {}}) == []

    def test_senses_may_not_be_empty(self):
        assert lint_senses("pl", {"pater": {"senses": []}}, {"pater": {}}) != []

    def test_more_than_four_senses_is_refused(self):
        entry = {"senses": ["a", "b", "c", "d", "e"]}
        assert any("at most 4" in e for e in lint_senses("pl", {"pater": entry}, {"pater": {}}))

    def test_more_than_six_derivatives_is_refused(self):
        entry = {"senses": ["ojciec"], "derivatives": list("abcdefg")}
        assert any("at most 6" in e for e in lint_senses("pl", {"pater": entry}, {"pater": {}}))

    def test_every_lemma_needs_an_entry_in_every_language(self):
        found = lint_senses("pl", {}, {"pater": {}})
        assert any("no entry for" in e for e in found)

    def test_and_no_entry_may_name_a_lemma_that_does_not_exist(self):
        found = lint_senses("pl", {"ghost": {"senses": ["x"]}}, {})
        assert any("unknown lemmas" in e for e in found)

    def test_a_lemma_note_cannot_point_to_an_absent_verse(self):
        entry = {"senses": ["zrozumienie"], "note": "W tym wersecie jest darem."}
        found = lint_senses("pl", {"intellectus": entry}, {"intellectus": {}})
        assert any("context-dependent deixis" in e for e in found)

    def test_contextual_here_is_rejected_in_english_too(self):
        entry = {"senses": ["refuge"], "note": "Here it names a place."}
        found = lint_senses("en", {"refugium": entry}, {"refugium": {}})
        assert any("context-dependent deixis" in e for e in found)

    def test_an_unnamed_prayer_is_not_a_context_anchor(self):
        entry = {"senses": ["Eve"], "note": "The prayer calls us her children."}
        found = lint_senses("en", {"Eva": entry}, {"Eva": {}})
        assert any("context-dependent deixis" in e for e in found)

    def test_an_impersonal_local_petition_is_rejected(self):
        entry = {"senses": ["ustanowić"], "note": "Prosi się o utwierdzenie słowa."}
        found = lint_senses("pl", {"statuo": entry}, {"statuo": {}})
        assert any("context-dependent deixis" in e for e in found)

    def test_an_explicitly_named_context_is_self_contained(self):
        entry = {"senses": ["understanding"], "note": "In Psalm 118:34 it is a gift."}
        assert lint_senses("en", {"intellectus": entry}, {"intellectus": {}}) == []

    def test_word_internal_here_is_not_mistaken_for_verse_context(self):
        entry = {"senses": ["bright"], "note": "The prefix here is intensive."}
        assert lint_senses("en", {"praeclarus": entry}, {"praeclarus": {}}) == []

    def test_note_citations_require_a_note(self):
        entry = {
            "senses": ["father"],
            "note_citations": [{"title": "A work", "locator": "p. 1"}],
        }
        found = lint_senses("en", {"pater": entry}, {"pater": {}})
        assert any("citations without a note" in e for e in found)

    def test_note_citations_have_exact_language_parity(self):
        citation = [{"title": "A work", "locator": "p. 1"}]
        langs = {
            "en": {"pater": {"senses": ["father"], "note_citations": citation}},
            "pl": {
                "pater": {
                    "senses": ["ojciec"],
                    "note_citations": [{"title": "A work", "locator": "s. 1"}],
                }
            },
        }
        assert any("citation parity differs" in e for e in lint_sense_parity(langs))


class TestOrphans:
    def test_an_entry_no_text_uses_is_reported(self):
        assert check_orphans({"pater": {}, "ghost": {}}, {"pater"}) != []

    def test_and_a_lexicon_every_entry_of_which_is_used_is_clean(self):
        assert check_orphans({"pater": {}}, {"pater"}) == []


def a_text(**morph):
    m = {"pos": "noun", "decl": 3, "gender": "m"}
    m.update(morph)
    return {
        "id": "orationes.test",
        "segments": [{"type": "verse", "words": [{"id": "w001", "lemma": "pater", "morph": m}]}],
    }


PATER = {"pater": {"head": "pater, patris", "pos": "noun", "gender": "m", "decl": 3}}


class TestATextAgainstTheLexicon:
    """The entry and every token of it must describe the same word: a
    paradigm fact recorded twice is a paradigm fact that can disagree."""

    def test_a_text_whose_lemmata_are_all_present_and_agreeing_is_clean(self):
        assert check_text_against_lexicon(a_text(), PATER) == []

    def test_every_lemma_a_text_names_must_have_an_entry(self):
        doc = a_text()
        doc["segments"][0]["words"][0]["lemma"] = "ghost"
        assert any("no lexicon entry" in e for e in check_text_against_lexicon(doc, PATER))

    def test_the_part_of_speech_must_agree(self):
        found = check_text_against_lexicon(a_text(pos="verb"), PATER)
        assert any("morph.pos=" in e for e in found)

    def test_the_declension_must_agree(self):
        found = check_text_against_lexicon(a_text(decl=2), PATER)
        assert any("morph.decl=" in e for e in found)

    def test_the_gender_must_agree(self):
        found = check_text_against_lexicon(a_text(gender="f"), PATER)
        assert any("morph.gender=" in e for e in found)

    def test_a_plural_may_take_the_gender_the_entry_gives_its_plural(self):
        # locus, loci m. but loca n. in the plural — the entry says so and
        # the token is then right to differ from the singular gender
        lex = {"locus": {"head": "locus, loci", "pos": "noun", "gender": "m", "gender_pl": "n"}}
        doc = a_text(gender="n", number="pl")
        doc["segments"][0]["words"][0]["lemma"] = "locus"
        del doc["segments"][0]["words"][0]["morph"]["decl"]
        assert check_text_against_lexicon(doc, lex) == []

    def test_and_a_second_dictionary_gender_satisfies_it_too(self):
        # dies m., f. for an appointed day
        lex = {"dies": {"head": "dies, diei", "pos": "noun", "gender": "m", "gender_alt": "f"}}
        doc = a_text(gender="f")
        doc["segments"][0]["words"][0]["lemma"] = "dies"
        del doc["segments"][0]["words"][0]["morph"]["decl"]
        assert check_text_against_lexicon(doc, lex) == []

    def test_the_conjugation_must_agree(self):
        lex = {"oro": {"head": "oro, orare", "pos": "verb", "conj": 1}}
        doc = a_text(pos="verb", conj=2)
        doc["segments"][0]["words"][0]["lemma"] = "oro"
        del doc["segments"][0]["words"][0]["morph"]["decl"]
        del doc["segments"][0]["words"][0]["morph"]["gender"]
        assert any("morph.conj=" in e for e in check_text_against_lexicon(doc, lex))
