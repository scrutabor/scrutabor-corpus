"""Interlinear lines that once broke as composed sequences stay readable.

Each case names one reviewed realization and, where one exists, a supported
alternative; neither is a rule for other occurrences of the same Latin words.
"""

from copy import deepcopy

import pytest

from build_reader import store
from checks.interlinear import check
from checks.layout import CORPUS

P = "proprium."
GROUPS = [
    # text, language, segment, first, last, anchor, captions
    (P + "sanctissimi-nominis-iesu-secreta", "en", "s01", 7, 8, 7, ("creature lives",)),
    (
        P + "sanctissimi-nominis-iesu-secreta",
        "en",
        "s01",
        29,
        30,
        29,
        ("it may please", "it may be pleasing"),
    ),
    (
        P + "sanctissimi-nominis-iesu-epistola",
        "en",
        "s01",
        75,
        80,
        76,
        ("salvation is not in any other",),
    ),
    (
        P + "dominica-ii-adventus-collecta",
        "en",
        "s01",
        7,
        9,
        9,
        ("the ways of Your Only-begotten",),
    ),
    (
        P + "dominica-ii-adventus-collecta",
        "en",
        "s01",
        14,
        18,
        18,
        (
            "we may be found worthy to serve You with purified minds",
            "we may deserve to serve You with purified minds",
        ),
    ),
    (P + "dominica-i-adventus-introitus", "en", "s01", 21, 22, 22, ("wait for You",)),
    (P + "dominica-i-adventus-introitus", "en", "s05", 75, 76, 76, ("wait for You",)),
    (P + "dominica-i-adventus-offertorium", "en", "s01", 22, 23, 23, ("wait for You",)),
    (P + "dominica-i-adventus-graduale", "en", "s01", 3, 4, 4, ("wait for You",)),
    (
        P + "dominica-ii-adventus-epistola",
        "en",
        "s01",
        5,
        9,
        8,
        ("was written for our instruction",),
    ),
    (P + "dominica-ii-adventus-epistola", "en", "s06", 100, 101, 101, ("all you Gentiles",)),
    (P + "dominica-iii-adventus-evangelium", "en", "s01", 4, 5, 4, ("the Jews sent",)),
    (
        P + "dominica-iii-adventus-secreta",
        "en",
        "s01",
        16,
        21,
        21,
        ("may wondrously work Your salvation in us",),
    ),
    (
        P + "dominica-iv-adventus-evangelium",
        "en",
        "s01",
        6,
        8,
        6,
        ("when Pontius Pilate was governing", "while Pontius Pilate was governing"),
    ),
    (P + "dominica-iv-adventus-evangelium", "en", "s01", 14, 15, 14, ("and Philip",)),
    (P + "dominica-iv-adventus-evangelium", "en", "s02", 94, 96, 94, ("all flesh will see",)),
    (P + "sancti-andreae-apostoli-alleluia", "en", "s01", 3, 5, 3, ("The Lord loved Andrew",)),
    ("ordinarium.praefatio-apostolorum", "en", "s03", 18, 19, 19, ("You would not forsake",)),
    (
        P + "dominica-i-adventus-collecta",
        "pl",
        "s01",
        14,
        16,
        15,
        ("pod Twoją ochroną zasłużyli",),
    ),
    (
        P + "dominica-ii-adventus-collecta",
        "pl",
        "s01",
        7,
        9,
        9,
        ("dróg Jednorodzonego Twojego",),
    ),
    (
        P + "dominica-i-adventus-evangelium",
        "en",
        "s06",
        104,
        107,
        105,
        ("this generation will not pass away",),
    ),
    (P + "sanctissimi-nominis-iesu-introitus", "en", "s01", 19, 21, 21, ("is in the glory",)),
    (P + "sanctissimi-nominis-iesu-introitus", "en", "s01", 73, 75, 75, ("is in the glory",)),
    (P + "sanctissimi-nominis-iesu-alleluia", "en", "s01", 5, 7, 5, ("my mouth will speak",)),
    (P + "sanctissimi-nominis-iesu-alleluia", "en", "s01", 9, 11, 9, ("let all flesh bless",)),
    (P + "dominica-ii-adventus-introitus", "en", "s01", 10, 12, 11, ("the Lord will make heard",)),
    (P + "dominica-iv-adventus-epistola", "en", "s01", 4, 5, 4, ("let a man account",)),
    (P + "dominica-iv-adventus-evangelium", "en", "s02", 84, 85, 84, ("the crooked will become",)),
    (P + "dominica-iv-adventus-communio", "en", "s01", 8, 10, 8, ("His name will be called",)),
    (
        P + "sancti-andreae-apostoli-postcommunio",
        "pl",
        "s01",
        5,
        8,
        8,
        ("uroczystością świętego Andrzeja Apostoła",),
    ),
]
DIRECT = [
    # Large groups replaced by single glosses that compose (smallest sufficient realization).
    (
        P + "sanctissimi-nominis-iesu-collecta",
        "pl",
        {
            "w017": "czyje",
            "w018": "święte",
            "w019": "imię",
            "w020": "czcimy",
            "w021": "na",
            "w022": "ziemi",
            "w023": "Tego",
            "w024": "także",
            "w025": "oglądaniem",
            "w026": "cieszyli się",
        },
    ),
    (
        P + "sanctissimi-nominis-iesu-postcommunio",
        "en",
        {
            "w017": "which",
            "w018": "in",
            "w019": "honor",
            "w020": "of the name",
            "w025": "Jesus",
            "w026": "Christ",
            "w029": "we have offered",
        },
    ),
    (
        "ordinarium.praefatio-apostolorum",
        "en",
        {
            "w028": "that",
            "w029": "by the same",
            "w030": "rulers",
            "w031": "it may be governed",
            "w032": "whom",
            "w036": "over it",
            "w037": "You appointed",
            "w038": "to preside",
            "w039": "as shepherds",
        },
    ),
]
LINES = {
    # The owner's two spot-check lines, composed as the reader shows them.
    (P + "sanctissimi-nominis-iesu-secreta", "en", "s01"): (
        "by which",
        "every",
        "creature lives",
        "may sanctify",
    ),
    (P + "dominica-ii-adventus-collecta", "en", "s01"): (
        "His",
        "coming",
        "we may be found worthy to serve You with purified minds",
    ),
}


def ids(first, last):
    return [f"w{i:03d}" for i in range(first, last + 1)]


def group_for(layer, segment, first):
    return next(
        (
            g
            for g in layer["segments"][segment].get("alignments", [])
            if f"w{first:03d}" in g["words"]
        ),
        None,
    )


def assert_group(layer, case):
    _, _, segment, first, last, anchor, captions = case
    group = group_for(layer, segment, first)
    assert group is not None
    assert group["words"] == ids(first, last) and group["anchor"] == f"w{anchor:03d}"
    assert group["gloss"] in captions
    assert all("gloss" not in layer["words"][w] for w in ids(first, last))


def composed(core, layer, segment):
    words = next(s["words"] for s in core["segments"] if s["id"] == segment)
    groups = {g["words"][0]: g for g in layer["segments"][segment].get("alignments", [])}
    out, i = [], 0
    while i < len(words):
        group = groups.get(words[i]["id"])
        if group:
            if group.get("gloss"):
                out.append(group["gloss"])
            i += len(group["words"])
        else:
            out.append(layer["words"][words[i]["id"]].get("gloss"))
            i += 1
    return out


@pytest.mark.parametrize("case", GROUPS)
def test_reviewed_line_group(case):
    core, layers = store.load(CORPUS, case[0])
    layer = layers[case[1]]
    assert check(core, layer) == []
    assert_group(layer, case)


@pytest.mark.parametrize("case", GROUPS)
def test_supported_alternatives_and_regressions(case):
    _, layers = store.load(CORPUS, case[0])
    for caption in case[-1]:
        candidate = deepcopy(layers[case[1]])
        group_for(candidate, case[2], case[3])["gloss"] = caption
        assert_group(candidate, case)
    broken = deepcopy(layers[case[1]])
    group = group_for(broken, case[2], case[3])
    broken["segments"][case[2]]["alignments"].remove(group)
    for word in group["words"]:
        broken["words"][word]["gloss"] = "x"
    with pytest.raises(AssertionError):
        assert_group(broken, case)


@pytest.mark.parametrize("text,language,glosses", DIRECT)
def test_single_glosses_compose(text, language, glosses):
    core, layers = store.load(CORPUS, text)
    layer = layers[language]
    assert check(core, layer) == []
    assert {w: layer["words"][w].get("gloss") for w in glosses} == glosses


@pytest.mark.parametrize("key,window", sorted(LINES.items()))
def test_spot_checked_lines_read_in_order(key, window):
    text, language, segment = key
    core, layers = store.load(CORPUS, text)
    line = composed(core, layers[language], segment)
    start = line.index(window[0])
    assert tuple(line[start : start + len(window)]) == window
