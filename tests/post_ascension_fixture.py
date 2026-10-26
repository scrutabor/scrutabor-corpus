"""Bounded current fields and historical inverses of the Ascension Sunday texts."""

import json
from copy import deepcopy
from pathlib import Path

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures/post-ascension-fields.json").read_text(encoding="utf-8")
)


def value_at(document, keys):
    value = document
    for key in keys:
        value = value[key]
    return value


def restore_layer(layer, relative):
    """Reverse only exact named current fields; preserve every other field."""
    result = deepcopy(layer)
    for field in FIXTURE["language_changes"][relative]:
        parent = value_at(result, field["keys"][:-1])
        key = field["keys"][-1]
        assert (key in parent) is field["after_present"], "current field presence"
        if field["after_present"]:
            assert parent[key] == field["after"], "current field value"
        if field["before_present"]:
            parent[key] = deepcopy(field["before"])
        else:
            parent.pop(key, None)
    return result


DEVOTED_COLLECT = "proprium.dominica-post-ascensionem-collecta"
DEVOTED_SOURCE_BEFORE = "b38a14752e77f8bb138f29901bb1c6d5bd3f3e6f47f7a8d8da100774041db71e"
DEVOTED_SOURCE_AFTER = "7fb22409b07c78940cf2fbef6503f6a2db004d50a3b41b30f1e81ff8f9fdfe25"
DEVOTED_WORD_BEFORE = {
    "id": "w009",
    "form": "devótam",
    "lemma": "devoveo",
    "morph": {
        "pos": "verb",
        "case": "acc",
        "gender": "f",
        "number": "sg",
        "tense": "perf",
        "voice": "pass",
        "mood": "part",
        "conj": 2,
    },
    "head": "w011",
}
DEVOTED_WORD_AFTER = {
    "id": "w009",
    "form": "devótam",
    "lemma": "devotus",
    "morph": {"pos": "adj", "case": "acc", "gender": "f", "number": "sg"},
    "head": "w011",
}


def historical_devoted_segments(core):
    """Reverse only the admitted adjective for a historical segment comparison."""
    result = deepcopy(core["segments"])
    if core["id"] != DEVOTED_COLLECT:
        return result
    word = next(w for s in result if s["id"] == "s01" for w in s["words"] if w["id"] == "w009")
    assert json.dumps(word, sort_keys=True) == json.dumps(DEVOTED_WORD_AFTER, sort_keys=True), (
        "current devoted Collect word"
    )
    word["lemma"] = DEVOTED_WORD_BEFORE["lemma"]
    word["morph"] = deepcopy(DEVOTED_WORD_BEFORE["morph"])
    return result


def expected_devoted_source_hash(text, segment, historical):
    """Advance a historical EXPECTED source hash, never an observation."""
    if (text, segment) != (DEVOTED_COLLECT, "s01"):
        return historical
    assert historical == DEVOTED_SOURCE_BEFORE, "historical devoted Collect source"
    return DEVOTED_SOURCE_AFTER


def expected_devoted_row(row, site=None):
    """Advance only an exact historical EXPECTED Collect row or projection."""
    result = deepcopy(row)
    identity = site if site is not None else row["site"]
    if identity not in {DEVOTED_COLLECT + ".s01.pl", DEVOTED_COLLECT + ".s01.en"}:
        return result
    expected = FIXTURE["verse_rows"][identity]["after"]
    assert json.dumps(result, sort_keys=True) == json.dumps(
        {key: expected[key] for key in result}, sort_keys=True
    ), "historical devoted Collect expected row"
    if "source_sha256" in result:
        result["source_sha256"] = expected_devoted_source_hash(
            DEVOTED_COLLECT, "s01", result["source_sha256"]
        )
    return result


def expected_row_successor(row, site=None):
    """Advance a historical expected row, never normalize an actual observation."""
    result = deepcopy(row)
    change = FIXTURE["verse_rows"].get(site if site is not None else row["site"])
    if change is not None:
        assert result == {key: change["before"][key] for key in result}, "historical expected row"
        result.update({key: change["after"][key] for key in result})
    return expected_devoted_row(result, site)
