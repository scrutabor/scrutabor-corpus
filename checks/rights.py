"""What this edition may reproduce, held as data rather than as a hope.

The corpus cites 52 works. Eight of them are cited for WORDING — a verse
translation that follows what the Church actually prays in that language — and
that is a different kind of citation from a scripture reference or a dictionary
note. A reference says where to look. A wording citation says whose words these
are.

Until 2026-08-18 nothing recorded the difference and nothing recorded rights at
all, while the repository offered the whole corpus under one licence. That is
the shape of a rights incident: not a wrong statement, but no statement, made
about 1,554 translated segments at once.

`sources.json` now carries every work with a status — public-domain, own,
permission, unverified — and a basis saying why. This file holds it to the
corpus:

- every title cited anywhere resolves to a work in the registry
- every work carries a status the registry declares
- nothing new can be cited without saying what it is

It does NOT decide whether a use is lawful. `permission` means a living rights
holder and no permission recorded here, and `unverified` means nobody has
established which case applies. Both are facts about this repository. Neither
is a legal opinion, and the count of them is the point: it is meant to be read
and acted on, not to sit at zero.
"""

from __future__ import annotations

import json
from pathlib import Path

STATUSES = ("public-domain", "own", "permission", "unverified")

# A citation on a translation names the wording this edition follows. Anywhere
# else it names a place to look, which raises no question of reproduction.
WORDING_FIELD = "translation_citations"


def load(corpus: Path) -> tuple[dict, list[str]]:
    path = corpus / "sources.json"
    if not path.exists():
        return {}, ["sources.json is missing — every cited work must declare its rights"]
    doc = json.loads(path.read_text(encoding="utf-8"))
    works = doc.get("works") or {}
    errors = []
    for title, work in sorted(works.items()):
        status = (work.get("rights") or {}).get("status")
        if status not in STATUSES:
            errors.append(f"sources.json:{title}: status {status!r} is not one of {STATUSES}")
        if not ((work.get("rights") or {}).get("basis") or "").strip():
            errors.append(f"sources.json:{title}: a status without a basis says nothing")
    return works, errors


def cited(doc: object, field: str | None = None) -> list[tuple[str, bool]]:
    """Every (title, is-wording) pair in a document."""
    out: list[tuple[str, bool]] = []
    if isinstance(doc, dict):
        if "title" in doc and "locator" in doc:
            out.append((doc["title"], field == WORDING_FIELD))
        for key, value in doc.items():
            out += cited(value, key if key.endswith("_citations") else field)
    elif isinstance(doc, list):
        for value in doc:
            out += cited(value, field)
    return out


def check(docs: list[dict], works: dict) -> list[str]:
    """One message per citation the registry cannot account for."""
    errors = []
    for doc in docs:
        for title, _wording in cited(doc):
            if title not in works:
                errors.append(
                    f"{doc.get('id') or doc.get('text') or '?'}: cites {title!r}, which is "
                    f"not in sources.json — a work this edition quotes must say what it is"
                )
    return errors


def exposure(docs: list[dict], works: dict) -> dict[str, int]:
    """How many sites follow wording whose rights are not settled.

    Counted rather than judged. A number that has to be looked at every build is
    harder to forget than a sentence in a README.
    """
    tally = {s: 0 for s in STATUSES}
    tally["unregistered"] = 0
    for doc in docs:
        for title, wording in cited(doc):
            if not wording:
                continue
            work = works.get(title)
            if work is None:
                tally["unregistered"] += 1
            else:
                tally[(work.get("rights") or {}).get("status", "unverified")] += 1
    return tally
