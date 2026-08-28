"""Corpus-wide validation for the normalized bibliography and evidence graph."""

from pathlib import Path

from build_reader.bibliography import validate


def check(corpus: Path) -> list[str]:
    return validate(corpus)
