"""Independently check performance metadata in the published neutral body."""

from __future__ import annotations

import json
from pathlib import Path


def verify(out: Path, manifest: dict) -> list[str]:
    """The current reader retains all eleven descriptors, even if the source lost them."""
    errors = []
    if manifest.get("schema_version") != "6.10.0":
        return ["participation performance requires reader 6.10.0"]
    entries = [
        entry for entry in manifest.get("texts", []) if entry.get("id") == "ordinarium.sanctus"
    ]
    if len(entries) != 1:
        return ["participation performance requires one Sanctus artifact"]
    if entries[0].get("path") != "texts/ordinarium/sanctus.json":
        return ["participation performance artifact path differs"]
    path = out / entries[0]["path"]
    if not path.is_file():
        return ["participation performance artifact is missing"]
    artifact = json.loads(path.read_text(encoding="utf-8"))
    rows = artifact.get("seg", [])
    identities = ["s02", "s03", "s04", "s05", "s06"]
    if [row.get("id") for row in rows] != ["s01", *identities]:
        errors.append("performance artifact must retain all six Sanctus rows")
    for row in rows:
        expected = (
            {
                "lecta": {"gradus": 3, "source": "DMS 31 c"},
                "cantu": {
                    "gradus": 2,
                    "source": "DMS 25 b",
                    "performance": {
                        "speaker": "schola",
                        "voice": "cantus",
                        "source": "DMS 25 b; 26",
                    },
                },
            }
            if row.get("id") in identities
            else None
        )
        if row.get("participation") != expected:
            errors.append(f"{row.get('id')}: published performance differs or is absent")
        if row.get("id") in identities and (
            row.get("type") != "verse"
            or row.get("speaker") != "sacerdos"
            or row.get("voice") != "clara"
            or row.get("delivery") != {"cantu": {"voice": "secreto"}}
        ):
            errors.append(f"{row.get('id')}: published priestly base changed")
    errors.extend(_agni(out, manifest))
    return errors


def _agni(out: Path, manifest: dict) -> list[str]:
    # A separate literal inventory prevents the producer from accepting its own omission.
    inventories = {
        "agnus-dei": (["s01", "s02", "s03", "s04", "s05"], {"s02", "s03", "s04"}, 25),
        "agnus-dei-defunctorum": (["s01", "s02", "s03"], {"s01", "s02", "s03"}, 28),
    }
    errors = []
    for slug, (identities, verses, count) in inventories.items():
        identity = "ordinarium." + slug
        path = f"texts/ordinarium/{slug}.json"
        entries = [e for e in manifest.get("texts", []) if e.get("id") == identity]
        if len(entries) != 1 or entries[0].get("path") != path or not (out / path).is_file():
            errors.append(f"performance requires one declared complete {identity} artifact")
            continue
        artifact = json.loads((out / path).read_text())
        rows = artifact.get("seg", [])
        if artifact.get("id") != identity or [r.get("id") for r in rows] != identities:
            errors.append(f"{identity}: performance source rows differ")
        # Compact words are tuples; stable IDs are verified by the full round-trip gate.
        if sum(len(r.get("w", [])) for r in rows) != count:
            errors.append(f"{identity}: performance word count differs")
        for row in rows:
            expected = (
                {
                    "lecta": {"gradus": 3, "source": "DMS 31 c"},
                    "cantu": {
                        "gradus": 2,
                        "source": "DMS 25 b",
                        "performance": {
                            "speaker": "schola",
                            "voice": "cantus",
                            "source": "DMS 25 b; 26",
                        },
                    },
                }
                if row.get("id") in verses
                else None
            )
            if row.get("participation") != expected:
                errors.append(
                    f"{identity}/{row.get('id')}: published performance differs or is absent"
                )
            if expected and (
                row.get("type") != "verse"
                or row.get("speaker") != "sacerdos"
                or row.get("voice") != "clara"
                or row.get("delivery") != {"cantu": {"voice": "secreto"}}
            ):
                errors.append(f"{identity}/{row.get('id')}: published priestly base changed")
    return errors
