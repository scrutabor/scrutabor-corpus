"""Derive and validate the compact summary of a textual apparatus.

The prose note may explain a difficult reading, but arithmetic and class
membership are facts already present in ``adjudicated``. Storing the derived
summary makes those facts easy for humans to scan; validating it prevents the
copied count or class list from drifting when an entry changes.

The same pass checks one class condition that is a fact about the readings
themselves: a ``capital-accent`` entry may differ from its witness only by
acutes that sit on capitals.
"""

import json
import sys
import unicodedata
from pathlib import Path

CORPUS = Path(__file__).resolve().parent.parent

# A withdrawn template on accent-only entries is not a general prose classifier.
DEPRECATED_ACCENT_RULING = (
    "The lexical accent is restored in the working text under the edition's house convention; "
    "the witness's capital typography is recorded exactly."
)


def deprecated_accent_rulings(apparatus: dict) -> list[str]:
    """Reject one complete withdrawn statement, not its words or other classes."""
    return [
        f"apparatus.adjudicated[{index}]: withdrawn accent ruling template"
        for index, entry in enumerate(apparatus.get("adjudicated", []))
        if entry.get("class") == "accent" and entry.get("ruling") == DEPRECATED_ACCENT_RULING
    ]


ACUTE = "\u0301"


def acute_letters(token: str) -> list[tuple[str, bool]]:
    """The alphabetic base letters of a token, in order, each with whether it
    carries an acute. Punctuation and other marks are not letters here."""
    letters: list[str] = []
    acute: list[bool] = []
    attached = False
    for character in unicodedata.normalize("NFD", token):
        if unicodedata.combining(character):
            if attached and character == ACUTE:
                acute[-1] = True
        elif character.isalpha():
            letters.append(character)
            acute.append(False)
            attached = True
        else:
            attached = False
    return list(zip(letters, acute, strict=True))


def capital_accent_issue(ours: str, theirs: str) -> str | None:
    """Why one witness reading cannot be a capital-accent difference, or None.

    The letters are aligned case-insensitively with punctuation ignored, for
    this comparison only. Every acute present on one side and absent on the
    other must sit on an uppercase letter on the side that carries it. A
    coexisting comma or change of case neither excuses an acute on a
    lowercase letter nor disqualifies a genuine one on a capital. An
    identical reading is positive support for the selected form, not a
    variant. Other diacritics are outside this condition.
    """
    if ours == theirs:
        return None
    left, right = acute_letters(ours), acute_letters(theirs)
    if [letter.casefold() for letter, _ in left] != [letter.casefold() for letter, _ in right]:
        return "letters cannot align for a capital-accent comparison"
    changed = [pair for pair in zip(left, right, strict=True) if pair[0][1] != pair[1][1]]
    if not changed:
        return "no changed acute on a capital"
    if any(acute and not letter.isupper() for pair in changed for letter, acute in pair):
        return "changed acute on a lowercase letter"
    return None


def capital_accent_positions(apparatus: dict) -> list[str]:
    """Check every witness reading of every capital-accent entry. The shape of
    a malformed record is the schema check's concern, not this one's."""
    errors: list[str] = []
    for index, entry in enumerate(apparatus.get("adjudicated", [])):
        if not isinstance(entry, dict) or entry.get("class") != "capital-accent":
            continue
        ours, witnesses = entry.get("ours"), entry.get("witnesses")
        if not isinstance(ours, str) or not isinstance(witnesses, dict):
            continue
        for witness, reading in witnesses.items():
            if not isinstance(reading, str):
                continue
            problem = capital_accent_issue(ours, reading)
            if problem:
                errors.append(f"apparatus.adjudicated[{index}] witness {witness!r}: {problem}")
    return errors


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
    errors = deprecated_accent_rulings(apparatus) + capital_accent_positions(apparatus)
    if actual != expected:
        errors.append(
            f"{path.name}: apparatus summary must be derived from adjudicated: "
            f"expected {expected!r}, got {actual!r}"
        )
    return errors


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
