"""Emit the reader edition, and refuse to pass if it lost anything.

    python build.py            emit into build/ and verify
    python build.py --check    emit into a scratch directory and verify only

The verdict names its subject the way run_checks.py does: what was written,
how big it is, and whether every word came back.
"""

import shutil
import sys
import tempfile
from pathlib import Path

from build_reader.emit import emit, verify

HERE = Path(__file__).resolve().parent


def main(check_only: bool) -> int:
    out = Path(tempfile.mkdtemp()) / "build" if check_only else HERE / "build"
    if not check_only:
        shutil.rmtree(out, ignore_errors=True)
    written = emit(HERE, out)
    errors = verify(HERE, out)
    for message in errors:
        print(f"ERROR: {message}")
    # The authored book is the neutral core plus every independently
    # publishable language layer. Measuring only one side would flatter the
    # reader-edition ratio.
    source = sum(p.stat().st_size for p in HERE.glob("texts/*/*.json")) + sum(
        p.stat().st_size for p in HERE.glob("languages/*/texts/*/*.json")
    )
    subject = (
        f"texts={written['texts']} language_texts={written['language_texts']} "
        f"bytes={written['bytes']} "
        f"source={source} ratio={written['bytes'] / source:.2f}"
    )
    if check_only:
        shutil.rmtree(out.parent, ignore_errors=True)
    if errors:
        print(f"READER FAIL {subject} errors={len(errors)}")
        return 1
    print(f"READER OK {subject} errors=0")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
