"""Bound the current Trinity captions and preserve earlier semantic controls."""

import hashlib
import json
from copy import deepcopy

import pytest
import test_preface_glory_scope as glory
import test_preface_trinity_contexts as trinity
from preface_caption_fixture import CAPTION_GROUPS, restore_caption_layer
from preface_note_fixture import restore_note_layer

from checks.interlinear import check
from checks.language_packs import check_layer
from checks.layout import CORPUS, formatted

REL = "texts/ordinarium/praefatio-sanctissimae-trinitatis.json"
BEFORE_EN = "fd5053f1ff4bc2f49ac0162630249928dea74e51e6be368ea446622c6b03e595"


def load():
    return json.loads((CORPUS / REL).read_text()), json.loads(
        (CORPUS / "languages/en" / REL).read_text()
    )


def assert_current(core, layer):
    assert not check(core, layer)
    assert not check_layer(core, layer, CORPUS / "languages/en" / REL)
    assert (
        hashlib.sha256(formatted(restore_caption_layer(layer, "en")).encode()).hexdigest()
        == BEFORE_EN
    )


def test_current_caption_positive_and_old_inverse_are_not_already_red():
    core, layer = load()
    assert_current(core, layer)
    trinity.restore(core, layer, "en")
    glory.assert_exact_inverse(core, layer, "en")
    assert restore_note_layer(layer, "en")["words"]["w085"] == {"gloss": "which"}
    assert layer["words"]["w094"] == {"gloss": "and they"}
    assert layer["words"]["w076"] == layer["words"]["w080"] == {"gloss": "and"}
    assert layer["segments"]["s06"]["alignments"][1] == {
        "words": ["w072"],
        "reason": "idiom",
    }


@pytest.mark.parametrize("sid,index", [("s02", 0), ("s06", 2), ("s06", 3), ("s06", 4)])
@pytest.mark.parametrize(
    "damage", ["member", "gloss", "anchor", "key-order", "position", "duplicate"]
)
def test_exact_selected_groups_cannot_hide_damaged_payload(sid, index, damage):
    core, original = load()
    assert_current(core, original)
    layer = deepcopy(original)
    groups = layer["segments"][sid]["alignments"]
    group = groups[index]
    if damage == "member":
        group["words"].pop()
    elif damage == "gloss":
        group["gloss"] += " changed"
    elif damage == "anchor":
        group["anchor"] = group["words"][0]
        if group["anchor"] == original["segments"][sid]["alignments"][index]["anchor"]:
            group["anchor"] = group["words"][-1]
    elif damage == "key-order":
        items = list(group.items())
        group.clear()
        group.update(reversed(items))
    elif damage == "position":
        groups.append(groups.pop(index))
        if groups == original["segments"][sid]["alignments"]:
            groups.insert(0, groups.pop())
    else:
        groups.append(deepcopy(group))
    with pytest.raises((AssertionError, KeyError)):
        assert_current(core, layer)


@pytest.mark.parametrize(
    "damage",
    [
        "translation",
        "note",
        "Quam",
        "qui",
        "other-word",
        "word-order",
        "segment-order",
        "segment-key-order",
        "extra-selected-help",
        "direct-key-order",
        "zero",
        "conjunction",
    ],
)
def test_old_context_and_caption_boundaries_remain_exact(damage):
    core, original = load()
    assert_current(core, original)
    layer = deepcopy(original)
    if damage == "translation":
        layer["segments"]["s07"]["translation"] += " Changed."
    elif damage == "note":
        layer["words"]["w064"]["explanation"] += " Changed."
    elif damage == "Quam":
        layer["words"]["w085"]["gloss"] = "Whom"
    elif damage == "qui":
        layer["words"]["w094"]["gloss"] = "they"
    elif damage == "other-word":
        layer["words"]["w016"]["gloss"] = "king"
    elif damage == "word-order":
        layer["words"]["w094"] = layer["words"].pop("w094")
    elif damage == "segment-order":
        layer["segments"]["s06"] = layer["segments"].pop("s06")
    elif damage == "segment-key-order":
        layer["segments"]["s06"] = dict(reversed(list(layer["segments"]["s06"].items())))
    elif damage == "extra-selected-help":
        layer["words"]["w075"]["explanation"] = "Changed."
    elif damage == "direct-key-order":
        layer["words"]["w094"] = {"note": "Changed.", "gloss": "and they"}
    elif damage == "zero":
        layer["segments"]["s06"]["alignments"][1]["reason"] = "punctuation"
    else:
        layer["words"]["w080"]["gloss"] = "or"
    with pytest.raises((AssertionError, KeyError)):
        assert_current(core, layer)


@pytest.mark.parametrize(
    "first,bad",
    [
        ("w038", "one singleness of a Person"),
        ("w043", "one Trinity of substances"),
        ("w083", "equality may adore"),
        ("w083", "only equality may be adored"),
        ("w095", "cease"),
        ("w099", "with many voices"),
    ],
)
def test_old_semantic_negatives_have_actual_new_positive_setup(first, bad):
    core, original = load()
    assert_current(core, original)
    layer = trinity.prepare(original, "en")
    assert not check(core, layer)
    trinity.restore(core, layer, "en")
    equality = layer["segments"]["s06"]["alignments"][-1]
    assert equality == CAPTION_GROUPS["s06"][-1]
    site = next(s for s in trinity.GROUPS["en"] if s["words"][0] == first)
    trinity.touching(layer, site)[0]["gloss"] = bad
    assert not check(core, layer)
    with pytest.raises(AssertionError):
        trinity.restore(core, layer, "en")


@pytest.mark.parametrize(
    "damage", ["origin", "review", "familiar_core", "source_sha256", "target_sha256"]
)
def test_retained_full_prose_provenance_is_not_vacuously_red(damage):
    core, layer = load()
    assert_current(core, layer)
    ledger = json.loads((CORPUS / "languages/en/translation-provenance.json").read_text())
    row = next(r for r in ledger["sites"] if r["site"] == layer["text"] + ".s05.en")
    segment = next(s for s in core["segments"] if s["id"] == "s05")
    translated = layer["segments"]["s05"]["translation"]
    glory.assert_english_provenance(row, segment, translated)
    row = deepcopy(row)
    row[damage] = True if damage == "familiar_core" else "changed"
    with pytest.raises(AssertionError):
        glory.assert_english_provenance(row, segment, translated)
