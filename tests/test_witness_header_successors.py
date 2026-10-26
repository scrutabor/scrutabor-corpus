"""Header privacy is not a new body, source claim or source-review grant."""

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit

import pytest
import witness_header_fixture as header_fixture
from witness_header_fixture import (
    BY_ID,
    DATA,
    REVIEWS,
    TRANSCRIPTS,
    assert_transcript_content,
    before_privacy,
    canonical_hash,
    expected_header_lines,
    expected_review,
    expected_transcript,
)

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = "witnesses/ordinarium.aufer-a-nobis/mr.txt"


def private_locator_header(line):
    matched = re.match(r"^#\s*(local-archive|path)\s*:\s*(.+)$", line)
    if not matched:
        return False
    kind, value = matched.groups()
    if urlsplit(value).scheme in {"https", "http"}:
        return False
    archive = re.fullmatch(
        r"(?:witnesses/raw/|\.\./raw/)([A-Za-z0-9._/-]+)", value.split(maxsplit=1)[0]
    )
    if archive:
        invalid_parts = any(part in {"", ".", ".."} for part in archive[1].split("/"))
        suffix = value.split(maxsplit=1)[1:]
        private_suffix = re.search(
            r"(?<![\w:/])(?:/|~|file:|\.\.?/|[A-Za-z]:[\\/])", " ".join(suffix)
        )
        return invalid_parts or private_suffix is not None
    return kind == "local-archive" or value.startswith(("/", "~", "..", "file:", "witnesses/raw/"))


def locator_errors(root):
    return [
        str(path.relative_to(root))
        for path in sorted((root / "witnesses").rglob("*.txt"))
        if any(private_locator_header(line) for line in path.read_text().splitlines())
    ]


def test_all_bound_transcript_and_review_successor_rows_are_exact():
    assert len(TRANSCRIPTS) == len(BY_ID) == 947
    assert len(REVIEWS) == 34
    assert sum(identifier.startswith("witness.") for identifier in REVIEWS) == 17
    assert sum(identifier.startswith("collation.") for identifier in REVIEWS) == 17
    for relative, row in TRANSCRIPTS.items():
        assert_transcript_content(ROOT, relative)
        assert expected_transcript(relative, row["before_sha256"]) == row["after_sha256"]
    graph = json.loads((ROOT / "bibliography/graph.json").read_text())
    records = {row["id"]: row for field in ("witnesses", "collations") for row in graph[field]}
    for identifier, change in REVIEWS.items():
        target = expected_review(identifier, change["before_sha256"])
        assert records[identifier]["review"] == {"status": "reviewed", "sha256": target}


def test_active_transcripts_have_no_private_filesystem_headers():
    assert any((ROOT / "witnesses").rglob("*.txt"))
    assert locator_errors(ROOT) == []


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("# path: /temporary/source/page", True),
        ("# local-archive: source/page", True),
        ("# path: https://example.invalid/private/page", False),
        ("Body text with # local-archive: is not a locator header.", False),
        ("# path: web/www/missa/Latin/Ordo/Prayers.txt", False),
        ("# local-archive: witnesses/raw/source.txt", False),
        ("# local-archive: witnesses/raw/source.txt (byte-identical to the pinned file)", False),
        ("# path: ../raw/source.txt (lines 12-14)", False),
        ("# path: ../raw/source.txt (lines 1-8); upstream lines 33-40", False),
        ("# path: ../raw/../../private/source.txt", True),
        ("# local-archive: witnesses/raw/../../private/source.txt", True),
        ("# local-archive: witnesses/raw//source.txt", True),
        ("# local-archive: witnesses/raw/source.txt (/private/source.txt)", True),
        ("# path: ../raw/source.txt (local=/private/source.txt)", True),
        ("# path: ../raw/source.txt (../private/source.txt)", True),
    ],
    ids=[
        "absolute-filesystem",
        "relative-archive",
        "public-url",
        "body-text",
        "upstream-source-path",
        "public-repository-archive",
        "public-repository-archive-note",
        "public-sibling-archive",
        "public-sibling-archive-upstream-lines",
        "sibling-archive-escape",
        "root-archive-escape",
        "noncanonical-archive",
        "private-archive-suffix",
        "assigned-private-archive-suffix",
        "relative-private-archive-suffix",
    ],
)
def test_locator_policy_distinguishes_public_locations_and_bodies(line, expected):
    assert private_locator_header(line) is expected


@pytest.mark.parametrize("damage", ["private-header", "body", "public-header"])
def test_real_clean_transcript_copy_rejects_and_same_bytes_recover(tmp_path, monkeypatch, damage):
    relative = SAMPLE
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    saved = (ROOT / relative).read_bytes()
    path.write_bytes(saved)
    assert_transcript_content(tmp_path, relative)
    assert locator_errors(tmp_path) == []
    original = deepcopy(TRANSCRIPTS[relative])
    scoped = deepcopy(original)
    with monkeypatch.context() as patch:
        patch.setitem(TRANSCRIPTS, relative, scoped)
        try:
            addition = {
                "private-header": b"# local-archive: /temporary/source/page\n",
                "body": b"Synthetic corruption of the source body.\n",
                "public-header": b"# note: synthetic extra public metadata\n",
            }[damage]
            changed = addition + saved
            assert changed != saved
            path.write_bytes(changed)
            # Even recomputing the complete digest cannot authorize a new body/header.
            scoped["after_sha256"] = hashlib.sha256(changed).hexdigest()
            assert scoped != original
            if damage == "private-header":
                assert locator_errors(tmp_path) == [relative]
            with pytest.raises(
                AssertionError, match=r"unchanged (public transcript headers|transcript body)"
            ):
                assert_transcript_content(tmp_path, relative)
        finally:
            path.write_bytes(saved)
            scoped.clear()
            scoped.update(original)
        assert scoped == original and path.read_bytes() == saved
        assert locator_errors(tmp_path) == []
        assert_transcript_content(tmp_path, relative)


@pytest.mark.parametrize("damage", ["identity", "digest", "unrelated-field", "review"])
def test_expected_side_comparison_rejects_actual_copy_mutation_and_recovers(damage):
    graph = json.loads((ROOT / "bibliography/graph.json").read_text())
    row = TRANSCRIPTS[SAMPLE]
    observed = next(record for record in graph["witnesses"] if record["id"] == row["witness"])
    changed = deepcopy(observed)

    def check(value):
        historical = before_privacy(value)
        assert historical["id"] == row["witness"]
        assert historical["review"] == {"status": "pending"}
        assert (
            canonical_hash({key: field for key, field in historical.items() if key != "review"})
            == row["before_identity_sha256"]
        )

    check(changed)
    saved = deepcopy(changed)
    if damage == "identity":
        changed["id"] += ".foreign"
    elif damage == "digest":
        changed["transcription_sha256"] = "0" * 64
    elif damage == "unrelated-field":
        changed["independence_basis"] += " Unrelated change."
    else:
        changed["review"] = {"status": "reviewed", "sha256": "0" * 64}
    assert changed != saved
    try:
        with pytest.raises(AssertionError):
            check(changed)
    finally:
        changed.clear()
        changed.update(saved)
    assert changed == saved == observed
    check(changed)


def test_historical_expected_digest_is_not_a_fresh_observation():
    row = TRANSCRIPTS[SAMPLE]
    assert expected_transcript(SAMPLE, row["before_sha256"]) == row["after_sha256"]
    with pytest.raises(AssertionError, match="historical transcript digest"):
        expected_transcript(SAMPLE, row["after_sha256"])
    with pytest.raises(AssertionError, match="known transcript successor identity"):
        expected_transcript(SAMPLE + ".foreign", row["before_sha256"])


def test_required_transcript_mapping_removal_rejects_and_same_copy_recovers(monkeypatch):
    changed = deepcopy(TRANSCRIPTS)
    saved = deepcopy(changed)
    row = changed[SAMPLE]
    with monkeypatch.context() as patch:
        patch.setattr(header_fixture, "TRANSCRIPTS", changed)
        assert expected_transcript(SAMPLE, row["before_sha256"]) == row["after_sha256"]
        del changed[SAMPLE]
        assert changed != saved
        try:
            with pytest.raises(AssertionError, match="known transcript successor identity"):
                expected_transcript(SAMPLE, row["before_sha256"])
        finally:
            changed.clear()
            changed.update(saved)
        assert changed == saved and list(changed) == list(saved)
        assert expected_transcript(SAMPLE, row["before_sha256"]) == row["after_sha256"]


def test_missing_real_review_capture_rejects_and_same_copy_recovers(monkeypatch):
    identifier = next(key for key in REVIEWS if key.startswith("witness."))
    changed = deepcopy(REVIEWS)
    saved = deepcopy(changed)
    row = changed[identifier]
    with monkeypatch.context() as patch:
        patch.setattr(header_fixture, "REVIEWS", changed)
        healthy = expected_review(identifier, row["before_sha256"])
        assert healthy == row["after_sha256"]
        row["after_sha256"] = None
        assert changed != saved
        try:
            with pytest.raises(AssertionError, match="required real source review capture"):
                expected_review(identifier, row["before_sha256"])
        finally:
            changed.clear()
            changed.update(saved)
        assert changed == saved
        assert expected_review(identifier, changed[identifier]["before_sha256"]) == healthy


def test_header_projection_preserves_the_complete_immutable_expected_prefix():
    fixture = json.loads((ROOT / "tests/fixtures/capital-accent-positions.json").read_text())
    prefix = fixture["trinity_collect"]["preceding_header"]
    saved = deepcopy(prefix)
    actual = expected_header_lines("trinity_collect_prefix", prefix)
    rule = DATA["header_lists"]["trinity_collect_prefix"]
    assert actual == prefix[: rule["index"]] + prefix[rule["index"] + 1 :]
    assert prefix == saved
    changed = deepcopy(prefix)
    changed[0] += " Synthetic change."
    assert changed != saved
    try:
        with pytest.raises(AssertionError, match="historical header list"):
            expected_header_lines("trinity_collect_prefix", changed)
    finally:
        changed[:] = saved
    assert changed == prefix == saved
    assert expected_header_lines("trinity_collect_prefix", changed) == actual
