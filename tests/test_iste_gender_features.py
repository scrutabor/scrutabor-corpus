"""Selected demonstrative genders retain contextual singular/plural distinctions."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from iste_gender_fixture import DATA, current_iste_expected_row
from marian_gospel_fixture import current_expected_row

from build_reader.layers import expand_core
from checks.lint import ISTA_FEATURE_TRIPLES, lint_text
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
READINGS = [
    ("nom", "sg", "f"),
    ("abl", "sg", "f"),
    ("nom", "pl", "n"),
    ("acc", "pl", "n"),
]
CASES = [
    ("annuntiatio-beatae-mariae-virginis-evangelium", "w058", "ista", "nom", "sg", "f"),
    ("annuntiatio-beatae-mariae-virginis-evangelium", "w120", "istud", "nom", "sg", "n"),
    ("beata-maria-virgo-regina-evangelium", "w058", "ista", "nom", "sg", "f"),
    ("beatae-mariae-virginis-a-rosario-evangelium", "w058", "ista", "nom", "sg", "f"),
    ("beatae-mariae-virginis-a-rosario-evangelium", "w120", "istud", "nom", "sg", "n"),
    ("nativitas-domini-in-aurora-graduale", "w016", "istud", "nom", "sg", "n"),
    ("septem-dolorum-beatae-mariae-virginis-sequentia", "w108", "istud", "acc", "sg", "n"),
    ("sancti-ioseph-opificis-evangelium", "w057", "ista", "nom", "pl", "n"),
    ("dominica-in-quinquagesima-evangelium", "w050", "istud", "nom", "sg", "n"),
]
CASE_IDS = [
    "annunciation-salutatio",
    "annunciation-event",
    "queenship-salutatio",
    "rosary-salutatio",
    "rosary-event",
    "aurora-subject",
    "stabat-object",
    "joseph-plural",
    "quinquagesima-verbum",
]


def diagnostic(word):
    if word["form"].lower() == "ista":
        return (
            f"{word['id']}: ista form {word['form']!r} (iste) requires feminine singular "
            "nominative or ablative, or neuter plural nominative or accusative"
        )
    return (
        f"{word['id']}: neuter pronoun form {word['form']!r} (iste) must be "
        "neuter singular nominative or accusative"
    )


def class_errors(form, lemma, morph):
    doc = {
        "segments": [
            {"id": "s01", "words": [{"id": "w001", "form": form, "lemma": lemma, "morph": morph}]}
        ]
    }
    errors, count = lint_text(doc)
    assert count == 1
    return [e for e in errors if "ista form" in e or "neuter pronoun form" in e]


def test_ordinary_ista_class_does_not_shrink_with_its_parameter_source():
    assert {
        ("nom", "sg", "f"),
        ("abl", "sg", "f"),
        ("nom", "pl", "n"),
        ("acc", "pl", "n"),
    } == ISTA_FEATURE_TRIPLES
    assert set(READINGS) == ISTA_FEATURE_TRIPLES


@pytest.mark.parametrize(
    "case,number,gender", READINGS, ids=["nom-sg-f", "abl-sg-f", "nom-pl-n", "acc-pl-n"]
)
@pytest.mark.parametrize("pos", ["pron", "adj"])
def test_ista_reading_rejects_each_missing_or_incompatible_feature_then_recovers(
    case, number, gender, pos
):
    morph = {"pos": pos, "case": case, "number": number, "gender": gender}
    baseline = deepcopy(morph)
    assert class_errors("ista", "iste", morph) == []
    for field, value in [
        ("case", None),
        ("number", None),
        ("gender", None),
        ("case", "gen"),
        ("number", "pl" if number == "sg" else "sg"),
        ("gender", "m"),
    ]:
        try:
            if value is None:
                morph.pop(field)
            else:
                morph[field] = value
            errors = class_errors("ista", "iste", morph)
            assert errors == [diagnostic({"id": "w001", "form": "ista"})]
        finally:
            morph.clear()
            morph.update(baseline)
        assert morph == baseline
        assert class_errors("ista", "iste", morph) == []


@pytest.mark.parametrize(
    "form,case,gender",
    [("Ista", "nom", "f"), ("Ísta", "abl", "f"), ("Istud", "nom", "n"), ("Ístud", "acc", "n")],
    ids=["ista-capital", "ista-folded-accent", "istud-capital", "istud-folded-accent"],
)
@pytest.mark.parametrize("pos", ["pron", "adj"])
def test_normalization_cannot_hide_the_named_diagnostic(form, case, gender, pos):
    # Only this class diagnostic is in scope; synthetic accents are not an
    # assertion that a two-syllable accented word passes all orthography rules.
    morph = {"pos": pos, "case": case, "number": "sg", "gender": gender}
    baseline = deepcopy(morph)
    assert class_errors(form, "iste", morph) == []
    try:
        morph.pop("gender")
        errors = class_errors(form, "iste", morph)
        assert len(errors) == 1 and "iste" in errors[0]
    finally:
        morph.clear()
        morph.update(baseline)
    assert class_errors(form, "iste", morph) == []


@pytest.mark.parametrize(
    "form,lemma,morph",
    [
        ("te", "tu", {"pos": "pron", "case": "acc", "number": "sg"}),
        ("nos", "nos", {"pos": "pron", "case": "nom", "number": "pl"}),
        ("sibi", "sui", {"pos": "pron", "case": "dat"}),
        ("ista", "alius", {"pos": "pron"}),
        ("ista", "iste", {"pos": "adv"}),
        ("istis", "iste", {"pos": "pron", "case": "abl", "number": "pl"}),
        ("isti", "iste", {"pos": "pron", "case": "dat", "number": "sg"}),
        ("isto", "iste", {"pos": "pron", "case": "dat", "number": "sg"}),
        ("hæc", "hic", {"pos": "pron", "case": "nom", "number": "pl"}),
        ("quæ", "qui", {"pos": "pron", "case": "nom", "number": "pl"}),
    ],
    ids=[
        "te",
        "nos",
        "sibi",
        "other-lemma",
        "other-pos",
        "istis",
        "rare-isti",
        "rare-isto",
        "haec-unsettled",
        "quae-unsettled",
    ],
)
def test_narrow_class_does_not_impose_gender_on_unowned_analyses(form, lemma, morph):
    # Scope exclusion, not a blanket approval of these synthetic analyses.
    assert class_errors(form, lemma, morph) == []


@pytest.mark.parametrize("name,wid,form,case,number,gender", CASES, ids=CASE_IDS)
@pytest.mark.parametrize("fault", ["missing", "masculine", "other-gender"])
def test_actual_context_gender_is_checked_and_restored_on_the_same_word(
    name, wid, form, case, number, gender, fault
):
    path = ROOT / "texts/proprium" / f"{name}.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    original = deepcopy(doc)
    word = next(w for s in doc["segments"] for w in s.get("words", []) if w["id"] == wid)
    morph = word["morph"]
    assert word["form"] == form and word["lemma"] == "iste"
    assert morph == {"pos": "pron", "case": case, "number": number, "gender": gender}
    expected_words = sum(len(s.get("words", [])) for s in doc["segments"])
    assert expected_words > 0
    assert lint_text(doc) == ([], expected_words)
    checked = expand_core(doc)
    visible = next(w for s in checked["segments"] for w in s.get("words", []) if w["id"] == wid)
    assert visible["morph"] == morph
    baseline = deepcopy(morph)
    try:
        if fault == "missing":
            morph.pop("gender")
        else:
            morph["gender"] = "m" if fault == "masculine" else ("n" if gender == "f" else "f")
        errors, count = lint_text(doc)
        assert count == expected_words and errors == [diagnostic(word)]
        assert word["morph"] is morph
    finally:
        morph.clear()
        morph.update(baseline)
    assert next(w for s in doc["segments"] for w in s.get("words", []) if w["id"] == wid) is word
    assert doc == original
    assert lint_text(doc) == ([], expected_words)


def test_source_binding_fixture_has_exact_seven_fields_and_ten_pending_rows():
    assert {(r["text"].split(".", 1)[1], r["word"]) for r in DATA["genders"]} == {
        ("annuntiatio-beatae-mariae-virginis-evangelium", "w058"),
        ("annuntiatio-beatae-mariae-virginis-evangelium", "w120"),
        ("beata-maria-virgo-regina-evangelium", "w058"),
        ("beatae-mariae-virginis-a-rosario-evangelium", "w058"),
        ("beatae-mariae-virginis-a-rosario-evangelium", "w120"),
        ("nativitas-domini-in-aurora-graduale", "w016"),
        ("septem-dolorum-beatae-mariae-virginis-sequentia", "w108"),
    }
    assert len(DATA["genders"]) == 7 and len(DATA["sources"]) == 5
    assert len(DATA["ledger_rows"]) == 10
    for case in DATA["ledger_rows"]:
        before, after = case["before"], case["after"]
        assert before["review"] == after["review"] == "working"
        assert before["source_sha256"] != after["source_sha256"]
        assert {k: v for k, v in before.items() if k != "source_sha256"} == {
            k: v for k, v in after.items() if k != "source_sha256"
        }


@pytest.mark.parametrize(
    "row_id",
    [
        "row-1",
        "row-2",
        "row-3",
        "row-4",
        "row-5",
        "row-6",
        "row-7",
        "row-8",
        "row-9",
        "row-10",
    ],
)
@pytest.mark.parametrize("fault", ["missing", "wrong", "extra"])
def test_historical_row_adapter_rejects_corruption_and_restores_same_input(row_id, fault):
    case = next(row for row in DATA["ledger_rows"] if row["id"] == row_id)
    row = deepcopy(case["before"])
    baseline = deepcopy(row)
    assert current_iste_expected_row(row) == case["after"] and row == baseline
    try:
        if fault == "missing":
            row.pop("source_sha256")
        elif fault == "wrong":
            row["source_sha256"] = "0" * 64
        else:
            row["unadmitted_gender_change"] = True
        with pytest.raises(AssertionError, match=r"^historical iste ledger row(?:\n|$)"):
            current_iste_expected_row(row)
    finally:
        row.clear()
        row.update(baseline)
    assert row == baseline
    assert current_iste_expected_row(row) == case["after"] and row == baseline


def reviewed_current_source(core, row, case):
    assert row == current_expected_row(case["before"]), "current iste source binding"
    segment = next(s for s in core["segments"] if s["id"] == row["segment"])
    assert canonical_hash(source_payload(segment)) == row["source_sha256"]


@pytest.mark.parametrize(
    "row_id",
    [
        "row-1",
        "row-2",
        "row-3",
        "row-4",
        "row-5",
        "row-6",
        "row-7",
        "row-8",
        "row-9",
        "row-10",
    ],
)
def test_actual_source_binding_and_unchanged_claims_reject_then_recover(row_id):
    case = next(r for r in DATA["ledger_rows"] if r["id"] == row_id)
    expected = case["after"]
    name = expected["text"].split(".", 1)[1]
    core = json.loads((ROOT / "texts/proprium" / f"{name}.json").read_text())
    ledger = json.loads(
        (ROOT / "languages" / expected["language"] / "translation-provenance.json").read_text()
    )
    row = next(r for r in ledger["sites"] if r["site"] == expected["site"])
    baseline = deepcopy(row)
    reviewed_current_source(core, row, case)
    for field, value in [
        ("source_sha256", None),
        ("source_sha256", "0" * 64),
        ("review", "approved"),
    ]:
        try:
            if value is None:
                row.pop(field)
            else:
                row[field] = value
            with pytest.raises(AssertionError, match=r"^current iste source binding(?:\n|$)"):
                reviewed_current_source(core, row, case)
        finally:
            row.clear()
            row.update(baseline)
        assert next(r for r in ledger["sites"] if r["site"] == expected["site"]) is row
        reviewed_current_source(core, row, case)
