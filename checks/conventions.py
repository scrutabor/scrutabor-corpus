"""Editorial diagnostics for contextual gloss conventions.

The corpus formerly treated a bare vocative and token-local capitalization as
universal rules.  A contextual reading aid must instead be allowed to say
``O Lord`` and to follow the devotional phrase's capitalization. Register
comparison is intentionally not part of the corpus gate: one stored Gospel
segment can contain several quoted speakers and addressees, and those
relationships cannot be inferred from token strings alone.
"""

from __future__ import annotations

ARCHAIC = {"thee", "thou", "thy", "thine"}
MODERN = {"you", "your", "yours"}


def _register(gloss: str) -> set[str]:
    """Which second-person registers a gloss uses, if any."""
    found = set()
    for token in gloss.lower().replace(",", " ").split():
        if token in ARCHAIC:
            found.add("archaic")
        elif token in MODERN:
            found.add("modern")
    return found


def check(doc: dict, gloss: dict) -> list[str]:
    """One message per gloss that breaks a settled convention."""
    errors: list[str] = []
    lang = gloss.get("lang", "?")
    entries = gloss.get("words") or {}

    for segment in doc.get("segments", []):
        words = segment.get("words") or []
        # The register follows who is addressed, so one segment speaks
        # to one person and cannot hold both registers. Checked per segment
        # rather than per text because a text may address God in one line and a
        # man in the next, which the Confiteor and the kiss of peace both do.
        if lang == "en":
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
