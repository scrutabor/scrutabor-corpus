"""Every word of an archive-bound witness must occur in the named archive.

A witness file is a transcription: a text this edition collated against, cut
from a source and stored beside a byte-level archive of that source. The
`path:` header names where it came from upstream, and the `fetched:` header
names the archived copy in `witnesses/raw/`.

Upstream line numbers ROT — the Divinum Officium project's `master` has already
moved under the recorded numbers, so a line that read 278 now reads 277. The
archive does not move, because it is in this repository. So the durable check
is not "is the line number right" but "does this transcription actually appear
in the archive it claims". This is a zero-tolerance whole-token vocabulary check,
not proof of word order, multiplicity, recension, or independent transcription.
Witnesses with no local raw reference are outside this check's coverage.

That check found one real gap: the Communicántes is cut from two files, its
`path:` said so, and its `fetched:` named one archive, so a reader following
the archive reference found half the prayer.

Two things must be normalised before comparing, and both are documented in the
witness headers themselves: the inline parenthetical rubrics are stripped when
a witness is cut, and the source prints the cross INSIDE a word (`bene + dícas`),
which a naive tokeniser splits in two.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from .transcription import OPTIONAL_ALLELUIA, seasonal_mode

RAW_REF = re.compile(r"(?:\.\./raw/|witnesses/raw/)(\S+?\.txt)")


def normalise(text: str, *, join_crosses: bool = True, seasonal_alleluia: str = "omit") -> str:
    text = unicodedata.normalize("NFC", text)
    if seasonal_alleluia == "include":
        text = OPTIONAL_ALLELUIA.sub(r"\1", text)
    text = re.sub(r"\([^()]*\)", " ", text)
    text = re.sub(r"\s*\+\s*", "" if join_crosses else " ", text)
    text = "".join(char if char.isalnum() else " " for char in text)
    return re.sub(r"\s+", " ", text).lower().strip()


def body_of(path: Path) -> str:
    return normalise(
        " ".join(
            line
            for line in path.read_text(errors="replace").splitlines()
            if not line.startswith("#")
        )
    )


def check(root: Path) -> list[str]:
    """One message per bound witness with missing archives or unattested words."""
    raw_dir = root / "witnesses" / "raw"
    archives: dict[str, dict[str, set[str]]] = {}
    for path in raw_dir.glob("*.txt"):
        text = path.read_text(encoding="utf-8")
        # The cross can split a word (bene + dícas) or separate whole words
        # (Hóstiam + puram). Neither spelling may disappear from the pool.
        archives[path.name] = {
            mode: set(normalise(text, seasonal_alleluia=mode).split())
            | set(normalise(text, join_crosses=False, seasonal_alleluia=mode).split())
            for mode in ("include", "omit")
        }
    errors: list[str] = []
    for path in sorted((root / "witnesses").rglob("*.txt")):
        if path.parent.name == "raw":
            continue
        head = "\n".join(
            line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("#")
        )
        named = list(dict.fromkeys(RAW_REF.findall(head)))
        if not named:
            continue
        missing = [n for n in named if n not in archives]
        if missing:
            errors.append(f"{path}: names archive(s) that do not exist: {missing}")
            continue
        try:
            mode = seasonal_mode(head)
        except ValueError as error:
            errors.append(f"{path}: {error}")
            continue
        pool = set().union(*(archives[n][mode] for n in named))
        words = body_of(path).split()
        if not words:
            errors.append(f"{path}: archive-bound witness has no words to check")
            continue
        absent = [w for w in words if w not in pool]
        if absent:
            errors.append(
                f"{path}: {len(absent)} of {len(words)} words are not in the archive it "
                f"names ({', '.join(named)}) — e.g. {absent[:5]}"
            )
    return errors
