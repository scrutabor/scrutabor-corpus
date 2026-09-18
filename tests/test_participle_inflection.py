"""Impossible inflections fail without pretending to disambiguate context."""

import pytest

from checks.participle_inflection import check


def subject(form, case, number="sg", gender="f", tense="perf"):
    return {
        "id": "t",
        "segments": [
            {
                "words": [
                    {
                        "id": "w1",
                        "form": form,
                        "morph": {
                            "pos": "verb",
                            "mood": "part",
                            "tense": tense,
                            "case": case,
                            "number": number,
                            "gender": gender,
                        },
                    }
                ]
            }
        ],
    }


def test_impossible_cases_and_genders_fail():
    assert check(subject("dissolúta", "gen", gender="m"))
    assert check(subject("turbáta", "abl", gender="m"))
    assert check(subject("inténti", "acc", number="pl", gender="m"))


@pytest.mark.parametrize("case", ["nom", "abl", "voc"])
def test_compatible_ambiguities_remain_for_contextual_review(case):
    assert check(subject("dissolúta", case)) == []


def test_ligatures_enclitics_and_future_passives():
    assert check(subject("sanctificátæque", "gen")) == []
    assert check(subject("suménda", "acc", number="pl", gender="n", tense="fut")) == []
    assert check(subject("ascéndens", "nom", gender="m", tense="pres")) == []
