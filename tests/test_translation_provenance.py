import copy
import json
from pathlib import Path

import pytest

from build_reader import bibliography
from build_reader.bibliography import DECISIONS, SCHEMA
from checks.translation_provenance import (
    canonical_hash,
    check,
    corpus_sites,
    initialize,
    load,
    protected,
    source_payload,
)


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
    graph = corpus / "bibliography" / "graph.json"
    graph.parent.mkdir(parents=True, exist_ok=True)
    graph.write_text(
        json.dumps({"schema_version": SCHEMA, "uses": [], "migration": {"removals": []}})
    )
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
            json.dumps({"schema_version": SCHEMA, "language": language, "uses": []})
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


def attach_legacy(corpus, language, count=1):
    path = corpus / "languages" / language / "texts" / "orationes" / "test.json"
    doc = json.loads(path.read_text())
    doc["segments"]["s01"]["translation_citations"] = [
        {"title": "A", "locator": str(index)} for index in range(count)
    ]
    path.write_text(json.dumps(doc))
    return [
        f"languages/{language}/texts/orationes/test.json#/segments/s01/translation_citations/{index}"
        for index in range(count)
    ]


def mapped_uses(corpus, language, refs, decisions, roles=None, addresses=None):
    path = corpus / "languages" / language / "bibliography.json"
    graph = json.loads(path.read_text())
    graph["uses"] = [
        {
            "decision": decision,
            "role": roles[index] if roles else "historical_wording_basis",
            "address": addresses[index]
            if addresses
            else {"kind": "segment", "text": "orationes.test", "segment": "s01"},
            "legacy_refs": [refs[index]],
        }
        for index, decision in enumerate(decisions)
    ]
    path.write_text(json.dumps(graph))


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("origin", ["public-domain", "traditional"])
@pytest.mark.parametrize(
    ("decision", "supported"),
    [
        ("RETAIN", True),
        ("RETAIN_WITH_CORRECTION", True),
        ("REMOVE", False),
        ("REPLACE", False),
        ("UNVERIFIED_NO_DIRECT_EVIDENCE", False),
    ],
)
def test_mapped_legacy_cannot_mask_a_rejected_inherited_basis(
    tmp_path, language, origin, decision, supported
):
    write_text(tmp_path)
    refs = attach_legacy(tmp_path, language)
    initialize_all(tmp_path)
    set_origin(tmp_path, origin, language)
    mapped_uses(tmp_path, language, refs, [decision])
    site = f"orationes.test.s01.{language}"
    assert corpus_sites(tmp_path)[site]["has_wording_citations"] is supported
    errors, _ = check(tmp_path)
    assert errors == ([] if supported else [f"{site}: origin={origin} requires a wording citation"])


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("decision", ["RETAIN", "RETAIN_WITH_CORRECTION"])
def test_retained_comparator_does_not_become_basis_via_its_legacy_ref(tmp_path, language, decision):
    write_text(tmp_path)
    refs = attach_legacy(tmp_path, language)
    initialize_all(tmp_path)
    set_origin(tmp_path, "public-domain", language)
    mapped_uses(tmp_path, language, refs, [decision], ["historical_wording_comparator"])
    errors, _ = check(tmp_path)
    assert errors == [
        f"orationes.test.s01.{language}: origin=public-domain requires a wording citation"
    ]


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize(
    ("decisions", "roles", "supported"),
    [
        (["REMOVE"], None, True),  # The second attachment is genuinely unmapped.
        (["REMOVE", "RETAIN"], None, True),
        (["REMOVE", "REPLACE"], None, False),
        (
            ["REMOVE", "RETAIN"],
            ["historical_wording_basis", "historical_wording_comparator"],
            False,
        ),
    ],
)
def test_mixed_legacy_inputs_preserve_only_the_actual_basis_routes(
    tmp_path, language, decisions, roles, supported
):
    write_text(tmp_path)
    refs = attach_legacy(tmp_path, language, 2)
    initialize_all(tmp_path)
    set_origin(tmp_path, "traditional", language)
    mapped_uses(tmp_path, language, refs, decisions, roles)
    errors, _ = check(tmp_path)
    assert errors == (
        []
        if supported
        else [f"orationes.test.s01.{language}: origin=traditional requires a wording citation"]
    )


@pytest.mark.parametrize("language", ["pl", "en"])
def test_explicit_migration_removal_cannot_supply_unmapped_legacy_basis(tmp_path, language):
    write_text(tmp_path)
    refs = attach_legacy(tmp_path, language)
    initialize_all(tmp_path)
    set_origin(tmp_path, "public-domain", language)
    path = tmp_path / "bibliography" / "graph.json"
    graph = json.loads(path.read_text())
    graph["migration"]["removals"] = [{"legacy_ref": refs[0], "reason": "Unsupported wording."}]
    path.write_text(json.dumps(graph))
    errors, _ = check(tmp_path)
    assert errors == [
        f"orationes.test.s01.{language}: origin=public-domain requires a wording citation"
    ]


@pytest.mark.parametrize(
    ("address", "package"),
    [
        ({"kind": "segment", "text": "orationes.test", "segment": "s02"}, "pl"),
        ({"kind": "text", "text": "orationes.other"}, "pl"),
        ({"kind": "word", "text": "orationes.test", "word": "w001"}, "pl"),
        ({"kind": "lemma", "lemma": "amen"}, "pl"),
        ({"kind": "segment", "text": "orationes.test", "segment": "s01"}, "en"),
    ],
)
def test_mapped_pointer_cannot_bypass_exact_language_or_address_scope(tmp_path, address, package):
    write_text(tmp_path)
    refs = attach_legacy(tmp_path, "pl")
    initialize_all(tmp_path)
    set_origin(tmp_path, "public-domain")
    mapped_uses(tmp_path, package, refs, ["RETAIN"], addresses=[address])
    errors, _ = check(tmp_path)
    assert errors == ["orationes.test.s01.pl: origin=public-domain requires a wording citation"]


def test_mapped_text_scope_basis_and_separate_new_basis_remain_supported(tmp_path):
    write_text(tmp_path)
    refs = attach_legacy(tmp_path, "pl")
    initialize_all(tmp_path)
    set_origin(tmp_path, "public-domain")
    mapped_uses(
        tmp_path, "pl", refs, ["RETAIN"], addresses=[{"kind": "text", "text": "orationes.test"}]
    )
    assert check(tmp_path)[0] == []
    path = tmp_path / "languages/pl/bibliography.json"
    graph = json.loads(path.read_text())
    graph["uses"][0]["decision"] = "REMOVE"
    graph["uses"].append(
        {
            "role": "historical_wording_basis",
            "decision": "RETAIN",
            "legacy_refs": [],
            "address": {"kind": "segment", "text": "orationes.test", "segment": "s01"},
        }
    )
    path.write_text(json.dumps(graph))
    assert check(tmp_path)[0] == []


def test_missing_neutral_decision_input_does_not_silently_enable_legacy_fallback(tmp_path):
    write_text(tmp_path, cited_pl=True)
    (tmp_path / "bibliography/graph.json").unlink()
    with pytest.raises(FileNotFoundError):
        corpus_sites(tmp_path)


@pytest.mark.parametrize(
    "mutation", ["REMOVE", "REPLACE", "UNVERIFIED_NO_DIRECT_EVIDENCE", "COMPARATOR"]
)
def test_real_only_basis_rejection_exposes_inherited_origin_and_restoration(monkeypatch, mutation):
    corpus = Path(__file__).resolve().parent.parent
    graph, languages = bibliography.load(corpus)
    original = copy.deepcopy((graph, languages))
    site = "ordinarium.misereatur.s06.en"
    recorded = copy.deepcopy(load(corpus)[0][site])
    assert recorded["origin"] in {"public-domain", "traditional"}
    assert corpus_sites(corpus)[site]["has_wording_citations"] is True
    target = next(
        use for use in languages["en"]["uses"] if use["id"] == "use.en.20c386fcb82abb0ee345"
    )
    assert target["legacy_refs"] == [
        "languages/en/texts/ordinarium/misereatur.json#/segments/s06/translation_citations/0"
    ]
    if mutation == "COMPARATOR":
        target["role"] = "historical_wording_comparator"
    else:
        target["decision"] = mutation
        target["decision_reason"] = "This use is withheld."
    monkeypatch.setattr(bibliography, "load", lambda _corpus: (graph, languages))
    assert corpus_sites(corpus)[site]["has_wording_citations"] is False
    diagnostic = f"{site}: origin={recorded['origin']} requires a wording citation"
    assert diagnostic in check(corpus)[0]
    monkeypatch.setattr(bibliography, "load", lambda _corpus: original)
    assert corpus_sites(corpus)[site]["has_wording_citations"] is True
    assert diagnostic not in check(corpus)[0]
    assert load(corpus)[0][site] == recorded


@pytest.mark.parametrize("review", ["working", "internally-reviewed", "expert-reviewed"])
def test_source_change_is_stale_until_explicit_rebinding_at_a_permitted_review(tmp_path, review):
    write_text(tmp_path)
    initialize_all(tmp_path)
    for language in ("pl", "en"):
        set_origin(tmp_path, "own", language)
    assert check(tmp_path)[0] == []
    source = tmp_path / "texts/orationes/test.json"
    document = json.loads(source.read_text())
    document["segments"][0]["words"][0]["morph"] = {"pos": "adv"}
    source.write_text(json.dumps(document))
    expected = [f"orationes.test.s01.{language}: stale source_sha256" for language in ("en", "pl")]
    assert check(tmp_path)[0] == expected
    current = canonical_hash(source_payload(document["segments"][0]))
    for language in ("pl", "en"):
        path = tmp_path / "languages" / language / "translation-provenance.json"
        ledger = json.loads(path.read_text())
        site = ledger["sites"][0]
        assert site["source_sha256"] != current
        inherited_target = site["target_sha256"]
        site["source_sha256"] = current
        # Fixture-only explicit review evidence; this does not review any real text.
        site["review"] = review
        assert site["target_sha256"] == inherited_target
        path.write_text(json.dumps(ledger))
    assert check(tmp_path)[0] == []


def test_requiem_shared_formula_protection_is_language_and_segment_bounded():
    expected = {
        ("ordinarium.agnus-dei-defunctorum", "pl", "s01"): True,
        ("ordinarium.agnus-dei-defunctorum", "pl", "s02"): True,
        ("ordinarium.agnus-dei-defunctorum", "pl", "s03"): True,
        ("ordinarium.ite-missa-est-defunctorum", "pl", "s01"): True,
        ("ordinarium.ite-missa-est-defunctorum", "pl", "s02"): True,
        ("ordinarium.ite-missa-est-defunctorum", "pl", "s03"): True,
        ("ordinarium.ite-missa-est-defunctorum", "pl", "s04"): True,
        ("ordinarium.ite-missa-est-defunctorum", "en", "s03"): True,
        ("ordinarium.ite-missa-est-defunctorum", "en", "s04"): True,
    }
    for language in ("pl", "en"):
        expected[("ordinarium.agnus-dei-defunctorum", language, "s99")] = False
        expected[("ordinarium.ite-missa-est-defunctorum", language, "s99")] = False
    for segment in ("s01", "s02", "s03"):
        expected[("ordinarium.agnus-dei-defunctorum", "en", segment)] = False
    for segment in ("s01", "s02"):
        expected[("ordinarium.ite-missa-est-defunctorum", "en", segment)] = False
    expected[("orationes.unrelated-amen", "pl", "s01")] = False
    for (text, language, segment), required in expected.items():
        assert protected(text, language, segment) is required


def test_equivalent_polish_greetings_keep_exact_clause_and_language_boundaries():
    from build_reader import store

    root = Path(__file__).resolve().parents[1]
    data = json.loads((root / "tests/fixtures/polish-greeting-protection.json").read_bytes())
    ledgers = {
        language: {
            row["site"]: row
            for row in json.loads(
                (root / f"languages/{language}/translation-provenance.json").read_bytes()
            )["sites"]
        }
        for language in ("pl", "en")
    }
    assert len(data["cases"]) == 10
    for case in data["cases"]:
        text, sid = case["text"], case["segment"]
        core = store.core(root, text)
        source = next(segment for segment in core["segments"] if segment["id"] == sid)
        assert source["type"] == "verse"
        assert [word["id"] for word in source["words"]] == case["words"]
        assert [word["form"] for word in source["words"]] == case["forms"]
        for language in ("pl", "en"):
            layer = store.raw_layer(root, language, text)
            target = layer["segments"][sid]["translation"]
            assert target == case["polish" if language == "pl" else "english"]
            row = ledgers[language][f"{text}.{sid}.{language}"]
            assert row["source_sha256"] == canonical_hash(source_payload(source))
            assert row["target_sha256"] == canonical_hash(target)
            assert protected(text, language, sid) is (language == "pl")
            assert row["familiar_core"] is (language == "pl")
            assert not protected(text, language, "s99")
    for case in data["negative_neighbours"]:
        for language in ("pl", "en"):
            assert not protected(case["text"], language, case["segment"])
