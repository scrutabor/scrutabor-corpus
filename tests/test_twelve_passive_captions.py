"""Short passive compounds preserve context without reusing a neighboring auxiliary."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import emit
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs, prose

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads(
    (ROOT / "tests/fixtures/twelve-passive-captions.json").read_text(encoding="utf-8")
)
CASES = DATA["cases"]
CONTROLS = DATA["controls"]
LAYERS = list(DATA["layers"])
FAULTS = ("split", "residual", "duplicate", "order", "anchor", "wide", "zero")
CREED = "ordinarium.credo"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def canonical(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def load(language, text):
    path = DATA["cores"][text]["path"]
    raw = (ROOT / path).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == DATA["cores"][text]["raw_sha256"]
    return json.loads(raw), json.loads((ROOT / "languages" / language / path).read_bytes())


def parent_at(value, pointer):
    for key in pointer[:-1]:
        value = value[key]
    return value, pointer[-1]


def predecessor(layer):
    result = deepcopy(layer)
    if layer["language"] == "en" and layer["text"] == CREED:
        require(
            canonical(result) == "d7de9f14766b37930719788ad05a5db9eef31775faf3478a044803dd68a24653",
            "whole passive predecessor",
        )
        for segment, group, captions in (
            (
                "s13",
                {"words": ["w113", "w114"], "anchor": "w114", "gloss": "there will be no"},
                {"w113": "no", "w114": "there will be"},
            ),
            (
                "s19",
                {"words": ["w161", "w162"], "anchor": "w162", "gloss": "of the age to come"},
                {"w161": "to come", "w162": "of the age"},
            ),
        ):
            groups = result["segments"][segment]["alignments"]
            require(groups[-1] == group, "whole passive predecessor")
            require(
                all("gloss" not in result["words"][wid] for wid in captions),
                "whole passive predecessor",
            )
            groups.pop()
            if not groups:
                del result["segments"][segment]["alignments"]
            for wid, gloss in captions.items():
                result["words"][wid]["gloss"] = gloss
        require(
            canonical(result) == "c96b861ca17d25ad250ace5f1aede154afe94d3aa8e1fea2b21dd8a046ddbfd0",
            "whole passive predecessor",
        )
    path = DATA["layers"][layer["language"] + ":" + layer["text"]]["path"]
    for operation in reversed(DATA["operations"]):
        if operation["path"] != path:
            continue
        parent, key = parent_at(result, operation["pointer"])
        require((key in parent) == operation["after_exists"], "passive successor presence")
        if key in parent:
            require(parent[key] == operation["after"], "passive successor value")
        if operation["before_exists"]:
            parent[key] = deepcopy(operation["before"])
        else:
            del parent[key]
    expected = DATA["layers"][layer["language"] + ":" + layer["text"]]["before_canonical"]
    require(canonical(result) == expected, "whole passive predecessor")
    return result


def selected(case, layer):
    groups = layer["segments"][case["segment"]].get("alignments", [])
    touching = [g for g in groups if set(g["words"]) & set(case["group"]["words"])]
    require(touching == [case["group"]], "reviewed short passive")
    require(
        all("gloss" not in layer["words"][wid] for wid in case["group"]["words"]),
        "reviewed short passive",
    )


def retained(control, layer):
    touching = [
        group
        for segment in layer["segments"].values()
        for group in segment.get("alignments", [])
        if set(group["words"]) & set(control["words"])
    ]
    require(touching == control["groups"], "retained passive context")
    require(
        {wid: layer["words"][wid] for wid in control["words"]} == control["entries"],
        "retained passive context",
    )


def healthy(core, layer):
    text, language = layer["text"], layer["language"]
    require(canonical(core) == DATA["cores"][text]["canonical_sha256"], "unchanged Latin core")
    indexed = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    for case in CASES:
        if (case["text"], case["language"]) == (text, language):
            require(
                [indexed[wid] for wid in case["group"]["words"]] == case["source_words"],
                "reviewed passive source",
            )
            selected(case, layer)
    for control in CONTROLS:
        if (control["text"], control["language"]) == (text, language):
            require(
                [indexed[wid] for wid in control["words"]] == control["source_words"],
                "retained passive source",
            )
            retained(control, layer)
    predecessor(layer)
    assert language_packs.check_core(core) == []
    path = ROOT / "languages" / language / DATA["cores"][text]["path"]
    assert language_packs.check_layer(core, layer, path) == []
    assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
    assert prose.check(layer) == []


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_selected_compound_and_real_language_contract(case):
    healthy(*load(case["language"], case["text"]))


@pytest.mark.parametrize("identity", LAYERS)
def test_whole_layer_predecessor_preserves_prose_help_and_outside_captions(identity):
    language, text = identity.split(":", 1)
    core, layer = load(language, text)
    healthy(core, layer)
    saved = deepcopy(layer)
    result = predecessor(layer)
    assert result is not layer and layer == saved


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_wrong_voice_number_or_complement_rejects_then_recovers(case):
    core, layer = load(case["language"], case["text"])
    healthy(core, layer)
    saved = deepcopy(layer)
    group = next(g for g in layer["segments"][case["segment"]]["alignments"] if g == case["group"])
    try:
        group["gloss"] = case["wrong"]
        assert layer != saved and case["wrong"] != case["group"]["gloss"]
        assert interlinear.check(core, layer) == []
        with pytest.raises(AssertionError, match=r"^reviewed short passive$"):
            selected(case, layer)
    finally:
        layer.clear()
        layer.update(deepcopy(saved))
        assert layer == saved
        healthy(core, layer)


@pytest.mark.parametrize(
    "case,fault",
    [(case, fault) for case in CASES for fault in FAULTS],
    ids=[case["id"] + "-" + fault for case in CASES for fault in FAULTS],
)
def test_exact_membership_and_unjustified_zero_reject_then_recover(case, fault):
    core, layer = load(case["language"], case["text"])
    healthy(core, layer)
    saved = deepcopy(layer)
    groups = layer["segments"][case["segment"]]["alignments"]
    group = next(g for g in groups if g == case["group"])
    try:
        if fault in ("split", "zero"):
            groups.remove(group)
            if not groups:
                del layer["segments"][case["segment"]]["alignments"]
            for wid, entry in case["before_entries"].items():
                layer["words"][wid] = deepcopy(entry)
            if fault == "zero":
                first = case["group"]["words"][0]
                del layer["words"][first]["gloss"]
                layer["segments"][case["segment"]].setdefault("alignments", []).append(
                    {"words": [first], "reason": "word-order"}
                )
                order = {
                    w["id"]: i for s in core["segments"] for i, w in enumerate(s.get("words", []))
                }
                layer["segments"][case["segment"]]["alignments"].sort(
                    key=lambda g: order[g["words"][0]]
                )
        elif fault == "residual":
            layer["words"][case["group"]["words"][0]]["gloss"] = group["gloss"]
        elif fault == "duplicate":
            groups.append(deepcopy(group))
        elif fault == "order":
            group["words"].reverse()
        elif fault == "anchor":
            group["anchor"] = next(w for w in group["words"] if w != group["anchor"])
        else:
            group["words"] = sorted([*group["words"], case["outside_word"]])
            del layer["words"][case["outside_word"]]["gloss"]
        assert layer != saved
        errors = interlinear.check(expand_core(core), enrich_layer(core, layer))
        diagnostics = {
            "residual": "expected exactly one direct gloss or alignment",
            "duplicate": "belongs to more than one alignment",
            "order": "contiguous and in source order",
        }
        if fault in diagnostics:
            assert any(diagnostics[fault] in error for error in errors)
        else:
            assert errors == []
        with pytest.raises(AssertionError, match=r"^reviewed short passive$"):
            selected(case, layer)
    finally:
        layer.clear()
        layer.update(deepcopy(saved))
        assert layer == saved
        healthy(core, layer)


@pytest.mark.parametrize("control", CONTROLS, ids=[control["id"] for control in CONTROLS])
def test_kept_compounds_protected_holds_and_nonpassive_controls(control):
    healthy(*load(control["language"], control["text"]))


@pytest.mark.parametrize("control", CONTROLS, ids=[control["id"] for control in CONTROLS])
def test_real_kept_control_mutation_rejects_then_recovers(control):
    core, layer = load(control["language"], control["text"])
    healthy(core, layer)
    saved = deepcopy(layer)
    try:
        layer["words"][control["words"][0]]["gloss"] = "changed"
        assert layer != saved
        with pytest.raises(AssertionError, match=r"^retained passive context$"):
            retained(control, layer)
    finally:
        layer.clear()
        layer.update(deepcopy(saved))
        assert layer == saved
        healthy(core, layer)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_false_creed_pair_cannot_consume_previous_sentence_auxiliary(language):
    core, layer = load(language, CREED)
    healthy(core, layer)
    saved = deepcopy(layer)
    try:
        layer["segments"]["s10"].setdefault("alignments", []).insert(
            0,
            {
                "words": ["w075", "w076"],
                "anchor": "w076",
                "gloss": "został ukrzyżowany" if language == "pl" else "was crucified",
            },
        )
        del layer["words"]["w076"]["gloss"]
        assert layer != saved
        assert any(
            "alignment names a word outside this segment" in error
            for error in interlinear.check(core, layer)
        )
    finally:
        layer.clear()
        layer.update(deepcopy(saved))
        assert layer == saved
        healthy(core, layer)


def artifact_for(core, layer):
    return emit.language_artifact(expand_core(core), enrich_layer(core, layer), emit.Table())


def reader_case(core, artifact, case):
    segment = next(s for s in core["segments"] if s["id"] == case["segment"])
    order = [w["id"] for w in segment["words"]]
    row = next(s for s in artifact["seg"] if s["id"] == case["segment"])
    start = order.index(case["group"]["words"][0])
    compact = {
        "s": start,
        "n": len(case["group"]["words"]),
        "a": order.index(case["group"]["anchor"]) - start,
        "g": case["group"]["gloss"],
    }
    stop = start + compact["n"]
    touching = [
        group for group in row.get("a", []) if group["s"] < stop and start < group["s"] + group["n"]
    ]
    require(touching == [compact], "reader short passive")
    require(
        all(row["g"][order.index(wid)] is None for wid in case["group"]["words"]),
        "reader short passive",
    )
    return row, compact


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_real_reader_projection_keeps_each_selected_member_once(case):
    core, layer = load(case["language"], case["text"])
    healthy(core, layer)
    artifact = artifact_for(core, layer)
    reader_case(core, artifact, case)


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_actual_reader_payload_damage_rejects_then_recovers(case):
    core, layer = load(case["language"], case["text"])
    healthy(core, layer)
    artifact = artifact_for(core, layer)
    reader_case(core, artifact, case)
    saved = deepcopy(artifact)
    for fault in ("caption", "duplicate", "direct"):
        row, expected = reader_case(core, artifact, case)
        target = next(g for g in row["a"] if g == expected)
        try:
            if fault == "caption":
                target["g"] = case["wrong"]
            elif fault == "duplicate":
                row["a"].append(deepcopy(target))
            else:
                row["g"][expected["s"]] = "extra"
            assert artifact != saved
            with pytest.raises(AssertionError, match=r"^reader short passive$"):
                reader_case(core, artifact, case)
        finally:
            artifact.clear()
            artifact.update(deepcopy(saved))
            assert artifact == saved
            reader_case(core, artifact, case)


@pytest.mark.parametrize("identity", LAYERS)
@pytest.mark.parametrize("fault", ["prose", "help", "outside"])
def test_unrelated_full_layer_change_cannot_hide_in_inverse(identity, fault):
    language, text = identity.split(":", 1)
    core, layer = load(language, text)
    healthy(core, layer)
    saved = deepcopy(layer)
    try:
        if fault == "prose":
            first = next(iter(layer["segments"]))
            field = "translation" if "translation" in layer["segments"][first] else "narrative"
            layer["segments"][first][field] += " Extra."
        elif fault == "help":
            layer["words"]["w001"]["note"] = "Extra."
        else:
            layer["words"]["w001"]["gloss"] += " extra"
        assert layer != saved
        with pytest.raises(AssertionError, match=r"^whole passive predecessor$"):
            predecessor(layer)
    finally:
        layer.clear()
        layer.update(deepcopy(saved))
        assert layer == saved
        healthy(core, layer)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_all_existing_provenance_rows_remain_exact(language):
    path = ROOT / "languages" / language / "translation-provenance.json"
    ledger = json.loads(path.read_bytes())
    rows = [row for row in ledger["sites"] if row["text"] in DATA["cores"]]
    assert rows == DATA["provenance"][language]
