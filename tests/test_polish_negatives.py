"""Negative concord is local; valid copulas and ellipses remain accepted."""

from copy import deepcopy

import pytest

from checks import interlinear, polish
from checks.polish_negatives import check_negative_predicates


def example(kind="finite"):
    nihil = {"id": "w001", "form": "nihil", "lemma": "nihil", "morph": {"pos": "pron"}}
    verb = {
        "id": "w002",
        "form": "respondit",
        "lemma": "respondeo",
        "morph": {"pos": "verb", "mood": "ind"},
    }
    words, glosses = [nihil, verb], ["nic", "odpowiedział"]
    if kind == "participle":
        verb.update(lemma="habeo", morph={"pos": "verb", "mood": "part"})
        glosses[1] = "mający"
    elif kind == "dative":
        pron = {
            "id": "w003",
            "form": "mihi",
            "lemma": "ego",
            "morph": {"pos": "pron", "case": "dat"},
        }
        words, glosses = [nihil, pron, verb], ["nic", "mi", "pomaga"]
    elif kind == "conscius":
        words = [
            nihil,
            {"id": "w003", "form": "enim", "lemma": "enim", "morph": {"pos": "conj"}},
            {"id": "w004", "form": "mihi", "lemma": "ego", "morph": {"pos": "pron", "case": "dat"}},
            {"id": "w005", "form": "conscius", "lemma": "conscius", "morph": {"pos": "adj"}},
            {**verb, "lemma": "sum"},
        ]
        glosses = ["niczego", "bowiem", "sobie", "świadom", "jestem"]
    elif kind == "passive":
        part = {
            "id": "w003",
            "form": "factum",
            "lemma": "facio",
            "morph": {
                "pos": "verb",
                "mood": "part",
                "tense": "perf",
                "voice": "pass",
                "case": "nom",
                "gender": "n",
            },
        }
        words, glosses = [part, {**verb, "lemma": "sum"}, nihil], ["uczynione", "zostało", "nic"]
    elif kind == "sollicitus":
        adj = {"id": "w003", "form": "solliciti", "lemma": "sollicitus", "morph": {"pos": "adj"}}
        words, glosses = [nihil, adj, {**verb, "lemma": "sum"}], ["nic", "zatroskani", "jesteście"]
    doc = {"id": "test.negative", "segments": [{"id": "s01", "words": words}]}
    layer = {
        "lang": "pl",
        "segments": {"s01": {}},
        "words": {w["id"]: {"gloss": g} for w, g in zip(words, glosses, strict=True)},
    }
    return doc, layer


KINDS = ("finite", "participle", "dative", "conscius", "passive", "sollicitus")


@pytest.mark.parametrize("kind", KINDS)
def test_dispatch_actually_calls_the_guard(kind, monkeypatch):
    doc, layer = example(kind)
    assert interlinear.check(doc, layer) == []
    errors = check_negative_predicates(doc, layer)
    assert len(errors) == 1
    assert set(errors) <= set(polish.check(doc, layer))
    monkeypatch.setattr(polish, "check_negative_predicates", lambda *_: [])
    assert not set(errors) & set(polish.check(doc, layer))


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("negative", ("nie", "NIE", "ｎｉｅ", "niemający"))
def test_direct_and_shared_negative_realizations(kind, negative):
    doc, layer = example(kind)
    last = doc["segments"][0]["words"][-1]["id"]
    layer["words"][last]["gloss"] = negative + "\u00a0" + layer["words"][last]["gloss"]
    assert check_negative_predicates(doc, layer) == []
    ids = [w["id"] for w in doc["segments"][0]["words"]]
    layer["words"] = {wid: {} for wid in ids}
    layer["segments"]["s01"]["alignments"] = [
        {"words": ids, "anchor": ids[0], "gloss": "nic " + negative + " odpowiada"}
    ]
    assert interlinear.check(doc, layer) == []
    assert check_negative_predicates(doc, layer) == []
    layer["segments"]["s01"]["alignments"][0]["gloss"] = "nic odpowiada"
    assert len(check_negative_predicates(doc, layer)) == 1


@pytest.mark.parametrize("kind", KINDS)
def test_local_punctuation_segment_and_provider_boundaries(kind):
    baseline, original = example(kind)
    words = baseline["segments"][0]["words"]
    for cut in range(1, len(words)):
        for index, key in ((cut - 1, "post"), (cut, "pre")):
            doc = deepcopy(baseline)
            doc["segments"][0]["words"][index][key] = ";"
            assert check_negative_predicates(doc, original) == []
        doc = deepcopy(baseline)
        doc["segments"] = [{"id": "s01", "words": words[:cut]}, {"id": "s02", "words": words[cut:]}]
        assert check_negative_predicates(doc, original) == []
    for wid in original["words"]:
        for bad in (None, 42, "", "   "):
            layer = deepcopy(original)
            layer["words"][wid]["gloss"] = bad
            assert check_negative_predicates(baseline, layer) == []
        layer = deepcopy(original)
        layer["words"][wid] = {}
        layer["segments"]["s01"]["alignments"] = [{"words": [wid], "reason": "word-order"}]
        assert interlinear.check(baseline, layer) == []
        assert check_negative_predicates(baseline, layer) == []
    for lang in ("en", "la", None):
        layer = deepcopy(original)
        layer["lang"] = lang
        assert check_negative_predicates(baseline, layer) == []


def test_prefix_is_not_negative_and_nominal_copula_is_different():
    doc, layer = example()
    for value in ("niebo", "niech", "niezapominajka"):
        layer["words"]["w002"]["gloss"] = value
        assert len(check_negative_predicates(doc, layer)) == 1
    layer["words"]["w001"]["gloss"] = "niczym"
    layer["words"]["w002"]["gloss"] = "jestem"
    doc["segments"][0]["words"][1]["lemma"] = "sum"
    assert check_negative_predicates(doc, layer) == []
    doc["segments"][0]["words"][1]["lemma"] = "glorior"
    assert len(check_negative_predicates(doc, layer)) == 1


def test_wider_group_and_remote_negative_are_not_borrowed():
    doc, layer = example()
    doc["segments"][0]["words"].append(
        {"id": "w003", "form": "enim", "lemma": "enim", "morph": {"pos": "conj"}}
    )
    layer["words"]["w003"] = {"gloss": "nie"}
    assert len(check_negative_predicates(doc, layer)) == 1
    layer["words"]["w002"] = {}
    layer["words"]["w003"] = {}
    layer["segments"]["s01"]["alignments"] = [
        {"words": ["w002", "w003"], "anchor": "w002", "gloss": "nie odpowiada bowiem"}
    ]
    assert interlinear.check(doc, layer) == []
    assert check_negative_predicates(doc, layer) == []


def test_non_and_nonfinite_boundaries():
    baseline, layer = example()
    for position in (0, 1):
        doc = deepcopy(baseline)
        doc["segments"][0]["words"].insert(position, {"id": "w003", "lemma": "non"})
        assert check_negative_predicates(doc, layer) == []
    for key, value in (("pos", "noun"), ("mood", "inf"), ("mood", "part")):
        doc = deepcopy(baseline)
        doc["segments"][0]["words"][1]["morph"][key] = value
        assert check_negative_predicates(doc, layer) == []
