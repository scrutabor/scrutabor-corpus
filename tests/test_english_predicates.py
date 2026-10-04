"""English comparison and jussive predicates keep one coherent realization."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from checks import english, interlinear

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "text,segment,ids,gloss",
    [
        ("ordinarium.deus-qui-humanae", "s02", ["w027", "w028"], "deigned"),
        ("ordinarium.supra-quae", "s02", ["w015", "w016"], "You deigned"),
        (
            "proprium.sanctae-annae-matris-beatae-mariae-virginis-collecta",
            "s01",
            ["w007", "w008"],
            "deigned",
        ),
    ],
)
def test_perfect_dignor_has_one_realization(text, segment, ids, gloss):
    category, name = text.split(".", 1)
    core = json.loads((ROOT / f"texts/{category}/{name}.json").read_bytes())
    layer = json.loads((ROOT / f"languages/en/texts/{category}/{name}.json").read_bytes())
    words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    assert [words[wid]["lemma"] for wid in ids] == ["dignor", "sum"]
    assert words[ids[0]]["morph"]["tense"] == "perf"
    groups = layer["segments"][segment].get("alignments", [])
    assert [g for g in groups if g["words"] == ids] == [
        {"words": ids, "anchor": ids[0], "gloss": gloss}
    ]
    assert all("gloss" not in layer["words"][wid] for wid in ids)
    assert interlinear.check(core, layer) == []


def example(kind):
    rows = {
        "comparison": [
            ("similis", {"pos": "adj", "case": "nom", "number": "sg", "gender": "n"}, "like"),
            (
                "sum",
                {
                    "pos": "verb",
                    "mood": "ind",
                    "tense": "pres",
                    "voice": "act",
                    "person": 3,
                    "number": "sg",
                },
                "is",
            ),
        ],
        "jussive": [
            (
                "sono",
                {
                    "pos": "verb",
                    "mood": "subj",
                    "tense": "pres",
                    "voice": "act",
                    "person": 3,
                    "number": "sg",
                },
                "let sound",
            ),
            ("vox", {"pos": "noun", "case": "nom", "number": "sg", "gender": "f"}, "voice"),
            ("tuus", {"pos": "adj", "case": "nom", "number": "sg", "gender": "f"}, "your"),
        ],
    }[kind]
    words = [
        {"id": f"w{i}", "form": lemma, "lemma": lemma, "morph": morph}
        for i, (lemma, morph, _) in enumerate(rows)
    ]
    if kind == "jussive":
        words[2]["head"] = "w1"
    return {"id": "test.predicates", "segments": [{"id": "s01", "words": words}]}, {
        "lang": "en",
        "segments": {"s01": {}},
        "words": {f"w{i}": {"gloss": gloss} for i, (_, _, gloss) in enumerate(rows)},
    }


def matches(doc, layer):
    return [
        e for e in english.check(doc, layer) if "comparison glosses" in e or "jussive glosses" in e
    ]


@pytest.mark.parametrize("kind", ["comparison", "jussive"])
def test_actual_dispatch_is_required(kind, monkeypatch):
    doc, layer = example(kind)
    assert interlinear.check(doc, layer) == []
    assert len(matches(doc, layer)) == 1
    monkeypatch.setattr(english, "check_predicate_junctions", lambda *_: [])
    assert matches(doc, layer) == []


@pytest.mark.parametrize("kind", ["comparison", "jussive"])
def test_unicode_case_and_whitespace(kind):
    doc, layer = example(kind)
    for word in layer["words"].values():
        text = word["gloss"].upper().replace(" ", "\u00a0\t")
        word["gloss"] = (
            " " + "".join(chr(ord(c) + 0xFEE0) if "A" <= c <= "Z" else c for c in text) + " "
        )
    assert len(matches(doc, layer)) == 1


@pytest.mark.parametrize("kind", ["comparison", "jussive"])
def test_every_lemma_and_required_morphology_boundary(kind):
    baseline, layer = example(kind)
    for i, word in enumerate(baseline["segments"][0]["words"]):
        doc = deepcopy(baseline)
        doc["segments"][0]["words"][i]["lemma"] = "alius"
        assert matches(doc, layer) == []
        for key in word["morph"]:
            # Gender of the comparative adjective is deliberately unrestricted.
            if kind == "comparison" and i == 0 and key == "gender":
                continue
            doc = deepcopy(baseline)
            doc["segments"][0]["words"][i]["morph"][key] = "outside"
            assert matches(doc, layer) == []
    if kind == "jussive":
        doc = deepcopy(baseline)
        doc["segments"][0]["words"][2]["head"] = "w0"
        assert matches(doc, layer) == []


@pytest.mark.parametrize("kind", ["comparison", "jussive"])
def test_punctuation_segments_and_foreign_language(kind):
    baseline, layer = example(kind)
    words = baseline["segments"][0]["words"]
    for boundary in range(1, len(words)):
        for i, key in [(boundary - 1, "post"), (boundary, "pre")]:
            doc = deepcopy(baseline)
            doc["segments"][0]["words"][i][key] = ";"
            assert matches(doc, layer) == []
        doc = deepcopy(baseline)
        doc["segments"] = [
            {"id": "s01", "words": words[:boundary]},
            {"id": "s02", "words": words[boundary:]},
        ]
        assert matches(doc, layer) == []
    layer["lang"] = "pl"
    assert matches(baseline, layer) == []
    assert english.check_predicate_junctions(baseline, layer) == []


@pytest.mark.parametrize("kind", ["comparison", "jussive"])
def test_providers_are_neither_duplicated_nor_inferred(kind):
    doc, baseline = example(kind)
    ids = list(baseline["words"])
    for i, wid in enumerate(ids):
        for shared in (False, True):
            selected = ids[max(0, i - 1) : max(0, i - 1) + 2] if shared else [wid]
            group = (
                {"words": selected, "anchor": selected[0], "gloss": "valid phrase"}
                if shared
                else {"words": selected, "reason": "word-order"}
            )
            layer = deepcopy(baseline)
            layer["segments"]["s01"]["alignments"] = [group]
            for member in selected:
                layer["words"][member].pop("gloss")
            assert interlinear.check(doc, layer) == []
            assert matches(doc, layer) == []
        for invalid in (None, 13, {}, []):
            layer = deepcopy(baseline)
            layer["words"][wid]["gloss"] = invalid
            assert english.check_predicate_junctions(doc, layer) == []
        layer = deepcopy(baseline)
        layer["words"].pop(wid)
        assert english.check_predicate_junctions(doc, layer) == []
        assert interlinear.check(doc, layer)


@pytest.mark.parametrize("replacement", ["similar", "like-minded", "like,", "‘like’", "is like"])
def test_other_comparison_realizations_are_not_this_diagnostic(replacement):
    doc, layer = example("comparison")
    layer["words"]["w0"]["gloss"] = replacement
    assert matches(doc, layer) == []


@pytest.mark.parametrize("replacement", ["may sound", "let it sound", "let your voice sound"])
def test_other_jussives_are_not_this_diagnostic(replacement):
    doc, layer = example("jussive")
    layer["words"]["w0"]["gloss"] = replacement
    assert matches(doc, layer) == []


@pytest.mark.parametrize(
    "name,pairs,comparands",
    [
        ("dominica-in-septuagesima-evangelium", [10], {14: "a man"}),
        ("dominica-vi-post-epiphaniam-evangelium", [9, 53], {13: "a grain", 57: "leaven"}),
        ("dominica-xvii-post-pentecosten-evangelium", [54], {56: "this"}),
        (
            "sanctae-annae-matris-beatae-mariae-virginis-evangelium",
            [10, 38, 62, 133],
            {14: "a treasure", 42: "a man", 66: "a net", 135: "a man"},
        ),
    ],
)
def test_comparisons_and_comparands_are_coherent(name, pairs, comparands):
    core = json.loads((ROOT / f"texts/proprium/{name}.json").read_bytes())
    layer = json.loads((ROOT / f"languages/en/texts/proprium/{name}.json").read_bytes())
    assert interlinear.check(core, layer) == []
    for n in pairs:
        ids = [f"w{n:03}", f"w{n + 1:03}"]
        selected = [g for g in layer["segments"]["s01"]["alignments"] if g["words"] == ids]
        assert len(selected) == 1 and selected[0]["anchor"] == ids[0]
        assert selected[0]["gloss"].casefold() == "is like"
        assert all("gloss" not in layer["words"][wid] for wid in ids)
    for n, expected in comparands.items():
        assert layer["words"][f"w{n:03}"]["gloss"] == expected
