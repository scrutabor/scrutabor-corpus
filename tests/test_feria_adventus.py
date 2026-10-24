"""The Advent feria, commemorated in the Mass of a feast kept on a weekday of Advent: the
authored contract, the closed list of the three feasts that can fall in Advent, the 163 dates of
the supported span with the feria's Mass resolved on each, the preceding Sunday's orations, the
Ember Friday and Saturday whose own Masses this edition does not yet carry, the Sundays with no
such commemoration, and the owned negative controls. The 163 rows are stated literally, as
Rubricae generales 21, 24–25, 108–109 e and 299 give them, and are compared with an independent
derivation from the calendar."""

import copy
import json
import shutil
from datetime import date
from pathlib import Path

import pytest

from build_reader import commemorationes as reader
from build_reader import emit, store
from checks import commemorationes as checker
from kalendarium import commemorationes as producer
from kalendarium.dismissal import canonical_inputs
from kalendarium.roman import year
from kalendarium.sanctorale import FESTA

CORPUS = Path(store.__file__).resolve().parent.parent
FA = "feria-adventus"
ORATIONS = ("collecta", "secreta", "postcommunio")
SUNDAYS = [
    "dominica-i-adventus",
    "dominica-ii-adventus",
    "dominica-iii-adventus",
    "dominica-iv-adventus",
]
# The Ember days of Advent by ISO weekday: the Wednesday, Friday and Saturday of the week of the
# Third Sunday of Advent, each with a Mass of its own (RG 24 b, 299) not yet in this edition.
EMBER = {
    3: "feria-quarta-quatuor-temporum-adventus",
    5: "feria-sexta-quatuor-temporum-adventus",
    6: "sabbato-quatuor-temporum-adventus",
}
# Each feast with every date of the supported span (liturgical years 2026-2101) on which it is
# kept on a weekday of Advent, and the Mass of the feria commemorated that day.
FERIAE = {
    "immaculata-conceptio": {
        "2025-12-08": "dominica-ii-adventus",
        "2026-12-08": "dominica-ii-adventus",
        "2027-12-08": "dominica-ii-adventus",
        "2028-12-08": "dominica-i-adventus",
        "2029-12-08": "dominica-i-adventus",
        "2031-12-08": "dominica-ii-adventus",
        "2032-12-08": "dominica-ii-adventus",
        "2033-12-08": "dominica-ii-adventus",
        "2034-12-08": "dominica-i-adventus",
        "2035-12-08": "dominica-i-adventus",
        "2036-12-08": "dominica-ii-adventus",
        "2037-12-08": "dominica-ii-adventus",
        "2038-12-08": "dominica-ii-adventus",
        "2039-12-08": "dominica-ii-adventus",
        "2040-12-08": "dominica-i-adventus",
        "2042-12-08": "dominica-ii-adventus",
        "2043-12-08": "dominica-ii-adventus",
        "2044-12-08": "dominica-ii-adventus",
        "2045-12-08": "dominica-i-adventus",
        "2046-12-08": "dominica-i-adventus",
        "2048-12-08": "dominica-ii-adventus",
        "2049-12-08": "dominica-ii-adventus",
        "2050-12-08": "dominica-ii-adventus",
        "2051-12-08": "dominica-i-adventus",
        "2053-12-08": "dominica-ii-adventus",
        "2054-12-08": "dominica-ii-adventus",
        "2055-12-08": "dominica-ii-adventus",
        "2056-12-08": "dominica-i-adventus",
        "2057-12-08": "dominica-i-adventus",
        "2059-12-08": "dominica-ii-adventus",
        "2060-12-08": "dominica-ii-adventus",
        "2061-12-08": "dominica-ii-adventus",
        "2062-12-08": "dominica-i-adventus",
        "2063-12-08": "dominica-i-adventus",
        "2064-12-08": "dominica-ii-adventus",
        "2065-12-08": "dominica-ii-adventus",
        "2066-12-08": "dominica-ii-adventus",
        "2067-12-08": "dominica-ii-adventus",
        "2068-12-08": "dominica-i-adventus",
        "2070-12-08": "dominica-ii-adventus",
        "2071-12-08": "dominica-ii-adventus",
        "2072-12-08": "dominica-ii-adventus",
        "2073-12-08": "dominica-i-adventus",
        "2074-12-08": "dominica-i-adventus",
        "2076-12-08": "dominica-ii-adventus",
        "2077-12-08": "dominica-ii-adventus",
        "2078-12-08": "dominica-ii-adventus",
        "2079-12-08": "dominica-i-adventus",
        "2081-12-08": "dominica-ii-adventus",
        "2082-12-08": "dominica-ii-adventus",
        "2083-12-08": "dominica-ii-adventus",
        "2084-12-08": "dominica-i-adventus",
        "2085-12-08": "dominica-i-adventus",
        "2087-12-08": "dominica-ii-adventus",
        "2088-12-08": "dominica-ii-adventus",
        "2089-12-08": "dominica-ii-adventus",
        "2090-12-08": "dominica-i-adventus",
        "2091-12-08": "dominica-i-adventus",
        "2092-12-08": "dominica-ii-adventus",
        "2093-12-08": "dominica-ii-adventus",
        "2094-12-08": "dominica-ii-adventus",
        "2095-12-08": "dominica-ii-adventus",
        "2096-12-08": "dominica-i-adventus",
        "2098-12-08": "dominica-ii-adventus",
        "2099-12-08": "dominica-ii-adventus",
        "2100-12-08": "dominica-ii-adventus",
    },
    "sancti-andreae-apostoli": {
        "2026-11-30": "dominica-i-adventus",
        "2027-11-30": "dominica-i-adventus",
        "2032-11-30": "dominica-i-adventus",
        "2033-11-30": "dominica-i-adventus",
        "2037-11-30": "dominica-i-adventus",
        "2038-11-30": "dominica-i-adventus",
        "2039-11-30": "dominica-i-adventus",
        "2043-11-30": "dominica-i-adventus",
        "2044-11-30": "dominica-i-adventus",
        "2048-11-30": "dominica-i-adventus",
        "2049-11-30": "dominica-i-adventus",
        "2050-11-30": "dominica-i-adventus",
        "2054-11-30": "dominica-i-adventus",
        "2055-11-30": "dominica-i-adventus",
        "2060-11-30": "dominica-i-adventus",
        "2061-11-30": "dominica-i-adventus",
        "2065-11-30": "dominica-i-adventus",
        "2066-11-30": "dominica-i-adventus",
        "2067-11-30": "dominica-i-adventus",
        "2071-11-30": "dominica-i-adventus",
        "2072-11-30": "dominica-i-adventus",
        "2076-11-30": "dominica-i-adventus",
        "2077-11-30": "dominica-i-adventus",
        "2078-11-30": "dominica-i-adventus",
        "2082-11-30": "dominica-i-adventus",
        "2083-11-30": "dominica-i-adventus",
        "2088-11-30": "dominica-i-adventus",
        "2089-11-30": "dominica-i-adventus",
        "2093-11-30": "dominica-i-adventus",
        "2094-11-30": "dominica-i-adventus",
        "2095-11-30": "dominica-i-adventus",
        "2099-11-30": "dominica-i-adventus",
        "2100-11-30": "dominica-i-adventus",
    },
    "sancti-thomae-apostoli": {
        "2026-12-21": "dominica-iv-adventus",
        "2027-12-21": "dominica-iv-adventus",
        "2028-12-21": "dominica-iii-adventus",
        "2029-12-21": "feria-sexta-quatuor-temporum-adventus",
        "2030-12-21": "sabbato-quatuor-temporum-adventus",
        "2032-12-21": "dominica-iv-adventus",
        "2033-12-21": "dominica-iv-adventus",
        "2034-12-21": "dominica-iii-adventus",
        "2035-12-21": "feria-sexta-quatuor-temporum-adventus",
        "2037-12-21": "dominica-iv-adventus",
        "2038-12-21": "dominica-iv-adventus",
        "2039-12-21": "dominica-iv-adventus",
        "2040-12-21": "feria-sexta-quatuor-temporum-adventus",
        "2041-12-21": "sabbato-quatuor-temporum-adventus",
        "2043-12-21": "dominica-iv-adventus",
        "2044-12-21": "dominica-iv-adventus",
        "2045-12-21": "dominica-iii-adventus",
        "2046-12-21": "feria-sexta-quatuor-temporum-adventus",
        "2047-12-21": "sabbato-quatuor-temporum-adventus",
        "2048-12-21": "dominica-iv-adventus",
        "2049-12-21": "dominica-iv-adventus",
        "2050-12-21": "dominica-iv-adventus",
        "2051-12-21": "dominica-iii-adventus",
        "2052-12-21": "sabbato-quatuor-temporum-adventus",
        "2054-12-21": "dominica-iv-adventus",
        "2055-12-21": "dominica-iv-adventus",
        "2056-12-21": "dominica-iii-adventus",
        "2057-12-21": "feria-sexta-quatuor-temporum-adventus",
        "2058-12-21": "sabbato-quatuor-temporum-adventus",
        "2060-12-21": "dominica-iv-adventus",
        "2061-12-21": "dominica-iv-adventus",
        "2062-12-21": "dominica-iii-adventus",
        "2063-12-21": "feria-sexta-quatuor-temporum-adventus",
        "2065-12-21": "dominica-iv-adventus",
        "2066-12-21": "dominica-iv-adventus",
        "2067-12-21": "dominica-iv-adventus",
        "2068-12-21": "feria-sexta-quatuor-temporum-adventus",
        "2069-12-21": "sabbato-quatuor-temporum-adventus",
        "2071-12-21": "dominica-iv-adventus",
        "2072-12-21": "dominica-iv-adventus",
        "2073-12-21": "dominica-iii-adventus",
        "2074-12-21": "feria-sexta-quatuor-temporum-adventus",
        "2075-12-21": "sabbato-quatuor-temporum-adventus",
        "2076-12-21": "dominica-iv-adventus",
        "2077-12-21": "dominica-iv-adventus",
        "2078-12-21": "dominica-iv-adventus",
        "2079-12-21": "dominica-iii-adventus",
        "2080-12-21": "sabbato-quatuor-temporum-adventus",
        "2082-12-21": "dominica-iv-adventus",
        "2083-12-21": "dominica-iv-adventus",
        "2084-12-21": "dominica-iii-adventus",
        "2085-12-21": "feria-sexta-quatuor-temporum-adventus",
        "2086-12-21": "sabbato-quatuor-temporum-adventus",
        "2088-12-21": "dominica-iv-adventus",
        "2089-12-21": "dominica-iv-adventus",
        "2090-12-21": "dominica-iii-adventus",
        "2091-12-21": "feria-sexta-quatuor-temporum-adventus",
        "2093-12-21": "dominica-iv-adventus",
        "2094-12-21": "dominica-iv-adventus",
        "2095-12-21": "dominica-iv-adventus",
        "2096-12-21": "feria-sexta-quatuor-temporum-adventus",
        "2097-12-21": "sabbato-quatuor-temporum-adventus",
        "2099-12-21": "dominica-iv-adventus",
        "2100-12-21": "dominica-iv-adventus",
    },
}
FEASTS = sorted(FERIAE)
# Each date: (the feast whose Mass is said, the Mass of the feria commemorated).
ROWS = {day: (feast, mass) for feast, dates in FERIAE.items() for day, mass in dates.items()}
# The printed dates of the three feasts that fall on a Sunday of Advent: St Andrew on the First
# and St Thomas on the Fourth, both of the first class and preferred to every feast (RG 11 a, 15);
# the Immaculate Conception on the Second, which it commemorates as an impeded Sunday
# (tests/test_dominica_impedita.py).
ADVENT_SUNDAYS = {
    "sancti-andreae-apostoli": [
        "2025-11-30", "2031-11-30", "2036-11-30", "2042-11-30", "2053-11-30", "2059-11-30",
        "2064-11-30", "2070-11-30", "2081-11-30", "2087-11-30", "2092-11-30", "2098-11-30",
    ],
    "sancti-thomae-apostoli": [
        "2025-12-21", "2031-12-21", "2036-12-21", "2042-12-21", "2053-12-21", "2059-12-21",
        "2064-12-21", "2070-12-21", "2081-12-21", "2087-12-21", "2092-12-21", "2098-12-21",
    ],
    "immaculata-conceptio": [
        "2030-12-08", "2041-12-08", "2047-12-08", "2052-12-08", "2058-12-08", "2069-12-08",
        "2075-12-08", "2080-12-08", "2086-12-08", "2097-12-08",
    ],
}  # fmt: skip
ALL_ADMITTED = dict.fromkeys(("lecta", "cantu-conventualis", "cantu-non-conventualis"), "admitted")
UNAVAILABLE = dict.fromkeys(ALL_ADMITTED, "omitted-required-de-tempore-unavailable")


@pytest.fixture(scope="module")
def inputs():
    return canonical_inputs(CORPUS)


@pytest.fixture(scope="module")
def table(inputs):
    forms, calendar = inputs
    return producer.calendar_table(forms, calendar, corpus=CORPUS)


def authored():
    return json.loads((CORPUS / "commemorationes" / f"{FA}.json").read_text(encoding="utf-8"))


def index_of(table, identity=FA):
    return [entry["id"] for entry in table["commemorations"]].index(identity)


def decided(table, identity=FA):
    index = index_of(table, identity)
    names = [decision["id"] for decision in table["decisions"]]
    return {
        row[0]: (
            table["masses"][row[1]],
            row[3],
            dict(zip(table["situations"], (names[v] for v in row[4:7]), strict=True)),
            row[7],
        )
        for row in table["pairs"]
        if row[2] == index
    }


def assert_plan(table):
    plan = decided(table)
    assert sorted(plan) == sorted(ROWS), "the Advent feria decided on its dates"
    for day, (feast, mass) in ROWS.items():
        assert plan[day][3] == mass, "the feria's Mass resolved"
        if mass in SUNDAYS:
            assert plan[day] == (feast, 0, ALL_ADMITTED, mass), "admitted in all Masses"
        else:
            assert plan[day] == (feast, 0, UNAVAILABLE, mass), "the Ember Mass unavailable"


def derived_from_the_calendar():
    """From kalendarium.roman.year alone: a feast kept on a weekday after the year's First Sunday
    of Advent and before the Nativity (RG 21); the feria's Mass is the preceding Sunday's, named
    by that Sunday's position, except on the Ember days of the week of the Third Sunday (RG 24 b,
    299)."""
    found = {}
    for ending in producer.YEARS:
        days = year(ending)
        sundays = [(day.when, day.position) for day in days if day.position in SUNDAYS]
        first = sundays[0][0]
        for day in days:
            if day.formulary not in FEASTS or day.when.isoweekday() == 7:
                continue
            if not first < day.when < date(first.year, 12, 25):
                continue
            mass = [position for when, position in sundays if when < day.when][-1]
            if mass == "dominica-iii-adventus" and day.when.isoweekday() in EMBER:
                mass = EMBER[day.when.isoweekday()]
            found[day.when.isoformat()] = (day.formulary, mass)
    return found


def test_the_authored_contract_is_exact_and_resolves_its_slots_by_the_calendar():
    doc = authored()
    assert set(doc) == checker.KEYS and doc["commemoration_schema"] == "1.4.0"
    assert (doc["id"], doc["title"]) == (FA, "Feria Adventus")
    assert (doc["rank"], doc["scope"], doc["conclusion"]) == ("privileged", "missa", "separate")
    assert doc["occurrence"] == {"kind": "advent-feria", "feasts": FEASTS}
    assert doc["slots"] == [
        {"key": key, "after": key, "text": None, "relation": "calendar"} for key in ORATIONS
    ]
    rubrics = doc["rubrics"]
    assert set(rubrics) == {"date", "scope", "rank", "admission", "conclusion"}
    assert "11 a and 15" in rubrics["date"] and "p. [XII]" in rubrics["date"]
    assert "20–21 and 24–25 (p. XIII)" in rubrics["date"]
    assert "places 4, 16, 18 and 25) and 93 (p. XVII)" in rubrics["date"]
    assert "298–299, p. XXII" in rubrics["scope"] and "Ember" in rubrics["scope"]
    assert "107–109 e (p. XVIII)" in rubrics["rank"] and "(108)" in rubrics["rank"]
    assert "111 a and c and 434 a and c" in rubrics["admission"]
    assert "113–114 (p. XIX)" in rubrics["admission"]
    assert "436–437" in rubrics["conclusion"] and "XXXI" in rubrics["conclusion"]
    for language, title in (("pl", "Dzień powszedni Adwentu"), ("en", "Weekday of Advent")):
        localized = json.loads(
            (CORPUS / "languages" / language / "commemorationes" / f"{FA}.json").read_text(
                encoding="utf-8"
            )
        )
        assert localized == {
            "commemoration_schema": "1.1.0",
            "id": FA,
            "language": language,
            "title": title,
        }
    assert checker.check(CORPUS) == (
        [],
        {
            "commemorations": 5,
            "slot_uses": 15,
            "proper_slots": 5,
            "reference_slots": 1,
            "calendar_slots": 9,
        },
    )


def test_the_feasts_are_the_calendar_feasts_that_can_fall_in_advent():
    assert list(checker.ADVENT_FERIA_FEASTS) == FEASTS and len(FEASTS) == 3
    # From 27 November, the earliest First Sunday of Advent (RG 20), to 24 December.
    advent = {f.formulary for f in FESTA if (11, 27) <= (f.month, f.day) <= (12, 24)}
    assert advent == set(FEASTS)
    assert {f.formulary: f.dies_class for f in FESTA if f.formulary in advent} == {
        "immaculata-conceptio": 1,
        "sancti-andreae-apostoli": 2,
        "sancti-thomae-apostoli": 2,
    }


def test_the_dates_are_the_printed_rules_and_the_calendar_derivation(table):
    assert derived_from_the_calendar() == ROWS and len(ROWS) == 163
    assert {feast: len(dates) for feast, dates in FERIAE.items()} == {
        "immaculata-conceptio": 66,
        "sancti-andreae-apostoli": 33,
        "sancti-thomae-apostoli": 64,
    }
    masses = [mass for _feast, mass in ROWS.values()]
    assert {mass: masses.count(mass) for mass in sorted(set(masses))} == {
        "dominica-i-adventus": 54,
        "dominica-ii-adventus": 45,
        "dominica-iii-adventus": 10,
        "dominica-iv-adventus": 33,
        "feria-sexta-quatuor-temporum-adventus": 11,
        "sabbato-quatuor-temporum-adventus": 10,
    }
    assert all(date.fromisoformat(day).isoweekday() != 7 for day in ROWS)
    assert producer.advent_ferias(authored()) == {d: m for d, (_f, m) in ROWS.items()}
    assert_plan(table)


def test_the_ember_days_are_named_and_only_st_thomas_meets_them():
    assert {weekday + 1: mass for weekday, mass in producer.ADVENT_EMBER_DAYS.items()} == EMBER
    assert reader.EMBER == EMBER
    ember = {day: (feast, mass) for day, (feast, mass) in ROWS.items() if mass not in SUNDAYS}
    assert len(ember) == 21 and {feast for feast, _mass in ember.values()} == {
        "sancti-thomae-apostoli"
    }
    for day, (_feast, mass) in ember.items():
        assert mass == EMBER[date.fromisoformat(day).isoweekday()]
    # St Thomas on 21 December is in the week of the Third Sunday of Advent from Thursday to
    # Saturday, and otherwise in the week of the Fourth; the Ember Wednesday never meets a feast.
    thomas = FERIAE["sancti-thomae-apostoli"]
    for day, mass in thomas.items():
        weekday = date.fromisoformat(day).isoweekday()
        assert (mass == "dominica-iv-adventus") == (weekday <= 3)
        assert (mass == "dominica-iii-adventus") == (weekday == 4)
    assert EMBER[3] not in {mass for _feast, mass in ROWS.values()}


def test_every_date_is_an_occurrence_and_no_other_date_is(table):
    index = index_of(table)
    assert sorted(day for day, i in table["occurrences"] if i == index) == sorted(ROWS)


@pytest.mark.parametrize("feast", sorted(ADVENT_SUNDAYS))
def test_a_sunday_of_advent_publishes_no_feria_pair(table, inputs, feast):
    _forms, calendar = inputs
    index = index_of(table)
    impeded = decided(table, "dominica-impedita")
    for day in ADVENT_SUNDAYS[feast]:
        assert date.fromisoformat(day).isoweekday() == 7
        row = next(r for rows in calendar["years"].values() for r in rows if r[0] == day)
        assert row[3] == 1 and calendar["formularies"][row[4]].endswith("-adventus")
        assert day not in decided(table) and [day, index] not in table["occurrences"]
        if feast == "immaculata-conceptio":
            assert impeded[day] == (feast, 0, ALL_ADMITTED, "dominica-ii-adventus")
        else:
            assert calendar["formularies"][row[1]] != feast and day not in impeded


@pytest.mark.parametrize(
    "day", ["2025-12-08", "2026-11-30", "2028-12-21", "2029-12-21", "2030-12-21", "2100-12-21"]
)
def test_sampled_dates_resolve_the_ferias_mass(table, day):
    feast, mass = ROWS[day]
    plan = ALL_ADMITTED if mass in SUNDAYS else UNAVAILABLE
    assert decided(table)[day] == (feast, 0, plan, mass)


def test_every_resolved_sunday_says_its_own_formularys_three_orations(inputs, table):
    forms, _calendar = inputs
    by_id = {form["id"]: form for form in forms}
    bodies = reader.slot_bodies(CORPUS)
    for sunday in SUNDAYS:
        texts = producer.formulary_orations(by_id[sunday])
        assert texts == [f"proprium/{sunday}-{key}" for key in ORATIONS]
        for text in texts:
            dotted = text.replace("/", ".", 1)
            assert dotted in bodies
            for language in ("pl", "en"):
                assert dotted in store.language_manifest(CORPUS, language)["texts"]
    for mass in EMBER.values():
        assert mass not in by_id and mass not in table["masses"]
        assert not any(body.startswith(f"proprium.{mass}") for body in bodies)
    reader.input_bodies(CORPUS)


def test_no_other_commemoration_shares_an_advent_feria_date(table):
    index = index_of(table)
    assert not [row for row in table["pairs"] if row[0] in ROWS and row[2] != index]
    crowded = copy.deepcopy(table)
    first = next(row for row in crowded["pairs"] if row[2] == index)
    litanies = index_of(crowded, "litaniae-maiores")
    crowded["occurrences"] = sorted([*crowded["occurrences"], [first[0], litanies]])
    crowded["pairs"] = sorted([*crowded["pairs"], [first[0], first[1], litanies, 0, 0, 0, 0, None]])
    with pytest.raises(ValueError, match="single commemoration"):
        producer.validate(crowded)
    producer.validate(table)


def test_the_resource_equals_the_independent_reconstruction(table):
    assert table == reader.expected(CORPUS)


def test_the_sunday_cannot_stand_for_the_ember_day(table, inputs, monkeypatch):
    real = producer.advent_ferias
    monkeypatch.setattr(
        producer,
        "advent_ferias",
        lambda doc: {
            day: mass if mass in SUNDAYS else "dominica-iii-adventus"
            for day, mass in real(doc).items()
        },
    )
    forms, calendar = inputs
    sundays = producer.calendar_table(forms, calendar, corpus=CORPUS)
    with pytest.raises(AssertionError, match="the feria's Mass resolved"):
        assert_plan(sundays)
    assert sundays != reader.expected(CORPUS)
    monkeypatch.undo()
    assert_plan(producer.calendar_table(forms, calendar, corpus=CORPUS))


def test_a_missing_sunday_stops_the_selection_rather_than_leaving_a_gap(inputs, monkeypatch):
    real = producer.formulary_orations
    monkeypatch.setattr(
        producer,
        "formulary_orations",
        lambda form: None if form and form["id"] == "dominica-iii-adventus" else real(form),
    )
    forms, calendar = inputs
    with pytest.raises(
        ValueError, match="the Mass of the Advent feria on 2028-12-21 is not in this edition"
    ):
        producer.calendar_table(forms, calendar, corpus=CORPUS)
    monkeypatch.undo()
    assert_plan(producer.calendar_table(forms, calendar, corpus=CORPUS))


@pytest.mark.parametrize("mass", sorted(EMBER.values()))
def test_an_authored_ember_mass_stops_the_selection(mass):
    form = {"id": mass, "components": []}
    with pytest.raises(ValueError, match=f"{mass} needs its own commemoration rule"):
        producer.advent_feria_decision(form, mass, "2029-12-21")
    assert producer.advent_feria_decision(None, mass, "2029-12-21") == [2, 2, 2]


def _fa_row(t, ember=False):
    index = index_of(t)
    return next(row for row in t["pairs"] if row[2] == index and (row[7] not in SUNDAYS) == ember)


def _with_ember_mass(t, plan):
    """The resource with the first Ember row's Mass presented as an authored Mass."""
    row = _fa_row(t, ember=True)
    row[4:7] = plan
    masses = sorted([*t["masses"], row[7]])
    t["pairs"] = sorted([[r[0], masses.index(t["masses"][r[1]]), *r[2:]] for r in t["pairs"]])
    t["masses"] = masses


RESOURCE_MUTATIONS = {
    "partly-unavailable": (
        lambda t: _fa_row(t).__setitem__(6, 2),
        "privileged commemoration is made in all Masses",
    ),
    "ordinary-plan": (
        lambda t: _fa_row(t).__setitem__(6, 1),
        "privileged commemoration is made in all Masses",
    ),
    "ember-admitted": (
        lambda t: _fa_row(t, ember=True).__setitem__(slice(4, 7), [0, 0, 0]),
        "needs an authored formulary",
    ),
    "ember-not-admitted": (
        lambda t: _fa_row(t, ember=True).__setitem__(slice(4, 7), [1, 1, 1]),
        "an Ember day of Advent names its own Mass",
    ),
    "ember-as-an-authored-mass": (
        lambda t: _with_ember_mass(t, [2, 2, 2]),
        "an Ember day of Advent names its own Mass",
    ),
    "ember-said-as-an-authored-mass": (
        lambda t: _with_ember_mass(t, [0, 0, 0]),
        "an Ember day of Advent names its own Mass",
    ),
    "resolved-without-formulary": (
        lambda t: _fa_row(t).__setitem__(7, None),
        "names its formulary exactly when",
    ),
    "unauthored-formulary-admitted": (
        lambda t: _fa_row(t).__setitem__(7, "dominica-v-adventus"),
        "needs an authored formulary",
    ),
    "mixed-slots": (
        lambda t: t["commemorations"][index_of(t)]["slots"][0].__setitem__(
            "text", "proprium/dominica-i-adventus-collecta"
        ),
        "all addressed or all resolved",
    ),
    "seven-values": (lambda t: _fa_row(t).pop(), "pair rows are"),
}


@pytest.mark.parametrize("name", sorted(RESOURCE_MUTATIONS))
def test_malformed_resolved_resources_are_rejected(table, name):
    mutation, message = RESOURCE_MUTATIONS[name]
    assert "dominica-v-adventus" not in table["masses"]
    broken = copy.deepcopy(table)
    mutation(broken)
    with pytest.raises(ValueError, match=message):
        producer.validate(broken)
    producer.validate(table)


def checker_corpus(tmp_path, documents):
    corpus = tmp_path / "corpus"
    (corpus / "commemorationes").mkdir(parents=True)
    (corpus / "texts" / "proprium").mkdir(parents=True)
    for language in ("pl", "en"):
        (corpus / "languages" / language / "commemorationes").mkdir(parents=True)
        (corpus / "languages" / language / "manifest.json").write_text("{}")
    for doc in documents:
        identity = doc["id"]
        (corpus / "commemorationes" / f"{identity}.json").write_text(json.dumps(doc))
        for language in ("pl", "en"):
            name = f"languages/{language}/commemorationes/{identity}.json"
            (corpus / name).write_bytes((CORPUS / name).read_bytes())
        for slot in doc["slots"]:
            if slot["text"] is not None:
                relative = slot["text"].split(".", 1)[1] + ".json"
                (corpus / "texts" / "proprium" / relative).write_text("{}")
    return corpus


def _feasts(change):
    def mutate(doc):
        doc["occurrence"]["feasts"] = change(doc["occurrence"]["feasts"])

    return mutate


AUTHORED_MUTATIONS = {
    "extra-feast": (
        _feasts(lambda f: sorted([*f, "sancti-stephani-protomartyris"])),
        "feasts must be exactly",
    ),
    "missing-feast": (_feasts(lambda f: f[:-1]), "feasts must be exactly"),
    "unordered-feasts": (_feasts(lambda f: f[::-1]), "feasts must be exactly"),
    "ordinary": (lambda d: d.__setitem__("rank", "ordinary"), "cannot use occurrence kind"),
    "sunday-kind": (
        lambda d: d["occurrence"].__setitem__("kind", "displaced-sunday"),
        "feasts must be exactly",
    ),
    "proper-slot": (
        lambda d: d["slots"][0].update(text="proprium.feria-adventus-collecta", relation="proper"),
        "the calendar relation is used by, and only by",
    ),
    "calendar-slot-names-a-text": (
        lambda d: d["slots"][1].__setitem__("text", "proprium.dominica-i-adventus-secreta"),
        "names no text",
    ),
    "unknown-kind": (
        lambda d: d["occurrence"].__setitem__("kind", "feria"),
        "occurrence kind needs exactly",
    ),
    "dated-kind": (
        lambda d: d["occurrence"].__setitem__("month", 12),
        "occurrence kind needs exactly",
    ),
    "text-prefix": (
        lambda d: d.__setitem__("text_prefix", "feria"),
        "text_prefix addresses proper slots",
    ),
}


@pytest.mark.parametrize("name", sorted(AUTHORED_MUTATIONS))
def test_authored_mutations_are_rejected_by_the_checker(tmp_path, name):
    mutation, message = AUTHORED_MUTATIONS[name]
    doc = authored()
    assert checker.check(checker_corpus(tmp_path / "healthy", [doc]))[0] == []
    mutation(doc)
    errors, _counts = checker.check(checker_corpus(tmp_path / "broken", [doc]))
    assert errors and any(message in error for error in errors), errors


def test_the_closed_list_is_checked_against_the_calendar(tmp_path, monkeypatch):
    doc = authored()
    assert checker.check(checker_corpus(tmp_path / "healthy", [doc]))[0] == []
    # A window that no longer reaches St Andrew's day makes the closed list disagree.
    monkeypatch.setattr(checker, "ADVENT_DATES", ((12, 1), (12, 24)))
    errors, _counts = checker.check(checker_corpus(tmp_path / "broken", [doc]))
    assert any("the Advent feria's feasts are not exactly" in error for error in errors), errors


def test_a_resolved_sunday_oration_missing_from_a_language_package_fails_before_emission(
    tmp_path,
):
    corpus = tmp_path / "corpus"
    for directory in (
        "commemorationes",
        "formularies",
        "languages/pl/commemorationes",
        "languages/en/commemorationes",
    ):
        shutil.copytree(CORPUS / directory, corpus / directory)
    bodies = reader.slot_bodies(CORPUS)
    for text in bodies:
        relative = f"{text.replace('.', '/', 1)}.json"
        for prefix in ("texts/", "languages/pl/texts/", "languages/en/texts/"):
            (corpus / prefix / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(CORPUS / prefix / relative, corpus / prefix / relative)
    for language in ("pl", "en"):
        manifest = store.language_manifest(CORPUS, language)
        restricted = {**manifest, "texts": [t for t in manifest["texts"] if t in bodies]}
        (corpus / f"languages/{language}/manifest.json").write_text(
            json.dumps(restricted, ensure_ascii=False), encoding="utf-8"
        )
    assert reader.slot_bodies(corpus) == bodies
    reader.input_bodies(corpus)
    path = corpus / "languages/en/manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["texts"].remove("proprium.dominica-iii-adventus-postcommunio")
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(
        ValueError, match="dominica-iii-adventus-postcommunio requires a declared en"
    ):
        reader.input_bodies(corpus)


def emitted(tmp_path, table):
    """The parts of an emitted edition the commemoration verifier reads, with stand-in bodies."""
    out = tmp_path / "edition"
    bodies = reader.slot_bodies(CORPUS)

    def declare(prefix, language=None):
        declarations = []
        for text in bodies:
            path = f"{prefix}texts/{text.replace('.', '/', 1)}.json"
            body = {"id": text, "seg": [["w001"]], **({"language": language} if language else {})}
            (out / path).parent.mkdir(parents=True, exist_ok=True)
            (out / path).write_text(json.dumps(body), encoding="utf-8")
            declarations.append({"id": text, "path": path})
        return declarations

    out.mkdir()
    (out / "commemorationes.json").write_text(json.dumps(table), encoding="utf-8")
    manifest = {
        "schema_version": emit.SCHEMA,
        "base": {"commemorationes": "commemorationes.json"},
        "languages": [
            {"id": language, "path": f"languages/{language}/manifest.json"}
            for language in ("pl", "en")
        ],
        "texts": declare(""),
    }
    for language in ("pl", "en"):
        package = {
            "language": language,
            "schema_version": emit.SCHEMA,
            "commemorationes": f"languages/{language}/commemorationes.json",
            "texts": declare(f"languages/{language}/", language),
        }
        (out / f"languages/{language}/manifest.json").write_text(
            json.dumps(package), encoding="utf-8"
        )
        (out / package["commemorationes"]).write_text(
            json.dumps(reader.language_catalog(CORPUS, language)), encoding="utf-8"
        )
    return out, manifest


def test_the_verifier_requires_every_admitted_sundays_orations_in_every_package(tmp_path, table):
    out, manifest = emitted(tmp_path, table)
    assert reader.verify(CORPUS, out, manifest, emit.SCHEMA) == []
    path = out / "languages/pl/manifest.json"
    package = json.loads(path.read_text(encoding="utf-8"))
    collect = "proprium.dominica-iii-adventus-collecta"
    package["texts"] = [d for d in package["texts"] if d["id"] != collect]
    path.write_text(json.dumps(package), encoding="utf-8")
    assert reader.verify(CORPUS, out, manifest, emit.SCHEMA) == [
        "commemorationes: languages/pl/texts/proprium/dominica-iii-adventus-collecta.json"
        " must be declared exactly once"
    ]


def test_the_verifier_rejects_an_ember_day_said_from_the_sunday(tmp_path, table):
    wrong = copy.deepcopy(table)
    row = next(r for r in wrong["pairs"] if r[0] == "2029-12-21")
    assert row[4:] == [2, 2, 2, "feria-sexta-quatuor-temporum-adventus"]
    row[4:] = [0, 0, 0, "dominica-iii-adventus"]
    producer.validate(wrong)
    out, manifest = emitted(tmp_path, wrong)
    # The Third Sunday's orations are transported for its own dates, so the reconstruction alone
    # tells the two resources apart.
    assert reader.verify(CORPUS, out, manifest, emit.SCHEMA) == [
        "commemorationes: resource differs from independent canonical reconstruction"
    ]
