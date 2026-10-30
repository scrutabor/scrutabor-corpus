"""Foot of the altar and Communion successors, reversed only on historical comparison copies.

The printed rubric "Ministri respondent:" stands where the 1962 page sets it in
the Introibo and the Misereatur tui, the priest's Amen in the Misereatur tui and
the colon in the Qui dixisti read as printed, the Qui dixisti rubrics follow
pp. 313-314 and its Latin has a printed-edition use, and the rubric segments of
the eleven texts cite the printed Missal witness. Older exact comparisons first
undo these declared changes on a copy; the caller keeps the actual current file.

Each inverse is a pure function of its input and never reads the working tree. It
turns the exact declared current value into its exact predecessor. A value that
carries none of the declared changes (that predecessor, or an earlier state an
older inverse in the same chain has already produced) is returned unchanged for
the older comparison that reads it, so chains stay exact in any delivery order.
Every other value, one that still carries a declared change without being the
exact current value, is rejected.
"""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from build_reader.bibliography_bindings import digest
from checks.layout import formatted

DATA = json.loads((Path(__file__).parent / "fixtures/foot-communion-successor.json").read_bytes())
DIAGNOSTIC = "exact foot of the altar and Communion successor"
GRAPH_DIAGNOSTIC = "exact foot of the altar and Communion graph addition"


def require(condition, diagnostic):
    if not condition:
        raise AssertionError(diagnostic)


def carries_change(rule, raw):
    """Whether any declared current fragment, none of which the predecessor holds, is present."""
    return any(operation["after"].encode() in raw for operation in rule["raw_inverse"])


def before_foot_communion_bytes(relative, raw, diagnostic=DIAGNOSTIC):
    """Require every current byte, then restore only the declared earlier fragments."""
    rule = DATA["files"].get(relative)
    if rule is None:
        return raw
    if hashlib.sha256(raw).hexdigest() != rule["after_sha256"]:
        require(not carries_change(rule, raw), diagnostic)
        return raw
    result = raw
    for operation in reversed(rule["raw_inverse"]):
        after, before = operation["after"].encode(), operation["before"].encode()
        require(result.count(after) == operation["count"], diagnostic)
        result = result.replace(after, before, operation["count"])
    require(hashlib.sha256(result).hexdigest() == rule["before_sha256"], diagnostic)
    return result


def before_foot_communion_core_bytes(text, raw, diagnostic=DIAGNOSTIC):
    relative = DATA["texts"].get(text)
    if relative is None:
        return raw
    return before_foot_communion_bytes(relative, raw, diagnostic)


def render(layout, value):
    if layout == "house":
        return formatted(value).encode("utf-8")
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def before_foot_communion_object(relative, value, diagnostic=DIAGNOSTIC):
    """Bind the complete current object, then parse its exact predecessor."""
    rule = DATA["files"].get(relative)
    if rule is None or "layout" not in rule:
        return value
    raw = render(rule["layout"], value)
    if digest(value) != rule["after_canonical_sha256"]:
        require(not carries_change(rule, raw), diagnostic)
        return value
    raw = before_foot_communion_bytes(relative, raw, diagnostic)
    result = json.loads(raw)
    require(digest(result) == rule["before_canonical_sha256"], diagnostic)
    return result


def before_foot_communion_core_object(text, value, diagnostic=DIAGNOSTIC):
    relative = DATA["texts"].get(text)
    if relative is None:
        return value
    return before_foot_communion_object(relative, value, diagnostic)


def layer_relative(layer):
    language = layer.get("language") if isinstance(layer, dict) else None
    text = layer.get("text") if isinstance(layer, dict) else None
    if not isinstance(language, str) or not isinstance(text, str):
        return None
    return f"languages/{language}/texts/{text.replace('.', '/', 1)}.json"


def before_foot_communion_layer(layer, diagnostic=DIAGNOSTIC):
    """The same exact inverse, addressed by a layer's own text and language."""
    relative = layer_relative(layer)
    if relative is None:
        return layer
    return before_foot_communion_object(relative, layer, diagnostic)


def before_foot_communion_layer_frame(layer, diagnostic=DIAGNOSTIC):
    """Restore the declared prose and remove the added rubric narratives on a copy.

    Only the declared entries are bound; a fault anywhere else stays in the copy for
    the older oracle that reads it.
    """
    relative = layer_relative(layer)
    rule = DATA["layer_frames"].get(relative) if relative else None
    if rule is None:
        return layer
    result = deepcopy(layer)
    for field, change in rule["fields"].items():
        if result.get(field) == change["after"]:
            result[field] = deepcopy(change["before"])
    segments = result["segments"]
    for sid, entry in rule["added"].items():
        if sid in segments:
            require(segments[sid] == entry, diagnostic)
            del segments[sid]
    order = [sid for sid in rule["order_before"] if sid in segments]
    result["segments"] = {
        sid: segments[sid] for sid in order + [sid for sid in segments if sid not in order]
    }
    return result


def before_foot_communion_graph(value, diagnostic=GRAPH_DIAGNOSTIC):
    """Remove the exact new use; every other record stays for the older guards."""
    rule = DATA["graph_use"]
    rows = value["uses"]
    indices = [i for i, row in enumerate(rows) if row.get("id") == rule["row"]["id"]]
    if not indices:
        return value
    require(indices == [rule["index"]], diagnostic)
    require(rows[rule["index"]] == rule["row"], diagnostic)
    result = deepcopy(value)
    del result["uses"][rule["index"]]
    return result


def current_foot_communion_row(row):
    """Map an exact predecessor ledger row to its declared successor; keep any other row."""
    for change in DATA["ledger_rows"]:
        if row == change["before"]:
            return deepcopy(change["after"])
    return row
