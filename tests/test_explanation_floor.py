"""The floor gate: shrinking the explanation layer must be a recorded act."""

import json
from pathlib import Path

from checks import explanation_floor

CORPUS = Path(__file__).resolve().parent.parent


def corpus_with(tmp_path, declared: dict) -> Path:
    (tmp_path / "texts" / "x").mkdir(parents=True)
    (tmp_path / "texts" / "x" / "t.json").write_text(
        json.dumps({"id": "x.t", "localization": {"explanations": declared}})
    )
    return tmp_path


def floor_file(tmp_path, sites, citations, adjudicated="2026-08-27 — test baseline"):
    p = tmp_path / "floor.json"
    p.write_text(json.dumps({"sites": sites, "citations": citations, "adjudicated": adjudicated}))
    return p


def test_the_corpus_honors_its_recorded_floor():
    assert explanation_floor.check(CORPUS) == []


def test_growth_needs_no_ceremony(tmp_path, monkeypatch):
    monkeypatch.setattr(explanation_floor, "FLOOR", floor_file(tmp_path, 1, 0))
    corpus = corpus_with(tmp_path, {"w001": {}, "w002": {"citations": [{"title": "T"}]}})
    assert explanation_floor.check(corpus) == []


def test_a_lost_site_fails_until_the_floor_is_lowered_with_a_reason(tmp_path, monkeypatch):
    monkeypatch.setattr(explanation_floor, "FLOOR", floor_file(tmp_path, 2, 0))
    corpus = corpus_with(tmp_path, {"w001": {}})
    errors = explanation_floor.check(corpus)
    assert any("removing explanation sites" in e for e in errors), errors


def test_a_lost_citation_fails_on_its_own(tmp_path, monkeypatch):
    monkeypatch.setattr(explanation_floor, "FLOOR", floor_file(tmp_path, 1, 1))
    corpus = corpus_with(tmp_path, {"w001": {}})
    errors = explanation_floor.check(corpus)
    assert any("dropping a cited claim" in e for e in errors), errors


def test_an_undated_floor_is_no_floor(tmp_path, monkeypatch):
    monkeypatch.setattr(explanation_floor, "FLOOR", floor_file(tmp_path, 0, 0, adjudicated=" "))
    corpus = corpus_with(tmp_path, {"w001": {}})
    errors = explanation_floor.check(corpus)
    assert any("names no adjudication" in e for e in errors), errors
