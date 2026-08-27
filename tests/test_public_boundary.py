"""A relative documentation reference must open from this repository.

This repository is self-contained: when a comment, a docstring, or an error
message points a reader at `notes/<page>.md`, `reviews/<page>.md`, or
`docs/<page>.md`, that file must exist here. A pointer a reader cannot follow
is worse than none — the first person to trip a check would be told to
consult a page that is not there. The rule is therefore the readable one:
say the thing, or cite a page this repository actually ships.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DOC_REFERENCE = re.compile(r"\b(?:notes|reviews|docs)/[A-Za-z0-9][A-Za-z0-9._-]*\.md\b")


def tracked(root: Path) -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True)
    return [name for name in out.stdout.split("\n") if name]


def dangling_references(root: Path, names: list[str]) -> list[str]:
    found = []
    for name in names:
        try:
            text = (root / name).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binaries: fonts, images
        for number, line in enumerate(text.splitlines(), start=1):
            for reference in DOC_REFERENCE.findall(line):
                if not (root / reference).is_file():
                    found.append(f"{name}:{number}: {reference}")
    return found


def test_every_cited_documentation_page_exists_here():
    found = dangling_references(ROOT, tracked(ROOT))
    assert not found, (
        "these point at documentation a reader of this repository cannot open:\n" + "\n".join(found)
    )


def test_the_gate_can_fail(tmp_path):
    # The example reference is assembled at runtime so this file's own text
    # does not carry a dangling literal for the scan above to trip on.
    reference = "/".join(["notes", "example.md"])
    (tmp_path / "src.py").write_text(f"# see {reference} for the rules\n")
    found = dangling_references(tmp_path, ["src.py"])
    assert found and reference in found[0]
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "example.md").write_text("# rules\n")
    assert dangling_references(tmp_path, ["src.py"]) == []
