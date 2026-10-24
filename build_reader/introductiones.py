"""introductiones.json: the Ordo introduction units and events, and their independent check.

The resource carries addresses and delivery, never words: each unit names its owner text by
its reader address, the segment and the owner's word ids in stored order, and each event, in
the order of the Mass, the ordered occurrences of those units before one Mass part, with the
delivery of each in both forms of Mass. An announcement occurrence is a slot that the reader
fills for each reading from `announcements` (the bound unit, the printed reference and the
pericope); `passion` names the announcements that stand alone, and what they omit. The words,
their glosses and their translations are the owner texts' own, which every package already
carries.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any, NoReturn

from build_reader import store

SCHEMA = "2.0.0"
FIELDS = {"schema_version", "units", "events", "passion", "announcements"}
UNIT_FIELDS = {"id", "role", "text", "segment", "words", "source"}
EVENT_FIELDS = {"id", "before", "source", "occurrences"}
OCCURRENCE_FIELDS = {"unit", "lecta", "cantu"}
SLOT_FIELDS = {"slot", "lecta", "cantu"}
DELIVERY_FIELDS = {"speaker", "voice", "source"}
PASSION_FIELDS = {"units", "omitted_events", "omitted_units", "lecta", "cantu", "source"}
ANNOUNCEMENT_FIELDS = {"reading", "unit", "reference", "pericope"}
ANNOUNCEMENT_FLAGS = {"book_supplied", "misprint", "reference_uncertain"}
ROLES = ("greeting", "response", "invitation", "gospel-response", "announcement")
VOICES = {"lecta": ("clara",), "cantu": ("cantus", "clara")}
SPEAKERS = {"lecta": ("sacerdos", "minister"), "cantu": ("sacerdos", "schola")}
EVENT_ORDER = (
    "collecta-introductio",
    "epistola-annuntiatio",
    "evangelium-salutatio",
    "evangelium-annuntiatio",
    "offertorium-introductio",
    "postcommunio-introductio",
)
IDENTITY = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
ADDRESS = re.compile(r"[a-z]+/[a-z0-9]+(?:-[a-z0-9]+)*\Z")
SEGMENT = re.compile(r"s[0-9]{2,}\Z")
WORD = re.compile(r"w[0-9]{3,}\Z")
NAME = "introductiones.json"
ROLE_PERFORMERS = {
    "greeting": ("sacerdos", "sacerdos"),
    "invitation": ("sacerdos", "sacerdos"),
    "announcement": ("sacerdos", "sacerdos"),
    "response": ("minister", "schola"),
    "gospel-response": ("minister", "schola"),
}
EVENT_CONTRACT = {
    "collecta-introductio": ("collecta", ("greeting", "response", "invitation")),
    "epistola-annuntiatio": ("epistola", ("announcement",)),
    "evangelium-salutatio": ("evangelium", ("greeting", "response")),
    "evangelium-annuntiatio": ("evangelium", ("announcement", "gospel-response")),
    "offertorium-introductio": ("offertorium", ("greeting", "response", "invitation")),
    "postcommunio-introductio": ("postcommunio", ("greeting", "response", "invitation")),
}


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
        "passion": copy.deepcopy(doc["passion"]),
        "announcements": [
            {
                "reading": binding["reading"].replace(".", "/", 1),
                "unit": binding["unit"],
                "reference": binding["reference_as_printed"],
                "pericope": copy.deepcopy(binding["pericope"]),
                **{
                    flag: True
                    for flag in ("book_supplied", "misprint")
                    if binding.get(flag) is True
                    and (flag != "misprint" or "uncertain" not in binding)
                },
                **({"reference_uncertain": True} if "uncertain" in binding else {}),
            }
            for binding in doc["announcements"]
        ],
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

    def delivery_errors(
        owner: str, holder: dict[str, Any], sung: tuple[str, ...], role: str
    ) -> None:
        for form in VOICES:
            delivery = holder[form]
            voices = VOICES[form] if form == "lecta" else sung
            if (
                not isinstance(delivery, dict)
                or set(delivery) != DELIVERY_FIELDS
                or delivery["speaker"] != ROLE_PERFORMERS[role][0 if form == "lecta" else 1]
                or delivery["voice"] not in voices
                or not text(delivery["source"])
            ):
                fail(f"event {owner} {form} delivery differs from the contract")

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
    announcing = {unit["id"] for unit in units if unit["role"] == "announcement"}
    unit_roles = {unit["id"]: unit["role"] for unit in units}
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
        contract = EVENT_CONTRACT.get(event["id"])
        if contract is None:
            fail("unknown event")
        before, roles = contract
        if event["before"] != before or not text(event["source"]):
            fail(f"event {event['id']} needs the part it precedes and a source citation")
        sequence = event["occurrences"]
        if not isinstance(sequence, list) or len(sequence) != len(roles):
            fail(f"event {event['id']} needs its exact ordered roles")
        for role, occurrence in zip(roles, sequence, strict=True):
            sung: tuple[str, ...]
            if isinstance(occurrence, dict) and set(occurrence) == SLOT_FIELDS:
                if role != "announcement" or occurrence["slot"] != "announcement":
                    fail(f"event {event['id']} names an unknown slot")
                sung = ("clara",) if event["id"] == "epistola-annuntiatio" else ("cantus",)
            elif isinstance(occurrence, dict) and set(occurrence) == OCCURRENCE_FIELDS:
                if (
                    role == "announcement"
                    or occurrence["unit"] not in identities
                    or occurrence["unit"] in announcing
                    or unit_roles[occurrence["unit"]] != role
                ):
                    fail(f"event {event['id']} names an unknown unit")
                sung = ("cantus",)
            else:
                fail(f"event {event['id']} occurrence fields differ from the contract")
            delivery_errors(event["id"], occurrence, sung, role)
    if tuple(seen) != EVENT_ORDER:
        fail("events must be the six events in the order of the Mass")
    passion = table["passion"]
    if (
        not isinstance(passion, dict)
        or set(passion) != PASSION_FIELDS
        or not isinstance(passion["units"], list)
        or not passion["units"]
        or passion["units"]
        != sorted(identity for identity in announcing if identity.startswith("passio-"))
        or passion["omitted_events"] != ["evangelium-salutatio"]
        or passion["omitted_units"] != ["responsio-gloria-tibi"]
        or not text(passion["source"])
    ):
        fail("passion differs from the contract")
    delivery_errors("passion", passion, ("cantus",), "announcement")
    rows = table["announcements"]
    if not isinstance(rows, list) or not rows:
        fail("at least one announcement required")
    readings: list[str] = []
    for row in rows:
        if (
            not isinstance(row, dict)
            or not ANNOUNCEMENT_FIELDS <= set(row) <= ANNOUNCEMENT_FIELDS | ANNOUNCEMENT_FLAGS
            or any(row[flag] is not True for flag in ANNOUNCEMENT_FLAGS & set(row))
        ):
            fail("exact announcement fields required")
        if row.get("reference_uncertain") is True and row.get("misprint") is True:
            fail("an uncertain scan reading is not a definite reference misprint")
        if not isinstance(row["reading"], str) or not ADDRESS.fullmatch(row["reading"]):
            fail("an announcement reading must be a slash address")
        if row["reading"] in readings:
            fail(f"{row['reading']} is announced twice")
        readings.append(row["reading"])
        if row["unit"] not in announcing:
            fail(f"{row['reading']} names no announcement unit")
        pericope = row["pericope"]
        if (
            not text(row["reference"])
            or not isinstance(pericope, dict)
            or set(pericope) != {"book", "passages"}
            or not text(pericope["book"])
            or not isinstance(pericope["passages"], list)
            or not pericope["passages"]
            or not all(
                isinstance(passage, dict)
                and set(passage) == {"chapter", "verses"}
                and type(passage["chapter"]) is int
                and passage["chapter"] >= 1
                and isinstance(passage["verses"], list)
                and passage["verses"]
                and all(
                    isinstance(verse, list)
                    and len(verse) == 2
                    and all(type(number) is int for number in verse)
                    and 1 <= verse[0] <= verse[1]
                    for verse in passage["verses"]
                )
                for passage in pericope["passages"]
            )
        ):
            fail(f"{row['reading']} needs its printed reference and a pericope")
    if readings != sorted(readings):
        fail("announcements must be in reading order")


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
                    **(
                        {"slot": occurrence["slot"]}
                        if "slot" in occurrence
                        else {"unit": occurrence["unit"]}
                    ),
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
    rule = authored["passion"]
    passion = {
        "units": list(rule["units"]),
        "omitted_events": list(rule["omitted_events"]),
        "omitted_units": list(rule["omitted_units"]),
        **{
            form: {key: rule[form][key] for key in ("speaker", "voice", "source")}
            for form in ("lecta", "cantu")
        },
        "source": rule["source"],
    }
    announcements: list[dict[str, Any]] = []
    for binding in authored["announcements"]:
        category, name = binding["reading"].split(".", 1)
        row: dict[str, Any] = {
            "reading": f"{category}/{name}",
            "unit": binding["unit"],
            "reference": binding["reference_as_printed"],
            "pericope": {
                "book": binding["pericope"]["book"],
                "passages": [
                    {
                        "chapter": passage["chapter"],
                        "verses": [list(verse) for verse in passage["verses"]],
                    }
                    for passage in binding["pericope"]["passages"]
                ],
            },
        }
        for flag in ("book_supplied", "misprint"):
            if binding.get(flag) is True and (flag != "misprint" or "uncertain" not in binding):
                row[flag] = True
        if "uncertain" in binding:
            row["reference_uncertain"] = True
        announcements.append(row)
    return {
        "schema_version": SCHEMA,
        "units": units,
        "events": events,
        "passion": passion,
        "announcements": announcements,
    }


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
    declared = manifest.get("texts")
    texts = declared if isinstance(declared, list) else []
    for row in want["announcements"]:
        identity = row["reading"].replace("/", ".", 1)
        path = f"texts/{row['reading']}.json"
        matches = [d for d in texts if isinstance(d, dict) and d.get("id") == identity]
        if len(matches) != 1 or matches[0].get("path") != path:
            errors.append(f"introductiones: the announced reading {path} must be declared once")
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
