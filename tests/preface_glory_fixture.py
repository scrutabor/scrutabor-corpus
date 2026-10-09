"""Exact inverse of the selected glory-scope clarification, not a normalizer."""

from copy import deepcopy

WORDS = ["w062", "w063", "w064"]
OLD_GLOSSES = {
    "pl": ["bez", "różnicy", "rozróżnienia"],
    "en": ["without", "difference", "of distinction"],
}
GROUP_GLOSSES = {
    "pl": "bez czynienia różnicy",
    "en": "without making any distinction",
}
NOTES = {
    "pl": "„Sine differentia discretionis” odnosi się do tego, co wyznajemy o chwale "
    "Ojca, Syna i Ducha Świętego: tę samą chwałę przypisujemy każdej z trzech Osób. "
    "Nie oznacza to zatarcia odrębności Osób. Następne zdanie wyraźnie ją potwierdza.",
    "en": "‘Sine differentia discretionis’ concerns what we profess about the glory "
    "of the Father, Son and Holy Spirit: the same glory belongs to all three Persons. "
    "It does not erase their personal distinctions, which the next sentence "
    "explicitly affirms.",
}
EN_BEFORE = (
    "For that which, by Your revelation, we believe of Your glory, the same we "
    "understand of Your Son and the same of the Holy Spirit, without difference "
    "arising from distinction."
)
EN_AFTER = (
    "For what we believe of Your glory through Your revelation, we understand "
    "likewise of Your Son and of the Holy Spirit, without making any distinction."
)
EN_TARGET = "ce6ff6e545de23c953dfdf86ce4352969a1626b39978fb5cb926ce4a6361a724"


def restore_glory_layer(layer, language):
    result = deepcopy(layer)
    segment = result["segments"]["s05"]
    assert list(segment) == ["translation", "alignments"]
    groups = segment.get("alignments", [])
    touching = [g for g in groups if set(g["words"]) & set(WORDS)]
    assert touching == [{"words": WORDS, "anchor": "w063", "gloss": GROUP_GLOSSES[language]}]
    assert list(touching[0]) == ["words", "anchor", "gloss"]
    assert groups[-1] is touching[0]
    for wid, old in zip(WORDS, OLD_GLOSSES[language], strict=True):
        expected = {"explanation": NOTES[language]} if wid == "w064" else {}
        assert result["words"][wid] == expected
        result["words"][wid] = {"gloss": old}
    groups.remove(touching[0])
    if language == "pl":
        assert not groups
        del segment["alignments"]
    else:
        assert segment["translation"] == EN_AFTER
        segment["translation"] = EN_BEFORE
    return result


def restore_glory_core(core):
    result = deepcopy(core)
    assert result["localization"] == {"about": True, "explanations": {"w064": {}}}
    assert list(result["localization"]) == ["about", "explanations"]
    del result["localization"]["explanations"]
    return result


def current_english_rows(previous):
    result = deepcopy(previous)
    row = next(r for r in result if r["segment"] == "s05")
    assert row["origin"] == "own" and row["review"] == "internally-reviewed"
    assert row["target_sha256"] == (
        "211bb5426c165670683385a1e09ad3236040ac51a015f0fe46951a3e8056ddfa"
    )
    row.update(origin="working-unsettled", review="working", target_sha256=EN_TARGET)
    return result
