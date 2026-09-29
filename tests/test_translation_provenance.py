import json

import pytest

from build_reader.bibliography import DECISIONS
from checks.translation_provenance import canonical_hash, check, initialize, protected


def text():
    return {
        "schema_version": "0.17.0",
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
        "schema_version": "0.17.0",
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
                    "schema_version": "0.17.0",
                    "language": language,
                    "direction": "ltr",
                    "texts": ["orationes.test"],
                }
            )
        )
        (root / "bibliography.json").write_text(
            json.dumps({"schema_version": "1.4.0", "language": language, "uses": []})
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


def test_paschal_pair_protects_its_inherited_greeting_in_both_languages():
    text_id = "proprium.annuntiatio-beatae-mariae-virginis-alleluia"
    assert protected(text_id, "pl")
    assert protected(text_id, "en")
    assert not protected(text_id, "la")


def set_origin(corpus, origin, language="pl"):
    path = corpus / "languages" / language / "translation-provenance.json"
    ledger = json.loads(path.read_text())
    ledger["sites"][0]["origin"] = origin
    path.write_text(json.dumps(ledger))


def set_basis(corpus, address, decision="RETAIN", role="historical_wording_basis", language="pl"):
    path = corpus / "languages" / language / "bibliography.json"
    graph = json.loads(path.read_text())
    graph["uses"] = [{"role": role, "decision": decision, "address": address}]
    path.write_text(json.dumps(graph))


@pytest.mark.parametrize("origin", ["public-domain", "traditional", "own", "trivial"])
@pytest.mark.parametrize("decision", sorted(DECISIONS))
@pytest.mark.parametrize("role", ["historical_wording_basis", "historical_wording_comparator"])
@pytest.mark.parametrize("kind", ["segment", "text"])
def test_graph_only_wording_origin_matches_retained_basis(tmp_path, origin, decision, role, kind):
    write_text(tmp_path)
    initialize_all(tmp_path)
    set_origin(tmp_path, origin)
    address = {"kind": kind, "text": "orationes.test"}
    if kind == "segment":
        address["segment"] = "s01"
    set_basis(tmp_path, address, decision, role)
    cited = role == "historical_wording_basis" and decision in {"RETAIN", "RETAIN_WITH_CORRECTION"}
    errors, _ = check(tmp_path)
    inherited = origin in {"public-domain", "traditional"}
    if inherited == cited:
        assert errors == []
    else:
        diagnostic = (
            "requires a wording citation" if inherited else "cannot carry a wording citation"
        )
        assert errors == [f"orationes.test.s01.pl: origin={origin} {diagnostic}"]


@pytest.mark.parametrize(
    ("address", "language"),
    [
        ({"kind": "segment", "text": "orationes.test", "segment": "s02"}, "pl"),
        ({"kind": "segment", "text": "orationes.other", "segment": "s01"}, "pl"),
        ({"kind": "text", "text": "orationes.other"}, "pl"),
        ({"kind": "word", "text": "orationes.test", "word": "w001"}, "pl"),
        ({"kind": "lemma", "lemma": "amen"}, "pl"),
        ({"kind": "segment", "text": "orationes.test", "segment": "s01"}, "en"),
        ({"kind": "text", "text": "orationes.test"}, "en"),
    ],
)
def test_unrelated_graph_basis_does_not_cover_a_site(tmp_path, address, language):
    write_text(tmp_path)
    initialize_all(tmp_path)
    set_origin(tmp_path, "public-domain")
    set_basis(tmp_path, address, language=language)
    errors, _ = check(tmp_path)
    assert errors == ["orationes.test.s01.pl: origin=public-domain requires a wording citation"]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_graph_basis_does_not_promote_unsettled_origin(tmp_path, language):
    write_text(tmp_path)
    initialize_all(tmp_path)
    set_basis(tmp_path, {"kind": "text", "text": "orationes.test"}, language=language)
    errors, tally = check(tmp_path)
    assert errors == []
    assert tally == {"working-unsettled": 2}


@pytest.mark.parametrize("origin", ["public-domain", "traditional"])
def test_legacy_wording_citation_remains_supported(tmp_path, origin):
    write_text(tmp_path, cited_pl=True)
    initialize_all(tmp_path)
    set_origin(tmp_path, origin)
    errors, _ = check(tmp_path)
    assert errors == []
