"""A text id is half of every word's global address, and nothing protected it.

SCHEMA.md gives a word's external address as `<text-id>.<word-id>`, and that is
what the apparatus, the review seals, the SRS deck and the app's own
concordance links all use — `/app/pl/ordinarium/credo?w=w005`. The mint made
the second half permanent. This file is about the first.

There has never been a rename, which is exactly why the rule is cheap to make
now: `redirects.json` is append-only, a retired id may never be reused for new
content, and a text that has moved must say where it went. Written after the
first rename, this file would be a migration instead of a rule.
"""

from __future__ import annotations

import json
from pathlib import Path


def load(corpus: Path) -> tuple[list[dict], list[str]]:
    path = corpus / "redirects.json"
    if not path.exists():
        return [], ["redirects.json is missing — a renamed text must be able to say so"]
    doc = json.loads(path.read_text(encoding="utf-8"))
    moved = doc.get("moved")
    if not isinstance(moved, list):
        return [], ["redirects.json: `moved` must be a list, even an empty one"]
    errors = []
    for entry in moved:
        if not entry.get("from"):
            errors.append("redirects.json: an entry with no `from` names nothing")
        if "to" not in entry:
            errors.append(f"redirects.json:{entry.get('from')}: needs `to`, or null if withdrawn")
        if not (entry.get("why") or "").strip():
            errors.append(f"redirects.json:{entry.get('from')}: a move without a reason")
    return moved, errors


def check(corpus: Path, text_ids: set[str]) -> list[str]:
    """A retired id is retired for good, and a live one has not been retired."""
    moved, errors = load(corpus)
    # Every source first, because a chain resolves forwards: a.one moves to
    # a.two which moves to a.three, and only the last is a live text. Checking
    # targets while still building the set of sources made the record
    # order-dependent, which an append-only file has no business being.
    sources = [str(entry.get("from")) for entry in moved]
    known = text_ids | set(sources)
    seen: set[str] = set()
    for entry in moved:
        source = str(entry.get("from"))
        if source in seen:
            errors.append(f"redirects.json:{source}: listed twice — the record is append only")
        seen.add(source)
        if source in text_ids:
            errors.append(
                f"redirects.json:{source}: is retired and is also a live text — an id that "
                f"has been given up may never name new content, or every reference to the "
                f"old one silently resolves to the new"
            )
        target = entry.get("to")
        if target and target not in known:
            errors.append(
                f"redirects.json:{source}: moved to {target!r}, which is not a text and is "
                f"not itself redirected"
            )
    return errors
