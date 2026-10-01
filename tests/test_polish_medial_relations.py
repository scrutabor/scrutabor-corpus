"""Keep attested medial relations complete, without rejecting valid splits."""

import copy
import json

import pytest

from checks import interlinear, polish
from checks.layout import CORPUS
from checks.polish_clauses import check_clause_junctions


def example(kind):
    slug, first, targets = (
        ("dominica-in-albis-alleluia", 21, ["w", "pośrodku"]),
        ("maternitas-beatae-mariae-virginis-evangelium", 51, ["w", "pośród"]),
        ("sanctae-annae-matris-beatae-mariae-virginis-evangelium", 103, ["spośród", "środka"]),
    )[kind]
    core = json.loads((CORPUS / "texts/proprium" / (slug + ".json")).read_bytes())
    words = core["segments"][0]["words"][first - 1 : first + 1]
    doc = {"id": "fixture", "segments": [{"id": "s01", "words": words}]}
    layer = {
        "lang": "pl",
        "segments": {"s01": {}},
        "words": {w["id"]: {"gloss": g} for w, g in zip(words, targets, strict=True)},
    }
    assert not interlinear.check(doc, layer)
    return doc, layer


@pytest.mark.parametrize("kind", range(3))
def test_repeated_medial_relation_reaches_dispatch(kind, monkeypatch):
    doc, layer = example(kind)
    assert len(check_clause_junctions(doc, layer)) == 1
    assert any("Polish medial" in e for e in polish.check(doc, layer))
    monkeypatch.setattr(polish, "check_clause_junctions", lambda *_: [])
    assert not any("Polish medial" in e for e in polish.check(doc, layer))


@pytest.mark.parametrize("kind", range(3))
def test_required_latin_features_and_head(kind):
    baseline, layer = example(kind)
    for index, keys in enumerate(
        (("lemma", "pos", "governs"), ("lemma", "pos", "case", "number", "gender"))
    ):
        for key in keys:
            for missing in (False, True):
                doc = copy.deepcopy(baseline)
                word = doc["segments"][0]["words"][index]
                target = word if key == "lemma" else word["morph"]
                if missing:
                    del target[key]
                else:
                    target[key] = "different"
                assert not check_clause_junctions(doc, layer), (kind, key, missing)
    doc = copy.deepcopy(baseline)
    doc["segments"][0]["words"][0]["head"] = "elsewhere"
    assert not check_clause_junctions(doc, layer)


@pytest.mark.parametrize("kind", range(3))
def test_exact_target_and_language_bounds(kind):
    doc, layer = example(kind)
    for entry in layer["words"].values():
        entry["gloss"] = "\t" + entry["gloss"].upper() + "… "
    assert len(check_clause_junctions(doc, layer)) == 1
    for wid in layer["words"]:
        other = copy.deepcopy(layer)
        other["words"][wid]["gloss"] = "inne wyrażenie"
        assert not check_clause_junctions(doc, other)
    layer["lang"] = "en"
    assert not check_clause_junctions(doc, layer)


@pytest.mark.parametrize("kind", range(3))
def test_valid_provider_and_source_boundaries(kind):
    doc, baseline = example(kind)
    ids = list(baseline["words"])
    for members, gloss in ((ids, "pośrodku"), ([ids[0]], None), ([ids[1]], None)):
        layer = copy.deepcopy(baseline)
        group = {"words": members}
        group.update({"anchor": members[0], "gloss": gloss} if gloss else {"reason": "idiom"})
        layer["segments"]["s01"]["alignments"] = [group]
        for wid in members:
            del layer["words"][wid]["gloss"]
        assert not interlinear.check(doc, layer)
        assert not check_clause_junctions(doc, layer)
    for index, field in ((0, "post"), (1, "pre")):
        other = copy.deepcopy(doc)
        other["segments"][0]["words"][index][field] = ":"
        assert not check_clause_junctions(other, baseline)
    a, b = doc["segments"][0]["words"]
    doc["segments"] = [{"id": "s01", "words": [a]}, {"id": "s02", "words": [b]}]
    assert not interlinear.check(doc, baseline)
    assert not check_clause_junctions(doc, baseline)


@pytest.mark.parametrize(
    "kind,targets", [(0, ["w", "środku"]), (1, ["w", "środku"]), (2, ["ze", "środka"])]
)
def test_legitimate_nominal_splits_are_not_rejected(kind, targets):
    doc, layer = example(kind)
    for wid, target in zip(layer["words"], targets, strict=True):
        layer["words"][wid]["gloss"] = target
    assert not interlinear.check(doc, layer)
    assert not check_clause_junctions(doc, layer)
