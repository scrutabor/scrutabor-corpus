import json

from checks.translation_provenance import canonical_hash, check, initialize


def text(target="Words."):
    return {
        "schema_version": "0.14.0",
        "id": "orationes.test",
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
                "translation": {"pl": target, "en": target},
            }
        ],
    }


def write_text(corpus, target="Words."):
    path = corpus / "texts" / "orationes" / "test.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(text(target)))


def test_initialize_covers_both_languages(tmp_path):
    write_text(tmp_path)
    assert initialize(tmp_path) == 0
    doc = json.loads((tmp_path / "translation-provenance.json").read_text())
    assert len(doc["sites"]) == 2
    assert {entry["language"] for entry in doc["sites"]} == {"pl", "en"}
    errors, tally = check(tmp_path)
    assert errors == []
    assert tally == {"working-unsettled": 2}


def test_target_change_makes_the_review_record_stale(tmp_path):
    write_text(tmp_path)
    assert initialize(tmp_path) == 0
    write_text(tmp_path, "Changed.")
    errors, _tally = check(tmp_path)
    assert len([error for error in errors if "stale target_sha256" in error]) == 2


def test_deleting_one_site_fails_coverage(tmp_path):
    write_text(tmp_path)
    assert initialize(tmp_path) == 0
    path = tmp_path / "translation-provenance.json"
    doc = json.loads(path.read_text())
    doc["sites"].pop()
    path.write_text(json.dumps(doc))
    errors, _tally = check(tmp_path)
    assert any("site(s) missing" in error for error in errors)


def test_own_origin_rejects_a_wording_citation(tmp_path):
    doc = text()
    doc["segments"][0]["translation_citations"] = {"pl": [{"title": "A", "locator": "1"}]}
    path = tmp_path / "texts" / "orationes" / "test.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(doc))
    assert initialize(tmp_path) == 0
    provenance = tmp_path / "translation-provenance.json"
    ledger = json.loads(provenance.read_text())
    pl = next(entry for entry in ledger["sites"] if entry["language"] == "pl")
    pl["origin"] = "own"
    provenance.write_text(json.dumps(ledger))
    errors, _tally = check(tmp_path)
    assert any("origin=own cannot carry" in error for error in errors)


def test_hash_is_canonical_for_object_key_order():
    assert canonical_hash({"a": 1, "b": 2}) == canonical_hash({"b": 2, "a": 1})
