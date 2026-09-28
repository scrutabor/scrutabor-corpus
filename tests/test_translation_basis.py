"""The grouped relationship registry covers every inherited translation once."""

import json
from pathlib import Path

import pytest

from build_reader import store
from checks.translation_basis import check, unbased, wording_bases

CORPUS = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize(
    ("text", "segment", "relationship"),
    [
        ("orationes.angelus-domini", "s02", "revised"),
        ("orationes.magnificat", "s01", "revised"),
        ("orationes.magnificat", "s02", "revised"),
        ("orationes.anima-christi", "s07", "revised"),
        ("ordinarium.deus-tu-conversus", "s09", "revised"),
        ("ordinarium.corpus-tuum", "s04", "revised"),
        ("proprium.dominica-iii-adventus-evangelium", "s02", "revised"),
        ("orationes.magnificat", "s10", "normalized"),
        ("orationes.angelus-domini", "s08", "normalized"),
        ("ordinarium.ecce-agnus-dei", "s02", "normalized"),
        ("ordinarium.per-ipsum", "s06", "normalized"),
        ("orationes.pater-noster", "s01", "normalized"),
    ],
)
def test_historical_wording_distinguishes_revision_from_spelling(
    text: str, segment: str, relationship: str
) -> None:
    # The source pages already print spoke, among and takes, but not the
    # modernized pronouns/constructions in the revised examples.
    assert store.translation_relationships(CORPUS, "en")[f"{text}.{segment}.en"] == relationship


@pytest.mark.parametrize(
    ("use_id", "printed", "scan"),
    [
        ("use.en.8837e83b38b72875de7e", "p. 12", "scan p. 39"),
        ("use.en.d847653074f03f178208", "pp. 38–39", "PDF pp. 50–51"),
    ],
)
def test_wording_locator_covers_the_complete_clause(use_id: str, printed: str, scan: str) -> None:
    graph = json.loads((CORPUS / "languages/en/bibliography.json").read_text())
    use = next(use for use in graph["uses"] if use["id"] == use_id)
    assert use["locator"]["printed"] == printed
    assert use["locator"]["scan"] == scan


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
