"""Source markup and Alleluia agreement between a translation and its Latin."""

import pytest

from checks.translation_integrity import check


def latin(*forms, kind="verse"):
    return {
        "id": "proprium.example",
        "segments": [
            {
                "id": "s01",
                "type": kind,
                "words": [{"id": f"w{i:03d}", "form": f} for i, f in enumerate(forms, 1)],
            }
        ],
    }


def layer(language, text):
    return {
        "text": "proprium.example",
        "language": language,
        "segments": {"s01": {"translation": text}},
    }


ANTIPHON = latin("Gaudéte", "in", "Dómino", "allelúia.")


@pytest.mark.parametrize(
    "text", ["@Sancti/04-25:Lectio1", "Radujcie się. ~(Alleluja.)", "$Per Dominum"]
)
def test_source_markup_is_refused(text):
    assert any("source markup" in e for e in check(ANTIPHON, layer("pl", text)))


def test_an_alleluia_the_latin_lacks_is_refused():
    errors = check(
        latin("Gaudéte", "in", "Dómino."), layer("en", "Rejoice in the Lord. (Alleluia.)")
    )
    assert any("1 Alleluia(s) in the translation, 0 in the Latin" in e for e in errors)


def test_an_alleluia_the_latin_has_must_be_translated():
    errors = check(ANTIPHON, layer("pl", "Radujcie się w Panu."))
    assert any("0 Alleluia(s) in the translation, 1 in the Latin" in e for e in errors)


@pytest.mark.parametrize(
    "language,text",
    [("en", "Rejoice in the Lord, allelúja."), ("pl", "Radujcie się w Panu, alleluia.")],
)
def test_each_language_spells_alleluia_its_own_way(language, text):
    assert any("spelled" in e for e in check(ANTIPHON, layer(language, text)))


def test_an_alleluia_that_runs_into_the_next_sentence_is_refused():
    doc = latin("Allelúia,", "allelúia.", "Gaudéte.")
    assert any("runs on" in e for e in check(doc, layer("pl", "Alleluja, alleluja Radujcie się.")))
    assert check(doc, layer("pl", "Alleluja, alleluja. Radujcie się.")) == []


def test_matching_translations_pass():
    assert check(ANTIPHON, layer("en", "Rejoice in the Lord, alleluia.")) == []
    assert check(ANTIPHON, layer("pl", "Radujcie się w Panu, alleluja.")) == []


def test_rubrics_are_not_counted():
    doc = latin("allelúia", kind="rubric")
    assert check(doc, layer("en", "The Alleluia is omitted.")) == []
