"""Intercession captions, apposition heads and the Lawrence Gospel prose, reversed on copies.

Four English intercession captions follow the Latin construction they render; seven attributive
forms of *beatus* and one intercession participle agree with the nearest following noun of their
apposition group; the English Lawrence Gospel reads `serves Me` and `My servant`; the
provenance ledgers carry the recomputed hashes. Older exact comparisons first undo these
declared changes on a copy; the caller keeps the actual current file.

Each inverse is a pure function of its input and never reads the working tree. A declared
change is undone only where its field holds exactly the declared new value, so the
predecessor (and any earlier state an older inverse in the same chain has produced) passes
unchanged, and every other difference, including a fault, reaches the older oracle and its
own diagnostic.
"""

import json
from copy import deepcopy
from pathlib import Path

from checks.layout import formatted

DATA = json.loads(
    (Path(__file__).parent / "fixtures/caption-followups-successor.json").read_bytes()
)
FILES = DATA["files"]
CORES = {rule["text"]: relative for relative, rule in FILES.items() if rule["kind"] == "core"}
MISSING = object()


def _step(container, step):
    """One path step: a key of a mapping, or the one list element with the given key value."""
    if isinstance(step, dict):
        if not isinstance(container, list):
            return MISSING
        ((key, wanted),) = step.items()
        found = [row for row in container if isinstance(row, dict) and row.get(key) == wanted]
        return found[0] if len(found) == 1 else MISSING
    if not isinstance(container, dict) or step not in container:
        return MISSING
    return container[step]


def _get(value, path):
    for step in path:
        value = _step(value, step)
        if value is MISSING:
            return MISSING
    return value


def _undo(rule, value):
    result = None
    for change in reversed(rule["changes"]):
        current = value if result is None else result
        if _get(current, change["path"]) != change["after"]:
            continue
        if result is None:
            result = deepcopy(value)
        parent = _get(result, change["path"][:-1])
        parent[change["path"][-1]] = deepcopy(change["before"])
    return value if result is None else result


def before_followups_object(relative, value):
    """A parsed file with the declared fields restored; unlisted files pass unchanged."""
    rule = FILES.get(relative)
    if rule is None:
        return value
    return _undo(rule, value)


def before_followups_bytes(relative, raw):
    """Whole-file bytes in the house layout; any other input reaches the old oracle."""
    rule = FILES.get(relative)
    if rule is None:
        return raw
    try:
        value = json.loads(raw)
    except ValueError:
        return raw
    if not isinstance(value, dict) or formatted(value).encode("utf-8") != raw:
        return raw
    result = _undo(rule, value)
    return raw if result is value else formatted(result).encode("utf-8")


def layer_relative(layer):
    """A layer's file, from its own text and language (`lang` in the reader's expansion)."""
    language = (layer.get("language") or layer.get("lang")) if isinstance(layer, dict) else None
    text = layer.get("text") if isinstance(layer, dict) else None
    if not isinstance(language, str) or not isinstance(text, str):
        return None
    return f"languages/{language}/texts/{text.replace('.', '/', 1)}.json"


def before_followups_layer(layer):
    """The same inverse, addressed by a layer's own text and language; frames included."""
    relative = layer_relative(layer)
    if relative is None:
        return layer
    return before_followups_object(relative, layer)


def before_followups_core(core):
    """The same inverse, addressed by a core's (or a core frame's) own text id."""
    relative = CORES.get(core.get("id")) if isinstance(core, dict) else None
    if relative is None:
        return core
    return before_followups_object(relative, core)


def before_followups_core_bytes(text, raw):
    relative = CORES.get(text)
    if relative is None:
        return raw
    return before_followups_bytes(relative, raw)
