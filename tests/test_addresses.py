"""The text half of a word's global address: each rule watched failing."""

import json
from pathlib import Path

from checks.addresses import check, load

CORPUS = Path(__file__).resolve().parent.parent


def repo(tmp_path, moved):
    (tmp_path / "redirects.json").write_text(json.dumps({"moved": moved}), encoding="utf-8")
    return tmp_path


def test_the_corpus_as_it_stands_is_clean():
    import glob

    ids = {
        f"{Path(p).parent.name}.{Path(p).stem}" for p in glob.glob(str(CORPUS / "texts/*/*.json"))
    }
    assert check(CORPUS, ids) == []


def test_a_missing_record_is_a_failure_not_a_default(tmp_path):
    _moved, errors = load(tmp_path)
    assert errors and "missing" in errors[0]


def test_a_retired_id_may_not_name_new_content(tmp_path):
    # The whole point. If `orationes.salve` is retired and then reused, every
    # reference to the old text silently resolves to a different one.
    where = repo(
        tmp_path, [{"from": "orationes.salve", "to": "orationes.salve-regina", "why": "renamed"}]
    )
    errors = check(where, {"orationes.salve", "orationes.salve-regina"})
    assert any("may never name new content" in e for e in errors)


def test_a_move_to_nowhere_fails(tmp_path):
    where = repo(tmp_path, [{"from": "a.b", "to": "c.d", "why": "renamed"}])
    assert any("is not a text" in e for e in check(where, {"x.y"}))


def test_a_withdrawal_needs_no_target(tmp_path):
    where = repo(tmp_path, [{"from": "a.b", "to": None, "why": "withdrawn, never printed"}])
    assert check(where, {"x.y"}) == []


def test_a_move_without_a_reason_fails(tmp_path):
    where = repo(tmp_path, [{"from": "a.b", "to": None, "why": "  "}])
    assert any("without a reason" in e for e in check(where, {"x.y"}))


def test_the_record_is_append_only(tmp_path):
    where = repo(
        tmp_path,
        [
            {"from": "a.b", "to": None, "why": "one"},
            {"from": "a.b", "to": None, "why": "again"},
        ],
    )
    assert any("listed twice" in e for e in check(where, {"x.y"}))


def test_a_chain_of_moves_resolves(tmp_path):
    where = repo(
        tmp_path,
        [
            {"from": "a.one", "to": "a.two", "why": "first rename"},
            {"from": "a.two", "to": "a.three", "why": "second rename"},
        ],
    )
    assert check(where, {"a.three"}) == []
