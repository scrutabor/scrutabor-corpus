"""The passive meanings remain available without posing as active senses."""

from pathlib import Path

import pytest

from build_reader import emit, store
from checks import interlinear
from checks.lexicon import lint_senses

ROOT = Path(__file__).resolve().parents[1]
QUALIFIED = {
    "pl": "stać się (w stronie biernej)",
    "en": "to become, come to pass (in the passive)",
}


@pytest.mark.parametrize("language", ["pl", "en"])
def test_facio_becoming_sense_is_explicitly_passive(language):
    entry = emit.lexicon_slice(ROOT, language, {"facio"})["facio"]
    assert QUALIFIED[language] in entry["senses"]
    assert len(entry["senses"]) == 4
    assert "fio" in entry["note"]
    assert "factus sum" in entry["note"]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_fio_keeps_its_own_complete_card(language):
    heads = emit.lexicon_slice(ROOT, lemmas={"facio", "fio"})
    senses = emit.lexicon_slice(ROOT, language, {"facio", "fio"})
    assert set(heads) == set(senses) == {"facio", "fio"}
    assert heads["facio"]["head"] == "fácio, fácere, feci, factum"
    assert heads["fio"]["head"] == "fio, fíeri, factus sum"
    assert "factus sum" in senses["fio"]["note"]
    required = "być czynionym" if language == "pl" else "to be done, be made"
    assert required in senses["fio"]["senses"]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_passive_qualifier_is_reader_language_not_export_apparatus(language):
    assert lint_senses(language, {"facio": {"senses": [QUALIFIED[language]]}}, {"facio": {}}) == []


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize(
    ("text", "word_id", "lemma"),
    [
        ("proprium.purificatio-beatae-mariae-virginis-postcommunio", "w024", "facio"),
        ("ordinarium.credo", "w044", "facio"),
        ("ordinarium.credo", "w074", "facio"),
        ("proprium.dominica-ii-post-pentecosten-alleluia", "w011", "facio"),
        ("proprium.sancti-andreae-apostoli-communio", "w006", "fio"),
        ("proprium.dominica-in-sexagesima-epistola", "w103", "facio"),
    ],
)
def test_source_lemma_remains_available_for_every_realization_kind(language, text, word_id, lemma):
    doc, languages = store.load(ROOT, text)
    assert interlinear.check(doc, languages[language]) == []
    word = next(w for s in doc["segments"] for w in s.get("words", []) if w["id"] == word_id)
    assert word["lemma"] == lemma
    entries = emit.lexicon_slice(ROOT, language, {word["lemma"]})
    assert entries[lemma]["senses"]
    if lemma == "facio":
        assert QUALIFIED[language] in entries[lemma]["senses"]
