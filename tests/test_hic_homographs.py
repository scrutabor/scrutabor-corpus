"""Keep the demonstrative and the adverb of place separate in reader help."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_neutral_cards_do_not_merge_demonstrative_and_adverb():
    cards = json.loads((ROOT / "lexicon/lemmata.json").read_text())["entries"]
    assert cards["hic"]["pos"] == "pron"
    assert "adv" not in cards["hic"].get("pos_alt", [])
    assert cards["hic_adverbium"]["pos"] == "adv"


@pytest.mark.parametrize(
    "language,pronoun,adverb", [("pl", "ten", "tutaj"), ("en", "this", "here")]
)
def test_localized_senses_follow_the_correct_homograph(language, pronoun, adverb):
    cards = json.loads((ROOT / "languages" / language / "lexicon.json").read_text())["entries"]
    assert pronoun in cards["hic"]["senses"]
    assert adverb not in cards["hic"]["senses"]
    assert adverb in cards["hic_adverbium"]["senses"]


def test_each_occurrence_uses_its_part_of_speech_key():
    seen = {"hic": 0, "hic_adverbium": 0}
    expected = {"hic": "pron", "hic_adverbium": "adv"}
    for path in (ROOT / "texts").glob("*/*.json"):
        doc = json.loads(path.read_text())
        for segment in doc["segments"]:
            for word in segment.get("words", []):
                if word["lemma"] in expected:
                    assert word["morph"]["pos"] == expected[word["lemma"]], (doc["id"], word["id"])
                    seen[word["lemma"]] += 1
    assert all(seen.values())
