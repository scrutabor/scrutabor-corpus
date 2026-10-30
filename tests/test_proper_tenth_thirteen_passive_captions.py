"""Thirteen contextual relations, not an automatic passive grouping rule."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from possessive_sweep_b4_successor_fixture import before_possessive_b4_layer

from build_reader import emit, store
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs, prose
from checks.translation_provenance import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "tests/fixtures/proper-tenth-thirteen-passive-captions.json").read_text())
LITERAL = {
    "tenth-107-pl": ("w086 w087", "w086", "zostali posłani"),
    "tenth-107-en": ("w086 w087", "w086", "have been sent"),
    "tenth-108-pl": ("w002 w003", "w002", "są zaszczyceni"),
    "tenth-108-en": ("w002 w003", "w002", "are honored"),
    "tenth-109-en": ("w008 w009", "w008", "is strengthened"),
    "tenth-110-pl": ("w060 w061", "w060", "zostali zaliczeni"),
    "tenth-110-en": ("w060 w061", "w060", "have been reckoned"),
    "tenth-111-pl": ("w004 w005", "w004", "są zaszczyceni"),
    "tenth-111-en": ("w004 w005", "w004", "are honored"),
    "tenth-112-en": ("w010 w011", "w010", "is strengthened"),
    "tenth-113-pl": ("w004 w005", "w004", "została dana"),
    "tenth-113-en": ("w004 w005", "w004", "has been given"),
    "tenth-114-pl": ("w148 w149", "w148", "jest napisane"),
    "tenth-114-en": ("w148 w149", "w148", "is written"),
    "tenth-116-pl": ("w189 w190", "w190", "obym był obroniony"),
    "tenth-116-en": ("w189 w190", "w190", "may I be defended"),
    "tenth-117-pl": ("w006 w007", "w006", "została rozlana"),
    "tenth-117-en": ("w006 w007", "w006", "has been poured out"),
    "tenth-118-pl": ("w002 w003", "w003", "była poślubiona"),
    "tenth-118-en": ("w002 w003", "w003", "was betrothed"),
    "tenth-119-pl": ("w093 w094", "w093", "zostały powiedziane"),
    "tenth-119-en": ("w093 w094", "w093", "were spoken"),
}
SCALAR_LITERAL = {
    "companion-1": "Will stand",
    "companion-2": "will be shaken",
    "companion-3": "will be amazed",
    "companion-4": "will be fulfilled",
    "companion-5": "przez",
}

STABAT_SOURCE_SUCCESSOR = {
    "text": "proprium.septem-dolorum-beatae-mariae-virginis-sequentia",
    "word_before": {
        "id": "w108",
        "form": "istud",
        "lemma": "iste",
        "morph": {"pos": "pron", "case": "acc", "number": "sg"},
    },
    "word_after": {
        "id": "w108",
        "form": "istud",
        "lemma": "iste",
        "morph": {"pos": "pron", "case": "acc", "number": "sg", "gender": "n"},
    },
    "before_core_sha256": "6cca0d3404612dfdeae665ac21c641968c5d0a75219ef1d41e26e32d39350709",
    "after_core_sha256": "d67b4a1ed71ceef21066e29c3d08e34f04e5730dedded2a6a63409437ac8c672",
    "rows": {
        "pl": {
            "before": {
                "site": "proprium.septem-dolorum-beatae-mariae-virginis-sequentia.s11.pl",
                "text": "proprium.septem-dolorum-beatae-mariae-virginis-sequentia",
                "segment": "s11",
                "language": "pl",
                "familiar_core": False,
                "origin": "working-unsettled",
                "review": "working",
                "source_sha256": "2b259455c503c95dfbad7f04569c87644045f3415353f44bf0014b32e8cae5f7",
                "target_sha256": "308d590d9b1c97ef5e60a8ea929e1387de91dbb04efaf3b1214f751872be58fa",
            },
            "after": {
                "site": "proprium.septem-dolorum-beatae-mariae-virginis-sequentia.s11.pl",
                "text": "proprium.septem-dolorum-beatae-mariae-virginis-sequentia",
                "segment": "s11",
                "language": "pl",
                "familiar_core": False,
                "origin": "working-unsettled",
                "review": "working",
                "source_sha256": "494d83215bf818a7611197e465c5491e2361c235c6eec92149c1b0928f9fed28",
                "target_sha256": "308d590d9b1c97ef5e60a8ea929e1387de91dbb04efaf3b1214f751872be58fa",
            },
        },
        "en": {
            "before": {
                "site": "proprium.septem-dolorum-beatae-mariae-virginis-sequentia.s11.en",
                "text": "proprium.septem-dolorum-beatae-mariae-virginis-sequentia",
                "segment": "s11",
                "language": "en",
                "familiar_core": False,
                "origin": "working-unsettled",
                "review": "working",
                "source_sha256": "2b259455c503c95dfbad7f04569c87644045f3415353f44bf0014b32e8cae5f7",
                "target_sha256": "d529cc96e606dc7486b32ecd5a34d69838dc1b940c7378f3b587feb17177ccbd",
            },
            "after": {
                "site": "proprium.septem-dolorum-beatae-mariae-virginis-sequentia.s11.en",
                "text": "proprium.septem-dolorum-beatae-mariae-virginis-sequentia",
                "segment": "s11",
                "language": "en",
                "familiar_core": False,
                "origin": "working-unsettled",
                "review": "working",
                "source_sha256": "494d83215bf818a7611197e465c5491e2361c235c6eec92149c1b0928f9fed28",
                "target_sha256": "d529cc96e606dc7486b32ecd5a34d69838dc1b940c7378f3b587feb17177ccbd",
            },
        },
    },
}
LAYERS = [pytest.param(r, id=r["id"]) for r in DATA["layers"]]
GROUPS = [pytest.param(r, id=r["id"]) for r in DATA["groups"]]
CONTROLS = [pytest.param(r, id=r["id"]) for r in DATA["controls"]]
SCALARS = [pytest.param(r, id=r["id"]) for r in DATA["scalars"]]


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


def touching(layer, members):
    return [
        g
        for s in layer["segments"].values()
        for g in s.get("alignments", [])
        if set(g["words"]) & set(members)
    ]


def reviewed(layer, case):
    words, anchor, gloss = LITERAL[case["id"]]
    expected = dict(words=words.split(), anchor=anchor, gloss=gloss)
    assert case["group"] == expected, "literal contextual oracle"
    assert touching(layer, expected["words"]) == [expected], "contextual short predicate"
    assert all("gloss" not in layer["words"][w] for w in expected["words"]), (
        "contextual short predicate"
    )


def retained(layer, case):
    assert touching(layer, case["members"]) == case["groups"], "retained contextual relation"
    assert {w: layer["words"][w] for w in case["members"]} == case["words"], (
        "retained contextual relation"
    )


def preserved(layer, case):
    layer = before_possessive_b4_layer(layer)
    comparison = deepcopy(layer)
    for g in DATA["groups"]:
        if (g["text"], g["language"]) == (case["text"], case["language"]):
            reviewed(comparison, g)
    for w, change in case["word_changes"].items():
        assert comparison["words"][w] == change["after"], "exact changed word fields"
        comparison["words"][w] = deepcopy(change["before"])
    for sid, change in case["alignment_changes"].items():
        assert comparison["segments"][sid]["alignments"] == change["after"]
        if change["before_present"]:
            comparison["segments"][sid]["alignments"] = deepcopy(change["before"])
        else:
            del comparison["segments"][sid]["alignments"]
    assert canonical_hash(comparison) == case["before_sha256"], "unchanged contextual remainder"


def compact(core, layer):
    tables = [emit.Table() for _ in range(4)]
    doc, target = expand_core(core), enrich_layer(core, layer)
    return (
        emit.core_artifact(doc, core, *tables[:3]),
        emit.language_artifact(doc, target, tables[3]),
        [t.order for t in tables],
    )


def predecessor_core(core, case):
    """An exact comparison copy; native and reader consumers retain current input."""
    if case["text"] != STABAT_SOURCE_SUCCESSOR["text"]:
        return core
    rule = STABAT_SOURCE_SUCCESSOR
    assert canonical_hash(core) == rule["after_core_sha256"], "exact current Stabat core"
    comparison = deepcopy(core)
    words = [w for s in comparison["segments"] for w in s.get("words", []) if w["id"] == "w108"]
    assert words == [rule["word_after"]], "exact current Stabat core"
    del words[0]["morph"]["gender"]
    assert words == [rule["word_before"]], "exact current Stabat core"
    assert canonical_hash(comparison) == rule["before_core_sha256"] == case["core_sha256"]
    return comparison


def predecessor_provenance(rows, case):
    if case["text"] != STABAT_SOURCE_SUCCESSOR["text"]:
        return rows
    rule = STABAT_SOURCE_SUCCESSOR["rows"][case["language"]]
    expected = deepcopy(case["provenance"])
    indices = [i for i, row in enumerate(expected) if row["site"] == rule["before"]["site"]]
    assert len(indices) == 1 and expected[indices[0]] == rule["before"]
    expected[indices[0]] = deepcopy(rule["after"])
    assert rows == expected, "exact current Stabat provenance"
    comparison = deepcopy(rows)
    comparison[indices[0]] = deepcopy(rule["before"])
    assert comparison == case["provenance"]
    return comparison


def exercise_source_comparison_guards(core, layer, rows, case):
    """Comparison guards, not assertions that every mutation is native-invalid."""
    saved_core, saved_rows = deepcopy(core), deepcopy(rows)
    for fault in ("missing-gender", "wrong-gender", "unselected-form"):
        try:
            word = next(
                w for s in core["segments"] for w in s.get("words", []) if w["id"] == "w108"
            )
            if fault == "missing-gender":
                del word["morph"]["gender"]
            elif fault == "wrong-gender":
                word["morph"]["gender"] = "f"
            else:
                core["segments"][0]["words"][0]["form"] += "x"
            assert core != saved_core
            with pytest.raises(AssertionError, match=r"^exact current Stabat core(?:\n|$)"):
                predecessor_core(core, case)
        finally:
            core.clear()
            core.update(deepcopy(saved_core))
            assert core == saved_core
            healthy(core, layer)
            assert canonical_hash(predecessor_core(core, case)) == case["core_sha256"]
    for fault in ("source-sha", "target-sha", "extra-field"):
        try:
            selected = next(
                r
                for r in rows
                if r["site"] == STABAT_SOURCE_SUCCESSOR["rows"][case["language"]]["after"]["site"]
            )
            if fault == "extra-field":
                selected["unexpected_comparison_field"] = True
            else:
                selected["source_sha256" if fault == "source-sha" else "target_sha256"] = "0" * 64
            assert rows != saved_rows
            with pytest.raises(AssertionError, match=r"^exact current Stabat provenance(?:\n|$)"):
                predecessor_provenance(rows, case)
        finally:
            assert len(rows) == len(saved_rows)
            for row, original in zip(rows, saved_rows, strict=True):
                row.clear()
                row.update(deepcopy(original))
            assert rows == saved_rows
            healthy(core, layer)
            assert predecessor_provenance(rows, case) == case["provenance"]


@pytest.mark.parametrize("case", LAYERS)
def test_complete_current_native_reader_prose_and_predecessor(case):
    core, layer = load(case)
    saved = deepcopy((core, layer, DATA))
    healthy(core, layer)
    assert canonical_hash(predecessor_core(core, case)) == case["core_sha256"]
    preserved(layer, case)
    assert {sid: s.get("translation") for sid, s in layer["segments"].items()} == case["prose"]
    ledger = json.loads(
        (ROOT / "languages" / case["language"] / "translation-provenance.json").read_text()
    )
    saved_ledger = deepcopy(ledger)
    rows = [r for r in ledger["sites"] if r["text"] == case["text"]]
    assert predecessor_provenance(rows, case) == case["provenance"]
    base, target, tables = compact(core, layer)
    expected_core, expected_layers = emit._strip(
        expand_core(core), {case["language"]: enrich_layer(core, layer)}
    )
    assert emit.expand(base, target, *tables) == (expected_core, expected_layers[case["language"]])
    if case["text"] == STABAT_SOURCE_SUCCESSOR["text"]:
        exercise_source_comparison_guards(core, layer, rows, case)
    assert (core, layer, DATA) == saved
    assert ledger == saved_ledger


@pytest.mark.parametrize("case", GROUPS)
def test_exact_members_anchor_and_latin_contributions(case):
    core, layer = load(case)
    healthy(core, layer)
    reviewed(layer, case)
    assert [
        w for s in core["segments"] for w in s.get("words", []) if w["id"] in case["members"]
    ] == case["source_words"]
    assert len(case["members"]) == 2


@pytest.mark.parametrize("case", GROUPS)
@pytest.mark.parametrize("fault", ["residual", "duplicate", "reversed", "anchor", "missing"])
def test_real_native_faults_and_same_object_recovery(case, fault):
    core, layer = load(case)
    saved = deepcopy(layer)
    healthy(core, layer)
    reviewed(layer, case)
    (group,) = touching(layer, case["members"])
    groups = layer["segments"][case["segment"]]["alignments"]
    try:
        if fault == "residual":
            layer["words"][case["members"][0]]["gloss"] = case["residual_gloss"]
            message = "expected exactly one direct gloss or alignment"
        elif fault == "duplicate":
            i = next(i for i, g in enumerate(groups) if g is group)
            groups.insert(i + 1, deepcopy(group))
            message = "belongs to more than one alignment"
        elif fault == "reversed":
            group["words"].reverse()
            message = "contiguous and in source order"
        elif fault == "anchor":
            group["anchor"] = case["outside_word"]
            message = "anchor must name the source word carrying the gloss"
        else:
            groups.remove(group)
            message = "expected exactly one direct gloss or alignment"
        assert layer != saved
        assert any(message in e for e in interlinear.check(core, layer))
        assert any(
            message in e
            for e in language_packs.check_layer(
                core, layer, store.layer_path(ROOT, case["language"], case["text"])
            )
        )
    finally:
        layer.clear()
        layer.update(saved)
        assert layer == saved
        healthy(core, layer)
        reviewed(layer, case)


@pytest.mark.parametrize("case", GROUPS)
@pytest.mark.parametrize("fault", ["agency", "legal-wrong-anchor"])
def test_structurally_legal_meaning_damage_is_not_native_semantic_approval(case, fault):
    core, layer = load(case)
    saved = deepcopy(layer)
    healthy(core, layer)
    reviewed(layer, case)
    try:
        (group,) = touching(layer, case["members"])
        if fault == "agency":
            group["gloss"] = case["wrong_predicate"]
        else:
            group["anchor"] = next(w for w in group["words"] if w != group["anchor"])
        assert layer != saved
        healthy(core, layer)
        with pytest.raises(AssertionError, match=r"^contextual short predicate(?:\n|$)"):
            reviewed(layer, case)
    finally:
        layer.clear()
        layer.update(saved)
        assert layer == saved
        healthy(core, layer)
        reviewed(layer, case)


@pytest.mark.parametrize("case", GROUPS)
@pytest.mark.parametrize("fault", ["gloss", "anchor"])
def test_actual_compact_reader_damage_and_same_artifact_recovery(case, fault):
    core, layer = load(case)
    healthy(core, layer)
    base, target, tables = compact(core, layer)
    saved = deepcopy(target)
    _, decoded = emit.expand(base, target, *tables)
    reviewed(decoded, case)
    segment = next(s for s in target["seg"] if s["id"] == case["segment"])
    words = next(s["words"] for s in core["segments"] if s["id"] == case["segment"])
    start = [w["id"] for w in words].index(case["members"][0])
    cell = next(r for r in segment["a"] if r["s"] == start)
    try:
        if fault == "gloss":
            cell["g"] = case["wrong_predicate"]
        else:
            assert cell["a"] == case["members"].index(case["group"]["anchor"])
            cell["a"] = 1 - cell["a"]
        assert target != saved
        _, decoded = emit.expand(base, target, *tables)
        assert interlinear.check(core, decoded) == []
        with pytest.raises(AssertionError, match=r"^contextual short predicate(?:\n|$)"):
            reviewed(decoded, case)
    finally:
        target.clear()
        target.update(saved)
        assert target == saved
        _, decoded = emit.expand(base, target, *tables)
        reviewed(decoded, case)


@pytest.mark.parametrize("case", SCALARS)
def test_exact_future_or_agent_companion_and_same_layer_recovery(case):
    core, layer = load(case)
    saved = deepcopy(layer)
    healthy(core, layer)
    assert case["after"]["gloss"] == SCALAR_LITERAL[case["id"]]
    assert layer["words"][case["word"]] == case["after"]
    try:
        layer["words"][case["word"]] = deepcopy(case["before"])
        assert layer != saved
        healthy(core, layer)
        with pytest.raises(AssertionError, match=r"^exact contextual companion(?:\n|$)"):
            assert layer["words"][case["word"]] == case["after"], "exact contextual companion"
    finally:
        layer.clear()
        layer.update(saved)
        assert layer == saved
        healthy(core, layer)
        assert layer["words"][case["word"]] == case["after"]


@pytest.mark.parametrize("case", CONTROLS)
@pytest.mark.parametrize("fault", ["caption", "forced-group"])
def test_retained_strengthening_and_shared_copula_are_not_forced_into_new_groups(case, fault):
    core, layer = load(case)
    saved = deepcopy(layer)
    healthy(core, layer)
    retained(layer, case)
    if case["id"].startswith("tenth-115-"):
        source = next(s for s in core["segments"] if s["id"] == "s03")["words"]
        words = {w["id"]: w for w in source}
        assert words["w020"]["head"] == words["w022"]["head"] == "w026"
        assert words["w021"]["lemma"] == "et" and words["w023"]["lemma"] == "sum"
        assert [layer["words"][w]["gloss"] for w in ("w020", "w021")] == (
            ["smutna", "i"] if case["language"] == "pl" else ["sad", "and"]
        )
    try:
        if fault == "caption":
            if case["groups"]:
                touching(layer, case["members"])[0]["gloss"] = "changed retained state"
            else:
                layer["words"][case["members"][0]]["gloss"] = "changed retained state"
        else:
            segment = layer["segments"][case["segment"]]
            remaining = [
                g
                for g in segment.get("alignments", [])
                if not set(g["words"]) & set(case["members"])
            ]
            remaining.append(
                dict(
                    words=case["members"], anchor=case["members"][0], gloss="changed retained state"
                )
            )
            segment["alignments"] = sorted(remaining, key=lambda g: g["words"][0])
            for w in case["members"]:
                layer["words"][w].pop("gloss", None)
        assert layer != saved
        healthy(core, layer)
        with pytest.raises(AssertionError, match=r"^retained contextual relation(?:\n|$)"):
            retained(layer, case)
    finally:
        layer.clear()
        layer.update(saved)
        assert layer == saved
        healthy(core, layer)
        retained(layer, case)


@pytest.mark.parametrize("case", LAYERS)
def test_whole_inverse_does_not_hide_unselected_prose(case):
    core, layer = load(case)
    saved = deepcopy(layer)
    healthy(core, layer)
    preserved(layer, case)
    try:
        sid = next(sid for sid, s in layer["segments"].items() if s.get("translation"))
        layer["segments"][sid]["translation"] += " Added."
        assert layer != saved
        with pytest.raises(AssertionError, match=r"^unchanged contextual remainder(?:\n|$)"):
            preserved(layer, case)
    finally:
        layer.clear()
        layer.update(saved)
        assert layer == saved
        healthy(core, layer)
        preserved(layer, case)
