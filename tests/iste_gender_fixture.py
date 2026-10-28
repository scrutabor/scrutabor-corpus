"""Exact expected-side source successors and a comparison-copy gender inverse.

Historical fixtures remain unchanged. The inverse removes only the seven
declared fields from a copy; callers retain their whole historical assertions.
It is not a repair or a validator for an arbitrary current document.
"""

import json
from copy import deepcopy
from pathlib import Path

DATA = json.loads(
    (Path(__file__).parent / "fixtures/iste-gender-source-successors.json").read_text(
        encoding="utf-8"
    )
)


def before_iste_gender(core):
    result = deepcopy(core)
    cases = [row for row in DATA["genders"] if row["text"] == core["id"]]
    for case in cases:
        words = [
            word
            for segment in result["segments"]
            if segment["id"] == case["segment"]
            for word in segment.get("words", [])
            if word["id"] == case["word"]
        ]
        assert len(words) == 1, "current iste gender word identity"
        word = words[0]
        assert (word["form"], word["lemma"], word["morph"]) == (
            case["form"],
            case["lemma"],
            case["after_morph"],
        ), "current iste gender features"
        word["morph"] = deepcopy(case["before_morph"])
    return result


def current_iste_source_hash(text, segment, historical):
    cases = [row for row in DATA["sources"] if (row["text"], row["segment"]) == (text, segment)]
    if not cases:
        return historical
    assert len(cases) == 1 and historical == cases[0]["before"], "historical iste source hash"
    return cases[0]["after"]


def current_iste_expected_row(row):
    result = deepcopy(row)
    cases = [case for case in DATA["ledger_rows"] if case["before"]["site"] == row["site"]]
    if not cases:
        return result
    assert len(cases) == 1 and row == cases[0]["before"], "historical iste ledger row"
    return deepcopy(cases[0]["after"])
