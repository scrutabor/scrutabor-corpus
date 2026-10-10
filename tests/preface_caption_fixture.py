"""Reverse only the selected Trinity caption changes before older inverses."""

from copy import deepcopy

from preface_note_fixture import restore_note_layer

CAPTION_GROUPS = {
    "s02": [
        {
            "words": ["w002", "w003", "w004", "w005"],
            "anchor": "w005",
            "gloss": "it is right and just",
        },
    ],
    "s06": [
        {
            "words": ["w073", "w074", "w075"],
            "anchor": "w075",
            "gloss": "distinction in Persons",
        },
        {
            "words": ["w077", "w078", "w079"],
            "anchor": "w079",
            "gloss": "unity in essence",
        },
        {
            "words": ["w081", "w082", "w083", "w084"],
            "anchor": "w083",
            "gloss": "equality in majesty may be adored",
        },
    ],
}
OLD_EQUALITY = {
    "words": ["w083", "w084"],
    "anchor": "w083",
    "gloss": "equality may be adored",
}
DIRECT_BEFORE = {"w068": "confession", "w094": "who"}
DIRECT_AFTER = {"w068": "the confession", "w094": "and they"}
GROUP_WORDS_BEFORE = {
    "w002": "right",
    "w003": "and",
    "w004": "just",
    "w005": "it is",
    "w073": "in",
    "w074": "Persons",
    "w075": "distinction",
    "w077": "in",
    "w078": "essence",
    "w079": "unity",
    "w081": "in",
    "w082": "majesty",
}


def current_caption_site(site):
    """Keep old fixture constants; name only the selected larger current span."""
    result = deepcopy(site)
    if {k: v for k, v in site.items() if k != "segment"} == OLD_EQUALITY:
        assert site["segment"] == "s06"
        result.update(deepcopy(CAPTION_GROUPS["s06"][-1]))
    return result


def restore_caption_layer(layer, language):
    result = restore_note_layer(layer, language)
    if language == "pl":
        return result
    assert language == "en" and result["text"] == "ordinarium.praefatio-sanctissimae-trinitatis"
    assert list(result["segments"]) == [f"s{i:02}" for i in range(1, 8)]
    assert list(result["words"]) == [f"w{i:03}" for i in range(1, 102)]
    for sid in ["s02", "s06"]:
        segment = result["segments"][sid]
        assert list(segment) == ["translation", "alignments"]
        groups = segment["alignments"]
        expected = CAPTION_GROUPS[sid]
        positions = [0] if sid == "s02" else [2, 3, 4]
        assert len(groups) == (2 if sid == "s02" else 5)
        for position, selected in zip(positions, expected, strict=True):
            actual = groups[position]
            assert list(actual) == ["words", "anchor", "gloss"] and actual == selected
            for wid in actual["words"]:
                assert result["words"][wid] == {}
        if sid == "s02":
            del groups[0]
        else:
            groups[2:] = [deepcopy(OLD_EQUALITY)]
    for wid, target in GROUP_WORDS_BEFORE.items():
        result["words"][wid] = {"gloss": target}
    # The old two-word group still realizes these two empty records.
    assert result["words"]["w083"] == {} and result["words"]["w084"] == {}
    for wid, target in DIRECT_AFTER.items():
        assert result["words"][wid] == {"gloss": target}
        result["words"][wid] = {"gloss": DIRECT_BEFORE[wid]}
    return result
