"""Neutral cores and language packs meet without sharing stored files."""

import json
from pathlib import Path

from build_reader.layers import enrich_layer, expand_core
from build_reader.store import (
    core,
    language_ids,
    language_manifest,
    languages_for,
    load,
    raw_layer,
    text_ids,
)

CORPUS = Path(__file__).resolve().parent.parent
IDS = text_ids(CORPUS)


def test_every_stored_document_expands_into_the_checking_views():
    for text_id in IDS:
        stored = core(CORPUS, text_id)
        text, layers = load(CORPUS, text_id)
        assert expand_core(stored) == text
        for language, layer in layers.items():
            assert enrich_layer(stored, raw_layer(CORPUS, language, text_id)) == layer


def test_the_editorial_layer_leaves_the_reading():
    doc = core(CORPUS, "ordinarium.credo")
    for gone in ("status", "notes", "source", "analysis_defaults", "analysis_defaults_words"):
        assert gone not in doc, gone
        assert gone in doc["editorial"] or gone.startswith("analysis") is False
    for segment in doc["segments"]:
        for word in segment.get("words") or []:
            assert "analysis" not in word


def test_a_word_and_each_gloss_live_in_different_files():
    text, glosses = load(CORPUS, "proprium.dominica-iv-adventus-communio")
    word = text["segments"][0]["words"][1]
    assert word["form"] == "Virgo"
    assert "gloss" not in word
    assert glosses["pl"]["words"][word["id"]]["gloss"] == "Dziewica"
    assert glosses["en"]["words"][word["id"]]["gloss"] == "a Virgin"
    assert word["morph"]["case"] == "nom"


def test_per_word_analysis_moves_to_the_editorial_block():
    # 166 words carry their own analysis. None may be lost, and none may stay.
    found = 0
    for text_id in IDS:
        text, _glosses = load(CORPUS, text_id)
        carried = {
            w["id"]: w["analysis"]
            for s in text["segments"]
            for w in (s.get("words") or [])
            if w.get("analysis")
        }
        doc = core(CORPUS, text_id)
        stored = {k: v["analysis"] for k, v in (doc["editorial"].get("words") or {}).items()}
        assert stored == carried, text_id
        found += len(carried)
    assert found > 100, "a test that finds nothing proves nothing"


def test_translation_citations_stay_in_the_language_that_made_the_wording_choice():
    text_id = "proprium.dominica-iv-adventus-communio"
    pl = raw_layer(CORPUS, "pl", text_id)
    en = raw_layer(CORPUS, "en", text_id)
    pl_cited = next(entry for entry in pl["segments"].values() if "translation_citations" in entry)
    en_cited = next(entry for entry in en["segments"].values() if "translation_citations" in entry)
    assert pl_cited["translation_citations"][0]["locator"] == "Isaiah 7:14"
    assert en_cited["translation_citations"] != pl_cited["translation_citations"]
    assert "translation_citations" not in core(CORPUS, text_id)["segments"][0]


def test_every_language_can_cover_a_strict_subset_without_touching_another():
    all_ids = set(IDS)
    for language in language_ids(CORPUS):
        covered = set(language_manifest(CORPUS, language)["texts"])
        assert covered <= all_ids


def test_a_language_manifest_can_publish_one_of_two_neutral_texts(tmp_path):
    for text_id in ("orationes.alpha", "orationes.beta"):
        path = tmp_path / "texts/orationes" / f"{text_id.split('.')[1]}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"id": text_id}), encoding="utf-8")
    manifest = tmp_path / "languages/zz/manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps({"language": "zz", "direction": "ltr", "texts": ["orationes.beta"]}),
        encoding="utf-8",
    )

    assert text_ids(tmp_path) == ["orationes.alpha", "orationes.beta"]
    assert language_ids(tmp_path) == ["zz"]
    assert languages_for(tmp_path, "orationes.alpha") == []
    assert languages_for(tmp_path, "orationes.beta") == ["zz"]


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
