"""Finite commemoration occurrences and their decisions on the edition's date/Mass pairs.

The authored commemoration owns its occurrence rule and its three ordered slots: the Greater
Litanies (Rubricae generales 80: April 25, or the following Tuesday when that day is Easter
Sunday or Easter Monday) and St Petronilla (31 May, never transferred). Every occurrence in the
supported span is published, whether or not a Mass row is represented on that day.

A pair is an explicit decision for one represented Mass on an occurrence date, stated for each
of three situations: a low Mass (lecta), a sung conventual Mass and a sung Mass that is not
conventual. Low conventual and non-conventual Masses receive the same decision (RG 108), so the
low situation is stated once. A privileged commemoration is admitted in all three (RG 108–109).
The ordinary commemorations carried here are not themselves second-class feasts, so each is
decided on a second-class weekday only: a first-class day admits no ordinary commemoration and a
second-class Sunday only a second-class feast (RG 111 a–b, 434), and no pair is published for
it there. On that weekday it is admitted in low and sung conventual Masses and not in a sung
Mass that is not conventual (RG 108), unless a de Tempore commemoration takes the single place
(RG 111 c, 113–114). The impeded Vigil of the Ascension is such a day (RG 31–33); its orations
are not yet in this edition, so the decision states that a required de Tempore commemoration is
unavailable and the ordinary one is omitted, rather than presenting the Mass as complete. At
most one commemoration is admitted for a date, Mass and situation: a second would need an
order and a conclusion plan this contract does not model.
No procession, local calendar or Office commemoration is inferred.
"""

from __future__ import annotations

import copy
import json
import re
from datetime import date, timedelta
from pathlib import Path

from kalendarium.computus import easter
from kalendarium.dismissal import canonical_inputs

SCHEMA = "2.0.0"
PROFILES = [{"id": "ordinary-separate-conclusions"}]
SITUATIONS = ["lecta", "cantu-conventualis", "cantu-non-conventualis"]
DECISIONS = [
    {"id": "admitted"},
    {"id": "not-admitted"},
    {"id": "omitted-required-de-tempore-unavailable"},
]
ADMITTED, NOT_ADMITTED, DE_TEMPORE_UNAVAILABLE = range(len(DECISIONS))
YEARS = range(2026, 2102)
IDENTITY = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
FIELDS = {
    "schema_version",
    "commemorations",
    "profiles",
    "situations",
    "decisions",
    "masses",
    "occurrences",
    "pairs",
}
ENTRY_FIELDS = {"id", "title", "rank", "conclusion", "slots"}
SLOT_FIELDS = {"key", "after", "text"}
RANKS = ("privileged", "ordinary")
# De Tempore days this edition does not yet carry that take the single second-class place on
# the fixed dates an ordinary commemoration may use (checks.commemorationes.ORDINARY_DATES),
# by their distance from Easter Sunday: the Vigil of the Ascension, a second-class vigil
# commemorated when impeded (RG 31–33).
UNAVAILABLE_DE_TEMPORE = {"vigilia-ascensionis": 38}


def occurrence(commemoration: dict, civil_year: int) -> date:
    """The civil date of one commemoration in one year, after its transfer rule."""
    rule = commemoration["occurrence"]
    when = date(civil_year, rule["month"], rule["day"])
    if rule["transfer"] == "easter-sunday-or-monday-to-tuesday":
        pascha = easter(civil_year)
        if when in (pascha, pascha + timedelta(days=1)):
            when = pascha + timedelta(days=2)
    elif rule["transfer"] != "none":  # pragma: no cover — the checker admits only these rules
        raise ValueError(f"commemorationes: unknown transfer rule {rule['transfer']!r}")
    return when


def unavailable_de_tempore(when: date) -> str | None:
    """The de Tempore day absent from this edition that falls on `when`, if any."""
    pascha = easter(when.year)
    for name, offset in UNAVAILABLE_DE_TEMPORE.items():
        if when == pascha + timedelta(days=offset):
            return name
    return None


def decision(commemoration: dict, when: date, dies_class: int) -> list[int] | None:
    """The decision in each situation for a represented Mass on an occurrence date.

    None means the day admits no such commemoration and no pair is published for it.
    """
    from checks.commemorationes import ORDINARY_DATES

    if commemoration["rank"] == "privileged":
        return [ADMITTED, ADMITTED, ADMITTED]
    if commemoration["rank"] != "ordinary" or (when.month, when.day) not in ORDINARY_DATES:
        raise ValueError(f"commemorationes: {commemoration['id']} is outside the modeled scope")
    if dies_class != 2 or when.weekday() == 6:
        return None
    if unavailable_de_tempore(when) is not None:
        return [DE_TEMPORE_UNAVAILABLE, DE_TEMPORE_UNAVAILABLE, NOT_ADMITTED]
    return [ADMITTED, ADMITTED, NOT_ADMITTED]


def authored(corpus: Path) -> list[dict]:
    """The validated authored commemorations in identity order."""
    from checks.commemorationes import check, documents

    problems, _ = check(corpus)
    if problems:
        raise ValueError("commemorationes: invalid authored documents: " + "; ".join(problems))
    return sorted((doc for _path, doc in documents(corpus)), key=lambda doc: doc["id"])


def _masses(forms: list[dict]) -> list[str]:
    masses = []
    for form in forms:
        mass = form.get("id") if isinstance(form, dict) else None
        if (
            not isinstance(mass, str)
            or not IDENTITY.fullmatch(mass)
            or mass == "none"
            or mass in masses
        ):
            raise ValueError("commemorationes: invalid, empty or duplicate Mass identity")
        masses.append(mass)
    return sorted(masses)


def entries(commemorations: list[dict]) -> list[dict]:
    return [
        {
            "id": doc["id"],
            "title": doc["title"],
            "rank": doc["rank"],
            "conclusion": doc["conclusion"],
            "slots": [
                {
                    "key": slot["key"],
                    "after": slot["after"],
                    "text": slot["text"].replace(".", "/", 1),
                }
                for slot in doc["slots"]
            ],
        }
        for doc in commemorations
    ]


def calendar_table(forms: list[dict], calendar: dict, *, corpus: Path) -> dict:
    masses = _masses(forms)
    actual_forms, actual_calendar = canonical_inputs(corpus)

    def canonical(value):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    if canonical(forms) != canonical(actual_forms) or canonical(calendar) != canonical(
        actual_calendar
    ):
        raise ValueError(
            "commemorationes: inputs differ from canonical authored catalogue/calendar"
        )
    commemorations = authored(corpus)
    occurrences = sorted(
        [occurrence(doc, civil_year).isoformat(), index]
        for index, doc in enumerate(commemorations)
        for civil_year in YEARS
    )
    dates = {(day, index) for day, index in occurrences}
    by_key: dict[str, list[dict]] = {}
    for form in forms:
        by_key.setdefault(form["calendar"]["key"], []).append(form)
    pairs = []
    for rows in calendar["years"].values():
        for row in rows:
            for index, doc in enumerate(commemorations):
                if (row[0], index) not in dates:
                    continue
                plan = decision(doc, date.fromisoformat(row[0]), row[3])
                if plan is None:
                    continue
                for form in by_key.get(calendar["formularies"][row[1]], []):
                    pairs.append([row[0], masses.index(form["id"]), index, 0, *plan])
    table = {
        "schema_version": SCHEMA,
        "commemorations": entries(commemorations),
        "profiles": copy.deepcopy(PROFILES),
        "situations": list(SITUATIONS),
        "decisions": copy.deepcopy(DECISIONS),
        "masses": masses,
        "occurrences": occurrences,
        "pairs": sorted(pairs),
    }
    validate(table)
    return table


def validate(table: dict) -> None:
    if not isinstance(table, dict) or set(table) != FIELDS:
        raise ValueError("commemorationes: exact resource fields required")
    if (
        table["schema_version"] != SCHEMA
        or table["profiles"] != PROFILES
        or table["situations"] != SITUATIONS
        or table["decisions"] != DECISIONS
    ):
        raise ValueError(
            "commemorationes: schema, profiles, situations or decisions differ from the contract"
        )
    commemorations = table["commemorations"]
    if not isinstance(commemorations, list) or not commemorations:
        raise ValueError("commemorationes: at least one commemoration required")
    identities: list[str] = []
    ranks: list[str] = []
    for entry in commemorations:
        if not isinstance(entry, dict) or set(entry) != ENTRY_FIELDS:
            raise ValueError("commemorationes: exact commemoration entry fields required")
        if (
            not isinstance(entry["id"], str)
            or not IDENTITY.fullmatch(entry["id"])
            or entry["id"] in identities
        ):
            raise ValueError("commemorationes: invalid or duplicate commemoration identity")
        identities.append(entry["id"])
        if entry["rank"] not in RANKS:
            raise ValueError(f"commemorationes: {entry['id']} has an unknown rank")
        ranks.append(entry["rank"])
        if not isinstance(entry["title"], str) or not entry["title"].strip():
            raise ValueError(f"commemorationes: {entry['id']} needs a Latin title")
        slots = entry["slots"]
        if not isinstance(slots, list) or not slots:
            raise ValueError(f"commemorationes: {entry['id']} has no slots")
        for slot in slots:
            if not isinstance(slot, dict) or set(slot) != SLOT_FIELDS:
                raise ValueError(
                    f"commemorationes: {entry['id']} slot fields differ from the contract"
                )
            if not all(isinstance(slot[key], str) and slot[key] for key in SLOT_FIELDS):
                raise ValueError(
                    f"commemorationes: {entry['id']} slot values must be nonempty strings"
                )
            if not re.fullmatch(r"[a-z]+/[a-z0-9-]+", slot["text"]):
                raise ValueError(
                    f"commemorationes: {entry['id']} slot text must be a slash address"
                )
    if identities != sorted(identities):
        raise ValueError("commemorationes: commemorations must be in identity order")
    masses = table["masses"]
    if (
        not isinstance(masses, list)
        or not masses
        or masses != sorted(set(masses))
        or any(not isinstance(m, str) or not IDENTITY.fullmatch(m) or m == "none" for m in masses)
    ):
        raise ValueError("commemorationes: masses must be sorted unique identities")

    def civil(value: object) -> str:
        try:
            if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
                raise ValueError
        except ValueError:
            raise ValueError("commemorationes: canonical civil date required") from None
        return value

    occurrences = table["occurrences"]
    if not isinstance(occurrences, list):
        raise ValueError("commemorationes: occurrences must be a sorted list")
    seen: set[tuple[str, int]] = set()
    for row in occurrences:
        if (
            not isinstance(row, list)
            or len(row) != 2
            or type(row[1]) is not int
            or not 0 <= row[1] < len(identities)
        ):
            raise ValueError("commemorationes: occurrence rows are [date, commemoration]")
        key = (civil(row[0]), row[1])
        if key in seen:
            raise ValueError("commemorationes: duplicate occurrence")
        seen.add(key)
    # Typed rows compare as (date, number, ...) tuples: numeric order, never string order.
    if occurrences != sorted(occurrences):
        raise ValueError("commemorationes: occurrences must be a sorted list")
    pairs = table["pairs"]
    if not isinstance(pairs, list):
        raise ValueError("commemorationes: pairs must be a sorted list")
    used: set[tuple[str, int, int]] = set()
    places: dict[tuple[str, int, int], list[int]] = {}
    for row in pairs:
        if (
            not isinstance(row, list)
            or len(row) != 4 + len(SITUATIONS)
            or any(type(value) is not int for value in row[1:])
            or not 0 <= row[1] < len(masses)
            or not 0 <= row[2] < len(identities)
            or not 0 <= row[3] < len(PROFILES)
            or any(not 0 <= value < len(DECISIONS) for value in row[4:])
        ):
            raise ValueError(
                "commemorationes: pair rows are [date, mass, commemoration, profile, "
                + ", ".join(SITUATIONS)
                + "]"
            )
        day = civil(row[0])
        if (day, row[2]) not in seen:
            raise ValueError("commemorationes: a pair must fall on a published occurrence")
        triple = (day, row[1], row[2])
        if triple in used:
            raise ValueError("commemorationes: duplicate pair")
        used.add(triple)
        plan = row[4:]
        if ranks[row[2]] == "privileged" and plan != [ADMITTED] * len(SITUATIONS):
            raise ValueError("commemorationes: a privileged commemoration is made in all Masses")
        if ranks[row[2]] == "ordinary" and (plan[0] != plan[1] or plan[2] != NOT_ADMITTED):
            raise ValueError(
                "commemorationes: an ordinary commemoration has one decision for low and sung "
                "conventual Masses and is not admitted in a sung Mass that is not conventual"
            )
        for situation, value in enumerate(plan):
            places.setdefault((day, row[1], situation), []).append(value)
    for (day, _mass, situation), values in places.items():
        if values.count(ADMITTED) > 1 or (ADMITTED in values and DE_TEMPORE_UNAVAILABLE in values):
            raise ValueError(
                f"commemorationes: {day} {SITUATIONS[situation]} admits more than the single "
                "commemoration this contract models"
            )
    if pairs != sorted(pairs):
        raise ValueError("commemorationes: pairs must be a sorted list")
