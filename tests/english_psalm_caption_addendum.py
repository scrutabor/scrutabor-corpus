"""Exact Psalm caption additions before the earlier short-possessive inverse."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from build_reader.bibliography_bindings import digest

DATA = json.loads(
    (Path(__file__).parent / "fixtures/english-psalm-caption-addendum.json").read_bytes()
)


def require(condition, diagnostic):
    if not condition:
        raise AssertionError(diagnostic)


def reverse_operations(value, diagnostic):
    result = deepcopy(value)
    for operation in reversed(DATA["operations"]):
        parent = result
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
    return result


def before_psalm_caption_layer(relative, value, diagnostic):
    if relative != DATA["relative"]:
        return value
    require(digest(value) == DATA["after_canonical_sha256"], diagnostic)
    result = reverse_operations(value, diagnostic)
    require(digest(result) == DATA["before_canonical_sha256"], diagnostic)
    return result


def before_psalm_caption_frame(relative, value, project, diagnostic):
    """Keep actual unrelated prose faults for the original prose oracle."""
    if relative != DATA["relative"]:
        return value
    require(digest(project(value)) == DATA["after_caption_sha256"], diagnostic)
    result = reverse_operations(value, diagnostic)
    require(digest(project(result)) == DATA["before_caption_sha256"], diagnostic)
    return result


def before_psalm_caption_bytes(relative, raw, diagnostic):
    if relative != DATA["relative"]:
        return raw
    require(hashlib.sha256(raw).hexdigest() == DATA["after_raw_sha256"], diagnostic)
    result = raw
    for operation in reversed(DATA["raw_operations"]):
        after, before = operation["after"].encode(), operation["before"].encode()
        require(result.count(after) == 1, diagnostic)
        result = result.replace(after, before, 1)
    require(hashlib.sha256(result).hexdigest() == DATA["before_raw_sha256"], diagnostic)
    return result
