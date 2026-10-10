"""Fifth-Sunday clauses preserve human agents, offerings and received pledge."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from checks import interlinear
from checks.language_packs import check_layer

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "proprium.dominica-v-post-epiphaniam-"
GROUPS = [
    ("collecta", "pl", 16, 19, 19, "zawsze była umocniona Twoją opieką"),
    ("collecta", "en", 8, 9, 9, "so that it, which"),
    ("epistola", "en", 63, 65, 65, "May Christ’s word dwell"),
    ("evangelium", "en", 4, 5, 4, "Jesus said"),
    ("evangelium", "en", 89, 94, 89, "you also uproot the wheat along with it"),
    ("secreta", "pl", 13, 16, 16, "sam pokierował chwiejnymi sercami"),
    ("secreta", "en", 1, 5, 5, "We offer You, Lord, offerings of atonement"),
    ("secreta", "en", 6, 11, 11, "so that You may both mercifully absolve our faults"),
    ("secreta", "en", 13, 16, 16, "guide our wavering hearts Yourself"),
    ("postcommunio", "pl", 5, 8, 7, "osiągnęli skutek owego zbawienia"),
    ("postcommunio", "pl", 9, 14, 14, "którego zadatek otrzymaliśmy przez te tajemnice"),
    ("postcommunio", "en", 5, 8, 7, "we may obtain the effect of that salvation"),
    ("postcommunio", "en", 9, 14, 14, "whose pledge we have received through these mysteries"),
]


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def documents(slug, language):
    relative = f"texts/proprium/dominica-v-post-epiphaniam-{slug}.json"
    return load(relative), load(f"languages/{language}/{relative}")


def selected_group(layer, lo, hi, anchor, caption):
    ids = [f"w{n:03d}" for n in range(lo, hi + 1)]
    found = [
        group
        for segment in layer["segments"].values()
        for group in segment.get("alignments", [])
        if set(group["words"]) & set(ids)
    ]
    assert found == [{"words": ids, "anchor": f"w{anchor:03d}", "gloss": caption}]
    assert all("gloss" not in layer["words"][wid] for wid in ids)


@pytest.mark.parametrize("slug,language,lo,hi,anchor,caption", GROUPS)
def test_selected_clauses_have_one_exact_provider(slug, language, lo, hi, anchor, caption):
    core, layer = documents(slug, language)
    selected_group(layer, lo, hi, anchor, caption)
    assert interlinear.check(core, layer) == []
    for n in range(lo, hi + 1):
        duplicate = deepcopy(layer)
        duplicate["words"][f"w{n:03d}"]["gloss"] = "duplicate"
        assert interlinear.check(core, duplicate)


@pytest.mark.parametrize(
    "language,values",
    [
        (
            "pl",
            {
                "w072": "nauczajcie",
                "w074": "napominajcie",
                "w083": "śpiewajcie",
                "w096": "wszystko czyńcie",
            },
        ),
        (
            "en",
            {
                "w072": "as you teach",
                "w074": "admonish",
                "w083": "singing",
                "w096": "do everything",
            },
        ),
    ],
)
def test_human_exhortation_does_not_change_latin_participles(language, values):
    core, layer = documents("epistola", language)
    words = {w["id"]: w for seg in core["segments"] for w in seg["words"]}
    for wid in ("w072", "w074", "w083"):
        assert words[wid]["morph"]["mood"] == "part"
        assert words[wid]["morph"]["number"] == "pl"
        assert core["editorial"]["words"][wid]["analysis"]["review"] == "pending"
    assert {wid: layer["words"][wid]["gloss"] for wid in values} == values
    path = ROOT / f"languages/{language}/texts/proprium/dominica-v-post-epiphaniam-epistola.json"
    assert check_layer(core, layer, path) == []
    orphan = deepcopy(core)
    del orphan["localization"]["explanations"]["w096"]
    assert check_layer(orphan, layer, path)


def test_polish_negation_does_not_rewrite_positive_objects():
    _, layer = documents("evangelium", "pl")
    assert {wid: layer["words"][wid]["gloss"] for wid in ("w088", "w094", "w056", "w057")} == {
        "w088": "kąkol",
        "w094": "pszenicy",
        "w056": "dobre",
        "w057": "nasienie",
    }


def test_plural_offerings_and_effect_distinct_from_received_pledge():
    _, secret = documents("secreta", "en")
    _, communion = documents("postcommunio", "en")
    assert "offerings of atonement" in secret["segments"]["s01"]["translation"]
    assert (
        "we may obtain the effect of that salvation "
        "whose pledge we have received through these mysteries"
        in communion["segments"]["s01"]["translation"]
    )


@pytest.mark.parametrize(
    "slug,body,page", [("collecta", 19, "415"), ("secreta", 16, "415"), ("postcommunio", 14, "416")]
)
def test_abbreviated_proper_does_not_claim_a_literal_full_conclusion(slug, body, page):
    text = PREFIX + slug
    graph = load("bibliography/graph.json")
    use = next(u for u in graph["uses"] if u["id"] == f"use.{text}.mr1962")
    assert f"{body}-word body and short Per Dominum cue" in use["claim"]
    assert use["locator"]["printed"] == f"p. {page}"
    witness = next(w for w in graph["witnesses"] if w["id"] == f"witness.{text}.mr1962")
    assert witness["orthography_profile"] == "page-body-with-declared-house-expansion"
    assert f"use.{text}.expanded-conclusion.mr1962" in witness["source_dependencies"]["uses"]
    assert witness["review"] == {"status": "pending"}


def selected_scalar(layer, wid, caption):
    assert layer["words"][wid]["gloss"] == caption
    assert not any(
        wid in group["words"]
        for segment in layer["segments"].values()
        for group in segment.get("alignments", [])
    )


@pytest.mark.parametrize(
    "slug,language,wid,caption,former",
    [
        ("postcommunio", "en", "w001", "We beseech You", "We beseech"),
        ("evangelium", "pl", "w096", "jednemu i drugiemu", "obojgu"),
    ],
)
def test_address_and_two_crop_kinds_remain_explicit(slug, language, wid, caption, former):
    core, layer = documents(slug, language)
    selected_scalar(layer, wid, caption)
    assert interlinear.check(core, layer) == []
    altered = deepcopy(layer)
    altered["words"][wid]["gloss"] = former
    with pytest.raises(AssertionError):
        selected_scalar(altered, wid, caption)
    altered["words"][wid]["gloss"] = caption
    selected_scalar(altered, wid, caption)
    assert interlinear.check(core, altered) == []


def selected_preface_dialogue(use):
    assert use["locator"]["section"] == "p.226 sung Preface dialogue: terminal and response"
    assert use["claim"].startswith("The p.226 sung Preface dialogue explicitly prints")


def test_secret_terminal_source_is_labeled_as_sung_preface_dialogue():
    graph = load("bibliography/graph.json")
    use = next(
        u for u in graph["uses"] if u["id"] == f"use.{PREFIX}secreta.oration-boundaries.mr1962"
    )
    selected_preface_dialogue(use)
    for field in ("claim", "section"):
        altered = deepcopy(use)
        if field == "claim":
            altered["claim"] = altered["claim"].replace(
                "The p.226 sung Preface dialogue", "Ordo226"
            )
        else:
            altered["locator"]["section"] = "Ordo Secret/Preface terminal and response"
        with pytest.raises(AssertionError):
            selected_preface_dialogue(altered)
        selected_preface_dialogue(use)
