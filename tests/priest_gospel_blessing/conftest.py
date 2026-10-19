"""Focused slices of genuine assembled files, never authored substitute readings."""

import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TEXT = "ordinarium.iube-domine-benedicere"
CORE = "texts/ordinarium/iube-domine-benedicere.json"
WITNESSES = f"witnesses/{TEXT}"
RAW = "witnesses/raw/missa-44667ff/Ordo/Ordo.txt"


@pytest.fixture
def blessing_corpus(tmp_path):
    def read(relative):
        return json.loads((ROOT / relative).read_text(encoding="utf-8"))

    def write(relative, value):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def copy(relative):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)

    # Missing new canonical files fail here. No fallback to detached proposals.
    for relative in (
        CORE,
        f"{WITNESSES}/mr.txt",
        f"{WITNESSES}/do.txt",
        f"{WITNESSES}/apparatus.json",
        RAW,
        "witnesses/ordinarium.munda-cor-meum/do.txt",
    ):
        copy(relative)
    registry = read("witnesses/raw/bindings.json")
    registry["archives"] = {"missa-ordo-44667ff": registry["archives"]["missa-ordo-44667ff"]}
    registry["bindings"] = {
        key: registry["bindings"][key]
        for key in ("munda-cor-meum-priest", "iube-domine-benedicere-priest")
    }
    write("witnesses/raw/bindings.json", registry)
    graph = read("bibliography/graph.json")
    # Keep real identities/migration decisions; scope only the evidence records.
    for field in ("uses", "witnesses", "collations"):
        graph[field] = [
            row
            for row in graph[field]
            if row.get("text", row.get("address", {}).get("text")) == TEXT
        ]
    write("bibliography/graph.json", graph)
    for language in ("pl", "en"):
        base = f"languages/{language}"
        copy(f"{base}/{CORE}")
        for name in ("bibliography.json", "lexicon.json", "translation-basis.json"):
            copy(f"{base}/{name}")
        manifest = read(f"{base}/manifest.json")
        assert manifest["texts"].count(TEXT) == 1
        manifest["texts"] = [TEXT]
        manifest["titles"] = {TEXT: manifest["titles"][TEXT]}
        write(f"{base}/manifest.json", manifest)
        provenance = read(f"{base}/translation-provenance.json")
        provenance["sites"] = [row for row in provenance["sites"] if row["text"] == TEXT]
        assert len(provenance["sites"]) == 3
        write(f"{base}/translation-provenance.json", provenance)
    return tmp_path
