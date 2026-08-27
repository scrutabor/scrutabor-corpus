"""Explanations may grow freely; shrinking them is an editorial event.

The 2026 recension cut the word-level prose deliberately, by recorded
adjudication — and then a handful of substantive notes were found to have
gone out with the routine ones, invisibly, because the site count had no
witness. This check gives it one: `explanation_floor.json` records the
adjudicated minimum for explanation sites and for the citations they carry,
and any change that drops below it must lower the floor in the same change,
with a dated reason. Growth never touches the file.
"""

from __future__ import annotations

import json
from pathlib import Path

FLOOR = Path(__file__).with_name("explanation_floor.json")


def counts(corpus: Path) -> tuple[int, int]:
    sites = citations = 0
    for path in sorted(corpus.glob("texts/*/*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        declared = (doc.get("localization") or {}).get("explanations") or {}
        sites += len(declared)
        citations += sum(len((entry or {}).get("citations") or []) for entry in declared.values())
    return sites, citations


def check(corpus: Path) -> list[str]:
    recorded = json.loads(FLOOR.read_text(encoding="utf-8"))
    sites, citations = counts(corpus)
    errors: list[str] = []
    if not str(recorded.get("adjudicated") or "").strip():
        errors.append(
            "explanation floor: the recorded baseline names no adjudication — "
            "a floor nobody dated is a floor nobody set"
        )
    if sites < recorded["sites"]:
        errors.append(
            f"explanation floor: {sites} sites against an adjudicated minimum of "
            f"{recorded['sites']} — removing explanation sites requires lowering "
            f"the floor in the same change, with a dated reason"
        )
    if citations < recorded["citations"]:
        errors.append(
            f"explanation floor: {citations} explanation citations against an "
            f"adjudicated minimum of {recorded['citations']} — dropping a cited "
            f"claim requires lowering the floor in the same change"
        )
    return errors
