"""Easter prose keeps source details and shared liturgical formulas."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from checks.translation_provenance import canonical_hash, source_payload

CORPUS = Path(__file__).resolve().parents[1]
PREFIX = "proprium.dominica-resurrectionis-"
TEXTS = [
    PREFIX + part
    for part in (
        "introitus",
        "collecta",
        "epistola",
        "graduale",
        "alleluia",
        "sequentia",
        "evangelium",
        "offertorium",
        "communio",
    )
] + ["ordinarium.praefatio-paschalis-in-die"]


def document(text, language=None):
    directory = CORPUS if language is None else CORPUS / "languages" / language
    return json.loads((directory / "texts" / (text.replace(".", "/") + ".json")).read_text())


def body(text, language):
    return document(text, language)["segments"]["s01"]["translation"]


def assert_morning(text):
    assert "very early in the morning" in text


def test_english_gospel_keeps_explicit_morning():
    text = body(PREFIX + "evangelium", "en")
    assert_morning(text)
    assert "the sun already risen" in text
    with pytest.raises(AssertionError):
        assert_morning(text.replace(" in the morning", ""))


@pytest.mark.parametrize("language", ["pl", "en"])
def test_introit_keeps_whole_doxology_and_exact_antiphon_reprise(language):
    gloria = document("orationes.gloria-patri", language)
    fixed = " ".join(gloria["segments"][s]["translation"] for s in ("s01", "s02"))
    text = body(PREFIX + "introitus", language)
    assert text.count(fixed) == 1
    before, reprise = text.split(fixed)
    reprise = reprise.strip()
    assert before.startswith(reprise + " ")
    assert before[len(reprise) :].strip()


@pytest.mark.parametrize(
    "language,night,day", [("pl", "tej nocy", "tego dnia"), ("en", "this night", "this day")]
)
def test_easter_preface_reuses_shared_body(language, night, day):
    night_body = body("ordinarium.praefatio-paschalis-in-nocte", language)
    day_body = body("ordinarium.praefatio-paschalis-in-die", language)
    assert night_body.count(night) == 1
    assert day_body == night_body.replace(night, day)


def test_english_preface_reuses_its_opening_caption():
    ids = [f"w{i:03d}" for i in range(1, 6)]
    groups = []
    for variant in ("nocte", "die"):
        layer = document("ordinarium.praefatio-paschalis-in-" + variant, "en")
        group = next(g for g in layer["segments"]["s01"]["alignments"] if g["words"] == ids)
        assert not any("gloss" in layer["words"][w] for w in ids)
        groups.append(group)
    assert groups[0] == groups[1]


def test_collect_help_caption_keeps_the_reflexive_lowercase():
    layer = document(PREFIX + "collecta", "pl")
    assert layer["words"]["w020"]["gloss"] == "swą pomocą"


def assert_binding(record, segment, translation):
    assert record["source_sha256"] == canonical_hash(source_payload(segment))
    assert record["target_sha256"] == canonical_hash(translation)


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("text", TEXTS)
def test_easter_prose_provenance_binds_current_words(language, text):
    core, layer = document(text), document(text, language)
    ledger = json.loads(
        (CORPUS / "languages" / language / "translation-provenance.json").read_text()
    )
    for segment in core["segments"]:
        translation = layer["segments"].get(segment["id"], {}).get("translation")
        if translation is None:
            continue
        record = next(
            r for r in ledger["sites"] if r["text"] == text and r["segment"] == segment["id"]
        )
        assert_binding(record, segment, translation)
        for field in ("source_sha256", "target_sha256"):
            stale = deepcopy(record)
            stale[field] = "0" * 64
            with pytest.raises(AssertionError):
                assert_binding(stale, segment, translation)


@pytest.mark.parametrize(
    "language,incipit,divinity",
    [("en", "Through the same ", "who, as God,"), ("pl", "Przez tegoż ", "Bóg,")],
)
def test_paschal_collects_reuse_the_same_conclusion(language, incipit, divinity):
    night = body("proprium.vigilia-paschalis-collecta", language)
    day = body(PREFIX + "collecta", language)
    conclusion = night[night.index(incipit) :]
    assert day.endswith(conclusion)
    assert divinity in conclusion


@pytest.mark.parametrize("part", ["graduale", "introitus"])
def test_advent_reflexive_at_a_target_sentence_start_retains_its_capital(part):
    layer = document("proprium.dominica-i-adventus-" + part, "pl")
    assert layer["segments"]["s02"]["translation"].startswith("Swoje drogi, Panie,")
