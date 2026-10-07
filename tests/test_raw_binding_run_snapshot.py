"""Witness checks validate the raw registry once per run and still report every witness."""

import json
import shutil
from pathlib import Path

from checks.witness_archive import check as check_archives

CORPUS = Path(__file__).resolve().parent.parent
REGISTRY = "witnesses/raw/bindings.json"


def copy_bound(tmp_path):
    registry = json.loads((CORPUS / REGISTRY).read_text())
    paths = [REGISTRY]
    paths += [item["path"] for item in registry["archives"].values()]
    paths += [item["witness"] for item in registry["bindings"].values()]
    for name in paths:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CORPUS / name, destination)
    return registry


def test_a_corrupt_archive_is_reported_for_every_witness_it_binds(tmp_path):
    registry = copy_bound(tmp_path)
    users: dict[str, set[str]] = {}
    for binding in registry["bindings"].values():
        for item in binding["evidence"]:
            users.setdefault(item["archive"], set()).add(binding["witness"])
    key, witnesses = max(users.items(), key=lambda pair: (len(pair[1]), pair[0]))
    assert len(witnesses) > 1
    archive = tmp_path / registry["archives"][key]["path"]
    archive.write_bytes(archive.read_bytes() + b"\n")
    errors = check_archives(tmp_path)
    flagged = {e.split(": archive ")[0] for e in errors if e.endswith("SHA-256 mismatch")}
    assert flagged == {str(tmp_path / witness) for witness in witnesses}


def test_an_intact_copy_has_no_errors(tmp_path):
    copy_bound(tmp_path)
    assert check_archives(tmp_path) == []
