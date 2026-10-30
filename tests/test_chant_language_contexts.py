"""Preserve local chant referents and distinct translation-origin labels."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from possessive_sweep_b2_successor_fixture import before_possessive_b2_layer

from build_reader import store
from checks import interlinear
from checks.translation_provenance import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
ANNUNCIATION = "proprium.annuntiatio-beatae-mariae-virginis-graduale"
ALBIS = (
    "proprium.dominica-in-albis-offertorium",
    "proprium.dominica-in-albis-communio",
)
PRONOUNS = {
    "pl": {"w006": "twoich", "w009": "ciebie", "w021": "cię", "w024": "twoja"},
    "en": {"w006": "your", "w009": "you", "w021": "you", "w024": "your"},
}
PL_PROSE = (
    "Łaska rozlała się na twoich wargach, dlatego Bóg pobłogosławił cię na wieki. "
    "Ze względu na prawdę i łagodność, i sprawiedliwość – a twoja prawica "
    "przedziwnie cię poprowadzi."
)


def assert_addressee(layer, language):
    actual = {word: layer["words"][word]["gloss"] for word in PRONOUNS[language]}
    assert actual == PRONOUNS[language], "chant addressee"
    assert layer["words"]["w010"]["gloss"] == {"pl": "Bóg", "en": "God"}[language]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_annunciation_retains_its_marian_application_and_divine_agent(language):
    layer = store.raw_layer(ROOT, language, ANNUNCIATION)
    assert_addressee(before_possessive_b2_layer(layer), language)


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("word", ["w006", "w009", "w021", "w024"])
def test_divine_addressee_capital_does_not_silently_replace_this_reading(language, word):
    original = before_possessive_b2_layer(store.raw_layer(ROOT, language, ANNUNCIATION))
    assert_addressee(original, language)
    changed = deepcopy(original)
    changed["words"][word]["gloss"] = changed["words"][word]["gloss"].capitalize()
    try:
        with pytest.raises(AssertionError, match="chant addressee"):
            assert_addressee(changed, language)
    finally:
        changed["words"][word]["gloss"] = original["words"][word]["gloss"]
    assert changed == original
    assert_addressee(changed, language)
    assert_addressee(original, language)


def test_annunciation_polish_prose_and_future_caption():
    assert store.raw_layer(ROOT, "pl", ANNUNCIATION)["segments"]["s01"]["translation"] == PL_PROSE
    assert store.raw_layer(ROOT, "en", ANNUNCIATION)["words"]["w020"]["gloss"] == "will lead"


@pytest.mark.parametrize("text", ALBIS)
def test_albis_own_wording_does_not_imply_completed_review(text):
    ledger = json.loads((ROOT / "languages/en/translation-provenance.json").read_bytes())
    rows = [row for row in ledger["sites"] if row["site"] == text + ".s01.en"]
    assert len(rows) == 1
    row = rows[0]
    assert row["origin"] == "own"
    assert row["review"] == "working"
    assert row["familiar_core"] is False
    prose = store.raw_layer(ROOT, "en", text)["segments"]["s01"]["translation"]
    assert row["target_sha256"] == canonical_hash(prose)


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("text", [ANNUNCIATION, *ALBIS])
def test_every_source_word_retains_one_caption(text, language):
    assert interlinear.check(store.core(ROOT, text), store.raw_layer(ROOT, language, text)) == []


ISAIAH_COMMUNIONS = (
    "proprium.annuntiatio-beatae-mariae-virginis-communio",
    "proprium.annuntiatio-beatae-mariae-virginis-tempore-paschali-communio",
)


def assert_initial_ecce(core, layer):
    assert core["id"] in ISAIAH_COMMUNIONS
    first = core["segments"][0]
    assert first["id"] == "s01"
    assert first["words"][0]["id"] == "w001"
    assert first["words"][0]["form"] == "Ecce"
    assert layer["words"]["w001"]["gloss"] == "Oto", "sentence-initial Ecce"


@pytest.mark.parametrize("text", ISAIAH_COMMUNIONS)
def test_annunciation_communion_polish_first_caption_starts_its_sentence(text):
    core = store.core(ROOT, text)
    original = store.raw_layer(ROOT, "pl", text)
    assert_initial_ecce(core, original)
    assert interlinear.check(core, original) == []
    changed = deepcopy(original)
    previous = changed["words"]["w001"]["gloss"]
    assert previous != "oto"
    changed["words"]["w001"]["gloss"] = "oto"
    try:
        with pytest.raises(AssertionError, match="sentence-initial Ecce"):
            assert_initial_ecce(core, changed)
    finally:
        changed["words"]["w001"]["gloss"] = previous
    assert changed == original
    assert_initial_ecce(core, changed)
    assert interlinear.check(core, changed) == []
    assert_initial_ecce(core, original)
