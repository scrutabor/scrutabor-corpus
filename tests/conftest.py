"""Whole-book reader inputs shared by artifact contract tests."""

import hashlib
import shutil
from pathlib import Path

import pytest

from build_reader.emit import emit

CORPUS = Path(__file__).resolve().parent.parent


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
