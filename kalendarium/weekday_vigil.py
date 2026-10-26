"""The closed Ascension-Vigil dependencies, never a general saints calendar.

nn. 31-33 and n. 91 give the weekday Vigil its identity and rank; nn. 108-109,
n. 111 and nn. 113-114 determine its ordinary commemorations. Missing bindings or
bodies stop the whole resource before emission, not an empty complete plan.
"""

from __future__ import annotations

import json
import re
from datetime import timedelta
from pathlib import Path

VIGIL = "vigilia-ascensionis"
IMPEDED = "impeded-weekday-vigil"
UNDER = "under-weekday-vigil"
IMPEDED_ID = "vigilia-ascensionis-impedita"
VIGIL_SCHEMA = "1.5.0"
FEASTS = ("beata-maria-virgo-regina", "sanctorum-philippi-et-iacobi-apostolorum")
ROLES = ("collecta", "secreta", "postcommunio")
VIGIL_ORATIONS = tuple(f"proprium.dominica-v-post-pascha-{role}" for role in ROLES)
# Exactly the source-identified potential lower routes, including joint groups.
# This is not authority to create full III-class feast Masses or local saints.
LOWER_DATES = (
    (4, 29),
    (4, 30),
    (5, 2),
    (5, 3),
    (5, 4),
    (5, 5),
    (5, 7),
    (5, 9),
    (5, 10),
    (5, 12),
    (5, 13),
    (5, 14),
    (5, 15),
    (5, 16),
    (5, 17),
    (5, 18),
    (5, 19),
    (5, 20),
    (5, 25),
    (5, 26),
    (5, 27),
    (5, 28),
    (5, 29),
    (5, 30),
    (6, 1),
    (6, 2),
)
BINDINGS = "kalendarium/ascension-vigil-orations.json"
TEXT_ID = re.compile(r"proprium\.[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")


def kind(doc: dict) -> str | None:
    return doc["occurrence"].get("kind")


def _body(corpus: Path, identity: str) -> None:
    """All required neutral segments and their declared PL/EN prose must exist."""
    if not isinstance(identity, str) or not TEXT_ID.fullmatch(identity):
        raise ValueError("commemorationes: actual dotted Proper oration bindings required")
    address = identity.replace(".", "/", 1)
    try:
        core = json.loads((corpus / f"texts/{address}.json").read_text(encoding="utf-8"))
        if core.get("id") != identity or not any(s.get("words") for s in core.get("segments", [])):
            raise ValueError("nonempty neutral body required")
        for language in ("pl", "en"):
            manifest = json.loads(
                (corpus / f"languages/{language}/manifest.json").read_text(encoding="utf-8")
            )
            declared = manifest.get("texts")
            if not isinstance(declared, list) or declared.count(identity) != 1:
                raise ValueError(f"declared {language} body required exactly once")
            layer = json.loads(
                (corpus / f"languages/{language}/texts/{address}.json").read_text(encoding="utf-8")
            )
            if layer.get("text") != identity or layer.get("language") != language:
                raise ValueError(f"correctly identified {language} body required")
            for segment in core["segments"]:
                if segment.get("words"):
                    prose = layer.get("segments", {}).get(segment["id"], {}).get("translation")
                    if not isinstance(prose, str) or not prose.strip():
                        raise ValueError(f"{language}/{segment['id']} translation required")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise ValueError(f"commemorationes: required Vigil body {identity}: {exc}") from exc


def require_inputs(corpus: Path, docs: list[dict], forms: list[dict], active: bool) -> bool:
    """A closed authored binding interface; no placeholder IDs or body fallback.

    The separate binding document must name real source-selected bodies
    after their identity/role adjudication; it grants no new review status.
    It is deliberately NOT supplied with invented IDs by this implementation.
    Its absence is a hard dependency failure.
    It binds all26 routes, not merely whichever documents happen to survive.
    """
    active = (
        active
        or any(kind(doc) in (IMPEDED, UNDER) for doc in docs)
        or any(form["id"] == VIGIL for form in forms)
    )
    if not active:
        return False
    selected = [form for form in forms if form["id"] == VIGIL]
    if len(selected) != 1 or selected[0]["calendar"] != {"key": VIGIL, "default": True}:
        raise ValueError("commemorationes: canonical Ascension Vigil formulary required")
    texts = []
    for role, target in zip(ROLES, VIGIL_ORATIONS, strict=True):
        components = [c for c in selected[0]["components"] if c["role"] == role]
        if len(components) != 1 or components[0] != {
            "key": role,
            "role": role,
            "text": target,
            "relation": "reference",
        }:
            raise ValueError(
                f"commemorationes: Ascension Vigil requires its exact {role} reference"
            )
        texts.append(target)
    impeded = [doc for doc in docs if kind(doc) == IMPEDED]
    if len(impeded) != 1 or impeded[0]["id"] != IMPEDED_ID:
        raise ValueError("commemorationes: one authored impeded Ascension Vigil required")
    try:
        binding = json.loads((corpus / BINDINGS).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(
            "commemorationes: complete Ascension Vigil oration bindings required"
        ) from exc
    if (
        not isinstance(binding, dict)
        or set(binding) != {"schema_version", "vigil", "routes"}
        or binding["schema_version"] != "1.0.0"
        or binding["vigil"] != VIGIL
        or not isinstance(binding["routes"], list)
        or len(binding["routes"]) != len(LOWER_DATES)
    ):
        raise ValueError("commemorationes: exact Ascension Vigil binding contract required")
    lower = [doc for doc in docs if kind(doc) == UNDER]
    seen = set()
    for expected, row in zip(LOWER_DATES, binding["routes"], strict=True):
        if (
            not isinstance(row, dict)
            or set(row) != {"month", "day", "commemoration", "orations"}
            or type(row["month"]) is not int
            or type(row["day"]) is not int
            or (row["month"], row["day"]) != expected
            or not isinstance(row["commemoration"], str)
            or row["commemoration"] in seen
            or not isinstance(row["orations"], dict)
            or set(row["orations"]) != set(ROLES)
        ):
            raise ValueError(
                "commemorationes: exact ordered Vigil date/identity/role bindings required"
            )
        seen.add(row["commemoration"])
        matched = [doc for doc in lower if doc["id"] == row["commemoration"]]
        if len(matched) != 1 or matched[0]["occurrence"] != {
            "kind": UNDER,
            "vigil": VIGIL,
            "month": expected[0],
            "day": expected[1],
        }:
            raise ValueError(
                f"commemorationes: Ascension Vigil requires ordinary orations for "
                f"{expected[0]:02d}-{expected[1]:02d}"
            )
        slots = matched[0]["slots"]
        if [slot["key"] for slot in slots] != list(ROLES) or any(
            slot["text"] != row["orations"][slot["key"]] for slot in slots
        ):
            raise ValueError(
                f"commemorationes: {matched[0]['id']} differs from its source-role bindings"
            )
        for role in ROLES:
            target = row["orations"][role]
            if not isinstance(target, str) or not TEXT_ID.fullmatch(target):
                raise ValueError("commemorationes: actual dotted Proper oration bindings required")
            texts.append(target)
    if len(lower) != len(LOWER_DATES) or {doc["id"] for doc in lower} != seen:
        raise ValueError("commemorationes: exactly the26 lower Ascension Vigil routes required")
    for identity in dict.fromkeys(texts):
        _body(corpus, identity)
    return True


def occurrences(doc: dict, ending: int) -> dict[str, str]:
    """Producer-only dates; the independent reader restates the source relation.

    Neither relation can transfer a Vigil or claim an impeded Sunday. Both
    use the actual single +38 Wednesday and the actual winning Roman row.
    """
    from kalendarium.computus import easter
    from kalendarium.roman import year
    from kalendarium.temporale import year as temporal_year

    when = easter(ending) + timedelta(days=38)
    candidates = [day for day in temporal_year(ending) if day.formulary == VIGIL]
    if len(candidates) != 1 or (
        candidates[0].when != when
        or when.weekday() != 2
        or candidates[0].position != VIGIL
        or candidates[0].dies_class != 2
        or candidates[0].season != "paschale"
        or candidates[0].transferred
    ):
        raise ValueError("commemorationes: exact Easter+38 weekday Vigil candidate required")
    kept = [day for day in year(ending) if day.when == when]
    if len(kept) != 1:
        raise ValueError("commemorationes: one Roman winner on the Vigil date required")
    day = kept[0]
    if day.formulary == VIGIL and day != candidates[0]:
        raise ValueError("commemorationes: winning Vigil differs from its exact temporal candidate")
    if kind(doc) == IMPEDED:
        if day.dies_class == 1:
            return {}  # RG33: entirely omitted, not a transferred occurrence.
        if day.formulary in doc["occurrence"]["feasts"] and day.dies_class == 2:
            return {when.isoformat(): VIGIL}
        if day.formulary != VIGIL:
            raise ValueError(
                "commemorationes: impeded weekday Vigil differs from its actual collision"
            )
        return {}
    if kind(doc) == UNDER:
        rule = doc["occurrence"]
        if day.formulary == VIGIL and (when.month, when.day) == (rule["month"], rule["day"]):
            return {when.isoformat(): VIGIL}
        return {}
    raise ValueError("commemorationes: unsupported weekday Vigil relation")
