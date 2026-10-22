"""Exact local expectations without rewriting historical provenance evidence."""

import json
from copy import deepcopy
from pathlib import Path

FIXTURE = json.loads(
    (Path(__file__).with_name("fixtures") / "corpus-christi-epistle-successor.json").read_text(
        encoding="utf-8"
    )
)
CHANGES = {
    row["before"]["site"]: row
    for row in FIXTURE["provenance_rows"]
    if row["before"]["site"] in FIXTURE["historical_successor_sites"]
}


def expected_corpus_christi_epistle_row(row, site):
    """Advance four expected PL hashes, not observations or historical fixtures."""
    result = deepcopy(row)
    change = CHANGES.get(site)
    if change is not None:
        required = {"origin", "review", "target_sha256", "familiar_core"}
        assert required <= set(result) and all(
            result[key] == value for key, value in change["before"].items() if key in result
        ), "historical Corpus Christi expected row"
        result["target_sha256"] = change["after"]["target_sha256"]
    return result
