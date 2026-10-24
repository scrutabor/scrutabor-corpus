"""Exact inverse of the Common Preface's separately identified source additions."""

import json
from copy import deepcopy
from pathlib import Path

DATA = json.loads((Path(__file__).parent / "fixtures/common-preface-source-chain.json").read_text())


def without_common_preface_source_chain(graph):
    """Recover the earlier graph only from the complete, exact current additions."""
    result = deepcopy(graph)
    for key, rows in DATA["additions"].items():
        identifiers = {row["id"] for row in rows}
        observed = sorted(
            (row for row in result[key] if row["id"] in identifiers),
            key=lambda row: row["id"],
        )
        assert observed == rows, "current Common Preface source additions"
        result[key] = [row for row in result[key] if row["id"] not in identifiers]
        remaining = [
            row
            for row in result[key]
            if row.get("text", row.get("address", {}).get("text")) == DATA["text"]
        ]
        assert remaining == DATA["records_before"][key], "earlier Common Preface source inventory"
    return result
