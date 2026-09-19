"""Source boundaries and contextual readings of the Anne and King propers."""

import json
from pathlib import Path

import pytest

from checks.collate import load_witness

CORPUS = Path(__file__).resolve().parents[1]
ANNE = "proprium.sanctae-annae-matris-beatae-mariae-virginis-secreta"
KING = "proprium.d-n-iesu-christi-regis-epistola"


def core(tid):
    return json.loads((CORPUS / "texts" / (tid.replace(".", "/", 1) + ".json")).read_text())


def layer(tid, language):
    return json.loads(
        (
            CORPUS / "languages" / language / "texts" / (tid.replace(".", "/", 1) + ".json")
        ).read_text()
    )


def test_anne_printed_and_digital_endings_are_declared_literal_composites():
    mr, printed = load_witness(CORPUS / "witnesses" / ANNE / "mr.txt")
    digital_meta, digital = load_witness(CORPUS / "witnesses" / ANNE / "do.txt")
    assert "RG115a" in mr["assembly"]
    assert "macro" in digital_meta["assembly"]
    assert "Fílii tui Dómini nostri Iesu Christi mater" in printed
    assert "Per eundem Dominum nostrum Iesum Christum Filium tuum," in printed
    assert printed.endswith("Amen;")
    assert "Dómine, placatus inténde" in digital
    assert "Per eúndem Dóminum nostrum Jesum Christum Fílium tuum," in digital
    assert len(printed.split()) == len(digital.split()) == 50


def test_king_printed_reading_keeps_real_punctuation_and_digital_corrigendum():
    metadata, printed = load_witness(CORPUS / "witnesses" / KING / "mr.txt")
    digital_meta, digital = load_witness(CORPUS / "witnesses" / KING / "do.txt")
    assert "n793" in metadata["location"] and "n794" in metadata["location"]
    assert "in lúmine, qui" in printed
    assert "sánguinem eius remissiónem" in printed
    assert "inhabitáre: et" in printed
    assert "creatúra:" in digital
    assert digital_meta["corrigenda"][0][:2] == ("creatúra", "creatúræ")
    assert len(printed.split()) == len(digital.split()) == 137


@pytest.mark.parametrize("language", ["pl", "en"])
def test_king_implicit_participial_subject_has_a_localized_explanation(language):
    doc = core(KING)
    word = next(w for w in doc["segments"][0]["words"] if w["id"] == "w119")
    assert word["morph"]["case"] == "nom"
    assert word["morph"]["gender"] == "m"
    assert word["ellipsis"] == "subject"
    assert "head" not in word and "substantive" not in word
    assert doc["localization"]["explanations"] == {"w108": {}, "w119": {}}
    target = layer(KING, language)
    assert target["words"]["w108"]["explanation"] != target["words"]["w119"]["explanation"]
    assert ("podmiot" if language == "pl" else "subject") in target["words"]["w119"]["explanation"]


def test_king_conjunctions_and_nominative_subjects_are_not_homographs():
    words = {w["id"]: w for w in core(KING)["segments"][0]["words"]}
    for wid in ("w060", "w062", "w064", "w066", "w124", "w128"):
        assert words[wid]["lemma"] == "sive"
        assert words[wid]["morph"]["pos"] == "conj"
    for wid in ("w068", "w082", "w094"):
        assert words[wid]["morph"]["case"] == "nom"


def test_king_english_retains_the_locative_and_plural_predicates():
    target = layer(KING, "en")
    assert target["words"]["w072"]["gloss"] == "in"
    assert target["words"]["w085"]["gloss"] == "hold together"
    assert target["words"]["w037"]["gloss"] == "of sins"
    passive = next(a for a in target["segments"]["s01"]["alignments"] if "w074" in a["words"])
    assert passive == {"words": ["w074", "w075"], "anchor": "w074", "gloss": "were created"}


def test_anne_english_restores_the_petition_and_two_benefits():
    target = layer(ANNE, "en")
    prose = target["segments"]["s01"]["translation"]
    assert "we pray" in prose
    assert "both our devotion and our salvation" in prose
    assert "holiness" not in prose
    assert target["words"]["w025"]["gloss"] == "they may benefit"
    assert "Through the same our Lord Jesus Christ, Thy Son," in prose
    assert target["segments"]["s02"]["translation"] == "world without end."
    assert target["segments"]["s03"]["translation"] == "Amen."
