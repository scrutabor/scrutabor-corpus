"""Literal roles, government and realization topology beyond generic concord."""

import json

import pytest

from checks.layout import CORPUS

DIRECT = (
    ("en", "proprium/dominica-xi-post-pentecosten-evangelium", "w015", "through"),
    ("pl", "proprium/dominica-ii-post-pentecosten-evangelium", "w148", "nie zakosztuje"),
    ("pl", "proprium/dominica-iii-in-quadragesima-epistola", "w083", "nie zwodzi"),
    ("pl", "proprium/sancti-matthiae-apostoli-evangelium", "w042", "nie zna"),
    ("pl", "proprium/sancti-matthiae-apostoli-evangelium", "w049", "nie zna"),
    ("pl", "proprium/sanctorum-simonis-et-iudae-apostolorum-evangelium", "w125", "nie dokonał"),
    ("pl", "proprium/transfiguratio-domini-evangelium", "w127", "nie ujrzeli"),
    ("en", "proprium/dominica-i-in-quadragesima-epistola", "w031", "giving"),
    ("pl", "proprium/dominica-ii-in-quadragesima-epistola", "w072", "nie dopuszczał się nadużyć"),
    ("pl", "proprium/dominica-ii-in-quadragesima-epistola", "w074", "nie oszukiwał"),
    ("pl", "litaniae/sanctissimi-nominis-iesu", "w449", "nie przestawali"),
    ("pl", "litaniae/sanctissimi-nominis-iesu", "w466", "nie pozbawiasz"),
    ("pl", "ordinarium/fili-dei-vivi", "w047", "nie dopuść"),
    ("pl", "ordinarium/praefatio-sacratissimi-cordis-iesu", "w050", "nie przestało"),
    ("pl", "proprium/corporis-christi-sequentia", "w210", "nie dokonuje się"),
    ("pl", "proprium/dominica-ii-post-pentecosten-collecta", "w017", "nie pozbawiasz"),
    ("pl", "proprium/dominica-iii-post-epiphaniam-epistola", "w011", "nieodpłacający"),
    ("pl", "proprium/dominica-in-sexagesima-collecta", "w009", "nie pokładamy ufności"),
    ("pl", "proprium/dominica-vi-post-pentecosten-secreta", "w014", "niczyje"),
)
GROUPS = (
    ("proprium/dominica-ii-in-quadragesima-epistola", "w015 w016", "w015", "you ought"),
    ("proprium/transfiguratio-domini-evangelium", "w126 w127", "w127", "they saw no one"),
    (
        "proprium/dominica-iii-post-epiphaniam-evangelium",
        "w046 w047 w048",
        "w046",
        "See that you tell no one",
    ),
    ("proprium/transfiguratio-domini-communio", "w004 w005", "w005", "tell no one"),
    ("proprium/transfiguratio-domini-evangelium", "w140 w141", "w141", "tell no one"),
    ("proprium/dominica-ii-in-quadragesima-epistola", "w070 w071", "w071", "that no one"),
    (
        "proprium/dominica-xi-post-pentecosten-evangelium",
        "w079 w080 w081",
        "w081",
        "not to tell anyone",
    ),
)


def layer(language, text):
    return json.loads((CORPUS / "languages" / language / "texts" / (text + ".json")).read_text())


@pytest.mark.parametrize("language,text,wid,gloss", DIRECT)
def test_contextual_predicate_or_possessive(language, text, wid, gloss):
    value = layer(language, text)
    assert value["words"][wid]["gloss"] == gloss
    assert not any(
        wid in group["words"]
        for segment in value["segments"].values()
        for group in segment.get("alignments", [])
    )


@pytest.mark.parametrize(
    "language,text,words,anchor,gloss",
    [("en", *row) for row in GROUPS]
    + [
        (
            "pl",
            "proprium/dominica-xi-post-pentecosten-evangelium",
            "w079 w080 w081",
            "w081",
            "aby nikomu nie mówili",
        )
    ],
)
def test_complete_subject_object_or_command_group(language, text, words, anchor, gloss):
    value = layer(language, text)
    ids = words.split()
    actual = [
        g for g in value["segments"]["s01"].get("alignments", []) if set(ids) & set(g["words"])
    ]
    assert actual == [{"words": ids, "anchor": anchor, "gloss": gloss}]
    assert all("gloss" not in value["words"][wid] for wid in ids)
