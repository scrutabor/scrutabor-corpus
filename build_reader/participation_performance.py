"""Independently check performance metadata in the published neutral body."""

from __future__ import annotations

import json
from pathlib import Path


def verify(out: Path, manifest: dict) -> list[str]:
    """The current reader retains all five descriptors, even if the source also lost them."""
    errors = []
    if manifest.get("schema_version") != "6.7.0":
        return ["participation performance requires reader 6.7.0"]
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
    return errors
