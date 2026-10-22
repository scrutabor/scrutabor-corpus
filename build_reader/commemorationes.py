"""Independent reconstruction and dependency checks for commemorationes.json."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from kalendarium.commemorationes import (
    DECISIONS,
    PROFILES,
    SCHEMA,
    SITUATIONS,
    YEARS,
    authored,
    entries,
    validate,
)
from kalendarium.computus import easter
from kalendarium.dismissal import canonical_inputs
from kalendarium.roman import year

TITLE_SCHEMA = "1.0.0"


def input_bodies(corpus: Path) -> None:
    """Fail before emission if any slot body is unavailable in the neutral core or in PL/EN."""
    from build_reader import store

    for doc in authored(corpus):
        for slot in doc["slots"]:
            identity = slot["text"]
            core = store.core(corpus, identity)
            if core.get("id") != identity or not any(
                s.get("words") for s in core.get("segments", [])
            ):
                raise ValueError(f"commemorationes: {identity} requires a nonempty neutral body")
            for language in ("pl", "en"):
                manifest = json.loads(
                    (corpus / f"languages/{language}/manifest.json").read_text(encoding="utf-8")
                )
                if (
                    not isinstance(manifest.get("texts"), list)
                    or manifest["texts"].count(identity) != 1
                ):
                    raise ValueError(
                        f"commemorationes: {identity} requires a declared {language} body"
                    )
                layer = json.loads(
                    (
                        corpus / f"languages/{language}/texts/{identity.replace('.', '/', 1)}.json"
                    ).read_text(encoding="utf-8")
                )
                if layer.get("text") != identity or layer.get("language") != language:
                    raise ValueError(
                        f"commemorationes: {identity} requires a correctly identified "
                        f"{language} body"
                    )
                for segment in core["segments"]:
                    if segment.get("words"):
                        localized = layer.get("segments", {}).get(segment["id"], {})
                        if (
                            not isinstance(localized.get("translation"), str)
                            or not localized["translation"].strip()
                        ):
                            raise ValueError(
                                f"commemorationes: {identity}/{language}/{segment['id']} "
                                "has no translation"
                            )


def language_catalog(corpus: Path, language: str) -> dict:
    """Localized titles only; the neutral resource carries the assembly data."""
    from checks.commemorationes import language_documents

    titles = []
    for _path, doc in language_documents(corpus, language):
        if doc.get("commemoration_schema") != TITLE_SCHEMA or doc.get("language") != language:
            raise ValueError("invalid localized commemoration title contract")
        titles.append({"id": doc["id"], "title": doc["title"]})
    return {"schema_version": TITLE_SCHEMA, "language": language, "titles": titles}


def expected(corpus: Path) -> dict:
    """No call to the producer: iterate the computed years anew, apply RG 80 again for the
    transferred occurrence, and restate the admission of RG 108–114 from the computed days."""
    forms, _ = canonical_inputs(corpus)
    masses = sorted(form["id"] for form in forms)
    commemorations = authored(corpus)
    names = [decision["id"] for decision in DECISIONS]
    admitted = names.index("admitted")
    not_admitted = names.index("not-admitted")
    unavailable = names.index("omitted-required-de-tempore-unavailable")
    occurrences = []
    for index, doc in enumerate(commemorations):
        rule = doc["occurrence"]
        for civil_year in YEARS:
            when = date(civil_year, rule["month"], rule["day"])
            pascha = easter(civil_year)
            moved = when == pascha or when == pascha + timedelta(days=1)
            if rule["transfer"] != "none" and moved:
                when = pascha + timedelta(days=2)
            occurrences.append([when.isoformat(), index])
    dates = {(day, index) for day, index in occurrences}
    pairs = []
    for ending in YEARS:
        for day in year(ending):
            iso = day.when.isoformat()
            for index, doc in enumerate(commemorations):
                if (iso, index) not in dates:
                    continue
                if doc["rank"] == "privileged":
                    plan = [admitted] * len(SITUATIONS)
                elif day.dies_class == 1 or day.when.isoweekday() == 7:
                    continue
                elif day.when + timedelta(days=1) == easter(day.when.year) + timedelta(days=39):
                    # The eve of Ascension Thursday: its Vigil, absent here, takes the place.
                    plan = [unavailable, unavailable, not_admitted]
                else:
                    plan = [admitted, admitted, not_admitted]
                for form in forms:
                    if form["calendar"]["key"] == day.formulary:
                        pairs.append([iso, masses.index(form["id"]), index, 0, *plan])
    return {
        "schema_version": SCHEMA,
        "commemorations": entries(commemorations),
        "profiles": PROFILES,
        "situations": SITUATIONS,
        "decisions": DECISIONS,
        "masses": masses,
        "occurrences": sorted(occurrences),
        "pairs": sorted(pairs),
    }


def verify(corpus: Path, out: Path, manifest: dict, reader_schema: str) -> list[str]:
    errors: list[str] = []

    def read(name):
        try:
            return json.loads((out / name).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(f"commemorationes: cannot read {name}: {exc}")
            return None

    base = manifest.get("base")
    if (
        manifest.get("schema_version") != reader_schema
        or not isinstance(base, dict)
        or base.get("commemorationes") != "commemorationes.json"
    ):
        errors.append("commemorationes: root schema and base.commemorationes declaration required")
    table = read("commemorationes.json")
    try:
        validate(table)
    except ValueError as exc:
        errors.append(str(exc))
    if table != expected(corpus):
        errors.append("commemorationes: resource differs from independent canonical reconstruction")
    slots = [
        slot["text"].replace("/", ".", 1)
        for entry in (table or {}).get("commemorations") or []
        for slot in entry.get("slots") or []
    ]

    def bodies(package, prefix, language=None):
        if not isinstance(package, dict):
            return
        declarations = package.get("texts")
        if not isinstance(declarations, list):
            errors.append(f"commemorationes: {prefix} text declarations missing")
            return
        for identity in slots:
            path = f"{prefix}texts/{identity.replace('.', '/', 1)}.json"
            matches = [d for d in declarations if isinstance(d, dict) and d.get("id") == identity]
            if len(matches) != 1 or matches[0].get("path") != path:
                errors.append(f"commemorationes: {path} must be declared exactly once")
                continue
            body = read(path)
            if (
                not isinstance(body, dict)
                or body.get("id") != identity
                or not isinstance(body.get("seg"), list)
                or not body["seg"]
                or (language and body.get("language") != language)
            ):
                errors.append(f"commemorationes: {path} has wrong identity/language or empty body")

    bodies(manifest, "")
    for language in ("pl", "en"):
        name = f"languages/{language}/manifest.json"
        declarations = manifest.get("languages")
        matches = (
            [d for d in declarations if isinstance(d, dict) and d.get("id") == language]
            if isinstance(declarations, list)
            else []
        )
        if len(matches) != 1 or matches[0].get("path") != name:
            errors.append(f"commemorationes: {name} must be declared exactly once")
            continue
        package = read(name)
        if (
            not isinstance(package, dict)
            or package.get("language") != language
            or package.get("schema_version") != reader_schema
            or package.get("commemorationes") != f"languages/{language}/commemorationes.json"
        ):
            errors.append(f"commemorationes: {name} has wrong package identity or declaration")
            continue
        titles = read(package["commemorationes"])
        if titles != language_catalog(corpus, language) or {
            t["id"] for t in titles.get("titles", [])
        } != {entry["id"] for entry in (table or {}).get("commemorations") or []}:
            errors.append(f"commemorationes: {package['commemorationes']} differs or is incomplete")
        bodies(package, f"languages/{language}/", language)
    return errors
