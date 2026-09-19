"""Paired punctuation in translations, including spans across verse boundaries."""

from __future__ import annotations

import re


def check(doc: dict) -> list[str]:
    """Check unambiguous delimiter and segment-boundary corruption, not style.

    A quotation may run across several translated verses. Apostrophes and single
    quotes are deliberately excluded: a final possessive apostrophe is not an
    unmatched quotation mark. ASCII quotation marks are also ambiguous.
    """
    language = doc.get("language") or doc.get("lang")
    pairs = {"(": ")", "[": "]", "«": "»", "„" if language == "pl" else "“": "”"}
    closing = set(pairs.values())
    stack: list[tuple[str, str]] = []
    errors: list[str] = []
    for sid, segment in (doc.get("segments") or {}).items():
        where = f"{doc.get('text', '?')}:{sid}.translation.{language}"
        if re.match(r"\s*[,;:]", segment.get("translation", "")):
            errors.append(f"{where}: separator belongs at the end of the preceding segment")
        if re.search(r"\(\([^()]*\)\)", segment.get("translation", "")):
            errors.append(f"{where}: duplicated parenthesis wrapper")
        for char in segment.get("translation", ""):
            if char in pairs:
                stack.append((char, where))
            elif char in closing:
                if stack and pairs[stack[-1][0]] == char:
                    stack.pop()
                else:
                    errors.append(f"{where}: unmatched closing delimiter {char!r}")
    for char, where in stack:
        errors.append(f"{where}: unmatched opening delimiter {char!r}")
    return errors
