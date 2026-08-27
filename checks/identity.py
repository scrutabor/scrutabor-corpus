"""A word's id is its identity, and identity may not be reassigned.

SCHEMA.md has said so since the beginning — "never renumbered, never reused",
"document order = array order, not ID order", "a textual insertion takes the
NEXT FREE NUMBER". The rule was right and nothing enforced it, and nothing
recorded what the next free number was: it had to be inferred as one past the
highest, which works only for as long as no word has ever been removed.

That is not an abstract worry. A word id is the anchor for 408 apparatus
entries, 371 mentions in review seals, 1,331 cross-references inside gloss
prose, 41 rulings in this package's own code, and every shareable `?w=` link.
Renumbering silently invalidates all of them — silently, because every one of
those references would still resolve, to the wrong word.

So the mint is recorded, in `ids.next`, and this file holds three things:

- nothing is minted outside the counter, and the counter only ever rises
- an id is used once, as a live word or as a tombstone, never both
- a removed word leaves a tombstone naming a segment that still exists, so a
  deep link to it degrades to its neighbourhood instead of dangling

The counter is compared against the version in git rather than against
anything in the working tree, because "did this change" is a question about
history and cannot be answered from one snapshot.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

SEGMENT_ID = re.compile(r"^s\d{2,}$")
WORD_ID = re.compile(r"^w(\d{3,})$")


def numbers(doc: dict) -> list[int]:
    out = []
    for segment in doc.get("segments", []):
        for word in segment.get("words") or []:
            found = WORD_ID.match(word["id"])
            if found:
                out.append(int(found.group(1)))
    return out


def check(doc: dict) -> list[str]:
    """The mint's own arithmetic, inside one document."""
    errors: list[str] = []
    tid = doc.get("id", "?")
    mint = doc.get("ids")
    if not isinstance(mint, dict) or "next" not in mint:
        return [f"{tid}: ids.next is missing — the mint must be recorded"]
    if not isinstance(mint["next"], int):
        return [f"{tid}: ids.next is not a number — the mint must be recorded"]

    segment_ids = [segment["id"] for segment in doc.get("segments", [])]
    seen_segments: set[str] = set()
    for sid in segment_ids:
        if not SEGMENT_ID.match(sid):
            errors.append(f"{tid}:{sid}: a segment id is s + at least two digits")
        if sid in seen_segments:
            errors.append(f"{tid}:{sid}: segment id used twice")
        seen_segments.add(sid)

    live = [w["id"] for s in doc.get("segments", []) for w in (s.get("words") or [])]
    seen = set()
    for wid in live:
        if not WORD_ID.match(wid):
            errors.append(f"{tid}:{wid}: a word id is w + at least three digits")
        if wid in seen:
            errors.append(f"{tid}:{wid}: used twice — an id is one word")
        seen.add(wid)

    retired = mint.get("retired") or {}
    segments = set(segment_ids)
    for wid, anchor in sorted(retired.items()):
        if wid in seen:
            errors.append(f"{tid}:{wid}: is both a live word and a tombstone")
        if anchor not in segments:
            errors.append(
                f"{tid}:{wid}: the tombstone points at segment {anchor!r}, which this "
                f"text does not have — a retired word must degrade to somewhere real"
            )

    for wid in list(seen) + list(retired):
        found = WORD_ID.match(wid)
        if found and int(found.group(1)) >= mint["next"]:
            errors.append(
                f"{tid}:{wid}: is at or past ids.next={mint['next']} — every id comes "
                f"from the mint, and the mint moves after it gives one out"
            )
    return errors


def resolve_ref(corpus: Path, ref: str) -> str:
    """The commit a ref names, so the verdict can say what it compared.

    A comparison whose reference nobody can see is how the history check ran
    as HEAD-against-itself in CI for a month. An unresolvable ref is answered
    honestly rather than raised: the comparison itself will then say what it
    could not do.
    """
    result = subprocess.run(
        ["git", "-C", str(corpus), "rev-parse", "--short", f"{ref}^{{commit}}"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unresolvable"


def committed(corpus: Path, relative: str, ref: str) -> dict | None:
    """The version of a file in git, or None if it is not there yet."""
    result = subprocess.run(
        ["git", "-C", str(corpus), "show", f"{ref}:{relative}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def check_against_history(corpus: Path, ref: str = "HEAD") -> list[str]:
    """No id may change what it points at, and the mint may not rewind.

    Compared against `ref` — HEAD locally, where it guards uncommitted work,
    and the base the workflow names in CI. A text that is new in this change
    has no history to contradict.

    A ref that does not resolve FAILS rather than passes: under an unknown
    ref every file reads as new, which is the same silence this check exists
    to end, arrived at from the other side.
    """
    errors: list[str] = []
    if resolve_ref(corpus, ref) == "unresolvable":
        return [f"identity: base ref '{ref}' does not resolve — nothing was compared"]
    for path in sorted(corpus.glob("texts/*/*.json")):
        relative = str(path.relative_to(corpus))
        was = committed(corpus, relative, ref)
        if was is None:
            continue
        now = json.loads(path.read_text(encoding="utf-8"))
        tid = now.get("id", relative)

        old_next = (was.get("ids") or {}).get("next")
        new_next = (now.get("ids") or {}).get("next")
        if isinstance(old_next, int) and isinstance(new_next, int) and new_next < old_next:
            errors.append(
                f"{tid}: ids.next went backwards, {old_next} to {new_next} — the mint "
                f"only ever rises, or an id it already gave out can be given again"
            )

        before = {
            w["id"]: w["form"] for s in was.get("segments", []) for w in (s.get("words") or [])
        }
        after = {
            w["id"]: w["form"] for s in now.get("segments", []) for w in (s.get("words") or [])
        }
        retired = ((now.get("ids") or {}).get("retired") or {}).keys()
        for wid in sorted(before):
            if wid not in after and wid not in retired:
                errors.append(
                    f"{tid}:{wid} ({before[wid]!r}) has gone without a tombstone — a "
                    f"removed word is retired, so links to it degrade rather than dangle"
                )

        # A SHIFT is the dangerous shape, and absence alone does not find it.
        # Renumbering from the middle of a text leaves every id present except
        # one, each now pointing at its neighbour — so the first draft of this
        # check reported a single missing word for a seven-word shift, and the
        # six references that had quietly changed meaning went unmentioned.
        #
        # What distinguishes a renumbering from a correction is that the words
        # did not change. Same forms, same order, different ids: nothing was
        # edited, only readdressed.
        was_forms = [w["form"] for s in was.get("segments", []) for w in (s.get("words") or [])]
        now_forms = [w["form"] for s in now.get("segments", []) for w in (s.get("words") or [])]
        if was_forms == now_forms:
            moved = [
                (wid, before[wid], after.get(wid))
                for wid in before
                if wid in after and before[wid] != after[wid]
            ]
            if moved:
                first = sorted(moved)[0]
                errors.append(
                    f"{tid}: {len(moved)} ids now name a different word while the text "
                    f"itself is unchanged — {first[0]} was {first[1]!r} and is {first[2]!r}. "
                    f"This is a renumbering, and every reference to those ids still "
                    f"resolves, to the wrong word"
                )
    return errors
