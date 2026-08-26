import json

from checks.translation_provenance import canonical_hash, check, initialize


def text():
    return {
        "schema_version": "0.16.0",
        "id": "orationes.test",
        "title": "Test",
        "category": "orationes",
        "segments": [
            {
                "id": "s01",
                "type": "verse",
                "words": [
                    {
                        "id": "w001",
                        "form": "Amen",
                        "lemma": "amen",
                        "morph": {"pos": "intj"},
                    }
                ],
            }
        ],
        "localization": {"about": True},
        "editorial": {},
    }


def layer(language, target="Words.", cited=False):
    segment = {"translation": target}
    if cited:
        segment["translation_citations"] = [{"title": "A", "locator": "1"}]
    return {
        "schema_version": "0.16.0",
        "language": language,
        "text": "orationes.test",
        "about": "About.",
        "segments": {"s01": segment},
        "words": {"w001": {"gloss": "amen"}},
    }


def write_text(corpus, target="Words.", cited_pl=False):
    path = corpus / "texts" / "orationes" / "test.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(text()))
    for language in ("pl", "en"):
        root = corpus / "languages" / language
        localized = root / "texts" / "orationes" / "test.json"
        localized.parent.mkdir(parents=True, exist_ok=True)
        localized.write_text(json.dumps(layer(language, target, cited_pl and language == "pl")))
        (root / "manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": "0.16.0",
                    "language": language,
                    "direction": "ltr",
                    "texts": ["orationes.test"],
                }
            )
        )


def initialize_all(corpus):
    assert initialize(corpus, "pl") == 0
    assert initialize(corpus, "en") == 0


def test_initialize_covers_both_languages(tmp_path):
    write_text(tmp_path)
    initialize_all(tmp_path)
    assert (
        sum(
            len(
                json.loads(
                    (tmp_path / f"languages/{lang}/translation-provenance.json").read_text()
                )["sites"]
            )
            for lang in ("pl", "en")
        )
        == 2
    )
    errors, tally = check(tmp_path)
    assert errors == []
    assert tally == {"working-unsettled": 2}


def test_target_change_makes_the_review_record_stale(tmp_path):
    write_text(tmp_path)
    initialize_all(tmp_path)
    write_text(tmp_path, "Changed.")
    errors, _tally = check(tmp_path)
    assert len([error for error in errors if "stale target_sha256" in error]) == 2


def test_deleting_one_site_fails_coverage(tmp_path):
    write_text(tmp_path)
    initialize_all(tmp_path)
    path = tmp_path / "languages/pl/translation-provenance.json"
    doc = json.loads(path.read_text())
    doc["sites"].pop()
    path.write_text(json.dumps(doc))
    errors, _tally = check(tmp_path)
    assert any("site(s) missing" in error for error in errors)


def test_own_origin_rejects_a_wording_citation(tmp_path):
    write_text(tmp_path, cited_pl=True)
    initialize_all(tmp_path)
    provenance = tmp_path / "languages/pl/translation-provenance.json"
    ledger = json.loads(provenance.read_text())
    ledger["sites"][0]["origin"] = "own"
    provenance.write_text(json.dumps(ledger))
    errors, _tally = check(tmp_path)
    assert any("origin=own cannot carry" in error for error in errors)


def test_hash_is_canonical_for_object_key_order():
    assert canonical_hash({"a": 1, "b": 2}) == canonical_hash({"b": 2, "a": 1})
