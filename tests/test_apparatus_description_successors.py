"""Bounded accent-description regressions, distinct from source acceptance."""

import json
import unicodedata
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest
from gospel_delivery_fixture import current_sung_record_hash, current_sung_selected_hash

from build_reader import bibliography_bindings as bindings
from build_reader import store
from build_reader.layers import expand_core
from checks.apparatus import (
    DEPRECATED_ACCENT_RULING,
    deprecated_accent_rulings,
    derived_summary,
    lint_apparatus_summary,
)
from checks.collate import corpus_tokens, load_witness

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads(
    (ROOT / "tests/fixtures/apparatus-description-successors.json").read_text(encoding="utf-8")
)
ROWS = [pytest.param(row, id=f"{row['text']}-{row['at']}") for row in FIXTURE["rows"]]
CHANGED = [
    pytest.param(row, id=f"{row['text']}-{row['at']}")
    for row in FIXTURE["rows"]
    if row["category"] != "already-qualified-retain"
]
RETAINED = [
    pytest.param(row, id=f"{row['text']}-{row['at']}")
    for row in FIXTURE["rows"]
    if row["category"] == "already-qualified-retain"
]
NON_ADDITIONS = [
    pytest.param(row, id=f"{row['text']}-{row['at']}")
    for row in FIXTURE["rows"]
    if row["category"] in {"accent-removal", "accent-shift", "mixed-case-plus-accent"}
]
SUCCESSORS = json.loads(
    (ROOT / "tests/fixtures/capital-accent-positions.json").read_text(encoding="utf-8")
)["description_successor_collations"]


def current_collation_rows(rows, successors):
    """The historical expected rows, each superseded one replaced by its exact current
    successor by stable ID. The historical row must still be complete and exact."""
    by_id: dict[str, dict] = {}
    for successor in successors:
        identity = successor["current"]["id"]
        assert successor["superseded"]["id"] == identity and identity not in by_id
        by_id[identity] = successor
    composed = []
    for row in rows:
        successor = by_id.pop(row["id"], None)
        if successor is None:
            composed.append(row)
            continue
        assert row == successor["superseded"], "superseded expected collation row"
        assert successor["current"]["before_sha256"] == row["before_sha256"]
        composed.append(successor["current"])
    assert not by_id, "every successor names a historical expected row"
    return composed


COLLATIONS = [
    pytest.param(row, id=row["id"])
    for row in current_collation_rows(FIXTURE["collations"], SUCCESSORS)
]


def apparatus(text):
    return json.loads((ROOT / f"witnesses/{text}/apparatus.json").read_text(encoding="utf-8"))


def assert_entry(row, entry):
    assert entry == {
        "at": row["at"],
        "ours": row["ours"],
        "witnesses": {"do": row["do"]},
        "class": "accent",
        "ruling": FIXTURE["rulings"][row["ruling_key"]],
    }, "selected exact accent description and forms"


def without_acute(value):
    return unicodedata.normalize("NFD", value).replace("\u0301", "")


def acute_positions(value):
    position, found = -1, []
    for character in unicodedata.normalize("NFD", value):
        if unicodedata.category(character) != "Mn":
            position += 1
        elif character == "\u0301":
            found.append(position)
    return found


def assert_category(row):
    ours, digital = row["ours"], row["do"]
    left, right = acute_positions(ours), acute_positions(digital)
    assert without_acute(ours).casefold() == without_acute(digital).casefold()
    category = row["category"]
    if category in {"accent-addition", "already-qualified-retain"}:
        assert left and not right and ours.islower() and digital.islower()
        assert without_acute(ours) == digital
    elif category == "accent-removal":
        assert not left and right and ours.islower() and digital.islower()
        assert ours == without_acute(digital)
    elif category == "accent-shift":
        assert left and right and left != right and ours.islower() and digital.islower()
        assert without_acute(ours) == without_acute(digital)
    else:
        assert category == "mixed-case-plus-accent"
        assert left and not right and ours.islower() and digital[0].isupper()
        assert without_acute(ours) != digital


def temporary_apparatus(tmp_path, entry):
    value = {"adjudicated": [deepcopy(entry)]}
    value["summary"] = derived_summary(value)
    path = tmp_path / "apparatus.json"
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def test_exact_population_and_categories_are_not_inferred_from_ruling_words():
    assert len(ROWS) == 46 and len(CHANGED) == 42 and len(RETAINED) == 4
    assert len(NON_ADDITIONS) == 5 and len(COLLATIONS) == 26
    assert len({(row["text"], row["at"]) for row in FIXTURE["rows"]}) == 46
    assert Counter(row["category"] for row in FIXTURE["rows"]) == Counter(
        {
            "accent-addition": 37,
            "accent-removal": 2,
            "accent-shift": 1,
            "mixed-case-plus-accent": 2,
            "already-qualified-retain": 4,
        }
    )
    assert FIXTURE["deprecated_accent_ruling"] == DEPRECATED_ACCENT_RULING


@pytest.mark.parametrize("row", ROWS)
def test_each_exact_ruling_keeps_canonical_face_and_archived_witness_locator(row):
    value = apparatus(row["text"])
    entry = value["adjudicated"][row["index"]]
    snapshot = deepcopy(value)
    assert_entry(row, entry)
    assert_category(row)
    core = store.core(ROOT, row["text"])
    assert bindings.digest(bindings.selected_text(core)) == current_sung_selected_hash(
        row["text"], FIXTURE["texts"][row["text"]]["selected_sha256"]
    )
    tokens = corpus_tokens(expand_core(core))
    assert tokens[row["canonical_ordinal"] - 1] == (row["at"], row["ours"])
    path = ROOT / f"witnesses/{row['text']}/do.txt"
    _metadata, body = load_witness(path)
    line = path.read_text(encoding="utf-8").splitlines()[row["do_line"] - 1]
    assert line.split()[row["do_word_in_line"] - 1] == row["do"]
    if row["locator"] == "unique exact token/unequal-count":
        assert body.split().count(row["do"]) == 1
        assert len(body.split()) != len(tokens)
    else:
        assert row["locator"] == "ordinal/equal-count"
        assert len(body.split()) == len(tokens)
        assert body.split()[row["canonical_ordinal"] - 1] == row["do"]
    for field in ("class", "ours"):
        bad = deepcopy(entry)
        bad[field] = "capital-accent" if field == "class" else "wrong"
        assert bad != entry
        with pytest.raises(AssertionError, match=r"^selected exact accent description and forms"):
            assert_entry(row, bad)
    assert_entry(row, entry)
    assert value == snapshot


@pytest.mark.parametrize("row", CHANGED)
def test_withdrawn_full_template_fails_actual_normal_check_route_then_restores(row, tmp_path):
    entry = apparatus(row["text"])["adjudicated"][row["index"]]
    original = deepcopy(entry)
    path = temporary_apparatus(tmp_path, entry)
    assert lint_apparatus_summary(path) == []
    damaged = deepcopy(entry)
    damaged["ruling"] = DEPRECATED_ACCENT_RULING
    assert damaged != entry
    path = temporary_apparatus(tmp_path, damaged)
    assert lint_apparatus_summary(path) == [
        "apparatus.adjudicated[0]: withdrawn accent ruling template"
    ]
    path = temporary_apparatus(tmp_path, original)
    assert lint_apparatus_summary(path) == [] and entry == original


@pytest.mark.parametrize("row", RETAINED)
def test_four_qualified_capital_typography_statements_are_retained_controls(row, tmp_path):
    entry = apparatus(row["text"])["adjudicated"][row["index"]]
    original = deepcopy(entry)
    assert_entry(row, entry)
    assert "capital typography" in entry["ruling"]
    assert entry["ruling"] != DEPRECATED_ACCENT_RULING
    assert deprecated_accent_rulings({"adjudicated": [entry]}) == []
    assert lint_apparatus_summary(temporary_apparatus(tmp_path, entry)) == []
    assert entry == original


@pytest.mark.parametrize("row", NON_ADDITIONS)
def test_removal_shift_and_mixed_readings_cannot_be_relabelled_as_pure_addition(row):
    entry = apparatus(row["text"])["adjudicated"][row["index"]]
    original = deepcopy(entry)
    assert_entry(row, entry)
    wrong = deepcopy(entry)
    wrong["ruling"] = FIXTURE["rulings"]["accent-addition"]
    assert wrong != entry
    # The narrow template guard is deliberately not a natural-language truth checker.
    assert deprecated_accent_rulings({"adjudicated": [wrong]}) == []
    with pytest.raises(AssertionError, match=r"^selected exact accent description and forms"):
        assert_entry(row, wrong)
    assert_entry(row, entry)
    assert entry == original


def test_template_gate_is_exact_and_class_scoped_not_a_ban_on_words_or_other_classes(tmp_path):
    entry = {"class": "capital-accent", "ruling": DEPRECATED_ACCENT_RULING}
    assert deprecated_accent_rulings({"adjudicated": [entry]}) == []
    assert lint_apparatus_summary(temporary_apparatus(tmp_path, entry)) == []
    entry["class"] = "accent"
    entry["ruling"] = "The selected reading differs in accent, not capital typography."
    assert deprecated_accent_rulings({"adjudicated": [entry]}) == []
    # A paraphrase can evade this mechanical guard; no semantic acceptance follows.
    entry["ruling"] = DEPRECATED_ACCENT_RULING + " "
    assert deprecated_accent_rulings({"adjudicated": [entry]}) == []


@pytest.mark.parametrize("successor", [pytest.param(s, id=s["current"]["id"]) for s in SUCCESSORS])
def test_current_collation_overlay_requires_the_exact_superseded_row(successor):
    rows = deepcopy(FIXTURE["collations"])
    original = deepcopy(rows)
    identity = successor["current"]["id"]
    position = next(i for i, row in enumerate(rows) if row["id"] == identity)
    stale = deepcopy(rows)
    stale[position]["after_sha256"] = successor["current"]["after_sha256"]
    assert stale[position] != successor["superseded"]
    with pytest.raises(AssertionError, match=r"^superseded expected collation row"):
        current_collation_rows(stale, SUCCESSORS)
    missing = [row for row in rows if row["id"] != identity]
    with pytest.raises(AssertionError, match=r"^every successor names a historical expected row"):
        current_collation_rows(missing, SUCCESSORS)
    composed = current_collation_rows(rows, SUCCESSORS)
    assert [row["id"] for row in composed] == [row["id"] for row in rows]
    assert composed[position] == successor["current"]
    replaced = {s["current"]["id"] for s in SUCCESSORS}
    assert [row for row in composed if row["id"] not in replaced] == [
        row for row in rows if row["id"] not in replaced
    ]
    assert rows == original


def test_bad_summary_does_not_hide_the_deprecated_template_or_vice_versa(tmp_path):
    entry = {"class": "accent", "ruling": DEPRECATED_ACCENT_RULING}
    path = temporary_apparatus(tmp_path, entry)
    value = json.loads(path.read_text())
    value["summary"]["entries"] = 0
    path.write_text(json.dumps(value), encoding="utf-8")
    errors = lint_apparatus_summary(path)
    assert errors[0] == "apparatus.adjudicated[0]: withdrawn accent ruling template"
    assert len(errors) == 2 and "summary must be derived" in errors[1]


@pytest.fixture(scope="module")
def source_subjects():
    graph = json.loads((ROOT / "bibliography/graph.json").read_text(encoding="utf-8"))
    collations = {row["id"]: row for row in graph["collations"]}
    required = {wid for row in FIXTURE["collations"] for wid in collations[row["id"]]["witnesses"]}
    snapshot = bindings._SourceSnapshot(ROOT, graph)
    docs, witnesses = {}, {}
    for row in graph["witnesses"]:
        if row["id"] not in required:
            continue
        if row["text"] not in docs:
            docs[row["text"]] = store.core(ROOT, row["text"])
        witnesses[row["id"]] = bindings._witness_subject(
            ROOT, row, docs[row["text"]], snapshot, reviewable=False
        )
    assert set(witnesses) == required
    return docs, witnesses, collations


@pytest.mark.parametrize("row", COLLATIONS)
def test_exact_pending_collation_hash_binds_full_apparatus_with_stale_inverse_control(
    row, source_subjects
):
    docs, witnesses, collations = source_subjects
    current = collations[row["id"]]
    original = deepcopy(current)
    assert current["review"] == {"status": "pending"}
    assert current["apparatus_sha256"] == row["after_sha256"]
    assert bindings.digest(apparatus(row["text"])) == row["after_sha256"]
    assert bindings.digest(
        {k: v for k, v in current.items() if k != "apparatus_sha256"}
    ) == current_sung_record_hash(row["id"], row["unchanged_record_fields_sha256"])
    subject = bindings._collation_subject(
        ROOT, current, docs[row["text"]], witnesses, reviewable=False
    )
    assert subject["collation"] == {k: v for k, v in current.items() if k != "review"}
    wrong = deepcopy(current)
    wrong["apparatus_sha256"] = row["before_sha256"]
    assert wrong != current
    with pytest.raises(
        bindings.BindingError, match=r"^apparatus_sha256 differs from the complete apparatus$"
    ):
        bindings._collation_subject(ROOT, wrong, docs[row["text"]], witnesses, reviewable=False)
    assert (
        bindings._collation_subject(ROOT, current, docs[row["text"]], witnesses, reviewable=False)
        == subject
    )
    assert current == original
