"""A capitalised word keeps the accent the printing drops."""

from checks.capitals import accented, check, syllables


def doc(*forms):
    return {
        "id": "t",
        "segments": [
            {"id": "s01", "words": [{"id": f"w{i:03d}", "form": f} for i, f in enumerate(forms)]}
        ],
    }


def test_the_word_that_settled_the_rule():
    # The edition prints Excita bare only because it is capitalised: the same
    # page sets éxcita lowercase and accented.
    errors = check(doc("Excita"))
    assert len(errors) == 1
    assert "Excita" in errors[0]
    assert check(doc("Éxcita")) == []


def test_a_disyllable_is_never_marked():
    # Latin does not mark what cannot move.
    assert check(doc("Ecce", "Deus", "Qui")) == []


def test_an_accent_on_a_ligature_counts():
    # The first draft listed accented letters and reported both of these as
    # bare, because their accents ride on ligatures.
    assert accented("Fœ́deris") and accented("Bartholomǽi")
    assert check(doc("Fœ́deris", "Bartholomǽi")) == []


def test_declared_bare_names_are_left_alone():
    assert check(doc("Israël", "Ierúsalem")) == []


def test_lowercase_is_not_this_check_s_business():
    # The printing only drops the accent on capitals.
    assert check(doc("excita")) == []


def test_syllable_counting_sees_ligatures():
    assert syllables("Fœ́deris") == 3
    assert syllables("Ecce") == 2
