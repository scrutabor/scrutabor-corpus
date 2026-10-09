"""Epiphany Sundays retain the chants of their actual occurrence.

Missale Romanum, Benziger 1962, pp. 45–50 and 412–417 prints the two
assemblies separately; Rubricae generales 18 governs the resumed sequence.
"""

import json
from datetime import date
from pathlib import Path

import pytest

from build_reader.emit import emit
from kalendarium.roman import year as roman_year
from kalendarium.temporale import year as temporal_year

CORPUS = Path(__file__).resolve().parents[1]
ROMANS = ("iii", "iv", "v", "vi")
CHANTS = ("introitus", "graduale", "alleluia", "offertorium", "communio")
OWN = ("collecta", "epistola", "evangelium", "secreta", "postcommunio")
ROLES = (
    "introitus",
    "collecta",
    "epistola",
    "graduale",
    "alleluia",
    "evangelium",
    "offertorium",
    "secreta",
    "praefatio",
    "communio",
    "postcommunio",
)


def identifier(roman, resumed):
    qualifier = "quae-superfuit-" if resumed else ""
    return f"dominica-{roman}-{qualifier}post-epiphaniam"


def assembly(roman, resumed):
    path = CORPUS / "formularies/temporale" / f"{identifier(roman, resumed)}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def expected_chants(resumed, separator="."):
    if resumed:
        return {
            role: f"proprium{separator}dominica-xxiii-post-pentecosten-{role}" for role in CHANTS
        }
    return {
        role: (
            f"proprium{separator}dominica-xvi-post-pentecosten-graduale"
            if role == "graduale"
            else f"proprium{separator}dominica-iii-post-epiphaniam-{role}"
        )
        for role in CHANTS
    }


@pytest.mark.parametrize("roman", ROMANS)
@pytest.mark.parametrize("resumed", (False, True))
def test_both_printings_have_their_own_chants_and_the_same_lessons(roman, resumed):
    form = assembly(roman, resumed)
    expected_id = identifier(roman, resumed)
    assert form["id"] == form["observance"] == expected_id
    assert form["calendar"] == {"key": expected_id, "default": True}
    assert "variant" not in form
    parts = form["components"]
    assert [part["role"] for part in parts] == list(ROLES)
    assert all(part["key"] == part["role"] and "condition" not in part for part in parts)
    by_role = {part["role"]: part for part in parts}
    assert {role: by_role[role]["text"] for role in CHANTS} == expected_chants(resumed)
    assert {role: by_role[role]["text"] for role in OWN} == {
        role: f"proprium.dominica-{roman}-post-epiphaniam-{role}" for role in OWN
    }
    assert by_role["praefatio"] == {
        "key": "praefatio",
        "role": "praefatio",
        "text": "ordinarium.praefatio-sanctissimae-trinitatis",
        "relation": "shared",
    }
    if resumed:
        assert all(by_role[role]["relation"] == "reference" for role in (*CHANTS, *OWN))


@pytest.mark.parametrize(
    "when,roman,resumed",
    [
        ("1961-11-05", "iv", True),
        ("1962-02-04", "v", False),
        ("1962-02-11", "vi", False),
        ("2028-01-30", "iv", False),
        ("2029-11-04", "iv", True),
        ("2028-02-06", "v", False),
        ("2026-11-08", "v", True),
        ("2038-02-14", "vi", False),
        ("2026-11-15", "vi", True),
    ],
)
def test_resolved_dates_select_the_correct_printing(when, roman, resumed):
    civil = date.fromisoformat(when)
    day = next(day for day in roman_year(civil.year) if day.when == civil)
    assert day.formulary == identifier(roman, resumed)
    assert day.season == "per-annum"
    assert day.position.endswith("-post-pentecosten") if resumed else day.position == day.formulary


@pytest.mark.parametrize("calendar", (temporal_year, roman_year))
def test_sunday_identity_survives_the_split_and_the_kings_precedence(calendar):
    for ending in range(1961, 2102):
        days = calendar(ending)
        # A liturgical year can include a fixed feast twice at its November
        # edges. This invariant concerns the Epiphany Sunday family only.
        families = [
            day.formulary.replace("-quae-superfuit-", "-")
            for day in days
            if day.formulary.endswith("-post-epiphaniam")
        ]
        assert len(families) == len(set(families)), ending
        for day in days:
            if not day.formulary.endswith("-post-epiphaniam"):
                continue
            resumed = "-quae-superfuit-" in day.formulary
            assert resumed == day.position.endswith("-post-pentecosten"), (ending, day)
        # The theoretical resumed III in RG18 coincides with Christ the King
        # throughout this range. Its printed study form is not a dated Mass.
        assert identifier("iii", True) not in {day.formulary for day in days}
    king = next(day for day in calendar(1967) if day.when == date(1967, 10, 29))
    assert king.formulary == "d-n-iesu-christi-regis"
    assert king.position == "dominica-xxiv-post-pentecosten"


@pytest.fixture(scope="module")
def reader(tmp_path_factory):
    out = tmp_path_factory.mktemp("epiphany-reader")
    emit(CORPUS, out)
    return out


def test_reader_catalogue_and_calendar_use_the_same_distinct_keys(reader):
    manifest = json.loads((reader / "manifest.json").read_text())
    catalog = json.loads((reader / manifest["base"]["formularies"]).read_text())
    by_id = {form["id"]: form for form in catalog["formularies"]}
    for roman in ROMANS:
        for resumed in (False, True):
            key = identifier(roman, resumed)
            form = by_id[key]
            assert form["calendar"] == {"key": key, "default": True}
            assert {p["role"]: p["text"] for p in form["components"] if p["role"] in CHANTS} == (
                expected_chants(resumed, "/")
            )
    calendar = json.loads((reader / manifest["base"]["calendar"]).read_text())
    seen = set()
    for rows in calendar["years"].values():
        for when, key_index, _season, _rank, position_index in rows:
            key = calendar["formularies"][key_index]
            if not key.endswith("-post-epiphaniam"):
                continue
            seen.add(key)
            position = calendar["formularies"][position_index]
            assert by_id[key]["calendar"]["key"] == key, when
            assert ("-quae-superfuit-" in key) == position.endswith("-post-pentecosten"), when
    for roman in ROMANS:
        assert identifier(roman, False) in seen
        assert (identifier(roman, True) in seen) == (roman != "iii")
    assert identifier("iii", True) in by_id  # actual printed study form, not a fake date


@pytest.mark.parametrize("language", ("pl", "en"))
def test_both_languages_distinguish_the_resumed_titles(reader, language):
    manifest = json.loads((reader / f"languages/{language}/manifest.json").read_text())
    localized = json.loads((reader / manifest["formularies"]).read_text())
    titles = {row["id"]: row["title"] for row in localized["titles"]}
    prefix = "Przeniesiona " if language == "pl" else "Transferred "
    for roman in ROMANS:
        ordinary = titles[identifier(roman, False)]
        assert not ordinary.startswith(prefix)
        assert titles[identifier(roman, True)] == prefix + ordinary


def test_catalogue_order_keeps_the_two_occurrences_in_their_seasons():
    forms = [json.loads(path.read_text()) for path in (CORPUS / "formularies").glob("*/*.json")]
    ordered = [form["id"] for form in sorted(forms, key=lambda form: form["order"])]
    normal_start = ordered.index(identifier("iii", False))
    assert ordered[normal_start : normal_start + 5] == [
        *(identifier(roman, False) for roman in ROMANS),
        "dominica-in-septuagesima",
    ]
    resumed_start = ordered.index("dominica-xxiii-post-pentecosten")
    assert ordered[resumed_start : resumed_start + 6] == [
        "dominica-xxiii-post-pentecosten",
        *(identifier(roman, True) for roman in ROMANS),
        "dominica-xxiv-post-pentecosten",
    ]
