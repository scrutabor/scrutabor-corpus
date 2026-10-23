"""St Petronilla's ordinary commemoration at the Queenship Mass on 31 May: the authored contract,
the explicit decision in each Mass situation, the omission on a Sunday or first-class day, the
2079 marker where the impeded Vigil of the Ascension takes the single place, and the owned
negative controls. The 43 admitted dates are stated literally, as the printed rules give them
(Rubricae generales 106–114; Benziger pp. 543–544, Vatican pp. 540–541), and are compared with
the calendar's own derivation."""

import copy
import hashlib
import json
import shutil
from datetime import date, timedelta
from pathlib import Path

import pytest

from build_reader import commemorationes as reader
from build_reader import store
from checks import commemorationes as checker
from kalendarium import commemorationes as producer
from kalendarium.computus import easter
from kalendarium.dismissal import canonical_inputs
from kalendarium.roman import year

CORPUS = Path(store.__file__).resolve().parent.parent
SP = "sancta-petronilla"
QUEENSHIP = "beata-maria-virgo-regina"
SLOTS = [
    ("collecta", "proprium.sanctae-petronillae-collecta"),
    ("secreta", "proprium.sanctae-petronillae-secreta"),
    ("postcommunio", "proprium.sanctae-petronillae-postcommunio"),
]
ADMITTED = [
    "2027-05-31", "2028-05-31", "2030-05-31", "2032-05-31", "2033-05-31", "2035-05-31",
    "2038-05-31", "2041-05-31", "2044-05-31", "2046-05-31", "2047-05-31", "2049-05-31",
    "2051-05-31", "2052-05-31", "2055-05-31", "2056-05-31", "2058-05-31", "2059-05-31",
    "2060-05-31", "2062-05-31", "2063-05-31", "2067-05-31", "2069-05-31", "2070-05-31",
    "2073-05-31", "2074-05-31", "2078-05-31", "2081-05-31", "2083-05-31", "2084-05-31",
    "2085-05-31", "2086-05-31", "2087-05-31", "2089-05-31", "2090-05-31", "2092-05-31",
    "2094-05-31", "2095-05-31", "2096-05-31", "2097-05-31", "2098-05-31", "2100-05-31",
    "2101-05-31",
]  # fmt: skip
MARKER = "2079-05-31"
SUNDAYS = {
    "2026-05-31": "sanctissimae-trinitatis",
    "2037-05-31": "sanctissimae-trinitatis",
    "2043-05-31": "dominica-ii-post-pentecosten",
    "2048-05-31": "sanctissimae-trinitatis",
    "2054-05-31": "dominica-ii-post-pentecosten",
    "2065-05-31": "dominica-ii-post-pentecosten",
    "2071-05-31": "dominica-post-ascensionem",
    "2076-05-31": "dominica-post-ascensionem",
    "2082-05-31": "dominica-post-ascensionem",
    "2093-05-31": "dominica-pentecostes",
    "2099-05-31": "dominica-pentecostes",
}
FIRST_CLASS_WEEKDAYS = {
    "2029-05-31": "corpus-christi",
    "2031-05-31": "vigilia-pentecostes",
    "2036-05-31": "vigilia-pentecostes",
    "2040-05-31": "corpus-christi",
    "2057-05-31": "ascensio-domini",
    "2068-05-31": "ascensio-domini",
}
# The 63 Greater-Litanies (date, Mass) pairs of selection schema 1.0.0, unchanged in 2.0.0 and
# 2.1.0.
LITANIES_SHA256 = "99f31b8d14c69419dc53a46df618fa10ced665db90bf0fddcbd35c396f69be7f"
# Identity order of the resource: dominica-impedita, feria-adventus, festum-impeditum,
# litaniae-maiores, sancta-petronilla.
LITANIES_INDEX, SP_INDEX = 3, 4
# The impeded Sunday's pairs (tests/test_dominica_impedita.py).
IMPEDED_SUNDAY_PAIRS = 75
# The impeded feast's pairs (tests/test_festum_impeditum.py).
IMPEDED_FEAST_PAIRS = 206
# The Advent feria's pairs (tests/test_feria_adventus.py).
ADVENT_FERIA_PAIRS = 163


@pytest.fixture(scope="module")
def inputs():
    return canonical_inputs(CORPUS)


@pytest.fixture(scope="module")
def table(inputs):
    forms, calendar = inputs
    return producer.calendar_table(forms, calendar, corpus=CORPUS)


def authored():
    return json.loads((CORPUS / "commemorationes" / f"{SP}.json").read_text(encoding="utf-8"))


def decided(table):
    index = [entry["id"] for entry in table["commemorations"]].index(SP)
    names = [decision["id"] for decision in table["decisions"]]
    return {
        row[0]: (
            table["masses"][row[1]],
            row[3],
            dict(zip(table["situations"], (names[v] for v in row[4:7]), strict=True)),
        )
        for row in table["pairs"]
        if row[2] == index
    }


LOW_AND_CONVENTUAL = {
    "lecta": "admitted",
    "cantu-conventualis": "admitted",
    "cantu-non-conventualis": "not-admitted",
}
OMITTED_FOR_VIGIL = {
    "lecta": "omitted-required-de-tempore-unavailable",
    "cantu-conventualis": "omitted-required-de-tempore-unavailable",
    "cantu-non-conventualis": "not-admitted",
}


def assert_plan(table):
    plan = decided(table)
    assert sorted(plan) == sorted([*ADMITTED, MARKER]), "Petronilla decided on her dates"
    for day in ADMITTED:
        assert plan[day] == (QUEENSHIP, 0, LOW_AND_CONVENTUAL), "low and conventual only"
    assert plan[MARKER] == (QUEENSHIP, 0, OMITTED_FOR_VIGIL), "2079 marker"


def test_the_authored_contract_is_exact_and_reaches_its_three_propers():
    doc = authored()
    assert doc["commemoration_schema"] == "1.4.0" and doc["id"] == SP
    assert doc["title"] == "S. Petronillæ Virginis"
    assert (doc["rank"], doc["scope"], doc["conclusion"]) == ("ordinary", "missa", "separate")
    assert doc["occurrence"] == {"month": 5, "day": 31, "transfer": "none"}
    assert doc["text_prefix"] == "sanctae-petronillae"
    assert [(s["key"], s["text"], s["relation"]) for s in doc["slots"]] == [
        (key, text, "proper") for key, text in SLOTS
    ]
    assert all(s["after"] == s["key"] for s in doc["slots"])
    rubrics = doc["rubrics"]
    assert set(rubrics) == {"date", "scope", "rank", "admission", "conclusion"}
    assert "544" in rubrics["date"] and "541" in rubrics["date"]
    assert "108" in rubrics["rank"] and "111" in rubrics["admission"]
    assert "113" in rubrics["admission"] and "Vigil of the Ascension" in rubrics["admission"]
    for language, title in (
        ("pl", "Świętej Petroneli, Dziewicy"),
        ("en", "Saint Petronilla, Virgin"),
    ):
        localized = json.loads(
            (CORPUS / "languages" / language / "commemorationes" / f"{SP}.json").read_text(
                encoding="utf-8"
            )
        )
        assert localized == {
            "commemoration_schema": "1.0.0",
            "id": SP,
            "language": language,
            "title": title,
        }


def test_she_occurs_every_31_may_and_is_never_transferred(table):
    index = [entry["id"] for entry in table["commemorations"]].index(SP)
    assert index == SP_INDEX and table["commemorations"][index]["rank"] == "ordinary"
    assert sorted(day for day, i in table["occurrences"] if i == index) == [
        f"{y}-05-31" for y in producer.YEARS
    ]
    for civil_year in (2026, 2079, 2101):
        assert producer.occurrence(authored(), civil_year) == date(civil_year, 5, 31)


def test_the_admitted_dates_are_the_printed_rule_dates_and_the_calendar_derivation(table):
    assert_plan(table)
    queenship = [
        day.when.isoformat()
        for ending in producer.YEARS
        for day in year(ending)
        if (day.when.month, day.when.day) == (5, 31) and day.formulary == QUEENSHIP
    ]
    vigil = [d for d in queenship if date.fromisoformat(d) == easter(int(d[:4])) + timedelta(38)]
    assert vigil == [MARKER]
    assert sorted(set(queenship) - set(vigil)) == ADMITTED and len(ADMITTED) == 43


@pytest.mark.parametrize("day", ["2027-05-31", "2028-05-31", "2032-05-31", "2101-05-31"])
def test_sampled_weekdays_admit_her_in_low_and_sung_conventual_masses_only(table, day):
    assert date.fromisoformat(day).weekday() != 6
    assert decided(table)[day] == (QUEENSHIP, 0, LOW_AND_CONVENTUAL)


@pytest.mark.parametrize("day", sorted(SUNDAYS))
def test_a_sunday_31_may_publishes_no_pair_for_her(table, inputs, day):
    _forms, calendar = inputs
    row = next(r for rows in calendar["years"].values() for r in rows if r[0] == day)
    assert date.fromisoformat(day).weekday() == 6
    assert calendar["formularies"][row[1]] == SUNDAYS[day]
    assert day not in decided(table)
    index = [entry["id"] for entry in table["commemorations"]].index(SP)
    assert [day, index] in table["occurrences"]


@pytest.mark.parametrize("day", sorted(FIRST_CLASS_WEEKDAYS))
def test_a_first_class_weekday_publishes_no_pair_for_her(table, inputs, day):
    _forms, calendar = inputs
    row = next(r for rows in calendar["years"].values() for r in rows if r[0] == day)
    assert date.fromisoformat(day).weekday() != 6 and row[3] == 1
    assert calendar["formularies"][row[1]] == FIRST_CLASS_WEEKDAYS[day]
    assert day not in decided(table)


def test_2079_is_an_explicit_omission_for_the_unavailable_vigil_not_an_empty_plan(table):
    rows = [row for row in table["pairs"] if row[0] == MARKER]
    assert len(rows) == 1
    assert producer.unavailable_de_tempore(date(2079, 5, 31)) == "vigilia-ascensionis"
    assert table["decisions"][rows[0][4]] == {"id": "omitted-required-de-tempore-unavailable"}
    assert decided(table)[MARKER][2] == OMITTED_FOR_VIGIL
    assert all(producer.unavailable_de_tempore(date.fromisoformat(d)) is None for d in ADMITTED)


def test_both_sung_situations_are_published_separately(table):
    plan = decided(table)
    assert table["situations"] == ["lecta", "cantu-conventualis", "cantu-non-conventualis"]
    assert {situation for _mass, _profile, by in plan.values() for situation in by} == set(
        table["situations"]
    )
    assert all(by["lecta"] == by["cantu-conventualis"] for _m, _p, by in plan.values())
    assert all(by["cantu-non-conventualis"] == "not-admitted" for _m, _p, by in plan.values())


def test_the_greater_litanies_decisions_are_unchanged(table):
    rows = [row for row in table["pairs"] if row[2] == LITANIES_INDEX]
    pairs = sorted([row[0], table["masses"][row[1]]] for row in rows)
    raw = json.dumps(pairs, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert hashlib.sha256(raw.encode()).hexdigest() == LITANIES_SHA256
    assert all(row[3:] == [0, 0, 0, 0, None] for row in rows)
    assert (
        len(table["pairs"])
        == len(rows)
        + 1
        + len(ADMITTED)
        + IMPEDED_SUNDAY_PAIRS
        + IMPEDED_FEAST_PAIRS
        + ADVENT_FERIA_PAIRS
    )


def test_the_resource_equals_the_independent_reconstruction(table):
    assert table == reader.expected(CORPUS)


def test_an_all_masses_ordinary_commemoration_is_rejected(table, inputs, monkeypatch):
    bad = copy.deepcopy(table)
    row = next(r for r in bad["pairs"] if r[0] == ADMITTED[0])
    row[6] = 0
    with pytest.raises(ValueError, match="not admitted in a sung Mass that is not conventual"):
        producer.validate(bad)
    producer.validate(table)
    real = producer.decision
    monkeypatch.setattr(
        producer,
        "decision",
        lambda doc, when, dies_class: (
            [0, 0, 0]
            if doc["rank"] == "ordinary" and real(doc, when, dies_class)
            else real(doc, when, dies_class)
        ),
    )
    forms, calendar = inputs
    with pytest.raises(ValueError, match="not admitted in a sung Mass that is not conventual"):
        producer.calendar_table(forms, calendar, corpus=CORPUS)
    monkeypatch.undo()
    assert_plan(producer.calendar_table(forms, calendar, corpus=CORPUS))


def test_an_ignored_single_place_is_rejected(table, inputs, monkeypatch):
    monkeypatch.setattr(producer, "unavailable_de_tempore", lambda when: None)
    forms, calendar = inputs
    ignored = producer.calendar_table(forms, calendar, corpus=CORPUS)
    with pytest.raises(AssertionError, match="2079 marker"):
        assert_plan(ignored)
    assert ignored != reader.expected(CORPUS)
    monkeypatch.undo()
    assert_plan(producer.calendar_table(forms, calendar, corpus=CORPUS))
    # A second commemoration admitted beside the first on one date, Mass and situation.
    crowded = copy.deepcopy(table)
    litany = next(r for r in crowded["pairs"] if r[2] == LITANIES_INDEX)
    crowded["occurrences"] = sorted([*crowded["occurrences"], [litany[0], SP_INDEX]])
    crowded["pairs"] = sorted(
        [*crowded["pairs"], [litany[0], litany[1], SP_INDEX, 0, 0, 0, 1, None]]
    )
    with pytest.raises(ValueError, match="single commemoration"):
        producer.validate(crowded)
    beside_marker = copy.deepcopy(table)
    marker = next(r for r in beside_marker["pairs"] if r[0] == MARKER)
    beside_marker["occurrences"] = sorted([*beside_marker["occurrences"], [MARKER, LITANIES_INDEX]])
    beside_marker["pairs"] = sorted(
        [*beside_marker["pairs"], [MARKER, marker[1], LITANIES_INDEX, 0, 0, 0, 0, None]]
    )
    with pytest.raises(ValueError, match="single commemoration"):
        producer.validate(beside_marker)
    producer.validate(table)


def test_a_wrong_date_is_rejected(table, inputs, monkeypatch):
    substituted = copy.deepcopy(table)
    forms, calendar = inputs
    trinity = next(r for rows in calendar["years"].values() for r in rows if r[0] == "2026-05-31")
    mass = substituted["masses"].index("sanctissimae-trinitatis")
    assert calendar["formularies"][trinity[1]] == "sanctissimae-trinitatis"
    substituted["pairs"] = sorted(
        [r for r in substituted["pairs"] if r[0] != ADMITTED[0]]
        + [["2026-05-31", mass, SP_INDEX, 0, 0, 0, 1, None]]
    )
    producer.validate(substituted)  # well formed, same count
    assert len(substituted["pairs"]) == len(table["pairs"])
    assert substituted != reader.expected(CORPUS)
    with pytest.raises(AssertionError, match="Petronilla decided on her dates"):
        assert_plan(substituted)
    moved = copy.deepcopy(table)
    row = next(r for r in moved["pairs"] if r[0] == ADMITTED[0])
    row[0] = "2027-05-30"
    moved["pairs"].sort()
    with pytest.raises(ValueError, match="published occurrence"):
        producer.validate(moved)
    wrong = authored()
    wrong["occurrence"]["day"] = 30
    real = producer.authored
    monkeypatch.setattr(
        producer,
        "authored",
        lambda corpus: [wrong if doc["id"] == SP else doc for doc in real(corpus)],
    )
    with pytest.raises(ValueError, match="outside the modeled scope"):
        producer.calendar_table(forms, calendar, corpus=CORPUS)
    monkeypatch.undo()
    assert_plan(producer.calendar_table(forms, calendar, corpus=CORPUS))


def checker_corpus(tmp_path, doc):
    corpus = tmp_path / "corpus"
    (corpus / "commemorationes").mkdir(parents=True)
    (corpus / "texts" / "proprium").mkdir(parents=True)
    for _key, text in SLOTS:
        (corpus / "texts" / "proprium" / (text.split(".", 1)[1] + ".json")).write_text("{}")
    for language in ("pl", "en"):
        (corpus / "languages" / language / "commemorationes").mkdir(parents=True)
        (corpus / "languages" / language / "manifest.json").write_text("{}")
        source = CORPUS / "languages" / language / "commemorationes" / f"{SP}.json"
        target = corpus / "languages" / language / "commemorationes" / f"{SP}.json"
        target.write_bytes(source.read_bytes())
    (corpus / "commemorationes" / f"{SP}.json").write_text(json.dumps(doc), encoding="utf-8")
    return corpus


def _nonexistent_dependency(doc):
    doc["slots"][2]["text"] = "proprium.sanctae-petronillae-oratio"


def _privileged_transfer(doc):
    doc["occurrence"]["transfer"] = "easter-sunday-or-monday-to-tuesday"


AUTHORED_MUTATIONS = {
    "nonexistent-dependency": (_nonexistent_dependency, "missing text"),
    "no-prefix": (lambda d: d.pop("text_prefix"), "proper relation must address"),
    "privileged-transfer": (_privileged_transfer, "cannot use transfer rule"),
    "wrong-date": (lambda d: d["occurrence"].__setitem__("day", 30), "outside the fixed dates"),
    "redundant-prefix": (lambda d: d.__setitem__("text_prefix", SP), "text_prefix must be"),
    "extra-field": (lambda d: d.__setitem__("missa", "vultum-tuum"), "exact commemoration"),
}


@pytest.mark.parametrize("name", sorted(AUTHORED_MUTATIONS))
def test_authored_mutations_are_rejected_by_the_checker(tmp_path, name):
    mutation, message = AUTHORED_MUTATIONS[name]
    doc = authored()
    assert checker.check(checker_corpus(tmp_path / "healthy", doc))[0] == []
    mutation(doc)
    errors, _counts = checker.check(checker_corpus(tmp_path / "broken", doc))
    assert errors and any(message in error for error in errors), errors


def test_a_slot_body_missing_from_a_language_package_fails_before_emission(tmp_path):
    corpus = tmp_path / "corpus"
    for directory in (
        "commemorationes",
        "languages/pl/commemorationes",
        "languages/en/commemorationes",
    ):
        shutil.copytree(CORPUS / directory, corpus / directory)
    slots = [
        s["text"]
        for path in (CORPUS / "commemorationes").glob("*.json")
        for s in json.loads(path.read_text(encoding="utf-8"))["slots"]
        if s["text"] is not None  # the impeded Sunday's and feast's slots are resolved per date
    ]
    for text in slots:
        relative = f"{text.replace('.', '/', 1)}.json"
        for prefix in ("texts/", "languages/pl/texts/", "languages/en/texts/"):
            (corpus / prefix / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(CORPUS / prefix / relative, corpus / prefix / relative)
    for language in ("pl", "en"):
        manifest = json.loads(
            (CORPUS / f"languages/{language}/manifest.json").read_text(encoding="utf-8")
        )
        manifest["texts"] = [text for text in manifest["texts"] if text in slots]
        (corpus / f"languages/{language}/manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
        )
    reader.input_bodies(corpus)
    path = corpus / "languages/pl/manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["texts"].remove("proprium.sanctae-petronillae-postcommunio")
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="sanctae-petronillae-postcommunio requires a declared pl"):
        reader.input_bodies(corpus)
