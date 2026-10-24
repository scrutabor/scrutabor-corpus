"""Bounded Polish sentence and consecration capitals with retained context."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from checks import interlinear, language_packs
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
SLUGS = ("credo", "qui-pridie", "qui-pridie-in-cena-domini")
FORMULAE = (("qui-pridie", "s11", "w043"), ("qui-pridie-in-cena-domini", "s12", "w050"))
CASES = (
    ("credo", "word", "w128", "Który", "który"),
    (
        "qui-pridie",
        "translation",
        "s11",
        "To jest bowiem Ciało Moje.",
        "To jest bowiem Ciało moje.",
    ),
    ("qui-pridie", "word", "w043", "Moje", "moje"),
    (
        "qui-pridie-in-cena-domini",
        "translation",
        "s12",
        "To jest bowiem Ciało Moje.",
        "To jest bowiem Ciało moje.",
    ),
    ("qui-pridie-in-cena-domini", "word", "w050", "Moje", "moje"),
)
NOTE = (
    "Zaimek odnosi się do Jezusa mówiącego do uczniów. "
    "Nie oznacza ciała kapłana, który wypowiada te słowa."
)


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise AssertionError(message)


@pytest.fixture(scope="module")
def documents():
    docs = {}
    for slug in SLUGS:
        rel = f"texts/ordinarium/{slug}.json"
        docs[slug] = {
            "core": read(rel),
            "pl": read("languages/pl/" + rel),
            "en": read("languages/en/" + rel),
        }
    docs["provenance"] = read("languages/pl/translation-provenance.json")["sites"]
    return docs


def field(layer, kind, key):
    return layer["words"][key]["gloss"] if kind == "word" else layer["segments"][key]["translation"]


def assert_targets(docs):
    for slug, kind, key, wanted, _ in CASES:
        require(
            field(docs[slug]["pl"], kind, key) == wanted,
            f"Protected Polish field: {slug}:{kind}:{key}",
        )
    credo = docs["credo"]["pl"]
    require(
        credo["segments"]["s15"]["translation"]
        == "Który z Ojcem i Synem wspólnie odbiera uwielbienie i chwałę: "
        "który mówił przez Proroków.",
        "Credo retained complete sentence",
    )
    for key in ("w123", "w137"):
        require(
            credo["words"][key]["gloss"] == "który",
            "Credo internal relative remains lowercase",
        )
    require(
        docs["qui-pridie-in-cena-domini"]["pl"]["words"]["w050"]["explanation"] == NOTE,
        "Retained Jesus first-person explanation",
    )


def assert_provenance(docs):
    for slug, segment, _ in FORMULAE:
        site = f"ordinarium.{slug}.{segment}.pl"
        matches = [row for row in docs["provenance"] if row["site"] == site]
        require(len(matches) == 1, f"Protected formula provenance: {site}")
        row = matches[0]
        source = next(s for s in docs[slug]["core"]["segments"] if s["id"] == segment)
        require(
            row["origin"] == "public-domain"
            and row["familiar_core"] is False
            and row["review"] == "working"
            and row["source_sha256"] == canonical_hash(source_payload(source))
            and row["target_sha256"]
            == canonical_hash(docs[slug]["pl"]["segments"][segment]["translation"]),
            f"Protected formula provenance: {site}",
        )


def test_actual_authorized_fields_and_unchanged_formula_context(documents):
    assert_targets(documents)
    assert_provenance(documents)
    credo = documents["credo"]["core"]
    words = {w["id"]: w for s in credo["segments"] for w in s.get("words", [])}
    assert words["w127"]["post"] == "."
    assert words["w128"]["form"] == "Qui"
    assert documents["credo"]["en"]["words"]["w128"]["gloss"] == "who"
    for slug, segment, word in FORMULAE:
        source = next(s for s in documents[slug]["core"]["segments"] if s["id"] == segment)
        assert [w["form"] for w in source["words"]] == ["Hoc", "est", "enim", "Corpus", "meum"]
        assert source["words"][-1]["id"] == word
        assert source["speaker"] == "sacerdos" and source["voice"] == "secreto"
        assert documents[slug]["en"]["segments"][segment]["translation"] == "For this is My Body."


@pytest.mark.parametrize("slug", SLUGS)
@pytest.mark.parametrize("language", ("pl", "en"))
def test_actual_native_layer_and_interlinear_contracts(documents, slug, language):
    core, layer = documents[slug]["core"], documents[slug][language]
    assert language_packs.check_core(core) == []
    path = ROOT / f"languages/{language}/texts/ordinarium/{slug}.json"
    assert language_packs.check_layer(core, layer, path) == []
    assert interlinear.check(core, layer) == []


@pytest.mark.parametrize("slug,kind,key,wanted,lowercase", CASES)
def test_each_lowercase_regression_is_rejected_with_healthy_controls(
    documents, slug, kind, key, wanted, lowercase
):
    assert_targets(documents)
    bad = deepcopy(documents)
    if kind == "word":
        bad[slug]["pl"]["words"][key]["gloss"] = lowercase
    else:
        bad[slug]["pl"]["segments"][key]["translation"] = lowercase
    with pytest.raises(AssertionError) as caught:
        assert_targets(bad)
    assert str(caught.value) == f"Protected Polish field: {slug}:{kind}:{key}"
    assert_targets(documents)


@pytest.mark.parametrize("word", ("w123", "w137"))
def test_no_blanket_relative_capitalization(documents, word):
    assert_targets(documents)
    bad = deepcopy(documents)
    bad["credo"]["pl"]["words"][word]["gloss"] = "Który"
    with pytest.raises(AssertionError) as caught:
        assert_targets(bad)
    assert str(caught.value) == "Credo internal relative remains lowercase"
    assert_targets(documents)


def test_missing_explanation_reaches_actual_native_topology_diagnostic(documents):
    actual = documents["qui-pridie-in-cena-domini"]
    core, layer = actual["core"], actual["pl"]
    path = ROOT / "languages/pl/texts/ordinarium/qui-pridie-in-cena-domini.json"
    assert language_packs.check_layer(core, layer, path) == []
    bad = deepcopy(layer)
    del bad["words"]["w050"]["explanation"]
    assert (
        "pl:ordinarium.qui-pridie-in-cena-domini: explanation topology differs — "
        "missing=['w050'] extra=[]" in language_packs.check_layer(core, bad, path)
    )
    assert language_packs.check_layer(core, layer, path) == []


@pytest.mark.parametrize(
    "slug,segment,key",
    (
        ("qui-pridie", "s11", "target_sha256"),
        ("qui-pridie", "s11", "review"),
        ("qui-pridie-in-cena-domini", "s12", "target_sha256"),
    ),
)
def test_stale_hash_or_carried_review_is_rejected(documents, slug, segment, key):
    assert_provenance(documents)
    bad = deepcopy(documents)
    site = f"ordinarium.{slug}.{segment}.pl"
    row = next(row for row in bad["provenance"] if row["site"] == site)
    row[key] = "0" * 64 if key == "target_sha256" else "internally-reviewed"
    with pytest.raises(AssertionError) as caught:
        assert_provenance(bad)
    assert str(caught.value) == f"Protected formula provenance: {site}"
    assert_provenance(documents)
