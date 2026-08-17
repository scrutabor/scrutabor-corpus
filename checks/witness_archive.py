"""Every witness must be findable in the archive it names.

A witness file is a transcription: a text this edition collated against, cut
from a source and stored beside a byte-level archive of that source. The
`path:` header names where it came from upstream, and the `fetched:` header
names the archived copy in `witnesses/raw/`.

Upstream line numbers ROT — the Divinum Officium project's `master` has already
moved under the recorded numbers, so a line that read 278 now reads 277. The
archive does not move, because it is in this repository. So the durable check
is not "is the line number right" but "does this transcription actually appear
in the archive it claims".

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
from pathlib import Path

RAW_REF = re.compile(r"\.\./raw/(\S+?\.txt)")
TOLERANCE = 0.02


def normalise(text: str) -> str:
    text = re.sub(r"\([^()]*\)", " ", text)
    text = re.sub(r"\s*\+\s*", "", text)
    text = re.sub(r"[^0-9A-Za-zÀ-ÿæœÆŒ ]", " ", text)
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
    """One message per witness whose text is not in the archive it names."""
    raw_dir = root / "witnesses" / "raw"
    archives = {p.name: normalise(p.read_text(errors="replace")) for p in raw_dir.glob("*.txt")}
    errors: list[str] = []
    for path in sorted((root / "witnesses").rglob("*.txt")):
        if path.parent.name == "raw":
            continue
        head = "\n".join(path.read_text(errors="replace").splitlines()[:20])
        named = RAW_REF.findall(head)
        if not named:
            continue
        missing = [n for n in named if n not in archives]
        if missing:
            errors.append(f"{path}: names archive(s) that do not exist: {missing}")
            continue
        pool = " ".join(archives[n] for n in named)
        words = body_of(path).split()
        if not words:
            continue
        absent = [w for w in words if w not in pool]
        if len(absent) / len(words) > TOLERANCE:
            errors.append(
                f"{path}: {len(absent)} of {len(words)} words are not in the archive it "
                f"names ({', '.join(named)}) — e.g. {absent[:5]}"
            )
    return errors
