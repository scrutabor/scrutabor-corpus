"""An introit's repetition rubric names its OWN antiphon.

The Missale signals the repetition typographically: after the Gloria Patri it
prints the antiphon's first word again and nothing else — *Glória Patri.
Gaudéte.* This edition writes that out as a rubric in its own voice, and the
rubric has to name the antiphon the reader is actually holding.

It did not. The sentence was written once for the First Sunday, whose introit
IS *Ad te levávi*, and copied unchanged into the Second and the Third, each of
which then told a reader to go back and repeat a different Sunday's antiphon.
Nothing compared the two, because the rubric is prose and the antiphon is
words, and no check in this corpus had ever looked at both at once.

So this one does. The rubric quotes an incipit, and the incipit must be the
opening of the text it stands in.
"""

from __future__ import annotations

import re
import unicodedata

RUBRIC = re.compile(r"repetitur\s+(.+?)\s+usque ad psalmum")


def fold(text: str) -> str:
    """Accents off, punctuation off, lowercase — an incipit is quoted for the
    eye and may lose the acute a heading drops."""
    stripped = "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"[^0-9a-z ]", " ", stripped.lower()).strip()


def check(doc: dict) -> list[str]:
    """One message per rubric naming an antiphon that is not this text's."""
    errors: list[str] = []
    words = [w for s in doc.get("segments", []) if s.get("words") for w in s["words"]]
    if not words:
        return errors
    opening = fold(" ".join(w["form"] for w in words[:6]))

    for segment in doc.get("segments", []):
        if segment.get("type") != "rubric":
            continue
        found = RUBRIC.search(segment.get("text") or "")
        if not found:
            continue
        named = fold(found.group(1))
        if not named or opening.startswith(named):
            continue
        errors.append(
            f"{doc['id']}:{segment['id']}: the rubric sends the reader back to "
            f"{found.group(1)!r}, but this text opens "
            f"{' '.join(w['form'] for w in words[:3])!r}"
        )
    return errors
