"""Three Gospel contexts preserve agents, possessors and personal referents."""

import json
from copy import deepcopy
from functools import cache
from pathlib import Path

import pytest

from build_reader import store
from build_reader.emit import Table, language_artifact
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear
from checks import translation_provenance as provenance
from checks.language_packs import check_layer

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads(
    (ROOT / "tests/fixtures/gospel-context-constructions.json").read_text(encoding="utf-8")
)
TEXTS = FIXTURE["texts"]
GROUPS = FIXTURE["groups"]
CASES = FIXTURE["prose_cases"]
CHANGED = [row for row in CASES if row["changed"]]
LOWER_CONTROLS = [row for row in CASES if not row["changed"] and row["expected"][0].islower()]
CAPTIONS = FIXTURE["caption_initials"]
PROVENANCE = FIXTURE["provenance"]
TOPOLOGY = (
    ("missing-group", "expected exactly one direct gloss or alignment"),
    ("duplicate-provider", "expected exactly one direct gloss or alignment"),
    ("outside-anchor", "anchor must name the source word carrying the gloss"),
    ("reverse-order", "aligned words must be contiguous and in source order"),
)
TOPOLOGY_CASES = [(row, kind, message) for row in GROUPS for kind, message in TOPOLOGY]


@cache
def _core(text):
    return store.core(ROOT, text)


@cache
def _layer(text, language):
    return store.raw_layer(ROOT, language, text)


def layer(row):
    return deepcopy(_layer(row["text"], row.get("language", "pl")))


def group_for(data, row):
    wanted = row["group"]
    overlaps = [
        group
        for group in data["segments"][row["segment"]].get("alignments", [])
        if set(wanted["words"]) & set(group["words"])
    ]
    assert overlaps == [wanted], "exact contextual group"
    assert all("gloss" not in data["words"][wid] for wid in wanted["words"]), (
        "one shared caption provider"
    )
    return overlaps[0]


def assert_case(data, row):
    prose = data["segments"]["s01"]["translation"]
    assert prose[row["start"] : row["end"]] == row["expected"], "contextual prose initial"


def assert_caption(data, row):
    assert data["words"][row["word"]]["gloss"] == row["after"], "divine caption initial"


def rejects(check, *args, message):
    with pytest.raises(AssertionError) as caught:
        check(*args)
    assert str(caught.value).splitlines()[0] == message


def test_finite_fixture_membership_and_no_implicit_global_case_rule():
    assert len(TEXTS) == len({row["id"] for row in TEXTS}) == 6
    assert len(GROUPS) == len({row["id"] for row in GROUPS}) == 7
    assert sum(len(row["group"]["words"]) for row in GROUPS) == 15
    assert len(CASES) == len({row["id"] for row in CASES}) == 328
    assert len(CHANGED) == 21
    assert len(LOWER_CONTROLS) == 223
    assert len(CAPTIONS) == 6 and len(PROVENANCE) == 4
    assert sum(len(row["edits"]) for row in TEXTS) == 21
    assert {row["family"] for row in CASES} == {"pronoun", "connector"}


@pytest.mark.parametrize("row", TEXTS, ids=lambda row: row["id"])
def test_complete_source_and_language_shape_and_exact_prose_inverse(row):
    core = deepcopy(_core(row["text"]))
    data = layer(row)
    saved = deepcopy((core, data))
    assert provenance.canonical_hash(core) == row["core_sha256"]
    assert core["localization"] == row["localization"] == {"about": True}
    assert sum(len(s["words"]) for s in core["segments"]) == row["source_words"]
    path = ROOT / row["path"]
    assert check_layer(core, data, path) == []
    assert interlinear.check(expand_core(core), enrich_layer(core, data)) == []
    prose = data["segments"]["s01"]["translation"]
    assert provenance.canonical_hash(prose) == row["prose_after_sha256"]
    old = prose
    for edit in reversed(row["edits"]):
        assert old[edit["start"] : edit["end"]] == edit["after"]
        assert edit["after"] == edit["before"][0].upper() + edit["before"][1:]
        old = old[: edit["start"]] + edit["before"] + old[edit["end"] :]
    assert provenance.canonical_hash(old) == row["prose_before_sha256"]
    assert (core, data) == saved


@pytest.mark.parametrize("row", CASES, ids=lambda row: row["id"])
def test_each_explicit_prose_referent_or_connector_keeps_its_local_case(row):
    assert_case(layer(row), row)


@pytest.mark.parametrize("row", CHANGED, ids=lambda row: row["id"])
def test_old_divine_prose_initial_is_rejected_and_same_layer_recovers(row):
    data = layer(row)
    saved = deepcopy(data)
    assert_case(data, row)
    prose = data["segments"]["s01"]["translation"]
    try:
        data["segments"]["s01"]["translation"] = (
            prose[: row["start"]] + row["before"] + prose[row["end"] :]
        )
        assert data != saved
        rejects(assert_case, data, row, message="contextual prose initial")
    finally:
        data.clear()
        data.update(deepcopy(saved))
    assert data == saved
    assert_case(data, row)


@pytest.mark.parametrize("row", LOWER_CONTROLS, ids=lambda row: row["id"])
def test_uppercase_human_reflexive_or_connector_is_rejected_and_recovers(row):
    data = layer(row)
    saved = deepcopy(data)
    assert_case(data, row)
    prose = data["segments"]["s01"]["translation"]
    wrong = row["expected"][0].upper() + row["expected"][1:]
    assert wrong != row["expected"] and len(wrong) == len(row["expected"])
    try:
        data["segments"]["s01"]["translation"] = prose[: row["start"]] + wrong + prose[row["end"] :]
        assert data != saved
        rejects(assert_case, data, row, message="contextual prose initial")
    finally:
        data.clear()
        data.update(deepcopy(saved))
    assert data == saved
    assert_case(data, row)


@pytest.mark.parametrize("row", CAPTIONS, ids=lambda row: row["id"])
def test_divine_polish_caption_initial_rejects_predecessor_and_recovers(row):
    data = layer(row)
    saved = deepcopy(data)
    assert_caption(data, row)
    try:
        data["words"][row["word"]]["gloss"] = row["before"]
        assert data != saved
        rejects(assert_caption, data, row, message="divine caption initial")
    finally:
        data.clear()
        data.update(deepcopy(saved))
    assert data == saved
    assert_caption(data, row)


@pytest.mark.parametrize("row", GROUPS, ids=lambda row: row["id"])
def test_each_short_group_preserves_its_source_analysis_and_one_provider(row):
    core = _core(row["text"])
    words = [w for s in core["segments"] for w in s["words"]]
    assert [w for w in words if w["id"] in row["group"]["words"]] == row["source_words"]
    group_for(layer(row), row)
    polish = deepcopy(_layer(row["text"], "pl"))
    assert {wid: polish["words"][wid] for wid in row["group"]["words"]} == row["polish_entries"]
    assert interlinear.check(core, polish) == []


@pytest.mark.parametrize("row", GROUPS, ids=lambda row: row["id"])
def test_structural_validity_does_not_accept_wrong_agent_or_possessive_order(row):
    core = _core(row["text"])
    data = layer(row)
    saved = deepcopy(data)
    group = group_for(data, row)
    old_order = " ".join(entry["gloss"] for entry in row["before_entries"].values())
    assert old_order != group["gloss"]
    try:
        group["gloss"] = old_order
        assert data != saved
        assert interlinear.check(core, data) == []
        rejects(group_for, data, row, message="exact contextual group")
    finally:
        data.clear()
        data.update(deepcopy(saved))
    assert data == saved
    group_for(data, row)


@pytest.mark.parametrize(
    "row,kind,diagnostic",
    TOPOLOGY_CASES,
    ids=[row["id"] + "-" + kind for row, kind, _message in TOPOLOGY_CASES],
)
def test_actual_alignment_consumer_rejects_bad_topology_and_same_copy_recovers(
    row, kind, diagnostic
):
    core = _core(row["text"])
    data = layer(row)
    saved = deepcopy(data)
    group = group_for(data, row)
    assert interlinear.check(core, data) == []
    try:
        if kind == "missing-group":
            data["segments"][row["segment"]]["alignments"].remove(group)
        elif kind == "duplicate-provider":
            data["words"][group["anchor"]]["gloss"] = group["gloss"]
        elif kind == "outside-anchor":
            group["anchor"] = "w001"
        else:
            group["words"].reverse()
        assert data != saved
        errors = interlinear.check(core, data)
        assert errors and any(diagnostic in error for error in errors)
    finally:
        data.clear()
        data.update(deepcopy(saved))
    assert data == saved
    assert interlinear.check(core, data) == []
    group_for(data, row)


@pytest.mark.parametrize("row", GROUPS, ids=lambda row: row["id"])
def test_former_separate_captions_are_structural_but_not_contextual_recovery(row):
    core = _core(row["text"])
    data = layer(row)
    saved = deepcopy(data)
    group = group_for(data, row)
    try:
        data["segments"][row["segment"]]["alignments"].remove(group)
        for wid, entry in row["before_entries"].items():
            data["words"][wid] = deepcopy(entry)
        assert data != saved
        assert interlinear.check(core, data) == []
        rejects(group_for, data, row, message="exact contextual group")
    finally:
        data.clear()
        data.update(deepcopy(saved))
    assert data == saved
    group_for(data, row)


@pytest.mark.parametrize("row", TEXTS, ids=lambda row: row["id"])
def test_reader_projection_keeps_complete_prose_and_exact_shared_group_routes(row):
    core = _core(row["text"])
    data = layer(row)
    saved = deepcopy(data)
    projected = language_artifact(expand_core(core), enrich_layer(core, data), Table())
    actual = projected["seg"][0]
    assert actual["tr"] == data["segments"]["s01"]["translation"]
    words = core["segments"][0]["words"]
    positions = {w["id"]: i for i, w in enumerate(words)}
    for group in GROUPS:
        if group["text"] != row["text"] or row["language"] != "en":
            continue
        g = group_for(data, group)
        start = positions[g["words"][0]]
        assert {
            "s": start,
            "n": len(g["words"]),
            "a": positions[g["anchor"]] - start,
            "g": g["gloss"],
        } in actual["a"]
        assert all(actual["g"][positions[wid]] is None for wid in g["words"])
    assert data == saved


@cache
def _current_provenance():
    recorded, errors = provenance.load(ROOT)
    assert errors == []
    current = provenance.corpus_sites(ROOT)
    ids = {row["id"] for row in PROVENANCE}
    return {k: current[k] for k in ids}, {k: recorded[k] for k in ids}


@pytest.mark.parametrize("row", PROVENANCE, ids=lambda row: row["id"])
def test_four_exact_target_successors_reject_old_hash_without_new_review(row, monkeypatch):
    current, original = _current_provenance()
    records = deepcopy(original)
    saved = deepcopy(records)
    target = records[row["id"]]
    assert target == row["after_record"]
    old = deepcopy(target)
    old["target_sha256"] = row["before_record"]["target_sha256"]
    assert old == row["before_record"]
    assert (target["origin"], target["review"], target["familiar_core"]) == (
        "working-unsettled",
        "working",
        False,
    )
    with monkeypatch.context() as control:
        control.setattr(provenance, "corpus_sites", lambda _root: deepcopy(current))
        control.setattr(provenance, "load", lambda _root: (records, []))
        healthy = provenance.check(ROOT)
        assert healthy[0] == []
        try:
            target["target_sha256"] = old["target_sha256"]
            assert records != saved
            errors, tally = provenance.check(ROOT)
            assert errors == [f"{row['id']}: stale target_sha256"]
            assert tally == healthy[1]
        finally:
            target.clear()
            target.update(deepcopy(row["after_record"]))
        assert records == saved
        assert provenance.check(ROOT) == healthy
    assert _current_provenance() == (current, original)
