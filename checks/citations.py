"""One work, one title.

The reader-facing bibliography is built by grouping citations on their title
string, so a work cited under two spellings becomes two entries on that page —
the same dictionary listed twice, each with half the backlinks. Nothing caught
that, because both spellings are individually correct English.

It happened on 2026-08-17: eighteen new lexicon notes cited "Lewis–Short, A
Latin Dictionary" beside the fifty-eight already citing "Lewis and Short, A
Latin Dictionary". Both name the same book. The bibliography would have shown
it twice.

So titles are compared on a key that ignores exactly the things that vary
between correct spellings — case, punctuation, dashes, and the connectives a
compound name may or may not spell out. Two DIFFERENT titles sharing a key is
an error, and the message prints both with their counts, because the fix is
always to pick the established one rather than to invent a third.
"""

from __future__ import annotations

import collections
import re

# The connectives a compound author-name may spell out or replace with a dash.
CONNECTIVES = {"and", "et", "&"}


def key(title: str) -> str:
    """What survives of a title once correct spellings stop differing."""
    words = re.split(r"[^0-9a-z]+", title.lower())
    return "".join(w for w in words if w and w not in CONNECTIVES)


def titles(node: object, found: collections.Counter) -> None:
    """Every citation title anywhere in a corpus document."""
    if isinstance(node, dict):
        if isinstance(node.get("title"), str) and ("locator" in node or "url" in node):
            found[node["title"]] += 1
        for value in node.values():
            titles(value, found)
    elif isinstance(node, list):
        for value in node:
            titles(value, found)


def check(docs: list[dict]) -> list[str]:
    """One message per work cited under more than one title."""
    found: collections.Counter[str] = collections.Counter()
    for doc in docs:
        titles(doc, found)

    grouped: dict[str, list[str]] = collections.defaultdict(list)
    for title in found:
        grouped[key(title)].append(title)

    errors: list[str] = []
    for variants in grouped.values():
        if len(variants) < 2:
            continue
        shown = ", ".join(f"{t!r} ({found[t]}x)" for t in sorted(variants, key=lambda t: -found[t]))
        errors.append(
            f"one work is cited under {len(variants)} titles — {shown} — and the "
            f"bibliography groups on the title, so it would be listed once per spelling"
        )
    return errors
