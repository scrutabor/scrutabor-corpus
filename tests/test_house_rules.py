"""Which differences between this edition and a witness are RULED, and
which are real.

The distinction is the whole economy of the collation: a ruled difference
is recorded once with its reason and never adjudicated again, while
everything else stops the gate until a human rules on it. Widening a ruling
by accident would silence real variants, so the boundary is tested from
both sides.
"""

import pytest

from checks.house_rules import CAPITAL_RULING, IJ_RULING, accented, bare, classify


class TestBare:
    def test_strips_the_marks(self):
        assert bare("Dóminus") == "Dominus"

    def test_leaves_a_ligature_alone_because_it_is_a_letter(self):
        assert bare("cælis") == "cælis"


class TestAccented:
    def test_names_the_letter_under_the_accent(self):
        assert accented("Dóminus") == ["o"]

    def test_and_names_it_as_the_capital_it_is(self):
        assert accented("Ómnia") == ["O"]

    def test_a_word_with_no_accent_has_none(self):
        assert accented("Dominus") == []


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
    """The ruling says one thing — "this edition accents capitals; most
    printings omit them" — so it may only be applied where the accent that
    differs is ON a capital. It used to fire on any accent at all, and
    seventeen rulings saying that about lowercase words were written into
    the apparatus of one prayer against a page that is unaccented
    throughout and had already declared the profile that never compares
    accents."""

    @pytest.mark.parametrize(
        ("ours", "theirs"), [("Ómnia", "Omnia"), ("Ángeli", "Angeli"), ("DÓMINUS", "DOMINUS")]
    )
    def test_our_accented_capital_against_their_bare_one_is_ruled(self, ours, theirs):
        kind, ruling = classify(ours, theirs)
        assert kind == "capital-accent"
        assert ruling == CAPITAL_RULING

    @pytest.mark.parametrize(
        ("ours", "theirs"),
        [("Dóminus", "Dominus"), ("defénde", "defende"), ("sǽculi", "sæculi")],
    )
    def test_but_an_accent_on_a_lowercase_letter_is_not_this_rule(self, ours, theirs):
        # A page that drops these drops accents altogether, which is a fact
        # about the page — `profile: substantive-only`, declared once — and
        # not something to assert word by word.
        assert classify(ours, theirs) is None


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
