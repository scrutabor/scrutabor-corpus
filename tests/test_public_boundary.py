"""Nothing here may point at a document only the authors can open.

This repository is public. The project's working notes are not: the backlog,
the review playbook, the quality taxonomy and the conventions live in a private
workbench, and a reader who follows `notes/quality.md` from a file here lands
nowhere. Worse, three of the pointers were in ERROR MESSAGES, so the first
person to trip a check would be told to consult a file that does not exist.

An external review found sixteen of these across both public repositories on
2026-08-19, and a re-review found three more that the FIRST VERSION OF THIS
GATE could not see: it matched `BACKLOG.md` with the extension, and the
survivors wrote the bare word — "the enum the BACKLOG said was still ahead",
"19 stale ranges (BACKLOG)", "recorded in the backlog". A gate that certifies
a boundary it cannot see past is worse than none, so the pattern now takes the
word under any casing.

The fix in every case was to say the thing rather than to cite it. A rule worth
enforcing in code is worth stating in the code.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The private workbench's own documents, by the names they are cited under.
PRIVATE = re.compile(
    r"""(?:
        reviews/[A-Z][A-Z0-9-]*\.md   # PLAYBOOK, OWNER-QUEUE, CAMPAIGN…
      | notes/[a-z-]+\.md             # quality, conventions, decisions…
      | \bbacklog\b                 # the tracker, under any casing
      | \bplaybook\b
      | \bowner-queue\b
      | scrutabor-workbench
    )""",
    re.VERBOSE | re.IGNORECASE,
)

# This file names them in order to forbid them.
EXEMPT = {"tests/test_public_boundary.py"}


def tracked() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True)
    return [name for name in out.stdout.split("\n") if name and name not in EXEMPT]


def test_no_public_file_cites_a_private_document():
    found = []
    for name in tracked():
        path = ROOT / name
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binaries: fonts, images
        for number, line in enumerate(text.splitlines(), start=1):
            if PRIVATE.search(line):
                found.append(f"{name}:{number}: {line.strip()[:90]}")
    assert not found, (
        "these point at documents a reader of this repository cannot open:\n" + "\n".join(found)
    )
