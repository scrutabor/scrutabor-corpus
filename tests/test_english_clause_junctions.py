"""English clause junctions retain subjects and respect construction boundaries."""

from copy import deepcopy

import pytest

from checks import english, interlinear


def example(kind):
    rows = {
        "temporal": [
            ("cum", {"pos": "conj"}, "when"),
            (
                "video",
                {
                    "pos": "verb",
                    "mood": "ind",
                    "voice": "act",
                    "person": 2,
                    "number": "pl",
                    "tense": "futperf",
                },
                "see",
            ),
        ],
        "perception": [
            (
                "video",
                {
                    "pos": "verb",
                    "mood": "ind",
                    "voice": "act",
                    "person": 2,
                    "number": "pl",
                    "tense": "futperf",
                },
                "you see",
            ),
            (
                "hic",
                {"pos": "pron", "case": "acc", "gender": "n", "number": "pl"},
                "these things",
            ),
            (
                "fio",
                {"pos": "verb", "mood": "inf", "tense": "pres", "voice": "act"},
                "to happen",
            ),
        ],
        "additive": [
            ("ita", {"pos": "adv"}, "so"),
            ("et", {"pos": "conj"}, "and"),
            ("vos", {"pos": "pron", "case": "nom", "number": "pl"}, "you"),
        ],
    }[kind]
    words = [
        {"id": f"w{i}", "form": lemma, "lemma": lemma, "morph": morph}
        for i, (lemma, morph, _) in enumerate(rows)
    ]
    layer = {
        "lang": "en",
        "segments": {"s01": {}},
        "words": {f"w{i}": {"gloss": text} for i, (_, _, text) in enumerate(rows)},
    }
    return {
        "id": "test.clause-junctions",
        "segments": [{"id": "s01", "words": words}],
    }, layer


def matches(doc, layer):
    return [
        e
        for e in english.check(doc, layer)
        if any(
            label in e for label in ("temporal glosses", "perception glosses", "additive glosses")
        )
    ]


@pytest.mark.parametrize("kind", ["temporal", "perception", "additive"])
def test_actual_dispatch(kind, monkeypatch):
    doc, layer = example(kind)
    assert len(matches(doc, layer)) == 1
    monkeypatch.setattr(english, "check_clause_junctions", lambda *_: [])
    assert matches(doc, layer) == []


@pytest.mark.parametrize("kind", ["temporal", "perception", "additive"])
@pytest.mark.parametrize("suffix", ["", ".", "…", "?!", " , "])
def test_unicode_spacing_case_and_terminal_punctuation(kind, suffix):
    doc, layer = example(kind)
    for word in layer["words"].values():
        text = word["gloss"].upper().replace(" ", "\u00a0\t")
        word["gloss"] = (
            " " + "".join(chr(ord(c) + 0xFEE0) if "A" <= c <= "Z" else c for c in text) + suffix
        )
    assert len(matches(doc, layer)) == 1


@pytest.mark.parametrize(
    "verb", ["see", "you see", "you have seen", "you will see", "you shall see"]
)
def test_each_supported_perception_predicate(verb):
    doc, layer = example("perception")
    layer["words"]["w0"]["gloss"] = verb
    assert len(matches(doc, layer)) == 1


@pytest.mark.parametrize(
    "kind,index,value",
    [
        ("temporal", 0, "when you"),
        ("temporal", 1, "you see"),
        ("temporal", 1, "you have seen"),
        ("temporal", 1, "you shall see"),
        ("perception", 2, "happen"),
        ("perception", 2, "happening"),
        ("perception", 0, "expect"),
        ("perception", 1, "this thing"),
        ("additive", 1, "also"),
        ("additive", 2, "you too"),
    ],
)
def test_correct_or_unexamined_phrases_are_not_rejected(kind, index, value):
    doc, layer = example(kind)
    layer["words"][f"w{index}"]["gloss"] = value
    assert matches(doc, layer) == []


@pytest.mark.parametrize(
    "kind,index,key,value",
    [
        ("temporal", 0, "lemma", "et"),
        ("temporal", 0, "pos", "prep"),
        ("temporal", 1, "lemma", "scio"),
        ("temporal", 1, "pos", "noun"),
        ("temporal", 1, "mood", "imp"),
        ("temporal", 1, "voice", "pass"),
        ("temporal", 1, "person", 3),
        ("temporal", 1, "number", "sg"),
        ("perception", 0, "lemma", "spero"),
        ("perception", 0, "pos", "noun"),
        ("perception", 0, "mood", "inf"),
        ("perception", 0, "voice", "pass"),
        ("perception", 1, "lemma", "is"),
        ("perception", 1, "pos", "noun"),
        ("perception", 1, "case", "nom"),
        ("perception", 1, "gender", "f"),
        ("perception", 1, "number", "sg"),
        ("perception", 2, "lemma", "ago"),
        ("perception", 2, "pos", "noun"),
        ("perception", 2, "mood", "ind"),
        ("perception", 2, "tense", "perf"),
        ("additive", 0, "lemma", "sic"),
        ("additive", 0, "pos", "noun"),
        ("additive", 1, "lemma", "autem"),
        ("additive", 1, "pos", "adv"),
        ("additive", 2, "lemma", "tu"),
        ("additive", 2, "pos", "noun"),
        ("additive", 2, "case", "acc"),
        ("additive", 2, "number", "sg"),
    ],
)
def test_each_latin_scope_restriction(kind, index, key, value):
    doc, layer = example(kind)
    word = doc["segments"][0]["words"][index]
    (word if key == "lemma" else word["morph"])[key] = value
    assert matches(doc, layer) == []


@pytest.mark.parametrize("kind", ["temporal", "perception", "additive"])
def test_every_internal_punctuation_and_segment_boundary(kind):
    baseline, layer = example(kind)
    words = baseline["segments"][0]["words"]
    for boundary in range(1, len(words)):
        for index, key in ((boundary - 1, "post"), (boundary, "pre")):
            doc = deepcopy(baseline)
            doc["segments"][0]["words"][index][key] = ";"
            assert matches(doc, layer) == []
        doc = deepcopy(baseline)
        doc["segments"] = [
            {"id": "s01", "words": words[:boundary]},
            {"id": "s02", "words": words[boundary:]},
        ]
        assert matches(doc, layer) == []


@pytest.mark.parametrize("kind", ["temporal", "perception", "additive"])
def test_missing_and_nonstring_providers(kind):
    doc, baseline = example(kind)
    for wid in baseline["words"]:
        for value in (None, 23, {}, []):
            layer = deepcopy(baseline)
            layer["words"][wid]["gloss"] = value
            assert english.check_clause_junctions(doc, layer) == []
        layer = deepcopy(baseline)
        layer["words"].pop(wid)
        assert matches(doc, layer) == []


@pytest.mark.parametrize("kind", ["temporal", "perception", "additive"])
def test_valid_shared_and_zero_providers_stop_direct_junctions(kind):
    doc, baseline = example(kind)
    assert interlinear.check(doc, baseline) == []
    ids = list(baseline["words"])
    for index, wid in enumerate(ids):
        for shared in (False, True):
            start = max(0, index - 1)
            members = ids[start : start + 2] if shared else [wid]
            alignment = (
                {"words": members, "anchor": members[0], "gloss": "a shared phrase"}
                if shared
                else {"words": members, "reason": "word-order"}
            )
            layer = deepcopy(baseline)
            layer["segments"]["s01"]["alignments"] = [alignment]
            for member in members:
                layer["words"][member].pop("gloss")
            assert interlinear.check(doc, layer) == []
            assert matches(doc, layer) == []
            # Intentionally invalid duplicate providers isolate the defensive
            # membership check from the absent direct gloss of a valid group.
            for member in members:
                layer["words"][member] = deepcopy(baseline["words"][member])
            assert interlinear.check(doc, layer)
            assert matches(doc, layer) == []
    # A real foreign segment has distinct IDs and valid providers; it must
    # not suppress the original clause's diagnostic.
    foreign_words = deepcopy(doc["segments"][0]["words"][:2])
    foreign_ids = ["foreign0", "foreign1"]
    for word, wid in zip(foreign_words, foreign_ids, strict=True):
        word["id"] = wid
    doc["segments"].append({"id": "s02", "words": foreign_words})
    layer = deepcopy(baseline)
    layer["words"].update({wid: {} for wid in foreign_ids})
    layer["segments"]["s02"] = {
        "alignments": [{"words": foreign_ids, "anchor": foreign_ids[0], "gloss": "another phrase"}]
    }
    assert interlinear.check(doc, layer) == []
    assert len(matches(doc, layer)) == 1


def test_main_clause_you_cannot_remove_the_subordinate_subject():
    doc, layer = example("temporal")
    words = doc["segments"][0]["words"]
    words.insert(
        0,
        {
            "id": "main",
            "form": "vos",
            "lemma": "vos",
            "morph": {"pos": "pron", "case": "nom", "number": "pl"},
        },
    )
    words.append(
        {
            "id": "imperative",
            "form": "scitote",
            "lemma": "scio",
            "morph": {"pos": "verb", "mood": "imp", "person": 2, "number": "pl"},
        }
    )
    layer["words"].update(main={"gloss": "you"}, imperative={"gloss": "know"})
    assert len(matches(doc, layer)) == 1
    layer["words"]["w1"]["gloss"] = "you see"
    assert english.check(doc, layer) == []


def test_empty_and_other_language():
    assert english.check_clause_junctions({}, {}) == []
    for kind in ("temporal", "perception", "additive"):
        doc, layer = example(kind)
        layer["lang"] = "pl"
        assert english.check(doc, layer) == []
        assert english.check_clause_junctions(doc, layer) == []
