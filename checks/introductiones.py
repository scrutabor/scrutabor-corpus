"""Ordo introductions: the reusable units that open a part of the Mass, and the events of
the priest-led Ordo that are made of them.

The Ritus servandus prints the greeting, its answer and the invitation before the Collect
(V, 1), the Offertory (VII, 1) and the prayers after Communion (XI, 1, in the manner of V, 1),
and the greeting and answer before the Gospel (VI, 2). They are words the reader follows, not
headings. Those words already stand, with stable word ids and their Polish and English layers,
as complete verse segments of other Ordinary texts. A unit addresses one such segment whole,
by its owner text, segment and first and last word in stored order, and never copies a word.

An event is the ordered sequence of units before one Mass part. Every occurrence of a unit in
an event carries its own delivery in both forms of Mass, cited where it is authored: the
Rubricae generales (511 for the low Mass, 513 a and 514 for the celebrant at a sung Mass) and
the Ritus servandus, and De musica sacra 16 b, 25 a and 26 for the answer the schola and the
faithful sing. An occurrence takes nothing from the place where its owner is said: the
invitation addressed in Aufer a nobis is said there at the foot of the altar, and its delivery
before the Collect is authored for the Collect.

The owner's base speaker, voice and participation are read here and held against the unit's
role, never copied into the library. Where the owner itself carries a sung override, as the
Preface dialogue does, the occurrence must agree with it. Which events a given date or Mass
uses (the Easter Vigil, the Passion, the Secret) is not decided here; `rubrics` records those
rules with their citations.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from build_reader import store
from checks.formularies import ROLES as MASS_ROLES
from checks.lint import duplicate_keys

SCHEMA = "1.0.0"
PATH = "ordo/introductiones.json"
KEYS = {"introduction_schema", "units", "events", "rubrics"}
UNIT_KEYS = {"id", "role", "text", "segment", "first", "last", "source"}
EVENT_KEYS = {"id", "before", "source", "occurrences"}
OCCURRENCE_KEYS = {"unit", "lecta", "cantu"}
DELIVERY_KEYS = {"speaker", "voice", "source"}
RUBRIC_KEYS = {"scope", "secret", "passion", "easter-vigil", "prayer-groups"}
IDENTITY = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
TEXT_IDENTITY = re.compile(r"[a-z]+\.[a-z0-9]+(?:-[a-z0-9]+)*\Z")

# The two forms of Mass, and the closed delivery vocabulary of each: the low Mass is said
# aloud by the celebrant and the server, the sung Mass is sung by the celebrant and answered
# by the schola, with the faithful's own part in the owner's participation.
FORMS = ("lecta", "cantu")
VOICES = {"lecta": "clara", "cantu": "cantus"}
SPEAKERS = {"lecta": ("sacerdos", "minister"), "cantu": ("sacerdos", "schola")}

# A role fixes who says the unit in each form and whether its owner carries the faithful's
# participation: the celebrant's greeting and invitation carry none, an answer carries the
# DMS 31 a and 25 a grades that its own words earn wherever they stand.
ROLES: dict[str, tuple[str, str, bool]] = {
    "greeting": ("sacerdos", "sacerdos", False),
    "response": ("minister", "schola", True),
    "invitation": ("sacerdos", "sacerdos", False),
    "gospel-response": ("minister", "schola", True),
}

# The events of the priest-led Ordo: the Mass part each one precedes and the roles of its
# units in order. The Gospel event stops at the answer to the greeting; its announcement is
# not yet a corpus text.
EVENTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "collecta-introductio": ("collecta", ("greeting", "response", "invitation")),
    "evangelium-salutatio": ("evangelium", ("greeting", "response")),
    "offertorium-introductio": ("offertorium", ("greeting", "response", "invitation")),
    "postcommunio-introductio": ("postcommunio", ("greeting", "response", "invitation")),
}
assert all(before in MASS_ROLES for before, _roles in EVENTS.values())


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load(corpus: Path) -> tuple[Any, list[str]]:
    """The authored library, or why it cannot be read. Repeated keys are refused."""
    path = corpus / PATH
    if not path.is_file():
        return None, [f"introductiones: {PATH} is missing"]
    try:
        repeated = duplicate_keys(path)
        doc = _read(path)
    except (OSError, ValueError) as exc:
        return None, [f"introductiones: {PATH} cannot be read: {exc}"]
    if repeated:
        return None, [f"introductiones: {PATH}: {message}" for message in repeated]
    return doc, []


def owner_segment(corpus: Path, unit: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """The owner's stored segment a unit names, or the reason it names none."""
    where = f"introductiones: unit {unit['id']}"
    text, segment_id = unit["text"], unit["segment"]
    if not isinstance(text, str) or not TEXT_IDENTITY.fullmatch(text):
        return None, f"{where}: owner text {text!r} is not a dotted text id"
    path = store.path_of(corpus, text)
    if not path.is_file():
        return None, f"{where}: owner text {text} does not exist"
    owner = _read(path)
    if owner.get("id") != text:
        return None, f"{where}: {path.name} does not carry the id {text}"
    found = [s for s in owner.get("segments") or [] if s.get("id") == segment_id]
    if len(found) != 1:
        return None, f"{where}: {text} has no segment {segment_id!r}"
    segment = found[0]
    if segment.get("type") != "verse" or not segment.get("words"):
        return None, f"{where}: {text} {segment_id} is not a verse with words"
    return segment, ""


def unit_words(corpus: Path, unit: dict[str, Any]) -> list[str]:
    """The word ids a valid unit addresses, in the owner's stored order."""
    segment, problem = owner_segment(corpus, unit)
    if segment is None:
        raise ValueError(problem)
    ids = [word["id"] for word in segment["words"]]
    return ids[ids.index(unit["first"]) : ids.index(unit["last"]) + 1]


def _unit_errors(corpus: Path, unit: dict[str, Any]) -> tuple[list[str], dict[str, Any] | None]:
    """Everything wrong with one unit, and its owner segment when the address resolves."""
    where = f"introductiones: unit {unit['id']}"
    errors: list[str] = []
    role = unit["role"]
    if role not in ROLES:
        errors.append(f"{where}: unknown role {role!r}")
    if not _nonempty(unit["source"]):
        errors.append(f"{where}: source citation is empty")
    segment, problem = owner_segment(corpus, unit)
    if segment is None:
        return [*errors, problem], None
    text, segment_id = unit["text"], unit["segment"]
    ids = [word.get("id") for word in segment["words"]]
    first, last = unit["first"], unit["last"]
    if first not in ids or last not in ids:
        return [*errors, f"{where}: {first!r}-{last!r} names a word outside {segment_id}"], None
    if ids.index(first) > ids.index(last):
        return [*errors, f"{where}: {first}-{last} is reversed in stored order"], None
    if (first, last) != (ids[0], ids[-1]):
        errors.append(
            f"{where}: a unit is a whole segment, and {segment_id} runs {ids[0]}-{ids[-1]}"
        )
    if role in ROLES:
        speaker, _performer, answered = ROLES[role]
        base = (segment.get("speaker"), segment.get("voice"))
        if base != (speaker, VOICES["lecta"]):
            errors.append(
                f"{where}: the owner's base {base[0]}/{base[1]} is not the {role}'s "
                f"{speaker}/{VOICES['lecta']}"
            )
        participation = segment.get("participation") or {}
        if answered and not all(participation.get(form) for form in FORMS):
            errors.append(f"{where}: a {role} needs its owner's participation in both forms")
        if not answered and participation:
            errors.append(
                f"{where}: a {role} is the celebrant's and its owner carries participation"
            )
    members = set(ids)
    for language in store.language_ids(corpus):
        manifest = _read(corpus / "languages" / language / "manifest.json")
        if (manifest.get("texts") or []).count(text) != 1:
            errors.append(f"{where}: {text} must be published once in the {language} package")
            continue
        try:
            layer = _read(store.layer_path(corpus, language, text))
        except (OSError, ValueError):
            errors.append(f"{where}: the {language} layer of {text} cannot be read")
            continue
        if layer.get("text") != text or layer.get("language") != language:
            errors.append(f"{where}: the {language} layer of {text} names another text")
            continue
        localized = layer.get("segments") or {}
        if not _nonempty((localized.get(segment_id) or {}).get("translation")):
            errors.append(f"{where}: {language} has no translation of {text} {segment_id}")
        for stored_under, entry in localized.items():
            for group in (entry or {}).get("alignments") or []:
                grouped = set(group.get("words") or [])
                if grouped & members and (stored_under != segment_id or not grouped <= members):
                    errors.append(
                        f"{where}: a {language} alignment group crosses the boundary of "
                        f"{segment_id}"
                    )
    return errors, segment


def _units(corpus: Path, units: Any) -> tuple[dict[str, dict[str, Any]], list[str]]:
    if not isinstance(units, list) or not units:
        return {}, ["introductiones: units must be a nonempty list"]
    errors: list[str] = []
    identities: list[str] = []
    resolved: dict[str, dict[str, Any]] = {}
    for position, unit in enumerate(units):
        if not isinstance(unit, dict) or set(unit) != UNIT_KEYS:
            errors.append(
                f"introductiones: units[{position}] needs exactly the fields {sorted(UNIT_KEYS)}"
            )
            continue
        identity = unit["id"]
        if not isinstance(identity, str) or not IDENTITY.fullmatch(identity):
            errors.append(f"introductiones: units[{position}] has an invalid id {identity!r}")
            continue
        if identity in identities:
            errors.append(f"introductiones: duplicate unit {identity}")
            continue
        identities.append(identity)
        problems, segment = _unit_errors(corpus, unit)
        errors += problems
        if segment is not None and unit["role"] in ROLES:
            resolved[identity] = {"role": unit["role"], "text": unit["text"], "owner": segment}
    if identities != sorted(identities):
        errors.append("introductiones: units must be in identity order")
    return resolved, errors


def _occurrence_errors(
    where: str, occurrence: dict[str, Any], role: str, unit: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    if unit["role"] != role:
        errors.append(f"{where}: a {role} stands here, not the {unit['role']} {occurrence['unit']}")
    performers = dict(zip(FORMS, ROLES[role][:2], strict=True))
    for form in FORMS:
        delivery = occurrence[form]
        if not isinstance(delivery, dict) or set(delivery) != DELIVERY_KEYS:
            errors.append(f"{where}: {form} delivery needs exactly {sorted(DELIVERY_KEYS)}")
            continue
        speaker, voice = delivery["speaker"], delivery["voice"]
        if speaker not in SPEAKERS[form] or voice != VOICES[form]:
            errors.append(
                f"{where}: {form} delivery {speaker!r}/{voice!r} is outside the closed vocabulary"
            )
            continue
        if speaker != performers[form]:
            errors.append(
                f"{where}: in the {form} form the {role} belongs to the {performers[form]}, "
                f"not the {speaker}"
            )
        if not _nonempty(delivery["source"]):
            errors.append(f"{where}: {form} delivery has no source citation")
    inherited = (unit["owner"].get("delivery") or {}).get("cantu")
    sung = occurrence["cantu"]
    if (
        inherited
        and isinstance(sung, dict)
        and {"speaker": sung.get("speaker"), "voice": sung.get("voice")} != inherited
    ):
        errors.append(
            f"{where}: the sung delivery differs from the owner's own override {inherited}"
        )
    return errors


def _events(events: Any, units: dict[str, dict[str, Any]]) -> tuple[int, int, list[str]]:
    if not isinstance(events, list) or not events:
        return 0, 0, ["introductiones: events must be a nonempty list"]
    errors: list[str] = []
    identities: list[str] = []
    occurrences = 0
    for position, event in enumerate(events):
        if not isinstance(event, dict) or set(event) != EVENT_KEYS:
            errors.append(
                f"introductiones: events[{position}] needs exactly the fields {sorted(EVENT_KEYS)}"
            )
            continue
        identity = event["id"]
        if not isinstance(identity, str) or identity not in EVENTS:
            errors.append(f"introductiones: events[{position}] is an unknown event {identity!r}")
            continue
        if identity in identities:
            errors.append(f"introductiones: duplicate event {identity}")
            continue
        identities.append(identity)
        where = f"introductiones: event {identity}"
        before, roles = EVENTS[identity]
        if event["before"] != before:
            errors.append(f"{where}: it precedes the {before}, not {event['before']!r}")
        if not _nonempty(event["source"]):
            errors.append(f"{where}: source citation is empty")
        sequence = event["occurrences"]
        if not isinstance(sequence, list) or len(sequence) != len(roles):
            errors.append(f"{where}: needs exactly the ordered roles {', '.join(roles)}")
            continue
        for index, (occurrence, role) in enumerate(zip(sequence, roles, strict=True)):
            here = f"{where} occurrence {index}"
            if not isinstance(occurrence, dict) or set(occurrence) != OCCURRENCE_KEYS:
                errors.append(f"{here}: needs exactly the fields {sorted(OCCURRENCE_KEYS)}")
                continue
            unit = units.get(occurrence["unit"]) if isinstance(occurrence["unit"], str) else None
            if unit is None:
                errors.append(f"{here}: names no valid unit ({occurrence['unit']!r})")
                continue
            errors += _occurrence_errors(here, occurrence, role, unit)
            occurrences += 1
    missing = sorted(set(EVENTS) - set(identities))
    if missing:
        errors.append(f"introductiones: events missing: {', '.join(missing)}")
    if identities != sorted(identities):
        errors.append("introductiones: events must be in identity order")
    return len(identities), occurrences, errors


def check(corpus: Path) -> tuple[list[str], dict[str, int]]:
    """Return errors and non-vacuous denominators for the Ordo introduction library."""
    counts = {"units": 0, "events": 0, "occurrences": 0, "owner_texts": 0}
    doc, errors = load(corpus)
    if errors:
        return errors, counts
    if not isinstance(doc, dict) or set(doc) != KEYS:
        return [f"introductiones: {PATH} needs exactly the fields {sorted(KEYS)}"], counts
    if doc["introduction_schema"] != SCHEMA:
        errors.append(f"introductiones: introduction_schema must be {SCHEMA}")
    units, unit_errors = _units(corpus, doc["units"])
    events, occurrences, event_errors = _events(doc["events"], units)
    errors += unit_errors + event_errors
    rubrics = doc["rubrics"]
    if not isinstance(rubrics, dict) or set(rubrics) != RUBRIC_KEYS:
        errors.append(f"introductiones: rubrics need exactly {sorted(RUBRIC_KEYS)}")
    elif not all(_nonempty(value) for value in rubrics.values()):
        errors.append("introductiones: every rubric must be a nonempty citation")
    counts = {
        "units": len(units),
        "events": events,
        "occurrences": occurrences,
        "owner_texts": len({unit["text"] for unit in units.values()}),
    }
    return errors, counts


def authored(corpus: Path) -> dict[str, Any]:
    """The validated authored library; an invalid one is refused, never projected."""
    problems, _counts = check(corpus)
    if problems:
        raise ValueError("introductiones: invalid authored library: " + "; ".join(problems))
    doc, _errors = load(corpus)
    return doc
