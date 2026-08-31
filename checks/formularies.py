"""Validate canonical Mass-formulary assemblies and their language titles."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from kalendarium.roman import FORMULARIES as CALENDAR_FORMULARIES

SCHEMA = "1.0.0"
COLLECTIONS = ("temporale", "sanctorale", "commune", "votive", "ritual", "local")
SEASONS = (
    "adventus",
    "nativitas",
    "epiphania",
    "septuagesima",
    "quadragesima",
    "passionis",
    "paschale",
    "per-annum",
)
ROLES = (
    "introitus",
    "collecta",
    "epistola",
    "graduale",
    "alleluia",
    "tractus",
    "sequentia",
    "evangelium",
    "offertorium",
    "secreta",
    "praefatio",
    "communio",
    "postcommunio",
)
RELATIONS = ("proper", "shared", "reference")


def _documents(corpus: Path) -> list[tuple[Path, dict]]:
    rows = []
    for path in sorted((corpus / "formularies").glob("*/*.json")):
        rows.append((path, json.loads(path.read_text(encoding="utf-8"))))
    return rows


def _language_documents(corpus: Path, language: str) -> dict[str, tuple[Path, dict]]:
    rows = {}
    for path in sorted((corpus / "languages" / language / "formularies").glob("*/*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        formulary_id = value.get("id")
        if isinstance(formulary_id, str):
            rows[formulary_id] = (path, value)
    return rows


def check(corpus: Path) -> tuple[list[str], dict[str, int]]:
    """Return errors and non-vacuous denominators for the authored catalogue."""
    errors: list[str] = []
    rows = _documents(corpus)
    text_ids = {
        f"{path.parent.name}.{path.stem}" for path in sorted((corpus / "texts").glob("*/*.json"))
    }
    proper_ids = {text_id for text_id in text_ids if text_id.startswith("proprium.")}
    seen_ids: set[str] = set()
    orders: list[int] = []
    used_texts: Counter[str] = Counter()
    calendar_groups: dict[str, list[tuple[str, bool]]] = defaultdict(list)
    observances: dict[str, list[dict]] = defaultdict(list)
    relations: Counter[str] = Counter()

    if not rows:
        errors.append("formularies: no authored documents found")
    for path, doc in rows:
        relative = path.relative_to(corpus)
        formulary_id = doc.get("id")
        expected_id = path.stem
        collection = path.parent.name
        if doc.get("formulary_schema") != SCHEMA:
            errors.append(f"{relative}: formulary_schema must be {SCHEMA}")
        if formulary_id != expected_id:
            errors.append(f"{relative}: id={formulary_id!r}, path says {expected_id!r}")
        if not isinstance(formulary_id, str) or not formulary_id:
            continue
        if formulary_id in seen_ids:
            errors.append(f"{relative}: duplicate formulary id {formulary_id}")
        seen_ids.add(formulary_id)
        order = doc.get("order")
        if not isinstance(order, int) or isinstance(order, bool) or order < 0:
            errors.append(f"{formulary_id}: order must be a non-negative integer")
        else:
            orders.append(order)
        if collection not in COLLECTIONS or doc.get("collection") != collection:
            errors.append(
                f"{formulary_id}: collection={doc.get('collection')!r}, path says {collection!r}"
            )
        if doc.get("season") not in SEASONS:
            errors.append(f"{formulary_id}: unknown season {doc.get('season')!r}")
        if not isinstance(doc.get("title"), str) or not doc["title"].strip():
            errors.append(f"{formulary_id}: Latin title is empty")
        observance = doc.get("observance")
        if not isinstance(observance, str) or not observance:
            errors.append(f"{formulary_id}: observance must be a stable non-empty id")
        else:
            observances[observance].append(doc)
        calendar = doc.get("calendar")
        if not isinstance(calendar, dict):
            errors.append(f"{formulary_id}: calendar must be an object")
        else:
            key = calendar.get("key")
            default = calendar.get("default")
            if not isinstance(key, str) or not key:
                errors.append(f"{formulary_id}: calendar.key must be a stable non-empty id")
            elif not isinstance(default, bool):
                errors.append(f"{formulary_id}: calendar.default must be a boolean")
            else:
                calendar_groups[key].append((formulary_id, default))
        prefix = doc.get("text_prefix", formulary_id)
        if not isinstance(prefix, str) or not prefix:
            errors.append(f"{formulary_id}: text_prefix must be a non-empty string")
            prefix = formulary_id
        components = doc.get("components")
        if not isinstance(components, list) or not components:
            errors.append(f"{formulary_id}: components must be a non-empty array")
            continue
        keys: set[str] = set()
        last_rank = -1
        for index, component in enumerate(components):
            if not isinstance(component, dict):
                errors.append(f"{formulary_id}: component {index} is not an object")
                continue
            key = component.get("key")
            role = component.get("role")
            target = component.get("text")
            relation = component.get("relation")
            if not isinstance(key, str) or not key:
                errors.append(f"{formulary_id}: component {index} has no stable key")
            elif key in keys:
                errors.append(f"{formulary_id}: duplicate component key {key}")
            else:
                keys.add(key)
            if role not in ROLES:
                errors.append(f"{formulary_id}:{key}: unknown role {role!r}")
            else:
                rank = ROLES.index(role)
                if rank <= last_rank:
                    errors.append(f"{formulary_id}:{key}: component order is not liturgical")
                last_rank = rank
                if key != role:
                    errors.append(f"{formulary_id}:{key}: key differs from unique role {role!r}")
            if target not in text_ids:
                errors.append(f"{formulary_id}:{key}: missing text {target!r}")
                continue
            used_texts[target] += 1
            if relation not in RELATIONS:
                errors.append(f"{formulary_id}:{key}: unknown relation {relation!r}")
                continue
            relations[relation] += 1
            expected_proper = f"proprium.{prefix}-{role}"
            if relation == "proper" and target != expected_proper:
                errors.append(
                    f"{formulary_id}:{key}: proper relation must address "
                    f"{expected_proper}, got {target}"
                )
            elif relation == "shared" and target.startswith("proprium."):
                errors.append(f"{formulary_id}:{key}: shared text {target} belongs to proprium")
            elif relation == "reference":
                if not target.startswith("proprium."):
                    errors.append(
                        f"{formulary_id}:{key}: reference {target} must address another proprium"
                    )
                elif target == expected_proper:
                    errors.append(
                        f"{formulary_id}:{key}: own proper {target} is mislabeled reference"
                    )

    if sorted(orders) != list(range(len(rows))):
        errors.append(
            "formularies: order must be the unique contiguous range "
            f"0..{len(rows) - 1}, got {sorted(orders)}"
        )
    for key, calendar_variants in sorted(calendar_groups.items()):
        defaults = [formulary_id for formulary_id, default in calendar_variants if default]
        if key not in CALENDAR_FORMULARIES:
            errors.append(f"formularies: calendar key {key!r} is not computed by the calendar")
        if len(defaults) != 1:
            errors.append(
                f"formularies: calendar key {key!r} has defaults {defaults}, expected one"
            )
    for observance, observance_forms in sorted(observances.items()):
        names = [doc.get("variant") for doc in observance_forms]
        if len(observance_forms) == 1 and names != [None]:
            errors.append(f"{observance}: a single formulary must not invent variant {names[0]!r}")
        if len(observance_forms) > 1:
            if any(not isinstance(name, str) or not name for name in names):
                errors.append(
                    f"{observance}: every member of a multi-Mass observance needs a variant"
                )
            elif len(names) != len(set(names)):
                errors.append(f"{observance}: duplicate variants {names}")

    missing_propers = sorted(proper_ids - set(used_texts))
    if missing_propers:
        errors.append(
            "formularies: proprium texts outside every assembly: " + ", ".join(missing_propers)
        )
    for language in ("pl", "en"):
        localized = _language_documents(corpus, language)
        missing = sorted(seen_ids - set(localized))
        extra = sorted(set(localized) - seen_ids)
        if missing:
            errors.append(f"formularies:{language}: missing titles for {', '.join(missing)}")
        if extra:
            errors.append(f"formularies:{language}: unknown titles for {', '.join(extra)}")
        for formulary_id, (path, doc) in localized.items():
            relative = path.relative_to(corpus)
            if doc.get("formulary_schema") != SCHEMA:
                errors.append(f"{relative}: formulary_schema must be {SCHEMA}")
            if path.stem != formulary_id or doc.get("language") != language:
                errors.append(f"{relative}: id/language does not match its path")
            if not isinstance(doc.get("title"), str) or not doc["title"].strip():
                errors.append(f"{relative}: localized title is empty")

    counts = {
        "formularies": len(rows),
        "observances": len(observances),
        "components": sum(relations.values()),
        "proper_texts": len(proper_ids),
        "proper_uses": sum(used_texts[text_id] for text_id in proper_ids),
        "shared_uses": relations["shared"],
        "reference_uses": relations["reference"],
    }
    return errors, counts
