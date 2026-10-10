"""Registry history preserves the reader's JSON address space, not Python equality."""

import copy
import json
from pathlib import Path

import pytest

from build_reader.emit import Table
from checks import identity

CORPUS = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (1, True),
        (1, 1.0),
        (0, False),
        (0, 0.0),
        (0.0, -0.0),
        ({"conj": 1}, {"conj": True}),
        ({"nested": [{"conj": 1}]}, {"nested": [{"conj": 1.0}]}),
        ({"sources": ["editorial", "whitakers"]}, {"sources": ["whitakers", "editorial"]}),
        ("1", 1),
        (None, "null"),
    ],
)
def test_prefix_rejects_different_json_keys_even_when_python_values_compare_equal(old, new):
    assert not identity.is_exact_prefix([old], [new])
    # A different canonical key must also have a different reader table address.
    table = Table([{"value": old}])
    assert table.intern({"value": new}) == 1


def test_prefix_keeps_object_order_tolerance_and_valid_appends():
    old = [{"first": 1, "second": {"a": "ł", "b": [1, 2]}}]
    reordered = [{"second": {"b": [1, 2], "a": "ł"}, "first": 1}]
    assert identity.is_exact_prefix(old, reordered)
    assert identity.is_exact_prefix(old, [*reordered, {"new": True}])
    assert identity.is_exact_prefix([], [None])
    assert Table(old).intern(reordered[0]) == 0
    assert not identity.is_exact_prefix(old, [])


def _fixture(tmp_path, monkeypatch, relative):
    records = json.loads((CORPUS / relative).read_text(encoding="utf-8"))
    target = tmp_path / relative
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(records), encoding="utf-8")
    monkeypatch.setattr(identity, "resolve_ref", lambda corpus, ref: "fixed-base")
    monkeypatch.setattr(
        identity, "committed", lambda corpus, path, ref: records if path == relative else None
    )
    assert identity.check_registry_history(tmp_path, "fixed-base") == []
    return records, target


def _changed(records, family, kind):
    new = copy.deepcopy(records)
    if kind == "shrink":
        new.pop()
    elif kind == "reorder":
        new[0], new[1] = new[1], new[0]
    elif family == "texts":
        new[0] = 1 if kind == "type" else "changed.text"
    elif family == "morphology":
        new[2]["conj"] = True if kind == "type" else 2
    elif family == "analysis":
        new[0]["sources"][0] = True if kind == "type" else "changed-source"
    else:
        new[0]["locator"] = True if kind == "type" else "changed locator"
    return new


@pytest.mark.parametrize("relative", identity.REGISTRY_FILES)
@pytest.mark.parametrize("kind", ["type", "value", "shrink", "reorder"])
def test_production_history_rejects_old_record_changes_and_restores(
    tmp_path, monkeypatch, relative, kind
):
    records, target = _fixture(tmp_path, monkeypatch, relative)
    family = Path(relative).stem
    target.write_text(json.dumps(_changed(records, family, kind)), encoding="utf-8")
    errors = identity.check_registry_history(tmp_path, "fixed-base")
    assert len(errors) == 1 and "not an exact prefix" in errors[0]
    assert errors[0].startswith(relative + ":")
    target.write_text(json.dumps(records), encoding="utf-8")
    assert identity.check_registry_history(tmp_path, "fixed-base") == []


@pytest.mark.parametrize("relative", identity.REGISTRY_FILES)
def test_production_history_allows_only_appended_addresses(tmp_path, monkeypatch, relative):
    records, target = _fixture(tmp_path, monkeypatch, relative)
    appended = [*records, "new.text" if Path(relative).stem == "texts" else {"new": "record"}]
    target.write_text(json.dumps(appended), encoding="utf-8")
    assert identity.check_registry_history(tmp_path, "fixed-base") == []
    target.write_text(json.dumps(records), encoding="utf-8")
    assert identity.check_registry_history(tmp_path, "fixed-base") == []


@pytest.mark.parametrize("relative", identity.REGISTRY_FILES[1:])
def test_production_history_tolerates_json_object_key_order(tmp_path, monkeypatch, relative):
    records, target = _fixture(tmp_path, monkeypatch, relative)
    reordered = [dict(reversed(list(row.items()))) for row in records]
    target.write_text(json.dumps(reordered), encoding="utf-8")
    assert identity.check_registry_history(tmp_path, "fixed-base") == []


@pytest.mark.parametrize("value", [True, 1.0])
def test_production_history_rejects_numeric_coercion(tmp_path, monkeypatch, value):
    relative = "build_reader/registry/morphology.json"
    records, target = _fixture(tmp_path, monkeypatch, relative)
    changed = copy.deepcopy(records)
    assert type(changed[2]["conj"]) is int and changed[2]["conj"] == 1
    changed[2]["conj"] = value
    target.write_text(json.dumps(changed), encoding="utf-8")
    assert any(
        "not an exact prefix" in error
        for error in identity.check_registry_history(tmp_path, "fixed-base")
    )
    target.write_text(json.dumps(records), encoding="utf-8")
    assert identity.check_registry_history(tmp_path, "fixed-base") == []
