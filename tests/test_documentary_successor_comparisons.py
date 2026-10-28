"""Complete current provenance rows precede their exact historical comparisons."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from documentary_successor_fixture import DATA, before_language_successors

from build_reader import store
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_current_rows_reject_each_changed_field_and_recover_same_container(language):
    relative = f"languages/{language}/translation-provenance.json"
    value = json.loads((ROOT / relative).read_bytes())
    snapshot = deepcopy(value)
    healthy = before_language_successors(relative, value)
    for change in DATA["ledgers"][relative]["rows"]:
        (row,) = [r for r in value["sites"] if r["site"] == change["after"]["site"]]
        core = store.core(ROOT, row["text"])
        layer = store.raw_layer(ROOT, language, row["text"])
        assert language_packs.check_core(core) == []
        assert (
            language_packs.check_layer(core, layer, store.layer_path(ROOT, language, row["text"]))
            == []
        )
        assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
        (segment,) = [s for s in core["segments"] if s["id"] == row["segment"]]
        assert row == change["after"]
        assert row["source_sha256"] == canonical_hash(source_payload(segment))
        assert row["target_sha256"] == canonical_hash(
            layer["segments"][row["segment"]]["translation"]
        )
        saved = deepcopy(row)
        for field in ("source_sha256", "target_sha256", "unexpected"):
            try:
                row[field] = "0" * 64
                assert row != saved
                with pytest.raises(AssertionError, match=r"^exact Joachim target successor$"):
                    before_language_successors(relative, value)
            finally:
                row.clear()
                row.update(saved)
            assert any(r is row for r in value["sites"])
            assert value == snapshot
            assert before_language_successors(relative, value) == healthy
