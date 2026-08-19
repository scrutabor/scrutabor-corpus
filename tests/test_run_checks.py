"""What the runner says it did, and what it says it did not.

`check_against_history` is an `--all` check: it compares each text against the
version in git, which is the only way to see a renumbering — every id is still
present, each now naming its neighbour. A single-text run cannot answer that
question, and until 2026-08-19 it did not say so, which is worst exactly when
someone runs it: verifying "just this text" after an id edit, and reading a
VERDICT OK as a clean bill for the one failure checks/identity.py calls
unrecoverable.

Run as a subprocess, because what is being tested is what the run PRINTS.
"""

import subprocess
import sys
from pathlib import Path

from run_checks import NOT_COMPARED

CORPUS = Path(__file__).resolve().parent.parent


def run(*args):
    return subprocess.run(
        [sys.executable, "run_checks.py", *args],
        cwd=CORPUS,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_a_single_text_run_says_that_history_was_not_compared():
    done = run("ordinarium.confiteor")
    assert done.returncode == 0
    assert NOT_COMPARED in done.stdout
    assert "run_checks.py --all` is the run that answers it" in done.stdout


def test_the_notice_stands_where_the_all_run_prints_its_own_answer():
    # Both lines open with IDENTITY, so the two runs answer the same question
    # in the same place and one of them answers it with a no.
    assert NOT_COMPARED.startswith("IDENTITY ")


def test_a_bad_text_id_still_fails_rather_than_reassuring_anybody():
    done = run("ordinarium.no-such-text")
    assert done.returncode != 0
