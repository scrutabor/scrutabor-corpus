"""The reader edition's bibliography strings stay inside what the reading face sets.

The reading face carries no glyph for U+2192 (RIGHTWARDS ARROW), so a locator
label or claim that writes one falls back to another face on the Bibliography
page, and every claim travels in the served evidence. The guard scans every
key and string the reader edition publishes under ``bibliography/`` and
``languages/<lang>/bibliography/``, and the authored graph and language
bibliographies it is built from. The negative controls show that it finds an
arrow in an emitted claim, an emitted locator label and an authored use.
"""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from reader_arrow_successor_fixture import DATA

ROOT = Path(__file__).resolve().parents[1]
ARROW = "\u2192"
SOURCES = (
    "bibliography/graph.json",
    "languages/en/bibliography.json",
    "languages/pl/bibliography.json",
)
LETTERS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")


def arrow_sites(node, path=()):
    """Every key or string value that contains U+2192, with its JSON path."""
    if isinstance(node, dict):
        for key, value in node.items():
            if ARROW in key:
                yield (*path, key)
            yield from arrow_sites(value, (*path, key))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from arrow_sites(value, (*path, index))
    elif isinstance(node, str) and ARROW in node:
        yield path


def evidence_files(out):
    return [
        *sorted((out / "bibliography").rglob("*.json")),
        *sorted(out.glob("languages/*/bibliography/**/*.json")),
    ]


def reader_arrow_sites(out):
    return [
        (path.relative_to(out).as_posix(), site)
        for path in evidence_files(out)
        for site in arrow_sites(json.loads(path.read_text(encoding="utf-8")))
    ]


def published_entries(out):
    """Use id -> (locator, claim) for every entry of every emitted text slice."""
    entries = {}
    for path in evidence_files(out):
        if "/texts/" not in path.as_posix():
            continue
        for group in json.loads(path.read_text(encoding="utf-8"))["source_groups"]:
            for entry in group["entries"]:
                assert entry["id"] not in entries
                entries[entry["id"]] = (group["locator"], entry["claim"])
    return entries


def test_no_reader_bibliography_string_uses_the_arrow(reader_out):
    files = evidence_files(reader_out)
    assert {"bibliography/catalog.json", "bibliography/index.json"} <= {
        path.relative_to(reader_out).as_posix() for path in files
    }
    assert len(files) > 1000
    assert reader_arrow_sites(reader_out) == []


def test_every_replaced_string_is_published_as_replaced(reader_out):
    entries = published_entries(reader_out)
    for row in DATA["strings"]:
        locator, claim = entries[row["use"]]
        value = claim if row["field"] == ["claim"] else locator[row["field"][1]]
        assert value == row["after"]


def test_the_authored_bibliography_has_no_arrow():
    for relative in SOURCES:
        assert list(arrow_sites(json.loads((ROOT / relative).read_bytes()))) == []


def test_each_replacement_introduces_only_letters_commas_and_spaces():
    rows = DATA["strings"]
    assert len({(row["file"], row["use"], tuple(row["field"])) for row in rows}) == 57
    assert sorted({row["file"] for row in rows}) == sorted(SOURCES)
    for row in rows:
        assert ARROW in row["before"] and ARROW not in row["after"]
        assert set(row["after"]) - set(row["before"]) <= LETTERS | {",", " "}


@pytest.mark.parametrize("field", ["claim", "section"])
def test_guard_finds_an_arrow_in_an_emitted_string(reader_copy, field):
    assert reader_arrow_sites(reader_copy) == []
    if field == "claim":
        relative = "bibliography/texts/orationes/cor-iesu.json"
        path = reader_copy / relative
        data = json.loads(path.read_text(encoding="utf-8"))
        data["source_groups"][0]["entries"][0]["claim"] += " (410 \u2192 411)"
        site = ("source_groups", 0, "entries", 0, "claim")
    else:
        relative = (
            "languages/en/bibliography/texts/proprium/dominica-iv-in-quadragesima-introitus.json"
        )
        path = reader_copy / relative
        data = json.loads(path.read_text(encoding="utf-8"))
        data["source_groups"][-1]["locator"]["section"] += "; shall \u2192 will"
        site = ("source_groups", len(data["source_groups"]) - 1, "locator", "section")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    assert reader_arrow_sites(reader_copy) == [(relative, site)]


@pytest.mark.parametrize("relative", SOURCES)
def test_guard_finds_an_arrow_in_an_authored_use(relative):
    value = json.loads((ROOT / relative).read_bytes())
    changed = deepcopy(value)
    changed["uses"][0]["claim"] = changed["uses"][0]["claim"] + " \u2192"
    assert list(arrow_sites(value)) == []
    assert list(arrow_sites(changed)) == [("uses", 0, "claim")]
