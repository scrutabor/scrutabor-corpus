"""Gloss conventions held to the corpus.

A vocative is glossed bare. The gloss of a word in the vocative renders that
word, and the address particle *O* renders no Latin word; where the Latin
prints its own *O*, that token carries the particle. Continuous translations
may still say "O Lord" where English idiom wants it. The rule was settled on
2026-08-17, deleted on 2026-09-17 without an owner record while 193 glosses
gained the particle, and restored on 2026-09-25 after the owner-requested
usage study (hand missals print the particle only under a Latin *O* in their
word-by-word aids).

The register comparison below is kept as a diagnostic, not a gate: one stored
Gospel segment can hold several speakers and addressees, which token strings
cannot tell apart.
"""

from __future__ import annotations

ARCHAIC = {"thee", "thou", "thy", "thine"}
MODERN = {"you", "your", "yours"}


def check(doc: dict, gloss: dict) -> list[str]:
    """One message per vocative whose gloss adds the particle O."""
    errors: list[str] = []
    lang = gloss.get("lang", "?")
    entries = gloss.get("words") or {}
    for segment in doc.get("segments", []):
        for word in segment.get("words") or []:
            if (word.get("morph") or {}).get("case") != "voc":
                continue
            text = (entries.get(word["id"], {}).get("gloss") or "").strip()
            if text.startswith(("O ", "o ")):
                errors.append(
                    f"{doc['id']}:{word['id']} ({word['form']}): the {lang} gloss "
                    f"{text!r} carries the vocative particle, which renders no Latin "
                    f"word — a vocative is glossed bare"
                )
    return errors


def _register(gloss: str) -> set[str]:
    """Which second-person registers a gloss uses, if any."""
    found = set()
    for token in gloss.lower().replace(",", " ").split():
        if token in ARCHAIC:
            found.add("archaic")
        elif token in MODERN:
            found.add("modern")
    return found


def register_diagnostic(doc: dict, gloss: dict) -> list[str]:
    """Segments whose English second person is glossed in both registers.

    Editorial diagnostic only (see the module docstring); not wired into the
    gate."""
    errors: list[str] = []
    if gloss.get("lang") != "en":
        return errors
    entries = gloss.get("words") or {}
    for segment in doc.get("segments", []):
        words = segment.get("words") or []
        registers: set[str] = set()
        for word in words:
            if word["lemma"] not in ("tu", "tuus"):
                continue
            registers |= _register(entries.get(word["id"], {}).get("gloss") or "")
        if len(registers) > 1:
            line = " ".join(w["form"] for w in words)
            errors.append(
                f"{doc['id']}:{segment['id']}: the English second person is glossed in "
                f"both registers inside one segment — {line[:60]!r} — and the register "
                f"follows who is addressed"
            )
    return errors
