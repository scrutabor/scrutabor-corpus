"""Derive and validate the compact summary of a textual apparatus.

The prose note may explain a difficult reading, but arithmetic and class
membership are facts already present in ``adjudicated``. Storing the derived
summary makes those facts easy for humans to scan; validating it prevents the
copied count or class list from drifting when an entry changes.
"""

import json
import sys
from pathlib import Path

CORPUS = Path(__file__).resolve().parent.parent


def derived_summary(apparatus: dict) -> dict:
    entries = apparatus.get("adjudicated", [])
    return {
        "entries": len(entries),
        "classes": sorted({entry.get("class") for entry in entries if entry.get("class")}),
    }


def lint_apparatus_summary(path: Path) -> list[str]:
    if not path.is_file():
        return []
    apparatus = json.loads(path.read_text(encoding="utf-8"))
    expected = derived_summary(apparatus)
    actual = apparatus.get("summary")
    if actual != expected:
        return [
            f"{path.name}: apparatus summary must be derived from adjudicated: "
            f"expected {expected!r}, got {actual!r}"
        ]
    return []


def write_summaries(corpus: Path = CORPUS) -> int:
    written = 0
    for path in sorted((corpus / "witnesses").glob("*/apparatus.json")):
        apparatus = json.loads(path.read_text(encoding="utf-8"))
        summary = derived_summary(apparatus)
        if apparatus.get("summary") == summary:
            continue
        # Keep the scan-friendly summary beside the prose note rather than at
        # the end of a potentially long entry array.
        updated = {}
        for key, value in apparatus.items():
            updated[key] = value
            if key == "note":
                updated["summary"] = summary
        if "summary" not in updated:
            updated = {"summary": summary, **updated}
        path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written += 1
    return written


if __name__ == "__main__":
    if sys.argv[1:] != ["--write"]:
        print("usage: python -m checks.apparatus --write")
        raise SystemExit(2)
    print(f"apparatus summaries written: {write_summaries()}")
