"""The rights gate: watched failing before it landed."""

import json
from pathlib import Path

from checks.rights import STATUSES, check, cited, exposure, load

CORPUS = Path(__file__).resolve().parent.parent


def test_the_registry_the_corpus_ships_is_complete():
    works, errors = load(CORPUS)
    assert errors == []
    assert works, "a registry with no works would pass every other test vacuously"


def test_every_work_declares_a_status_and_a_basis():
    works, _ = load(CORPUS)
    for title, work in works.items():
        assert work["rights"]["status"] in STATUSES, title
        assert work["rights"]["basis"].strip(), title


def test_english_wording_does_not_name_the_latin_vulgate():
    failures = []
    for path in sorted((CORPUS / "texts").rglob("*.json")):
        doc = json.loads(path.read_text())
        for segment in doc["segments"]:
            citations = segment.get("translation_citations", {}).get("en", [])
            if any(citation["title"] == "Biblia Sacra Vulgata" for citation in citations):
                failures.append(f"{doc['id']}:{segment['id']}")

    assert failures == [], (
        "an English wording citation must name the English rendering it follows, "
        f"not the Latin source text: {failures}"
    )


def test_a_citation_outside_the_registry_fails():
    doc = {
        "id": "x",
        "segments": {
            "s01": {
                "translation_citations": [{"title": "A Work Nobody Registered", "locator": "p. 1"}]
            }
        },
    }
    errors = check([doc], {"Known": {"rights": {"status": "own", "basis": "ours"}}})
    assert len(errors) == 1
    assert "A Work Nobody Registered" in errors[0]


def test_a_registered_citation_passes():
    doc = {
        "id": "x",
        "segments": {"s01": {"translation_citations": [{"title": "Known", "locator": "p. 1"}]}},
    }
    assert check([doc], {"Known": {"rights": {"status": "own", "basis": "ours"}}}) == []


def test_only_a_translation_citation_counts_as_wording():
    # A note or an about citation says where to look. It reproduces nothing.
    doc = {
        "id": "x",
        "segments": {"s01": {"translation_citations": [{"title": "W", "locator": "1"}]}},
        "about_citations": [{"title": "W", "locator": "2"}],
        "words": {"w1": {"function_citations": [{"title": "W", "locator": "3"}]}},
    }
    works = {"W": {"rights": {"status": "permission", "basis": "b"}}}
    assert exposure([doc], works)["permission"] == 1
    assert len(cited(doc)) == 3


def test_an_unregistered_wording_citation_is_counted_apart():
    doc = {
        "id": "x",
        "segments": {"s01": {"translation_citations": [{"title": "Stranger", "locator": "1"}]}},
    }
    assert exposure([doc], {})["unregistered"] == 1


def test_a_status_with_no_basis_is_rejected(tmp_path):
    (tmp_path / "sources.json").write_text(
        json.dumps({"works": {"W": {"title": "W", "rights": {"status": "own", "basis": "  "}}}})
    )
    _works, errors = load(tmp_path)
    assert len(errors) == 1
    assert "says nothing" in errors[0]


def test_a_missing_registry_is_a_failure_not_a_default(tmp_path):
    _works, errors = load(tmp_path)
    assert errors and "missing" in errors[0]
