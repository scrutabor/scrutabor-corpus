"""Keep directional carriers complete and unduplicated in selected clauses.

These fixtures concern eight particular direct-caption realizations. They do
not prescribe a single translation for respicio or for every in/ad construction.
"""

import json
from copy import deepcopy

import pytest

from checks.interlinear import effective_gloss
from checks.layout import CORPUS

# Language, text, segment, edited word/lemma, old/new caption, retained verb,
# and the separately realized Latin preposition when there is one.
CASES = [
    (
        "pl",
        "proprium.dominica-i-passionis-collecta",
        "s01",
        "w004",
        "familia",
        "rodzinę",
        "na rodzinę",
        ("w007", "wejrzyj"),
        None,
    ),
    (
        "pl",
        "proprium.dominica-iii-in-quadragesima-collecta",
        "s01",
        "w004",
        "votum",
        "pragnienia",
        "na pragnienia",
        ("w006", "wejrzyj"),
        None,
    ),
    (
        "pl",
        "proprium.dominica-iii-post-epiphaniam-collecta",
        "s01",
        "w004",
        "infirmitas",
        "słabość",
        "na słabość",
        ("w007", "wejrzyj"),
        None,
    ),
    (
        "pl",
        "proprium.dominica-iii-post-pentecosten-secreta",
        "s01",
        "w003",
        "munus",
        "dary",
        "na dary",
        ("w001", "Wejrzyj"),
        None,
    ),
    (
        "en",
        "litaniae.sacratissimi-cordis-iesu",
        "s089",
        "w342",
        "respicio",
        "look upon",
        "look",
        ("w342", "look"),
        ("w343", "in"),
    ),
    (
        "en",
        "proprium.dominica-ii-passionis-introitus",
        "s01",
        "w027",
        "respicio",
        "look upon",
        "look",
        ("w027", "look"),
        ("w028", "in"),
    ),
    (
        "en",
        "proprium.dominica-ii-passionis-tractus",
        "s01",
        "w004",
        "respicio",
        "look upon",
        "look",
        ("w004", "look"),
        ("w005", "in"),
    ),
    (
        "en",
        "proprium.sacratissimi-cordis-iesu-secreta",
        "s01",
        "w001",
        "respicio",
        "Look upon",
        "Look",
        ("w001", "Look"),
        ("w004", "ad"),
    ),
]
CASE_IDS = [f"{case[0]}-{case[1]}" for case in CASES]


def load(text, language):
    category, name = text.split(".", 1)
    path = f"texts/{category}/{name}.json"
    return (
        json.loads((CORPUS / path).read_text()),
        json.loads((CORPUS / "languages" / language / path).read_text()),
    )


def assert_direct(layer, word_id, expected):
    assert not any(
        word_id in group["words"]
        for segment in layer["segments"].values()
        for group in segment.get("alignments", [])
    ), f"{word_id} has a competing alignment provider"
    assert layer["words"][word_id].get("gloss") == expected
    assert effective_gloss(layer, word_id) == expected


def assert_carriers(core, layer, case):
    language, text, segment_id, word_id, lemma, _, caption, verb, carrier = case
    assert core["id"] == layer["text"] == text
    assert layer["language"] == language
    segment = next(segment for segment in core["segments"] if segment["id"] == segment_id)
    words = {word["id"]: word for word in segment["words"]}
    assert words[word_id]["lemma"] == lemma
    assert_direct(layer, word_id, caption)
    verb_id, verb_caption = verb
    assert words[verb_id]["lemma"] == "respicio"
    assert_direct(layer, verb_id, verb_caption)
    if carrier is None:
        # Polish needs na before these expressed accusative objects, including
        # the three fronted objects whose verb is later in the Latin order.
        assert language == "pl"
        assert words[word_id]["morph"]["case"] == "acc"
    else:
        carrier_id, carrier_lemma = carrier
        assert language == "en"
        assert words[carrier_id]["lemma"] == carrier_lemma
        assert words[carrier_id]["morph"]["pos"] == "prep"
        assert words[carrier_id]["morph"]["governs"] == "acc"
        assert_direct(layer, carrier_id, "upon")


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_selected_clauses_have_their_contextual_carrier(case):
    assert_carriers(*load(case[1], case[0]), case)


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
@pytest.mark.parametrize(
    "mutation",
    ["old-caption", "wrong-lemma", "omitted-carrier", "misplaced-carrier", "alignment"],
)
def test_contextual_contract_rejects_broken_carriers(case, mutation):
    core, layer = load(case[1], case[0])
    assert_carriers(core, layer, case)
    core, layer = deepcopy(core), deepcopy(layer)
    language, _, segment_id, word_id, _, old, caption, verb, carrier = case
    if mutation == "old-caption":
        layer["words"][word_id]["gloss"] = old
    elif mutation == "wrong-lemma":
        segment = next(segment for segment in core["segments"] if segment["id"] == segment_id)
        next(word for word in segment["words"] if word["id"] == word_id)["lemma"] = "dono"
    elif mutation == "omitted-carrier":
        # For PL the repaired noun is the carrier. For EN it is the distinct
        # in/ad token, not the now correctly bare look caption.
        carrier_id = word_id if language == "pl" else carrier[0]
        layer["words"][carrier_id].pop("gloss")
    elif mutation == "misplaced-carrier":
        if language == "pl":
            layer["words"][word_id]["gloss"] = old
            layer["words"][verb[0]]["gloss"] += " na"
        else:
            layer["words"][word_id]["gloss"] += " upon"
            layer["words"][carrier[0]].pop("gloss")
    else:
        segment = next(segment for segment in core["segments"] if segment["id"] == segment_id)
        ids = [word["id"] for word in segment["words"]]
        index = ids.index(word_id)
        layer["segments"][segment_id].setdefault("alignments", []).append(
            {"words": ids[index : index + 2], "anchor": word_id, "gloss": caption}
        )
    with pytest.raises(AssertionError):
        assert_carriers(core, layer, case)


# Transitive, absolute, directional and grouped realizations remain distinct.
# These are actual counterexamples to a dictionary-wide na/upon replacement.
COUNTEREXAMPLES = [
    ("orationes.magnificat", "pl", "w014", "wejrzał na"),
    ("orationes.magnificat", "en", "w014", "has regarded"),
    ("proprium.dominica-in-quinquagesima-evangelium", "pl", "w139", "Przejrzyj"),
    (
        "proprium.dominica-in-quinquagesima-evangelium",
        "en",
        "w139",
        "Receive your sight",
    ),
    ("proprium.dominica-resurrectionis-evangelium", "pl", "w040", "spojrzawszy"),
    ("proprium.dominica-resurrectionis-evangelium", "en", "w040", "looking"),
    ("proprium.dominica-i-adventus-evangelium", "en", "w058", "look up"),
    ("proprium.dominica-xiv-post-pentecosten-evangelium", "en", "w059", "Look at"),
    ("proprium.visitatio-beatae-mariae-virginis-epistola", "en", "w022", "gazing"),
    ("proprium.dominica-iii-post-pentecosten-secreta", "en", "w001", "Look upon"),
    ("ordinarium.supra-quae", "en", "w007", "to look"),
    ("proprium.dominica-iii-in-quadragesima-introitus", "en", "w013", "Look"),
    ("proprium.dominica-iii-in-quadragesima-introitus", "en", "w070", "Look"),
    (
        "proprium.sanctissimi-nominis-iesu-postcommunio",
        "pl",
        "w009",
        "wejrzyj łaskawie na",
    ),
    (
        "proprium.sanctissimi-nominis-iesu-postcommunio",
        "en",
        "w009",
        "look graciously upon",
    ),
]


@pytest.mark.parametrize("text,language,word_id,caption", COUNTEREXAMPLES)
def test_other_contexts_keep_their_own_effective_realizations(text, language, word_id, caption):
    core, layer = load(text, language)
    word = next(
        word
        for segment in core["segments"]
        for word in segment.get("words", [])
        if word["id"] == word_id
    )
    assert word["lemma"] == "respicio"
    assert effective_gloss(layer, word_id) == caption
