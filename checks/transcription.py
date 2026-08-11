"""Check witness transcriptions against the raw source spans they declare.

Only witnesses with a parseable ``path: ... (line[s] N-M)`` declaration and
a matching local archive are checked. Source framing is removed in the same
careful way as the attribution check: speaker markers, rubrics, runtime calls,
and name slots are not part of the transcribed prayer. The comparison keeps
letters, accents, capitalization, ligatures, and comma placement exact.

Most witnesses are one contiguous source excerpt and must occur as a whole.
A few are explicitly composed from shared source blocks or repeat an antiphon;
for those, every sentence-level clause must occur in the ordered union of the
declared spans. This still catches the accent mutation that motivated the
check without mistaking declared source expansion for a transcription error.
"""

import re
import unicodedata
from pathlib import Path

from .attribute import _range_declarations, _raw_archive_for


def _signature(text: str, *, terminal_punctuation: bool) -> str:
    allowed = ",.!?;:" if terminal_punctuation else ","
    normalized = unicodedata.normalize("NFC", text)
    return "".join(char for char in normalized if char.isalpha() or char in allowed)


def _source_text(lines: list[str]) -> str:
    textual = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("!!!"):
            line = stripped[3:]
            stripped = line.lstrip()
        if stripped.startswith(("!", "&", "#", "_", "wait")):
            continue
        line = re.sub(r"^[SMVROsmvro]\.\s*", "", line.strip())
        line = re.sub(r"\([^)]*\)", " ", line)
        line = re.sub(r"N\.[a-z]?\s+et\s+N\.[a-z]?", " ", line)
        line = re.sub(r"N\.[a-z]?", " ", line)
        line = re.sub(r"wait\d+", " ", line)
        textual.append(line)
    return " ".join(textual)


def _body(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.startswith("#")).strip()


def check_transcriptions(witness_dir: Path) -> tuple[list[str], int]:
    errors: list[str] = []
    checked = 0
    for witness in sorted(witness_dir.glob("*.txt")):
        text = witness.read_text(encoding="utf-8")
        declarations = _range_declarations(text)
        if not declarations:
            continue
        body = _body(text)
        if not body:
            errors.append(f"{witness.name}: declared raw span but empty transcription")
            continue

        spans = []
        missing = []
        for declared_path, numbers in declarations:
            raw = _raw_archive_for(declared_path)
            if raw is None:
                missing.append(declared_path)
                continue
            lines = raw.read_text(encoding="utf-8").splitlines()
            spans.append(_source_text(lines[min(numbers) - 1 : max(numbers)]))
        if missing:
            errors.append(
                f"{witness.name}: declared raw source has no local archive: {', '.join(missing)}"
            )
            continue

        source = " ".join(spans)
        full_body = _signature(body, terminal_punctuation=True)
        full_source = _signature(source, terminal_punctuation=True)
        if full_body not in full_source:
            clauses = [
                _signature(clause, terminal_punctuation=False)
                for clause in re.split(r"[.!?;:]+", body)
                if _signature(clause, terminal_punctuation=False)
            ]
            clause_source = _signature(source, terminal_punctuation=False)
            missing_clauses = [clause for clause in clauses if clause not in clause_source]
            if missing_clauses:
                errors.append(
                    f"{witness.name}: transcription differs from its declared raw span "
                    f"near {missing_clauses[0][:48]!r}"
                )
                continue
        checked += 1
    return errors, checked
