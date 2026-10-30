"""Reader-face arrow successors, reversed only on historical comparison copies.

Fifty-seven bibliography strings wrote U+2192, which the reading face does not
set. Twenty-four Mass Ordo selection orders now read "410, then 411"; five
English locator labels and fourteen English claims read "Holy Ghost becomes
Holy Spirit" or "shall becomes will"; fourteen Polish claims read "Twego na
Twojego". Older exact comparisons first restore the declared earlier strings
on a copy. Each inverse maps only an exact current string to its predecessor,
so the predecessor itself passes unchanged and every other value, including a
fault, reaches the older oracle and its own diagnostic.
"""

import json
from copy import deepcopy
from pathlib import Path

DATA = json.loads((Path(__file__).parent / "fixtures/reader-arrow-successor.json").read_bytes())
GRAPH = "bibliography/graph.json"
FILES: dict[str, list[dict]] = {}
for _row in DATA["strings"]:
    FILES.setdefault(_row["file"], []).append(_row)
BY_USE = {row["use"]: row for row in DATA["strings"]}


def _container(use, path):
    """The mapping that holds the last key of path, or None."""
    container = use
    for key in path[:-1]:
        if not isinstance(container, dict):
            return None
        container = container.get(key)
    return container if isinstance(container, dict) else None


def before_arrow_use(use):
    """One use record: the exact current string returns to its predecessor."""
    row = BY_USE.get(use.get("id")) if isinstance(use, dict) else None
    if row is None:
        return use
    container = _container(use, row["field"])
    if container is None or container.get(row["field"][-1]) != row["after"]:
        return use
    result = deepcopy(use)
    _container(result, row["field"])[row["field"][-1]] = row["before"]
    return result


def before_arrow_object(relative, value):
    """A graph-shaped or language bibliography object; unlisted files pass unchanged."""
    if relative not in FILES or not isinstance(value, dict):
        return value
    uses = value.get("uses")
    if not isinstance(uses, list):
        return value
    restored = {index: before_arrow_use(use) for index, use in enumerate(uses)}
    changed = {index: use for index, use in restored.items() if use is not uses[index]}
    if not changed:
        return value
    result = deepcopy(value)
    for index, use in changed.items():
        result["uses"][index] = use
    return result


def before_arrow_graph(value):
    """The graph, or a records mapping taken from it."""
    return before_arrow_object(GRAPH, value)


def before_arrow_language(language, value):
    return before_arrow_object(f"languages/{language}/bibliography.json", value)


def before_arrow_bytes(relative, raw):
    """Whole-file bytes in the canonical layout; any other input reaches the old oracle."""
    if relative not in FILES:
        return raw
    try:
        value = json.loads(raw)
    except ValueError:
        return raw
    if (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode() != raw:
        return raw
    result = before_arrow_object(relative, value)
    if result is value:
        return raw
    return (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode()
