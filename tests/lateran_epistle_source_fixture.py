"""Exact source comparisons do not alter arguments to native consumers."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from documentary_bibliography_fixture import current_source_uses
from edition_revision_fixture import before_bibliography_record, current_bibliography_record

DATA = json.loads((Path(__file__).parent / "fixtures/lateran-epistle-source.json").read_bytes())


def canonical_hash(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def before_lateran_registry(value):
    """Remove only the one complete new binding; never remove an archive."""
    result = deepcopy(value)
    assert result["archives"].get(DATA["archive_id"]) == DATA["archive"], (
        "exact Lateran registry successor"
    )
    assert result["bindings"].get(DATA["binding_id"]) == DATA["binding"], (
        "exact Lateran registry successor"
    )
    del result["bindings"][DATA["binding_id"]]
    return result


def current_lateran_subject():
    """The complete modern expectation from the historical documentary record."""
    wanted = deepcopy(DATA["expected_subject"])
    wanted["witness"] = current_bibliography_record("witnesses", wanted["witness"], subject=True)
    wanted["source_uses"] = current_source_uses(wanted["source_uses"])
    return wanted


def before_lateran_records(value):
    """Reverse exact records and the explicit review-subject inventory transition."""
    result = deepcopy(value)
    rows = {row["after"]["id"]: (field, row) for field, row in DATA["records"].items()}

    def visit(item, in_subject=False):
        if isinstance(item, list):
            for child in item:
                visit(child)
        elif isinstance(item, dict):
            if (
                isinstance(item.get("witness"), dict)
                and item["witness"].get("id") == DATA["witness_id"]
            ):
                assert item in (DATA["expected_subject"], current_lateran_subject()), (
                    "exact Lateran source subject"
                )
                item["source_uses"] = deepcopy(DATA["expected_subject"]["source_uses"])
                item.pop("raw_resolution")
                item["contract"] = "witness-identity-2"
            identity = item.get("id")
            if identity in rows:
                field, row = rows[identity]
                before = deepcopy(row["before"])
                after = deepcopy(row["after"])
                native = field == "witnesses" and in_subject and "review" not in item
                if native:
                    del before["review"]
                    del after["review"]
                assert before_bibliography_record(field, item, subject=native) == after, (
                    "exact Lateran source comparison inverse"
                )
                item.clear()
                item.update(before)
            for key, child in item.items():
                visit(child, key == "witness" and item.get("contract") == "witness-identity-2")

    visit(result)
    return result


def before_lateran_graph(value):
    """Require all three current records before the complete graph comparison."""
    for collection, rule in DATA["records"].items():
        matches = [row for row in value[collection] if row["id"] == rule["after"]["id"]]
        assert (
            len(matches) == 1
            and before_bibliography_record(collection, matches[0]) == rule["after"]
        ), "exact Lateran source comparison inverse"
    return before_lateran_records(value)


def before_lateran_core(value):
    """Guard the whole current core, then undo only its documentary method."""
    rule = DATA["core_method"]
    assert canonical_hash(value) == rule["after_canonical_sha256"], "exact Lateran core successor"
    result = deepcopy(value)
    assert result["editorial"]["source"]["method"] == rule["after"]
    result["editorial"]["source"]["method"] = rule["before"]
    assert canonical_hash(result) == rule["before_canonical_sha256"]
    return result
