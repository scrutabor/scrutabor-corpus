"""The declared Canon table and its actual reader-package dependencies."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from kalendarium.canon import calendar_table


def artifact_json(table: dict) -> str:
    """Keep one choice per diff line, without repeating any text content."""

    def compact(value: object) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    lines = ["{"]
    lines.extend(
        f"  {json.dumps(key)}:{compact(value)}," for key, value in table.items() if key != "pairs"
    )
    lines.append('  "pairs":[')
    lines.extend(
        f"    {compact(row)}{',' if i + 1 < len(table['pairs']) else ''}"
        for i, row in enumerate(table["pairs"])
    )
    lines.extend(["  ]", "}"])
    return "\n".join(lines) + "\n"


def verify(
    out: Path,
    manifest: dict,
    formularies: dict,
    calendar: dict,
    language_coverage: dict[str, set[str]],
    reader_schema: str,
) -> list[str]:
    """Reconstruct from source inputs, not the emitter's output or binding.

    The caller separately checks every text's round trip, exact lexicons and
    evidence graph. This preflight proves the table and required bodies can
    actually be resolved in the neutral edition and each language package.
    """
    errors: list[str] = []

    def read(name: str) -> dict | None:
        try:
            doc = json.loads((out / name).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(f"canon: cannot read {name}: {exc}")
            return None
        if not isinstance(doc, dict):
            errors.append(f"canon: {name} must be an object")
            return None
        return doc

    def bodies(package: dict, prefix: str, required: list[str]) -> None:
        entries = package.get("texts")
        if not isinstance(entries, list):
            errors.append(f"canon: {prefix} has no text declarations")
            return
        for text in required:
            matched = [
                entry for entry in entries if isinstance(entry, dict) and entry.get("id") == text
            ]
            name = f"{prefix}texts/{text.replace('.', '/', 1)}.json"
            if len(matched) != 1 or matched[0].get("path") != name:
                errors.append(f"canon: {name} must be declared exactly once")
                continue
            artifact = read(name)
            if artifact is None:
                continue
            if artifact.get("id") != text or not artifact.get("seg"):
                errors.append(f"canon: {name} has the wrong identity or empty body")
            if prefix and artifact.get("language") != package.get("language"):
                errors.append(f"canon: {name} has the wrong language")

    if manifest.get("schema_version") != reader_schema:
        errors.append("canon: root reader schema does not declare this contract")
    base = manifest.get("base")
    if not isinstance(base, dict) or base.get("canon") != "canon.json":
        errors.append("canon: base.canon must declare canon.json")
    # This module owns a compiler reference distinct from the emitter's. A
    # malformed emitting function must not also supply its own expected value.
    expected = calendar_table(formularies["formularies"], calendar)
    table = read("canon.json")
    if table is not None:
        if table != expected:
            errors.append("canon: selection table differs from the source calendar/catalogue")
        pairs = table.get("pairs")
        masses = table.get("masses")
        profiles = table.get("profiles")
        if not isinstance(pairs, list) or not pairs:
            errors.append("canon: pairs must be non-empty")
        elif (
            not isinstance(masses, list)
            or not masses
            or not isinstance(profiles, list)
            or not profiles
        ):
            errors.append("canon: Mass and profile indexes must be non-empty")
        else:
            for row in pairs:
                valid = isinstance(row, list) and len(row) == 3
                if valid:
                    day, mass, profile = row
                    try:
                        valid = isinstance(day, str) and date.fromisoformat(day).isoformat() == day
                    except ValueError:
                        valid = False
                    valid = (
                        valid
                        and type(mass) is int
                        and 0 <= mass < len(masses)
                        and type(profile) is int
                        and 0 <= profile < len(profiles)
                    )
                if not valid:
                    errors.append(f"canon: invalid date/Mass/profile row {row!r}")
                    break
    required = sorted(
        {text for profile in expected["profiles"] for text in profile["texts"].values()}
    )
    bodies(manifest, "", required)
    declarations = manifest.get("languages")
    if not isinstance(declarations, list):
        errors.append("canon: root language package declarations are missing")
        return errors
    for language, covered in language_coverage.items():
        matched = [
            entry
            for entry in declarations
            if isinstance(entry, dict) and entry.get("id") == language
        ]
        name = f"languages/{language}/manifest.json"
        if len(matched) != 1 or matched[0].get("path") != name:
            errors.append(f"canon: {name} must be declared exactly once")
            continue
        package = read(name)
        if package is None:
            continue
        if (
            package.get("language") != language
            or package.get("schema_version") != reader_schema
            or package.get("corpus_schema") != manifest.get("corpus_schema")
        ):
            errors.append(f"canon: {name} has the wrong package identity/version")
        bodies(package, f"languages/{language}/", [text for text in required if text in covered])
    return errors
