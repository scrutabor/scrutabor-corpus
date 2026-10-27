"""Finite target-sentence reprise cases, not automatic Latin capitalization."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from checks.language_packs import check_layer

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads(
    (ROOT / "tests/fixtures/introit-reprise-caption-boundaries.json").read_text(encoding="utf-8")
)["cases"]
assert len(CASES) == len({row["id"] for row in CASES}) == 27
GROUPS = [row for row in CASES if row["anchor"] is not None]
GROUP_FAULTS = [
    (row, fault) for row in GROUPS for fault in ("anchor", "duplicate", "order", "member")
]


def path_of(text, language=None):
    category, name = text.split(".", 1)
    prefix = ROOT if language is None else ROOT / "languages" / language
    return prefix / "texts" / category / f"{name}.json"


def load(row):
    core = json.loads(path_of(row["text"]).read_text(encoding="utf-8"))
    layer = json.loads(path_of(row["text"], row["language"]).read_text(encoding="utf-8"))
    return core, layer


def caption_errors(row, core, layer):
    errors = []
    segment = next(s for s in core["segments"] if s["id"] == row["segment"])
    words = segment["words"]
    ids = [w["id"] for w in words]
    start = ids.index(row["words"][0])
    selected = words[start : start + len(row["words"])]
    preceding = words[max(0, start - 2) : start]
    if (
        core["id"] != row["text"]
        or layer["text"] != row["text"]
        or layer["language"] != row["language"]
        or [w["id"] for w in selected] != row["words"]
        or [w["form"] for w in selected] != row["forms"]
        or [{"word": w["id"], "form": w["form"], "post": w.get("post", "")} for w in preceding]
        != row["preceding"]
    ):
        errors.append(f"latin:{row['id']}")
    groups = layer["segments"][row["segment"]].get("alignments", [])
    touching = [g for g in groups if set(g["words"]) & set(row["words"])]
    if row["anchor"] is None:
        if touching:
            errors.append(f"unit:{row['id']}")
        actual = layer["words"][row["words"][0]].get("gloss")
    else:
        if (
            len(touching) != 1
            or touching[0]["words"] != row["words"]
            or touching[0].get("anchor") != row["anchor"]
        ):
            errors.append(f"unit:{row['id']}")
        if any("gloss" in layer["words"][wid] for wid in row["words"]):
            errors.append(f"members:{row['id']}")
        actual = touching[0].get("gloss") if touching else None
    if actual != row["expected"]:
        errors.append(f"caption:{row['id']}")
    return errors


def exact_unit(row, layer):
    if row["anchor"] is None:
        return layer["words"][row["words"][0]]
    (group,) = [
        g for g in layer["segments"][row["segment"]]["alignments"] if g["words"] == row["words"]
    ]
    return group


def healthy(row, core, layer):
    assert check_layer(core, layer, path_of(row["text"], row["language"])) == []
    assert caption_errors(row, core, layer) == []


@pytest.mark.parametrize("row", CASES, ids=[row["id"] for row in CASES])
def test_reprise_caption_case_rejects_changed_copy_and_restores(row):
    core, layer = load(row)
    saved = deepcopy(layer)
    healthy(row, core, layer)
    unit = exact_unit(row, layer)
    expected = row["expected"]
    first = expected[0].lower() if expected[0].isupper() else expected[0].upper()
    changed = first + expected[1:]
    try:
        unit["gloss"] = changed
        assert changed != expected and layer != saved
        assert caption_errors(row, core, layer) == [f"caption:{row['id']}"]
        with pytest.raises(AssertionError):
            healthy(row, core, layer)
    finally:
        layer.clear()
        layer.update(saved)
    assert layer == saved
    healthy(row, core, layer)


@pytest.mark.parametrize(
    "row,fault", GROUP_FAULTS, ids=[f"{row['id']}-{fault}" for row, fault in GROUP_FAULTS]
)
def test_exact_group_identity_rejects_tampering_and_restores(row, fault):
    core, layer = load(row)
    saved = deepcopy(layer)
    healthy(row, core, layer)
    group = exact_unit(row, layer)
    try:
        if fault == "anchor":
            group["anchor"] = next(w for w in row["words"] if w != row["anchor"])
        elif fault == "duplicate":
            layer["segments"][row["segment"]]["alignments"].append(deepcopy(group))
        elif fault == "order":
            group["words"].reverse()
        else:
            layer["words"][row["words"][0]]["gloss"] = row["expected"]
        assert layer != saved
        kind = "members" if fault == "member" else "unit"
        assert caption_errors(row, core, layer) == [f"{kind}:{row['id']}"]
        with pytest.raises(AssertionError):
            assert caption_errors(row, core, layer) == []
    finally:
        layer.clear()
        layer.update(saved)
    assert layer == saved
    healthy(row, core, layer)


def test_direct_caption_cannot_be_shadowed_by_a_group():
    row = CASES[1]
    assert (row["language"], row["words"]) == ("en", ["w014"])
    core, layer = load(row)
    saved = deepcopy(layer)
    healthy(row, core, layer)
    try:
        layer["segments"][row["segment"]].setdefault("alignments", []).append(
            {"words": ["w014", "w015"], "anchor": "w014", "gloss": "Rest eternal"}
        )
        assert layer != saved
        assert caption_errors(row, core, layer) == [f"unit:{row['id']}"]
        with pytest.raises(AssertionError):
            healthy(row, core, layer)
    finally:
        layer.clear()
        layer.update(saved)
    assert layer == saved
    healthy(row, core, layer)


def test_reprise_guard_names_its_exact_latin_subject():
    row = next(r for r in CASES if r["text"] == "proprium.cathedra-sancti-petri-introitus")
    core, layer = load(row)
    saved = deepcopy(core)
    healthy(row, core, layer)
    word = next(w for s in core["segments"] for w in s.get("words", []) if w["id"] == "w092")
    try:
        word["form"] = "Condidit"
        assert core != saved
        assert caption_errors(row, core, layer) == [f"latin:{row['id']}"]
        with pytest.raises(AssertionError):
            assert caption_errors(row, core, layer) == []
    finally:
        core.clear()
        core.update(saved)
    assert core == saved
    healthy(row, core, layer)
