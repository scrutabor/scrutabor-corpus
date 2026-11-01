"""Adoro te devote, reversed on copies: the new prayer's rows in the shared files.

Adoro te devote enters the prayers. The shared files gain its 28 provenance rows per language,
five uses, five witnesses and one collation in the bibliography graph, eight lexicon cards per
language and eight lemmata, its manifest entry and title in both languages, two morphology
registry rows and the text registry row; the third Polish sense of *sapio* reads `smakować` and
the English card gains a fourth sense. Older exact comparisons first undo these declared
additions on a copy; the caller keeps the actual current file.

Each inverse is a pure function of its input and never reads the working tree. A file's
declared additions are undone together, and only where every one of them holds exactly the
declared value at its declared place, so the predecessor (and any earlier state an older
inverse in the same chain has produced) passes unchanged, and every other difference,
including a partial or altered addition, reaches the older oracle and its own diagnostic.
"""

import json
from copy import deepcopy
from pathlib import Path

from build_reader.emit import _record_array
from checks.layout import formatted

DATA = json.loads((Path(__file__).parent / "fixtures/adoro-te-devote-successor.json").read_bytes())
FILES = DATA["files"]
GRAPH = "bibliography/graph.json"
MISSING = object()


def render(layout, value):
    """The file's own layout: house, the plain two-space dump, or one registry record a line."""
    if layout == "house":
        return formatted(value).encode("utf-8")
    if layout == "records":
        return _record_array(value).encode("utf-8")
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _get(value, path):
    for step in path:
        if isinstance(step, int):
            if not isinstance(value, list) or not 0 <= step < len(value):
                return MISSING
        elif not isinstance(value, dict) or step not in value:
            return MISSING
        value = value[step]
    return value


def _holds(value, change):
    """Whether one declared addition or field change holds exactly at its declared place."""
    if "insert" not in change:
        return _get(value, change["path"]) == change["after"]
    place = change["key"] if "key" in change else change["index"]
    return _get(value, [*change["path"], place]) == change["insert"]


def _undo(rule, value):
    if not all(_holds(value, change) for change in rule["changes"]):
        return value
    result = deepcopy(value)
    for change in reversed(rule["changes"]):
        if "insert" not in change:
            parent = _get(result, change["path"][:-1])
            parent[change["path"][-1]] = deepcopy(change["before"])
        elif "key" in change:
            del _get(result, change["path"])[change["key"]]
        else:
            del _get(result, change["path"])[change["index"]]
    return result


def before_adoro_object(relative, value):
    """A parsed file with the declared additions removed; unlisted files pass unchanged."""
    rule = FILES.get(relative)
    if rule is None:
        return value
    return _undo(rule, value)


def before_adoro_bytes(relative, raw):
    """Whole-file bytes in the file's own layout; any other input reaches the old oracle."""
    rule = FILES.get(relative)
    if rule is None:
        return raw
    try:
        value = json.loads(raw)
    except ValueError:
        return raw
    if render(rule["layout"], value) != raw:
        return raw
    result = _undo(rule, value)
    return raw if result is value else render(rule["layout"], result)


def before_adoro_graph(value):
    """The complete bibliography graph without the eleven new records."""
    return before_adoro_object(GRAPH, value)
