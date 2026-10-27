"""Finite dismissal choices for the edition's canonical date/Mass pairs."""

from __future__ import annotations

import copy
import json
import re
from datetime import date
from pathlib import Path

from kalendarium.computus import easter
from kalendarium.roman import year

SCHEMA = "1.0.0"
ROLE = "ite-missa-est"
PROFILES = [
    {"id": "ordinary", "text": "ordinarium.ite-missa-est"},
    {"id": "paschale", "text": "ordinarium.ite-missa-est-paschale"},
]
YEARS = range(2026, 2102)
IDENTITY = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")


def canonical_inputs(corpus: Path) -> tuple[list[dict], dict]:
    """Reconstruct each run from authored catalogue and the existing generator."""
    from build_reader import store
    from checks.formularies import check

    problems, _ = check(corpus)
    if problems:
        raise ValueError("dismissal: invalid authored catalogue: " + "; ".join(problems))
    forms = []
    for authored in sorted(store.formularies(corpus), key=lambda value: value["order"]):
        form = {k: copy.deepcopy(v) for k, v in authored.items() if k != "formulary_schema"}
        for component in form["components"]:
            component["text"] = component["text"].replace(".", "/", 1)
        form.setdefault("ordinary_omissions", [])
        for omission in form["ordinary_omissions"]:
            omission["text"] = omission["text"].replace(".", "/", 1)
        forms.append(form)
    keys: list[str] = []
    seasons: list[str] = []
    years: dict[str, list] = {}

    def index(values, value):
        if value not in values:
            values.append(value)
        return values.index(value)

    for ending in YEARS:
        years[str(ending)] = [
            [
                d.when.isoformat(),
                index(keys, d.formulary),
                index(seasons, d.season),
                d.dies_class,
                index(keys, d.position),
            ]
            for d in year(ending)
        ]
    return forms, {"formularies": keys, "seasons": seasons, "years": years}


def _identities(forms: list[dict]) -> list[str]:
    if not isinstance(forms, list) or not forms:
        raise ValueError("dismissal: nonempty canonical Mass catalogue required")
    masses = []
    for form in forms:
        if not isinstance(form, dict):
            raise ValueError("dismissal: Mass must be an object")
        mass = form.get("id")
        if (
            not isinstance(mass, str)
            or not IDENTITY.fullmatch(mass)
            or mass == "none"
            or mass in masses
        ):
            raise ValueError("dismissal: invalid, empty or duplicate Mass identity")
        calendar = form.get("calendar")
        if (
            not isinstance(calendar, dict)
            or not isinstance(calendar.get("key"), str)
            or not calendar["key"]
        ):
            raise ValueError("dismissal: canonical calendar identity required")
        if form.get("collection") not in {"temporale", "sanctorale"}:
            raise ValueError("dismissal: unsupported Mass collection")
        masses.append(mass)
    return sorted(masses)


def calendar_table(forms: list[dict], calendar: dict, *, corpus: Path) -> dict:
    masses = _identities(forms)
    actual_forms, actual_calendar = canonical_inputs(corpus)

    # Equality is the validity boundary, including all row fields and dates.
    # No caller's forged date/key pair may acquire validity by being well typed.
    def canonical(value):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    if canonical(forms) != canonical(actual_forms) or canonical(calendar) != canonical(
        actual_calendar
    ):
        raise ValueError("dismissal: inputs differ from canonical authored catalogue/calendar")
    pairs = []
    by_key: dict[str, list[dict]] = {}
    for form in forms:
        by_key.setdefault(form["calendar"]["key"], []).append(form)
    for rows in calendar["years"].values():
        for row in rows:
            day = date.fromisoformat(row[0])
            for form in by_key.get(calendar["formularies"][row[1]], []):
                offset = (day - easter(day.year)).days
                paschal = (offset == -1 and form["id"] == "vigilia-paschalis") or (
                    0 <= offset <= 6 and form["collection"] == "temporale"
                )
                pairs.append([row[0], masses.index(form["id"]), int(paschal)])
    table = {
        "schema_version": SCHEMA,
        "role": ROLE,
        "profiles": copy.deepcopy(PROFILES),
        "masses": masses,
        "pairs": sorted(pairs),
    }
    validate(table)
    return table


def validate(table: dict) -> None:
    if not isinstance(table, dict) or set(table) != {
        "schema_version",
        "role",
        "profiles",
        "masses",
        "pairs",
    }:
        raise ValueError("dismissal: exact resource fields required")
    if table["schema_version"] != SCHEMA or table["role"] != ROLE or table["profiles"] != PROFILES:
        raise ValueError("dismissal: unsupported version, role or body profiles")
    masses, pairs = table["masses"], table["pairs"]
    if (
        not isinstance(masses, list)
        or not masses
        or any(not isinstance(m, str) or not IDENTITY.fullmatch(m) or m == "none" for m in masses)
    ):
        raise ValueError("dismissal: nonempty typed Mass identities required")
    if masses != sorted(set(masses)):
        raise ValueError("dismissal: unique ordered Mass identities required")
    if not isinstance(pairs, list) or not pairs:
        raise ValueError("dismissal: nonempty pairs required")
    seen = set()
    for row in pairs:
        if not isinstance(row, list) or len(row) != 3:
            raise ValueError("dismissal: exact three-field row required")
        day, mass, profile = row
        try:
            valid_day = isinstance(day, str) and date.fromisoformat(day).isoformat() == day
        except ValueError:
            valid_day = False
        if (
            not valid_day
            or type(mass) is not int
            or not 0 <= mass < len(masses)
            or type(profile) is not int
            or not 0 <= profile < len(PROFILES)
        ):
            raise ValueError("dismissal: invalid canonical date or nonnegative integer index")
        pair = (day, mass)
        if pair in seen:
            raise ValueError("dismissal: duplicate date/Mass pair")
        seen.add(pair)
    if pairs != sorted(pairs):
        raise ValueError("dismissal: ordered pairs required")
