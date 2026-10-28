"""One exact documentary inverse, after validating the actual current source."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from build_reader.bibliography_bindings import digest, witness_subject
from build_reader.layers import expand_core
from checks.collate import collate
from checks.raw_binding import resolve_binding

ROOT = Path(__file__).resolve().parents[1]
F = json.loads((ROOT / "tests/fixtures/anne-documentary-source.json").read_bytes())


TARGET = json.loads((ROOT / "tests/fixtures/anne-epistle-constructions.json").read_bytes())
COMPARISON = json.loads(
    (ROOT / "tests/fixtures/documentary-successor-comparisons.json").read_bytes()
)


def target_core(value, diagnostic="exact Anne complete core predecessor"):
    """The complete joint current object is guarded before the method-only inverse."""
    assert value.get("id") == F["text"], diagnostic
    assert value.get("editorial", {}).get("source", {}).get("method") == F["method"]["after"], (
        diagnostic
    )
    assert digest(value) == COMPARISON["anne_core_sha256"], diagnostic
    result = deepcopy(value)
    result["editorial"]["source"]["method"] = F["method"]["before"]
    assert digest(result) == TARGET["core_after_sha256"], diagnostic
    return result


def target_history(value, diagnostic="exact Anne complete core predecessor"):
    result = target_core(value, diagnostic)
    for operation in reversed(TARGET["core_operations"]):
        parts = operation["pointer"].split("/")[1:]
        parent = result
        for part in parts[:-1]:
            parent = parent[int(part)] if isinstance(parent, list) else parent[part]
        key = int(parts[-1]) if isinstance(parent, list) else parts[-1]
        before, after = operation["before"], operation["after"]
        assert after["exists"] and parent[key] == after["value"], diagnostic
        if before["exists"]:
            parent[key] = deepcopy(before["value"])
        else:
            del parent[key]
    assert digest(result) == TARGET["core_before_sha256"], diagnostic
    return result


def record(graph, field, identity):
    matches = [row for row in graph[field] if row["id"] == identity]
    assert len(matches) == 1, "single Anne documentary record"
    return matches[0]


def current(root=ROOT, graph=None):
    """Pass real current inputs to the native APIs, never a predecessor copy."""
    if graph is None:
        graph = json.loads((root / "bibliography/graph.json").read_bytes())
    for field, rule in F["records"].items():
        assert record(graph, field, rule["after"]["id"]) == rule["after"], (
            "complete current Anne documentary record"
        )
    registry = json.loads((root / "witnesses/raw/bindings.json").read_bytes())
    assert registry["archives"].get(F["archive_id"]) == F["archive"], (
        "complete current Anne archive"
    )
    assert registry["bindings"].get(F["binding_id"]) == F["binding"], (
        "complete current Anne binding"
    )
    actual = resolve_binding(root / F["witness"], root)
    assert actual is not None and actual.text == F["literal"]
    assert actual.source == F["expected_source"], "complete Anne raw1 payload"
    core = json.loads((root / F["core"]).read_bytes())
    assert digest(target_history(core)["segments"]) == F["core_segments_sha256"], (
        "unchanged Anne selected words and analyses"
    )
    assert core["editorial"]["source"]["method"] == F["method"]["after"]
    app = json.loads((root / F["apparatus"]).read_bytes())
    assert app == F["new_apparatus"], "complete Anne literal apparatus"
    assert hashlib.sha256((root / F["mr"]).read_bytes()).hexdigest() == F["mr_sha256"]
    witness = record(graph, "witnesses", F["records"]["witnesses"]["after"]["id"])
    subject = witness_subject(root, witness, graph, core)
    assert subject["contract"] == "witness-review-2"
    assert subject["raw_resolution"] == F["expected_source"]
    assert set(subject["source_uses"]) == {witness["use"]}
    errors, warnings, stats = collate(expand_core(core), root / "witnesses" / F["text"])
    assert errors == warnings == []
    assert stats["words"] == 229 and stats["witnesses"] == 2
    assert stats["orthographic"] == 13 and stats["corrigenda"] == 0
    return actual, subject


def before_anne_graph(value):
    """Invert three whole guarded records on a copy, only after actual validation."""
    current()
    result = deepcopy(value)
    for field, rule in F["records"].items():
        actual = record(result, field, rule["after"]["id"])
        assert actual == rule["after"], "exact Anne graph successor"
        actual.clear()
        actual.update(deepcopy(rule["before"]))
    return result


def before_anne_registry(value):
    """Remove only the two complete additions from a historical comparison copy."""
    current()
    result = deepcopy(value)
    for field, key, expected in (
        ("archives", F["archive_id"], F["archive"]),
        ("bindings", F["binding_id"], F["binding"]),
    ):
        assert result[field].get(key) == expected, "exact Anne registry successor"
        del result[field][key]
    return result


def before_anne_core(value):
    """Exact joint history copy; actual native callers keep the current object."""
    current()
    assert value.get("editorial", {}).get("source", {}).get("method") == F["method"]["after"], (
        "exact Anne current documentary method"
    )
    return target_history(value)


def before_anne_records(value):
    """Undo exact Anne records/subjects on a copy, retaining all unrelated records."""
    result = deepcopy(value)
    rules = {rule["after"]["id"]: rule for rule in F["records"].values()}
    witness = F["records"]["witnesses"]
    use = F["records"]["uses"]

    def visit(item):
        if isinstance(item, list):
            for child in item:
                visit(child)
            return
        if not isinstance(item, dict):
            return
        if (
            isinstance(item.get("witness"), dict)
            and item["witness"].get("id") == witness["after"]["id"]
        ):
            assert set(item) == {
                "contract",
                "witness",
                "source_uses",
                "selected_text",
                "raw_resolution",
            }, "complete current Anne witness subject"
            assert item["contract"] == "witness-review-2"
            assert item["witness"] == {k: v for k, v in witness["after"].items() if k != "review"}
            assert item["source_uses"] == {use["after"]["id"]: use["after"]}
            assert item["raw_resolution"] == F["expected_source"]
            assert (
                digest(item["selected_text"])
                == F["records"]["collations"]["after"]["selected_text_sha256"]
            )
            item["contract"] = "witness-identity-2"
            del item["raw_resolution"]
        if item.get("id") in rules:
            rule = rules[item["id"]]
            before, after = deepcopy(rule["before"]), deepcopy(rule["after"])
            if "review" in after and "review" not in item:
                del before["review"]
                del after["review"]
            assert item == after, "exact Anne graph successor"
            item.clear()
            item.update(before)
        for child in item.values():
            visit(child)

    visit(result)
    return result
