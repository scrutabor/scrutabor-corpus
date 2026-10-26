"""The Canon follows its own rubrics, not preface periods or a device clock."""

from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path

import pytest

from build_reader import emit, store
from kalendarium.canon import PROFILES, ROLES, _profile_id, calendar_table
from kalendarium.computus import easter
from kalendarium.roman import year

# The installed module, rather than this test's location, identifies the corpus.
CORPUS = Path(store.__file__).resolve().parent.parent


def decoded(table):
    return {
        (day, table["masses"][mass]): table["profiles"][profile]["id"]
        for day, mass, profile in table["pairs"]
    }


@pytest.fixture(scope="module")
def authored():
    return store.formularies(CORPUS)


@pytest.fixture(scope="module")
def calendar():
    return emit.kalendarium()


@pytest.fixture(scope="module")
def table(authored, calendar):
    return calendar_table(authored, calendar)


@pytest.fixture(scope="module")
def lookup(table):
    return decoded(table)


def test_every_represented_pair_has_one_explicit_complete_profile(authored, table):
    # Independent enumeration via the actual Roman calendar, not the emitter's
    # compact rows or the compiler's source-rule helper.
    expected = {
        (day.when.isoformat(), mass["id"])
        for ending in emit.KALENDARIUM
        for day in year(ending)
        for mass in authored
        if mass["calendar"]["key"] == day.formulary
    }
    assert set(decoded(table)) == expected
    assert len(table["pairs"]) == len(expected) == 7682
    assert len(table["masses"]) == 114
    assert table["schema_version"] == "1.0.0"
    assert table["roles"] == ["communicantes", "hanc-igitur", "qui-pridie"]
    assert len(table["profiles"]) == 9
    for profile in table["profiles"]:
        assert list(profile["texts"]) == list(ROLES)
        assert all(text.startswith("ordinarium.") for text in profile["texts"].values())
    ordinary = set(PROFILES["ordinary"])
    assert len({text for values in PROFILES.values() for text in values} - ordinary) == 11


def test_profile_bodies_preserve_each_role():
    assert PROFILES["ordinary"] == (
        "ordinarium.communicantes",
        "ordinarium.hanc-igitur",
        "ordinarium.qui-pridie",
    )
    assert PROFILES["in-cena-domini"] == (
        "ordinarium.communicantes-in-cena-domini",
        "ordinarium.hanc-igitur-in-cena-domini",
        "ordinarium.qui-pridie-in-cena-domini",
    )
    for name in ("pascha-in-nocte", "pascha-in-die", "pentecostes"):
        assert PROFILES[name][1:] == (
            "ordinarium.hanc-igitur-paschale",
            "ordinarium.qui-pridie",
        )
    for name in ("nativitas-in-nocte", "nativitas-in-die", "epiphania", "ascensio"):
        assert PROFILES[name][1:] == PROFILES["ordinary"][1:]


def test_each_named_communicantes_is_bound_to_its_own_body(table):
    expected = {
        "ordinary": "communicantes",
        "nativitas-in-nocte": "communicantes-in-nativitate-domini-in-nocte",
        "nativitas-in-die": "communicantes-in-nativitate-domini-in-die",
        "epiphania": "communicantes-in-epiphania-domini",
        "in-cena-domini": "communicantes-in-cena-domini",
        "pascha-in-nocte": "communicantes-in-nocte-paschae",
        "pascha-in-die": "communicantes-in-die-paschae",
        "ascensio": "communicantes-in-ascensione-domini",
        "pentecostes": "communicantes-in-pentecoste",
    }
    assert {entry["id"]: entry["texts"]["communicantes"] for entry in table["profiles"]} == {
        name: f"ordinarium.{slug}" for name, slug in expected.items()
    }


def test_every_other_pair_keeps_the_ordinary_profile(lookup):
    # Read the ranges as a date set, independently of the resolver's branch
    # ordering. Ferial dates contribute nothing unless actually represented.
    proper_dates = set()
    for ending in emit.KALENDARIUM:
        nativity = date(ending - 1, 12, 25)
        pascha = easter(ending)
        proper_dates.update(nativity + timedelta(days=n) for n in range(8))
        proper_dates.add(date(ending, 1, 6))
        proper_dates.update(
            pascha + timedelta(days=n) for n in [-3, -1, *range(7), 39, *range(48, 56)]
        )
    ordinary = {
        (day, mass) for (day, mass) in lookup if date.fromisoformat(day) not in proper_dates
    }
    assert len(ordinary) == 6587
    assert all(lookup[pair] == "ordinary" for pair in ordinary)
    assert all(profile != "ordinary" for pair, profile in lookup.items() if pair not in ordinary)


@pytest.mark.parametrize("ending", emit.KALENDARIUM)
def test_three_christmas_masses_and_octave_cross_the_civil_year(lookup, ending):
    # p. 18 restricts noctem to the first named Mass; RG 501 covers the
    # remaining Masses within the octave, including another saint's Mass.
    nativity = f"{ending - 1}-12-25"
    assert lookup[nativity, "nativitas-domini-in-nocte"] == "nativitas-in-nocte"
    for mass in ("nativitas-domini-in-aurora", "nativitas-domini-in-die"):
        assert lookup[nativity, mass] == "nativitas-in-die"
    assert lookup[f"{ending}-01-01", "in-octava-nativitatis"] == "nativitas-in-die"
    other_masses = [
        profile
        for (day, _mass), profile in lookup.items()
        if f"{ending - 1}-12-26" <= day <= f"{ending - 1}-12-31"
    ]
    assert other_masses and set(other_masses) == {"nativitas-in-die"}


@pytest.mark.parametrize("ending", emit.KALENDARIUM)
def test_actual_masses_do_not_borrow_longer_preface_periods(lookup, ending):
    assert lookup[f"{ending}-01-06", "epiphania-domini"] == "epiphania"
    for (day, mass), profile in lookup.items():
        if day.startswith(f"{ending}-01-") and mass in {
            "sanctissimi-nominis-iesu",
            "sancta-familia",
            "commemoratio-baptismatis-domini",
        }:
            assert profile == "ordinary", (day, mass)
    pascha = easter(ending)
    exact = {
        (-3, "feria-v-in-cena-domini"): "in-cena-domini",
        (-1, "vigilia-paschalis"): "pascha-in-nocte",
        (0, "dominica-resurrectionis"): "pascha-in-die",
        (7, "dominica-in-albis"): "ordinary",
        (39, "ascensio-domini"): "ascensio",
        (42, "dominica-post-ascensionem"): "ordinary",
        (48, "vigilia-pentecostes"): "pentecostes",
        (49, "dominica-pentecostes"): "pentecostes",
        (56, "sanctissimae-trinitatis"): "ordinary",
    }
    for (offset, mass), profile in exact.items():
        assert lookup[(pascha + timedelta(days=offset)).isoformat(), mass] == profile


@pytest.mark.parametrize(
    "day,mass,expected",
    [
        ("2025-12-24", "vigilia-nativitatis", "ordinary"),
        ("2025-12-26", "sancti-stephani-protomartyris", "nativitas-in-die"),
        ("2026-01-01", "in-octava-nativitatis", "nativitas-in-die"),
        ("2026-01-02", "ferial-control", "ordinary"),
        ("2026-01-05", "ferial-control", "ordinary"),
        ("2026-01-06", "epiphania-domini", "epiphania"),
        ("2026-01-07", "ferial-control", "ordinary"),
        ("2026-01-12", "ferial-control", "ordinary"),
        ("2026-04-01", "ferial-control", "ordinary"),
        ("2026-04-02", "missa-chrismatis", "ordinary"),
        ("2026-04-02", "feria-v-in-cena-domini", "in-cena-domini"),
        ("2026-04-04", "vigilia-paschalis", "pascha-in-nocte"),
        ("2026-04-05", "dominica-resurrectionis", "pascha-in-die"),
        ("2026-04-11", "ferial-control", "pascha-in-die"),
        ("2026-04-12", "dominica-in-albis", "ordinary"),
        ("2026-05-13", "ferial-control", "ordinary"),
        ("2026-05-14", "ascensio-domini", "ascensio"),
        ("2026-05-15", "ferial-control", "ordinary"),
        ("2026-05-22", "ferial-control", "ordinary"),
        ("2026-05-23", "vigilia-pentecostes", "pentecostes"),
        ("2026-05-30", "ferial-control", "pentecostes"),
        ("2026-05-31", "sanctissimae-trinitatis", "ordinary"),
    ],
)
def test_source_endpoints_even_where_the_edition_has_no_ferial_mass(day, mass, expected):
    # Source-rule unit controls, NOT claims of selectable ferial/Chrism Masses.
    # April 5 is the externally tabulated Easter date for this civil year.
    assert _profile_id(date.fromisoformat(day), mass) == expected


@pytest.mark.parametrize(
    "pair",
    [
        ("2026-04-02", "vigilia-paschalis"),
        ("2026-04-02", "missa-chrismatis"),
        ("2026-04-02", "none"),
        ("2026-04-06", "dominica-resurrectionis"),
        ("2026-04-11", "ferial-control"),
        ("2026-05-30", "ferial-control"),
        ("2026-05-31", "dominica-pentecostes"),
        ("2026-01-06", "nativitas-domini-in-nocte"),
    ],
)
def test_unsupported_pairs_are_not_present_as_ordinary_or_proper(lookup, pair):
    assert pair not in lookup


def test_compilation_is_deterministic_and_does_not_mutate_inputs(authored, calendar, table):
    before_mass, before_calendar = deepcopy(authored), deepcopy(calendar)
    shuffled = deepcopy(calendar)
    shuffled["years"] = {
        key: list(reversed(days)) for key, days in reversed(shuffled["years"].items())
    }
    reversed_masses = list(reversed(authored))
    before_reversed, before_shuffled = deepcopy(reversed_masses), deepcopy(shuffled)
    assert calendar_table(reversed_masses, shuffled) == table
    assert reversed_masses == before_reversed
    assert shuffled == before_shuffled
    assert authored == before_mass
    assert calendar == before_calendar


@pytest.mark.parametrize("index", [-1, True, False, 0.0, "0", 1])
def test_bad_calendar_index_does_not_select_another_identity(index):
    with pytest.raises(ValueError, match="Invalid calendar identity index"):
        calendar_table(
            [{"id": "mass", "calendar": {"key": "key"}}],
            {"formularies": ["key"], "years": {"2026": [["2026-01-01", index]]}},
        )


@pytest.mark.parametrize("day", ["20260101", "2026-W01-4", "2026-02-30"])
def test_invalid_or_noncanonical_date_is_rejected(day):
    with pytest.raises(ValueError):
        calendar_table(
            [{"id": "mass", "calendar": {"key": "key"}}],
            {"formularies": ["key"], "years": {"2026": [[day, 0]]}},
        )


@pytest.mark.parametrize("mass", ["none", "", None, 7])
def test_reserved_or_invalid_mass_identity_is_rejected(mass):
    with pytest.raises(ValueError, match="Invalid or duplicate Mass identity"):
        calendar_table([{"id": mass, "calendar": {"key": "key"}}], {"formularies": [], "years": {}})


def test_duplicate_mass_calendar_identity_or_date_is_rejected():
    mass = {"id": "mass", "calendar": {"key": "key"}}
    calendar = {"formularies": ["key"], "years": {"2026": [["2026-01-01", 0]]}}
    with pytest.raises(ValueError, match="duplicate Mass identity"):
        calendar_table([mass, mass], calendar)
    calendar["formularies"].append("key")
    with pytest.raises(ValueError, match="Duplicate calendar identity"):
        calendar_table([mass], calendar)
    calendar["formularies"].pop()
    calendar["years"]["2027"] = [["2026-01-01", 0]]
    with pytest.raises(ValueError, match="Duplicate calendar date"):
        calendar_table([mass], calendar)


def test_missing_mass_catalogue_entry_does_not_silently_drop_the_pair():
    with pytest.raises(ValueError, match="No represented Mass"):
        calendar_table([], {"formularies": ["key"], "years": {"2026": [["2026-01-01", 0]]}})
