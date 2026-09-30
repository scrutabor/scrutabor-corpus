"""A reflexive subject must not masquerade as a conjunction."""

from copy import deepcopy

import pytest

from checks import polish


def example():
    doc = {
        "id": "test.aci",
        "segments": [
            {
                "id": "s01",
                "words": [
                    {
                        "id": "w001",
                        "form": "se",
                        "lemma": "sui",
                        "morph": {"pos": "pron", "case": "acc"},
                    }
                ],
            }
        ],
    }
    gloss = {"lang": "pl", "words": {"w001": {"gloss": "że"}}, "segments": {"s01": {}}}
    return doc, gloss


def matches(doc, gloss):
    return [error for error in polish.check(doc, gloss) if "replaces a reflexive pronoun" in error]


def test_dispatch_invokes_the_rule(monkeypatch):
    doc, gloss = example()
    assert len(matches(doc, gloss)) == 1
    monkeypatch.setattr(polish, "check_reflexive_marker", lambda *_: [])
    assert matches(doc, gloss) == []


@pytest.mark.parametrize("value", ["że", "ŻE", "  że\t", "Z\u0307E\u00a0"])
def test_target_case_unicode_and_spacing(value):
    doc, gloss = example()
    gloss["words"]["w001"]["gloss"] = value
    assert len(matches(doc, gloss)) == 1


@pytest.mark.parametrize("value", ["se", "Se", " SE\t"])
def test_source_case_and_spacing(value):
    doc, gloss = example()
    doc["segments"][0]["words"][0]["form"] = value
    assert len(matches(doc, gloss)) == 1


@pytest.mark.parametrize(
    "value", ["siebie", "się", "że on", "że oni", "żeby", "gdy", "that", None, ""]
)
def test_other_realizations_are_not_judged(value):
    doc, gloss = example()
    gloss["words"]["w001"]["gloss"] = value
    assert matches(doc, gloss) == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("lemma", "ego"),
        ("lemma", "si"),
        ("form", "sese"),
        ("pos", "conj"),
        ("case", "abl"),
        ("case", "dat"),
    ],
)
def test_only_declared_latin_scope_is_judged(field, value):
    doc, gloss = example()
    word = doc["segments"][0]["words"][0]
    (word if field in {"lemma", "form"} else word["morph"])[field] = value
    assert matches(doc, gloss) == []


@pytest.mark.parametrize(
    "group",
    [
        {"words": ["w001", "w002"], "anchor": "w002", "gloss": "że widzi"},
        {"words": ["w001"], "reason": "inflection"},
    ],
)
def test_shared_and_zero_providers_are_left_to_alignment_check(group):
    doc, gloss = example()
    gloss["segments"]["s01"]["alignments"] = [deepcopy(group)]
    del gloss["words"]["w001"]["gloss"]
    assert matches(doc, gloss) == []


def test_alignment_membership_does_not_leak_between_segments():
    doc, gloss = example()
    gloss["segments"]["s02"] = {"alignments": [{"words": ["w001"], "reason": "inflection"}]}
    assert len(matches(doc, gloss)) == 1


def test_a_group_does_not_hide_other_direct_words():
    doc, gloss = example()
    gloss["segments"]["s01"]["alignments"] = [{"words": ["w002"], "reason": "inflection"}]
    assert len(matches(doc, gloss)) == 1


@pytest.mark.parametrize("lang", ["en", "la", None])
def test_only_polish_dispatch(lang):
    doc, gloss = example()
    gloss["lang"] = lang
    assert polish.check(doc, gloss) == []


def test_absent_provider_and_empty_documents():
    doc, gloss = example()
    del gloss["words"]["w001"]
    assert matches(doc, gloss) == []
    assert polish.check_reflexive_marker({"segments": []}, {}) == []


def test_absent_morphology_is_not_invented():
    doc, gloss = example()
    del doc["segments"][0]["words"][0]["morph"]
    assert polish.check_reflexive_marker(doc, gloss) == []


@pytest.mark.parametrize(
    "value",
    [
        "że,",
        "że.",
        "„że”",
        '"że"',
        "(że)",
        "że—",
        "…że…",
        "[że]",
        "« ŻE »",
        "‘że’",
        "。że。",
        "( Z\u0307E\u00a0 )",
        "– że –",
        "że:",
    ],
)
def test_punctuated_conjunction_still_loses_the_reflexive_subject(value):
    doc, gloss = example()
    gloss["words"]["w001"]["gloss"] = value
    assert len(matches(doc, gloss)) == 1


@pytest.mark.parametrize(
    "value",
    [
        "że on",
        "że będzie",
        "(że on)",
        "że-on",
        "ż-e",
        "ż.e",
        "że1",
        "1że",
        "że+",
        "+że",
        "że🙂",
        "żę",
        "(się)",
        "",
        "…",
        " () ",
    ],
)
def test_internal_content_is_not_erased(value):
    doc, gloss = example()
    gloss["words"]["w001"]["gloss"] = value
    assert matches(doc, gloss) == []


@pytest.mark.parametrize("value", ["se,", "(se)", "s-e", "sese"])
def test_source_scope_is_not_broadened(value):
    doc, gloss = example()
    doc["segments"][0]["words"][0]["form"] = value
    assert matches(doc, gloss) == []
