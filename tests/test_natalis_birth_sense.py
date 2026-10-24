"""Keep the natal adjective's birth sense available in dictionary resources."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.emit import lexicon_slice

ROOT = Path(__file__).resolve().parent.parent
EXPECTED = {"senses": ["narodziny", "urodziny", "dotyczący narodzin"]}


def require_natalis_birth_sense(entry):
    assert entry == EXPECTED, "retain noun senses and the explicit birth-related adjective"


def test_authored_natalis_has_explicit_birth_related_polish_sense():
    pl = json.loads((ROOT / "languages/pl/lexicon.json").read_text(encoding="utf-8"))
    require_natalis_birth_sense(pl["entries"]["natalis"])


def test_dictionary_slice_keeps_birth_sense_without_changing_lemma_identity():
    pl = lexicon_slice(ROOT, "pl", {"natalis"})
    require_natalis_birth_sense(pl["natalis"])
    neutral = lexicon_slice(ROOT, None, {"natalis"})
    assert neutral["natalis"] == {"head": "natális, -e", "pos": "adj"}
    en = lexicon_slice(ROOT, "en", {"natalis"})
    assert en["natalis"] == {"senses": ["natal, of birth"]}


@pytest.mark.parametrize(
    "senses",
    [
        ["narodziny", "urodziny", "rodzinny"],
        ["narodziny", "urodziny"],
        ["rodzinny"],
        ["dotyczący narodzin"],
    ],
    ids=["ambiguous-adjective", "noun-only", "family-only", "noun-senses-erased"],
)
def test_birth_sense_regression_rejects_mutant_and_recovers(senses):
    entry = deepcopy(EXPECTED)
    entry["senses"] = senses
    with pytest.raises(AssertionError, match="explicit birth-related adjective"):
        require_natalis_birth_sense(entry)
    entry["senses"] = deepcopy(EXPECTED["senses"])
    require_natalis_birth_sense(entry)
