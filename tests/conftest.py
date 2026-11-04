"""Whole-book reader inputs shared by artifact contract tests."""

import hashlib
import shutil
import stat
from pathlib import Path

import pytest

from build_reader.emit import emit

CORPUS = Path(__file__).resolve().parent.parent


_TMP_PATH = pytest.StashKey[tuple[Path, tuple[int, int]]]()
_PHASE_PASSED = pytest.StashKey[dict[str, bool]]()


@pytest.fixture
def tmp_path(tmp_path, request):
    """Track the directory actually allocated to this test."""
    identity = tmp_path.stat()
    request.node.stash[_TMP_PATH] = tmp_path, (identity.st_dev, identity.st_ino)
    return tmp_path


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    report = yield
    tracked = item.stash.get(_TMP_PATH, None)
    if tracked is None:
        return report
    phases = item.stash.setdefault(_PHASE_PASSED, {})
    phases[report.when] = report.passed
    if report.when == "teardown" and all(
        phases.get(phase, False) for phase in ("setup", "call", "teardown")
    ):
        path, identity = tracked
        try:
            current = path.lstat()
        except FileNotFoundError:
            return report
        if stat.S_ISDIR(current.st_mode) and (current.st_dev, current.st_ino) == identity:
            try:
                shutil.rmtree(path)
            except FileNotFoundError:
                if path.exists() or path.is_symlink():
                    raise
    return report


def artifact_snapshot(out):
    return {
        path.relative_to(out): hashlib.sha256(path.read_bytes()).digest()
        for path in out.rglob("*.json")
    }


@pytest.fixture(scope="session")
def emitted_book(tmp_path_factory):
    """Emit the actual complete corpus once; consumers must leave it intact."""
    out = tmp_path_factory.mktemp("reader-edition")
    written = emit(CORPUS, out)
    before = artifact_snapshot(out)
    assert before
    yield out, written
    assert artifact_snapshot(out) == before, "a test changed the shared reader edition"


@pytest.fixture
def reader_out(emitted_book):
    """Read-only artifact root; mutations use reader_copy instead."""
    return emitted_book[0]


@pytest.fixture
def reader_copy(emitted_book, tmp_path):
    """A private complete artifact tree for one test's negative controls."""
    out = tmp_path / "reader-copy"
    shutil.copytree(emitted_book[0], out)
    return out
