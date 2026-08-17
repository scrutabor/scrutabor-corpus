"""The note a reader reads and the tag a reader parses must say the same thing.

The gloss files explain each word in prose, and that prose names the word a
form agrees with or the preposition that governs it, with the word id beside
it: *Zgadza się z „pópulum" (w007)*, *Agrees with "culpa" (w034)*, *Ablативus
po „in" (w029)*. The text files record the same relation as data, in `head`.

Nothing compared them, and they had drifted apart in both directions: *ipsa*
tagged feminine under a note reading "neuter plural", *clamántem* headed at
*te* under notes naming *pópulum*, *ímpiis* headed at *viris* under notes
calling it substantival. A reader meets both layers on the same panel.

The claim is only extracted where the prose makes it unambiguously — an
agreement phrase or a government phrase, immediately followed by an id. Notes
that merely mention another word ("It joins X to Y") assert no relation this
file can check, and are left alone.
"""

from __future__ import annotations

import re

# "agrees with X (wNNN)" — the note claims W's head is wNNN.
AGREES = [
    re.compile(r"[Zz]gadza(?:ją)?\s+się\s+z(?P<rest>[^.]{0,90})"),
    re.compile(r"zgadzając[ye]?\w*\s+się\s+z(?P<rest>[^.]{0,90})"),
    re.compile(r"[Aa]gree(?:s|ing)\s+with(?P<rest>[^.]{0,90})"),
]
ID = re.compile(r"\((w\d{3})\)")


def _claims(text: str, patterns: list[re.Pattern]) -> list[set[str]]:
    """One set per agreement clause: every word id that clause names.

    A note may name more than one, and truthfully — *sperántibus* agrees with
    `Nobis` AND `fámulis`, which stand in apposition. The data records one of
    them, so the check asks only that the recorded head be among those named.
    """
    out = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            named = {m.group(1) for m in ID.finditer(match.group("rest"))}
            if named:
                out.append(named)
    return out


def check(doc: dict, gloss: dict) -> list[str]:
    """One message per place where the prose and the data disagree."""
    from checks.syntax import is_modifier

    words = {w["id"]: w for s in doc.get("segments", []) for w in (s.get("words") or [])}
    lang = gloss.get("lang", "?")
    errors: list[str] = []
    for wid, entry in (gloss.get("words") or {}).items():
        note = entry.get("function")
        word = words.get(wid)
        if not note or word is None or not is_modifier(word):
            continue

        for named in _claims(note, AGREES):
            named = {c for c in named if c in words}
            if not named or word.get("head") in named:
                continue
            shown = " / ".join(f"{words[c]['form']!r} ({c})" for c in sorted(named))
            if word.get("substantive"):
                errors.append(
                    f"{doc['id']}:{wid} ({word['form']}): the {lang} note says it agrees "
                    f"with {shown}, but the word is marked `substantive`, which claims "
                    f"it agrees with nothing expressed"
                )
            else:
                errors.append(
                    f"{doc['id']}:{wid} ({word['form']}): the {lang} note says it agrees "
                    f"with {shown}, but head={word.get('head')!r}"
                )

    return errors
