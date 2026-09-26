"""The grouped relationship registry covers every inherited translation once."""

from pathlib import Path

from checks.translation_basis import check, unbased, wording_bases

CORPUS = Path(__file__).resolve().parent.parent


def test_translation_basis_is_complete_and_nonoverlapping() -> None:
    errors, tally = check(CORPUS)
    assert errors == []
    assert sum(tally.values()) > 1000
    assert tally["traditional-composite"] > 0


def test_printed_wording_needs_a_basis_use_not_a_comparator() -> None:
    uses = [
        {
            "role": "historical_wording_basis",
            "decision": "RETAIN",
            "address": {"kind": "segment", "text": "t.a", "segment": "s01"},
        },
        {
            "role": "historical_wording_comparator",
            "decision": "RETAIN_WITH_CORRECTION",
            "address": {"kind": "segment", "text": "t.a", "segment": "s02"},
        },
        {
            "role": "historical_wording_basis",
            "decision": "REMOVE",
            "address": {"kind": "segment", "text": "t.a", "segment": "s03"},
        },
        {
            "role": "historical_wording_basis",
            "decision": "RETAIN",
            "address": {"kind": "text", "text": "t.b"},
        },
    ]
    expanded = {
        "t.a.s01.en": "exact",
        "t.a.s02.en": "normalized",
        "t.a.s03.en": "exact",
        "t.a.s04.en": "revised",
        "t.b.s01.en": "normalized",
    }
    assert unbased(expanded, *wording_bases(uses, "en")) == ["t.a.s02.en", "t.a.s03.en"]
