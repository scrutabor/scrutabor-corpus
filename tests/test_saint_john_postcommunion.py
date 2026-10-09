"""The interwoven petition retains its referents and historical wording basis."""

import json
from pathlib import Path

import pytest

from checks.interlinear import check
from checks.translation_provenance import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
NAME = "sancti-ioannis-apostoli-et-evangelistae-postcommunio"
TEXT = f"proprium.{NAME}"


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def layer(language):
    return load(f"languages/{language}/texts/proprium/{NAME}.json")


@pytest.mark.parametrize("language", ["pl", "en"])
def test_every_latin_word_retains_exactly_one_realization(language):
    core = load(f"texts/proprium/{NAME}.json")
    data = layer(language)
    ids = [word["id"] for segment in core["segments"] for word in segment.get("words", [])]
    assert len(ids) == 41
    assert set(data["words"]) == set(ids)
    assert check(core, data) == []
    assert data["words"]["w010"]["gloss"] == {"pl": "abyśmy", "en": "that"}[language]
    assert data["segments"]["s02"] == {"translation": "Amen."}


def test_polish_relative_precedes_its_correlate_without_splitting_government():
    data = layer("pl")
    assert data["segments"]["s01"].get("alignments") == [
        {
            "words": ["w011", "w012", "w013", "w014"],
            "anchor": "w014",
            "gloss": "na czyją pamiątkę te dary",
        },
        {
            "words": ["w016", "w017", "w018", "w019"],
            "anchor": "w017",
            "gloss": "tego modlitwami byli także chronieni",
        },
    ]
    assert data["words"]["w015"] == {"gloss": "przyjęliśmy"}


def test_english_relative_and_prayer_possessor_are_explicitly_connected():
    data = layer("en")
    assert data["segments"]["s01"].get("alignments") == [
        {
            "words": ["w002", "w003", "w004"],
            "anchor": "w002",
            "gloss": "with heavenly food and drink",
        },
        {"words": ["w005", "w006"], "anchor": "w005", "gloss": "our God"},
        {
            "words": [f"w{number:03}" for number in range(11, 20)],
            "anchor": "w017",
            "gloss": "we may also be protected by the prayers of the one "
            "in whose commemoration we have received these gifts",
        },
        {"words": ["w021", "w022"], "anchor": "w021", "gloss": "our Lord"},
        {"words": ["w023", "w024"], "anchor": "w023", "gloss": "Jesus Christ"},
        {"words": ["w025", "w026"], "anchor": "w025", "gloss": "Your Son"},
        {
            "words": ["w027", "w028", "w029", "w030", "w031"],
            "anchor": "w029",
            "gloss": "who lives and reigns with You",
        },
        {"words": ["w034", "w035"], "anchor": "w034", "gloss": "of the Holy Spirit"},
        {"words": ["w037", "w038", "w039", "w040"], "anchor": "w039", "gloss": "forever and ever"},
    ]


def test_english_address_and_conclusion_have_one_contemporary_register():
    data = layer("en")
    expected = {"w007": "You", "w020": "Through", "w036": "God"}
    assert {word: data["words"][word]["gloss"] for word in expected} == expected
    alignments = data["segments"]["s01"]["alignments"]
    groups = {tuple(group["words"]): group["gloss"] for group in alignments}
    assert groups[("w025", "w026")] == "Your Son"
    assert groups[("w027", "w028", "w029", "w030", "w031")] == "who lives and reigns with You"
    assert groups[("w037", "w038", "w039", "w040")] == "forever and ever"
    assert data["segments"]["s01"]["translation"] == (
        "Refreshed with heavenly food and drink, we humbly implore You, our God, "
        "that we may also be protected by the prayers of the one in whose memory "
        "we have received these gifts. Through our Lord Jesus Christ, Your Son, "
        "who lives and reigns with You in the unity of the Holy Spirit, God, "
        "forever and ever."
    )


def test_revised_wording_names_separate_body_and_conclusion_pages():
    uses = [
        use
        for use in load("languages/en/bibliography.json")["uses"]
        if use["address"].get("text") == TEXT and use["role"] == "historical_wording_basis"
    ]
    assert len(uses) == 2
    assert {use["locator"]["printed"] for use in uses} == {"p. 72", "p. 29"}
    assert {use["locator"]["scan"] for use in uses} == {"PDF p. 99", "PDF p. 56"}
    for use in uses:
        assert use["address"] == {"kind": "segment", "text": TEXT, "segment": "s01"}
        assert use["edition"] == "edition.the-missal-for-the-use-of-the-laity-1853"
        assert use["digital_item"] == "item.missal-for-the-use-of-the-laity-1853.scan"
        assert use["decision"] == "RETAIN"
        assert "legacy_refs" not in use
    records = load("languages/en/translation-basis.json")["records"]
    assert [record for record in records if TEXT in record["texts"]] == [
        {"texts": [TEXT], "segments": ["s01"], "relationship": "revised"}
    ]


def test_historical_origin_does_not_claim_completed_translation_review():
    sites = load("languages/en/translation-provenance.json")["sites"]
    entry = next(site for site in sites if site["site"] == f"{TEXT}.s01.en")
    assert entry["origin"] == "public-domain"
    assert entry["review"] == "working"
    assert entry["target_sha256"] == canonical_hash(layer("en")["segments"]["s01"]["translation"])
