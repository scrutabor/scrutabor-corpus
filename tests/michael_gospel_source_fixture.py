"""Exact documentary comparison copies, never native input normalization."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

DATA = json.loads((Path(__file__).with_name("fixtures") / "michael-gospel-source.json").read_text())
TEXT = DATA["text"]
RECORDS = {row["id"]: row for row in DATA["records"]}
WITNESS = next(row for row in DATA["records"] if row["collection"] == "witnesses")


def digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def assert_michael_transcript(root):
    """This DO was never in947; do not borrow generic privacy membership."""
    raw = (root / DATA["witness"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == DATA["transcript"]["after_sha256"], (
        "complete current Michael Gospel transcript"
    )
    assert raw.decode() == DATA["transcript"]["after"], "exact Michael Gospel transcript"
    return raw


def before_michael_registry(value):
    """Remove one full exact plan; both complete existing archives remain."""
    assert value["bindings"].get(DATA["binding_id"]) == DATA["binding"], (
        "exact Michael Gospel registry addition"
    )
    assert all(value["archives"].get(key) == row for key, row in DATA["archives"].items()), (
        "unchanged Michael source archives"
    )
    result = deepcopy(value)
    del result["bindings"][DATA["binding_id"]]
    return result


def before_michael_records(value):
    """Guard complete current records/payloads before their exact inverse."""
    result = deepcopy(value)
    if isinstance(result, dict) and {"uses", "witnesses", "collations"} <= result.keys():
        present = [
            row["id"] for field in ("uses", "witnesses", "collations") for row in result[field]
        ]
        if "works" in result or set(present) & RECORDS.keys():
            assert all(present.count(identity) == 1 for identity in RECORDS), (
                "complete Michael Gospel record membership"
            )

    def visit(item):
        if isinstance(item, list):
            for child in item:
                visit(child)
            return
        if not isinstance(item, dict):
            return
        if isinstance(item.get("witness"), dict) and item["witness"].get("id") == WITNESS["id"]:
            assert set(item) == {
                "contract",
                "witness",
                "source_uses",
                "selected_text",
                "raw_resolution",
            }, "complete Michael Gospel witness subject"
            assert item["contract"] == "witness-review-2", "current Michael source contract"
            assert item["witness"] == {
                key: field for key, field in WITNESS["after"].items() if key != "review"
            }, "complete Michael Gospel witness record"
            assert item["source_uses"] == DATA["source_uses"]["after"], (
                "complete Michael Gospel source uses"
            )
            assert item["raw_resolution"] == DATA["expected_source"], (
                "complete Michael Gospel raw resolution"
            )
            assert digest(item["selected_text"]) in DATA["gospel_selected"].values(), (
                "exact current or historical sung Michael selection"
            )
            selected = item["selected_text"]
            item.clear()
            item.update(
                contract="witness-identity-2",
                witness={key: field for key, field in WITNESS["before"].items() if key != "review"},
                source_uses=deepcopy(DATA["source_uses"]["before"]),
                selected_text=selected,
            )
            return
        if item.get("id") in RECORDS:
            row = RECORDS[item["id"]]
            before, after = deepcopy(row["before"]), deepcopy(row["after"])
            if "review" in after and "review" not in item:
                del before["review"]
                del after["review"]
            if row["collection"] == "collations":
                selected = item.get("selected_text_sha256")
                assert selected in DATA["gospel_selected"].values(), (
                    "exact current or historical sung Michael selection"
                )
                before["selected_text_sha256"] = after["selected_text_sha256"] = selected
            assert item == after, "complete Michael Gospel source record"
            item.clear()
            item.update(before)
            return
        for child in item.values():
            visit(child)

    visit(result)
    return result
