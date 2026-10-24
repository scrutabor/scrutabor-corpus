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
    if doc.get("id") != TEXT:
        return []
    segments = doc.get("segments", [])
    errors = []
    if [s.get("id") for s in segments] != ["s01", *ROWS]:
        errors.append("Sanctus performance requires the exact six source rows")
    if not segments or segments[0].get("type") != "rubric":
        errors.append("Sanctus opening must remain a rubric")
    for segment in segments:
        identity = segment.get("id")
        if identity not in ROWS:
            continue
        first, forms = ROWS[identity]
        expected = [(f"w{first + offset:03}", form) for offset, form in enumerate(forms.split())]
        actual = [(w.get("id"), w.get("form")) for w in segment.get("words", [])]
        if actual != expected:
            errors.append(f"{identity}: Sanctus performance source words/IDs differ")
        if (
            segment.get("type") != "verse"
            or segment.get("speaker") != "sacerdos"
            or segment.get("voice") != "clara"
            or ("delivery" in segment and segment["delivery"] != {"cantu": {"voice": "secreto"}})
        ):
            errors.append(f"{identity}: Sanctus priestly base must remain unchanged")
    return errors


def priestly_delivery(doc: dict[str, Any], segment: dict[str, Any]) -> dict[str, Any]:
    """RG511h/513e/514: only the voice changes, never the priestly owner."""
    if doc.get("id") == TEXT and segment.get("id") in ROWS and not base_errors(doc):
        return {"cantu": {"voice": "secreto"}}
    return {}


def supplement(doc: dict[str, Any], segment: dict[str, Any], grants: dict[str, Any]) -> None:
    """DMS25b/26 singing beside RitusVII8/11 priestly recitation; no clock."""
    if (
        doc.get("id") == TEXT
        and segment.get("id") in ROWS
        and grants.get("cantu") == {"gradus": 2, "source": "DMS 25 b"}
    ):
        grants["cantu"]["performance"] = deepcopy(PERFORMANCE)


def publication_errors(doc: dict[str, Any]) -> list[str]:
    """Publication cannot silently omit a required claim or invent another."""
    errors = base_errors(doc)
    for segment in doc.get("segments", []):
        expected = (
            {"cantu": {"source": "DMS 25 b", "performance": PERFORMANCE}}
            if doc.get("id") == TEXT and segment.get("id") in ROWS
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
