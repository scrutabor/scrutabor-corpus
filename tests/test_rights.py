"""The rights gate: watched failing before it landed."""

import json
from pathlib import Path

from checks.rights import STATUSES, check, cited, exposure, load, wording_sites

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
    assert (
        check(
            [doc],
            {
                "Known": {
                    "rights": {"status": "own", "basis": "ours"},
                    "cited_for_wording": True,
                }
            },
        )
        == []
    )


def test_wording_flags_must_match_current_translation_citations():
    doc = {
        "text": "x",
        "lang": "en",
        "segments": {
            "s01": {
                "translation": "Words.",
                "translation_citations": [{"title": "Used", "locator": "1"}],
            }
        },
    }
    works = {
        "Used": {"rights": {"status": "public-domain", "basis": "b"}},
        "Stale": {
            "rights": {"status": "public-domain", "basis": "b"},
            "cited_for_wording": True,
        },
    }
    errors = check([doc], works)
    assert len(errors) == 2
    assert any("Used" in error and "not true" in error for error in errors)
    assert any("Stale" in error and "no current translation" in error for error in errors)


def test_only_a_translation_citation_counts_as_wording():
    # A note or an about citation says where to look. It reproduces nothing.
    doc = {
        "text": "x",
        "lang": "en",
        "segments": {
            "s01": {
                "translation": "Words.",
                "translation_citations": [{"title": "W", "locator": "1"}],
            }
        },
        "about_citations": [{"title": "W", "locator": "2"}],
        "words": {"w1": {"function_citations": [{"title": "W", "locator": "3"}]}},
    }
    works = {"W": {"rights": {"status": "permission", "basis": "b"}}}
    assert exposure([doc], works)["permission"] == 1
    assert len(cited(doc)) == 3


def test_an_uncited_translation_is_counted_as_own():
    doc = {
        "text": "x",
        "lang": "pl",
        "segments": {"s01": {"translation": "Własne słowa."}},
    }
    tally, errors = wording_sites([doc], {})
    assert errors == []
    assert tally["own"] == 1
    assert sum(tally.values()) == 1


def test_deleting_a_citation_changes_the_class_not_the_denominator():
    works = {"W": {"rights": {"status": "permission", "basis": "b"}}}
    cited_doc = {
        "text": "x",
        "lang": "en",
        "segments": {
            "s01": {
                "translation": "Words.",
                "translation_citations": [{"title": "W", "locator": "1"}],
            }
        },
    }
    uncited_doc = {
        "text": "x",
        "lang": "en",
        "segments": {"s01": {"translation": "Words."}},
    }
    before, _ = wording_sites([cited_doc], works)
    after, _ = wording_sites([uncited_doc], works)
    assert before["permission"] == 1
    assert after["own"] == 1
    assert sum(before.values()) == sum(after.values()) == 1


def test_one_site_with_several_sources_takes_the_most_restrictive_status():
    works = {
        "Old": {"rights": {"status": "public-domain", "basis": "b"}},
        "Unknown": {"rights": {"status": "unverified", "basis": "b"}},
    }
    doc = {
        "text": "x",
        "lang": "en",
        "segments": {
            "s01": {
                "translation": "Words.",
                "translation_citations": [
                    {"title": "Old", "locator": "1"},
                    {"title": "Unknown", "locator": "2"},
                ],
            }
        },
    }
    tally, errors = wording_sites([doc], works)
    assert errors == []
    assert tally["unverified"] == 1
    assert sum(tally.values()) == 1


def test_a_translation_site_cannot_be_counted_twice():
    doc = {
        "text": "x",
        "lang": "pl",
        "segments": {"s01": {"translation": "Słowa."}},
    }
    tally, errors = wording_sites([doc, doc], {})
    assert tally["own"] == 1
    assert len(errors) == 1
    assert "more than once" in errors[0]


def test_an_unregistered_wording_citation_is_counted_apart():
    doc = {
        "text": "x",
        "lang": "en",
        "segments": {
            "s01": {
                "translation": "Words.",
                "translation_citations": [{"title": "Stranger", "locator": "1"}],
            }
        },
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
