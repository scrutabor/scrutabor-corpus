"""Source qualifications have an additive exact predecessor, without repairing unknown faults."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from edition_revision_fixture import (
    SOURCE_SCOPE_FILES,
    SOURCE_SCOPE_REVISION,
    before_owner_layer,
    before_owner_revision,
    before_review_layer,
    before_review_revision,
    before_source_scope_revision,
)

ROOT = Path(__file__).resolve().parents[1]
LAYERS = sorted(relative for relative in SOURCE_SCOPE_FILES if "/texts/" in relative)


def test_receipt_names_only_the_twelve_authored_json_subjects_and_four_layer_fields():
    unrelated = b'{"unlisted": true}\n'
    assert before_source_scope_revision("not-a-declared-subject.json", unrelated) is unrelated
    assert SOURCE_SCOPE_REVISION["parent"] == "ef428dbac9f2b876a893e745d5e946d8b0c89c81"
    assert set(SOURCE_SCOPE_FILES) == {
        "bibliography/graph.json",
        "languages/en/bibliography.json",
        "languages/en/texts/orationes/regina-caeli.json",
        "languages/en/texts/psalmi/118-he.json",
        "languages/en/translation-basis.json",
        "languages/en/translation-provenance.json",
        "languages/pl/bibliography.json",
        "languages/pl/texts/orationes/regina-caeli.json",
        "languages/pl/texts/orationes/te-deum.json",
        "languages/pl/translation-basis.json",
        "languages/pl/translation-provenance.json",
        "texts/orationes/regina-caeli.json",
    }
    assert {
        relative: [change["path"] for change in entry["changes"]]
        for relative, entry in SOURCE_SCOPE_FILES.items()
        if "changes" in entry
    } == {
        "languages/en/texts/orationes/regina-caeli.json": [["about"]],
        "languages/en/texts/psalmi/118-he.json": [["words", "w062", "explanation"]],
        "languages/pl/texts/orationes/regina-caeli.json": [["about"]],
        "languages/pl/texts/orationes/te-deum.json": [["translation_label"]],
    }


@pytest.mark.parametrize("relative", sorted(SOURCE_SCOPE_FILES))
def test_exact_source_scope_predecessor_refuses_corrupt_or_unrelated_bytes(relative):
    raw = (ROOT / relative).read_bytes()
    entry = SOURCE_SCOPE_FILES[relative]
    assert hashlib.sha256(raw).hexdigest() == entry["current"]
    previous = before_source_scope_revision(relative, raw)
    assert previous != raw and hashlib.sha256(previous).hexdigest() == entry["previous"]
    assert before_source_scope_revision(relative, previous) is previous
    for damaged in (raw + b" ", raw.replace(b'"', b"'", 1), b'{"unrelated": true}\n'):
        assert before_source_scope_revision(relative, damaged) is damaged
    assert (ROOT / relative).read_bytes() == raw


@pytest.mark.parametrize("relative", LAYERS)
def test_direct_historical_owner_and_review_views_restore_only_declared_source_scope(relative):
    raw = (ROOT / relative).read_bytes()
    previous = before_source_scope_revision(relative, raw)
    current, predecessor = json.loads(raw), json.loads(previous)
    for inverse in (before_owner_revision, before_review_revision):
        assert inverse(relative, raw) == inverse(relative, previous)
        damaged = raw + b" "
        assert inverse(relative, damaged) is damaged
    for inverse in (before_owner_layer, before_review_layer):
        saved = deepcopy(current)
        assert inverse(current) == inverse(predecessor)
        assert current == saved
        faulty = {**deepcopy(current), "unlisted_source_scope_fault": True}
        assert inverse(faulty) == {**inverse(predecessor), "unlisted_source_scope_fault": True}
        path = SOURCE_SCOPE_FILES[relative]["changes"][0]["path"]
        container = faulty
        for field in path[:-1]:
            container = container[field]
        container[path[-1]] = {"unexpected": "qualification changed"}
        altered = deepcopy(faulty)
        result = inverse(faulty)
        for field in path:
            result = result[field]
        assert result == {"unexpected": "qualification changed"}
        assert faulty == altered
