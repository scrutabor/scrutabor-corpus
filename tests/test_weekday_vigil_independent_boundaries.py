"""Weekday Vigil authored/transport boundaries and selected source-rule projections.

Out-of-span years project the selected 1962 rules, NOT historical Ordos or
an expansion of the shipped range. No catalogue/body stand-ins are allowed.
"""

import copy
from datetime import date, timedelta
from pathlib import Path

import pytest

from build_reader import commemorationes as reader
from build_reader import store
from kalendarium import commemorationes as producer
from kalendarium import dismissal, roman, temporale
from kalendarium import weekday_vigil as vigil
from kalendarium.computus import easter

ROOT = Path(store.__file__).resolve().parent.parent


def test_authored_preflight_rejects_transport_addresses_and_real_consumers_recover():
    docs = producer.authored(ROOT)  # Genuine full catalogue; no partial/dummy fixture.
    authored = store.formularies(ROOT)
    forms, calendar = dismissal.canonical_inputs(ROOT)
    assert vigil.require_inputs(ROOT, docs, authored, True)
    assert authored != forms
    with pytest.raises(ValueError) as caught:
        vigil.require_inputs(ROOT, docs, forms, True)
    assert str(caught.value) == (
        "commemorationes: Ascension Vigil requires its exact collecta reference"
    )
    assert vigil.require_inputs(ROOT, docs, authored, True)
    # Both real callers must feed authored IDs into the strict helper while
    # preserving their canonical slash-addressed inputs and equality boundary.
    actual = producer.calendar_table(forms, calendar, corpus=ROOT)
    assert actual == reader.expected(ROOT)
    assert actual["schema_version"] == "2.1.0"


@pytest.mark.parametrize(
    "identity,place",
    [
        ("ascensio-domini", 3),
        ("epiphania-domini", 3),
        ("vigilia-nativitatis", 5),
        ("in-octava-nativitatis", 5),
    ],
)
def test_selected_literal_table_places_reject_inherited_fallback_and_recover(
    monkeypatch, identity, place
):
    day = next(day for day in temporale.year(2026) if day.formulary == identity)
    assert roman._temporal_precedence(day) == place
    actual = roman._temporal_precedence
    with monkeypatch.context() as context:
        context.setattr(roman, "_temporal_precedence", lambda d: 6 if d == day else actual(d))
        with pytest.raises(AssertionError):
            assert roman._temporal_precedence(day) == place
    assert roman._temporal_precedence(day) == place


def test_selected_ordinal_repairs_preserve_all_existing_collision_results(monkeypatch):
    # A regression observation against the exact inherited four-key behavior,
    # not an independent historical/whole-precedence oracle. The new Vigil's
    # place21 branch remains active in both sides of this comparison.
    changed = {
        "ascensio-domini",
        "epiphania-domini",
        "vigilia-nativitatis",
        "in-octava-nativitatis",
    }
    years = range(2026, 2102)
    actual = roman._temporal_precedence
    proposed = {year: roman.year(year) for year in years}
    with monkeypatch.context() as context:
        context.setattr(
            roman,
            "_temporal_precedence",
            lambda day: 6 if day.formulary in changed else actual(day),
        )
        inherited = {year: roman.year(year) for year in years}
    assert proposed == inherited
    assert {year: roman.year(year) for year in years} == proposed


# These literal civil dates were independently computed with stdlib arithmetic.
# Selected source-role IDs come from the frozen 26-route source inventory, not
# from the binding document being tested. Public commemoration IDs remain unguessed.
PROJECTIONS = [
    (
        1818,
        "1818-03-22",
        "1818-04-29",
        (
            "proprium.sancti-petri-martyris-collecta",
            "proprium.sancti-petri-martyris-secreta",
            "proprium.sancti-petri-martyris-postcommunio",
        ),
    ),
    (
        2008,
        "2008-03-23",
        "2008-04-30",
        (
            "proprium.sanctae-catharinae-senensis-collecta",
            "proprium.sanctae-catharinae-senensis-secreta",
            "proprium.sanctae-catharinae-senensis-postcommunio",
        ),
    ),
    (
        2005,
        "2005-03-27",
        "2005-05-04",
        (
            "proprium.sanctae-monicae-collecta",
            "proprium.sanctae-petronillae-secreta",
            "proprium.sanctae-petronillae-postcommunio",
        ),
    ),
]


@pytest.mark.parametrize("ending,pascha,iso,targets", PROJECTIONS)
def test_out_of_span_1962_rule_projection_not_historical_ordo(
    monkeypatch, ending, pascha, iso, targets
):
    original_ranges = (dismissal.YEARS, producer.YEARS, reader.YEARS)
    assert all(list(years) == list(range(2026, 2102)) for years in original_ranges)
    when = date.fromisoformat(iso)
    assert easter(ending) == date.fromisoformat(pascha)
    assert when == easter(ending) + timedelta(days=38) and when.weekday() == 2
    docs = producer.authored(ROOT)
    assert vigil.require_inputs(ROOT, docs, store.formularies(ROOT), True)
    selected = [
        doc
        for doc in docs
        if doc["occurrence"]
        == {
            "kind": vigil.UNDER,
            "vigil": vigil.VIGIL,
            "month": when.month,
            "day": when.day,
        }
    ]
    assert len(selected) == 1
    doc = selected[0]
    assert doc["rank"] == "ordinary"
    assert tuple(slot["key"] for slot in doc["slots"]) == vigil.ROLES
    assert tuple(slot["text"] for slot in doc["slots"]) == targets
    assert vigil.occurrences(doc, ending) == {iso: vigil.VIGIL}
    wrong = copy.deepcopy(doc)
    wrong["occurrence"]["day"] += 1
    assert vigil.occurrences(wrong, ending) == {}
    assert vigil.occurrences(doc, ending) == {iso: vigil.VIGIL}
    # Scoped in-memory year substitution exercises the REAL canonical-input,
    # producer and independent reader code. No persisted fixture/range changes.
    with monkeypatch.context() as context:
        for module in (dismissal, producer, reader):
            context.setattr(module, "YEARS", (ending,))
        forms, calendar = dismissal.canonical_inputs(ROOT)
        actual = producer.calendar_table(forms, calendar, corpus=ROOT)
        assert actual == reader.expected(ROOT)
        index = next(
            i for i, entry in enumerate(actual["commemorations"]) if entry["id"] == doc["id"]
        )
        rows = [row for row in actual["pairs"] if row[0] == iso and row[2] == index]
        assert len(rows) == 1
        row = rows[0]
        assert actual["masses"][row[1]] == vigil.VIGIL
        assert row[4:] == [0, 0, 1, None]
        assert actual["decisions"] == [
            {"id": "admitted"},
            {"id": "not-admitted"},
            {"id": "omitted-required-de-tempore-unavailable"},
        ]
    assert original_ranges == (dismissal.YEARS, producer.YEARS, reader.YEARS)
    assert all(list(years) == list(range(2026, 2102)) for years in original_ranges)
