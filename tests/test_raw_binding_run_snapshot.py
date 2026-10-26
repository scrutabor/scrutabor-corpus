"""Witness checks validate the raw registry once per run and still report every witness."""

import json
import shutil
from pathlib import Path

import pytest

from checks.witness_archive import check as check_archives

CORPUS = Path(__file__).resolve().parent.parent
REGISTRY = "witnesses/raw/bindings.json"
LATERAN = "witnesses/proprium.dedicatio-archibasilicae-sanctissimi-salvatoris-postcommunio/do.txt"


# Independent archive inventory of the two closed Mass/Common chains.
MASS_SECRETS = {
    "secret-maternitas-do44667ff": (
        "do-sancti-10-11",
        "common-c10",
        "common-c11",
        "prayers",
        "missa-ordo-44667ff",
    ),
    "secret-omnium-sanctorum-do44667ff": (
        "all-saints",
        "common-c3a",
        "prayers",
        "missa-ordo-44667ff",
    ),
}
SECRET_ARCHIVES = sorted({key for keys in MASS_SECRETS.values() for key in keys})


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


@pytest.mark.parametrize(
    "selection", ["most-shared", "inline-rubric", "literal-common", *SECRET_ARCHIVES]
)
def test_a_corrupt_archive_is_reported_for_every_witness_it_binds(tmp_path, selection):
    registry = copy_bound(tmp_path)
    assert check_archives(tmp_path) == []
    users: dict[str, set[str]] = {}
    inline_archives = set()
    common_archives = set()
    for identity, binding in registry["bindings"].items():
        if binding.get("contract") == "raw-reading-6":
            evidence = [binding["template"], binding["variant"]]
        elif binding.get("contract") == "raw-reading-7":
            evidence = [binding]
            inline_archives.add(binding["archive"])
        elif binding.get("contract") == "raw-reading-8":
            evidence = [binding["selection"], binding["body"], binding["conclusion"]]
            common_archives.add(binding["body"]["archive"])
        elif binding.get("contract") == "raw-reading-9":
            evidence = [{"archive": key} for key in MASS_SECRETS[identity]]
        else:
            evidence = binding["evidence"]
        for item in evidence:
            users.setdefault(item["archive"], set()).add(binding["witness"])
    if selection == "inline-rubric":
        (key,) = inline_archives
        witnesses = users[key]
        assert "witnesses/ordinarium.aufer-a-nobis/do.txt" in witnesses
        assert len(witnesses) > 1
    elif selection == "literal-common":
        # The Common archive has one user; its feast and Mass archives are shared.
        (key,) = common_archives
        witnesses = users[key]
        assert key == "common-c8" and witnesses == {LATERAN}
        assert LATERAN in users["do-sancti-11-09"] and LATERAN in users["prayers"]
        assert len(users["prayers"]) > 1
    elif selection in SECRET_ARCHIVES:
        key = selection
        witnesses = users[key]
        expected_secrets = {
            registry["bindings"][identity]["witness"]
            for identity, keys in MASS_SECRETS.items()
            if key in keys
        }
        assert expected_secrets and expected_secrets <= witnesses
    else:
        key, witnesses = max(users.items(), key=lambda pair: (len(pair[1]), pair[0]))
        assert len(witnesses) > 1
    archive = tmp_path / registry["archives"][key]["path"]
    original = archive.read_bytes()
    try:
        archive.write_bytes(original + b"\n")
        errors = check_archives(tmp_path)
        flagged = {e.split(": archive ")[0] for e in errors if e.endswith("SHA-256 mismatch")}
        assert flagged == {str(tmp_path / witness) for witness in witnesses}
        assert len(errors) == len(witnesses)
    finally:
        archive.write_bytes(original)
    assert check_archives(tmp_path) == []


def test_an_intact_copy_has_no_errors(tmp_path):
    copy_bound(tmp_path)
    assert check_archives(tmp_path) == []
