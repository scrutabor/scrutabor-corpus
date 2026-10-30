"""Ordo-witness notes successors, reversed only on historical comparison copies.

Eleven Ordinary and prayer cores ground their notes and rubric provenance on the
printed pages, apparatus prose and three English and Polish introductions take
the recorded corrections, the Preface dialogue transcript records the p. 286
misprint and the attribution rationale the printed basis of three omnes
speakers. The graph gains the dialogue rubric's printed use and eight
leaf-bound continuation uses, narrows the scan locator of their eight parents to
the leaf each binds, and corrects two Enchiridion records. Older exact
comparisons first undo these declared changes on a copy; the caller keeps the
actual current file.

Each inverse is a pure function of its input and never reads the working tree.
It turns the exact declared current value into its exact predecessor. A declared
change is undone only where it stands exactly as declared, so the predecessor,
and any earlier state an older inverse in the same chain has produced, passes
unchanged, and every other difference, including a fault, reaches the older
oracle and its own diagnostic.
"""

import json
from copy import deepcopy
from pathlib import Path

from checks.layout import formatted

DATA = json.loads((Path(__file__).parent / "fixtures/ordo-notes-successor.json").read_bytes())
GRAPH = "bibliography/graph.json"
ADDED = {row["id"]: row for row in DATA["graph"]["added"]}
CHANGED = {change["after"]["id"]: change for change in DATA["graph"]["changed"]}


def plain(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def render(layout, value):
    if layout == "house":
        return formatted(value).encode("utf-8")
    return plain(value)


def before_ordo_notes_use(use):
    """One use record: the exact current record returns to its predecessor."""
    change = CHANGED.get(use.get("id")) if isinstance(use, dict) else None
    if change is None or use != change["after"]:
        return use
    return deepcopy(change["before"])


def before_ordo_notes_graph(value):
    """The graph, or a records mapping taken from it, without the declared changes.

    Each exact new use is removed and each exact corrected use restored where its id
    occurs once; any other record, including a damaged or repeated declared one,
    stays for the older guards.
    """
    if not isinstance(value, dict) or not isinstance(value.get("uses"), list):
        return value
    counts = {}
    for use in value["uses"]:
        identity = use.get("id") if isinstance(use, dict) else None
        counts[identity] = counts.get(identity, 0) + 1
    uses = []
    changed = False
    for use in value["uses"]:
        identity = use.get("id") if isinstance(use, dict) else None
        if counts[identity] != 1:
            uses.append(use)
            continue
        if ADDED.get(identity) == use:
            changed = True
            continue
        previous = before_ordo_notes_use(use)
        changed = changed or previous is not use
        uses.append(previous)
    if not changed:
        return value
    return {key: deepcopy(uses if key == "uses" else item) for key, item in value.items()}


def before_ordo_notes_bytes(relative, raw):
    """Whole-file bytes; only the declared earlier fragments are restored."""
    rule = DATA["files"].get(relative)
    if rule is None:
        return raw
    if relative == GRAPH:
        try:
            value = json.loads(raw)
        except ValueError:
            return raw
        if plain(value) != raw:
            return raw
        result = before_ordo_notes_graph(value)
        return raw if result is value else plain(result)
    result = raw
    for operation in reversed(rule["raw_inverse"]):
        after, before = operation["after"].encode("utf-8"), operation["before"].encode("utf-8")
        if result.count(after) == 1:
            result = result.replace(after, before, 1)
    return raw if result == raw else result


def before_ordo_notes_core_bytes(text, raw):
    relative = DATA["texts"].get(text)
    if relative is None:
        return raw
    return before_ordo_notes_bytes(relative, raw)


def before_ordo_notes_object(relative, value):
    """A parsed JSON file (or the graph, or a records mapping taken from it)."""
    if relative == GRAPH:
        return before_ordo_notes_graph(value)
    rule = DATA["files"].get(relative)
    if rule is None or "layout" not in rule or not isinstance(value, dict):
        return value
    raw = render(rule["layout"], value)
    result = before_ordo_notes_bytes(relative, raw)
    if result == raw:
        return value
    return json.loads(result)


def before_ordo_notes_core_object(text, value):
    relative = DATA["texts"].get(text)
    if relative is None:
        return value
    return before_ordo_notes_object(relative, value)


def layer_relative(layer):
    language = layer.get("language") if isinstance(layer, dict) else None
    text = layer.get("text") if isinstance(layer, dict) else None
    if not isinstance(language, str) or not isinstance(text, str):
        return None
    return f"languages/{language}/texts/{text.replace('.', '/', 1)}.json"


def before_ordo_notes_layer(layer):
    """The same inverse, addressed by a layer's own text and language."""
    relative = layer_relative(layer)
    if relative is None:
        return layer
    return before_ordo_notes_object(relative, layer)
