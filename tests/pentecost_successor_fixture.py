"""Exact current target-hash successors, leaving historical fixtures intact."""

import json
from copy import deepcopy
from pathlib import Path

FIXTURE = json.loads(
    (Path(__file__).with_name("fixtures") / "pentecost-successors.json").read_text()
)
CHANGES = {row["before"]["site"]: row for row in FIXTURE["provenance_rows"]}


def expected_pentecost_row(row, site=None):
    """Advance only historical expected rows, never actual observed rows."""
    result = deepcopy(row)
    identity = site if site is not None else result["site"]
    change = CHANGES.get(identity)
    if change is not None:
        assert "target_sha256" in result and all(
            result[key] == value for key, value in change["before"].items() if key in result
        ), "historical Pentecost expected row"
        result["target_sha256"] = change["after"]["target_sha256"]
    return result
