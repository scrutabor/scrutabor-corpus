"""Context-specific Mary referents and the complete Purification petition."""

from pathlib import Path

import pytest

from build_reader import store
from checks import interlinear
from checks.translation_provenance import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
PURIF = "proprium.purificatio-beatae-mariae-virginis-postcommunio"
EASTER = "proprium.dominica-resurrectionis-sequentia"
DEAD = "proprium.commemoratio-omnium-fidelium-defunctorum-missa-i-sequentia"


@pytest.mark.parametrize("text,word,expected", [(DEAD, "w133", "Marię"), (EASTER, "w027", "Mario")])
def test_contextual_polish_names(text, word, expected):
    assert store.raw_layer(ROOT, "pl", text)["words"][word]["gloss"] == expected


@pytest.mark.parametrize(
    "phrase",
    [
        "through the intercession of blessed Mary, ever Virgin",
        "the most holy mysteries",
        "You have bestowed to safeguard our restoration",
        "make the most holy mysteries",
        "a remedy for us both now and in the future",
    ],
)
def test_purification_petition_preserves_its_distinct_units(phrase):
    assert phrase in store.raw_layer(ROOT, "en", PURIF)["segments"]["s01"]["translation"]


def test_purification_conclusion_and_separate_response():
    layer = store.raw_layer(ROOT, "en", PURIF)
    assert layer["segments"]["s01"]["translation"].endswith(
        "Through our Lord Jesus Christ, Your Son, who lives and reigns with You "
        "in the unity of the Holy Spirit, God, forever and ever."
    )
    assert layer["segments"]["s02"]["translation"] == "Amen."


def test_purification_prose_is_still_a_hash_bound_working_translation():
    import json

    ledger = json.loads((ROOT / "languages/en/translation-provenance.json").read_bytes())
    entry = next(e for e in ledger["sites"] if e["site"] == PURIF + ".s01.en")
    prose = store.raw_layer(ROOT, "en", PURIF)["segments"]["s01"]["translation"]
    assert entry["target_sha256"] == canonical_hash(prose)
    assert entry["origin"] == "working-unsettled"
    assert entry["review"] == "working"


def test_familiar_easter_prose_is_not_rewritten_with_the_interlinear():
    prose = store.raw_layer(ROOT, "pl", EASTER)["segments"]["s01"]["translation"]
    assert "Powiedz nam, Maryjo, coś widziała w drodze?" in prose


@pytest.mark.parametrize("text", [DEAD, EASTER, PURIF])
@pytest.mark.parametrize("language", ["pl", "en"])
def test_complete_providers_survive_the_local_corrections(text, language):
    assert interlinear.check(store.core(ROOT, text), store.raw_layer(ROOT, language, text)) == []


def test_marys_intercession_remains_present_in_both_word_layers():
    for language, name in [("pl", "Maryi"), ("en", "Mary")]:
        layer = store.raw_layer(ROOT, language, PURIF)
        assert layer["words"]["w016"]["gloss"] == name
        assert layer["words"]["w014"]["gloss"]
        assert layer["words"]["w017"]["gloss"]
        assert layer["words"]["w018"]["gloss"]
