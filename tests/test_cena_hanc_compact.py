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
        "a także wyrwanie nas z wiecznego potępienia "
        "i zaliczenie do trzody Twoich wybranych nakazał"
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
    groups = layer["segments"]["s06"]["alignments"]
    if kind == "rescue-synonym":
        groups[0]["gloss"] = "ocalenie nas od wiecznego potępienia"
    else:
        groups[1]["gloss"] = groups[1]["gloss"].replace("nakazał", "polecił")
    assert check(core, layer) == []
    assert hanc_polish_errors(core, layer) == []


@pytest.mark.parametrize(
    "site,before,after,diagnostic",
    [
        (0, "nas ", "", "Hanc rescue keeps us as patients"),
        (0, "wyrwanie nas", "wyrwanie innych przez nas", "Hanc rescue keeps us as patients"),
        (0, "wiecznego potępienia", "doczesnej kary", "Hanc rescue keeps us as patients"),
        (1, "zaliczenie", "zaliczamy", "Hanc second outcome remains nominal inclusion"),
        (1, "do trzody", "do grona", "Hanc inclusion retains the Father's elect flock"),
        (1, "Twoich", "naszych", "Hanc inclusion retains the Father's elect flock"),
        (1, " nakazał", "", "Hanc one final finite governor"),
        ("w033", "abyś", "aby", "Hanc acceptance, disposition and command share upstream abyś"),
        ("w048", "i", "lub", "Hanc both outcomes remain coordinated"),
        ("w052", "bierne", "czynne", "Hanc detail distinguishes target nouns"),
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
        field = "explanation" if site == "w052" else "gloss"
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
    group = layer["segments"]["s06"]["alignments"].pop(index)
    expected = {
        f"{HANC}:{wid}:pl: expected exactly one direct gloss or alignment" for wid in group["words"]
    }
    assert Counter(check(core, layer)) == Counter(expected)
    layer["segments"]["s06"]["alignments"].insert(index, group)
    assert layer == original and check(core, layer) == []


@pytest.mark.parametrize("wid", ["w043", "w048", "w054"])
def test_duplicate_providers_cover_both_groups_and_direct_conjunction(wid):
    core, layer = subject()
    original = deepcopy(layer)
    assert check(core, layer) == []
    if wid == "w048":
        layer["segments"]["s06"]["alignments"].insert(
            1,
            {"words": [wid], "reason": "word-order"},
        )
    else:
        layer["words"][wid]["gloss"] = "dodatkowy podpis"
    assert check(core, layer) == [
        f"{HANC}:{wid}:pl: expected exactly one direct gloss or alignment"
    ]
    if wid == "w048":
        layer["segments"]["s06"]["alignments"].pop(1)
    else:
        del layer["words"][wid]["gloss"]
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
        group["words"].remove("w045")
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
    layer["words"]["w048"] = {}
    assert check(core, layer) == []
    with pytest.raises(AssertionError, match=r"^Hanc compact two groups$"):
        assert_hanc_scope(layer)
    assert hanc_polish_errors(core, layer) == [
        "Hanc nominal model needs its two complete compact constituents"
    ]
    layer["segments"]["s06"]["alignments"] = original["segments"]["s06"]["alignments"]
    layer["words"]["w048"] = original["words"]["w048"]
    assert layer == original
    assert_hanc_scope(layer)
    assert layer["words"]["w052"]["explanation"] == DETAIL
