"""The Greater-Litanies commemoration: authored contract, computed occurrences, dated
activation on the edition's Mass rows, and the owned negative controls. The cases follow the
sealed assembly audit (weekday Mark, ordinary second-class Sunday, Easter Sunday and Monday
transfers, another octave weekday, Low Sunday)."""

import copy
import json
from datetime import date
from pathlib import Path

import pytest

from build_reader import commemorationes as reader
from build_reader import store
from checks import commemorationes as checker
from checks.formularies import check as check_formularies
from kalendarium import commemorationes as producer
from kalendarium.dismissal import canonical_inputs

CORPUS = Path(store.__file__).resolve().parent.parent
LM = "litaniae-maiores"
SLOTS = [
    ("collecta", "proprium.litaniae-maiores-collecta", "proper"),
    ("secreta", "proprium.dominica-i-passionis-secreta", "reference"),
    ("postcommunio", "proprium.litaniae-maiores-postcommunio", "proper"),
]
CASES = {
    # civil year: (occurrence, represented Mass or None)
    2026: ("2026-04-25", "sancti-marci-evangelistae"),
    2027: ("2027-04-25", "dominica-iv-post-pascha"),
    2030: ("2030-04-25", None),  # Thursday in the Easter octave: no represented Mass
    2038: ("2038-04-27", None),  # April 25 is Easter Sunday: the following Tuesday
    2049: ("2049-04-25", "dominica-in-albis"),  # first class: one privileged commemoration
    2095: ("2095-04-26", None),  # April 25 is Easter Monday: the following Tuesday
}


@pytest.fixture(scope="module")
def inputs():
    return canonical_inputs(CORPUS)


@pytest.fixture(scope="module")
def table(inputs):
    forms, calendar = inputs
    return producer.calendar_table(forms, calendar, corpus=CORPUS)


def authored():
    return json.loads((CORPUS / "commemorationes" / f"{LM}.json").read_text(encoding="utf-8"))


def test_the_authored_contract_is_exact_and_reaches_its_propers():
    doc = authored()
    assert doc["commemoration_schema"] == "1.0.0" and doc["id"] == LM
    assert (doc["rank"], doc["scope"], doc["conclusion"]) == ("privileged", "missa", "separate")
    assert doc["occurrence"] == {
        "month": 4,
        "day": 25,
        "transfer": "easter-sunday-or-monday-to-tuesday",
    }
    assert [(s["key"], s["text"], s["relation"]) for s in doc["slots"]] == SLOTS
    assert all(s["after"] == s["key"] for s in doc["slots"])
    assert set(doc["rubrics"]) == {"date", "scope", "rank", "admission", "conclusion"}
    assert "80" in doc["rubrics"]["date"] and "109" in doc["rubrics"]["rank"]
    assert checker.check(CORPUS) == (
        [],
        {"commemorations": 1, "slot_uses": 3, "proper_slots": 2, "reference_slots": 1},
    )
    errors, counts = check_formularies(CORPUS)
    assert errors == [] and counts["proper_texts"] == 1005
    for language, title in (("pl", "Litanie Większe"), ("en", "Greater Litanies")):
        localized = json.loads(
            (CORPUS / "languages" / language / "commemorationes" / f"{LM}.json").read_text(
                encoding="utf-8"
            )
        )
        assert localized == {
            "commemoration_schema": "1.0.0",
            "id": LM,
            "language": language,
            "title": title,
        }


@pytest.mark.parametrize("civil_year", sorted(CASES))
def test_the_occurrence_follows_rubric_80(civil_year):
    expected, _mass = CASES[civil_year]
    assert producer.occurrence(authored(), civil_year).isoformat() == expected


def test_every_occurrence_is_published_and_only_represented_masses_pair(table):
    assert table["schema_version"] == "1.0.0"
    assert table["profiles"] == [{"id": "ordinary-separate-conclusions"}]
    assert [(entry["id"], entry["title"]) for entry in table["commemorations"]] == [
        (LM, "Litaniæ maiores")
    ]
    assert [s["text"] for s in table["commemorations"][0]["slots"]] == [
        text.replace(".", "/", 1) for _key, text, _relation in SLOTS
    ]
    occurrences = {day for day, index in table["occurrences"] if index == 0}
    assert len(table["occurrences"]) == len(producer.YEARS) == 76
    pairs = {(day, table["masses"][mass]) for day, mass, index, profile in table["pairs"]}
    assert all(profile == 0 for *_rest, profile in table["pairs"])
    for expected, mass in CASES.values():
        assert expected in occurrences
        on_day = {m for d, m in pairs if d == expected}
        assert on_day == ({mass} if mass else set())
    assert {m for _d, m in pairs} == {
        "sancti-marci-evangelistae",
        "dominica-in-albis",
        "dominica-ii-post-pascha",
        "dominica-iii-post-pascha",
        "dominica-iv-post-pascha",
    }
    assert len(table["pairs"]) == 63
    assert len(occurrences - {d for d, _m in pairs}) == 13


def test_the_resource_equals_the_independent_reconstruction(table):
    assert table == reader.expected(CORPUS)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda t: t["pairs"].append(["2026-04-26", 0, 0, 0]),
        lambda t: t["pairs"].append(copy.deepcopy(t["pairs"][0])),
        lambda t: t["pairs"].reverse(),
        lambda t: t["pairs"][0].__setitem__(3, 1),
        lambda t: t["pairs"][0].__setitem__(1, len(t["masses"])),
        lambda t: t["occurrences"].append(["2026-04-25", 0]),
        lambda t: t["occurrences"].__setitem__(0, ["2026-4-25", 0]),
        lambda t: t.__setitem__("profiles", [{"id": "single-conclusion"}]),
        lambda t: t["commemorations"][0]["slots"][0].__setitem__("text", "litaniae-maiores"),
        lambda t: t.pop("occurrences"),
        lambda t: t["commemorations"][0].__setitem__("title", ""),
    ],
    ids=[
        "pair-off-occurrence",
        "duplicate-pair",
        "unsorted-pairs",
        "unknown-profile",
        "unknown-mass",
        "duplicate-occurrence",
        "noncanonical-date",
        "foreign-profile",
        "dotted-slot-address",
        "missing-occurrences",
        "empty-title",
    ],
)
def test_malformed_resources_are_rejected(table, mutation):
    broken = copy.deepcopy(table)
    mutation(broken)
    with pytest.raises(ValueError, match="commemorationes"):
        producer.validate(broken)
    producer.validate(table)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda forms, calendar: calendar["years"]["2026"].pop(),
        lambda forms, calendar: forms.pop(),
        lambda forms, calendar: calendar["years"]["2026"][0].__setitem__(0, "2026-04-25"),
    ],
    ids=["dropped-day", "dropped-mass", "forged-date"],
)
def test_producer_does_not_trust_forged_inputs(inputs, mutation):
    forms, calendar = copy.deepcopy(inputs)
    mutation(forms, calendar)
    with pytest.raises(ValueError, match="canonical"):
        producer.calendar_table(forms, calendar, corpus=CORPUS)


@pytest.mark.parametrize(
    "mutation,message",
    [
        (lambda d: d["occurrence"].__setitem__("transfer", "next-free-day"), "transfer"),
        (lambda d: d["slots"].reverse(), "slot 0"),
        (
            lambda d: d["slots"][0].__setitem__("text", "proprium.litaniae-maiores-oratio"),
            "missing",
        ),
        (lambda d: d["slots"][1].__setitem__("relation", "proper"), "proper relation"),
        (lambda d: d["rubrics"].__setitem__("date", ""), "nonempty"),
        (lambda d: d.__setitem__("rank", "solemn"), "rank"),
    ],
    ids=["transfer", "slot-order", "unknown-text", "mislabeled-reference", "empty-rubric", "rank"],
)
def test_authored_mutations_are_rejected_by_the_checker(tmp_path, mutation, message):
    corpus = tmp_path / "corpus"
    (corpus / "commemorationes").mkdir(parents=True)
    (corpus / "texts" / "proprium").mkdir(parents=True)
    for _key, text, _relation in SLOTS:
        (corpus / "texts" / "proprium" / (text.split(".", 1)[1] + ".json")).write_text("{}")
    for language in ("pl", "en"):
        (corpus / "languages" / language / "commemorationes").mkdir(parents=True)
        (corpus / "languages" / language / "manifest.json").write_text("{}")
        source = CORPUS / "languages" / language / "commemorationes" / f"{LM}.json"
        (corpus / "languages" / language / "commemorationes" / f"{LM}.json").write_bytes(
            source.read_bytes()
        )
    doc = authored()
    (corpus / "commemorationes" / f"{LM}.json").write_text(json.dumps(doc), encoding="utf-8")
    assert checker.check(corpus)[0] == []
    mutation(doc)
    (corpus / "commemorationes" / f"{LM}.json").write_text(json.dumps(doc), encoding="utf-8")
    errors, _counts = checker.check(corpus)
    assert errors and any(message in error for error in errors), errors


def test_a_missing_localized_title_is_reported(tmp_path):
    corpus = tmp_path / "corpus"
    (corpus / "commemorationes").mkdir(parents=True)
    (corpus / "texts" / "proprium").mkdir(parents=True)
    for _key, text, _relation in SLOTS:
        (corpus / "texts" / "proprium" / (text.split(".", 1)[1] + ".json")).write_text("{}")
    (corpus / "languages" / "pl" / "commemorationes").mkdir(parents=True)
    (corpus / "languages" / "pl" / "manifest.json").write_text("{}")
    (corpus / "commemorationes" / f"{LM}.json").write_bytes(
        (CORPUS / "commemorationes" / f"{LM}.json").read_bytes()
    )
    errors, _counts = checker.check(corpus)
    assert errors == [f"commemorationes:pl: missing titles for {LM}"]


def test_occurrence_dates_never_fall_on_easter_sunday_or_monday():
    from kalendarium.computus import easter

    doc = authored()
    for civil_year in producer.YEARS:
        when = producer.occurrence(doc, civil_year)
        pascha = easter(civil_year)
        assert (when - pascha).days not in (0, 1)
        assert when == date(civil_year, 4, 25) or (when - pascha).days == 2
