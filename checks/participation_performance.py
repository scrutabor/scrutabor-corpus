"""A participation performance supplements, never replaces, the base actor."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

TEXT = "ordinarium.sanctus"
ROWS = {
    "s02": (1, "Sanctus Sanctus Sanctus Dóminus Deus Sábaoth"),
    "s03": (7, "Pleni sunt cæli et terra glória tua"),
    "s04": (14, "Hosánna in excélsis"),
    "s05": (17, "Benedíctus qui venit in nómine Dómini"),
    "s06": (23, "Hosánna in excélsis"),
}
INVENTORIES = {
    TEXT: ROWS,
    **{
        "ordinarium.agnus-dei": {
            "s02": (1, "Agnus Dei qui tollis peccáta mundi miserére nobis"),
            "s03": (9, "Agnus Dei qui tollis peccáta mundi miserére nobis"),
            "s04": (17, "Agnus Dei qui tollis peccáta mundi dona nobis pacem"),
        },
        "ordinarium.agnus-dei-defunctorum": {
            "s01": (1, "Agnus Dei qui tollis peccáta mundi dona eis réquiem"),
            "s02": (10, "Agnus Dei qui tollis peccáta mundi dona eis réquiem"),
            "s03": (19, "Agnus Dei qui tollis peccáta mundi dona eis réquiem sempitérnam"),
        },
    },
}
TEXTS = frozenset(INVENTORIES)
PERFORMANCE = {"speaker": "schola", "voice": "cantus", "source": "DMS 25 b; 26"}


def source_fields(segment: dict[str, Any]) -> dict[str, Any]:
    """Bind the new ritual claim without changing any legacy source payload."""
    forms = segment.get("participation")
    if not isinstance(forms, dict):
        return {}
    selected = {
        form: {"source": grant.get("source"), "performance": grant["performance"]}
        for form, grant in forms.items()
        if isinstance(grant, dict) and "performance" in grant
    }
    return {"participation_performance": deepcopy(selected)} if selected else {}


def base_errors(doc: dict[str, Any]) -> list[str]:
    """Closed source identity; do not repair an altered base by deriving over it."""
    if doc.get("id") not in TEXTS:
        return []
    rows = INVENTORIES[doc["id"]]
    prefix = [] if doc["id"].endswith("-defunctorum") else ["s01"]
    label = "Sanctus" if doc["id"] == TEXT else "Agnus Dei"
    segments = doc.get("segments", [])
    errors = []
    suffix = ["s05"] if doc["id"] == "ordinarium.agnus-dei" else []
    if [s.get("id") for s in segments] != [*prefix, *rows, *suffix]:
        errors.append(
            "Sanctus performance requires the exact six source rows"
            if doc["id"] == TEXT
            else "Agnus Dei performance requires the exact source rows"
        )
    if prefix and (not segments or segments[0].get("type") != "rubric"):
        errors.append(f"{label} opening must remain a rubric")
    if suffix and segments and segments[-1].get("type") != "rubric":
        errors.append("Agnus Dei closing source instruction must remain a rubric")
    for segment in segments:
        identity = segment.get("id")
        if identity not in rows:
            continue
        first, forms = rows[identity]
        expected = [(f"w{first + offset:03}", form) for offset, form in enumerate(forms.split())]
        actual = [(w.get("id"), w.get("form")) for w in segment.get("words", [])]
        if actual != expected:
            errors.append(f"{identity}: {label} performance source words/IDs differ")
        if (
            segment.get("type") != "verse"
            or segment.get("speaker") != "sacerdos"
            or segment.get("voice") != "clara"
            or ("delivery" in segment and segment["delivery"] != {"cantu": {"voice": "secreto"}})
        ):
            errors.append(f"{identity}: {label} priestly base must remain unchanged")
    return errors


def priestly_delivery(doc: dict[str, Any], segment: dict[str, Any]) -> dict[str, Any]:
    """RG511h–i/512/513e/514: only the voice changes, never the priestly owner."""
    if (
        doc.get("id") in TEXTS
        and segment.get("id") in INVENTORIES[doc["id"]]
        and not base_errors(doc)
    ):
        return {"cantu": {"voice": "secreto"}}
    return {}


def supplement(doc: dict[str, Any], segment: dict[str, Any], grants: dict[str, Any]) -> None:
    """DMS25b/26 singing beside RitusVII8/11 priestly recitation; no clock."""
    if (
        doc.get("id") in TEXTS
        and segment.get("id") in INVENTORIES[doc["id"]]
        and grants.get("cantu") == {"gradus": 2, "source": "DMS 25 b"}
    ):
        grants["cantu"]["performance"] = deepcopy(PERFORMANCE)


def publication_errors(doc: dict[str, Any]) -> list[str]:
    """Publication cannot silently omit a required claim or invent another."""
    errors = base_errors(doc)
    for segment in doc.get("segments", []):
        expected = (
            {"cantu": {"source": "DMS 25 b", "performance": PERFORMANCE}}
            if doc.get("id") in TEXTS and segment.get("id") in INVENTORIES[doc["id"]]
            else None
        )
        actual = source_fields(segment).get("participation_performance")
        if actual != expected:
            errors.append(f"{segment.get('id')}: participation performance differs")
        if expected and segment.get("participation") != {
            "lecta": {"gradus": 3, "source": "DMS 31 c"},
            "cantu": {"gradus": 2, "source": "DMS 25 b", "performance": PERFORMANCE},
        }:
            errors.append(f"{segment.get('id')}: performance grant differs")
        if expected and segment.get("delivery") != {"cantu": {"voice": "secreto"}}:
            errors.append(f"{segment.get('id')}: priestly sung-Mass voice must be secreto")
    return errors
