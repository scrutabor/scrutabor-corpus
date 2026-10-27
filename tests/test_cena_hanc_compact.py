"""Actual Hanc layers, exact membership and bounded source-relation controls."""

import re
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest
from cena_hanc_fixture import (
    DETAIL,
    HANC,
    assert_hanc_scope,
    assert_hanc_source,
    hanc_polish_errors,
    ids,
)

from build_reader import store
from checks.interlinear import check, effective_gloss
from checks.language_packs import check_core, check_layer
from checks.prose import check as check_prose

ROOT = Path(__file__).resolve().parents[1]


def subject():
    return store.core(ROOT, HANC), store.raw_layer(ROOT, "pl", HANC)


def test_actual_compact_hanc_and_pending_source():
    core, layer = subject()
    assert_hanc_source(core)
    assert_hanc_scope(layer)
    assert hanc_polish_errors(core, layer) == []
    assert check_core(core) == []
    assert check_layer(core, layer, store.layer_path(ROOT, "pl", HANC)) == []
    assert check(core, layer) == []
    assert check_prose(layer) == []
    assert layer["segments"]["s06"]["translation"] == (
        "I dni nasze uporządkuj w Twoim pokoju, a także racz nakazać, "
        "byśmy zostali wyrwani z wiecznego potępienia i zaliczeni do trzody Twoich wybranych."
    )
    line = " ".join(
        effective_gloss(layer, word["id"])
        for segment in core["segments"]
        if segment["id"] in {"s05", "s06"}
        for word in segment.get("words", [])
        if effective_gloss(layer, word["id"])
    )
    assert line == (
        "prosimy Panie abyś łaskawie przyjął i dni nasze w Twoim pokoju uporządkował "
        "a także z wiecznego potępienia nas wyrwać "
        "i do Twoich wybranych nakazał trzody zaliczyć"
    )
    for key in ("analysis_defaults", "analysis_defaults_words"):
        assert core["editorial"][key]["review"] == "pending"
    assert all(
        item.get("analysis", {}).get("review", "pending") == "pending"
        for item in core["editorial"].get("words", {}).values()
    )


def test_all_sixty_actual_memberships_and_source_contiguity():
    core, layer = subject()
    actual_ids = [w["id"] for s in core["segments"] for w in s.get("words", [])]
    assert actual_ids == ids(1, 60)
    providers = Counter(wid for wid, item in layer["words"].items() if item.get("gloss"))
    for segment in core["segments"]:
        positions = {word["id"]: n for n, word in enumerate(segment.get("words", []))}
        for group in layer["segments"][segment["id"]].get("alignments", []):
            indices = [positions[wid] for wid in group["words"]]
            assert indices == list(range(indices[0], indices[0] + len(indices)))
            providers.update(group["words"])
    assert providers == Counter(actual_ids)
    assert_hanc_scope(layer)


@pytest.mark.parametrize("kind", ["rescue-synonym", "command-synonym"])
def test_bounded_semantic_controls_are_not_only_literal_fixture_equality(kind):
    core, layer = subject()
    assert hanc_polish_errors(core, layer) == []
    original = deepcopy(layer)
    if kind == "rescue-synonym":
        layer["words"]["w047"]["gloss"] = "ocalić"
    else:
        layer["words"]["w052"]["gloss"] = "polecił"
    assert layer != original
    assert check(core, layer) == []
    assert hanc_polish_errors(core, layer) == []
    layer.clear()
    layer.update(original)
    assert check(core, layer) == [] and hanc_polish_errors(core, layer) == []


@pytest.mark.parametrize(
    "site,before,after,diagnostic",
    [
        ("w046", "nas", "ich", "Hanc rescue keeps us as patients"),
        ("w047", "wyrwać", "wyrwać innych przez nas", "Hanc rescue keeps us as patients"),
        ("w045", "potępienia", "doczesnej kary", "Hanc rescue keeps us as patients"),
        ("w054", "zaliczyć", "zaliczamy", "Hanc second outcome remains commanded inclusion"),
        ("w053", "trzody", "grona", "Hanc inclusion retains the Father's elect flock"),
        (0, "Twoich", "naszych", "Hanc inclusion retains the Father's elect flock"),
        ("w052", "nakazał", "nakazujemy", "Hanc one final finite governor"),
        ("w033", "abyś", "aby", "Hanc acceptance, disposition and command share upstream abyś"),
        ("w048", "i", "lub", "Hanc both outcomes remain coordinated"),
        ("w052", "bierne", "czynne", "Hanc detail distinguishes target infinitives"),
    ],
    ids=[
        "patient",
        "agent",
        "eternal",
        "second-outcome",
        "flock",
        "possessor",
        "governor",
        "upstream",
        "coordination",
        "detail",
    ],
)
def test_named_semantic_losses_fail_and_restore(site, before, after, diagnostic):
    core, layer = subject()
    original = deepcopy(layer)
    assert hanc_polish_errors(core, layer) == []
    if isinstance(site, int):
        item, field = layer["segments"]["s06"]["alignments"][site], "gloss"
    else:
        item = layer["words"][site]
        field = "explanation" if site == "w052" and before == "bierne" else "gloss"
    value = item[field]
    assert before in value and before != after
    item[field] = value.replace(before, after)
    assert item[field] != value
    assert check(core, layer) == []  # These are semantic losses, not missing memberships.
    assert any(error.startswith(diagnostic) for error in hanc_polish_errors(core, layer))
    item[field] = value
    assert layer == original and hanc_polish_errors(core, layer) == []


@pytest.mark.parametrize(
    "wid,field,value",
    [
        ("w047", "form", "éripe"),
        ("w047", "voice", "act"),
        ("w054", "voice", "act"),
        ("w046", "case", "dat"),
        ("w052", "person", 3),
        ("w053", "case", "acc"),
    ],
    ids=[
        "eripi-not-eripe",
        "eripi-passive",
        "numerari-passive",
        "nos-accusative",
        "iubeas-addressee",
        "flock-ablative",
    ],
)
def test_selected_infinitives_patient_and_governed_case_fail_and_restore(wid, field, value):
    core, _ = subject()
    original = deepcopy(core)
    assert_hanc_source(core)
    word = next(w for s in core["segments"] for w in s.get("words", []) if w["id"] == wid)
    item = word if field == "form" else word["morph"]
    before = item[field]
    assert before != value
    item[field] = value
    with pytest.raises(AssertionError, match="^" + re.escape("Hanc selected source: " + wid) + "$"):
        assert_hanc_source(core)
    item[field] = before
    assert core == original
    assert_hanc_source(core)


@pytest.mark.parametrize("index", [0, 1], ids=["release", "inclusion"])
def test_missing_actual_constituent_reports_its_every_member_and_restores(index):
    core, layer = subject()
    original = deepcopy(layer)
    assert check(core, layer) == []
    members = ids(43, 47) if index == 0 else ids(49, 54)
    layer["segments"]["s06"]["alignments"] = [
        group
        for group in layer["segments"]["s06"]["alignments"]
        if not set(group["words"]) & set(members)
    ]
    if not layer["segments"]["s06"]["alignments"]:
        del layer["segments"]["s06"]["alignments"]
    for wid in members:
        layer["words"][wid].pop("gloss", None)
    expected = {
        f"{HANC}:{wid}:pl: expected exactly one direct gloss or alignment" for wid in members
    }
    assert Counter(check(core, layer)) == Counter(expected)
    layer.clear()
    layer.update(original)
    assert layer == original and check(core, layer) == []


@pytest.mark.parametrize("wid", ["w043", "w048", "w054"])
def test_duplicate_providers_cover_both_groups_and_direct_conjunction(wid):
    core, layer = subject()
    original = deepcopy(layer)
    assert check(core, layer) == []
    groups = layer["segments"]["s06"]["alignments"]
    duplicate = {"words": [wid], "reason": "word-order"}
    position = next(
        (index for index, group in enumerate(groups) if wid < group["words"][0]), len(groups)
    )
    groups.insert(position, duplicate)
    assert check(core, layer) == [
        f"{HANC}:{wid}:pl: expected exactly one direct gloss or alignment"
    ]
    assert groups.pop(position) is duplicate
    assert layer == original and check(core, layer) == []


@pytest.mark.parametrize(
    "kind,diagnostic",
    [
        ("noncontiguous", "aligned words must be contiguous and in source order"),
        ("anchor-outside", "anchor must name the source word carrying the gloss"),
        ("technical", "gloss must be target-language wording"),
    ],
    ids=["contiguity", "anchor", "visible-wording"],
)
def test_actual_first_constituent_structural_controls(kind, diagnostic):
    core, layer = subject()
    original = deepcopy(layer)
    assert check(core, layer) == []
    group = layer["segments"]["s06"]["alignments"][0]
    if kind == "noncontiguous":
        group["words"].append("w053")
    elif kind == "anchor-outside":
        group["anchor"] = "w052"
    else:
        group["gloss"] = "[UNRESOLVED]"
    assert any(diagnostic in error for error in check(core, layer))
    group.clear()
    group.update(deepcopy(original["segments"]["s06"]["alignments"][0]))
    assert layer == original and check(core, layer) == []


def test_predecessor_twelve_word_polish_model_is_structurally_valid_but_not_current_model():
    core, layer = subject()
    original = deepcopy(layer)
    assert_hanc_scope(layer)
    layer["segments"]["s06"]["alignments"] = [
        {
            "words": ids(43, 54),
            "anchor": "w052",
            "gloss": (
                "nakazał, byśmy zostali wyrwani z wiecznego potępienia "
                "i zaliczeni do trzody Twoich wybranych"
            ),
        }
    ]
    for wid in ids(43, 54):
        layer["words"][wid].pop("gloss", None)
    assert check(core, layer) == []
    with pytest.raises(AssertionError, match=r"^Hanc reviewed short groups$"):
        assert_hanc_scope(layer)
    assert hanc_polish_errors(core, layer) == [
        "Hanc short model needs its complete elect constituent"
    ]
    layer.clear()
    layer.update(original)
    assert layer == original
    assert_hanc_scope(layer)
    assert layer["words"]["w052"]["explanation"] == DETAIL
