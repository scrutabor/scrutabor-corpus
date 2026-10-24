"""Quiet priestly recitation does not replace or silence the sung participation."""

import copy
import json
from pathlib import Path

import pytest

from checks.delivery import check_doc, derive
from checks.participation_performance import publication_errors

CORPUS = Path(__file__).resolve().parent.parent
ROWS = ["s02", "s03", "s04", "s05", "s06"]


def subject():
    return json.loads((CORPUS / "texts/ordinarium/sanctus.json").read_text(encoding="utf-8"))


def test_actual_source_keeps_the_priest_and_derives_only_the_quiet_sung_voice():
    doc = subject()
    assert check_doc(doc) == ([], 5)
    assert publication_errors(doc) == []
    assert derive(doc, doc["segments"][0]) == {}
    for row in doc["segments"][1:]:
        assert (row["speaker"], row["voice"]) == ("sacerdos", "clara")
        assert derive(doc, row) == row["delivery"] == {"cantu": {"voice": "secreto"}}
        assert row["participation"]["cantu"]["performance"]["speaker"] == "schola"


@pytest.mark.parametrize("identity", ROWS)
@pytest.mark.parametrize("mutation", ["clara", "missing", "choir", "lecta", "extra"])
def test_each_priest_delivery_rejects_voice_role_and_scope_substitution(identity, mutation):
    doc = subject()
    row = next(s for s in doc["segments"] if s["id"] == identity)
    if mutation == "clara":
        row["delivery"]["cantu"]["voice"] = "clara"
    elif mutation == "missing":
        del row["delivery"]
    elif mutation == "choir":
        row["delivery"]["cantu"] = {"speaker": "schola", "voice": "cantus"}
    elif mutation == "lecta":
        row["delivery"] = {"lecta": {"voice": "secreto"}}
    else:
        row["delivery"]["cantu"]["speaker"] = "sacerdos"
    assert check_doc(doc)[0]
    assert publication_errors(doc)


def test_missing_all_quiet_overrides_is_not_an_absent_feature_default():
    doc = subject()
    for row in doc["segments"][1:]:
        del row["delivery"]
    errors, _ = check_doc(doc)
    assert len(errors) == 5
    assert len(publication_errors(doc)) == 5


def test_rubric_and_lookalike_text_cannot_gain_the_priestly_rule():
    doc = subject()
    rubric = doc["segments"][0]
    rubric["delivery"] = {"cantu": {"voice": "secreto"}}
    assert check_doc(doc)[0]
    lookalike = copy.deepcopy(doc)
    lookalike["id"] = "ordinarium.lookalike"
    assert all(derive(lookalike, row) == {} for row in lookalike["segments"])
