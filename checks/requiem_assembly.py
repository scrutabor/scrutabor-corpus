"""Closed All Souls assembly, prescribed by Ritus X.4 and XIII.1."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

FAMILY = "commemoratio-omnium-fidelium-defunctorum"
MASSES = (FAMILY, FAMILY + "-missa-ii", FAMILY + "-missa-iii")
OMISSIONS = [
    {"text": "ordinarium.lavabo", "segments": ["s09", "s10"], "reason": "lavabo-doxology"},
    {"text": "ordinarium.iudica-me", "reason": "requiem-iudica"},
    {"text": "ordinarium.qui-dixisti", "reason": "requiem-peace-prayer"},
    {"text": "ordinarium.benedictio", "reason": "requiem-blessing"},
]
TARGETS = {
    "ordinarium.iudica-me": "ce480f23033dc3110cdcacd910945676d8440b610c6953371e11ef16fb21865b",
    "ordinarium.qui-dixisti": "3e2c1d50d2af09518a87bfcf8c61a8d7e940f73dda4b9e990323f61985ad448c",
    "ordinarium.benedictio": "c43dbca818a84d849b213fc29e4a5216212bdd7608bbf169b34d383ff03e7410",
}


def is_requiem(doc: dict) -> bool:
    """Recognize only the represented family; inconsistent identities still fail."""
    return doc.get("id") in MASSES or doc.get("observance") == FAMILY


def target_errors(corpus: Path) -> list[str]:
    """Bind complete canonical study bodies, never a segment-suppression guess."""
    errors = []
    for identity, expected in TARGETS.items():
        try:
            doc = json.loads((corpus / f"texts/{identity.replace('.', '/', 1)}.json").read_text())
            selected = {
                "id": doc["id"],
                "segments": [
                    {k: s[k] for k in ("id", "type", "text", "speaker", "voice", "words") if k in s}
                    for s in doc["segments"]
                ],
            }
            actual = hashlib.sha256(
                json.dumps(
                    selected, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode()
            ).hexdigest()
            if actual != expected:
                errors.append(f"ordinary_omissions target: {identity} complete source body differs")
        except (OSError, ValueError, KeyError, TypeError) as error:
            errors.append(f"ordinary_omissions target: {identity}: {error}")
    return errors


def assembly_errors(doc: dict, corpus: Path) -> list[str]:
    from checks.lavabo_omissions import target_errors as lavabo_target_errors
    from checks.participation_performance import publication_errors

    errors = []
    identity = doc.get("id")
    calendar = doc.get("calendar")
    if (
        identity not in MASSES
        or doc.get("observance") != FAMILY
        or doc.get("collection") != "sanctorale"
        or not isinstance(calendar, dict)
        or calendar.get("key") != FAMILY
    ):
        errors.append("Requiem assembly requires the exact authored All Souls family")
    if doc.get("formulary_schema") != "1.5.0":
        errors.append("formulary_schema must be 1.5.0")
    if doc.get("ordinary_omissions") != OMISSIONS:
        errors.append("ordinary_omissions must contain the exact four Requiem prescriptions")
    components = doc.get("components", [])
    if not isinstance(components, list) or any(not isinstance(c, dict) for c in components):
        return [*errors, "Requiem assembly components must be objects"]
    rows = [(i, c) for i, c in enumerate(components) if c.get("role") == "agnus-dei"]
    if (
        len(rows) != 1
        or rows[0][1]
        != {
            "key": "agnus-dei",
            "role": "agnus-dei",
            "text": "ordinarium.agnus-dei-defunctorum",
            "relation": "shared",
        }
        or rows[0][0] == 0
        or rows[0][0] + 1 >= len(components)
        or components[rows[0][0] - 1].get("role") != "praefatio"
        or components[rows[0][0] + 1].get("role") != "communio"
    ):
        errors.append(
            "Requiem assembly requires its complete shared Agnus between Preface and Communion"
        )
    errors.extend(lavabo_target_errors(corpus))
    errors.extend(target_errors(corpus))
    try:
        body = json.loads((corpus / "texts/ordinarium/agnus-dei-defunctorum.json").read_text())
        if body.get("id") != "ordinarium.agnus-dei-defunctorum":
            errors.append("Requiem assembly Agnus body identity differs")
        errors.extend(publication_errors(body))
    except (OSError, ValueError) as error:
        errors.append(f"Requiem assembly Agnus body: {error}")
    return errors
