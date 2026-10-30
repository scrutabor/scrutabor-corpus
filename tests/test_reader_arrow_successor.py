"""The reader-face arrow successor restores exactly its declared strings on a copy.

Each of the 57 bibliography strings holds its replacement in the authored file.
The comparison inverse maps exactly that replacement back to the earlier string,
leaves every other field and every other value untouched, and passes the
predecessor itself through unchanged.
"""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from reader_arrow_successor_fixture import (
    DATA,
    FILES,
    before_arrow_bytes,
    before_arrow_graph,
    before_arrow_language,
    before_arrow_object,
    before_arrow_use,
)

ROOT = Path(__file__).resolve().parents[1]
GRAPH = "bibliography/graph.json"


def current(relative):
    return json.loads((ROOT / relative).read_bytes())


def field(use, path):
    value = use
    for key in path:
        value = value[key]
    return value


def with_field(use, path, value):
    result = deepcopy(use)
    container = result
    for key in path[:-1]:
        container = container[key]
    container[path[-1]] = value
    return result


def uses_by_id(value):
    return {use["id"]: use for use in value["uses"]}


def test_successor_names_fifty_seven_strings_in_three_files():
    assert len(DATA["strings"]) == len({row["use"] for row in DATA["strings"]}) == 57
    assert {relative: len(rows) for relative, rows in FILES.items()} == {
        GRAPH: 24,
        "languages/en/bibliography.json": 19,
        "languages/pl/bibliography.json": 14,
    }
    sections = [row for row in DATA["strings"] if row["field"] == ["locator", "section"]]
    assert len(sections) == 5
    assert all(row["file"] == "languages/en/bibliography.json" for row in sections)
    assert all(row["field"] == ["claim"] for row in DATA["strings"] if row not in sections)


@pytest.mark.parametrize("relative", sorted(FILES))
def test_current_file_holds_every_replacement(relative):
    uses = uses_by_id(current(relative))
    for row in FILES[relative]:
        assert field(uses[row["use"]], row["field"]) == row["after"]


@pytest.mark.parametrize("relative", sorted(FILES))
def test_inverse_restores_only_the_declared_strings(relative):
    actual = current(relative)
    saved = deepcopy(actual)
    previous = before_arrow_object(relative, actual)
    assert actual == saved and previous is not actual
    assert {key: value for key, value in previous.items() if key != "uses"} == {
        key: value for key, value in actual.items() if key != "uses"
    }
    rows = {row["use"]: row for row in FILES[relative]}
    assert [use["id"] for use in previous["uses"]] == [use["id"] for use in actual["uses"]]
    restored = 0
    for old, new in zip(previous["uses"], actual["uses"], strict=True):
        row = rows.get(new["id"])
        if row is None:
            assert old == new
            continue
        assert field(old, row["field"]) == row["before"]
        assert with_field(old, row["field"], row["after"]) == new
        restored += 1
    assert restored == len(rows)
    assert before_arrow_object(relative, previous) is previous


@pytest.mark.parametrize("relative", sorted(FILES))
def test_byte_inverse_matches_the_object_inverse(relative):
    raw = (ROOT / relative).read_bytes()
    previous = before_arrow_bytes(relative, raw)
    assert previous != raw
    assert json.loads(previous) == before_arrow_object(relative, json.loads(raw))
    assert (json.dumps(json.loads(previous), ensure_ascii=False, indent=2) + "\n").encode() == (
        previous
    )
    assert before_arrow_bytes(relative, previous) == previous
    assert before_arrow_bytes(relative, raw + b" ") == raw + b" "
    assert before_arrow_bytes("languages/de/bibliography.json", raw) is raw


def test_graph_and_language_entries_are_the_same_inverse():
    graph = current(GRAPH)
    assert before_arrow_graph(graph) == before_arrow_object(GRAPH, graph)
    text = "ordinarium.qui-pridie"
    records = {
        "uses": [use for use in graph["uses"] if (use.get("address") or {}).get("text") == text],
        "witnesses": [],
    }
    previous = uses_by_id(before_arrow_graph(records))
    assert previous[f"use.{text}.main-ordo-literal.do44667ff"]["claim"] == next(
        row["before"]
        for row in FILES[GRAPH]
        if row["use"] == f"use.{text}.main-ordo-literal.do44667ff"
    )
    for language in ("en", "pl"):
        relative = f"languages/{language}/bibliography.json"
        value = current(relative)
        assert before_arrow_language(language, value) == before_arrow_object(relative, value)
    unrelated = {"uses": [{"id": "use.unrelated", "claim": "x"}]}
    assert before_arrow_object("languages/de/bibliography.json", unrelated) is unrelated
    assert before_arrow_graph(unrelated) is unrelated


@pytest.mark.parametrize("fault", ["changed", "missing-field", "other-id", "predecessor"])
@pytest.mark.parametrize("kind", ["claim", "section"])
def test_any_other_value_reaches_the_older_oracle_unchanged(kind, fault):
    row = next(
        row
        for row in DATA["strings"]
        if row["field"][-1] == ("claim" if kind == "claim" else "section")
    )
    use = deepcopy(uses_by_id(current(row["file"]))[row["use"]])
    assert before_arrow_use(use) == with_field(use, row["field"], row["before"])
    if fault == "changed":
        use = with_field(use, row["field"], row["after"] + " Changed.")
    elif fault == "missing-field":
        container = use
        for key in row["field"][:-1]:
            container = container[key]
        del container[row["field"][-1]]
    elif fault == "other-id":
        use["id"] = "use.unrelated"
    else:
        use = with_field(use, row["field"], row["before"])
    saved = deepcopy(use)
    assert before_arrow_use(use) is use and use == saved
