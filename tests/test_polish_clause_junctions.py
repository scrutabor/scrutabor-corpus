"""Precise Polish construction diagnostics exclude different Latin/provider scopes."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from checks import interlinear, polish
from checks.polish_clauses import check_clause_junctions

ROOT = Path(__file__).resolve().parents[1]
CASES = (
    (("w022", "w023"), ("zamętu", "szumu")),
    (("w027", "w028"), ("mdlejącymi", "ludźmi")),
    (("w054", "w055", "w056", "w057"), ("gdy te", "zaś", "dziać się", "zaczną")),
    (("w091", "w092", "w093"), ("zobaczycie", "to", "dziać się")),
)
REQUIRED = (
    (("pos", "case", "number"), ("pos", "case", "number")),
    (
        ("pos", "mood", "tense", "voice", "case", "number", "gender"),
        ("pos", "case", "number", "gender"),
    ),
    (
        ("pos", "case", "number", "gender"),
        ("pos",),
        ("pos", "mood", "tense", "voice"),
        ("pos", "mood", "tense", "voice", "case", "number", "gender"),
    ),
    (
        ("pos", "mood", "tense", "voice", "person", "number"),
        ("pos", "case", "number", "gender"),
        ("pos", "mood", "tense", "voice"),
    ),
)


def example(kind):
    core = json.loads((ROOT / "texts/proprium/dominica-i-adventus-evangelium.json").read_text())
    words = {w["id"]: w for s in core["segments"] for w in s["words"]}
    ids, glosses = CASES[kind]
    doc = {
        "id": "test.polish-clauses",
        "segments": [{"id": "s01", "words": [words[w] for w in ids]}],
    }
    layer = {
        "lang": "pl",
        "segments": {"s01": {}},
        "words": {w: {"gloss": g} for w, g in zip(ids, glosses, strict=True)},
    }
    return doc, layer


def dispatched(doc, layer):
    return [e for e in polish.check(doc, layer) if "Polish " in e and " glosses produce " in e]


@pytest.mark.parametrize("kind", range(4))
def test_real_dispatch_and_provider_positive(kind, monkeypatch):
    doc, layer = example(kind)
    assert not interlinear.check(doc, layer)
    assert len(dispatched(doc, layer)) == 1
    monkeypatch.setattr(polish, "check_clause_junctions", lambda *_: [])
    assert dispatched(doc, layer) == []


@pytest.mark.parametrize("kind", range(4))
def test_each_latin_feature_and_lemma_is_required(kind):
    baseline, layer = example(kind)
    for index, keys in enumerate(REQUIRED[kind]):
        for key in ("lemma", *keys):
            doc = deepcopy(baseline)
            word = doc["segments"][0]["words"][index]
            target = word if key == "lemma" else word["morph"]
            target[key] = "different"
            assert check_clause_junctions(doc, layer) == [], (index, key)
    for word in baseline["segments"][0]["words"]:
        if "head" in word:
            doc = deepcopy(baseline)
            next(w for w in doc["segments"][0]["words"] if w["id"] == word["id"])["head"] = (
                "elsewhere"
            )
            assert check_clause_junctions(doc, layer) == []


@pytest.mark.parametrize("kind", range(4))
@pytest.mark.parametrize("suffix", ["", ".", "?!", "…", " , "])
def test_unicode_spacing_case_and_terminal_punctuation(kind, suffix):
    doc, layer = example(kind)
    for word in layer["words"].values():
        word["gloss"] = " \t" + word["gloss"].upper().replace(" ", "\u00a0\t") + suffix
    assert len(check_clause_junctions(doc, layer)) == 1


@pytest.mark.parametrize("kind", range(4))
def test_all_provider_boundaries_are_structurally_valid(kind):
    doc, baseline = example(kind)
    ids = list(baseline["words"])
    for index, wid in enumerate(ids):
        for shared in (False, True):
            layer = deepcopy(baseline)
            members = ids[max(0, index - 1) : max(0, index - 1) + 2] if shared else [wid]
            alignment = (
                {"words": members, "anchor": members[0], "gloss": "wspólne wyrażenie"}
                if shared
                else {"words": members, "reason": "word-order"}
            )
            layer["segments"]["s01"]["alignments"] = [alignment]
            for member in members:
                layer["words"][member].pop("gloss")
            assert interlinear.check(doc, layer) == []
            assert check_clause_junctions(doc, layer) == []
            # Isolate explicit provider membership from the missing direct gloss.
            # This extra fixture is intentionally structurally invalid.
            for member in members:
                layer["words"][member] = deepcopy(baseline["words"][member])
            assert interlinear.check(doc, layer)
            assert check_clause_junctions(doc, layer) == []


@pytest.mark.parametrize("kind", range(4))
def test_every_internal_source_and_segment_boundary(kind):
    baseline, layer = example(kind)
    words = baseline["segments"][0]["words"]
    for cut in range(1, len(words)):
        for index, key in ((cut - 1, "post"), (cut, "pre")):
            doc = deepcopy(baseline)
            doc["segments"][0]["words"][index][key] = ";"
            assert check_clause_junctions(doc, layer) == []
        doc = deepcopy(baseline)
        doc["segments"] = [{"id": "s01", "words": words[:cut]}, {"id": "s02", "words": words[cut:]}]
        assert check_clause_junctions(doc, layer) == []


@pytest.mark.parametrize("kind", range(4))
def test_missing_unknown_and_other_language_are_not_semantic_rejections(kind):
    doc, baseline = example(kind)
    for wid in baseline["words"]:
        for value in (None, 23, {}, [], "inne wyrażenie"):
            layer = deepcopy(baseline)
            layer["words"][wid]["gloss"] = value
            assert check_clause_junctions(doc, layer) == []
        layer = deepcopy(baseline)
        del layer["words"][wid]
        assert check_clause_junctions(doc, layer) == []
    baseline["lang"] = "en"
    assert check_clause_junctions(doc, baseline) == []
    assert check_clause_junctions({}, {}) == []
