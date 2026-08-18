"""The merge must lose nothing, and must be undoable."""

import glob
import json
from pathlib import Path

from build_reader.merge import load, merge, split

CORPUS = Path(__file__).resolve().parent.parent
IDS = sorted(
    f"{Path(p).parent.name}.{Path(p).stem}" for p in glob.glob(str(CORPUS / "texts/*/*.json"))
)


def test_every_text_in_the_corpus_survives_a_round_trip():
    # The whole proof. A merge that cannot be taken apart again is a migration
    # nobody can undo, and 111 texts is too many to undo by hand.
    for text_id in IDS:
        text, glosses = load(CORPUS, text_id)
        back_text, back_glosses = split(merge(text, glosses))
        assert back_text == text, text_id
        for lang in ("pl", "en"):
            assert back_glosses[lang] == glosses[lang], f"{text_id}/{lang}"


def test_the_editorial_layer_leaves_the_reading():
    text, glosses = load(CORPUS, "ordinarium.credo")
    doc = merge(text, glosses)
    for gone in ("status", "notes", "source", "analysis_defaults", "analysis_defaults_words"):
        assert gone not in doc, gone
        assert gone in doc["editorial"] or gone.startswith("analysis") is False
    for segment in doc["segments"]:
        for word in segment.get("words") or []:
            assert "analysis" not in word


def test_a_word_carries_the_latin_and_both_glosses_together():
    text, glosses = load(CORPUS, "proprium.dominica-iv-adventus-communio")
    doc = merge(text, glosses)
    word = doc["segments"][0]["words"][1]
    assert word["form"] == "Virgo"
    assert set(word["gloss"]) == {"pl", "en"}
    assert word["morph"]["case"] == "nom"


def test_per_word_analysis_moves_to_the_editorial_block():
    # 166 words carry their own analysis. None may be lost, and none may stay.
    found = 0
    for text_id in IDS:
        text, glosses = load(CORPUS, text_id)
        carried = {
            w["id"]: w["analysis"]
            for s in text["segments"]
            for w in (s.get("words") or [])
            if w.get("analysis")
        }
        doc = merge(text, glosses)
        stored = {k: v["analysis"] for k, v in (doc["editorial"].get("words") or {}).items()}
        assert stored == carried, text_id
        found += len(carried)
    assert found > 100, "a test that finds nothing proves nothing"


def test_citations_stay_attached_to_the_language_that_made_the_claim():
    text, glosses = load(CORPUS, "proprium.dominica-iv-adventus-communio")
    doc = merge(text, glosses)
    cites = doc["segments"][0]["translation_citations"]
    assert set(cites) == {"pl", "en"}
    assert cites["pl"][0]["locator"] == "Isaiah 7:14"


def test_a_merged_document_is_not_larger_than_its_three_sources():
    total = merged = 0
    for text_id in IDS:
        text, glosses = load(CORPUS, text_id)
        total += len(json.dumps(text, ensure_ascii=False))
        total += sum(len(json.dumps(g, ensure_ascii=False)) for g in glosses.values())
        merged += len(json.dumps(merge(text, glosses), ensure_ascii=False))
    assert merged < total, f"{merged} against {total}"


def test_a_null_key_is_rejected():
    from checks.lint import lint_nulls

    doc = {
        "id": "t",
        "segments": [
            {"id": "s01", "type": "rubric", "narrative": None},
            {"id": "s02", "type": "verse", "words": [{"id": "w001", "post": None}]},
        ],
    }
    errors = lint_nulls(doc)
    assert len(errors) == 2
    assert "narrative" in errors[0] and "post" in errors[1]


def test_the_corpus_carries_no_null_keys():
    from checks.lint import lint_nulls

    for text_id in IDS:
        text, _ = load(CORPUS, text_id)
        assert lint_nulls(text) == [], text_id


def test_a_note_range_follows_the_text_and_not_the_number_line():
    # Minted ids are not contiguous. A word inserted inside a cited range takes
    # the next free number and sits between its neighbours, and a range read
    # arithmetically would walk past it and report ids that do not exist.
    from checks.lint import lint_notes

    doc = {
        "id": "t",
        "notes": 'The pair "alpha beta gamma" at w001-w003 carries it.',
        "segments": [
            {
                "id": "s01",
                "type": "verse",
                "words": [
                    {"id": "w001", "form": "alpha", "lemma": "a", "morph": {"pos": "adv"}},
                    {"id": "w009", "form": "beta", "lemma": "b", "morph": {"pos": "adv"}},
                    {"id": "w003", "form": "gamma", "lemma": "c", "morph": {"pos": "adv"}},
                ],
            }
        ],
    }
    assert lint_notes(doc) == []
