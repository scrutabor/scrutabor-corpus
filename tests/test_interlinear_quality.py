"""Reader-visible interlinear corruption must not return."""

import pytest

from checks.interlinear_quality import check

DOC = {"id": "t.t"}


def layer(language, text):
    return {"language": language, "words": {"w1": {"gloss": text}}}


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


def test_dictionary_asides_do_not_leak_into_inline_glosses():
    for text in ("the Lord (of God)", "you (more than one)", "persecution (esp. of Christians)"):
        assert check(DOC, layer("en", text))
    for text in ("the Lord", "you", "persecution", "is risen"):
        assert check(DOC, layer("en", text)) == []


def test_structural_absorption_marker_is_rejected():
    assert check(DOC, layer("en", "[included]"))
    assert check(DOC, layer("pl", "[dopełnienie]"))
    assert check(DOC, layer("pl", "—"))


def test_no_polish_auxiliary_marker_is_reader_wording():
    assert check(DOC, layer("pl", "[czas posiłkowy]"))
    assert check(DOC, layer("pl", "[pomocnicze]"))
    assert check(DOC, layer("pl", "[auxiliary]"))
    assert check(DOC, layer("pl", "[czasownik posiłkowy]"))


def future_periphrastic_doc():
    return {
        "id": "t.future",
        "segments": [
            {
                "id": "s01",
                "words": [
                    {
                        "id": "w1",
                        "lemma": "sum",
                        "morph": {"pos": "verb", "mood": "ind", "tense": "pres"},
                    },
                    {
                        "id": "w2",
                        "lemma": "sum",
                        "morph": {"pos": "verb", "mood": "part", "tense": "fut"},
                    },
                ],
            }
        ],
    }


def future_layer(language, first, second):
    return {
        "language": language,
        "words": {"w1": {"gloss": first}, "w2": {"gloss": second}},
    }


def test_authored_and_enriched_language_fields_activate_the_checks():
    assert check(DOC, {"language": "en", "words": {"w1": {"gloss": "one/two"}}})
    assert check(DOC, {"lang": "en", "words": {"w1": {"gloss": "one/two"}}})


def test_future_periphrastic_cannot_duplicate_its_auxiliary():
    doc = future_periphrastic_doc()
    assert check(doc, future_layer("pl", "jest", "będzie"))
    assert check(doc, future_layer("en", "is", "shall be"))
    assert check(doc, future_layer("pl", "[czasownik posiłkowy]", "będzie"))
    assert check(doc, future_layer("en", "[auxiliary]", "shall be"))


def word_doc(form):
    return {"id": "t.t", "segments": [{"id": "s01", "words": [{"id": "w1", "form": form}]}]}


@pytest.mark.parametrize(
    "language,bare,complete",
    [
        ("pl", "Tobą", "z Tobą"),
        ("en", "Thee", "with Thee"),
        ("en", "thee", "with thee"),
        ("en", "you", "with you"),
    ],
)
def test_tecum_does_not_drop_its_fused_preposition(language, bare, complete):
    assert check(word_doc("tecum"), layer(language, bare))
    assert check(word_doc("Tecum"), layer(language, complete)) == []
    assert check(word_doc("te"), layer(language, bare)) == []


def test_idiomatic_cum_and_explicit_alignment_are_not_overcorrected():
    assert check(word_doc("nobíscum"), layer("pl", "nam")) == []
    assert check(word_doc("Tecum"), layer("pl", "Przy Tobie")) == []
    shared = layer("pl", "")
    shared["segments"] = {
        "s01": {"alignments": [{"words": ["w1", "w2"], "anchor": "w1", "gloss": "wspólnie z Tobą"}]}
    }
    assert check(word_doc("tecum"), shared) == []


@pytest.mark.parametrize("language,copula,pronoun", [("pl", "jest", "jego"), ("en", "is", "his")])
def test_eius_is_not_a_copula(language, copula, pronoun):
    assert check(word_doc("eius"), layer(language, copula))
    assert check(word_doc("eius"), layer(language, pronoun)) == []
    assert check(word_doc("est"), layer(language, copula)) == []
