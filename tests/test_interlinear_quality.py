"""Reader-visible interlinear corruption must not return."""

from checks.interlinear_quality import check

DOC = {"id": "t.t"}


def layer(language, text):
    return {"lang": language, "words": {"w1": {"gloss": text}}}


def test_corruption_marker_is_rejected_in_each_language():
    assert check(DOC, layer("pl", "Ń"))
    assert check(DOC, layer("en", "UNRESOLVED"))


def test_english_dictionary_choice_list_is_not_a_contextual_gloss():
    assert check(DOC, layer("en", "cock, rooster"))
    assert check(DOC, layer("en", "nearly/almost"))
    assert check(DOC, layer("en", "but; however"))
    assert check(DOC, layer("en", "cock")) == []


def test_duplicated_english_plural_suffix_is_rejected():
    assert check(DOC, layer("en", "ageses"))
    assert check(DOC, layer("en", "taxeses"))
    assert check(DOC, layer("en", "ages")) == []


def test_structural_absorption_marker_is_allowed():
    assert check(DOC, layer("en", "[included]")) == []
    assert check(DOC, layer("pl", "[dopełnienie]")) == []
