"""The impeded Sunday, commemorated in the Mass of the first-class feast that takes its place:
the authored contract, the 75 dates of the supported span with the Sunday resolved on each, the
resumed Sunday after Epiphany of RG 18, the Second Sunday of Advent under the Immaculate
Conception, the decision in each Mass situation, the dependency on the resolved formulary's own
orations, the days with no such commemoration, and the owned negative controls. The 75 rows are
stated literally, as Rubricae generales 15–18 and 108–109 give them, and are compared with an
independent derivation from the calendar."""

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
DI = "dominica-impedita"
ORATIONS = ("collecta", "secreta", "postcommunio")
FEASTS = [
    "assumptio-beatae-mariae-virginis",
    "dedicatio-sancti-michaelis-archangeli",
    "immaculata-conceptio",
    "nativitas-sancti-ioannis-baptistae",
    "omnium-sanctorum",
    "sancti-ioseph-opificis",
    "sancti-petri-et-pauli-apostolorum",
]
# Each date of the supported span (liturgical years 2026-2101) on which one of the feasts is
# kept on a Sunday it impedes: (the feast, the Sunday commemorated).
IMPEDED = {
    "2026-11-01": ("omnium-sanctorum", "dominica-xxiii-post-pentecosten"),
    "2027-08-15": ("assumptio-beatae-mariae-virginis", "dominica-xiii-post-pentecosten"),
    "2029-06-24": ("nativitas-sancti-ioannis-baptistae", "dominica-v-post-pentecosten"),
    "2030-09-29": ("dedicatio-sancti-michaelis-archangeli", "dominica-xvi-post-pentecosten"),
    "2030-12-08": ("immaculata-conceptio", "dominica-ii-adventus"),
    "2031-06-29": ("sancti-petri-et-pauli-apostolorum", "dominica-iv-post-pentecosten"),
    "2032-08-15": ("assumptio-beatae-mariae-virginis", "dominica-xiii-post-pentecosten"),
    "2033-05-01": ("sancti-ioseph-opificis", "dominica-ii-post-pascha"),
    "2035-06-24": ("nativitas-sancti-ioannis-baptistae", "dominica-vi-post-pentecosten"),
    "2036-06-29": ("sancti-petri-et-pauli-apostolorum", "dominica-iv-post-pentecosten"),
    "2037-11-01": ("omnium-sanctorum", "dominica-xxiii-post-pentecosten"),
    "2038-08-15": ("assumptio-beatae-mariae-virginis", "dominica-ix-post-pentecosten"),
    "2039-05-01": ("sancti-ioseph-opificis", "dominica-iii-post-pascha"),
    "2040-06-24": ("nativitas-sancti-ioannis-baptistae", "dominica-v-post-pentecosten"),
    "2041-09-29": ("dedicatio-sancti-michaelis-archangeli", "dominica-xvi-post-pentecosten"),
    "2041-12-08": ("immaculata-conceptio", "dominica-ii-adventus"),
    "2042-06-29": ("sancti-petri-et-pauli-apostolorum", "dominica-v-post-pentecosten"),
    "2043-11-01": ("omnium-sanctorum", "dominica-iv-quae-superfuit-post-epiphaniam"),
    "2044-05-01": ("sancti-ioseph-opificis", "dominica-ii-post-pascha"),
    "2046-06-24": ("nativitas-sancti-ioannis-baptistae", "dominica-vi-post-pentecosten"),
    "2047-09-29": ("dedicatio-sancti-michaelis-archangeli", "dominica-xvii-post-pentecosten"),
    "2047-12-08": ("immaculata-conceptio", "dominica-ii-adventus"),
    "2048-11-01": ("omnium-sanctorum", "dominica-xxiii-post-pentecosten"),
    "2049-08-15": ("assumptio-beatae-mariae-virginis", "dominica-x-post-pentecosten"),
    "2050-05-01": ("sancti-ioseph-opificis", "dominica-iii-post-pascha"),
    "2052-09-29": ("dedicatio-sancti-michaelis-archangeli", "dominica-xvi-post-pentecosten"),
    "2052-12-08": ("immaculata-conceptio", "dominica-ii-adventus"),
    "2053-06-29": ("sancti-petri-et-pauli-apostolorum", "dominica-v-post-pentecosten"),
    "2054-11-01": ("omnium-sanctorum", "dominica-iv-quae-superfuit-post-epiphaniam"),
    "2055-08-15": ("assumptio-beatae-mariae-virginis", "dominica-x-post-pentecosten"),
    "2057-06-24": ("nativitas-sancti-ioannis-baptistae", "dominica-ii-post-pentecosten"),
    "2058-09-29": ("dedicatio-sancti-michaelis-archangeli", "dominica-xvii-post-pentecosten"),
    "2058-12-08": ("immaculata-conceptio", "dominica-ii-adventus"),
    "2059-06-29": ("sancti-petri-et-pauli-apostolorum", "dominica-vi-post-pentecosten"),
    "2060-08-15": ("assumptio-beatae-mariae-virginis", "dominica-x-post-pentecosten"),
    "2061-05-01": ("sancti-ioseph-opificis", "dominica-iii-post-pascha"),
    "2063-06-24": ("nativitas-sancti-ioannis-baptistae", "dominica-iii-post-pentecosten"),
    "2064-06-29": ("sancti-petri-et-pauli-apostolorum", "dominica-v-post-pentecosten"),
    "2065-11-01": ("omnium-sanctorum", "dominica-iv-quae-superfuit-post-epiphaniam"),
    "2066-08-15": ("assumptio-beatae-mariae-virginis", "dominica-xi-post-pentecosten"),
    "2067-05-01": ("sancti-ioseph-opificis", "dominica-iv-post-pascha"),
    "2068-06-24": ("nativitas-sancti-ioannis-baptistae", "dominica-ii-post-pentecosten"),
    "2069-09-29": ("dedicatio-sancti-michaelis-archangeli", "dominica-xvii-post-pentecosten"),
    "2069-12-08": ("immaculata-conceptio", "dominica-ii-adventus"),
    "2070-06-29": ("sancti-petri-et-pauli-apostolorum", "dominica-vi-post-pentecosten"),
    "2071-11-01": ("omnium-sanctorum", "dominica-xxi-post-pentecosten"),
    "2072-05-01": ("sancti-ioseph-opificis", "dominica-iii-post-pascha"),
    "2074-06-24": ("nativitas-sancti-ioannis-baptistae", "dominica-iii-post-pentecosten"),
    "2075-09-29": ("dedicatio-sancti-michaelis-archangeli", "dominica-xviii-post-pentecosten"),
    "2075-12-08": ("immaculata-conceptio", "dominica-ii-adventus"),
    "2076-11-01": ("omnium-sanctorum", "dominica-xxi-post-pentecosten"),
    "2077-08-15": ("assumptio-beatae-mariae-virginis", "dominica-xi-post-pentecosten"),
    "2078-05-01": ("sancti-ioseph-opificis", "dominica-iv-post-pascha"),
    "2080-09-29": ("dedicatio-sancti-michaelis-archangeli", "dominica-xviii-post-pentecosten"),
    "2080-12-08": ("immaculata-conceptio", "dominica-ii-adventus"),
    "2081-06-29": ("sancti-petri-et-pauli-apostolorum", "dominica-vi-post-pentecosten"),
    "2082-11-01": ("omnium-sanctorum", "dominica-xxi-post-pentecosten"),
    "2083-08-15": ("assumptio-beatae-mariae-virginis", "dominica-xii-post-pentecosten"),
    "2085-06-24": ("nativitas-sancti-ioannis-baptistae", "dominica-iii-post-pentecosten"),
    "2086-09-29": ("dedicatio-sancti-michaelis-archangeli", "dominica-xix-post-pentecosten"),
    "2086-12-08": ("immaculata-conceptio", "dominica-ii-adventus"),
    "2087-06-29": ("sancti-petri-et-pauli-apostolorum", "dominica-iii-post-pentecosten"),
    "2088-08-15": ("assumptio-beatae-mariae-virginis", "dominica-xi-post-pentecosten"),
    "2089-05-01": ("sancti-ioseph-opificis", "dominica-iv-post-pascha"),
    "2091-06-24": ("nativitas-sancti-ioannis-baptistae", "dominica-iv-post-pentecosten"),
    "2092-06-29": ("sancti-petri-et-pauli-apostolorum", "dominica-vi-post-pentecosten"),
    "2093-11-01": ("omnium-sanctorum", "dominica-xxii-post-pentecosten"),
    "2094-08-15": ("assumptio-beatae-mariae-virginis", "dominica-xii-post-pentecosten"),
    "2096-06-24": ("nativitas-sancti-ioannis-baptistae", "dominica-iii-post-pentecosten"),
    "2097-09-29": ("dedicatio-sancti-michaelis-archangeli", "dominica-xix-post-pentecosten"),
    "2097-12-08": ("immaculata-conceptio", "dominica-ii-adventus"),
    "2098-06-29": ("sancti-petri-et-pauli-apostolorum", "dominica-iii-post-pentecosten"),
    "2099-11-01": ("omnium-sanctorum", "dominica-xxii-post-pentecosten"),
    "2100-08-15": ("assumptio-beatae-mariae-virginis", "dominica-xiii-post-pentecosten"),
    "2101-05-01": ("sancti-ioseph-opificis", "dominica-ii-post-pascha"),
}
RESUMED_IV = "dominica-iv-quae-superfuit-post-epiphaniam"
RG18 = ["2043-11-01", "2054-11-01", "2065-11-01"]
# The first-class feast of the Lord that takes a Sunday's place with no commemoration (16 a).
PRECIOUS_BLOOD_SUNDAYS = [
    "2029-07-01", "2035-07-01", "2040-07-01", "2046-07-01", "2057-07-01", "2063-07-01",
    "2068-07-01", "2074-07-01", "2085-07-01", "2091-07-01", "2096-07-01",
]  # fmt: skip
ALL_ADMITTED = dict.fromkeys(("lecta", "cantu-conventualis", "cantu-non-conventualis"), "admitted")


@pytest.fixture(scope="module")
def inputs():
    return canonical_inputs(CORPUS)


@pytest.fixture(scope="module")
def table(inputs):
    forms, calendar = inputs
    return producer.calendar_table(forms, calendar, corpus=CORPUS)


def authored():
    return json.loads((CORPUS / "commemorationes" / f"{DI}.json").read_text(encoding="utf-8"))


def index_of(table, identity=DI):
    return [entry["id"] for entry in table["commemorations"]].index(identity)


def decided(table):
    index = index_of(table)
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
    assert sorted(plan) == sorted(IMPEDED), "the impeded Sunday decided on its dates"
    for day in RG18:
        assert plan[day][3] == RESUMED_IV, "RG 18"
    for day, (feast, sunday) in IMPEDED.items():
        assert plan[day] == (feast, 0, ALL_ADMITTED, sunday), "admitted in all Masses"


def derived_from_the_calendar():
    """From kalendarium.roman.year alone: the feast's day keeps the impeded Sunday's position,
    and RG 18 is restated from the year's chronological count of Sundays after Pentecost."""
    found = {}
    for ending in producer.YEARS:
        days = year(ending)
        after = [
            day.when
            for day in days
            if day.position.startswith("dominica-") and day.position.endswith("-post-pentecosten")
        ]
        for day in days:
            if day.formulary not in FEASTS or day.when.weekday() != 6:
                continue
            sunday = day.position
            if day.when in after:
                place, total = after.index(day.when) + 1, len(after)
                if place == total:
                    sunday = "dominica-xxiv-post-pentecosten"
                elif place > 23:
                    numeral = ["iii", "iv", "v", "vi"][6 - (total - 1 - place) - 3]
                    sunday = f"dominica-{numeral}-quae-superfuit-post-epiphaniam"
            found[day.when.isoformat()] = (day.formulary, sunday)
    return found


def test_the_authored_contract_is_exact_and_resolves_its_slots_by_the_calendar():
    doc = authored()
    assert set(doc) == checker.KEYS and doc["commemoration_schema"] == "1.4.0"
    assert (doc["id"], doc["title"]) == (DI, "Dominica impedita")
    assert (doc["rank"], doc["scope"], doc["conclusion"]) == ("privileged", "missa", "separate")
    assert doc["occurrence"] == {"kind": "displaced-sunday", "feasts": FEASTS}
    assert doc["slots"] == [
        {"key": key, "after": key, "text": None, "relation": "calendar"} for key in ORATIONS
    ]
    rubrics = doc["rubrics"]
    assert set(rubrics) == {"date", "scope", "rank", "admission", "conclusion"}
    assert "15–18" in rubrics["date"] and "[XII]" in rubrics["date"] and "(18)" in rubrics["date"]
    assert "16 a, 17, 112 b" in rubrics["date"] and "XVII" in rubrics["date"]
    assert "Rubricae generales 14" in rubrics["scope"]
    assert "108–109 a" in rubrics["rank"] and "XVIII" in rubrics["rank"]
    assert "111 a" in rubrics["admission"] and "434 a" in rubrics["admission"]
    assert "436–437" in rubrics["conclusion"] and "XXXI" in rubrics["conclusion"]
    for language, title in (("pl", "Niedziela przeszkodzona"), ("en", "Impeded Sunday")):
        localized = json.loads(
            (CORPUS / "languages" / language / "commemorationes" / f"{DI}.json").read_text(
                encoding="utf-8"
            )
        )
        assert localized == {
            "commemoration_schema": "1.1.0",
            "id": DI,
            "language": language,
            "title": title,
        }
    errors, counts = checker.check(CORPUS)
    # Three calendar slots here, three in the impeded feast (tests/test_festum_impeditum.py) and
    # three in the Advent feria (tests/test_feria_adventus.py).
    assert errors == [] and counts["calendar_slots"] == 9


def test_the_feasts_are_the_first_class_feasts_that_commemorate_the_sunday_they_impede():
    first_class = {feast.formulary for feast in FESTA if feast.dies_class == 1}
    assert set(FEASTS) < first_class and sorted(FEASTS) == FEASTS
    assert list(checker.DISPLACED_SUNDAY_FEASTS) == FEASTS
    # The other four: a feast of the Lord (16 a); two feasts that always meet a first-class
    # Sunday of Lent or Passiontide and are transferred (96); and All Souls, to which a Sunday is
    # preferred (16 b, 96 b). Only the feast of the Lord is ever kept on a Sunday.
    lord = "pretiosissimi-sanguinis-domini-nostri-iesu-christi"
    assert first_class - set(FEASTS) == {
        lord,
        "sancti-ioseph-sponsi-beatae-mariae-virginis",
        "annuntiatio-beatae-mariae-virginis",
        "commemoratio-omnium-fidelium-defunctorum",
    }
    kept = [
        (day.when.isoformat(), day.formulary)
        for ending in producer.YEARS
        for day in year(ending)
        if day.formulary in first_class - set(FEASTS) and day.when.weekday() == 6
    ]
    assert kept == [(day, lord) for day in PRECIOUS_BLOOD_SUNDAYS]


def test_the_dates_and_sundays_are_the_printed_rules_and_the_calendar_derivation(table):
    assert derived_from_the_calendar() == IMPEDED and len(IMPEDED) == 75
    counts = {feast: sum(1 for f, _s in IMPEDED.values() if f == feast) for feast in FEASTS}
    assert counts == {
        "assumptio-beatae-mariae-virginis": 12,
        "dedicatio-sancti-michaelis-archangeli": 10,
        "immaculata-conceptio": 10,
        "nativitas-sancti-ioannis-baptistae": 11,
        "omnium-sanctorum": 11,
        "sancti-ioseph-opificis": 10,
        "sancti-petri-et-pauli-apostolorum": 11,
    }
    assert len({sunday for _f, sunday in IMPEDED.values()}) == 22
    assert producer.impeded_sundays(authored()) == {d: s for d, (_f, s) in IMPEDED.items()}
    assert_plan(table)


def test_every_date_is_an_occurrence_and_no_other_date_is(table):
    index = index_of(table)
    assert sorted(day for day, i in table["occurrences"] if i == index) == sorted(IMPEDED)
    for day in PRECIOUS_BLOOD_SUNDAYS:
        assert [day, index] not in table["occurrences"] and day not in decided(table)


@pytest.mark.parametrize("day", RG18)
def test_rg18_resolves_the_resumed_fourth_sunday_after_epiphany_not_the_position(
    table, inputs, day
):
    forms, calendar = inputs
    row = next(r for rows in calendar["years"].values() for r in rows if r[0] == day)
    assert calendar["formularies"][row[1]] == "omnium-sanctorum"
    assert calendar["formularies"][row[4]] == "dominica-xxiv-post-pentecosten"
    assert decided(table)[day] == ("omnium-sanctorum", 0, ALL_ADMITTED, RESUMED_IV)
    resumed = next(form for form in forms if form["id"] == RESUMED_IV)
    assert producer.sunday_orations(resumed) == [
        f"proprium/dominica-iv-post-epiphaniam-{key}" for key in ORATIONS
    ]


def test_the_position_is_the_sunday_when_rg18_does_not_apply(table, inputs):
    _forms, calendar = inputs
    row = next(r for rows in calendar["years"].values() for r in rows if r[0] == "2026-11-01")
    assert calendar["formularies"][row[4]] == "dominica-xxiii-post-pentecosten"
    assert decided(table)["2026-11-01"][3] == "dominica-xxiii-post-pentecosten"
    advent = [day for day, (feast, _s) in IMPEDED.items() if feast == "immaculata-conceptio"]
    assert len(advent) == 10 and all(day.endswith("-12-08") for day in advent)
    assert {decided(table)[day][3] for day in advent} == {"dominica-ii-adventus"}


def test_every_resolved_sunday_says_its_own_formularys_three_orations(inputs):
    forms, _calendar = inputs
    by_id = {form["id"]: form for form in forms}
    bodies = reader.slot_bodies(CORPUS)
    for sunday in sorted({s for _f, s in IMPEDED.values()}):
        texts = producer.sunday_orations(by_id[sunday])
        source = "dominica-iv-post-epiphaniam" if sunday == RESUMED_IV else sunday
        assert texts == [f"proprium/{source}-{key}" for key in ORATIONS]
        for text in texts:
            dotted = text.replace("/", ".", 1)
            assert dotted in bodies
            for language in ("pl", "en"):
                assert dotted in store.language_manifest(CORPUS, language)["texts"]
    reader.input_bodies(CORPUS)


@pytest.mark.parametrize("day", ["2026-11-01", "2030-12-08", "2033-05-01", "2101-05-01"])
def test_sampled_dates_admit_the_sunday_in_every_mass_situation(table, day):
    feast, sunday = IMPEDED[day]
    assert date.fromisoformat(day).weekday() == 6
    assert decided(table)[day] == (feast, 0, ALL_ADMITTED, sunday)


def test_no_other_commemoration_shares_an_impeded_sunday(table):
    index = index_of(table)
    assert not [row for row in table["pairs"] if row[0] in IMPEDED and row[2] != index]
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


def test_the_position_cannot_stand_for_the_formulary(table, inputs, monkeypatch):
    monkeypatch.setattr(producer, "impeded_sunday", lambda day, ending: day.position)
    forms, calendar = inputs
    positional = producer.calendar_table(forms, calendar, corpus=CORPUS)
    with pytest.raises(AssertionError, match="RG 18"):
        assert_plan(positional)
    assert positional != reader.expected(CORPUS)
    monkeypatch.undo()
    assert_plan(producer.calendar_table(forms, calendar, corpus=CORPUS))


def test_a_missing_dependency_is_stated_unavailable_and_never_admitted(table, inputs, monkeypatch):
    real = producer.sunday_orations
    monkeypatch.setattr(
        producer,
        "sunday_orations",
        lambda form: None if form and form["id"] == RESUMED_IV else real(form),
    )
    forms, calendar = inputs
    missing = producer.calendar_table(forms, calendar, corpus=CORPUS)
    plan = decided(missing)
    unavailable = dict.fromkeys(ALL_ADMITTED, "omitted-required-de-tempore-unavailable")
    for day in RG18:
        assert plan[day] == ("omnium-sanctorum", 0, unavailable, RESUMED_IV)
    with pytest.raises(AssertionError, match="admitted in all Masses"):
        assert_plan(missing)
    assert missing != reader.expected(CORPUS)
    monkeypatch.undo()
    assert_plan(producer.calendar_table(forms, calendar, corpus=CORPUS))


def _di_row(t):
    index = index_of(t)
    return next(row for row in t["pairs"] if row[2] == index)


def _litany_row(t):
    index = index_of(t, "litaniae-maiores")
    return next(row for row in t["pairs"] if row[2] == index)


RESOURCE_MUTATIONS = {
    "resolved-without-formulary": (
        lambda t: _di_row(t).__setitem__(7, None),
        "names its formulary exactly when",
    ),
    "addressed-with-formulary": (
        lambda t: _litany_row(t).__setitem__(7, "dominica-ii-adventus"),
        "names its formulary exactly when",
    ),
    "unauthored-formulary-admitted": (
        lambda t: _di_row(t).__setitem__(7, "dominica-vii-post-epiphaniam"),
        "needs an authored formulary",
    ),
    "partly-unavailable": (
        lambda t: _di_row(t).__setitem__(6, 2),
        "privileged commemoration is made in all Masses",
    ),
    "unavailable-without-formulary": (
        lambda t: _litany_row(t).__setitem__(slice(4, 7), [2, 2, 2]),
        "privileged commemoration is made in all Masses",
    ),
    "mixed-slots": (
        lambda t: t["commemorations"][index_of(t)]["slots"][0].__setitem__(
            "text", "proprium/dominica-ii-adventus-collecta"
        ),
        "all addressed or all resolved",
    ),
    "seven-values": (lambda t: _di_row(t).pop(), "pair rows are"),
    "not-an-identity": (lambda t: _di_row(t).__setitem__(7, "Dominica II"), "pair rows are"),
}


@pytest.mark.parametrize("name", sorted(RESOURCE_MUTATIONS))
def test_malformed_resolved_resources_are_rejected(table, name):
    mutation, message = RESOURCE_MUTATIONS[name]
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
        _feasts(lambda f: sorted([*f, "pretiosissimi-sanguinis-domini-nostri-iesu-christi"])),
        "feasts must be exactly",
    ),
    "missing-feast": (_feasts(lambda f: f[:-1]), "feasts must be exactly"),
    "unordered-feasts": (_feasts(lambda f: f[::-1]), "feasts must be exactly"),
    "ordinary": (lambda d: d.__setitem__("rank", "ordinary"), "cannot use occurrence kind"),
    "proper-slot": (
        lambda d: d["slots"][0].update(
            text="proprium.dominica-impedita-collecta", relation="proper"
        ),
        "the calendar relation is used by, and only by",
    ),
    "calendar-slot-names-a-text": (
        lambda d: d["slots"][1].__setitem__("text", "proprium.dominica-ii-adventus-secreta"),
        "names no text",
    ),
    "unknown-kind": (
        lambda d: d["occurrence"].__setitem__("kind", "sunday"),
        "occurrence kind needs exactly",
    ),
    "dated-kind": (
        lambda d: d["occurrence"].__setitem__("month", 11),
        "occurrence kind needs exactly",
    ),
    "text-prefix": (
        lambda d: d.__setitem__("text_prefix", "dominica"),
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


def test_a_fixed_date_commemoration_cannot_take_a_calendar_slot(tmp_path):
    litanies = json.loads(
        (CORPUS / "commemorationes" / "litaniae-maiores.json").read_text(encoding="utf-8")
    )
    assert checker.check(checker_corpus(tmp_path / "healthy", [litanies]))[0] == []
    litanies["slots"][2].update(text=None, relation="calendar")
    errors, _counts = checker.check(checker_corpus(tmp_path / "broken", [litanies]))
    assert any("the calendar relation is used by, and only by" in error for error in errors)


def test_a_resolved_oration_missing_from_a_language_package_fails_before_emission(tmp_path):
    corpus = tmp_path / "corpus"
    for directory in (
        "commemorationes",
        "formularies",
        "languages/pl/commemorationes",
        "languages/en/commemorationes",
    ):
        shutil.copytree(CORPUS / directory, corpus / directory)
    bodies = reader.slot_bodies(CORPUS)
    # The six addressed slots, the 22 Sundays' orations, the twenty impeded feasts' 59
    # (tests/test_festum_impeditum.py) and those of the First, Third and Fourth Sundays of Advent
    # that the Advent feria says (tests/test_feria_adventus.py; the Second is among the 22).
    assert len(bodies) == 6 + 3 * 22 + 59 + 3 * 3
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
    manifest["texts"].remove("proprium.dominica-iv-post-epiphaniam-secreta")
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(
        ValueError, match="dominica-iv-post-epiphaniam-secreta requires a declared en"
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
    collect = "proprium.dominica-xiii-post-pentecosten-collecta"
    package["texts"] = [d for d in package["texts"] if d["id"] != collect]
    path.write_text(json.dumps(package), encoding="utf-8")
    assert reader.verify(CORPUS, out, manifest, emit.SCHEMA) == [
        "commemorationes: languages/pl/texts/proprium/dominica-xiii-post-pentecosten-collecta.json"
        " must be declared exactly once"
    ]


def test_the_verifier_rejects_a_resource_resolved_to_another_sunday(tmp_path, table):
    wrong = copy.deepcopy(table)
    row = next(r for r in wrong["pairs"] if r[0] == RG18[0])
    row[7] = "dominica-xxiv-post-pentecosten"
    producer.validate(wrong)
    out, manifest = emitted(tmp_path, wrong)
    errors = reader.verify(CORPUS, out, manifest, emit.SCHEMA)
    assert (
        errors[0] == "commemorationes: resource differs from independent canonical reconstruction"
    )
    # The stand-in packages carry the orations of the true resolution only.
    assert len(errors) == 1 + 3 * 3
    assert all("/dominica-xxiv-post-pentecosten-" in error for error in errors[1:])
