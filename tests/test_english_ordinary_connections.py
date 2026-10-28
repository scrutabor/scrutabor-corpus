"""Short English constructions retain scope, recipients and finite prayer."""

from copy import deepcopy
from pathlib import Path

import pytest
from test_twelve_passive_captions import predecessor

from build_reader import emit, store
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs

ROOT = Path(__file__).resolve().parents[1]
CREED = "ordinarium.credo"
CANON = "ordinarium.te-igitur"
TRINITY = "ordinarium.suscipe-sancta-trinitas"
CASES = ("kingdom", "age", "canon-recipient", "trinity-recipient", "petition")
SUBJECTS = {
    "kingdom": CREED,
    "age": CREED,
    "canon-recipient": CANON,
    "trinity-recipient": TRINITY,
    "petition": CANON,
}
GROUPS = {
    "kingdom": ("s13", ["w113", "w114"], "w114", "there will be no"),
    "age": ("s19", ["w161", "w162"], "w162", "of the age to come"),
    "petition": ("s04", ["w017", "w018"], "w017", "You may accept"),
}
OLD = {
    "kingdom": ("no", "there will be"),
    "age": ("to come", "of the age"),
    "petition": ("accept",),
}
WRONG = {
    "kingdom": "there will be",
    "age": "of the life to come",
    "petition": "we may accept",
}


def load(case):
    text = SUBJECTS[case]
    return store.core(ROOT, text), store.raw_layer(ROOT, "en", text)


def reader(core, layer):
    doc, target = expand_core(core), enrich_layer(core, layer)
    assert language_packs.check_core(core) == [], "native core"
    assert language_packs.check_layer(core, layer, store.layer_path(ROOT, "en", core["id"])) == []
    assert interlinear.check(doc, target) == [], "native realization"
    parses, analyses, shared, local = emit.Table(), emit.Table(), emit.Table(), emit.Table()
    base = emit.core_artifact(doc, core, parses, analyses, shared)
    localized = emit.language_artifact(doc, target, local)
    back, received = emit.expand(
        base, localized, parses.order, analyses.order, shared.order, local.order
    )
    assert back["segments"] == doc["segments"]
    assert received["words"] == target["words"]
    for sid, segment in target["segments"].items():
        assert received["segments"][sid].get("alignments") == segment.get("alignments")
    return received, localized


def meaning(case, core, layer):
    received, artifact = reader(core, layer)
    words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    if case in GROUPS:
        sid, members, anchor, gloss = GROUPS[case]
        expected = {"words": members, "anchor": anchor, "gloss": gloss}
        touching = [
            g
            for g in received["segments"][sid].get("alignments", [])
            if set(g["words"]) & set(members)
        ]
        assert touching == [expected], "English construction"
        assert [interlinear.effective_gloss(received, w) for w in members] == [
            gloss if w == anchor else "" for w in members
        ]
        segment = next(s for s in core["segments"] if s["id"] == sid)
        order = [w["id"] for w in segment["words"]]
        start = order.index(members[0])
        row = next(s for s in artifact["seg"] if s["id"] == sid)
        compact = {"s": start, "n": 2, "a": order.index(anchor) - start, "g": gloss}
        assert [a for a in row["a"] if a["s"] == start] == [compact]
        assert row["g"][start : start + 2] == [None, None]
        if case == "kingdom":
            assert words["w113"]["lemma"] == "non"
            assert words["w114"]["morph"]["tense"] == "fut"
            assert words["w115"]["morph"]["case"] == "nom"
        elif case == "age":
            assert words["w161"]["head"] == "w162"
            assert words["w161"]["morph"]["case"] == "gen"
            assert words["w161"]["morph"]["gender"] == "n"
            assert words["w161"]["morph"]["tense"] == "fut"
            assert words["w160"]["morph"]["case"] == "acc"
            assert received["words"]["w161"]["explanation"]
        else:
            assert words["w018"]["morph"]["person"] == 2
            assert words["w018"]["morph"]["mood"] == "subj"
            assert words["w020"]["morph"]["person"] == 2
            assert words["w020"]["morph"]["mood"] == "subj"
            assert layer["words"]["w016"]["gloss"] == "that"
            assert layer["words"]["w019"]["gloss"] == "and"
            assert layer["words"]["w020"]["gloss"] == "bless"
    else:
        wid = "w032" if case == "canon-recipient" else "w007"
        before, after = ("w031", "w033") if wid == "w032" else ("w006", "w008")
        assert words[wid]["morph"]["case"] == "dat"
        assert words[before]["morph"]["case"] == "acc"
        assert words[after]["morph"]["person"] == 1
        assert words[after]["morph"]["number"] == "pl"
        assert interlinear.effective_gloss(received, wid) == "to You", "divine recipient"


@pytest.mark.parametrize("case", CASES)
def test_current_connections_reach_reader_storage(case):
    meaning(case, *load(case))


@pytest.mark.parametrize("case", CASES)
def test_predecessor_and_wrong_scope_fail_then_restore(case):
    core, layer = load(case)
    saved = deepcopy(layer)
    meaning(case, core, layer)
    faults = ("old", "wrong", "duplicate") if case in GROUPS else ("old", "wrong")
    for fault in faults:
        try:
            if case in GROUPS:
                sid, members, _, _ = GROUPS[case]
                group = next(
                    g for g in layer["segments"][sid]["alignments"] if g["words"] == members
                )
                if fault == "old" and case != "petition":
                    layer["segments"][sid]["alignments"].remove(group)
                    if not layer["segments"][sid]["alignments"]:
                        del layer["segments"][sid]["alignments"]
                    for wid, gloss in zip(members, OLD[case], strict=True):
                        layer["words"][wid]["gloss"] = gloss
                elif fault == "duplicate":
                    layer["words"][members[0]]["gloss"] = "extra"
                else:
                    group["gloss"] = OLD[case][0] if fault == "old" else WRONG[case]
            else:
                wid = "w032" if case == "canon-recipient" else "w007"
                layer["words"][wid]["gloss"] = "You" if fault == "old" else "from You"
            assert layer != saved
            if fault == "duplicate":
                assert any(
                    "exactly one" in error
                    for error in interlinear.check(expand_core(core), enrich_layer(core, layer))
                )
            with pytest.raises(AssertionError):
                meaning(case, core, layer)
        finally:
            layer.clear()
            layer.update(deepcopy(saved))
        assert layer == saved
        meaning(case, core, layer)


def test_coordination_and_other_valid_caption_shapes_are_retained():
    core, layer = load("petition")
    saved = deepcopy(layer)
    reader(core, layer)
    assert layer["words"]["w001"]["gloss"] == "You"
    assert layer["words"]["w020"]["gloss"] == "bless"
    # Repeating the modal is grammatical, although this bounded wording does not need it.
    alternative = deepcopy(layer)
    alternative["words"]["w020"]["gloss"] = "You may bless"
    received, _ = reader(core, alternative)
    assert interlinear.effective_gloss(received, "w020") == "You may bless"
    assert layer == saved
    creed, english = load("age")
    received, _ = reader(creed, english)
    assert interlinear.effective_gloss(received, "w043") == "not"
    assert interlinear.effective_gloss(received, "w103") == "will come"
    assert interlinear.effective_gloss(received, "w160") == "the life"


def test_full_creed_comparison_inverse_rejects_drift_without_mutating_native_input():
    core, layer = load("age")
    saved = deepcopy(layer)
    meaning("age", core, layer)
    meaning("kingdom", core, layer)
    old = predecessor(layer)
    assert old is not layer and old != layer and layer == saved
    for fault in ("prose", "help", "outside", "new-caption", "new-anchor"):
        try:
            if fault == "prose":
                layer["segments"]["s13"]["translation"] += " Extra."
            elif fault == "help":
                layer["words"]["w161"]["explanation"] += " Extra."
            elif fault == "outside":
                layer["words"]["w001"]["gloss"] += " extra"
            else:
                group = layer["segments"]["s13"]["alignments"][-1]
                group["gloss" if fault == "new-caption" else "anchor"] = "wrong"
            assert layer != saved
            with pytest.raises(AssertionError, match=r"^whole passive predecessor(?:\n|$)"):
                predecessor(layer)
        finally:
            layer.clear()
            layer.update(deepcopy(saved))
        assert layer == saved and predecessor(layer) == old
        meaning("kingdom", core, layer)
        meaning("age", core, layer)
