"""Finite English caption successors, reversed only for historical comparisons."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from english_psalm_caption_addendum import (
    before_psalm_caption_bytes,
    before_psalm_caption_frame,
    before_psalm_caption_layer,
)

from build_reader.bibliography_bindings import digest

DATA = json.loads(
    (Path(__file__).parent / "fixtures/english-short-possessive-successors.json").read_bytes()
)
LAYERS = {rule["relative"]: rule for rule in DATA["layers"]}


def require(condition, diagnostic):
    if not condition:
        raise AssertionError(diagnostic)


def caption_frame(value):
    """Complete raw caption identity, entries and explicit alignment presence/order.

    Segment prose/citations and about stay outside this frame; complete word
    cards stay inside it. An old segment-prose fault remains in the returned copy
    and reaches its own oracle.
    """
    return {
        "identity": {key: value[key] for key in ("schema_version", "language", "text")},
        "words": deepcopy(value["words"]),
        "segment_order": list(value["segments"]),
        "segments": {
            sid: {"alignments": deepcopy(row["alignments"])} if "alignments" in row else {}
            for sid, row in value["segments"].items()
        },
    }


def inverse_groups(rule, value, diagnostic):
    result = deepcopy(value)
    for change in reversed(rule["groups"]):
        segment = result["segments"][change["segment"]]
        groups = segment["alignments"]
        require(groups[change["index"]] == change["group"], diagnostic)
        for word, entry in change["after_entries"].items():
            require(result["words"][word] == entry, diagnostic)
            result["words"][word] = deepcopy(change["before_entries"][word])
        groups.pop(change["index"])
        if not groups and not change["had_alignments_before"]:
            del segment["alignments"]
    return result


def before_short_possessive_layer(relative, value, diagnostic="short possessive current layer"):
    """Bind the whole current layer before undoing six enrolled short groups."""
    value = before_psalm_caption_layer(relative, value, diagnostic)
    if relative not in LAYERS:
        return value
    rule = LAYERS[relative]
    require(digest(value) == rule["after_canonical_sha256"], diagnostic)
    require(digest(caption_frame(value)) == rule["after_caption_sha256"], diagnostic)
    result = inverse_groups(rule, value, diagnostic)
    require(digest(result) == rule["before_canonical_sha256"], diagnostic)
    return result


def before_short_possessive_caption_frame(
    relative, value, diagnostic="short possessive current caption frame"
):
    """Compare captions only, preserving every non-caption field and prose fault."""
    value = before_psalm_caption_frame(relative, value, caption_frame, diagnostic)
    if relative not in LAYERS:
        return value
    rule = LAYERS[relative]
    require(digest(caption_frame(value)) == rule["after_caption_sha256"], diagnostic)
    result = inverse_groups(rule, value, diagnostic)
    require(digest(caption_frame(result)) == rule["before_caption_sha256"], diagnostic)
    return result


def before_short_possessive_bytes(relative, raw, diagnostic="short possessive current bytes"):
    """Require exact actual bytes, then restore the exact declared old lines."""
    raw = before_psalm_caption_bytes(relative, raw, diagnostic)
    if relative not in LAYERS:
        return raw
    rule = LAYERS[relative]
    require(hashlib.sha256(raw).hexdigest() == rule["after_raw_sha256"], diagnostic)
    result = raw
    for operation in reversed(rule["raw_inverse_operations"]):
        after, before = operation["after"].encode(), operation["before"].encode()
        require(result.count(after) == 1, diagnostic)
        result = result.replace(after, before, 1)
    require(hashlib.sha256(result).hexdigest() == rule["before_raw_sha256"], diagnostic)
    return result
