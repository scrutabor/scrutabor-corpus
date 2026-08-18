"""A capital does not lose its accent.

The 1962 typical edition omits the acute on a CAPITAL letter. That is a
typographic habit of the printing, not a claim about the word, and the same
page proves it: the Advent III gradual sets *éxcita* lowercase and accented,
and the Advent III alleluia sets *Excita* capitalized and bare — one word, one
page, differing only in case.

So the edition's accent is restored when a word is capitalized, and this check
holds that decision. Without it the rule is a sentence in a ledger, and the
first text transcribed straight off a page image would quietly disagree with
the eighty before it.

Only words of THREE syllables or more are checked. Latin never marks the
accent on a disyllable because it cannot fall anywhere else, and the edition
does not either — *Ecce* and *Deus* are correct bare, and a rule that demanded
otherwise would fire on hundreds of correct forms and be switched off.
"""

from __future__ import annotations

import re
import unicodedata

VOWEL_GROUP = re.compile(r"[aeiouyæœáéíóúýàèìòùǽǣ]+", re.IGNORECASE)

# U+0301 COMBINING ACUTE. Membership is decided by DECOMPOSING the character,
# not by listing accented letters: a first draft listed them and reported
# Fœ́deris and Bartholomǽi as bare, because their accents ride on ligatures —
# œ with a combining acute, and the precomposed ǽ — that no hand-written list
# was going to remember.
ACUTE = "\u0301"


def accented(form: str) -> bool:
    return ACUTE in unicodedata.normalize("NFD", form)


# Words the edition prints bare for reasons other than case, declared rather
# than inferred. Hebrew and Greek names keep the shape their source gives them.
EXPECTED_BARE = {
    "Israel",
    "Israël",
    "Ierusalem",
    "Ierúsalem",
}


def syllables(form: str) -> int:
    return len(VOWEL_GROUP.findall(form))


def check(doc: dict) -> list[str]:
    """One message per capitalised word that lost the accent it should carry."""
    errors: list[str] = []
    for segment in doc.get("segments", []):
        for word in segment.get("words") or []:
            form = word["form"]
            if not form or not form[0].isupper() or form in EXPECTED_BARE:
                continue
            if syllables(form) < 3:
                continue
            if accented(form):
                continue
            errors.append(
                f"{doc['id']}:{word['id']} ({form}): a capitalised word of "
                f"{syllables(form)} syllables carries no accent — the typical edition drops "
                f"it on capitals and this edition restores it (checks/capitals.py)"
            )
    return errors
