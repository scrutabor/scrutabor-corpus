"""Canon consecration successors, reversed only on historical comparison copies.

The Simili modo and Supplices rubrics read as the 1962 page prints them, the
Qui pridie and Quam oblationem rubrics stand where the page sets them (three
verses divide around them), Simili modo and Supplices have printed-edition
uses, the Te igitur transcript prints the comma after pétimus, and every rubric
from the Te igitur to the Per ipsum cites the printed Missal witness. Older
exact comparisons first undo these declared changes on a copy; the caller keeps
the actual current file.

Each whole-file inverse accepts exactly two inputs: the declared current file,
which it turns into its exact predecessor, and that exact predecessor, which it
returns unchanged so that a comparison chain reaching it twice stays exact.
Every other input is rejected.
"""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from foot_communion_successor_fixture import (
    before_foot_communion_bytes,
    before_foot_communion_graph,
    before_foot_communion_object,
)
from ordo_notes_successor_fixture import before_ordo_notes_bytes, before_ordo_notes_object
from possessive_sweep_b1_successor_fixture import (
    before_possessive_b1_bytes,
    before_possessive_b1_layer_frame,
    before_possessive_b1_object,
)
from possessive_sweep_b2_successor_fixture import (
    before_possessive_b2_bytes,
    before_possessive_b2_layer_frame,
)
from possessive_sweep_b3_successor_fixture import (
    before_possessive_b3_bytes,
    before_possessive_b3_layer_frame,
)
from reader_arrow_successor_fixture import before_arrow_bytes, before_arrow_object

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads(
    (Path(__file__).parent / "fixtures/canon-consecration-successor.json").read_bytes()
)
DIAGNOSTIC = "exact Canon consecration successor"
GRAPH_DIAGNOSTIC = "exact Canon consecration graph addition"


def require(condition, diagnostic):
    if not condition:
        raise AssertionError(diagnostic)


def before_canon_bytes(relative, raw, diagnostic=DIAGNOSTIC):
    """Require every current byte, then restore only the declared earlier fragments."""
    raw = before_possessive_b3_bytes(relative, raw)
    raw = before_possessive_b2_bytes(relative, raw)
    raw = before_possessive_b1_bytes(relative, raw)
    raw = before_ordo_notes_bytes(relative, raw)
    raw = before_arrow_bytes(relative, raw)
    rule = DATA["files"].get(relative)
    if rule is None:
        return before_foot_communion_bytes(relative, raw, diagnostic)
    digest = hashlib.sha256(raw).hexdigest()
    if digest == rule["before_sha256"]:
        return raw
    raw = before_foot_communion_bytes(relative, raw, diagnostic)
    digest = hashlib.sha256(raw).hexdigest()
    require(digest == rule["after_sha256"], diagnostic)
    result = raw
    for operation in reversed(rule["raw_inverse"]):
        after, before = operation["after"].encode(), operation["before"].encode()
        require(result.count(after) == operation["count"], diagnostic)
        result = result.replace(after, before, operation["count"])
    require(hashlib.sha256(result).hexdigest() == rule["before_sha256"], diagnostic)
    return result


def before_canon_core_bytes(text, raw, diagnostic=DIAGNOSTIC):
    relative = DATA["texts"].get(text)
    if relative is None:
        return raw
    return before_canon_bytes(relative, raw, diagnostic)


def before_canon_object(relative, value, diagnostic=DIAGNOSTIC):
    """Accept only the complete current file or its exact predecessor, as parsed JSON."""
    if relative not in DATA["files"]:
        return before_foot_communion_object(relative, value, diagnostic)
    value = before_possessive_b1_object(relative, value)
    value = before_arrow_object(relative, before_ordo_notes_object(relative, value))
    actual = before_possessive_b1_bytes(relative, (ROOT / relative).read_bytes())
    actual = before_ordo_notes_bytes(relative, actual)
    raw = before_foot_communion_bytes(relative, before_arrow_bytes(relative, actual), diagnostic)
    previous = json.loads(before_canon_bytes(relative, raw, diagnostic))
    if value == previous:
        return value
    current = before_foot_communion_object(relative, value, diagnostic)
    require(current == json.loads(raw), diagnostic)
    return previous


def before_canon_core_object(text, value, diagnostic=DIAGNOSTIC):
    relative = DATA["texts"].get(text)
    if relative is None:
        return value
    return before_canon_object(relative, value, diagnostic)


def layer_relative(layer):
    language = layer.get("language") or layer.get("lang")
    text = layer.get("text")
    if not isinstance(language, str) or not isinstance(text, str):
        return None
    return f"languages/{language}/texts/{text.replace('.', '/', 1)}.json"


def before_canon_layer(layer, diagnostic=DIAGNOSTIC):
    """The same exact inverse, addressed by a layer's own text and language."""
    relative = layer_relative(layer)
    if relative is None:
        return layer
    return before_canon_object(relative, layer, diagnostic)


def before_canon_graph(value, diagnostic=GRAPH_DIAGNOSTIC):
    """Remove the exact new uses; every other record stays for the older guards."""
    value = before_foot_communion_graph(value, diagnostic)
    rules = DATA["graph_uses"]
    rows = value["uses"]
    found = [
        [i for i, row in enumerate(rows) if row.get("id") == rule["row"]["id"]] for rule in rules
    ]
    if not any(found):
        return value
    for indices, rule in zip(found, rules, strict=True):
        require(indices == [rule["index"]], diagnostic)
        require(rows[rule["index"]] == rule["row"], diagnostic)
    result = deepcopy(value)
    for rule in sorted(rules, key=lambda rule: rule["index"], reverse=True):
        del result["uses"][rule["index"]]
    return result


def before_canon_core_frame(core, diagnostic=DIAGNOSTIC):
    """Rejoin the divided verses and restore the rubrics on a copy of any core-shaped value.

    Only the declared segments are bound; a fault anywhere else stays in the copy for
    the older oracle that reads it.
    """
    rule = DATA["core_frames"].get(core.get("id")) if isinstance(core, dict) else None
    if rule is None:
        return core
    result = deepcopy(core)
    segments = {segment["id"]: segment for segment in result["segments"]}
    require(set(segments) == set(rule["order_after"]), diagnostic)
    for merge in rule["merges"]:
        kept, new = segments[merge["kept"]], segments.pop(merge["new"])
        require([w["id"] for w in kept["words"]] == merge["kept_words"], diagnostic)
        require([w["id"] for w in new["words"]] == merge["new_words"], diagnostic)
        if merge["kept_first"]:
            kept["words"] = kept["words"] + new["words"]
        else:
            kept["words"] = new["words"] + kept["words"]
    for sid, change in rule["rubrics"].items():
        require(segments[sid].get("text") == change["after"], diagnostic)
        segments[sid]["text"] = change["before"]
    for sid, text in rule["added_rubrics"].items():
        require(segments.pop(sid).get("text") == text, diagnostic)
    result["segments"] = [segments[sid] for sid in rule["order_before"]]
    return result


def before_canon_layer_frame(layer, diagnostic=DIAGNOSTIC):
    """Rejoin the divided translations and narratives on a copy of a layer-shaped value."""
    layer = before_possessive_b3_layer_frame(layer)
    layer = before_possessive_b2_layer_frame(layer)
    layer = before_possessive_b1_layer_frame(layer)
    relative = layer_relative(layer) if isinstance(layer, dict) else None
    rule = DATA["layer_frames"].get(relative)
    if rule is None:
        return layer
    result = deepcopy(layer)
    segments = result["segments"]
    for sid, change in rule["changed"].items():
        field = change["field"]
        require(segments[sid].get(field) == change["after"], diagnostic)
        segments[sid][field] = change["before"]
    for sid, entry in rule["added"].items():
        require(segments.pop(sid) == entry, diagnostic)
    order = [sid for sid in rule["order_before"] if sid in segments]
    result["segments"] = {
        sid: segments[sid] for sid in order + [s for s in segments if s not in order]
    }
    return result


def current_canon_row(row):
    """Map an exact predecessor ledger row to its declared successor; keep any other row."""
    for change in DATA["ledger_rows"]:
        if change["before"] is not None and row == change["before"]:
            return deepcopy(change["after"])
    return row
