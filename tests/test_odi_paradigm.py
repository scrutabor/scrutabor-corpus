"""The unnumbered odi paradigm and its attested contextual forms."""

import copy
import json
from pathlib import Path

import pytest

from checks.lexicon import check_paradigm, check_text_against_lexicon, load_lexicon

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = [
    (
        "texts/proprium/dominica-ii-post-epiphaniam-epistola.json",
        "w044",
        "Odiéntes",
        {
            "pos": "verb",
            "case": "nom",
            "number": "pl",
            "gender": "m",
            "tense": "pres",
            "voice": "act",
            "mood": "part",
        },
        "Nienawidzący",
        "Hate",
    ),
    (
        "texts/proprium/dominica-ii-post-pentecosten-epistola.json",
        "w005",
        "odit",
        {
            "pos": "verb",
            "mood": "ind",
            "number": "sg",
            "person": 3,
            "tense": "perf",
            "voice": "act",
        },
        "nienawidzi",
        "hates",
    ),
    (
        "texts/proprium/dominica-ii-post-pentecosten-epistola.json",
        "w028",
        "odit",
        {
            "pos": "verb",
            "mood": "ind",
            "number": "sg",
            "person": 3,
            "tense": "perf",
            "voice": "act",
        },
        "nienawidzi",
        "hates",
    ),
    (
        "texts/proprium/dominica-pentecostes-introitus.json",
        "w027",
        "odérunt",
        {
            "mood": "ind",
            "number": "pl",
            "person": 3,
            "pos": "verb",
            "tense": "perf",
            "voice": "act",
        },
        "nienawidzą",
        "hate",
    ),
    (
        "texts/proprium/dominica-xi-post-pentecosten-introitus.json",
        "w029",
        "odérunt",
        {
            "pos": "verb",
            "mood": "ind",
            "number": "pl",
            "person": 3,
            "tense": "perf",
            "voice": "act",
        },
        "nienawidzą",
        "hate",
    ),
    (
        "texts/proprium/dominica-xxiii-post-pentecosten-graduale.json",
        "w011",
        "odérunt",
        {
            "pos": "verb",
            "mood": "ind",
            "number": "pl",
            "person": 3,
            "tense": "perf",
            "voice": "act",
        },
        "nienawidzą",
        None,
    ),
    (
        "texts/proprium/nativitas-domini-in-die-epistola.json",
        "w133",
        "odísti",
        {
            "mood": "ind",
            "number": "sg",
            "person": 2,
            "pos": "verb",
            "tense": "perf",
            "voice": "act",
        },
        "znienawidziłeś",
        "have hated",
    ),
    (
        "texts/proprium/sanctae-annae-matris-beatae-mariae-virginis-graduale.json",
        "w004",
        "odísti",
        {
            "pos": "verb",
            "mood": "ind",
            "number": "sg",
            "person": 2,
            "tense": "perf",
            "voice": "act",
        },
        "znienawidziłaś",
        "have hated",
    ),
    (
        "texts/proprium/sanctae-annae-matris-beatae-mariae-virginis-tractus.json",
        "w040",
        "odísti",
        {
            "pos": "verb",
            "mood": "ind",
            "number": "sg",
            "person": 2,
            "tense": "perf",
            "voice": "act",
        },
        "znienawidziłaś",
        "have hated",
    ),
    (
        "texts/proprium/sancti-laurentii-martyris-evangelium.json",
        "w038",
        "odit",
        {
            "pos": "verb",
            "mood": "ind",
            "number": "sg",
            "person": 3,
            "tense": "perf",
            "voice": "act",
        },
        "ma w nienawiści",
        "hates",
    ),
    (
        "texts/proprium/sanctorum-simonis-et-iudae-apostolorum-evangelium.json",
        "w017",
        "odit",
        {
            "pos": "verb",
            "mood": "ind",
            "number": "sg",
            "person": 3,
            "tense": "perf",
            "voice": "act",
        },
        "nienawidzi",
        "hates",
    ),
    (
        "texts/proprium/sanctorum-simonis-et-iudae-apostolorum-evangelium.json",
        "w047",
        "odit",
        {
            "pos": "verb",
            "mood": "ind",
            "number": "sg",
            "person": 3,
            "tense": "perf",
            "voice": "act",
        },
        "nienawidzi",
        "hates",
    ),
    (
        "texts/proprium/sanctorum-simonis-et-iudae-apostolorum-evangelium.json",
        "w111",
        "odit",
        {
            "pos": "verb",
            "mood": "ind",
            "number": "sg",
            "person": 3,
            "tense": "perf",
            "voice": "act",
        },
        "nienawidzi",
        "hates",
    ),
    (
        "texts/proprium/sanctorum-simonis-et-iudae-apostolorum-evangelium.json",
        "w115",
        "odit",
        {
            "pos": "verb",
            "mood": "ind",
            "number": "sg",
            "person": 3,
            "tense": "perf",
            "voice": "act",
        },
        "nienawidzi",
        "hates",
    ),
    (
        "texts/proprium/sanctorum-simonis-et-iudae-apostolorum-evangelium.json",
        "w134",
        "odérunt",
        {
            "pos": "verb",
            "mood": "ind",
            "number": "pl",
            "person": 3,
            "tense": "perf",
            "voice": "act",
        },
        "znienawidzili",
        "have hated",
    ),
]
PL_NOTE = (
    "Czasownik ułomny. Formy perfectum często wyrażają stan teraźniejszy, "
    "np. odi: „nienawidzę”. W późniejszej łacinie występują też formy czasu teraźniejszego, "
    "w tym imiesłów odientes. Znaczenie czasowe konkretnej formy wynika z jej kontekstu."
)
EN_NOTE = (
    "A defective verb. Perfect forms often express a present state, as in odi, “I hate”. "
    "Later Latin also has present forms, including the participle odientes. "
    "The time reference of a particular form depends on its context."
)


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def probe(conj=None):
    morph = {
        "pos": "verb",
        "tense": "perf",
        "mood": "ind",
        "voice": "act",
        "number": "sg",
        "person": 3,
    }
    if conj is not None:
        morph["conj"] = conj
    return {
        "id": "probe.odi",
        "segments": [{"words": [{"id": "w001", "lemma": "odi", "form": "odit", "morph": morph}]}],
    }


def test_odi_card_preserves_attested_head_and_qualified_notes():
    neutral = read("lexicon/lemmata.json")
    entry = neutral["entries"]["odi"]
    assert entry == {
        "head": "odi, odísse, osus sum",
        "pos": "verb",
        "localization": {"note": True},
    }
    assert neutral["analysis_defaults"]["review"] == "pending"
    assert read("languages/pl/lexicon.json")["entries"]["odi"] == {
        "senses": ["nienawidzić"],
        "note": PL_NOTE,
    }
    assert read("languages/en/lexicon.json")["entries"]["odi"] == {
        "senses": ["to hate", "to dislike"],
        "note": EN_NOTE,
    }
    assert load_lexicon(ROOT)[2] == []


@pytest.mark.parametrize("path,wid,form,morph,pl,en", EXPECTED)
def test_odi_tokens_keep_complete_other_morphology_and_meaning(path, wid, form, morph, pl, en):
    doc = read(path)
    word = next(w for s in doc["segments"] for w in s.get("words", []) if w["id"] == wid)
    assert word["lemma"] == "odi"
    assert word["form"] == form
    assert word["morph"] == morph
    assert doc["editorial"]["words"][wid]["analysis"] == {
        "confidence": "high",
        "sources": ["editorial", "whitakers"],
        "review": "pending",
    }
    assert read("languages/pl/" + path)["words"][wid].get("gloss") == pl
    assert read("languages/en/" + path)["words"][wid].get("gloss") == en
    entries = read("lexicon/lemmata.json")["entries"]
    assert check_text_against_lexicon(doc, entries) == []


def test_odi_inventory_and_existing_group():
    found = []
    for path in sorted((ROOT / "texts").glob("*/*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for segment in doc["segments"]:
            for word in segment.get("words", []):
                if word["lemma"] == "odi":
                    found.append((str(path.relative_to(ROOT)), word["id"]))
    assert found == [(row[0], row[1]) for row in EXPECTED]
    layer = read("languages/en/texts/proprium/dominica-xxiii-post-pentecosten-graduale.json")
    group = next(g for g in layer["segments"]["s01"]["alignments"] if "w011" in g["words"])
    assert group == {"words": ["w010", "w011"], "anchor": "w011", "gloss": "hate us"}


@pytest.mark.parametrize("number", [1, 2, 3, 4])
def test_numbered_odi_lemma_is_rejected_even_when_token_agrees(number):
    entries = {"odi": {"head": "odi, odísse, osus sum", "pos": "verb", "conj": number}}
    assert any("no numbered conjugation" in e for e in check_paradigm(entries))
    assert any(
        "no numbered conjugation" in e for e in check_text_against_lexicon(probe(number), entries)
    )


@pytest.mark.parametrize("number", [1, 2, 3, 4])
def test_numbered_odi_token_is_rejected_against_correct_card(number):
    entries = {"odi": {"head": "odi, odísse, osus sum", "pos": "verb"}}
    assert check_paradigm(entries) == []
    assert check_text_against_lexicon(probe(), entries) == []
    assert any(
        "no numbered conjugation" in e for e in check_text_against_lexicon(probe(number), entries)
    )


def test_ordinary_third_conjugation_still_requires_its_number():
    entries = {"credo": {"head": "credo, crédere, crédidi, créditum", "pos": "verb", "conj": 3}}
    doc = probe(3)
    doc["segments"][0]["words"][0]["lemma"] = "credo"
    assert check_paradigm(entries) == []
    assert check_text_against_lexicon(doc, entries) == []
    missing = copy.deepcopy(entries)
    del missing["credo"]["conj"]
    assert any("no conjugation recorded" in e for e in check_paradigm(missing))
