"""introductiones.json: the Ordo introduction units and events, and their independent check.

The resource carries addresses and delivery, never words: each unit names its owner text by
its reader address, the segment and the owner's word ids in stored order, and each event the
ordered occurrences of those units before one Mass part, with the delivery of each in both
forms of Mass. The words, their glosses and their translations are the owner texts' own, which
every package already carries.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any, NoReturn

from build_reader import store

SCHEMA = "1.0.0"
FIELDS = {"schema_version", "units", "events"}
UNIT_FIELDS = {"id", "role", "text", "segment", "words", "source"}
EVENT_FIELDS = {"id", "before", "source", "occurrences"}
OCCURRENCE_FIELDS = {"unit", "lecta", "cantu"}
DELIVERY_FIELDS = {"speaker", "voice", "source"}
ROLES = ("greeting", "response", "invitation", "gospel-response")
VOICES = {"lecta": "clara", "cantu": "cantus"}
SPEAKERS = {"lecta": ("sacerdos", "minister"), "cantu": ("sacerdos", "schola")}
IDENTITY = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
ADDRESS = re.compile(r"[a-z]+/[a-z0-9]+(?:-[a-z0-9]+)*\Z")
SEGMENT = re.compile(r"s[0-9]{2,}\Z")
WORD = re.compile(r"w[0-9]{3,}\Z")
NAME = "introductiones.json"


def resource(corpus: Path) -> dict[str, Any]:
    """Project the validated authored library onto reader addresses and resolved word ids."""
    from checks.introductiones import authored, unit_words

    doc = authored(corpus)
    table = {
        "schema_version": SCHEMA,
        "units": [
            {
                "id": unit["id"],
                "role": unit["role"],
                "text": unit["text"].replace(".", "/", 1),
                "segment": unit["segment"],
                "words": unit_words(corpus, unit),
                "source": unit["source"],
            }
            for unit in doc["units"]
        ],
        "events": copy.deepcopy(doc["events"]),
    }
    validate(table)
    return table


def artifact_json(table: dict[str, Any]) -> str:
    return json.dumps(table, ensure_ascii=False, indent=1) + "\n"


def validate(table: Any) -> None:
    """The emitted contract: exact fields, closed vocabularies, resolvable references."""

    def fail(message: str) -> NoReturn:
        raise ValueError(f"introductiones: {message}")

    def text(value: Any) -> bool:
        return isinstance(value, str) and bool(value.strip())

    if not isinstance(table, dict) or set(table) != FIELDS:
        fail("exact resource fields required")
    if table["schema_version"] != SCHEMA:
        fail(f"schema_version must be {SCHEMA}")
    units, events = table["units"], table["events"]
    if not isinstance(units, list) or not units:
        fail("at least one unit required")
    identities: list[str] = []
    for unit in units:
        if not isinstance(unit, dict) or set(unit) != UNIT_FIELDS:
            fail("exact unit fields required")
        if (
            not isinstance(unit["id"], str)
            or not IDENTITY.fullmatch(unit["id"])
            or unit["id"] in identities
        ):
            fail("invalid or duplicate unit identity")
        identities.append(unit["id"])
        if unit["role"] not in ROLES:
            fail(f"unit {unit['id']} has an unknown role")
        if not isinstance(unit["text"], str) or not ADDRESS.fullmatch(unit["text"]):
            fail(f"unit {unit['id']} text must be a slash address")
        if not isinstance(unit["segment"], str) or not SEGMENT.fullmatch(unit["segment"]):
            fail(f"unit {unit['id']} names no segment")
        words = unit["words"]
        if (
            not isinstance(words, list)
            or not words
            or len(set(words)) != len(words)
            or not all(isinstance(word, str) and WORD.fullmatch(word) for word in words)
        ):
            fail(f"unit {unit['id']} words must be unique word ids")
        if not text(unit["source"]):
            fail(f"unit {unit['id']} has no source citation")
    if identities != sorted(identities):
        fail("units must be in identity order")
    if not isinstance(events, list) or not events:
        fail("at least one event required")
    seen: list[str] = []
    for event in events:
        if not isinstance(event, dict) or set(event) != EVENT_FIELDS:
            fail("exact event fields required")
        if (
            not isinstance(event["id"], str)
            or not IDENTITY.fullmatch(event["id"])
            or event["id"] in seen
        ):
            fail("invalid or duplicate event identity")
        seen.append(event["id"])
        if not text(event["before"]) or not text(event["source"]):
            fail(f"event {event['id']} needs the part it precedes and a source citation")
        sequence = event["occurrences"]
        if not isinstance(sequence, list) or not sequence:
            fail(f"event {event['id']} has no occurrences")
        for occurrence in sequence:
            if not isinstance(occurrence, dict) or set(occurrence) != OCCURRENCE_FIELDS:
                fail(f"event {event['id']} occurrence fields differ from the contract")
            if occurrence["unit"] not in identities:
                fail(f"event {event['id']} names an unknown unit")
            for form, voice in VOICES.items():
                delivery = occurrence[form]
                if (
                    not isinstance(delivery, dict)
                    or set(delivery) != DELIVERY_FIELDS
                    or delivery["speaker"] not in SPEAKERS[form]
                    or delivery["voice"] != voice
                    or not text(delivery["source"])
                ):
                    fail(f"event {event['id']} {form} delivery differs from the contract")
    if seen != sorted(seen):
        fail("events must be in identity order")


def input_bodies(corpus: Path) -> None:
    """Fail before emission if the authored library or any owner segment is unavailable."""
    from checks.introductiones import check

    problems, _counts = check(corpus)
    if problems:
        raise ValueError("introductiones: invalid authored library: " + "; ".join(problems))


def expected(corpus: Path) -> dict[str, Any]:
    """Restate the resource from the stored files alone, calling neither producer nor checker."""
    authored = json.loads((corpus / "ordo" / NAME).read_text(encoding="utf-8"))
    units = []
    for unit in authored["units"]:
        category, name = unit["text"].split(".", 1)
        owner = json.loads(
            (corpus / "texts" / category / f"{name}.json").read_text(encoding="utf-8")
        )
        (segment,) = [s for s in owner["segments"] if s["id"] == unit["segment"]]
        ids = [word["id"] for word in segment["words"]]
        units.append(
            {
                "id": unit["id"],
                "role": unit["role"],
                "text": f"{category}/{name}",
                "segment": unit["segment"],
                "words": ids[ids.index(unit["first"]) : ids.index(unit["last"]) + 1],
                "source": unit["source"],
            }
        )
    events = [
        {
            "id": event["id"],
            "before": event["before"],
            "source": event["source"],
            "occurrences": [
                {
                    "unit": occurrence["unit"],
                    **{
                        form: {
                            "speaker": occurrence[form]["speaker"],
                            "voice": occurrence[form]["voice"],
                            "source": occurrence[form]["source"],
                        }
                        for form in ("lecta", "cantu")
                    },
                }
                for occurrence in event["occurrences"]
            ],
        }
        for event in authored["events"]
    ]
    return {"schema_version": SCHEMA, "units": units, "events": events}


def verify(corpus: Path, out: Path, manifest: dict, reader_schema: str) -> list[str]:
    """The emitted resource against its restatement, and every owner segment it needs."""
    errors: list[str] = []
    unreadable = object()

    def read(name: str) -> Any:
        try:
            return json.loads((out / name).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(f"introductiones: cannot read {name}: {exc}")
            return unreadable

    base = manifest.get("base")
    if (
        manifest.get("schema_version") != reader_schema
        or not isinstance(base, dict)
        or base.get("introductiones") != NAME
    ):
        errors.append("introductiones: root schema and base.introductiones declaration required")
    table = read(NAME)
    if table is unreadable:
        return errors
    try:
        validate(table)
    except ValueError as exc:
        errors.append(str(exc))
        return errors
    try:
        want = expected(corpus)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"introductiones: the corpus cannot restate the resource: {exc}")
        return errors
    if table != want:
        errors.append("introductiones: resource differs from the independent restatement")

    def bodies(package: Any, prefix: str, language: str | None = None) -> None:
        declarations = package.get("texts") if isinstance(package, dict) else None
        if not isinstance(declarations, list):
            errors.append(f"introductiones: {prefix or 'root '}text declarations missing")
            return
        for unit in want["units"]:
            identity = unit["text"].replace("/", ".", 1)
            path = f"{prefix}texts/{unit['text']}.json"
            matches = [d for d in declarations if isinstance(d, dict) and d.get("id") == identity]
            if len(matches) != 1 or matches[0].get("path") != path:
                errors.append(f"introductiones: {path} must be declared exactly once")
                continue
            body = read(path)
            rows = (
                [r for r in body.get("seg") or [] if isinstance(r, dict)]
                if isinstance(body, dict) and isinstance(body.get("seg"), list)
                else []
            )
            row = [r for r in rows if r.get("id") == unit["segment"]]
            if (
                not isinstance(body, dict)
                or body.get("id") != identity
                or (language is not None and body.get("language") != language)
                or len(row) != 1
            ):
                errors.append(
                    f"introductiones: {path} has the wrong identity or no {unit['segment']}"
                )
                continue
            if language is None:
                cells_value = row[0].get("w")
                cells = cells_value if isinstance(cells_value, list) else []
                if [c.get("i") for c in cells if isinstance(c, dict)] != unit["words"]:
                    errors.append(
                        f"introductiones: {path} {unit['segment']} does not carry the words "
                        f"of {unit['id']}"
                    )
            elif not isinstance(row[0].get("tr"), str) or not row[0]["tr"].strip():
                errors.append(f"introductiones: {path} {unit['segment']} has no translation")

    bodies(manifest, "")
    declarations = manifest.get("languages")
    for language in store.language_ids(corpus):
        name = f"languages/{language}/manifest.json"
        matches = (
            [d for d in declarations if isinstance(d, dict) and d.get("id") == language]
            if isinstance(declarations, list)
            else []
        )
        if len(matches) != 1 or matches[0].get("path") != name:
            errors.append(f"introductiones: {name} must be declared exactly once")
            continue
        package = read(name)
        if (
            not isinstance(package, dict)
            or package.get("language") != language
            or package.get("schema_version") != reader_schema
        ):
            errors.append(f"introductiones: {name} has the wrong package identity or version")
            continue
        bodies(package, f"languages/{language}/", language)
    return errors
