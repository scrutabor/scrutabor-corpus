"""Selected negative predicates; exact readings, not a universal word-order rule."""

from pathlib import Path

import pytest

from build_reader import store
from checks import interlinear

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("ordinarium.panem-caelestem", "s04", [9, 10], 10, "sum", "pres", "ind", "sg", 1, "I am not"),
    ("ordinarium.panem-caelestem", "s07", [26, 27], 27, "sum", "pres", "ind", "sg", 1, "I am not"),
    ("ordinarium.panem-caelestem", "s10", [43, 44], 44, "sum", "pres", "ind", "sg", 1, "I am not"),
    (
        "proprium.dominica-i-adventus-graduale",
        "s01",
        [5, 6],
        6,
        "confundo",
        "fut",
        "ind",
        "pl",
        3,
        "will not be put to shame",
    ),
    (
        "proprium.dominica-i-adventus-evangelium",
        "s07",
        [118, 119],
        119,
        "transeo",
        "fut",
        "ind",
        "pl",
        3,
        "will not pass away",
    ),
    (
        "proprium.corporis-christi-sequentia",
        "s04",
        [41, 42],
        42,
        "ambigo",
        "pres",
        "ind",
        "sg",
        3,
        "it is not doubted",
    ),
    (
        "proprium.dominica-ii-passionis-communio",
        "s01",
        [3, 4],
        4,
        "possum",
        "pres",
        "ind",
        "sg",
        3,
        "cannot",
    ),
    (
        "proprium.dominica-ii-passionis-evangelium",
        "s10",
        [120, 121],
        121,
        "possum",
        "pres",
        "ind",
        "sg",
        3,
        "cannot",
    ),
    (
        "proprium.septem-dolorum-beatae-mariae-virginis-sequentia",
        "s05",
        [43, 44],
        44,
        "fleo",
        "impf",
        "subj",
        "sg",
        3,
        "would not weep",
    ),
    (
        "proprium.commemoratio-omnium-fidelium-defunctorum-missa-i-sequentia",
        "s14",
        [144, 145],
        145,
        "sum",
        "pres",
        "ind",
        "pl",
        3,
        "are not",
    ),
    (
        "proprium.dominica-iii-adventus-evangelium",
        "s03",
        [29, 30, 31],
        30,
        "sum",
        "pres",
        "ind",
        "sg",
        1,
        "I am not",
    ),
]


@pytest.mark.parametrize("text,sid,nums,anchor,lemma,tense,mood,number,person,gloss", CASES)
def test_selected_negative_predicate(
    text, sid, nums, anchor, lemma, tense, mood, number, person, gloss
):
    core, layers = store.load(ROOT, text)
    layer = layers["en"]
    words = next(s["words"] for s in core["segments"] if s["id"] == sid)
    ids = [f"w{n:03}" for n in nums]
    indices = [next(i for i, w in enumerate(words) if w["id"] == wid) for wid in ids]
    assert indices == list(range(indices[0], indices[0] + len(ids)))
    assert [words[i]["lemma"] for i in indices] == ["non", lemma] + (
        ["ego"] if len(ids) == 3 else []
    )
    finite = words[indices[1]]["morph"]
    assert (finite["tense"], finite["mood"], finite["number"], finite["person"]) == (
        tense,
        mood,
        number,
        person,
    )
    assert finite["voice"] == ("pass" if lemma in {"confundo", "ambigo"} else "act")
    groups = [g for g in layer["segments"][sid].get("alignments", []) if set(g["words"]) & set(ids)]
    assert groups == [{"words": ids, "anchor": f"w{anchor:03}", "gloss": gloss}]
    assert all("gloss" not in layer["words"][wid] for wid in ids)
    assert not interlinear.check(core, layer)


@pytest.mark.parametrize("text", sorted({row[0] for row in CASES}))
def test_complete_member_storage_and_provider_coverage(text):
    core = store.core(ROOT, text)
    layer = store.raw_layer(ROOT, "en", text)
    assert list(layer["words"]) == [w["id"] for s in core["segments"] for w in s.get("words", [])]
    assert not interlinear.check(core, layer)


def test_three_invocations_remain_separate():
    core, layers = store.load(ROOT, "ordinarium.panem-caelestem")
    layer = layers["en"]
    for sid, ids, anchor in [
        ("s04", ["w009", "w010"], "w010"),
        ("s07", ["w026", "w027"], "w027"),
        ("s10", ["w043", "w044"], "w044"),
    ]:
        segment = next(s for s in core["segments"] if s["id"] == sid)
        assert [w["lemma"] for w in segment["words"]] == ["dominus", "non", "sum", "dignus"]
        assert layer["segments"][sid]["alignments"] == [
            {"words": ids, "anchor": anchor, "gloss": "I am not"}
        ]


def test_lauda_content_is_not_a_new_nominative_subject():
    core = store.core(ROOT, "proprium.corporis-christi-sequentia")
    words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    assert words["w032"]["lemma"] == "qui" and words["w032"]["morph"]["case"] == "acc"
    assert words["w040"]["lemma"] == "do" and words["w040"]["morph"]["case"] == "acc"
    assert words["w040"]["morph"]["tense"] == "perf"
    assert words["w040"]["morph"]["voice"] == "pass"
