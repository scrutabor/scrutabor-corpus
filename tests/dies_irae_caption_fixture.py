"""Undo only the exact current caption successor on a comparison copy."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads(
    (ROOT / "tests/fixtures/dies-irae-contextual-captions.json").read_text(encoding="utf-8")
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def canonical(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def parent_at(value, pointer):
    for key in pointer[:-1]:
        value = value[key]
    return value, pointer[-1]


def restore_dies_irae_layer(layer):
    comparison = deepcopy(layer)
    if layer.get("text") != DATA["text"]:
        return comparison
    language = layer.get("language")
    require(language in DATA["before_canonical"], "reviewed Dies irae language")
    for operation in reversed(DATA["operations"]):
        if operation["language"] != language:
            continue
        parent, key = parent_at(comparison, operation["pointer"])
        require(
            (key in parent) == operation["after_exists"],
            "reviewed Dies irae caption field presence",
        )
        if key in parent:
            require(parent[key] == operation["after"], "reviewed Dies irae caption field value")
        if operation["before_exists"]:
            parent[key] = deepcopy(operation["before"])
        else:
            del parent[key]
    require(
        canonical(comparison) == DATA["before_canonical"][language],
        "reviewed Dies irae whole predecessor layer",
    )
    return comparison
