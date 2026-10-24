"""Te Deum captions follow their own sentences and explain the active recast."""

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PL_WORDS = {
    "w028": "Święty",
    "w034": "Pełne",
    "w140": "I",
    "w164": "Racz",
    "w172": "Zmiłuj się",
    "w177": "Niech będzie",
    "w015": "aniołowie",
    "w044": "apostołów",
    "w047": "proroków",
    "w051": "męczenników",
}
PL_GROUPS = {
    "s18": "Wierzymy, że przyjdziesz jako Sędzia",
    "s21": "Spraw, byśmy w wiecznej chwale zostali zaliczeni do grona Twoich świętych",
    "s22": "Ocal",
}
PL_EXPLANATION = "Prosimy Boga, aby zaliczył nas do grona świętych w wiecznej chwale."
EN_GROUP = "We believe that You will come as judge"
EN_EXPLANATION = (
    "The Latin addresses Christ in a passive construction. The caption recasts it "
    "actively as the praying community’s confession: “We believe.”"
)
EN_QUOTATION = "The Cherubim and Seraphim continually take up the threefold “Holy.”"


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def layers():
    return {
        language: read(f"languages/{language}/texts/orationes/te-deum.json")
        for language in ("pl", "en")
    }


def assert_captions(layers):
    pl, en = layers["pl"], layers["en"]
    for word, expected in PL_WORDS.items():
        assert pl["words"][word]["gloss"] == expected, f"pl:words:{word}:gloss"
    for segment, expected in PL_GROUPS.items():
        assert pl["segments"][segment]["alignments"][0]["gloss"] == expected, (
            f"pl:segments:{segment}:gloss"
        )
    assert pl["words"]["w130"]["explanation"] == PL_EXPLANATION, "pl:words:w130:explanation"
    assert en["words"]["w015"]["gloss"] == "angels", "en:words:w015:gloss"
    assert en["words"]["w027"]["explanation"] == EN_QUOTATION, "en:words:w027:explanation"
    assert en["segments"]["s18"]["alignments"][0]["gloss"] == EN_GROUP, "en:segments:s18:gloss"
    assert en["words"]["w112"]["explanation"] == EN_EXPLANATION, "en:words:w112:explanation"


def test_contextual_case_and_paired_active_recast(layers):
    assert_captions(layers)
    pl = layers["pl"]
    # A later word in an acclamation or repeated plea is not a new sentence.
    assert pl["words"]["w029"]["gloss"] == "święty"
    assert pl["words"]["w030"]["gloss"] == "święty"
    assert pl["words"]["w175"]["gloss"] == "zmiłuj się"


CASES = (
    [("pl", "words", word, "gloss") for word in PL_WORDS]
    + [("pl", "segments", segment, "gloss") for segment in PL_GROUPS]
    + [("pl", "words", "w130", "explanation")]
    + [
        ("en", "words", "w015", "gloss"),
        ("en", "words", "w027", "explanation"),
        ("en", "segments", "s18", "gloss"),
        ("en", "words", "w112", "explanation"),
    ]
)


@pytest.mark.parametrize("language,section,identity,field", CASES)
def test_each_caption_or_explanation_regression_is_detected(
    layers, language, section, identity, field
):
    assert len(CASES) == len(set(CASES)) == 18, "mutation identity population"
    assert_captions(layers)
    changed = deepcopy(layers)
    target = changed[language][section][identity]
    if section == "segments":
        target = target["alignments"][0]
    target[field] = "Changed"
    expected_site = f"{language}:{section}:{identity}:{field}"
    with pytest.raises(AssertionError, match=re.escape(expected_site)):
        assert_captions(changed)
    assert_captions(layers)


def test_active_target_does_not_rewrite_the_latin_personal_passive(layers):
    core = read("texts/orationes/te-deum.json")
    (segment,) = [segment for segment in core["segments"] if segment["id"] == "s18"]
    ids = [word["id"] for word in segment["words"]]
    assert ids == ["w109", "w110", "w111", "w112"]
    verb = segment["words"][1]
    assert (verb["form"], verb["lemma"]) == ("créderis", "credo")
    assert verb["morph"] == {
        "pos": "verb",
        "person": 2,
        "number": "sg",
        "tense": "pres",
        "mood": "ind",
        "voice": "pass",
        "conj": 3,
    }
    for language in ("pl", "en"):
        (group,) = layers[language]["segments"]["s18"]["alignments"]
        assert group["words"] == ids and group["anchor"] == "w110"


def test_eternal_glory_and_causative_request_keep_their_crossing_dependencies(layers):
    core = read("texts/orationes/te-deum.json")
    (segment,) = [segment for segment in core["segments"] if segment["id"] == "s21"]
    words = {word["id"]: word for word in segment["words"]}
    assert words["w123"]["head"] == "w129"
    assert words["w124"]["form"] == "fac" and words["w124"]["morph"]["mood"] == "imp"
    assert words["w130"]["lemma"] == "numero"
    assert words["w130"]["morph"]["mood"] == "inf"
    assert words["w130"]["morph"]["voice"] == "pass"
    (group,) = layers["pl"]["segments"]["s21"]["alignments"]
    assert group["words"] == list(words) and group["anchor"] == "w124"
