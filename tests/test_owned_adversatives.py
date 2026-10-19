"""One source-owned but is distinct from an adjacent adversative's own but."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import store
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, prose
from checks.lint import lint_gloss

ROOT = Path(__file__).resolve().parents[1]
GOSPEL = "proprium.dominica-iii-post-pascha-evangelium"


def absorption(core, layer):
    return [
        error
        for error in lint_gloss(enrich_layer(core, layer), expand_core(core))
        if "absorbs the conjunction" in error
    ]


def subject(owner="autem", extra_adverb=False, side="after"):
    actual = store.core(ROOT, GOSPEL)
    by_id = {w["id"]: w for s in actual["segments"] for w in s["words"]}
    members = [deepcopy(by_id[wid]) for wid in ("w104", "w105", "w106")]
    neighbor = deepcopy(by_id["w107"])
    members[1].update(form=owner, lemma=owner)
    if owner == "sed":
        members[0], members[1] = members[1], members[0]
    if extra_adverb:
        members.insert(-1, {"id": "w900", "form": "nunc", "lemma": "nunc", "morph": {"pos": "adv"}})
    anchor = members[-1]["id"] if side == "after" else members[0]["id"]
    group = {
        "words": [w["id"] for w in members],
        "anchor": anchor,
        "gloss": "but you will now be sorrowful" if extra_adverb else "but you will be sorrowful",
    }
    words = [*members, neighbor] if side == "after" else [neighbor, *members]
    core = {"id": "proprium.test", "segments": [{"id": "s01", "type": "verse", "words": words}]}
    layer = {
        "language": "en",
        "text": "proprium.test",
        "segments": {"s01": {"alignments": [group]}},
        "words": {w["id"]: {} for w in words},
    }
    layer["words"]["w107"]["gloss"] = "but"
    return core, layer, group


def test_actual_three_word_group_preserves_both_distinct_source_connectives():
    core = store.core(ROOT, GOSPEL)
    layer = store.raw_layer(ROOT, "en", GOSPEL)
    by_id = {w["id"]: w for s in core["segments"] for w in s["words"]}
    assert [by_id[wid]["lemma"] for wid in ("w104", "w105", "w106", "w107")] == [
        "vos",
        "autem",
        "contristo",
        "sed",
    ]
    groups = [g for s in layer["segments"].values() for g in s.get("alignments", [])]
    assert next(g for g in groups if "w105" in g["words"]) == {
        "words": ["w104", "w105", "w106"],
        "anchor": "w106",
        "gloss": "but you will be sorrowful",
    }
    assert layer["words"]["w107"]["gloss"] == "but"
    assert interlinear.check(core, layer) == []
    assert absorption(core, layer) == []


@pytest.mark.parametrize("owner", ["autem", "sed"])
@pytest.mark.parametrize("extra_adverb", [False, True])
@pytest.mark.parametrize("side", ["before", "after"])
def test_owned_identity_not_a_three_member_limit(owner, extra_adverb, side):
    core, layer, _ = subject(owner, extra_adverb, side)
    assert interlinear.check(core, layer) == []
    assert absorption(core, layer) == []


@pytest.mark.parametrize(
    "damage",
    [
        "owner-form",
        "owner-lemma",
        "owner-pos",
        "no-owner",
        "unsupported-owner",
        "two-owners",
        "finite-mood",
        "finite-pos",
        "finite-person",
        "finite-number",
        "neighbor-form",
        "neighbor-lemma",
        "neighbor-pos",
        "duplicate-but",
        "extra-and",
        "extra-however",
        "extra-because",
        "wrong-language",
        "fused-extra-connective",
    ],
)
def test_unowned_or_extra_connective_is_rejected_then_restored(damage):
    core, layer, group = subject()
    original_core, original_layer = deepcopy(core), deepcopy(layer)
    assert absorption(core, layer) == []
    words = {w["id"]: w for w in core["segments"][0]["words"]}
    owner, predicate, neighbor = words["w105"], words["w106"], words["w107"]
    if damage == "owner-form":
        owner["form"] = "ergo"
    elif damage == "owner-lemma":
        owner["lemma"] = "ergo"
    elif damage == "owner-pos":
        owner["morph"]["pos"] = "adv"
    elif damage == "no-owner":
        owner.update(form="nunc", lemma="nunc", morph={"pos": "adv"})
    elif damage == "unsupported-owner":
        owner.update(form="quia", lemma="quia")
    elif damage == "two-owners":
        words["w104"].update(form="sed", lemma="sed", morph={"pos": "conj"})
    elif damage.startswith("finite-"):
        field = damage.removeprefix("finite-")
        predicate["morph"][field] = {"mood": "part", "pos": "noun", "person": True, "number": "du"}[
            field
        ]
    elif damage == "neighbor-form":
        neighbor["form"] = "et"
    elif damage == "neighbor-lemma":
        neighbor["lemma"] = "et"
    elif damage == "neighbor-pos":
        neighbor["morph"]["pos"] = "adv"
    elif damage == "duplicate-but":
        group["gloss"] += " but"
    elif damage == "extra-and":
        group["gloss"] += " and"
    elif damage == "extra-however":
        group["gloss"] += " however"
    elif damage == "extra-because":
        group["gloss"] += " because"
    elif damage == "wrong-language":
        layer["language"] = "pl"
        layer["words"]["w107"]["gloss"] = "ale"
        group["gloss"] = "ale będziecie zasmuceni"
    else:
        words["w104"]["form"] = "vosque"
    assert absorption(core, layer)
    core.clear()
    core.update(original_core)
    layer.clear()
    layer.update(original_layer)
    assert absorption(core, layer) == []


@pytest.mark.parametrize("damage", ["gap", "reorder", "duplicate", "unknown", "anchor", "overlap"])
def test_invalid_groups_still_fail_group_checks_and_restore(damage):
    core, layer, group = subject()
    original = deepcopy(layer)
    assert interlinear.check(core, layer) == []
    if damage == "gap":
        group["words"].remove("w105")
    elif damage == "reorder":
        group["words"][:2] = ["w105", "w104"]
    elif damage == "duplicate":
        group["words"].append("w105")
    elif damage == "unknown":
        group["words"].append("w999")
    elif damage == "anchor":
        group["anchor"] = "w107"
    else:
        layer["segments"]["s01"]["alignments"].append(deepcopy(group))
    assert interlinear.check(core, layer)
    if damage in {"gap", "reorder", "duplicate", "unknown"}:
        assert absorption(core, layer)
    layer.clear()
    layer.update(original)
    assert interlinear.check(core, layer) == []
    assert absorption(core, layer) == []


@pytest.mark.parametrize(
    "language,role,wid,key,corrected,old",
    [
        ("pl", "epistola", "w048", "explanation", ". W tym kontekście", "; w tym kontekście"),
        ("en", "epistola", "w048", "explanation", ". In this context", "; in this context"),
        ("pl", "evangelium", "w124", "note", ". Obie pozwalają", "; obie pozwalają"),
        ("en", "evangelium", "w124", "note", ". Both allow", "; both allow"),
    ],
)
def test_actual_house_prose_rejects_semicolon_and_restores_sentence_boundary(
    language, role, wid, key, corrected, old
):
    path = ROOT / f"languages/{language}/texts/proprium/dominica-iii-post-pascha-{role}.json"
    layer = json.loads(path.read_text(encoding="utf-8"))
    field = layer["words"][wid]
    original = field[key]
    assert corrected in original and ";" not in original
    assert prose.check(layer) == []
    field[key] = original.replace(corrected, old)
    assert any(
        f"{wid}.{key}" in error and "uses a semicolon" in error for error in prose.check(layer)
    )
    field[key] = original
    assert prose.check(layer) == []
