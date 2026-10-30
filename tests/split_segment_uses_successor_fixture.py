"""Split-segment use successors, reversed only on historical comparison copies.

Three Canon verses are divided around their printed rubrics: Qui pridie s02 and
s13, Quam oblationem s05 and s09, Simili modo s15 and s06. Nine English and
Polish bibliography uses quote wording that runs across both halves, and each
has a record addressed to the new segment, identical but for its id and segment
and without the legacy citation pointer of the earlier segment. Older exact
comparisons first remove exactly those nine records on a copy; every other
value, including a fault, reaches the older oracle and its own diagnostic.
"""

import json
from copy import deepcopy
from pathlib import Path

DATA = json.loads(
    (Path(__file__).parent / "fixtures/split-segment-uses-successor.json").read_bytes()
)
ADDED = {(row["file"], row["row"]["id"]): row["row"] for row in DATA["added"]}
FILES = frozenset(row["file"] for row in DATA["added"])


def before_split_uses_object(relative, value):
    """A language bibliography object; unlisted files pass unchanged."""
    if relative not in FILES or not isinstance(value, dict):
        return value
    uses = value.get("uses")
    if not isinstance(uses, list):
        return value
    kept = [
        use
        for use in uses
        if not (isinstance(use, dict) and ADDED.get((relative, use.get("id"))) == use)
    ]
    if len(kept) == len(uses):
        return value
    result = {key: deepcopy(item) for key, item in value.items() if key != "uses"}
    result["uses"] = deepcopy(kept)
    return {key: result[key] for key in value}


def before_split_uses_bytes(relative, raw):
    """Whole-file bytes in the canonical layout; any other input reaches the old oracle."""
    if relative not in FILES:
        return raw
    try:
        value = json.loads(raw)
    except ValueError:
        return raw
    if (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode() != raw:
        return raw
    result = before_split_uses_object(relative, value)
    if result is value:
        return raw
    return (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode()
