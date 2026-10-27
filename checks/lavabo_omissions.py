"""Closed source-owned Lavabo doxology omission, not a second calendar."""

from __future__ import annotations

import json
from pathlib import Path

LEGACY_SCHEMA = "1.3.0"
OMISSION_SCHEMA = "1.4.0"
CATALOG_SCHEMA = "1.4.0"
DESCRIPTOR = {
    "text": "ordinarium.lavabo",
    "segments": ["s09", "s10"],
    "reason": "lavabo-doxology",
}
DOXOLOGY = (
    "Glória Patri et Fílio et Spirítui Sancto",
    "Sicut erat in princípio et nunc et semper et in sǽcula sæculórum Amen",
)


def required(doc: dict) -> bool:
    """Ritus VII.6: de Tempore in Passiontide, or a Mass for the Dead.

    These are classifications of the actual authored Mass. The calendar
    occurrence still decides whether it can be selected on a particular date.
    The supported dead-Mass family is the three All Souls formularies only.
    """
    return (doc.get("collection") == "temporale" and doc.get("season") == "passionis") or doc.get(
        "observance"
    ) == "commemoratio-omnium-fidelium-defunctorum"


def errors(doc: dict, corpus: Path) -> list[str]:
    needed = required(doc)
    schema = OMISSION_SCHEMA if needed else LEGACY_SCHEMA
    result = []
    if doc.get("formulary_schema") != schema:
        result.append(f"formulary_schema must be {schema}")
    if needed:
        if doc.get("ordinary_omissions") != [DESCRIPTOR]:
            result.append("ordinary_omissions must contain the exact Lavabo doxology descriptor")
    elif "ordinary_omissions" in doc:
        result.append("ordinary_omissions is not prescribed for this Mass")
    if result or not needed:
        return result
    try:
        text = json.loads((corpus / "texts/ordinarium/lavabo.json").read_text(encoding="utf-8"))
        segments = text["segments"]
        words = [word for segment in segments for word in segment.get("words", [])]
        if (
            text["id"] != "ordinarium.lavabo"
            or [segment["id"] for segment in segments] != [f"s{i:02d}" for i in range(1, 11)]
            or segments[0]["type"] != "rubric"
            or any(segment["type"] != "verse" for segment in segments[1:])
            or [word["id"] for word in words] != [f"w{i:03d}" for i in range(1, 95)]
        ):
            raise ValueError("Lavabo complete body identity differs")
        for index, (first, last) in enumerate(((75, 81), (82, 94))):
            segment = segments[index + 8]
            selected = segment["words"]
            if (
                [word["id"] for word in selected] != [f"w{i:03d}" for i in range(first, last + 1)]
                or " ".join(word["form"] for word in selected) != DOXOLOGY[index]
                or segment.get("speaker") != "sacerdos"
                or segment.get("voice") != "secreto"
            ):
                raise ValueError("Lavabo doxology scope differs")
    except (
        OSError,
        UnicodeError,
        ValueError,
        KeyError,
        TypeError,
        IndexError,
        AttributeError,
    ) as error:
        result.append(f"ordinary_omissions target: {error}")
    return result
