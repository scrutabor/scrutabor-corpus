"""The impeded feast, commemorated in the Mass of the second-class Sunday that is preferred to it:
the authored contract, the closed list of twenty second-class feasts, the 206 dates of the
supported span with the feast resolved on each, the decision in each Mass situation, the feast
formulary's own orations (St Paul's joined to St Peter's at the Chair, the Nativity of the
Blessed Virgin Mary's Postcommunion by reference), the first-class Sundays with no such
commemoration, and the owned negative controls. The 206 rows are stated literally, as Rubricae
generales 16, 95, 108 and 111 b give them, and are compared with an independent derivation from
the calendar."""

import copy
import json
import shutil
from calendar import isleap
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
FI = "festum-impeditum"
ORATIONS = ("collecta", "secreta", "postcommunio")
OCTAVE_SUNDAY = "dominica-infra-octavam-nativitatis"
# Each feast with every date of the supported span (liturgical years 2026-2101) on which it falls
# on a second-class Sunday, and the Sunday whose Mass is said that day.
IMPEDED = {
    "beata-maria-virgo-regina": {
        "2043-05-31": "dominica-ii-post-pentecosten",
        "2054-05-31": "dominica-ii-post-pentecosten",
        "2065-05-31": "dominica-ii-post-pentecosten",
        "2071-05-31": "dominica-post-ascensionem",
        "2076-05-31": "dominica-post-ascensionem",
        "2082-05-31": "dominica-post-ascensionem",
    },
    "beatae-mariae-virginis-a-rosario": {
        "2029-10-07": "dominica-xx-post-pentecosten",
        "2035-10-07": "dominica-xxi-post-pentecosten",
        "2040-10-07": "dominica-xx-post-pentecosten",
        "2046-10-07": "dominica-xxi-post-pentecosten",
        "2057-10-07": "dominica-xvii-post-pentecosten",
        "2063-10-07": "dominica-xviii-post-pentecosten",
        "2068-10-07": "dominica-xvii-post-pentecosten",
        "2074-10-07": "dominica-xviii-post-pentecosten",
        "2085-10-07": "dominica-xviii-post-pentecosten",
        "2091-10-07": "dominica-xix-post-pentecosten",
        "2096-10-07": "dominica-xviii-post-pentecosten",
    },
    "cathedra-sancti-petri": {
        "2060-02-22": "dominica-in-sexagesima",
        "2071-02-22": "dominica-in-sexagesima",
        "2082-02-22": "dominica-in-sexagesima",
        "2088-02-22": "dominica-in-quinquagesima",
        "2093-02-22": "dominica-in-quinquagesima",
        "2099-02-22": "dominica-in-quinquagesima",
    },
    "immaculatum-cor-beatae-mariae-virginis": {
        "2027-08-22": "dominica-xiv-post-pentecosten",
        "2032-08-22": "dominica-xiv-post-pentecosten",
        "2038-08-22": "dominica-x-post-pentecosten",
        "2049-08-22": "dominica-xi-post-pentecosten",
        "2055-08-22": "dominica-xi-post-pentecosten",
        "2060-08-22": "dominica-xi-post-pentecosten",
        "2066-08-22": "dominica-xii-post-pentecosten",
        "2077-08-22": "dominica-xii-post-pentecosten",
        "2083-08-22": "dominica-xiii-post-pentecosten",
        "2088-08-22": "dominica-xii-post-pentecosten",
        "2094-08-22": "dominica-xiii-post-pentecosten",
        "2100-08-22": "dominica-xiv-post-pentecosten",
    },
    "maternitas-beatae-mariae-virginis": {
        "2026-10-11": "dominica-xx-post-pentecosten",
        "2037-10-11": "dominica-xx-post-pentecosten",
        "2043-10-11": "dominica-xxi-post-pentecosten",
        "2048-10-11": "dominica-xx-post-pentecosten",
        "2054-10-11": "dominica-xxi-post-pentecosten",
        "2065-10-11": "dominica-xxi-post-pentecosten",
        "2071-10-11": "dominica-xviii-post-pentecosten",
        "2076-10-11": "dominica-xviii-post-pentecosten",
        "2082-10-11": "dominica-xviii-post-pentecosten",
        "2093-10-11": "dominica-xix-post-pentecosten",
        "2099-10-11": "dominica-xix-post-pentecosten",
    },
    "nativitas-beatae-mariae-virginis": {
        "2030-09-08": "dominica-xiii-post-pentecosten",
        "2041-09-08": "dominica-xiii-post-pentecosten",
        "2047-09-08": "dominica-xiv-post-pentecosten",
        "2052-09-08": "dominica-xiii-post-pentecosten",
        "2058-09-08": "dominica-xiv-post-pentecosten",
        "2069-09-08": "dominica-xiv-post-pentecosten",
        "2075-09-08": "dominica-xv-post-pentecosten",
        "2080-09-08": "dominica-xv-post-pentecosten",
        "2086-09-08": "dominica-xvi-post-pentecosten",
        "2097-09-08": "dominica-xvi-post-pentecosten",
    },
    "sanctae-annae-matris-beatae-mariae-virginis": {
        "2026-07-26": "dominica-ix-post-pentecosten",
        "2037-07-26": "dominica-ix-post-pentecosten",
        "2043-07-26": "dominica-x-post-pentecosten",
        "2048-07-26": "dominica-ix-post-pentecosten",
        "2054-07-26": "dominica-x-post-pentecosten",
        "2065-07-26": "dominica-x-post-pentecosten",
        "2071-07-26": "dominica-vii-post-pentecosten",
        "2076-07-26": "dominica-vii-post-pentecosten",
        "2082-07-26": "dominica-vii-post-pentecosten",
        "2093-07-26": "dominica-viii-post-pentecosten",
        "2099-07-26": "dominica-viii-post-pentecosten",
    },
    "sancti-bartholomaei-apostoli": {
        "2031-08-24": "dominica-xii-post-pentecosten",
        "2036-08-24": "dominica-xii-post-pentecosten",
        "2042-08-24": "dominica-xiii-post-pentecosten",
        "2053-08-24": "dominica-xiii-post-pentecosten",
        "2059-08-24": "dominica-xiv-post-pentecosten",
        "2064-08-24": "dominica-xiii-post-pentecosten",
        "2070-08-24": "dominica-xiv-post-pentecosten",
        "2081-08-24": "dominica-xiv-post-pentecosten",
        "2087-08-24": "dominica-xi-post-pentecosten",
        "2092-08-24": "dominica-xiv-post-pentecosten",
        "2098-08-24": "dominica-xi-post-pentecosten",
    },
    "sancti-iacobi-apostoli": {
        "2027-07-25": "dominica-x-post-pentecosten",
        "2032-07-25": "dominica-x-post-pentecosten",
        "2038-07-25": "dominica-vi-post-pentecosten",
        "2049-07-25": "dominica-vii-post-pentecosten",
        "2055-07-25": "dominica-vii-post-pentecosten",
        "2060-07-25": "dominica-vii-post-pentecosten",
        "2066-07-25": "dominica-viii-post-pentecosten",
        "2077-07-25": "dominica-viii-post-pentecosten",
        "2083-07-25": "dominica-ix-post-pentecosten",
        "2088-07-25": "dominica-viii-post-pentecosten",
        "2094-07-25": "dominica-ix-post-pentecosten",
        "2100-07-25": "dominica-x-post-pentecosten",
    },
    "sancti-ioachim-confessoris": {
        "2026-08-16": "dominica-xii-post-pentecosten",
        "2037-08-16": "dominica-xii-post-pentecosten",
        "2043-08-16": "dominica-xiii-post-pentecosten",
        "2048-08-16": "dominica-xii-post-pentecosten",
        "2054-08-16": "dominica-xiii-post-pentecosten",
        "2065-08-16": "dominica-xiii-post-pentecosten",
        "2071-08-16": "dominica-x-post-pentecosten",
        "2076-08-16": "dominica-x-post-pentecosten",
        "2082-08-16": "dominica-x-post-pentecosten",
        "2093-08-16": "dominica-xi-post-pentecosten",
        "2099-08-16": "dominica-xi-post-pentecosten",
    },
    "sancti-ioannis-apostoli-et-evangelistae": {
        "2026-12-27": "dominica-infra-octavam-nativitatis",
        "2037-12-27": "dominica-infra-octavam-nativitatis",
        "2043-12-27": "dominica-infra-octavam-nativitatis",
        "2048-12-27": "dominica-infra-octavam-nativitatis",
        "2054-12-27": "dominica-infra-octavam-nativitatis",
        "2065-12-27": "dominica-infra-octavam-nativitatis",
        "2071-12-27": "dominica-infra-octavam-nativitatis",
        "2076-12-27": "dominica-infra-octavam-nativitatis",
        "2082-12-27": "dominica-infra-octavam-nativitatis",
        "2093-12-27": "dominica-infra-octavam-nativitatis",
        "2099-12-27": "dominica-infra-octavam-nativitatis",
    },
    "sancti-laurentii-martyris": {
        "2031-08-10": "dominica-x-post-pentecosten",
        "2036-08-10": "dominica-x-post-pentecosten",
        "2042-08-10": "dominica-xi-post-pentecosten",
        "2053-08-10": "dominica-xi-post-pentecosten",
        "2059-08-10": "dominica-xii-post-pentecosten",
        "2064-08-10": "dominica-xi-post-pentecosten",
        "2070-08-10": "dominica-xii-post-pentecosten",
        "2081-08-10": "dominica-xii-post-pentecosten",
        "2087-08-10": "dominica-ix-post-pentecosten",
        "2092-08-10": "dominica-xii-post-pentecosten",
        "2098-08-10": "dominica-ix-post-pentecosten",
    },
    "sancti-lucae-evangelistae": {
        "2026-10-18": "dominica-xxi-post-pentecosten",
        "2037-10-18": "dominica-xxi-post-pentecosten",
        "2043-10-18": "dominica-xxii-post-pentecosten",
        "2048-10-18": "dominica-xxi-post-pentecosten",
        "2054-10-18": "dominica-xxii-post-pentecosten",
        "2065-10-18": "dominica-xxii-post-pentecosten",
        "2071-10-18": "dominica-xix-post-pentecosten",
        "2076-10-18": "dominica-xix-post-pentecosten",
        "2082-10-18": "dominica-xix-post-pentecosten",
        "2093-10-18": "dominica-xx-post-pentecosten",
        "2099-10-18": "dominica-xx-post-pentecosten",
    },
    "sancti-matthaei-apostoli-et-evangelistae": {
        "2031-09-21": "dominica-xvi-post-pentecosten",
        "2036-09-21": "dominica-xvi-post-pentecosten",
        "2042-09-21": "dominica-xvii-post-pentecosten",
        "2053-09-21": "dominica-xvii-post-pentecosten",
        "2059-09-21": "dominica-xviii-post-pentecosten",
        "2064-09-21": "dominica-xvii-post-pentecosten",
        "2070-09-21": "dominica-xviii-post-pentecosten",
        "2081-09-21": "dominica-xviii-post-pentecosten",
        "2087-09-21": "dominica-xv-post-pentecosten",
        "2092-09-21": "dominica-xviii-post-pentecosten",
        "2098-09-21": "dominica-xv-post-pentecosten",
    },
    "sancti-matthiae-apostoli": {
        "2030-02-24": "dominica-in-sexagesima",
        "2041-02-24": "dominica-in-sexagesima",
        "2047-02-24": "dominica-in-quinquagesima",
        "2052-02-25": "dominica-in-sexagesima",
        "2058-02-24": "dominica-in-quinquagesima",
        "2069-02-24": "dominica-in-quinquagesima",
    },
    "sancti-stephani-protomartyris": {
        "2027-12-26": "dominica-infra-octavam-nativitatis",
        "2032-12-26": "dominica-infra-octavam-nativitatis",
        "2038-12-26": "dominica-infra-octavam-nativitatis",
        "2049-12-26": "dominica-infra-octavam-nativitatis",
        "2055-12-26": "dominica-infra-octavam-nativitatis",
        "2060-12-26": "dominica-infra-octavam-nativitatis",
        "2066-12-26": "dominica-infra-octavam-nativitatis",
        "2077-12-26": "dominica-infra-octavam-nativitatis",
        "2083-12-26": "dominica-infra-octavam-nativitatis",
        "2088-12-26": "dominica-infra-octavam-nativitatis",
        "2094-12-26": "dominica-infra-octavam-nativitatis",
        "2100-12-26": "dominica-infra-octavam-nativitatis",
    },
    "sanctorum-innocentium-martyrum": {
        "2025-12-28": "dominica-infra-octavam-nativitatis",
        "2031-12-28": "dominica-infra-octavam-nativitatis",
        "2036-12-28": "dominica-infra-octavam-nativitatis",
        "2042-12-28": "dominica-infra-octavam-nativitatis",
        "2053-12-28": "dominica-infra-octavam-nativitatis",
        "2059-12-28": "dominica-infra-octavam-nativitatis",
        "2064-12-28": "dominica-infra-octavam-nativitatis",
        "2070-12-28": "dominica-infra-octavam-nativitatis",
        "2081-12-28": "dominica-infra-octavam-nativitatis",
        "2087-12-28": "dominica-infra-octavam-nativitatis",
        "2092-12-28": "dominica-infra-octavam-nativitatis",
        "2098-12-28": "dominica-infra-octavam-nativitatis",
    },
    "sanctorum-philippi-et-iacobi-apostolorum": {
        "2031-05-11": "dominica-iv-post-pascha",
        "2036-05-11": "dominica-iv-post-pascha",
        "2042-05-11": "dominica-v-post-pascha",
        "2053-05-11": "dominica-v-post-pascha",
        "2059-05-11": "dominica-post-ascensionem",
        "2064-05-11": "dominica-v-post-pascha",
        "2070-05-11": "dominica-post-ascensionem",
        "2081-05-11": "dominica-post-ascensionem",
        "2087-05-11": "dominica-iii-post-pascha",
        "2092-05-11": "dominica-post-ascensionem",
        "2098-05-11": "dominica-iii-post-pascha",
    },
    "septem-dolorum-beatae-mariae-virginis": {
        "2030-09-15": "dominica-xiv-post-pentecosten",
        "2041-09-15": "dominica-xiv-post-pentecosten",
        "2047-09-15": "dominica-xv-post-pentecosten",
        "2052-09-15": "dominica-xiv-post-pentecosten",
        "2058-09-15": "dominica-xv-post-pentecosten",
        "2069-09-15": "dominica-xv-post-pentecosten",
        "2075-09-15": "dominica-xvi-post-pentecosten",
        "2080-09-15": "dominica-xvi-post-pentecosten",
        "2086-09-15": "dominica-xvii-post-pentecosten",
        "2097-09-15": "dominica-xvii-post-pentecosten",
    },
    "visitatio-beatae-mariae-virginis": {
        "2028-07-02": "dominica-iv-post-pentecosten",
        "2034-07-02": "dominica-v-post-pentecosten",
        "2045-07-02": "dominica-v-post-pentecosten",
        "2051-07-02": "dominica-vi-post-pentecosten",
        "2056-07-02": "dominica-vi-post-pentecosten",
        "2062-07-02": "dominica-vii-post-pentecosten",
        "2073-07-02": "dominica-vii-post-pentecosten",
        "2079-07-02": "dominica-iii-post-pentecosten",
        "2084-07-02": "dominica-vii-post-pentecosten",
        "2090-07-02": "dominica-iv-post-pentecosten",
    },
}
FEASTS = sorted(IMPEDED)
# Each date: (the Sunday whose Mass is said, the feast commemorated).
ROWS = {day: (sunday, feast) for feast, dates in IMPEDED.items() for day, sunday in dates.items()}
# A first-class Sunday admits only a privileged commemoration (RG 111 a): (feast, Sunday).
FIRST_CLASS_SUNDAYS = {
    "2026-02-22": ("cathedra-sancti-petri", "dominica-i-in-quadragesima"),
    "2026-05-31": ("beata-maria-virgo-regina", "sanctissimae-trinitatis"),
    "2032-02-22": ("cathedra-sancti-petri", "dominica-ii-in-quadragesima"),
    "2037-02-22": ("cathedra-sancti-petri", "dominica-i-in-quadragesima"),
    "2037-05-31": ("beata-maria-virgo-regina", "sanctissimae-trinitatis"),
    "2043-02-22": ("cathedra-sancti-petri", "dominica-ii-in-quadragesima"),
    "2048-05-31": ("beata-maria-virgo-regina", "sanctissimae-trinitatis"),
    "2054-02-22": ("cathedra-sancti-petri", "dominica-ii-in-quadragesima"),
    "2065-02-22": ("cathedra-sancti-petri", "dominica-ii-in-quadragesima"),
    "2075-02-24": ("sancti-matthiae-apostoli", "dominica-i-in-quadragesima"),
    "2080-02-25": ("sancti-matthiae-apostoli", "dominica-i-in-quadragesima"),
    "2086-02-24": ("sancti-matthiae-apostoli", "dominica-ii-in-quadragesima"),
    "2093-05-31": ("beata-maria-virgo-regina", "dominica-pentecostes"),
    "2097-02-24": ("sancti-matthiae-apostoli", "dominica-ii-in-quadragesima"),
    "2099-05-31": ("beata-maria-virgo-regina", "dominica-pentecostes"),
}
# St Mark on a second-class Sunday: the privileged Greater Litanies take the single place (111 b).
MARK_SUNDAYS = [
    "2027-04-25", "2032-04-25", "2066-04-25", "2077-04-25", "2083-04-25", "2088-04-25",
    "2094-04-25", "2100-04-25",
]  # fmt: skip
LOW_AND_CONVENTUAL = {
    "lecta": "admitted",
    "cantu-conventualis": "admitted",
    "cantu-non-conventualis": "not-admitted",
}


@pytest.fixture(scope="module")
def inputs():
    return canonical_inputs(CORPUS)


@pytest.fixture(scope="module")
def table(inputs):
    forms, calendar = inputs
    return producer.calendar_table(forms, calendar, corpus=CORPUS)


def authored():
    return json.loads((CORPUS / "commemorationes" / f"{FI}.json").read_text(encoding="utf-8"))


def index_of(table, identity=FI):
    return [entry["id"] for entry in table["commemorations"]].index(identity)


def decided(table, identity=FI):
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
    assert sorted(plan) == sorted(ROWS), "the impeded feast decided on its dates"
    for day, (sunday, feast) in ROWS.items():
        assert plan[day][3] == feast, "the feast resolved"
        assert plan[day] == (sunday, 0, LOW_AND_CONVENTUAL, feast), "low and conventual only"


def printed(feast, civil_year):
    """The printed calendar's date of a feast: St Matthias on 25 February in a leap year."""
    month, day = next((f.month, f.day) for f in FESTA if f.formulary == feast)
    if feast == "sancti-matthiae-apostoli" and isleap(civil_year):
        day = 25
    return date(civil_year, month, day)


def derived_from_the_calendar():
    """From kalendarium.roman.year and the feasts' printed dates alone: a feast whose own date is
    a Sunday on which the calendar keeps a Sunday of the second class (RG 16)."""
    found = {}
    for ending in producer.YEARS:
        for day in year(ending):
            if day.when.weekday() != 6 or day.dies_class != 2:
                continue
            if not day.formulary.startswith("dominica-"):
                continue
            for feast in FEASTS:
                if printed(feast, day.when.year) == day.when:
                    found[day.when.isoformat()] = (day.formulary, feast)
    return found


def test_the_authored_contract_is_exact_and_resolves_its_slots_by_the_calendar():
    doc = authored()
    assert set(doc) == checker.KEYS and doc["commemoration_schema"] == "1.4.0"
    assert (doc["id"], doc["title"]) == (FI, "Festum impeditum")
    assert (doc["rank"], doc["scope"], doc["conclusion"]) == ("ordinary", "missa", "separate")
    assert doc["occurrence"] == {"kind": "impeded-feast", "feasts": FEASTS}
    assert doc["slots"] == [
        {"key": key, "after": key, "text": None, "relation": "calendar"} for key in ORATIONS
    ]
    rubrics = doc["rubrics"]
    assert set(rubrics) == {"date", "scope", "rank", "admission", "conclusion"}
    assert "10–12 and 15–17" in rubrics["date"] and "[XII]" in rubrics["date"]
    assert "93 and 95 (p. XVII)" in rubrics["date"] and "(16)" in rubrics["date"]
    assert "Vatican p. 22" in rubrics["date"]
    assert "Rubricae generales 110, p. XVIII" in rubrics["scope"]
    assert "106–109 (p. XVIII)" in rubrics["rank"] and "(108)" in rubrics["rank"]
    assert "111 a–b" in rubrics["admission"] and "434 a–b" in rubrics["admission"]
    assert "113–114 (p. XIX)" in rubrics["admission"]
    assert "436–437" in rubrics["conclusion"] and "XXXI" in rubrics["conclusion"]
    for language, title in (("pl", "Święto przeszkodzone"), ("en", "Impeded Feast")):
        localized = json.loads(
            (CORPUS / "languages" / language / "commemorationes" / f"{FI}.json").read_text(
                encoding="utf-8"
            )
        )
        assert localized == {
            "commemoration_schema": "1.1.0",
            "id": FI,
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


def test_the_feasts_are_the_second_class_feasts_a_second_class_sunday_impedes():
    assert list(checker.IMPEDED_FEASTS) == FEASTS and len(FEASTS) == 20
    second_class = {f.formulary for f in FESTA if f.dies_class == 2 and f.precedence == 16}
    lord = {f.formulary for f in FESTA if f.dies_class == 2 and f.precedence == 14}
    assert set(FEASTS) < second_class
    # The other four: two that only meet a first-class Sunday of Advent and one that only meets
    # Christ the King (15, 17 d), and St Mark, who meets the Greater Litanies (111 b).
    others = {
        "sancti-andreae-apostoli",
        "sancti-thomae-apostoli",
        "sanctorum-simonis-et-iudae-apostolorum",
    }
    assert second_class - set(FEASTS) == others | {"sancti-marci-evangelistae"}
    # A second-class feast of the Lord takes the Sunday's place (16 a).
    assert lord == {
        "purificatio-beatae-mariae-virginis",
        "transfiguratio-domini",
        "exaltatio-sanctae-crucis",
        "dedicatio-archibasilicae-sanctissimi-salvatoris",
    }
    for ending in producer.YEARS:
        for day in year(ending):
            if day.when.weekday() != 6:
                continue
            for feast in others | lord:
                if printed(feast, day.when.year) != day.when:
                    continue
                if feast in lord:
                    assert day.formulary == feast, "a feast of the Lord takes the Sunday's place"
                else:
                    assert day.dies_class == 1, "only a first-class Sunday"


def test_st_mark_yields_the_single_place_to_the_greater_litanies(table):
    litanies = decided(table, "litaniae-maiores")
    found = [
        day.when.isoformat()
        for ending in producer.YEARS
        for day in year(ending)
        if (day.when.month, day.when.day) == (4, 25)
        and day.when.weekday() == 6
        and day.dies_class == 2
    ]
    assert found == MARK_SUNDAYS
    for day in MARK_SUNDAYS:
        assert litanies[day][2] == dict.fromkeys(LOW_AND_CONVENTUAL, "admitted")
        assert day not in decided(table)


def test_the_dates_are_the_printed_rules_and_the_calendar_derivation(table):
    assert derived_from_the_calendar() == ROWS and len(ROWS) == 206
    assert {feast: len(dates) for feast, dates in IMPEDED.items()} == {
        "beata-maria-virgo-regina": 6,
        "beatae-mariae-virginis-a-rosario": 11,
        "cathedra-sancti-petri": 6,
        "immaculatum-cor-beatae-mariae-virginis": 12,
        "maternitas-beatae-mariae-virginis": 11,
        "nativitas-beatae-mariae-virginis": 10,
        "sanctae-annae-matris-beatae-mariae-virginis": 11,
        "sancti-bartholomaei-apostoli": 11,
        "sancti-iacobi-apostoli": 12,
        "sancti-ioachim-confessoris": 11,
        "sancti-ioannis-apostoli-et-evangelistae": 11,
        "sancti-laurentii-martyris": 11,
        "sancti-lucae-evangelistae": 11,
        "sancti-matthaei-apostoli-et-evangelistae": 11,
        "sancti-matthiae-apostoli": 6,
        "sancti-stephani-protomartyris": 12,
        "sanctorum-innocentium-martyrum": 12,
        "sanctorum-philippi-et-iacobi-apostolorum": 11,
        "septem-dolorum-beatae-mariae-virginis": 10,
        "visitatio-beatae-mariae-virginis": 10,
    }
    assert len({sunday for sunday, _feast in ROWS.values()}) == 28
    assert all(date.fromisoformat(day).weekday() == 6 for day in ROWS)
    assert producer.impeded_feasts(authored()) == {d: f for d, (_s, f) in ROWS.items()}
    assert_plan(table)


def test_every_date_is_an_occurrence_and_no_other_date_is(table):
    index = index_of(table)
    assert sorted(day for day, i in table["occurrences"] if i == index) == sorted(ROWS)


@pytest.mark.parametrize("day", sorted(FIRST_CLASS_SUNDAYS))
def test_a_first_class_sunday_publishes_no_pair_for_the_feast(table, inputs, day):
    _forms, calendar = inputs
    feast, sunday = FIRST_CLASS_SUNDAYS[day]
    row = next(r for rows in calendar["years"].values() for r in rows if r[0] == day)
    assert date.fromisoformat(day).weekday() == 6 and row[3] == 1
    assert calendar["formularies"][row[1]] == sunday
    assert printed(feast, int(day[:4])) == date.fromisoformat(day)
    assert day not in decided(table)
    assert [day, index_of(table)] not in table["occurrences"]


@pytest.mark.parametrize(
    "day", ["2025-12-28", "2043-05-31", "2052-02-25", "2060-02-22", "2100-12-26"]
)
def test_sampled_dates_admit_the_feast_in_low_and_sung_conventual_masses_only(table, day):
    sunday, feast = ROWS[day]
    assert decided(table)[day] == (sunday, 0, LOW_AND_CONVENTUAL, feast)


def test_the_sunday_within_the_octave_commemorates_the_occurring_feast(table):
    octave = {day: feast for day, (sunday, feast) in ROWS.items() if sunday == OCTAVE_SUNDAY}
    assert len(octave) == 35
    for day, feast in octave.items():
        expected = {
            "12-26": "sancti-stephani-protomartyris",
            "12-27": "sancti-ioannis-apostoli-et-evangelistae",
            "12-28": "sanctorum-innocentium-martyrum",
        }
        assert expected[day[5:]] == feast
        assert decided(table)[day] == (OCTAVE_SUNDAY, 0, LOW_AND_CONVENTUAL, feast)


def test_every_resolved_feast_says_its_own_formularys_three_orations(inputs):
    forms, _calendar = inputs
    by_id = {form["id"]: form for form in forms}
    bodies = reader.slot_bodies(CORPUS)
    said = set()
    for feast in FEASTS:
        texts = producer.formulary_orations(by_id[feast])
        own = [f"proprium/{feast}-{key}" for key in ORATIONS]
        if feast == "nativitas-beatae-mariae-virginis":
            # The formulary's Postcommunion is the Visitation's, by reference.
            own[2] = "proprium/visitatio-beatae-mariae-virginis-postcommunio"
        assert texts == own
        for text in texts:
            dotted = text.replace("/", ".", 1)
            said.add(dotted)
            assert dotted in bodies
            for language in ("pl", "en"):
                assert dotted in store.language_manifest(CORPUS, language)["texts"]
    assert len(said) == 59
    # St Paul's oration follows St Peter's under the one conclusion (RG 110).
    for key in ORATIONS:
        core = store.core(CORPUS, f"proprium.cathedra-sancti-petri-{key}")
        rubric = [s for s in core["segments"] if s.get("type") == "rubric"]
        assert [s["text"] for s in rubric] == [
            "Et fit commemoratio Sancti Pauli Apostoli sub unica conclusione:"
        ]
    reader.input_bodies(CORPUS)


def test_no_other_commemoration_shares_an_impeded_feast_date(table):
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


def test_an_all_masses_commemoration_of_the_feast_is_rejected(table, inputs, monkeypatch):
    bad = copy.deepcopy(table)
    row = next(r for r in bad["pairs"] if r[2] == index_of(bad))
    row[6] = 0
    with pytest.raises(ValueError, match="not admitted in a sung Mass that is not conventual"):
        producer.validate(bad)
    producer.validate(table)
    monkeypatch.setattr(producer, "impeded_feast_decision", lambda form, day, dies_class: [0, 0, 0])
    forms, calendar = inputs
    with pytest.raises(ValueError, match="not admitted in a sung Mass that is not conventual"):
        producer.calendar_table(forms, calendar, corpus=CORPUS)
    monkeypatch.undo()
    assert_plan(producer.calendar_table(forms, calendar, corpus=CORPUS))


def test_the_sunday_cannot_stand_for_the_feast(table, inputs, monkeypatch):
    real = producer.impeded_feasts
    monkeypatch.setattr(
        producer, "impeded_feasts", lambda doc: {day: ROWS[day][0] for day in real(doc)}
    )
    forms, calendar = inputs
    sundays = producer.calendar_table(forms, calendar, corpus=CORPUS)
    with pytest.raises(AssertionError, match="the feast resolved"):
        assert_plan(sundays)
    assert sundays != reader.expected(CORPUS)
    monkeypatch.undo()
    assert_plan(producer.calendar_table(forms, calendar, corpus=CORPUS))


def test_a_missing_feast_stops_the_selection_rather_than_leaving_a_gap(inputs, monkeypatch):
    real = producer.formulary_orations
    monkeypatch.setattr(
        producer,
        "formulary_orations",
        lambda form: None if form and form["id"] == "cathedra-sancti-petri" else real(form),
    )
    forms, calendar = inputs
    with pytest.raises(ValueError, match="the feast impeded on 2060-02-22 is not in this edition"):
        producer.calendar_table(forms, calendar, corpus=CORPUS)
    monkeypatch.undo()
    assert_plan(producer.calendar_table(forms, calendar, corpus=CORPUS))


def _fi_row(t):
    index = index_of(t)
    return next(row for row in t["pairs"] if row[2] == index)


RESOURCE_MUTATIONS = {
    "unavailable": (
        lambda t: _fi_row(t).__setitem__(slice(4, 7), [2, 2, 1]),
        "a resolved ordinary commemoration is admitted",
    ),
    "not-admitted": (
        lambda t: _fi_row(t).__setitem__(slice(4, 7), [1, 1, 1]),
        "a resolved ordinary commemoration is admitted",
    ),
    "all-masses": (
        lambda t: _fi_row(t).__setitem__(6, 0),
        "not admitted in a sung Mass that is not conventual",
    ),
    "resolved-without-formulary": (
        lambda t: _fi_row(t).__setitem__(7, None),
        "names its formulary exactly when",
    ),
    "unauthored-formulary-admitted": (
        lambda t: _fi_row(t).__setitem__(7, "sanctae-anastasiae-martyris"),
        "needs an authored formulary",
    ),
    "mixed-slots": (
        lambda t: t["commemorations"][index_of(t)]["slots"][0].__setitem__(
            "text", "proprium/cathedra-sancti-petri-collecta"
        ),
        "all addressed or all resolved",
    ),
    "seven-values": (lambda t: _fi_row(t).pop(), "pair rows are"),
}


@pytest.mark.parametrize("name", sorted(RESOURCE_MUTATIONS))
def test_malformed_resolved_resources_are_rejected(table, name):
    mutation, message = RESOURCE_MUTATIONS[name]
    assert "sanctae-anastasiae-martyris" not in table["masses"]
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
    "lord-feast": (
        _feasts(lambda f: sorted([*f, "purificatio-beatae-mariae-virginis"])),
        "feasts must be exactly",
    ),
    "litanies-feast": (
        _feasts(lambda f: sorted([*f, "sancti-marci-evangelistae"])),
        "feasts must be exactly",
    ),
    "missing-feast": (_feasts(lambda f: f[:-1]), "feasts must be exactly"),
    "unordered-feasts": (_feasts(lambda f: f[::-1]), "feasts must be exactly"),
    "privileged": (lambda d: d.__setitem__("rank", "privileged"), "cannot use occurrence kind"),
    "sunday-kind": (
        lambda d: d["occurrence"].__setitem__("kind", "displaced-sunday"),
        "feasts must be exactly",
    ),
    "proper-slot": (
        lambda d: d["slots"][0].update(
            text="proprium.festum-impeditum-collecta", relation="proper"
        ),
        "the calendar relation is used by, and only by",
    ),
    "calendar-slot-names-a-text": (
        lambda d: d["slots"][1].__setitem__("text", "proprium.cathedra-sancti-petri-secreta"),
        "names no text",
    ),
    "unknown-kind": (
        lambda d: d["occurrence"].__setitem__("kind", "feast"),
        "occurrence kind needs exactly",
    ),
    "dated-kind": (
        lambda d: d["occurrence"].__setitem__("month", 2),
        "occurrence kind needs exactly",
    ),
    "text-prefix": (
        lambda d: d.__setitem__("text_prefix", "festum"),
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


def test_a_fixed_date_ordinary_commemoration_cannot_take_a_calendar_slot(tmp_path):
    petronilla = json.loads(
        (CORPUS / "commemorationes" / "sancta-petronilla.json").read_text(encoding="utf-8")
    )
    assert checker.check(checker_corpus(tmp_path / "healthy", [petronilla]))[0] == []
    petronilla["slots"][2].update(text=None, relation="calendar")
    errors, _counts = checker.check(checker_corpus(tmp_path / "broken", [petronilla]))
    assert any("the calendar relation is used by, and only by" in error for error in errors)


def test_a_resolved_feast_oration_missing_from_a_language_package_fails_before_emission(tmp_path):
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
    path = corpus / "languages/pl/manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["texts"].remove("proprium.visitatio-beatae-mariae-virginis-postcommunio")
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(
        ValueError, match="visitatio-beatae-mariae-virginis-postcommunio requires a declared pl"
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


def test_the_verifier_requires_every_admitted_feasts_orations_in_every_package(tmp_path, table):
    out, manifest = emitted(tmp_path, table)
    assert reader.verify(CORPUS, out, manifest, emit.SCHEMA) == []
    path = out / "languages/en/manifest.json"
    package = json.loads(path.read_text(encoding="utf-8"))
    secret = "proprium.cathedra-sancti-petri-secreta"
    package["texts"] = [d for d in package["texts"] if d["id"] != secret]
    path.write_text(json.dumps(package), encoding="utf-8")
    assert reader.verify(CORPUS, out, manifest, emit.SCHEMA) == [
        "commemorationes: languages/en/texts/proprium/cathedra-sancti-petri-secreta.json"
        " must be declared exactly once"
    ]


def test_the_verifier_rejects_a_resource_resolved_to_the_sunday(tmp_path, inputs, table):
    wrong = copy.deepcopy(table)
    row = next(r for r in wrong["pairs"] if r[0] == "2060-02-22")
    assert row[7] == "cathedra-sancti-petri"
    row[7] = "dominica-in-sexagesima"
    producer.validate(wrong)
    out, manifest = emitted(tmp_path, wrong)
    errors = reader.verify(CORPUS, out, manifest, emit.SCHEMA)
    assert (
        errors[0] == "commemorationes: resource differs from independent canonical reconstruction"
    )
    # The stand-in packages carry the orations of the true resolution only, so each of the three
    # orations the Sunday's formulary assembles is missing from all three packages.
    forms, _calendar = inputs
    sexagesima = next(form for form in forms if form["id"] == "dominica-in-sexagesima")
    said = producer.formulary_orations(sexagesima)
    assert len(errors) == 1 + 3 * 3
    assert all(sum(f"texts/{text}.json" in error for text in said) == 1 for error in errors[1:])
