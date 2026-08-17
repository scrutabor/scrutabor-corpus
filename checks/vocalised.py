"""A Polish preposition is voiced by the word AFTER it, which may be the next gloss.

Polish *z* becomes *ze* and *w* becomes *we* before a word the bare form cannot
be said against: always before *mnie* and *mną*, and before an opening cluster
of the same articulation — *ze słowami*, *ze świętym*, *we wszystkich*.

The rule is ordinary orthography. What makes it escape every other check in
this corpus is WHERE the mistake lives. The word-by-word layer puts one gloss
under one Latin word, so a Polish verb that governs a preposition carries it at
the END of its own cell — *irrídeant* is glossed "niech szydzą z" — and the
noun it governs is a different cell entirely. Each cell is correct alone. The
reader sees "niech szydzą z mnie", and it should be "ze mnie".

So this check reads PAIRS, in the order the reader meets them, which is the
only place the defect exists. Found by the owner on 2026-08-18 in the Advent
introit, in a text that had passed collation, linting, adversarial review and a
human reading — all of which look at one cell, or at prose, and never at a
seam.

The corpus convicted itself: it already wrote *ze świętym*, *ze Słowem*, *we
mnie* and *we wszystkich* in other places, so the seven sites this found were
the edition disagreeing with itself rather than a rule anyone had to settle.
"""

from __future__ import annotations

import re

# Before these the vocalised form is obligatory, whatever follows them.
ALWAYS = ("mnie", "mną")

# An opening cluster of the same articulation as the preposition. Deliberately
# narrow: only the clusters where the bare form is genuinely unsayable, because
# a rule that fires on *z domu* would be noise and would be switched off.
CLUSTERS = {
    "z": r"^(s|z|ś|ź|ż|sz|rz)[bcćdfghjklłmnńprstwzźż]",
    "w": r"^(w|f)[bcćdfghjklłmnńprstwzźż]",
}

# Words that take the vocalised form without a rule accounting for them. The
# corpus writes *we Mszach* thirteen times and is right to, but that is this
# word and not a class: a draft that generalised it to every m + consonant
# immediately demanded *we mnóstwo*, which is wrong. Lexicalised exceptions are
# listed, never inferred.
LEXICAL = {"w": ("msz",)}

VOCALISED = {"z": "ze", "w": "we"}


def wants_vocalised(prep: str, following: str) -> bool:
    """True when `prep` must take its -e form before `following`."""
    word = following.lower().lstrip("(„\"'")
    if word.startswith(ALWAYS):
        return True
    if word.startswith(LEXICAL.get(prep, ())):
        return True
    return bool(re.match(CLUSTERS[prep], word))


def check(doc: dict, gloss: dict) -> list[str]:
    """One message per seam where a stranded preposition wants its -e."""
    if gloss.get("lang") != "pl":
        return []
    errors: list[str] = []
    entries = gloss.get("words") or {}

    for segment in doc.get("segments", []):
        words = segment.get("words") or []
        for index, word in enumerate(words[:-1]):
            text = (entries.get(word["id"], {}).get("gloss") or "").strip()
            following = (entries.get(words[index + 1]["id"], {}).get("gloss") or "").strip()
            if not text or not following:
                continue
            trailing = re.search(r"\b([zw])$", text, re.I)
            if not trailing:
                continue
            prep = trailing.group(1).lower()
            if not wants_vocalised(prep, following):
                continue
            errors.append(
                f"{doc['id']}:{word['id']} ({word['form']}): the Polish gloss ends in "
                f"{prep!r} and the next gloss is {following.split()[0]!r}, which reads "
                f"{prep} {following.split()[0]} — Polish wants {VOCALISED[prep]} here"
            )
    return errors
