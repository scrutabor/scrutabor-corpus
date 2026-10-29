"""Independently retain the exact authored assembly in the neutral catalogue."""

from __future__ import annotations

import copy
import json
from pathlib import Path


def manifest_errors(manifest: dict) -> list[str]:
    base = manifest.get("base")
    if (
        manifest.get("schema_version") != "6.10.0"
        or not isinstance(base, dict)
        or base.get("formularies") != "formularies.json"
    ):
        return ["Requiem assembly requires reader 6.10.0 and its declared catalogue"]
    return []


def verify(corpus: Path, out: Path, manifest: dict) -> list[str]:
    errors = manifest_errors(manifest)
    if errors:
        return errors
    published = json.loads((out / "formularies.json").read_text())
    # Read authored objects directly, independently of emit.formulary_catalog.
    originals = [
        json.loads(p.read_text()) for p in sorted((corpus / "formularies").glob("*/*.json"))
    ]
    expected = []
    for original in sorted(originals, key=lambda row: row["order"]):
        row = copy.deepcopy(original)
        del row["formulary_schema"]
        for component in row["components"]:
            component["text"] = component["text"].replace(".", "/", 1)
        row["ordinary_omissions"] = [
            {**item, "text": item["text"].replace(".", "/", 1)}
            for item in row.get("ordinary_omissions", [])
        ]
        expected.append(row)
    if published != {"schema_version": "1.5.0", "formularies": expected}:
        return ["Requiem assembly catalogue differs from independent authored reconstruction"]
    return []
