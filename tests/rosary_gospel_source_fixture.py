"""Exact documentary inverses on historical comparison copies, never native inputs."""

import json
from copy import deepcopy
from pathlib import Path

DATA = json.loads((Path(__file__).parent / "fixtures/rosary-gospel-source.json").read_bytes())


def before_rosary_core(core):
    result = deepcopy(core)
    if result.get("id") == DATA["text"]:
        source = result["editorial"]["source"]
        assert source["method"] == DATA["core_method"]["after"], "exact Rosary source method"
        source["method"] = DATA["core_method"]["before"]
    return result


def before_rosary_registry(registry):
    result = deepcopy(registry)
    for field, identity, expected in (
        ("archives", DATA["archive_id"], DATA["archive"]),
        ("bindings", DATA["binding_id"], DATA["binding"]),
    ):
        assert result[field].get(identity) == expected, "exact Rosary registry addition"
        del result[field][identity]
    return result


def before_rosary_records(value):
    result = deepcopy(value)
    rows = {row["id"]: row for row in DATA["records"]}
    witness_id = next(row["id"] for row in DATA["records"] if row["collection"] == "witnesses")

    def visit(item):
        if isinstance(item, list):
            for child in item:
                visit(child)
        elif isinstance(item, dict):
            # The former identity-only subject had no raw_resolution at all.
            # Check every new field before reversing this exact contract transition.
            if isinstance(item.get("witness"), dict) and item["witness"].get("id") == witness_id:
                assert set(item) == {
                    "contract",
                    "witness",
                    "source_uses",
                    "selected_text",
                    "raw_resolution",
                }, "exact Rosary resolved subject shape"
                assert item["contract"] == "witness-review-2", "exact Rosary resolved contract"
                assert item["raw_resolution"] == DATA["expected_source"], (
                    "complete Rosary resolved source"
                )
                assert set(item["source_uses"]) == {item["witness"]["use"]}, (
                    "exact Rosary source inventory"
                )
                del item["raw_resolution"]
                item["contract"] = "witness-identity-2"
            identity = item.get("id")
            if identity in rows:
                rule = rows[identity]
                before, after = deepcopy(rule["before"]), deepcopy(rule["after"])
                if rule["collection"] == "witnesses" and "review" not in item:
                    del before["review"]
                    del after["review"]
                if rule["collection"] == "collations":
                    selected = item.get("selected_text_sha256")
                    assert selected in {
                        after["selected_text_sha256"],
                        DATA["historical_selected_sha256"],
                    }, "exact Rosary selected subject"
                    before["selected_text_sha256"] = selected
                    after["selected_text_sha256"] = selected
                assert item == after, "exact Rosary source record"
                item.clear()
                item.update(before)
            for child in item.values():
                visit(child)

    visit(result)
    return result


def before_rosary_graph(graph):
    for rule in DATA["records"]:
        matches = [row for row in graph[rule["collection"]] if row["id"] == rule["id"]]
        assert matches == [rule["after"]], "complete Rosary graph record"
    return before_rosary_records(graph)
