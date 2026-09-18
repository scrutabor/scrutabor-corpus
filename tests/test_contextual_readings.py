"""Contextual homonyms and names that a suffix or agreement check cannot settle."""

import json
from pathlib import Path

import pytest

CORPUS = Path(__file__).resolve().parents[1]


def word(text, identifier):
    doc = json.loads((CORPUS / "texts" / f"{text}.json").read_text())
    return next(w for s in doc["segments"] for w in s.get("words", []) if w["id"] == identifier)


@pytest.mark.parametrize(
    "text,identifier",
    [
        ("proprium/sancti-ioachim-confessoris-evangelium", "w001"),
        ("proprium/commemoratio-omnium-fidelium-defunctorum-missa-i-sequentia", "w044"),
    ],
)
def test_liber_means_a_book_not_free(text, identifier):
    token = word(text, identifier)
    assert token["lemma"] == "liber_volumen"
    assert token["morph"]["pos"] == "noun"


@pytest.mark.parametrize(
    "identifier,case",
    [
        ("w003", "gen"),
        ("w008", "gen"),
        ("w009", "nom"),
        ("w011", "acc"),
        ("w015", "acc"),
        ("w016", "nom"),
        ("w021", "acc"),
        ("w038", "acc"),
        ("w039", "nom"),
    ],
)
def test_genealogy_distinguishes_generation_subject_and_object(identifier, case):
    token = word("proprium/sancti-ioachim-confessoris-evangelium", identifier)
    assert token["morph"]["case"] == case
    if identifier in {"w038", "w039"}:
        assert token["lemma"] == "Aram"


@pytest.mark.parametrize(
    "text,identifier,lemma,pos",
    [
        ("dominica-ii-post-epiphaniam-evangelium", "w008", "Cana", "noun"),
        ("dominica-infra-octavam-nativitatis-evangelium", "w058", "Anna", "noun"),
        ("sanctae-annae-matris-beatae-mariae-virginis-epistola", "w035", "linum", "noun"),
        ("dominica-x-post-pentecosten-introitus", "w024", "iacto", "verb"),
        ("dominica-in-septuagesima-epistola", "w049", "pugno", "verb"),
        ("dominica-i-passionis-epistola", "w077", "mediator", "noun"),
        ("dominica-vi-post-epiphaniam-evangelium", "w064", "satum", "noun"),
        ("dominica-xxiv-post-pentecosten-evangelium", "w066", "fuga", "noun"),
        ("nativitas-domini-in-die-epistola", "w171", "amictus", "noun"),
    ],
)
def test_context_selects_the_dictionary_identity(text, identifier, lemma, pos):
    token = word(f"proprium/{text}", identifier)
    assert (token["lemma"], token["morph"]["pos"]) == (lemma, pos)


def layer(language, text):
    return json.loads((CORPUS / "languages" / language / "texts" / f"{text}.json").read_text())


@pytest.mark.parametrize("language,gloss", [("pl", "nieobłudnej"), ("en", "unfeigned")])
def test_non_ficta_is_not_a_double_negative(language, gloss):
    doc = layer(language, "proprium/dominica-i-in-quadragesima-epistola")
    alignment = next(a for a in doc["segments"]["s01"]["alignments"] if "w081" in a["words"])
    assert alignment["words"] == ["w081", "w082"]
    assert alignment["gloss"] == gloss
    assert all("gloss" not in doc["words"][wid] for wid in alignment["words"])


def test_sequence_translations_follow_their_own_latin_stanza():
    doc = layer("en", "proprium/commemoratio-omnium-fidelium-defunctorum-missa-i-sequentia")
    sheep = doc["segments"]["s15"]["translation"]
    accursed = doc["segments"]["s16"]["translation"]
    assert "Your sheep" in sheep and "Your right" in sheep
    assert "flames" not in sheep
    assert "the cursed" in accursed and "the blessed" in accursed
    assert "Your sheep" not in accursed


def test_postcommunion_conclusion_preserves_person_and_addressee():
    doc = layer("en", "proprium/pretiosissimi-sanguinis-domini-nostri-iesu-christi-postcommunio")
    target = doc["segments"]["s01"]["translation"]
    assert "Who liveth and reigneth with Thee" in target
    assert "Who livest" not in target


def test_creaturae_preserves_the_witnessed_genitive():
    token = word("proprium/d-n-iesu-christi-regis-epistola", "w045")
    assert token["form"] == "creatúræ"
    assert token["morph"]["case"] == "gen"
