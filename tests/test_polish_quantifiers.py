"""Polish numeral government can differ from the Latin noun's case."""

import pytest

from checks.polish import _numeral_government, check_prepositions


def phrase(preposition, quantity, noun, *, linked=True):
    doc = {
        "id": "example.quantity",
        "segments": [
            {
                "words": [
                    {"id": "w1", "form": "in", "morph": {"pos": "prep"}, "head": "w3"},
                    {
                        "id": "w2",
                        "form": "multis",
                        "morph": {"pos": "adj"},
                        "head": "w3" if linked else "w4",
                    },
                    {"id": "w3", "form": "argumentis", "morph": {"pos": "noun"}},
                ]
            }
        ],
    }
    gloss = {
        "words": {
            key: {"gloss": value}
            for key, value in zip(("w1", "w2", "w3"), (preposition, quantity, noun), strict=True)
        }
    }
    return doc, gloss


@pytest.mark.parametrize("quantity", ["wiele", "kilka", "pięć"])
def test_accusative_quantity_governs_genitive_noun(quantity):
    assert check_prepositions(*phrase("przez", quantity, "dowodów")) == []


@pytest.mark.parametrize(
    "preposition,quantity,noun",
    [
        ("dzięki", "wielu", "dowodom"),
        ("z", "wieloma", "dowodami"),
        ("bez", "wielu", "dowodów"),
    ],
)
def test_oblique_quantity_agrees_with_noun(preposition, quantity, noun):
    assert check_prepositions(*phrase(preposition, quantity, noun)) == []


@pytest.mark.parametrize(
    "preposition,quantity,noun",
    [
        ("przez", "wiele", "dowodom"),
        ("przez", "wiele", "dowody"),
        ("dzięki", "wiele", "dowodów"),
        ("przez", "wieloma", "dowody"),
        ("z", "wieloma", "dowodów"),
    ],
)
def test_quantity_does_not_hide_wrong_government(preposition, quantity, noun):
    assert check_prepositions(*phrase(preposition, quantity, noun))


def test_unrelated_quantity_does_not_excuse_a_bad_object():
    assert check_prepositions(*phrase("przez", "wiele", "dowodów", linked=False))


@pytest.mark.parametrize(
    "quantity,noun", [("wielu", "dowodów"), ("dwóch", "dowodów"), ("pięć", "dowodu")]
)
def test_gender_and_number_remain_correlated_with_case(quantity, noun):
    assert check_prepositions(*phrase("przez", quantity, noun))


@pytest.mark.parametrize(
    "quantity,noun",
    [("wielu", "świadków"), ("pięć", "dowodów"), ("wiele", "wody"), ("dwa", "dowody")],
)
def test_personal_plural_mass_and_agreeing_numerals_are_supported(quantity, noun):
    assert check_prepositions(*phrase("przez", quantity, noun)) == []


def test_combined_government_modes_keep_both_readings():
    modes = {
        mode
        for number, case, _, mode in _numeral_government("pół")
        if number == frozenset({"sg"}) and {"dat", "inst", "loc"} <= case
    }
    assert modes == {"congr", "rec"}
