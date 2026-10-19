"""Finite commemoration occurrences and their activation on the edition's date/Mass pairs.

The authored commemoration owns its occurrence rule (Rubricae generales 80 for the Greater
Litanies: April 25, or the following Tuesday when that day is Easter Sunday or Easter Monday)
and its three ordered slots. Every occurrence in the supported span is published, whether or
not a Mass row is represented on that day; a pair is published only for an actual represented
Mass on an occurrence date, always under the ordinary separate-conclusion profile (RG 436–437).
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

SCHEMA = "1.0.0"
PROFILES = [{"id": "ordinary-separate-conclusions"}]
YEARS = range(2026, 2102)
IDENTITY = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
FIELDS = {"schema_version", "commemorations", "profiles", "masses", "occurrences", "pairs"}
ENTRY_FIELDS = {"id", "title", "rank", "conclusion", "slots"}
SLOT_FIELDS = {"key", "after", "text"}


def occurrence(commemoration: dict, civil_year: int) -> date:
    """The civil date of one commemoration in one year, after its transfer rule."""
    rule = commemoration["occurrence"]
    when = date(civil_year, rule["month"], rule["day"])
    if rule["transfer"] == "easter-sunday-or-monday-to-tuesday":
        pascha = easter(civil_year)
        if when in (pascha, pascha + timedelta(days=1)):
            when = pascha + timedelta(days=2)
    else:  # pragma: no cover — the checker admits only the rules named here
        raise ValueError(f"commemorationes: unknown transfer rule {rule['transfer']!r}")
    return when


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
            for index in range(len(commemorations)):
                if (row[0], index) not in dates:
                    continue
                for form in by_key.get(calendar["formularies"][row[1]], []):
                    pairs.append([row[0], masses.index(form["id"]), index, 0])
    table = {
        "schema_version": SCHEMA,
        "commemorations": entries(commemorations),
        "profiles": copy.deepcopy(PROFILES),
        "masses": masses,
        "occurrences": occurrences,
        "pairs": sorted(pairs),
    }
    validate(table)
    return table


def validate(table: dict) -> None:
    if not isinstance(table, dict) or set(table) != FIELDS:
        raise ValueError("commemorationes: exact resource fields required")
    if table["schema_version"] != SCHEMA or table["profiles"] != PROFILES:
        raise ValueError("commemorationes: schema or profiles differ from the contract")
    commemorations = table["commemorations"]
    if not isinstance(commemorations, list) or not commemorations:
        raise ValueError("commemorationes: at least one commemoration required")
    identities: list[str] = []
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
    if not isinstance(occurrences, list) or occurrences != sorted(occurrences):
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
    pairs = table["pairs"]
    if not isinstance(pairs, list) or pairs != sorted(pairs):
        raise ValueError("commemorationes: pairs must be a sorted list")
    used: set[tuple[str, int, int]] = set()
    for row in pairs:
        if (
            not isinstance(row, list)
            or len(row) != 4
            or any(type(value) is not int for value in row[1:])
            or not 0 <= row[1] < len(masses)
            or not 0 <= row[2] < len(identities)
            or not 0 <= row[3] < len(PROFILES)
        ):
            raise ValueError("commemorationes: pair rows are [date, mass, commemoration, profile]")
        day = civil(row[0])
        if (day, row[2]) not in seen:
            raise ValueError("commemorationes: a pair must fall on a published occurrence")
        triple = (day, row[1], row[2])
        if triple in used:
            raise ValueError("commemorationes: duplicate pair")
        used.add(triple)
