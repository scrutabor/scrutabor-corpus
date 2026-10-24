"""The announcement before every Epistle and Gospel: bindings, events, the Passion rule and
their delivery.

Each reading the formularies name as an Epistle or a Gospel is bound once to the announcement
the Benziger editio iuxta typicam prints over it. The binding is restated here from the pinned
census of the printed headings (tests/fixtures/reading-announcement-bindings.json) and the
announcement texts themselves, never from the library: the unit is the one formula the printed
heading folds to, and the print is recorded only where it differs by an accent, a capital or a
closing full stop. The Epistle's announcement is said clara at a sung Mass as the Epistle is
(RG 514), the Gospel's is sung as the Gospel is (RG 473, 514), and the Passion takes its
announcement alone (RG 472). Every negative control is a real mutation with its owned
diagnostic, followed by restoration of the healthy state.
"""

import copy
import json
import re
import unicodedata
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from test_introductiones import COUNTS, edit, small_corpus, target_path

from build_reader import introductiones as reader
from build_reader import store
from checks import introductiones as checker

CORPUS = Path(__file__).resolve().parent.parent
LIBRARY = "ordo/introductiones.json"
FIXTURE = json.loads(
    (CORPUS / "tests/fixtures/reading-announcement-bindings.json").read_text(encoding="utf-8")
)
READINGS = FIXTURE["readings"]
FORMULAS = json.loads(
    (CORPUS / "tests/fixtures/reading-announcement-formulas.json").read_text(encoding="utf-8")
)
LAST_GOSPEL = "ordinarium.evangelium-ultimum"
PASSION = "proprium.dominica-ii-passionis-evangelium"
PASSIO = "passio-domini-nostri-iesu-christi-secundum-matthaeum"
CROSS = "✠ "
CLASS_PARTS = {
    "lectio-epistolae-pauli": "epistola",
    "lectio-epistolae-apostoli": "epistola",
    "lectio-actuum": "epistola",
    "lectio-libri": "epistola",
    "lectio-prophetae": "epistola",
    "sequentia": "evangelium",
    "initium": "evangelium",
    "passio": "evangelium",
}
CLASS_READINGS = {
    "lectio-epistolae-pauli": 62,
    "lectio-epistolae-apostoli": 11,
    "lectio-actuum": 7,
    "lectio-libri": 18,
    "lectio-prophetae": 5,
    "sequentia": 99,
    "initium": 2,
    "passio": 1,
}
VARIANTS = {
    "proprium.ascensio-domini-epistola": "Léctio Actuum Apostolórum",
    "proprium.corporis-christi-evangelium": "Sequéntia sancti Evangélii secundum Ioánnem",
    "proprium.dedicatio-archibasilicae-sanctissimi-salvatoris-epistola": (
        "Léctio libri Apocalypsis beáti Ioánnis Apóstoli"
    ),
    "proprium.dominica-i-passionis-epistola": "Léctio Epístolæ beáti Pauli Apostoli ad Hebrǽos",
    "proprium.dominica-in-quinquagesima-epistola": (
        "Léctio Epístolæ beáti Pauli Apostoli ad Corínthios"
    ),
    "proprium.dominica-pentecostes-epistola": "Léctio Actuum Apostolórum",
    "proprium.epiphania-domini-evangelium": "Sequéntia sancti Evangélii secúndum Matthǽum.",
    "proprium.feria-v-in-cena-domini-epistola": (
        "Léctio Epístolæ beáti Pauli apóstoli ad Corínthios"
    ),
    "proprium.immaculatum-cor-beatae-mariae-virginis-evangelium": (
        "Sequéntia sancti Evangelii secúndum Ioánnem"
    ),
    "proprium.nativitas-domini-in-aurora-epistola": "Léctio Epístolæ beáti Pauli Apostoli ad Titum",
    "proprium.nativitas-domini-in-die-evangelium": "Inítium sancti Evangélii secúndum Ioánnem",
    "proprium.sancti-andreae-apostoli-evangelium": "Sequéntia sancti Evangélii secúndum Matthǽum.",
    "proprium.sancti-matthiae-apostoli-epistola": "Léctio Actuum Apostolórum",
    "proprium.sancti-petri-et-pauli-apostolorum-epistola": "Léctio Actuum Apostolórum",
    "proprium.sancti-stephani-protomartyris-epistola": "Léctio Actuum Apostolórum",
    "proprium.sanctissimi-nominis-iesu-epistola": "Léctio Actuum Apostolórum",
    "proprium.sanctorum-innocentium-martyrum-epistola": (
        "Léctio libri Apocalypsis beáti Ioánnis Apóstoli"
    ),
    "proprium.vigilia-pentecostes-epistola": "Léctio Actuum Apostolórum",
}
MISPRINTS = {
    "proprium.dominica-iii-in-quadragesima-evangelium": ("Luc. 11, 4-28", [11, 14, 28]),
    "proprium.dominica-in-albis-evangelium": ("Ioann. 80, 19-31", [20, 19, 31]),
}
SUPPLIED = {
    "proprium.dominica-ii-passionis-evangelium": "Matth",
    "proprium.omnium-sanctorum-evangelium": "Matth",
}


def library() -> dict[str, Any]:
    return json.loads((CORPUS / LIBRARY).read_text(encoding="utf-8"))


def fold(value: str) -> str:
    bare = "".join(c for c in unicodedata.normalize("NFD", value) if c != "́")
    return unicodedata.normalize("NFC", bare).lower().removesuffix(".")


def formulas() -> dict[str, str]:
    """Every announcement unit and the words of its owner segment, read from the texts."""
    found: dict[str, str] = {}
    for formula in FORMULAS["formulas"]:
        core = store.core(CORPUS, formula["text"])
        found[formula["text"].split(".", 1)[1]] = " ".join(
            w["form"] + w.get("post", "") for w in core["segments"][0]["words"]
        )
    last = next(s for s in store.core(CORPUS, LAST_GOSPEL)["segments"] if s["id"] == "s05")
    found["initium-sancti-evangelii-secundum-ioannem"] = " ".join(
        w["form"] + w.get("post", "") for w in last["words"]
    )
    return found


def roles() -> dict[str, str]:
    found: dict[str, set[str]] = {}
    for formulary in store.formularies(CORPUS):
        for component in formulary["components"]:
            if component["role"] in ("epistola", "evangelium"):
                found.setdefault(component["text"], set()).add(component["role"])
    assert all(len(value) == 1 for value in found.values())
    return {text: value.pop() for text, value in found.items()}


def numbers(reference: str) -> list[int]:
    return [int(n) for n in re.findall(r"\d+", re.sub(r"^[12] (?=[A-Z])", "", reference))]


def pericope_numbers(pericope: dict[str, Any]) -> list[int]:
    found: list[int] = []
    for passage in pericope["passages"]:
        found.append(passage["chapter"])
        for first, last in passage["verses"]:
            found += [first] if first == last else [first, last]
    return found


def restated() -> list[dict[str, Any]]:
    """The 205 bindings from the census and the announcement texts alone."""
    units = formulas()
    by_fold = {fold(text): unit for unit, text in units.items()}
    assert len(by_fold) == len(units) == 27
    bindings: list[dict[str, Any]] = []
    for row in READINGS:
        heading = row["heading_as_printed"].removeprefix(CROSS)
        assert row["heading_as_printed"].startswith(CROSS) is (
            CLASS_PARTS[row["class"]] == "evangelium" and row["class"] != "passio"
        )
        unit = by_fold[fold(heading)]
        binding: dict[str, Any] = {"reading": row["reading"], "unit": unit, "leaf": row["leaf"]}
        binding["page"] = row["printed_page"]
        if heading != units[unit]:
            binding["as_printed"] = heading
        binding["reference_as_printed"] = row["reference_as_printed"]
        for key in ("book_supplied",):
            if key in row:
                binding[key] = row[key]
        binding["pericope"] = row["pericope"]
        for key in ("misprint", "comparator", "uncertain"):
            if key in row:
                binding[key] = row[key]
        bindings.append(binding)
    return bindings


# ---------------------------------------------------------------------------------------------
# The bindings
# ---------------------------------------------------------------------------------------------


def test_every_formulary_reading_is_bound_once_as_the_census_prints_it():
    doc = library()
    assert len(READINGS) == 205
    assert doc["announcements"] == restated()
    readings = roles()
    assert [b["reading"] for b in doc["announcements"]] == sorted(readings)
    assert Counter(readings.values()) == {"epistola": 103, "evangelium": 102}
    units = {unit["id"]: unit for unit in doc["units"]}
    for binding, row in zip(doc["announcements"], READINGS, strict=True):
        unit = units[binding["unit"]]
        assert unit["role"] == "announcement"
        assert CLASS_PARTS[row["class"]] == readings[binding["reading"]]
        head = binding["unit"].split("-", 1)[0]
        assert row["class"].startswith(head)
    assert Counter(row["class"] for row in READINGS) == CLASS_READINGS
    assert {b["unit"] for b in doc["announcements"]} == set(formulas())
    assert checker.check(CORPUS) == ([], COUNTS)


def test_the_print_is_recorded_only_where_it_differs_and_only_by_accent_case_or_stop():
    doc = library()
    units = formulas()
    printed = {b["reading"]: b["as_printed"] for b in doc["announcements"] if "as_printed" in b}
    assert printed == VARIANTS
    for binding in doc["announcements"]:
        if "as_printed" in binding:
            assert binding["as_printed"] != units[binding["unit"]]
            assert fold(binding["as_printed"]) == fold(units[binding["unit"]])
    stops = [r for r, value in printed.items() if value.endswith(".")]
    assert sorted(stops) == [
        "proprium.epiphania-domini-evangelium",
        "proprium.sancti-andreae-apostoli-evangelium",
    ]
    # The reused Last Gospel announcement ends with the full stop the Proper does not print.
    assert units["initium-sancti-evangelii-secundum-ioannem"].endswith("Ioánnem.")


def test_references_keep_the_print_beside_the_pericope_misprints_and_supplied_books():
    doc = library()
    for binding in doc["announcements"]:
        reading, reference = binding["reading"], binding["reference_as_printed"]
        if reading in MISPRINTS:
            assert (reference, pericope_numbers(binding["pericope"])) == MISPRINTS[reading]
            assert binding["misprint"] is True
            assert binding["comparator"].startswith("Divinum Officium (44667ff), Tempora/")
            assert numbers(reference) != pericope_numbers(binding["pericope"])
        else:
            assert not {"misprint", "comparator", "uncertain"} & set(binding)
            assert numbers(reference) == pericope_numbers(binding["pericope"])
        if reading in SUPPLIED:
            assert binding["book_supplied"] is True
            assert binding["pericope"]["book"] == SUPPLIED[reading]
            assert not re.match(r"[A-Z]", reference)
        else:
            assert "book_supplied" not in binding
            assert (
                checker.ABBREVIATIONS[checker.BOOK.match(reference)[1]]
                == (binding["pericope"]["book"])
            )
        assert binding["pericope"]["book"] in checker.UNIT_BOOKS[binding["unit"]]
    albis = next(
        b for b in doc["announcements"] if b["reading"] == "proprium.dominica-in-albis-evangelium"
    )
    assert "8" in albis["uncertain"] and "2" in albis["uncertain"]


def test_the_two_announcement_events_follow_the_order_of_the_mass():
    doc = library()
    ids = [event["id"] for event in doc["events"]]
    assert ids == list(checker.EVENTS)
    assert ids.index("epistola-annuntiatio") == ids.index("collecta-introductio") + 1
    assert ids.index("evangelium-annuntiatio") == ids.index("evangelium-salutatio") + 1
    events = {event["id"]: event for event in doc["events"]}
    (epistle,) = events["epistola-annuntiatio"]["occurrences"]
    announcement, answer = events["evangelium-annuntiatio"]["occurrences"]
    for slot in (epistle, announcement):
        assert set(slot) == {"slot", "lecta", "cantu"} and slot["slot"] == "announcement"
        assert slot["lecta"]["speaker"] == "sacerdos" and slot["lecta"]["voice"] == "clara"
    assert epistle["cantu"] == {"speaker": "sacerdos", "voice": "clara", "source": "RG 514"}
    assert announcement["cantu"] == {
        "speaker": "sacerdos",
        "voice": "cantus",
        "source": "RG 473, 514; Ritus servandus VI, 5",
    }
    assert answer["unit"] == "responsio-gloria-tibi"
    assert events["evangelium-salutatio"]["occurrences"][0]["unit"] == "salutatio"


def test_the_passion_is_announced_alone_by_the_celebrant():
    doc = library()
    rule = doc["passion"]
    assert rule == {
        "units": [PASSIO],
        "omitted_events": ["evangelium-salutatio"],
        "omitted_units": ["responsio-gloria-tibi"],
        "lecta": {
            "speaker": "sacerdos",
            "voice": "clara",
            "source": "Dominica II Passionis, n. 8 a",
        },
        "cantu": {
            "speaker": "sacerdos",
            "voice": "cantus",
            "source": "Dominica II Passionis, n. 8 a",
        },
        "source": "RG 472; Dominica II Passionis, nn. 8, 8 a",
    }
    bound = [b for b in doc["announcements"] if b["unit"] in rule["units"]]
    assert [b["reading"] for b in bound] == [PASSION]
    parts = {
        s["delivery"]["cantu"]["speaker"]
        for s in store.core(CORPUS, PASSION)["segments"]
        if s["type"] == "verse"
    }
    assert parts == {"chronista", "christus", "synagoga"}
    gospel = next(e for e in doc["events"] if e["id"] == "evangelium-annuntiatio")
    assert [o.get("unit") for o in gospel["occurrences"]] == [None, *rule["omitted_units"]]
    assert (
        "Rubricae generales 472" in doc["rubrics"]["passion"]
        and "(n. 8 a)" in doc["rubrics"]["passion"]
    )


def test_every_sung_announcement_is_delivered_as_its_reading():
    doc = library()
    events = {event["id"]: event for event in doc["events"]}
    sung = {
        "epistola": events["epistola-annuntiatio"]["occurrences"][0]["cantu"]["voice"],
        "evangelium": events["evangelium-annuntiatio"]["occurrences"][0]["cantu"]["voice"],
    }
    assert sung == {"epistola": "clara", "evangelium": "cantus"}
    readings = roles()
    for binding in doc["announcements"]:
        voice = "cantus" if binding["unit"] == PASSIO else sung[readings[binding["reading"]]]
        verses = [
            s for s in store.core(CORPUS, binding["reading"])["segments"] if s["type"] == "verse"
        ]
        assert verses
        for verse in verses:
            assert (verse.get("delivery") or {}).get("cantu", {}).get("voice", verse["voice"]) == (
                voice
            )
    assert checker.SUNG_VOICES == {"announcement": ("cantus", "clara")}


def test_the_leaf_is_the_first_leaf_of_each_readings_printed_witness():
    for binding in library()["announcements"]:
        header = (CORPUS / "witnesses" / binding["reading"] / "mr.txt").read_text(encoding="utf-8")
        location = next(line for line in header.splitlines() if line.startswith("# location:"))
        assert int(re.search(r"n(\d+)", location)[1]) == binding["leaf"]


# ---------------------------------------------------------------------------------------------
# Owned negative controls on a small copy of the corpus
# ---------------------------------------------------------------------------------------------


def binding_of(doc: dict[str, Any], reading: str) -> dict[str, Any]:
    return next(b for b in doc["announcements"] if b["reading"] == reading)


def event_of(doc: dict[str, Any], identity: str) -> dict[str, Any]:
    return next(e for e in doc["events"] if e["id"] == identity)


def unit_of(doc: dict[str, Any], identity: str) -> dict[str, Any]:
    return next(u for u in doc["units"] if u["id"] == identity)


def bind(reading: str, /, **changes: Any) -> Callable[[Any], None]:
    def mutate(doc: Any) -> None:
        binding = binding_of(doc, reading)
        for key, value in changes.items():
            if value is None:
                binding.pop(key)
            else:
                binding[key] = value

    return mutate


def slot(event: str, form: str, **changes: Any) -> Callable[[Any], None]:
    return lambda doc: event_of(doc, event)["occurrences"][0][form].update(changes)


def passion_set(key: str, value: Any) -> Callable[[Any], None]:
    return lambda doc: doc["passion"].__setitem__(key, value)


def verse_delivery(value: Any) -> Callable[[Any], None]:
    def mutate(doc: Any) -> None:
        verse = next(s for s in doc["segments"] if s["type"] == "verse")
        if value is None:
            verse.pop("delivery")
        else:
            verse["delivery"] = value

    return mutate


def swap_events(first: str, second: str) -> Callable[[Any], None]:
    def mutate(doc: Any) -> None:
        events = doc["events"]
        a, b = events.index(event_of(doc, first)), events.index(event_of(doc, second))
        events[a], events[b] = events[b], events[a]

    return mutate


def gospel_reversed(doc: Any) -> None:
    occurrences = event_of(doc, "evangelium-annuntiatio")["occurrences"]
    occurrences.reverse()


EPISTLE = "proprium.dominica-i-adventus-epistola"
GOSPEL = "proprium.dominica-i-adventus-evangelium"
LENT = "proprium.dominica-iii-in-quadragesima-evangelium"
SAINTS = "proprium.omnium-sanctorum-evangelium"
ACTS = "proprium.dominica-pentecostes-epistola"
ROMANS = "lectio-epistolae-beati-pauli-apostoli-ad-romanos"
LUKE = "sequentia-sancti-evangelii-secundum-lucam"
MATTHEW = "sequentia-sancti-evangelii-secundum-matthaeum"
LEAF = "proprium.dominica-i-adventus-epistola"

# (case id, target, mutation, owned diagnostic fragment)
CASES: list[tuple[str, str, Callable[[Any], Any], str]] = [
    (
        "unbound-reading",
        "library",
        lambda d: d["announcements"].remove(binding_of(d, EPISTLE)),
        f"readings without an announcement: {EPISTLE}",
    ),
    (
        "double-binding",
        "library",
        lambda d: d["announcements"].insert(1, copy.deepcopy(d["announcements"][0])),
        "is bound twice",
    ),
    (
        "foreign-reading",
        "library",
        bind(EPISTLE, reading="proprium.dominica-i-adventus-collecta"),
        "no formulary reads it as an Epistle or a Gospel",
    ),
    (
        "lesson-before-the-gospel",
        "library",
        bind(GOSPEL, unit=ROMANS),
        "cannot head the evangelium",
    ),
    ("gospel-before-the-epistle", "library", bind(EPISTLE, unit=LUKE), "cannot head the epistola"),
    (
        "passion-as-sequentia",
        "library",
        bind(PASSION, unit=MATTHEW),
        "a Passion sung in parts takes a passio announcement, and only it",
    ),
    (
        "sequentia-as-passion",
        "library",
        bind("proprium.dominica-i-in-quadragesima-evangelium", unit=PASSIO),
        "a Passion sung in parts takes a passio announcement, and only it",
    ),
    ("unit-not-announcement", "library", bind(EPISTLE, unit="salutatio"), "not an announcement"),
    (
        "foreign-book",
        "library",
        bind(
            EPISTLE, pericope={"book": "1 Cor", "passages": [{"chapter": 13, "verses": [[11, 14]]}]}
        ),
        "does not announce the book '1 Cor'",
    ),
    (
        "print-variant-outside-the-set",
        "library",
        bind(ACTS, as_printed="Léctio Actibus Apostolórum"),
        "only by accent, case or stop",
    ),
    (
        "print-equal-to-the-formula",
        "library",
        bind(EPISTLE, as_printed="Léctio Epístolæ beáti Pauli Apóstoli ad Romános"),
        "only by accent, case or stop",
    ),
    ("leaf-outside-the-witness", "library", bind(EPISTLE, leaf=81), "is not the first leaf"),
    ("missing-page", "library", bind(EPISTLE, page=" "), "leaf and printed page are required"),
    (
        "pericope-leaves-the-print",
        "library",
        bind(
            EPISTLE, pericope={"book": "Rom", "passages": [{"chapter": 13, "verses": [[11, 15]]}]}
        ),
        "must keep the printed chapter and verses",
    ),
    (
        "reversed-verse-range",
        "library",
        bind(
            EPISTLE, pericope={"book": "Rom", "passages": [{"chapter": 13, "verses": [[14, 11]]}]}
        ),
        "a verse range is [first, last] in order",
    ),
    (
        "misprint-without-difference",
        "library",
        bind(EPISTLE, misprint=True, comparator="Divinum Officium"),
        "a misprint is true and differs from its pericope",
    ),
    ("misprint-without-comparator", "library", bind(LENT, comparator=None), "names the comparator"),
    (
        "misprint-unmarked",
        "library",
        bind(LENT, misprint=None, comparator=None),
        "must keep the printed chapter and verses",
    ),
    (
        "comparator-without-misprint",
        "library",
        bind(EPISTLE, comparator="Divinum Officium"),
        "belongs to a misprint",
    ),
    ("supplied-book-unmarked", "library", bind(SAINTS, book_supplied=None), "needs book_supplied"),
    ("supplied-book-printed", "library", bind(EPISTLE, book_supplied=True), "names its book"),
    (
        "unknown-binding-field",
        "library",
        bind(EPISTLE, note="Lesson"),
        "and only the optional",
    ),
    (
        "unsorted-announcements",
        "library",
        lambda d: d["announcements"].reverse(),
        "announcements must be in reading order",
    ),
    (
        "slot-names-a-unit",
        "library",
        lambda d: event_of(d, "epistola-annuntiatio")["occurrences"][0].update(
            {"unit": ROMANS, "slot": None}
        )
        or event_of(d, "epistola-annuntiatio")["occurrences"][0].pop("slot"),
        "an announcement is a slot",
    ),
    (
        "unknown-slot",
        "library",
        lambda d: event_of(d, "evangelium-annuntiatio")["occurrences"][0].update(slot="lectio"),
        "the slot is 'announcement'",
    ),
    (
        "epistle-announcement-sung",
        "library",
        slot("epistola-annuntiatio", "cantu", voice="cantus"),
        "the sung announcement (cantus) must be delivered as its reading (clara)",
    ),
    (
        "gospel-announcement-spoken",
        "library",
        slot("evangelium-annuntiatio", "cantu", voice="clara"),
        "the sung announcement (clara) must be delivered as its reading (cantus)",
    ),
    (
        "clara-under-cantu-for-a-greeting",
        "library",
        lambda d: event_of(d, "collecta-introductio")["occurrences"][0]["cantu"].update(
            voice="clara"
        ),
        "outside the closed vocabulary",
    ),
    (
        "announcement-sung-by-the-schola",
        "library",
        slot("evangelium-annuntiatio", "cantu", speaker="schola"),
        "belongs to the sacerdos",
    ),
    (
        "announcement-read-by-the-server",
        "library",
        slot("epistola-annuntiatio", "lecta", speaker="minister"),
        "belongs to the sacerdos",
    ),
    (
        "gospel-events-reordered",
        "library",
        swap_events("evangelium-salutatio", "evangelium-annuntiatio"),
        "events must be in the order of the Mass",
    ),
    (
        "epistle-event-after-the-gospel",
        "library",
        swap_events("epistola-annuntiatio", "evangelium-annuntiatio"),
        "events must be in the order of the Mass",
    ),
    (
        "gloria-tibi-before-the-announcement",
        "library",
        gospel_reversed,
        "an announcement is a slot",
    ),
    (
        "missing-announcement-event",
        "library",
        lambda d: d["events"].remove(event_of(d, "epistola-annuntiatio")),
        "events missing: epistola-annuntiatio",
    ),
    (
        "passion-keeps-the-greeting",
        "library",
        passion_set("omitted_events", []),
        "omits exactly the events",
    ),
    (
        "passion-keeps-gloria-tibi",
        "library",
        passion_set("omitted_units", []),
        "omits exactly the units",
    ),
    (
        "passion-names-a-sequentia",
        "library",
        passion_set("units", [MATTHEW]),
        "the units must be the passio announcements",
    ),
    (
        "passion-sung-by-the-chronista",
        "library",
        lambda d: d["passion"]["cantu"].update(speaker="chronista"),
        "is not the celebrant's sacerdos/cantus",
    ),
    (
        "passion-without-source",
        "library",
        passion_set("source", ""),
        "passion: source citation is empty",
    ),
    ("passion-missing", "library", lambda d: d.pop("passion"), "needs exactly the fields"),
    (
        "announcement-owner-is-no-heading",
        "library",
        lambda d: unit_of(d, "salutatio").update(role="announcement"),
        "an announcement opens with",
    ),
    (
        "announcement-without-books",
        "library",
        lambda d: unit_of(d, "lectio-libri-iudith").update(id="lectio-libri-iudithae")
        or [
            b.update(unit="lectio-libri-iudithae")
            for b in d["announcements"]
            if b["unit"] == "lectio-libri-iudith"
        ],
        "needs its row in the closed table of books",
    ),
    (
        "epistle-body-sung",
        f"owner:{EPISTLE}",
        verse_delivery({"cantu": {"speaker": "sacerdos", "voice": "cantus"}}),
        "must be delivered as its reading",
    ),
    (
        "gospel-body-spoken",
        f"owner:{GOSPEL}",
        verse_delivery(None),
        "must be delivered as its reading",
    ),
    (
        "announcement-owner-changed",
        "owner:ordinarium.lectio-actuum-apostolorum",
        lambda d: d["segments"][0]["words"][1].update(form="Actibus"),
        "only by accent, case or stop",
    ),
    (
        "announcement-owner-with-participation",
        "owner:ordinarium.lectio-libri-iudith",
        lambda d: d["segments"][0].update(participation={"lecta": {"source": "DMS 31 a"}}),
        "is the celebrant's and its owner carries participation",
    ),
    (
        "announcement-unpublished",
        "manifest:en",
        lambda d: d["texts"].remove("ordinarium.lectio-libri-iudith"),
        "must be published once in the en package",
    ),
    (
        "announcement-untranslated",
        "layer:pl:ordinarium.lectio-isaiae-prophetae",
        lambda d: d["segments"]["s01"].update(translation=" "),
        "pl has no translation of ordinarium.lectio-isaiae-prophetae s01",
    ),
]


def corpus_target(corpus: Path, target: str) -> Path:
    """`owner:` of a reading is its core; every other target as test_introductiones names it."""
    kind, _, rest = target.partition(":")
    if kind == "owner" and rest.startswith("proprium."):
        return store.path_of(corpus, rest)
    return target_path(corpus, target)


@pytest.mark.parametrize(
    "target,mutate,message",
    [case[1:] for case in CASES],
    ids=[case[0] for case in CASES],
)
def test_each_binding_defect_fails_its_owned_diagnostic_and_restores(
    tmp_path, target, mutate, message
):
    corpus = small_corpus(tmp_path)
    assert checker.check(corpus) == ([], COUNTS)
    path = corpus_target(corpus, target)
    healthy = path.read_bytes()
    edit(path, mutate)
    assert path.read_bytes() != healthy
    errors, _counts = checker.check(corpus)
    assert any(message in error for error in errors), errors
    assert all(error.startswith("introductiones: ") for error in errors)
    with pytest.raises(ValueError, match="invalid authored library"):
        checker.authored(corpus)
    path.write_bytes(healthy)
    assert checker.check(corpus) == ([], COUNTS)


TEXT_CASES: dict[str, tuple[str, Callable[[str], str], str]] = {
    "witness-leaf-moved": (
        f"witnesses/{LEAF}/mr.txt",
        lambda text: text.replace("leaves n80", "leaves n79", 1),
        "is not the first leaf of its printed witness",
    ),
    "witness-missing-location": (
        f"witnesses/{LEAF}/mr.txt",
        lambda text: text.replace("# location:", "# place:", 1),
        "is not the first leaf of its printed witness",
    ),
    "reading-both-roles": (
        "formularies/temporale/dominica-i-adventus.json",
        lambda text: text.replace(
            '"role": "evangelium",\n      "text": "proprium.dominica-i-adventus-evangelium"',
            '"role": "evangelium",\n      "text": "proprium.dominica-i-adventus-epistola"',
            1,
        ),
        "is both an Epistle and a Gospel",
    ),
}


@pytest.mark.parametrize("name", list(TEXT_CASES))
def test_each_witness_or_formulary_defect_fails_its_owned_diagnostic_and_restores(tmp_path, name):
    relative, change, message = TEXT_CASES[name]
    corpus = small_corpus(tmp_path)
    assert checker.check(corpus) == ([], COUNTS)
    path = corpus / relative
    healthy = path.read_text(encoding="utf-8")
    damaged = change(healthy)
    assert damaged != healthy
    path.write_text(damaged, encoding="utf-8")
    errors, _counts = checker.check(corpus)
    assert any(message in error for error in errors), errors
    path.write_text(healthy, encoding="utf-8")
    assert checker.check(corpus) == ([], COUNTS)


# ---------------------------------------------------------------------------------------------
# The reader resource
# ---------------------------------------------------------------------------------------------


def test_the_resource_reads_back_every_binding_and_the_passion_rule():
    table = reader.resource(CORPUS)
    assert table == reader.expected(CORPUS)
    assert table["schema_version"] == "2.0.0"
    assert table["passion"] == library()["passion"]
    rows = {row["reading"]: row for row in table["announcements"]}
    assert len(rows) == 205
    for binding in restated():
        row = rows[binding["reading"].replace(".", "/", 1)]
        expected = {
            "reading": binding["reading"].replace(".", "/", 1),
            "unit": binding["unit"],
            "reference": binding["reference_as_printed"],
            "pericope": binding["pericope"],
            **{
                flag: True
                for flag in ("book_supplied", "misprint")
                if flag in binding and (flag != "misprint" or "uncertain" not in binding)
            },
            **({"reference_uncertain": True} if "uncertain" in binding else {}),
        }
        assert row == expected
    assert [event["id"] for event in table["events"]] == list(reader.EVENT_ORDER)
    text = reader.artifact_json(table)
    for leftover in ('"as_printed"', '"leaf"', '"page"', '"comparator"', '"uncertain"'):
        assert leftover not in text


RESOURCE_FAULTS: dict[str, Callable[[Any], None]] = {
    "dotted-reading": lambda t: t["announcements"][0].update(
        reading=t["announcements"][0]["reading"].replace("/", ".")
    ),
    "repeated-reading": lambda t: t["announcements"].insert(1, t["announcements"][0]),
    "unsorted-readings": lambda t: t["announcements"].reverse(),
    "unit-not-announcement": lambda t: t["announcements"][0].update(unit="salutatio"),
    "false-flag": lambda t: t["announcements"][0].update(misprint=False),
    "leaf-carried": lambda t: t["announcements"][0].update(leaf=576),
    "no-reference": lambda t: t["announcements"][0].update(reference=" "),
    "empty-pericope": lambda t: t["announcements"][0]["pericope"].update(passages=[]),
    "no-announcements": lambda t: t.update(announcements=[]),
    "unknown-slot": lambda t: t["events"][1]["occurrences"][0].update(slot="lectio"),
    "slot-sung-by-all": lambda t: t["events"][1]["occurrences"][0]["cantu"].update(speaker="omnes"),
    "greeting-clara-under-cantu": lambda t: t["events"][0]["occurrences"][0]["cantu"].update(
        voice="clara"
    ),
    "announcement-unit-in-an-event": lambda t: t["events"][1]["occurrences"].__setitem__(
        0,
        {
            **{k: v for k, v in t["events"][1]["occurrences"][0].items() if k != "slot"},
            "unit": ROMANS,
        },
    ),
    "events-reordered": lambda t: t["events"].__setitem__(
        slice(2, 4), list(reversed(t["events"][2:4]))
    ),
    "passion-keeps-the-greeting": lambda t: t["passion"].update(omitted_events=[]),
    "passion-names-no-announcement": lambda t: t["passion"].update(units=["salutatio"]),
    "passion-clara-under-cantu": lambda t: t["passion"]["cantu"].update(voice="clara"),
    "no-passion": lambda t: t.pop("passion"),
}


@pytest.mark.parametrize("fault", list(RESOURCE_FAULTS))
def test_the_emitted_contract_rejects_each_malformed_announcement_resource(fault):
    table = reader.resource(CORPUS)
    broken = copy.deepcopy(table)
    RESOURCE_FAULTS[fault](broken)
    assert broken != table
    with pytest.raises(ValueError, match="introductiones: "):
        reader.validate(broken)
    reader.validate(table)
