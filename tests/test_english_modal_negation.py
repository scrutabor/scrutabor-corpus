"""Regression candidate: precise direct English modal-negation junctions."""

from copy import deepcopy

import pytest

from checks.english import check
from checks.interlinear import check as check_interlinear


def _modal_document():
    return {
        "id": "t.t",
        "segments": [
            {
                "id": "s01",
                "type": "verse",
                "words": [
                    {"id": "w1", "form": "non", "lemma": "non", "morph": {"pos": "adv"}},
                    {
                        "id": "w2",
                        "form": "potest",
                        "lemma": "possum",
                        "morph": {"pos": "verb"},
                    },
                ],
            }
        ],
    }


def _modal_layer(left="not", right="cannot", language="en"):
    return {"lang": language, "words": {"w1": {"gloss": left}, "w2": {"gloss": right}}}


@pytest.mark.parametrize("negative", ["cannot", "can not", "can’t", "could not", "couldn’t"])
@pytest.mark.parametrize("subject", ["", "I ", "you ", "he ", "she ", "it ", "we ", "they "])
def test_ordinary_english_gate_rejects_duplicate_modal_negation(negative, subject):
    errors = check(_modal_document(), _modal_layer("not", subject + negative))
    assert len(errors) == 1
    assert "t.t:w1–w2" in errors[0]
    assert "negation twice" in errors[0]


def test_modal_match_is_case_insensitive_and_strips_outer_space():
    errors = check(_modal_document(), _modal_layer("  NoT\t", "  SHE\tCOULD NOT  "))
    assert len(errors) == 1
    assert "negation twice" in errors[0]


@pytest.mark.parametrize("right", ["can", "could", "he can", "can do", "could prevail", "is able"])
def test_a_single_negative_with_positive_modal_is_retained(right):
    assert check(_modal_document(), _modal_layer("not", right)) == []


@pytest.mark.parametrize("language", ["pl", "la", "fr", None])
def test_modal_check_obeys_ordinary_language_dispatch(language):
    assert check(_modal_document(), _modal_layer(language=language)) == []


def test_modal_check_does_not_cross_segment_boundaries():
    source = _modal_document()
    first, second = source["segments"][0]["words"]
    source["segments"] = [{"id": "s01", "words": [first]}, {"id": "s02", "words": [second]}]
    assert check(source, _modal_layer()) == []


def test_modal_check_does_not_skip_intervening_latin_words():
    source = _modal_document()
    source["segments"][0]["words"].insert(
        1, {"id": "w3", "form": "enim", "lemma": "enim", "morph": {"pos": "conj"}}
    )
    layer = _modal_layer()
    layer["words"]["w3"] = {"gloss": "for"}
    assert check(source, layer) == []


@pytest.mark.parametrize("position,lemma", [(0, "nemo"), (0, "neque"), (1, "volo"), (1, "sum")])
def test_other_latin_lemmas_are_outside_the_modal_guard(position, lemma):
    source = _modal_document()
    source["segments"][0]["words"][position]["lemma"] = lemma
    assert check(source, _modal_layer()) == []


@pytest.mark.parametrize("left", ["not only", "not yet", "by no means", "never"])
def test_the_guard_does_not_infer_the_scope_of_complex_negation(left):
    assert check(_modal_document(), _modal_layer(left, "cannot")) == []


def test_shared_modal_alignment_is_one_realization():
    layer = {
        "lang": "en",
        "words": {"w1": {}, "w2": {}},
        "segments": {
            "s01": {"alignments": [{"words": ["w1", "w2"], "anchor": "w2", "gloss": "cannot"}]}
        },
    }
    assert check_interlinear(_modal_document(), layer) == []
    assert check(_modal_document(), layer) == []


def test_zero_realization_is_not_a_second_direct_gloss():
    layer = _modal_layer()
    layer["words"]["w1"] = {}
    layer["segments"] = {"s01": {"alignments": [{"words": ["w1"], "reason": "idiom"}]}}
    assert check_interlinear(_modal_document(), layer) == []
    assert check(_modal_document(), layer) == []


def test_later_segment_is_checked_and_inputs_are_unchanged():
    source = _modal_document()
    source["segments"].insert(0, {"id": "intro", "words": []})
    layer = _modal_layer()
    before = deepcopy((source, layer))
    assert len(check(source, layer)) == 1
    assert (source, layer) == before


def test_conflicting_direct_and_shared_realizations_are_not_silently_accepted():
    layer = _modal_layer()
    layer["segments"] = {
        "s01": {"alignments": [{"words": ["w1", "w2"], "anchor": "w2", "gloss": "cannot"}]}
    }
    errors = check_interlinear(_modal_document(), layer)
    assert len(errors) == 2
    assert all("expected exactly one direct gloss or alignment" in error for error in errors)
