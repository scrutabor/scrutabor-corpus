"""Exact current expectations following the historical chant labels."""

import json
from copy import deepcopy
from pathlib import Path

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures/marian-chant-successors.json").read_text(encoding="utf-8")
)


def expected_marian_row(row, site):
    """Advance an expected hash at six named sites, never an actual ledger row."""
    result = deepcopy(row)
    change = FIXTURE["layers"].get(site)
    if change is not None:
        assert result["origin"] == "working-unsettled", "historical chant origin"
        assert result["review"] == "working", "historical chant review"
        assert result["target_sha256"] == change["target_before"], "historical chant target"
        if "familiar_core" in result:
            assert result["familiar_core"] is False, "historical chant protection"
        result["target_sha256"] = change["target_after"]
    return result
