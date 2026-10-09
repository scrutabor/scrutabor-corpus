"""Bound the common-glory clarification without erasing personal distinction."""

import hashlib
import json
from copy import deepcopy

import pytest
from preface_caption_fixture import restore_caption_layer
from preface_glory_fixture import (
    EN_AFTER,
    EN_TARGET,
    restore_glory_core,
    restore_glory_layer,
)

from checks.interlinear import check
from checks.language_packs import check_layer
from checks.layout import CORPUS, formatted
from checks.translation_provenance import canonical_hash, source_payload

REL = "texts/ordinarium/praefatio-sanctissimae-trinitatis.json"
PREVIOUS = {
    "core": "98684a9b594700dd7aa7a7284ee6accd229cbf2017d096ffa41121fb2b31d7ca",
    "pl": "f10505455c090f2e202985917aba7ac596e0c223e36280efa3730f1b7efdfd8b",
    "en": "1cc744fc827d79cb47898b5fb595b2d975c498eaf57fe9568525cf7954ee1945",
}


def load(language):
    return json.loads((CORPUS / REL).read_text()), json.loads(
        (CORPUS / "languages" / language / REL).read_text()
    )


def assert_exact_inverse(core, layer, language):
    assert (
        hashlib.sha256(formatted(restore_glory_core(core)).encode()).hexdigest() == PREVIOUS["core"]
    )
    assert (
        hashlib.sha256(
            formatted(
                restore_glory_layer(restore_caption_layer(layer, language), language)
            ).encode()
        ).hexdigest()
        == PREVIOUS[language]
    )


@pytest.mark.parametrize("language", ["pl", "en"])
def test_only_the_named_glory_fields_changed(language):
    core, layer = load(language)
    assert_exact_inverse(core, layer, language)
    assert not check(core, layer)
    assert not check_layer(core, layer, CORPUS / "languages" / language / REL)


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize(
    "mutation",
    [
        "note",
        "other-note",
        "member",
        "duplicate",
        "anchor",
        "gloss",
        "verse",
        "other-verse",
        "about",
        "order",
        "group-key-order",
        "segment-key-order",
        "declaration-key-order",
        "missing-word",
        "core-word",
        "declaration",
    ],
)
def test_inverse_cannot_hide_unreviewed_payload(language, mutation):
    core, layer = load(language)
    group = next(g for g in layer["segments"]["s05"]["alignments"] if "w062" in g["words"])
    if mutation == "note":
        layer["words"]["w064"]["explanation"] += " Changed."
    elif mutation == "other-note":
        layer["words"]["w061"]["explanation"] = "Changed."
    elif mutation == "member":
        group["words"].pop()
    elif mutation == "duplicate":
        layer["segments"]["s05"]["alignments"].append(deepcopy(group))
    elif mutation == "anchor":
        group["anchor"] = "w062"
    elif mutation == "gloss":
        group["gloss"] = "there are no distinct Persons"
    elif mutation == "verse":
        layer["segments"]["s05"]["translation"] += " Changed."
    elif mutation == "other-verse":
        layer["segments"]["s06"]["translation"] += " Changed."
    elif mutation == "about":
        layer["about"] += " Changed."
    elif mutation == "order":
        layer["words"]["w061"] = layer["words"].pop("w061")
    elif mutation == "group-key-order":
        values = list(group.items())
        group.clear()
        group.update(reversed(values))
    elif mutation == "segment-key-order":
        layer["segments"]["s05"] = dict(reversed(list(layer["segments"]["s05"].items())))
    elif mutation == "declaration-key-order":
        core["localization"] = dict(reversed(list(core["localization"].items())))
    elif mutation == "missing-word":
        del layer["words"]["w062"]
    elif mutation == "core-word":
        next(w for s in core["segments"] for w in s.get("words", []) if w["id"] == "w064")[
            "form"
        ] = "changed"
    else:
        core["localization"]["explanations"]["w065"] = {}
    with pytest.raises((AssertionError, KeyError)):
        assert_exact_inverse(core, layer, language)


def test_inverse_preserves_position_of_the_added_group():
    core, layer = load("en")
    assert_exact_inverse(core, layer, "en")
    groups = layer["segments"]["s05"]["alignments"]
    assert len(groups) > 1 and groups[-1]["words"] == ["w062", "w063", "w064"]
    groups.insert(0, groups.pop())
    with pytest.raises(AssertionError):
        assert_exact_inverse(core, layer, "en")


def assert_english_provenance(row, segment, translated):
    assert row["origin"] == "working-unsettled" and row["review"] == "working"
    assert row["familiar_core"] is False
    assert translated == EN_AFTER
    assert (
        row["source_sha256"]
        == canonical_hash(source_payload(segment))
        == ("88d4fe9af744ad39978d27b4f8f6e137fd42d0cea4205ff8b89f551165587bd3")
    )
    assert row["target_sha256"] == canonical_hash(translated) == EN_TARGET


def provenance_inputs():
    core, layer = load("en")
    rows = json.loads((CORPUS / "languages/en/translation-provenance.json").read_text())["sites"]
    row = next(r for r in rows if r["text"] == core["id"] and r["segment"] == "s05")
    segment = next(s for s in core["segments"] if s["id"] == "s05")
    return row, segment, layer["segments"]["s05"]["translation"]


def test_english_provenance_does_not_inherit_prior_approval():
    assert_english_provenance(*provenance_inputs())


@pytest.mark.parametrize(
    "field,value",
    [
        ("origin", "own"),
        ("review", "internally-reviewed"),
        ("familiar_core", True),
        ("source_sha256", "0" * 64),
        ("target_sha256", "0" * 64),
    ],
)
def test_promotion_and_stale_binding_are_rejected(field, value):
    row, segment, translated = provenance_inputs()
    assert_english_provenance(row, segment, translated)
    row[field] = value
    with pytest.raises(AssertionError):
        assert_english_provenance(row, segment, translated)
