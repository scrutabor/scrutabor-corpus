"""Form-specific ritual delivery of a segment.

The corpus stores the low-Mass delivery in ``speaker`` and ``voice``. Proper
chants are the systematic exception at a sung Mass: the schola sings what the
celebrant reads aloud at low Mass. This module derives that exception from the
liturgical genus, so individual formularies cannot drift between the two
models.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from checks.layout import formatted
from checks.orations import structure, sung_delivery
from checks.participation import CANTU_III_PROPER, proper_genus

ROOT = Path(__file__).resolve().parent.parent

# The solemn Passion has three traditional parts.  The printed role sequence
# is fixed here independently of the text files, just as the chant genera
# below are fixed independently of their stored overrides.  At low Mass the
# celebrant reads every part, which remains the base ``speaker`` in the text.
PALM_PASSION = "proprium.dominica-ii-passionis-evangelium"
PALM_PASSION_ROLES = (
    "CXCXCXCXCXCXCSCSCXCXCXCSCSCSCXCSCSCSCSCSCSCSCSCSCSCSCXCSCSCSCSCSCSCSCSCSCSCSCSCSCSCXCXCSCSCCSC"
)
PALM_PASSION_SEGMENTS = tuple(f"s{number:02d}" for number in range(1, 96) if number != 92)
assert len(PALM_PASSION_ROLES) == len(PALM_PASSION_SEGMENTS)
PALM_PASSION_DELIVERY = {
    segment: {"C": "chronista", "X": "christus", "S": "synagoga"}[role]
    for segment, role in zip(PALM_PASSION_SEGMENTS, PALM_PASSION_ROLES, strict=True)
}


def derive(doc: dict[str, Any], seg: dict[str, Any]) -> dict[str, Any]:
    """Return the form-specific override required by this segment."""
    _, orations = structure(doc)
    if seg.get("id") in orations:
        return sung_delivery(orations[seg["id"]])
    if doc.get("id") == PALM_PASSION and seg.get("id") in PALM_PASSION_DELIVERY:
        return {
            "cantu": {
                "speaker": PALM_PASSION_DELIVERY[seg["id"]],
                "voice": "cantus",
            }
        }
    if (
        doc.get("category") == "proprium"
        and seg.get("type") == "verse"
        and seg.get("words")
        and proper_genus(doc["id"]) in CANTU_III_PROPER
    ):
        return {"cantu": {"speaker": "schola", "voice": "cantus"}}
    return {}


def check_doc(doc: dict[str, Any]) -> tuple[list[str], int]:
    """Compare stored delivery with the derived liturgical role."""
    errors, overridden = [], 0
    for seg in doc.get("segments", []):
        want, have = derive(doc, seg), seg.get("delivery") or {}
        if want != have:
            errors.append(
                f"{seg['id']}: delivery {have or 'absent'} — "
                f"the Mass forms require {want or 'none'}"
            )
        if want:
            overridden += 1
    return errors, overridden


def run(write: bool = False) -> int:
    problems, written, carried = 0, 0, 0
    for path in sorted(ROOT.glob("texts/*/*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        for seg in doc.get("segments", []):
            want, have = derive(doc, seg), seg.get("delivery") or {}
            if want == have:
                carried += 1 if want else 0
                continue
            if write:
                if want:
                    seg["delivery"] = want
                else:
                    seg.pop("delivery", None)
                changed, written = True, written + 1
            else:
                problems += 1
                print(
                    f"delivery: {doc['id']} {seg['id']} carries {have!r}, "
                    f"the Mass forms require {want!r}"
                )
        if changed:
            path.write_text(formatted(doc), encoding="utf-8")

    if write:
        print(f"delivery: wrote {written} segments")
        return 0
    print(f"delivery: OK {carried} form-specific segment overrides")
    return problems


if __name__ == "__main__":
    sys.exit(1 if run(write="--write" in sys.argv) else 0)
