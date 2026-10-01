"""Preserve complete medial relations without hiding duplicate prepositions."""

import copy
import json

import pytest

from build_reader.layers import expand_core
from checks import english, interlinear
from checks.layout import CORPUS


def middle(preposition):
    slug, start = {
        "inter": ("dominica-xi-post-pentecosten-evangelium", 15),
        "per": ("dominica-xiii-post-pentecosten-evangelium", 10),
    }[preposition]
    core = json.loads((CORPUS / "texts/proprium" / (slug + ".json")).read_bytes())
    words = expand_core(core)["segments"][0]["words"][start - 1 : start + 2]
    doc = {"id": "fixture", "segments": [{"id": "s01", "words": words}]}
    targets = ["through", "the midst", "of the region"]
    layer = {
        "lang": "en",
        "segments": {"s01": {}},
        "words": {word["id"]: {"gloss": gloss} for word, gloss in zip(words, targets, strict=True)},
    }
    return doc, layer


@pytest.mark.parametrize("preposition", ["inter", "per"])
@pytest.mark.parametrize("modifier", ["the midst", "the middle"])
@pytest.mark.parametrize("spacing", ["plain", "double", "nbsp", "emspace"])
def test_nominalized_medial_adjective_preserves_of(preposition, modifier, spacing):
    doc, layer = middle(preposition)
    middle_word = doc["segments"][0]["words"][1]["id"]
    layer["words"][middle_word]["gloss"] = modifier
    if spacing != "plain":
        for entry in layer["words"].values():
            gap = {"double": "  ", "nbsp": "\u00a0", "emspace": "\u2003"}[spacing]
            entry["gloss"] = gap + entry["gloss"].upper().replace(" ", gap) + gap
    assert not interlinear.check(doc, layer)
    assert not english.check_doubled_preposition(doc, layer)
    assert not english.check(doc, layer)


@pytest.mark.parametrize("preposition", ["inter", "per"])
@pytest.mark.parametrize(
    "field",
    [
        "prep-lemma",
        "prep-pos",
        "governs",
        "middle-lemma",
        "middle-pos",
        "noun-pos",
        "noun-case",
        "prep-head",
        "middle-head",
        "case",
        "number",
        "gender",
        "missing-case",
        "missing-number",
        "missing-gender",
        "prep-post",
        "middle-pre",
        "middle-post",
        "noun-pre",
        "segment",
        "own-gloss",
        "middle-gloss",
        "object-gloss",
    ],
)
def test_exception_remains_structurally_narrow(preposition, field):
    doc, layer = middle(preposition)
    prep, mid, noun = doc["segments"][0]["words"]
    if field == "prep-lemma":
        prep["lemma"] = "contra"
    elif field == "prep-pos":
        # Keep the ordinary duplicate detector applicable to another prep,
        # while directly proving the exception refuses this non-preposition.
        prep["morph"]["pos"] = "adv"
    elif field == "governs":
        prep["morph"]["governs"] = "abl"
    elif field == "middle-lemma":
        mid["lemma"] = "magnus"
    elif field == "middle-pos":
        mid["morph"]["pos"] = "noun"
    elif field == "noun-pos":
        noun["morph"]["pos"] = "adj"
    elif field == "noun-case":
        noun["morph"]["case"] = "gen"
        mid["morph"]["case"] = "gen"
    elif field == "prep-head":
        prep["head"] = mid["id"]
    elif field == "middle-head":
        mid["head"] = prep["id"]
    elif field in {"case", "number", "gender"}:
        old = mid["morph"][field]
        mid["morph"][field] = {
            "case": "gen",
            "number": "pl" if old == "sg" else "sg",
            "gender": "n",
        }[field]
    elif field.startswith("missing-"):
        del mid["morph"][field.removeprefix("missing-")]
    elif field in {"prep-post", "middle-pre", "middle-post", "noun-pre"}:
        word, side = field.split("-")
        {"prep": prep, "middle": mid, "noun": noun}[word][side] = ":"
    elif field == "segment":
        doc["segments"][0]["words"] = [prep]
        doc["segments"].append({"id": "s02", "words": [mid, noun]})
    elif field == "own-gloss":
        layer["words"][prep["id"]]["gloss"] = "from"
    elif field == "middle-gloss":
        layer["words"][mid["id"]]["gloss"] = "middle"
    elif field == "object-gloss":
        layer["words"][noun["id"]]["gloss"] = "in the region"
    assert not interlinear.check(doc, layer)
    assert not english._nominalized_middle_objects(doc, layer)
    if field not in {"prep-pos", "prep-head"}:
        assert len(english.check_doubled_preposition(doc, layer)) == 1
        assert any("renders the preposition twice" in e for e in english.check(doc, layer))


@pytest.mark.parametrize("preposition", ["inter", "per"])
@pytest.mark.parametrize("kind", ["shared", "zero-middle", "zero-preposition"])
def test_valid_exceptional_providers_are_not_direct_splits(preposition, kind):
    doc, layer = middle(preposition)
    prep, mid, noun = doc["segments"][0]["words"]
    if kind == "shared":
        group = {
            "words": [mid["id"], noun["id"]],
            "anchor": mid["id"],
            "gloss": "the midst of the region",
        }
    else:
        group = {"words": [(mid if kind == "zero-middle" else prep)["id"]], "reason": "idiom"}
    for wid in group["words"]:
        layer["words"][wid].pop("gloss")
    layer["segments"]["s01"]["alignments"] = [group]
    assert not interlinear.check(doc, layer)
    assert not english._nominalized_middle_objects(doc, layer)
    assert len(english.check_doubled_preposition(doc, layer)) == (kind == "zero-middle")


@pytest.mark.parametrize("preposition", ["inter", "per"])
def test_valid_middle_in_another_segment_does_not_exempt_the_wrong_one(preposition):
    doc, layer = middle(preposition)
    original = doc["segments"][0]["words"]
    extra = copy.deepcopy(original)
    replacements = {w["id"]: "x" + w["id"] for w in extra}
    for w in extra:
        old = w["id"]
        w["id"] = replacements[old]
        if w.get("head") in replacements:
            w["head"] = replacements[w["head"]]
        layer["words"][w["id"]] = copy.deepcopy(layer["words"][old])
    extra[1]["lemma"] = "magnus"
    doc["segments"].append({"id": "s02", "words": extra})
    assert not interlinear.check(doc, layer)
    assert len(english.check_doubled_preposition(doc, layer)) == 1
