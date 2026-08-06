"""The syllabifier and the normal forms collation compares.

These are the philological rules of the edition written as code, and until
now they were only exercised through whole-corpus runs — which say that
something is wrong somewhere, not which rule broke. The cases below are the
ones checks/normalize.py names in its own docstrings, so a change that
contradicts the documentation fails here rather than in a witness file.
"""

import pytest

from checks.normalize import (
    after_prefix,
    fold_ligatures,
    has_accent,
    strip_accents,
    substantive,
    syllable_count,
)


class TestStripAccents:
    def test_removes_the_marks_and_keeps_the_letters(self):
        assert strip_accents("Dóminus") == "Dominus"
        assert strip_accents("sæculórum") == "sæculorum"

    def test_leaves_a_bare_word_alone(self):
        assert strip_accents("Pater") == "Pater"

    def test_does_not_touch_the_ligature_itself(self):
        # æ is a letter here, not an accented a — fold_ligatures' business
        assert strip_accents("cælis") == "cælis"


class TestFoldLigatures:
    @pytest.mark.parametrize(
        ("written", "folded"),
        [("cælis", "caelis"), ("Ægýptum", "Aegýptum"), ("cœli", "coeli"), ("sǽculi", "saeculi")],
    )
    def test_expands_every_ligature_the_books_print(self, written, folded):
        assert fold_ligatures(written) == folded


class TestSubstantive:
    def test_keeps_only_the_letters(self):
        assert substantive("Iesu Christi,") == "iesu christi"

    def test_collapses_whitespace_and_drops_punctuation(self):
        assert substantive("  Pater  noster,   qui es. ") == "pater noster qui es"

    def test_j_is_a_difference_unless_the_witness_declares_otherwise(self):
        # ORTHOGRAPHY.md: j/i is substantive by default, so that a witness
        # which prints j is recorded as printing j
        assert substantive("Jesu") != substantive("Iesu")
        assert substantive("Jesu", fold_ji=True) == substantive("Iesu", fold_ji=True)

    def test_a_witness_may_declare_assimilated_ex(self):
        assert substantive("exspécto") != substantive("expécto")
        assert substantive("exspécto", fold_xs=True) == substantive("expécto", fold_xs=True)


class TestAfterPrefix:
    def test_a_compound_of_iuvo_keeps_its_consonant(self):
        assert after_prefix("adiutórium", 2) is True

    def test_a_compound_of_eo_does_not(self):
        # ábiit is ab + iit: the i is a vowel, and nothing in the spelling
        # distinguishes it from adiutórium's — hence the stem list
        assert after_prefix("ábiit", 2) is False

    def test_a_word_that_merely_starts_with_a_prefix_shape_does_not(self):
        assert after_prefix("addit", 2) is False


class TestSyllableCount:
    @pytest.mark.parametrize(
        ("form", "count"),
        [
            ("et", 1),
            ("Pater", 2),
            ("Dóminus", 3),
            ("Spíritus", 3),
            ("sæculórum", 4),  # the ligature is one syllable
            ("cælis", 2),
        ],
    )
    def test_ordinary_words(self, form, count):
        assert syllable_count(form) == count

    @pytest.mark.parametrize(
        ("form", "count"),
        [
            ("Eia", 2),  # at the head of a word, before a vowel
            ("Iesus", 2),
            ("Ioánnes", 3),
            ("iube", 2),
            ("eius", 2),  # between two vowels
            ("allelúia", 4),
            ("maiestátis", 4),
        ],
    )
    def test_consonantal_i_is_a_glide_not_a_nucleus(self, form, count):
        assert syllable_count(form) == count

    @pytest.mark.parametrize(
        ("form", "count"),
        [("adiutórium", 5), ("iustítiam", 4), ("coniúnctio", 4)],
    )
    def test_a_compound_keeps_the_consonant_of_its_simplex(self, form, count):
        assert syllable_count(form) == count

    def test_but_a_compound_of_eo_has_a_vowel_there(self):
        assert syllable_count("ábiit") == 3  # á-bi-it, not á-biit

    @pytest.mark.parametrize(("form", "count"), [("quia", 2), ("relíquiæ", 4)])
    def test_the_qu_glide_is_consumed_before_the_i_rule_can_see_it(self, form, count):
        assert syllable_count(form) == count

    def test_au_is_a_diphthong_and_eu_is_not(self):
        assert syllable_count("laus") == 1
        assert syllable_count("Deum") == 2

    def test_the_diaeresis_is_its_own_syllable(self):
        assert syllable_count("Míchaël") == 3


class TestHasAccent:
    def test_finds_an_accent_anywhere(self):
        assert has_accent("Dóminus") is True
        assert has_accent("sǽculi") is True

    def test_and_reports_none_when_there_is_none(self):
        assert has_accent("Pater") is False
        assert has_accent("cælis") is False
