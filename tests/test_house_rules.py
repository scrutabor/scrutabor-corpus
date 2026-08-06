"""Which differences between this edition and a witness are RULED, and
which are real.

The distinction is the whole economy of the collation: a ruled difference
is recorded once with its reason and never adjudicated again, while
everything else stops the gate until a human rules on it. Widening a ruling
by accident would silence real variants, so the boundary is tested from
both sides.
"""

import pytest

from checks.house_rules import CAPITAL_RULING, IJ_RULING, bare, classify


class TestBare:
    def test_strips_the_marks(self):
        assert bare("Dóminus") == "Dominus"

    def test_leaves_a_ligature_alone_because_it_is_a_letter(self):
        assert bare("cælis") == "cælis"


class TestOrthographyRuling:
    @pytest.mark.parametrize(
        ("ours", "theirs"),
        [("Iesu", "Jesu"), ("Ioánnem", "Joannem"), ("maiestátis", "majestatis"), ("iube", "jube")],
    )
    def test_the_j_form_against_our_i_form_is_ruled(self, ours, theirs):
        kind, ruling = classify(ours, theirs)
        assert kind == "orthography"
        assert ruling == IJ_RULING

    def test_and_it_is_the_same_rule_whichever_side_prints_j(self):
        assert classify("Jesu", "Iesu")[0] == "orthography"


class TestCapitalAccentRuling:
    @pytest.mark.parametrize(
        ("ours", "theirs"),
        [("Dóminus", "Dominus"), ("DÓMINUS", "DOMINUS"), ("sǽculi", "saeculi".replace("ae", "æ"))],
    )
    def test_our_accent_against_their_bare_letter_is_ruled(self, ours, theirs):
        kind, ruling = classify(ours, theirs)
        assert kind == "capital-accent"
        assert ruling == CAPITAL_RULING


class TestWhatIsNotRuled:
    def test_two_identical_words_are_not_a_difference_at_all(self):
        assert classify("Pater", "Pater") is None

    def test_a_different_word_is_a_real_variant(self):
        assert classify("Pater", "Mater") is None

    def test_a_different_ending_is_a_real_variant(self):
        assert classify("Dómine", "Dóminus") is None

    def test_the_ligature_against_its_expansion_is_not_ruled_here(self):
        # It is a difference the collation settles by profile, not by these
        # two rulings — this test exists so that widening either of them to
        # swallow it fails loudly.
        assert classify("cælis", "caelis") is None
