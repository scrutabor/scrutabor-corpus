"""Exact expected-side transcript-header successors; never normalize native inputs."""

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path

DATA = json.loads((Path(__file__).parent / "fixtures/witness-header-successors.json").read_text())
TRANSCRIPTS = DATA["transcripts"]
BY_ID = {row["witness"]: row for row in TRANSCRIPTS.values()}
REVIEWS = DATA["reviews"]


def canonical_hash(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def expected_transcript(relative, historical):
    """Advance only an explicitly named historical EXPECTED complete digest."""
    assert relative in TRANSCRIPTS, "known transcript successor identity"
    row = TRANSCRIPTS[relative]
    assert historical == row["before_sha256"], "historical transcript digest"
    return row["after_sha256"]


def expected_review(identifier, historical):
    """Advance exactly the admitted review subset; other existing reviews stay exact."""
    if identifier not in REVIEWS:
        return historical
    row = REVIEWS[identifier]
    assert historical == row["before_sha256"], "historical source review digest"
    actual = row["after_sha256"]
    assert isinstance(actual, str) and re.fullmatch(r"[0-9a-f]{64}", actual), (
        "required real source review capture"
    )
    return actual


# This narrow content successor is separate from the immutable privacy snapshots.
SOURCE_SCOPE = json.loads(
    (Path(__file__).parent / "fixtures/all-souls-first-source-successors.json").read_text()
)


def before_source_scope_header(relative, raw):
    """Verify actual new bytes, then invert one exact public header on a comparison copy."""
    rule = SOURCE_SCOPE["scope_header"]
    if relative != rule["relative"]:
        return raw
    assert hashlib.sha256(raw).hexdigest() == rule["after_sha256"], (
        "source-scope complete transcript"
    )
    addition = rule["added_line"].encode("utf-8")
    assert raw.count(addition) == 1, "source-scope single header"
    comparison = raw.replace(addition, b"", 1)
    assert hashlib.sha256(comparison).hexdigest() == rule["before_sha256"], (
        "source-scope predecessor transcript"
    )
    return comparison


def assert_transcript_content(root, relative):
    """Inspect real current bytes; no predecessor string is fabricated or installed."""
    assert relative in TRANSCRIPTS, "known transcript successor identity"
    row = TRANSCRIPTS[relative]
    raw = (root / relative).read_bytes()
    raw = before_source_scope_header(relative, raw)
    assert hashlib.sha256(raw).hexdigest() == row["after_sha256"], (
        "current complete transcript digest"
    )
    lines = raw.splitlines(keepends=True)
    headers = b"".join(line for line in lines if line.startswith(b"#"))
    body = b"".join(line for line in lines if not line.startswith(b"#"))
    assert hashlib.sha256(headers).hexdigest() == row["public_headers_sha256"], (
        "unchanged public transcript headers"
    )
    assert hashlib.sha256(body).hexdigest() == row["body_sha256"], "unchanged transcript body"


def expected_header_lines(identity, historical):
    """Project one bound obsolete expected header, without a filesystem-path literal."""
    row = DATA["header_lists"][identity]
    assert canonical_hash(historical) == row["before_sha256"], "historical header list"
    result = list(historical)
    removed = result.pop(row["index"])
    assert canonical_hash(removed) == row["removed_sha256"], "historical header entry"
    assert canonical_hash(result) == row["after_sha256"], "projected public header list"
    return result


def before_privacy(value, diagnostic="exact transcript-header comparison inverse"):
    """Reverse exact known scalars on comparison copies ONLY, never native arguments."""
    result = deepcopy(value)

    def visit(item):
        if isinstance(item, list):
            for child in item:
                visit(child)
        elif isinstance(item, dict):
            identifier = item.get("id")
            if identifier in SOURCE_SCOPE["mr_records"] and "transcription_sha256" in item:
                source = SOURCE_SCOPE["mr_records"][identifier]
                assert item == source["after"], "exact source-scope comparison inverse"
                item.clear()
                item.update(deepcopy(source["before"]))
            if identifier in BY_ID and "transcription_sha256" in item:
                row = BY_ID[identifier]
                assert item["transcription_sha256"] == row["after_sha256"], diagnostic
                item["transcription_sha256"] = row["before_sha256"]
                identity = {key: field for key, field in item.items() if key != "review"}
                assert canonical_hash(identity) == row["before_identity_sha256"], diagnostic
            if identifier in REVIEWS and "review" in item:
                old = REVIEWS[identifier]["before_sha256"]
                new = expected_review(identifier, old)
                assert item["review"] == {"status": "reviewed", "sha256": new}, diagnostic
                item["review"] = {"status": "reviewed", "sha256": old}
            for child in item.values():
                visit(child)

    visit(result)
    return result
