"""Purification Mass: the same Latin in different parts of one Mass reads the same way.

The Tract quotes the end of the Gospel, the Communion repeats Luke 2:26 from it and the
Gradual repeats the Introit antiphon. A reader meets them minutes apart, so identical
Latin keeps identical word help unless the context differs. The Communion lacks the
Gospel's *prius* and has *accépit* for *accéperat*, so only its shared terms are compared.
The Nativity preface opens like every preface; its Polish line must stay grammatical.
"""

import copy
from pathlib import Path

import pytest

from build_reader import store
from checks import interlinear

ROOT = Path(__file__).resolve().parents[1]
P = "proprium.purificatio-beatae-mariae-virginis-"
GOSPEL, TRACT, COMMUNION = P + "evangelium", P + "tractus", P + "communio"
INTROIT, GRADUAL = "proprium.dominica-viii-post-pentecosten-introitus", P + "graduale"


def wid(number):
    return f"w{number:03}"


def glosses(layer, first, last):
    return [interlinear.effective_gloss(layer, wid(n)) for n in range(first, last + 1)]


def layer_of(language, text):
    return store.load(ROOT, text)[1][language]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_tract_and_gospel_canticle_share_word_help(language):
    # Tract w033-w063 = Gospel w123-w153 (Luke 2:29-32), token for token.
    tract, gospel = layer_of(language, TRACT), layer_of(language, GOSPEL)
    assert glosses(tract, 33, 63) == glosses(gospel, 123, 153)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_gradual_repeats_the_introit_antiphon_words(language):
    # Introit w001-w019 = Gradual w001-w019 (Ps 47:10-11 up to terræ).
    assert glosses(layer_of(language, INTROIT), 1, 19) == glosses(
        layer_of(language, GRADUAL), 1, 19
    )


TERMS = {
    # language: (respónsum in both glosses, respónsum in both proses,
    # Christum Dómini in both proses)
    "pl": ("zapowiedź", "zapowiedź", "Chrystusa Pańskiego"),
    "en": ("an answer", "an answer", "the Christ of the Lord"),
}


@pytest.mark.parametrize("language", ["pl", "en"])
def test_communion_and_gospel_name_simeons_answer_alike(language):
    gloss_term, prose_term, christ = TERMS[language]
    gospel, communion = layer_of(language, GOSPEL), layer_of(language, COMMUNION)
    # The noun is w077 in the Gospel (grouped with accéperat in English) and w001 in
    # the Communion (grouped with accépit Símeon in English).
    gospel_gloss = interlinear.effective_gloss(gospel, "w077") or interlinear.effective_gloss(
        gospel, "w078"
    )
    communion_gloss = interlinear.effective_gloss(communion, "w001") or interlinear.effective_gloss(
        communion, "w002"
    )
    assert gloss_term in gospel_gloss.lower() and gloss_term in communion_gloss.lower()
    for layer in (gospel, communion):
        prose = layer["segments"]["s01"]["translation"]
        assert prose_term in prose and christ in prose
    assert glosses(gospel, 89, 90) == glosses(communion, 13, 14)


def test_gospel_polish_law_custom_and_spirit():
    layer = layer_of("pl", GOSPEL)
    # legem w011, lege w025 and w044, legis w108: the Law of Moses and of the Lord.
    assert all(
        interlinear.effective_gloss(layer, wid(n)).startswith("Praw") for n in (11, 25, 44, 108)
    )
    # consuetúdinem is custom, as on its card and in the Holy Family Gospel.
    assert interlinear.effective_gloss(layer, "w107") == "zwyczaju"
    # in spíritu as at every other Polish site; accéperat in the contemporary past.
    assert glosses(layer, 93, 94) == ["w", "Duchu"]
    assert interlinear.effective_gloss(layer, "w078") == "otrzymał"


def test_english_prose_shares_the_answer_clause():
    clause = "that he would not see death before he had seen the Christ of the Lord"
    for text in (GOSPEL, COMMUNION):
        assert clause in layer_of("en", text)["segments"]["s01"]["translation"], text


def test_secret_and_postcommunion_english_prose():
    secret = layer_of("en", P + "secreta")
    assert "Your loving-kindness" in secret["segments"]["s01"]["translation"]
    assert interlinear.effective_gloss(secret, "w018") == "loving-kindness"
    # The Purification Postcommunion extends the Low Sunday prayer with Mary's intercession.
    shared = (
        "the most holy mysteries, which You have bestowed to safeguard our restoration, "
        "a remedy for us both now and in the future"
    )
    for text in (P + "postcommunio", "proprium.dominica-in-albis-postcommunio"):
        assert shared in layer_of("en", text)["segments"]["s01"]["translation"], text


def preface_openings():
    for path in sorted((ROOT / "texts/ordinarium").glob("praefatio-*.json")):
        doc, layers = store.load(ROOT, "ordinarium." + path.stem)
        words = [w for s in doc["segments"] for w in s.get("words", [])]
        forms = [w["form"] for w in words]
        if "ágere" in forms:
            i = forms.index("ágere")
            yield doc["id"], words[i - 6]["id"], words[i]["id"], layers


def test_every_preface_opening_reads_as_one_polish_clause():
    openings = list(preface_openings())
    assert len(openings) == 20
    for text, nos, agere, layers in openings:
        pl, en = layers["pl"], layers["en"]
        assert (interlinear.effective_gloss(pl, nos), interlinear.effective_gloss(pl, agere)) == (
            "abyśmy",
            "składali",
        ), text
        assert (interlinear.effective_gloss(en, nos), interlinear.effective_gloss(en, agere)) == (
            "that we should",
            "give",
        ), text


def test_mutations_are_rejected():
    tract = layer_of("en", TRACT)
    gospel = copy.deepcopy(layer_of("en", GOSPEL))
    gospel["words"]["w145"]["gloss"] = "a Light"
    assert glosses(tract, 33, 63) != glosses(gospel, 123, 153)
    communion = copy.deepcopy(layer_of("pl", COMMUNION))
    communion["segments"]["s01"]["translation"] = communion["segments"]["s01"][
        "translation"
    ].replace("zapowiedź", "odpowiedź")
    assert "zapowiedź" not in communion["segments"]["s01"]["translation"]
