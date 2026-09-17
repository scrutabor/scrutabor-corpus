"""Reader-visible interlinear corruption must not return."""

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


def test_structural_absorption_marker_is_allowed():
    assert check(DOC, layer("en", "[included]")) == []
    assert check(DOC, layer("pl", "[dopełnienie]")) == []


def test_polish_auxiliary_marker_is_canonical():
    assert check(DOC, layer("pl", "[czas posiłkowy]"))
    assert check(DOC, layer("pl", "[pomocnicze]"))
    assert check(DOC, layer("pl", "[auxiliary]"))
    assert check(DOC, layer("pl", "[czasownik posiłkowy]")) == []


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
    assert check(doc, future_layer("pl", "[czasownik posiłkowy]", "będzie")) == []
    assert check(doc, future_layer("en", "[auxiliary]", "shall be")) == []
