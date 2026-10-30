"""Reverse exact Dies irae government and onset captions on a comparison copy."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from possessive_sweep_b2_successor_fixture import before_possessive_b2_layer

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads(
    (ROOT / "tests/fixtures/dies-irae-government-successor.json").read_text(encoding="utf-8")
)


def canonical(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def before_dies_irae_government_layer(layer):
    """Accept the complete named successor; never normalize a native input."""
    comparison = deepcopy(layer)
    if layer.get("text") != DATA["text"]:
        return comparison
    comparison = before_possessive_b2_layer(comparison)
    language = layer.get("language")
    require(language in DATA["layers"], "reviewed Dies irae language")
    rule = DATA["layers"][language]
    diagnostic = "reviewed Dies irae whole predecessor layer"
    require(canonical(comparison) == rule["after_canonical_sha256"], diagnostic)
    for operation in reversed(rule["operations"]):
        parent = comparison
        for key in operation["pointer"][:-1]:
            parent = parent[key]
        key = operation["pointer"][-1]
        require((key in parent) == operation["after_exists"], diagnostic)
        if key in parent:
            require(parent[key] == operation["after"], diagnostic)
        if operation["before_exists"]:
            parent[key] = deepcopy(operation["before"])
        else:
            del parent[key]
    require(canonical(comparison) == rule["before_canonical_sha256"], diagnostic)
    return comparison
