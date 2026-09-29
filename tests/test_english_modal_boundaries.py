"""Whitespace, punctuation and complement boundaries for direct modal glosses."""

import pytest

from checks.english import check
from checks.interlinear import check as check_interlinear


def _modal_case(right):
    source = {
        "id": "t.t",
        "segments": [
            {
                "id": "s01",
                "words": [
                    {"id": "w1", "lemma": "non", "form": "non", "morph": {"pos": "adv"}},
                    {"id": "w2", "lemma": "possum", "form": "potest", "morph": {"pos": "verb"}},
                ],
            }
        ],
    }
    layer = {"lang": "en", "words": {"w1": {"gloss": "not"}, "w2": {"gloss": right}}}
    return source, layer


@pytest.mark.parametrize(
    "right",
    [
        "can  not",
        "can\tnot",
        "can\nnot",
        "could  not",
        "could\tnot",
        "could\u00a0not",
        "could\u202fnot",
        "cannot.",
        "cannot!",
        "cannot?",
        "cannot;",
        "cannot:",
        "cannot,",
        "cannot…",
        "cannot)",
        "cannot”",
        "could not.",
        "couldn’t!",
        "cannot prevail",
        "he cannot do",
        "can’t enter",
        "we could not enter",
        "couldn’t return",
        "they can not see",
        "SHE COULD\tNOT ENTER",
    ],
)
def test_negative_modal_predicates_remain_negative_before_complements_or_punctuation(right):
    source, layer = _modal_case(right)
    errors = check(source, layer)
    assert len(errors) == 1
    assert "t.t:w1–w2" in errors[0] and "negation twice" in errors[0]


@pytest.mark.parametrize("subject", ["I", "you", "he", "she", "it", "we", "they"])
def test_existing_seven_pronoun_subjects_work_with_a_following_complement(subject):
    assert len(check(*_modal_case(subject + " cannot enter"))) == 1


@pytest.mark.parametrize(
    "right",
    [
        "can note",
        "can notice",
        "can notify",
        "could notate",
        "could notably prevail",
        "can nothing",
        "cannotary",
        "cannoté",
        "cannot_word",
        "can’tation",
        "couldn’tation",
    ],
)
def test_a_negative_modal_must_end_at_a_word_boundary(right):
    assert check(*_modal_case(right)) == []


@pytest.mark.parametrize(
    "right",
    [
        "he who cannot",
        "one who cannot",
        "we know he cannot",
        "whether they cannot",
        "I can say that he cannot",
        "hecannot",
        "itself cannot",
        "anyone cannot",
        "I myself cannot",
        "thou canst not",
    ],
)
def test_the_negative_predicate_must_begin_the_gloss_with_only_the_allowed_subject(right):
    assert check(*_modal_case(right)) == []


@pytest.mark.parametrize("right", ["can prevail", "could do", "he can enter", "we could return"])
def test_positive_modal_complements_do_not_trigger_a_second_negation(right):
    assert check(*_modal_case(right)) == []


def test_an_expanded_shared_predicate_is_not_read_as_duplicate_direct_glosses():
    source, layer = _modal_case("can")
    source["segments"][0]["words"].append(
        {"id": "w3", "lemma": "praevaleo", "form": "prævalére", "morph": {"pos": "verb"}}
    )
    layer["words"] = {"w1": {}, "w2": {}, "w3": {}}
    layer["segments"] = {
        "s01": {
            "alignments": [{"words": ["w1", "w2", "w3"], "anchor": "w2", "gloss": "cannot prevail"}]
        }
    }
    assert check_interlinear(source, layer) == []
    assert check(source, layer) == []
