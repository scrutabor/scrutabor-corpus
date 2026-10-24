"""Finite Michael successors consumed by older, immutable baseline tests."""

import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads(
    (ROOT / "tests/fixtures/michael-secret-successor.json").read_text(encoding="utf-8")
)
TEXT = FIXTURE["text"]


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def predecessor_documents(documents):
    """Undo only the authored successor before an older exact inverse runs."""
    required = {operation["path"] for operation in FIXTURE["document_operations"]}
    require(required <= set(documents), "Michael successor document set")
    result = deepcopy(documents)
    for operation in reversed(FIXTURE["document_operations"]):
        parent = result[operation["path"]]
        parts = operation["pointer"].split("/")[1:]
        for part in parts[:-1]:
            parent = parent[part]
        key = parts[-1]
        require((key in parent) == operation["after"]["exists"], "Michael successor field presence")
        if key in parent:
            require(parent[key] == operation["after"]["value"], "Michael successor field value")
        if operation["before"]["exists"]:
            parent[key] = deepcopy(operation["before"]["value"])
        else:
            del parent[key]
    return result


def control_expectation(row):
    if (row["text"], row["language"], row["segment"]) != (TEXT, "pl", "s01"):
        return row
    require(row == FIXTURE["previous_polish_control"], "Michael historical control identity")
    result = deepcopy(row)
    result["class"] = "reviewed Michael AA successor"
    result["direct"] = {}
    result["groups"] = [deepcopy(FIXTURE["groups"]["pl"][0])]
    return result


def ledger_expectation(row):
    if row["site"] != f"{TEXT}.s01.en":
        return row
    require(row == FIXTURE["previous_interrupted_ledger"], "Michael historical ledger identity")
    return {**row, "target_sha256": FIXTURE["ledger_after"]["en"][0]["target_sha256"]}


def explanation_expectation(row):
    if row[1] != TEXT:
        return None
    normalized = [row[0], row[1], row[2], list(row[3]), row[4]]
    require(
        normalized == FIXTURE["previous_polish_explanation_row"],
        "Michael historical explanation identity",
    )
    return {
        "requirement": {},
        "pl": FIXTURE["explanations"]["pl"],
        "en": FIXTURE["explanations"]["en"],
    }
