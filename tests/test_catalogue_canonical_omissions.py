"""Canonical calendar inputs bind the complete source-owned reader catalogue."""

import copy
from pathlib import Path

import pytest

from build_reader import commemorationes as commemoration_reader
from build_reader import dismissal as dismissal_reader
from build_reader import emit, store
from kalendarium import commemorationes as commemoration_producer
from kalendarium import dismissal as dismissal_producer

ROOT = Path(__file__).resolve().parents[1]
OMITTED = {
    "dominica-i-passionis",
    "dominica-ii-passionis",
    "feria-v-in-cena-domini",
    "commemoratio-omnium-fidelium-defunctorum",
    "commemoratio-omnium-fidelium-defunctorum-missa-ii",
    "commemoratio-omnium-fidelium-defunctorum-missa-iii",
}
CONSUMERS = ("dismissal", "commemorationes")
FAULTS = (
    "missing-retention-field",
    "missing-prescription",
    "removed-prescription",
    "added-prescription",
    "foreign-omission",
    "dotted-notation",
    "extra-segment",
    "unknown-row-field",
    "forged-date",
)
CASES = [(consumer, fault) for consumer in CONSUMERS for fault in FAULTS]


@pytest.fixture(scope="module")
def actual_inputs():
    return dismissal_producer.canonical_inputs(ROOT)


@pytest.fixture(scope="module")
def actual_tables(actual_inputs):
    forms, calendar = actual_inputs
    saved = copy.deepcopy(actual_inputs)
    tables = {
        "dismissal": dismissal_producer.calendar_table(forms, calendar, corpus=ROOT),
        "commemorationes": commemoration_producer.calendar_table(forms, calendar, corpus=ROOT),
    }
    assert actual_inputs == saved
    return tables


def producer(name):
    return dismissal_producer if name == "dismissal" else commemoration_producer


def test_all_authored_fields_and_both_omission_shapes_project_independently(actual_inputs):
    authored = sorted(store.formularies(ROOT), key=lambda row: row["order"])
    saved = copy.deepcopy(authored)
    expected = []
    for doc in authored:
        row = {k: copy.deepcopy(v) for k, v in doc.items() if k != "formulary_schema"}
        for component in row["components"]:
            component["text"] = component["text"].replace(".", "/", 1)
        if doc["id"] in OMITTED:
            assert doc["ordinary_omissions"] == [
                {
                    "text": "ordinarium.lavabo",
                    "segments": ["s09", "s10"],
                    "reason": "lavabo-doxology",
                }
            ]
            row["ordinary_omissions"] = [
                {
                    "text": "ordinarium/lavabo",
                    "segments": ["s09", "s10"],
                    "reason": "lavabo-doxology",
                }
            ]
        else:
            assert "ordinary_omissions" not in doc
            row["ordinary_omissions"] = []
        expected.append(row)
    forms, calendar = actual_inputs
    assert len(expected) == 114
    assert sum(bool(row["ordinary_omissions"]) for row in expected) == 6
    assert sum(not row["ordinary_omissions"] for row in expected) == 108
    assert forms == expected == emit.formulary_catalog(ROOT)["formularies"]
    assert calendar == emit.kalendarium()
    assert authored == saved


@pytest.mark.parametrize("consumer", CONSUMERS)
def test_real_emitted_catalogue_is_valid_for_both_strict_consumers(
    actual_inputs, actual_tables, consumer
):
    forms = emit.formulary_catalog(ROOT)["formularies"]
    calendar = emit.kalendarium()
    saved = copy.deepcopy((forms, calendar))
    actual = producer(consumer).calendar_table(forms, calendar, corpus=ROOT)
    expected = (
        dismissal_reader.expected(ROOT)
        if consumer == "dismissal"
        else commemoration_reader.expected(ROOT)
    )
    assert actual == expected == actual_tables[consumer]
    assert (forms, calendar) == saved == actual_inputs


@pytest.mark.parametrize(
    "consumer,fault", CASES, ids=[consumer + "-" + fault for consumer, fault in CASES]
)
def test_forged_omission_or_calendar_is_rejected_and_same_inputs_recover(
    actual_inputs, actual_tables, consumer, fault
):
    forms, calendar = copy.deepcopy(actual_inputs)
    saved_forms, saved_calendar = copy.deepcopy((forms, calendar))
    omitted = next(row for row in forms if row["id"] == "dominica-i-passionis")
    retained = next(row for row in forms if row["id"] == "vigilia-paschalis")
    assert (
        producer(consumer).calendar_table(forms, calendar, corpus=ROOT) == actual_tables[consumer]
    )
    try:
        if fault == "missing-retention-field":
            del retained["ordinary_omissions"]
        elif fault == "missing-prescription":
            del omitted["ordinary_omissions"]
        elif fault == "removed-prescription":
            omitted["ordinary_omissions"] = []
        elif fault == "added-prescription":
            retained["ordinary_omissions"] = copy.deepcopy(omitted["ordinary_omissions"])
        elif fault == "foreign-omission":
            omitted["ordinary_omissions"][0]["text"] = "ordinarium/gloria"
        elif fault == "dotted-notation":
            omitted["ordinary_omissions"][0]["text"] = "ordinarium.lavabo"
        elif fault == "extra-segment":
            omitted["ordinary_omissions"][0]["segments"].insert(0, "s08")
        elif fault == "unknown-row-field":
            retained["caller_owned"] = True
        else:
            day = calendar["years"]["2027"][0]
            day[0] = "2027-03-28" if day[0] != "2027-03-28" else "2027-03-27"
        assert (forms, calendar) != (saved_forms, saved_calendar)
        with pytest.raises(ValueError, match="inputs differ from canonical authored"):
            producer(consumer).calendar_table(forms, calendar, corpus=ROOT)
    finally:
        for form, saved in zip(forms, saved_forms, strict=True):
            form.clear()
            form.update(copy.deepcopy(saved))
        calendar.clear()
        calendar.update(copy.deepcopy(saved_calendar))
    assert (forms, calendar) == (saved_forms, saved_calendar)
    assert (
        producer(consumer).calendar_table(forms, calendar, corpus=ROOT) == actual_tables[consumer]
    )
    assert actual_inputs == (saved_forms, saved_calendar)
