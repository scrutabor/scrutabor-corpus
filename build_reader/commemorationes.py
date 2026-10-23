"""Independent reconstruction and dependency checks for commemorationes.json."""

from __future__ import annotations

import json
from calendar import isleap
from datetime import date, timedelta
from pathlib import Path

from kalendarium.commemorationes import (
    DECISIONS,
    PROFILES,
    SCHEMA,
    SITUATIONS,
    YEARS,
    authored,
    displaced,
    entries,
    formulary_orations,
    impeded,
    impeded_feasts,
    impeded_sundays,
    sunday_orations,
    validate,
)
from kalendarium.computus import easter
from kalendarium.dismissal import canonical_inputs
from kalendarium.roman import year
from kalendarium.sanctorale import FESTA
from kalendarium.temporale import Dies

TITLE_SCHEMA = "1.0.0"
# RG 18: the resumed Sundays after Epiphany take the places after the Twenty-third Sunday after
# Pentecost so that the one before the last is the Sixth; the last is always the Twenty-fourth.
RESUMED = {3: "iii", 4: "iv", 5: "v", 6: "vi"}
ROLES = ("collecta", "secreta", "postcommunio")
# The sanctoral feasts' printed fixed dates (month, day).
FIXED = {feast.formulary: (feast.month, feast.day) for feast in FESTA}


def slot_bodies(corpus: Path) -> list[str]:
    """Every dotted text a commemoration may say: the addressed slots, and the orations of
    each impeded Sunday and each impeded feast whose formulary is in this edition."""
    from build_reader import store

    forms = {form["id"]: form for form in store.formularies(corpus)}
    found: list[str] = []
    for doc in authored(corpus):
        if displaced(doc):
            for sunday in sorted(set(impeded_sundays(doc).values())):
                texts = sunday_orations(forms.get(sunday)) or []
                found.extend(text.replace("/", ".", 1) for text in texts)
        elif impeded(doc):
            for feast in sorted(set(impeded_feasts(doc).values())):
                texts = formulary_orations(forms.get(feast)) or []
                found.extend(text.replace("/", ".", 1) for text in texts)
        else:
            found.extend(slot["text"] for slot in doc["slots"])
    return list(dict.fromkeys(found))


def input_bodies(corpus: Path) -> None:
    """Fail before emission if any slot body is unavailable in the neutral core or in PL/EN."""
    from build_reader import store

    for identity in slot_bodies(corpus):
        core = store.core(corpus, identity)
        if core.get("id") != identity or not any(s.get("words") for s in core.get("segments", [])):
            raise ValueError(f"commemorationes: {identity} requires a nonempty neutral body")
        for language in ("pl", "en"):
            manifest = json.loads(
                (corpus / f"languages/{language}/manifest.json").read_text(encoding="utf-8")
            )
            if (
                not isinstance(manifest.get("texts"), list)
                or manifest["texts"].count(identity) != 1
            ):
                raise ValueError(f"commemorationes: {identity} requires a declared {language} body")
            layer = json.loads(
                (
                    corpus / f"languages/{language}/texts/{identity.replace('.', '/', 1)}.json"
                ).read_text(encoding="utf-8")
            )
            if layer.get("text") != identity or layer.get("language") != language:
                raise ValueError(
                    f"commemorationes: {identity} requires a correctly identified {language} body"
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


def _printed(feast: str, civil_year: int) -> date:
    """A sanctoral feast's printed fixed date: the calendar gives St Matthias 25 February in a
    leap year."""
    month, day = FIXED[feast]
    if feast == "sancti-matthiae-apostoli" and isleap(civil_year):
        day = 25
    return date(civil_year, month, day)


def _sunday(day: Dies, after: list[date]) -> str:
    """RG 18 restated from the year's own count of Sundays after Pentecost, Trinity first."""
    if day.when not in after:
        return day.position
    place, total = after.index(day.when) + 1, len(after)
    if place == total:
        return "dominica-xxiv-post-pentecosten"
    if place > 23:
        return f"dominica-{RESUMED[6 - (total - 1 - place)]}-quae-superfuit-post-epiphaniam"
    return day.position


def expected(corpus: Path) -> dict:
    """No call to the producer: iterate the computed years anew, apply RG 80 again for the
    transferred occurrence, restate the admission of RG 108–114 from the computed days,
    restate RG 15–18 for the impeded Sunday from the computed positions, and restate RG 16 for
    the impeded feast from the feasts' printed dates and the computed second-class Sundays."""
    forms, _ = canonical_inputs(corpus)
    masses = sorted(form["id"] for form in forms)
    by_id = {form["id"]: form for form in forms}
    commemorations = authored(corpus)
    names = [decision["id"] for decision in DECISIONS]
    admitted = names.index("admitted")
    not_admitted = names.index("not-admitted")
    unavailable = names.index("omitted-required-de-tempore-unavailable")
    occurrences = []
    for index, doc in enumerate(commemorations):
        rule = doc["occurrence"]
        if "kind" in rule:
            continue
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
        days = year(ending)
        after = [
            day.when
            for day in days
            if day.position.startswith("dominica-") and day.position.endswith("-post-pentecosten")
        ]
        for day in days:
            iso = day.when.isoformat()
            for index, doc in enumerate(commemorations):
                rule = doc["occurrence"]
                resolution: str | None = None
                if rule.get("kind") == "impeded-feast":
                    if (
                        day.when.isoweekday() != 7
                        or day.dies_class != 2
                        or not day.formulary.startswith("dominica-")
                    ):
                        continue
                    named = [f for f in rule["feasts"] if _printed(f, day.when.year) == day.when]
                    if not named:
                        continue
                    if len(named) != 1:
                        raise ValueError(f"commemorationes: {iso} falls on more than one feast")
                    occurrences.append([iso, index])
                    resolution = named[0]
                    feast = by_id.get(resolution)
                    if feast is None or not all(
                        any(c["role"] == role for c in feast["components"]) for role in ROLES
                    ):
                        raise ValueError(f"commemorationes: {resolution} is not in this edition")
                    plan = [admitted, admitted, not_admitted]
                elif "kind" in rule:
                    if day.formulary not in rule["feasts"] or day.when.isoweekday() != 7:
                        continue
                    occurrences.append([iso, index])
                    resolution = _sunday(day, after)
                    sunday = by_id.get(resolution)
                    complete = sunday is not None and all(
                        any(c["role"] == role for c in sunday["components"]) for role in ROLES
                    )
                    plan = [admitted if complete else unavailable] * len(SITUATIONS)
                elif (iso, index) not in dates:
                    continue
                elif doc["rank"] == "privileged":
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
                        pairs.append([iso, masses.index(form["id"]), index, 0, *plan, resolution])
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
        if isinstance(slot.get("text"), str)
    ]
    # An admitted impeded Sunday or impeded feast says the orations its formulary assembles:
    # read them from the authored formularies rather than from the emitted catalogue.
    from build_reader import store

    forms = {form["id"]: form for form in store.formularies(corpus)}
    width = 4 + len(SITUATIONS)
    admitted = [decision["id"] for decision in DECISIONS].index("admitted")
    for row in (table or {}).get("pairs") or []:
        if not isinstance(row, list) or len(row) != width + 1 or row[width] is None:
            continue
        if admitted in row[4:width]:
            try:
                texts = formulary_orations(forms.get(row[width]))
            except ValueError as exc:
                texts = None
                errors.append(str(exc))
            if texts is None:
                errors.append(f"commemorationes: {row[0]} admits {row[width]} without its orations")
            else:
                slots.extend(texts)
    slots = list(dict.fromkeys(slots))

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
