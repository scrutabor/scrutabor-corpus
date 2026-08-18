"""The introit rubric gate: watched failing before it landed."""

from checks.incipit import check, fold


def introit(opening: str, rubric: str) -> dict:
    return {
        "id": "proprium.test-introitus",
        "segments": [
            {
                "id": "s01",
                "type": "verse",
                "words": [{"id": f"w{i:03d}", "form": f} for i, f in enumerate(opening.split(), 1)],
            },
            {"id": "s04", "type": "rubric", "text": rubric},
        ],
    }


def test_the_rubric_naming_another_sundays_antiphon_fails():
    errors = check(
        introit("Gaudéte in Dómino semper", "Quo finito, repetitur Ad te levávi usque ad psalmum.")
    )
    assert len(errors) == 1
    assert "Ad te levávi" in errors[0]
    assert "Gaudéte" in errors[0]


def test_the_rubric_naming_its_own_antiphon_passes():
    assert (
        check(
            introit("Gaudéte in Dómino semper", "Quo finito, repetitur Gaudéte usque ad psalmum.")
        )
        == []
    )


def test_a_quoted_incipit_may_drop_the_acute_a_heading_drops():
    assert (
        check(introit("Roráte cæli désuper", "Quo finito, repetitur Rorate usque ad psalmum."))
        == []
    )


def test_a_text_with_no_such_rubric_is_not_this_checks_business():
    doc = introit("Ad te levávi", "Hic genuflectitur.")
    assert check(doc) == []


def test_a_text_with_no_words_reports_nothing_rather_than_raising():
    assert (
        check(
            {
                "id": "x",
                "segments": [
                    {"id": "s01", "type": "rubric", "text": "repetitur X usque ad psalmum"}
                ],
            }
        )
        == []
    )


def test_fold_removes_accents_and_punctuation():
    assert fold("Pópulus Sion,") == "populus sion"
