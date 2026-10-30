"""Finite historical controls beside actual text-only Ordo observations.

The graph inverse is comparison-only. Historical actor fixtures are separate
directories, never normalized arguments or edits to the actual corpus.
"""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from ordo_notes_successor_fixture import before_ordo_notes_graph
from reader_arrow_successor_fixture import before_arrow_graph

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "tests/fixtures/main-ordo-consumer-history.json").read_bytes())


def current_ordo_row(text):
    row = DATA["texts"][text]
    raw = (ROOT / row["witness"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == row["after_sha256"], (
        "complete current main Ordo transcript"
    )
    registry = json.loads((ROOT / "witnesses/raw/bindings.json").read_bytes())
    assert registry["bindings"][row["binding_id"]] == row["binding"], (
        "complete current main Ordo binding"
    )
    assert registry["archives"][DATA["archive_id"]] == DATA["archive"], (
        "complete current main Ordo archive"
    )
    return row


def before_main_ordo_records(records, text):
    """Invert only two complete named additions before the unchanged old oracle."""
    assert text in {"ordinarium.panem-caelestem", "ordinarium.praefatio-dialogus"}
    row = DATA["texts"][text]
    result = deepcopy(before_arrow_graph(before_ordo_notes_graph(records)))
    for collection, name in (("uses", "use_record"), ("witnesses", "witness_record")):
        expected = row[name]
        matches = [item for item in result[collection] if item.get("id") == expected["id"]]
        assert len(matches) == 1 and matches[0] == expected, (
            "complete named main Ordo graph addition"
        )
        result[collection].remove(matches[0])
    return result


def copy_attribution_sources(root, text, *, historical=False):
    """Copy a complete current binding, or an explicit separate old source fixture."""
    assert text in {"ordinarium.panem-caelestem", "ordinarium.lavabo", "ordinarium.kyrie"}
    assert root.resolve() != ROOT.resolve()
    row = current_ordo_row(text)
    folder = ROOT / "witnesses" / text
    for source in folder.iterdir():
        if source.is_file():
            target = root / source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
    if historical:
        assert not (root / "witnesses/raw/bindings.json").exists()
        old = row["before_utf8"].encode("utf-8")
        assert hashlib.sha256(old).hexdigest() == row["before_sha256"]
        current = (root / row["witness"]).read_bytes()

        def body(value):
            return b"".join(
                line for line in value.splitlines(keepends=True) if not line.startswith(b"#")
            )

        assert body(old) == body(current), "unchanged historical/current Ordo body"
        (root / row["witness"]).write_bytes(old)
        archive = DATA["legacy_archive"]
        raw = (ROOT / archive["path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == archive["sha256"]
        target = root / archive["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        return
    archive = DATA["archive"]
    raw = (ROOT / archive["path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == archive["sha256"]
    target = root / archive["path"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    registry = {
        "version": 1,
        "archives": {DATA["archive_id"]: deepcopy(archive)},
        "bindings": {row["binding_id"]: deepcopy(row["binding"])},
    }
    (root / "witnesses/raw/bindings.json").write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
