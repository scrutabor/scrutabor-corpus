"""Finite negative existence, possession and named contextual companions.

Literal semantic guards are not an automatic Polish case analyzer.
"""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from lateran_epistle_fixture import before_lateran_rows, before_lateran_targets
from negative_government_fixture import DATA, predecessor_core, predecessor_layer, predecessor_rows

from build_reader import emit, store
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs, prose
from checks.translation_provenance import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
LITERAL = {
    "caption-01": "śmierci",
    "caption-02": "nie będzie",
    "caption-03": "życia",
    "caption-04": "wiecznego",
    "caption-05": "nikogo, kto",
    "caption-06": "nie będzie",
    "caption-07": "na",
    "caption-08": "on",
    "caption-09": "ludem",
    "caption-10": "Bogiem",
    "caption-11": "I",
    "caption-12": "I",
    "caption-13": "I",
    "caption-14": "Oto",
    "caption-15": "Oto",
    "caption-16": "aniołów",
}
LAYERS = [pytest.param(r, id=r["id"]) for r in DATA["layers"]]
CAPTIONS = [pytest.param(r, id=r["id"]) for r in DATA["captions"]]
CONTROLS = [pytest.param(r, id=r["id"]) for r in DATA["controls"]]
KEEP_LITERAL = (
    "Bóg",
    "i",
    "z",
    "morderca",
    "trwającego",
    "ani",
    "Moje",
    "było",
    "było",
    "śmierć",
    "śmierć",
    "trud",
    "daremny",
)
FRAME_LITERAL = {
    "death": [
        "i",
        "śmierci",
        "już",
        "nie",
        "będzie",
        "ani",
        "smutku",
        "ani",
        "wołania",
        "ani",
        "bólu",
        "nie będzie",
        "już",
    ],
    "predicates": [
        "I",
        "oni",
        "ludem",
        "Jego",
        "będą",
        "i",
        "sam",
        "Bóg",
        "z",
        "nimi",
        "będzie",
        "ich",
        "Bogiem",
    ],
    "throne-pl": [
        "I",
        "rzekł",
        "Ten, który",
        "siedział",
        "na",
        "tronie",
        "Oto",
        "nowym",
        "czynię",
        "wszystko",
    ],
    "throne-en": ["He who", "was sitting", "on", "the throne"],
    "possession": [
        "A",
        "wiecie",
        "że",
        "żaden",
        "morderca",
        "nie",
        "ma",
        "życia",
        "wiecznego",
        "w",
        "sobie",
        "trwającego",
    ],
    "inhabitant": ["i", None, "niech nie będzie", "nikogo, kto", "zamieszka", "w", "nim"],
    "coordination": [
        "jakiego",
        "nie",
        "było",
        "od",
        "początku",
        "świata",
        "aż",
        "dotąd",
        "ani",
        "nie będzie",
    ],
    "speech": ["I", "usłyszałem", "głos", "donośny", "z", "tronu", "mówiący", "Oto"],
}
FRAMES = [pytest.param(r, id=r["id"]) for r in DATA["frames"]]


def load(case):
    return store.core(ROOT, case["text"]), store.raw_layer(ROOT, case["language"], case["text"])


def healthy(core, layer):
    assert language_packs.check_core(core) == []
    assert (
        language_packs.check_layer(
            core, layer, store.layer_path(ROOT, layer["language"], core["id"])
        )
        == []
    )
    assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
    assert prose.check(layer) == []


def reviewed(layer, case):
    expected = LITERAL[case["id"]]
    assert case["after"] == expected, "literal contextual government"
    assert layer["words"][case["word"]].get("gloss") == expected, "literal contextual government"
    assert not any(
        case["word"] in group["words"]
        for segment in layer["segments"].values()
        for group in segment.get("alignments", [])
    ), "literal contextual government"


def compact(core, layer):
    tables = [emit.Table() for _ in range(4)]
    doc, target = expand_core(core), enrich_layer(core, layer)
    return (
        emit.core_artifact(doc, core, *tables[:3]),
        emit.language_artifact(doc, target, tables[3]),
        [table.order for table in tables],
    )


@pytest.mark.parametrize("case", LAYERS)
def test_complete_current_layer_native_reader_and_exact_inverse(case):
    core, layer = load(case)
    saved = deepcopy((core, layer, DATA))
    healthy(core, layer)
    assert canonical_hash(predecessor_core(core)) == case["core_sha256"]
    comparison_layer = before_lateran_targets(layer)
    comparison = predecessor_layer(layer)
    assert canonical_hash(comparison) == case["before_sha256"]
    assert {s: r.get("translation") for s, r in comparison_layer["segments"].items()} == case[
        "prose"
    ]
    assert {s: r.get("alignments", []) for s, r in comparison_layer["segments"].items()} == case[
        "alignments"
    ]
    ledger = json.loads(
        (ROOT / "languages" / case["language"] / "translation-provenance.json").read_text()
    )
    rows = [r for r in ledger["sites"] if r["text"] == case["text"]]
    assert before_lateran_rows(rows) == case["provenance"]
    base, target, tables = compact(core, layer)
    wanted_core, wanted = emit._strip(
        expand_core(core), {case["language"]: enrich_layer(core, layer)}
    )
    assert emit.expand(base, target, *tables) == (wanted_core, wanted[case["language"]])
    assert (core, layer, DATA) == saved


@pytest.mark.parametrize("case", CAPTIONS)
def test_contextual_literal_rejects_old_word_and_same_entry_recovers(case):
    core, layer = load(case)
    healthy(core, layer)
    reviewed(layer, case)
    entry = layer["words"][case["word"]]
    saved = deepcopy(entry)
    try:
        entry["gloss"] = case["before"]
        assert entry != saved
        with pytest.raises(AssertionError, match=r"^literal contextual government(?:\n|$)"):
            reviewed(layer, case)
    finally:
        entry.clear()
        entry.update(saved)
        assert layer["words"][case["word"]] is entry and entry == saved
        healthy(core, layer)
        reviewed(layer, case)


@pytest.mark.parametrize("case", CAPTIONS)
def test_missing_actual_native_provider_rejects_and_same_entry_recovers(case):
    core, layer = load(case)
    healthy(core, layer)
    reviewed(layer, case)
    entry = layer["words"][case["word"]]
    saved = deepcopy(entry)
    try:
        del entry["gloss"]
        assert entry != saved
        diagnostic = "expected exactly one direct gloss or alignment"
        assert any(diagnostic in e for e in interlinear.check(core, layer))
        assert any(
            diagnostic in e
            for e in language_packs.check_layer(
                core, layer, store.layer_path(ROOT, case["language"], case["text"])
            )
        )
    finally:
        entry.clear()
        entry.update(saved)
        assert layer["words"][case["word"]] is entry and entry == saved
        healthy(core, layer)
        reviewed(layer, case)


@pytest.mark.parametrize("case", CAPTIONS)
def test_actual_reader_direct_caption_damage_and_same_artifact_recovery(case):
    core, layer = load(case)
    healthy(core, layer)
    base, target, tables = compact(core, layer)
    saved = deepcopy(target)
    _, decoded = emit.expand(base, target, *tables)
    reviewed(decoded, case)
    segment = next(
        s for s in core["segments"] if any(w["id"] == case["word"] for w in s.get("words", []))
    )
    position = [w["id"] for w in segment["words"]].index(case["word"])
    cell = next(s for s in target["seg"] if s["id"] == segment["id"])
    try:
        cell["g"][position] = case["before"]
        assert target != saved
        _, decoded = emit.expand(base, target, *tables)
        with pytest.raises(AssertionError, match=r"^literal contextual government(?:\n|$)"):
            reviewed(decoded, case)
    finally:
        target.clear()
        target.update(saved)
        assert target == saved
        _, decoded = emit.expand(base, target, *tables)
        reviewed(decoded, case)
        healthy(core, layer)


@pytest.mark.parametrize("case", LAYERS)
@pytest.mark.parametrize("fault", ["missing", "wrong", "extra"])
def test_whole_current_inverse_rejects_unaccounted_fields_then_recovers(case, fault):
    core, layer = load(case)
    saved = deepcopy(layer)
    healthy(core, layer)
    predecessor_layer(layer)
    try:
        if fault == "missing":
            del layer["words"]["w001"]
        elif fault == "wrong":
            layer["about"] += " Changed."
        else:
            layer["words"]["w001"]["extra"] = True
        assert layer != saved
        with pytest.raises(AssertionError, match=r"^complete current government layer(?:\n|$)"):
            predecessor_layer(layer)
    finally:
        layer.clear()
        layer.update(saved)
        assert layer == saved
        healthy(core, layer)
        predecessor_layer(layer)


@pytest.mark.parametrize("case", CONTROLS)
def test_nominative_genitive_continuation_and_elliptical_keeps(case):
    core, layer = load(case)
    healthy(core, layer)
    source = next(
        w for s in core["segments"] for w in s.get("words", []) if w["id"] == case["word"]
    )
    assert source == case["source_word"]
    entry = layer["words"][case["word"]]
    saved = deepcopy(entry)
    assert tuple(r["gloss"] for r in DATA["controls"]) == KEEP_LITERAL
    assert entry["gloss"] == case["gloss"]
    try:
        entry["gloss"] = "changed retained reading"
        assert entry != saved
        with pytest.raises(AssertionError, match=r"^retained contextual control(?:\n|$)"):
            assert entry["gloss"] == case["gloss"], "retained contextual control"
    finally:
        entry.clear()
        entry.update(saved)
        assert layer["words"][case["word"]] is entry and entry == saved
        healthy(core, layer)


@pytest.mark.parametrize("fault", ["target", "origin", "extra"])
def test_complete_current_provenance_inverse_rejects_then_same_row_recovers(fault):
    ledger = json.loads((ROOT / "languages/pl/translation-provenance.json").read_text())
    rows = [r for r in ledger["sites"] if r["site"] == DATA["provenance"]["after"]["site"]]
    assert len(rows) == 1
    row = rows[0]
    saved = deepcopy(row)
    assert predecessor_rows(rows) == [DATA["provenance"]["before"]]
    try:
        row[{"target": "target_sha256", "origin": "origin", "extra": "extra"}[fault]] = "wrong"
        assert row != saved
        with pytest.raises(
            AssertionError, match=r"^complete current government provenance(?:\n|$)"
        ):
            predecessor_rows(rows)
    finally:
        row.clear()
        row.update(saved)
        assert rows[0] is row and row == saved
        assert predecessor_rows(rows) == [DATA["provenance"]["before"]]


def test_prose_case_changes_have_one_exact_current_target_digest():
    row = DATA["provenance"]["after"]
    layer = store.raw_layer(ROOT, "pl", row["text"])
    wording = layer["segments"]["s01"]["translation"]
    assert "swoich aniołów" in wording and "lecz Moje słowa" in wording
    assert "Aniołów" not in wording and "moje słowa" not in wording
    assert canonical_hash(wording) == row["target_sha256"]
    assert DATA["provenance"]["before"]["source_sha256"] == row["source_sha256"]
    assert set(LITERAL) == {r["id"] for r in DATA["captions"]}


def readback(core, layer, frame):
    selected = [
        w for s in core["segments"] for w in s.get("words", []) if w["id"] in frame["members"]
    ]
    assert selected == frame["source_words"], "complete contextual source frame"
    values = []
    for wid in frame["members"]:
        groups = [
            g
            for s in layer["segments"].values()
            for g in s.get("alignments", [])
            if wid in g["words"]
        ]
        assert len(groups) <= 1, "complete contextual government readback"
        if groups:
            assert "gloss" not in layer["words"][wid], "complete contextual government readback"
            values.append(groups[0].get("gloss") if groups[0].get("anchor") == wid else None)
        else:
            values.append(layer["words"][wid].get("gloss"))
    assert values == FRAME_LITERAL[frame["id"]], "complete contextual government readback"


@pytest.mark.parametrize("frame", FRAMES)
def test_contextual_polarity_government_subject_and_boundary_readback_recovers(frame):
    core, layer = load(frame)
    healthy(core, layer)
    readback(core, layer, frame)
    entry = layer["words"][frame["word"]]
    saved = deepcopy(entry)
    try:
        entry["gloss"] = frame["before"]
        assert entry != saved
        with pytest.raises(
            AssertionError, match=r"^complete contextual government readback(?:\n|$)"
        ):
            readback(core, layer, frame)
    finally:
        entry.clear()
        entry.update(saved)
        assert layer["words"][frame["word"]] is entry and entry == saved
        healthy(core, layer)
        readback(core, layer, frame)
