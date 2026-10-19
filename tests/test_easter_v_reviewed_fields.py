"""Contextual wording and embedded doxology scope in the fifth Easter formulary."""

import json
from pathlib import Path

import pytest

from build_reader import bibliography, store

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "proprium.dominica-v-post-pascha-"
PARTS = (
    "introitus",
    "collecta",
    "epistola",
    "alleluia",
    "evangelium",
    "offertorium",
    "secreta",
    "communio",
    "postcommunio",
)
INTROIT = PREFIX + "introitus"

FIELDS = (
    pytest.param(
        "collecta",
        "w018",
        "gloss",
        "pod Twoim",
        id="collecta-w018-gloss",
    ),
    pytest.param(
        "collecta",
        "w029",
        "gloss",
        "który",
        id="collecta-w029-gloss",
    ),
    pytest.param(
        "epistola",
        "w025",
        "gloss",
        "naturalne",
        id="epistola-w025-gloss",
    ),
    pytest.param(
        "offertorium",
        "w019",
        "gloss",
        "pozwolił",
        id="offertorium-w019-gloss",
    ),
    pytest.param(
        "secreta",
        "w025",
        "gloss",
        "który",
        id="secreta-w025-gloss",
    ),
    pytest.param(
        "postcommunio",
        "w023",
        "gloss",
        "który",
        id="postcommunio-w023-gloss",
    ),
    pytest.param(
        "introitus",
        "w028",
        "explanation",
        (
            "„Laudi eius” jest w celowniku: dosłownie „Jego uwielbieniu”. Chodzi o "
            "to, by uwielbienie Boga wyrażało należną Mu chwałę."
        ),
        id="introitus-w028-explanation",
    ),
    pytest.param(
        "epistola",
        "w025",
        "explanation",
        ("Wyrażenie „vultum nativitatis suae” oznacza własną twarz, taką, jaką ma się z natury."),
        id="epistola-w025-explanation",
    ),
    pytest.param(
        "offertorium",
        "w027",
        "explanation",
        (
            "Jeden czasownik odnosi się tu do dwóch członów: Bóg nie odrzucił "
            "modlitwy i nie cofnął swojego miłosierdzia."
        ),
        id="offertorium-w027-explanation",
    ),
)
CLAUSES = (
    pytest.param(
        "pl",
        "collecta",
        "daj nam, którzy Cię błagamy",
        id="pl-collecta-01",
    ),
    pytest.param(
        "pl",
        "collecta",
        "pod Twoim kierownictwem to samo czynili",
        id="pl-collecta-02",
    ),
    pytest.param(
        "pl",
        "epistola",
        "swoją naturalną twarz",
        id="pl-epistola-03",
    ),
    pytest.param(
        "pl",
        "epistola",
        "polega na tym: odwiedzać sieroty i wdowy w ich utrapieniu",
        id="pl-epistola-04",
    ),
    pytest.param(
        "pl",
        "epistola",
        "zachowywać nieskalanym przez ten świat",
        id="pl-epistola-05",
    ),
    pytest.param(
        "pl",
        "evangelium",
        "lecz będę wam otwarcie mówił o Ojcu",
        id="pl-evangelium-06",
    ),
    pytest.param(
        "pl",
        "evangelium",
        "a nie mówię wam, że Ja poproszę Ojca za wami",
        id="pl-evangelium-07",
    ),
    pytest.param(
        "pl",
        "evangelium",
        "nie potrzebujesz, by ktoś Cię pytał",
        id="pl-evangelium-08",
    ),
    pytest.param(
        "pl",
        "offertorium",
        ("nie odrzucił mojego błagania ani nie oddalił ode mnie swojego miłosierdzia"),
        id="pl-offertorium-09",
    ),
    pytest.param(
        "en",
        "epistola",
        "immediately forgot what he was like",
        id="en-epistola-10",
    ),
    pytest.param(
        "en",
        "epistola",
        "becoming not a forgetful hearer but a doer of the work",
        id="en-epistola-11",
    ),
    pytest.param(
        "en",
        "evangelium",
        "but will tell you plainly about the Father",
        id="en-evangelium-12",
    ),
    pytest.param(
        "en",
        "evangelium",
        "I do not say to you that I will entreat the Father for you",
        id="en-evangelium-13",
    ),
    pytest.param(
        "en",
        "evangelium",
        "By this we believe that You came forth from God.",
        id="en-evangelium-14",
    ),
    pytest.param(
        "en",
        "communio",
        "proclaim His salvation as good news from day to day",
        id="en-communio-15",
    ),
    pytest.param(
        "en",
        "postcommunio",
        (
            "Grant, O Lord, that we who have been filled with the strength of the "
            "heavenly table may both desire what is right and receive what we desire."
        ),
        id="en-postcommunio-16",
    ),
    pytest.param(
        "en",
        "introitus",
        "make His praise glorious.",
        id="en-introitus-17",
    ),
    pytest.param(
        "en",
        "offertorium",
        "He has kept me alive and has not let my feet falter.",
        id="en-offertorium-18",
    ),
)
GROUPS = (
    pytest.param(
        "pl",
        "epistola",
        ["w036", "w037"],
        "w036",
        "zapomniał",
        id="pl-epistola-w036",
    ),
    pytest.param(
        "pl",
        "epistola",
        ["w069", "w070"],
        "w069",
        "za pobożnego",
        id="pl-epistola-w069",
    ),
    pytest.param(
        "pl",
        "evangelium",
        ["w040", "w041"],
        "w040",
        "mówiłem",
        id="pl-evangelium-w040",
    ),
    pytest.param(
        "pl",
        "evangelium",
        ["w114", "w115", "w116"],
        "w116",
        "nic nie mówisz w przenośni",
        id="pl-evangelium-w114",
    ),
    pytest.param(
        "pl",
        "evangelium",
        ["w124", "w125"],
        "w124",
        "potrzeba",
        id="pl-evangelium-w124",
    ),
    pytest.param(
        "pl",
        "evangelium",
        ["w131", "w132"],
        "w131",
        "dlatego",
        id="pl-evangelium-w131",
    ),
    pytest.param(
        "pl",
        "communio",
        ["w010", "w011"],
        "w011",
        "zwiastujcie",
        id="pl-communio-w010",
    ),
    pytest.param(
        "en",
        "introitus",
        ["w001", "w002", "w003"],
        "w003",
        "Proclaim the joyful news",
        id="en-introitus-w001",
    ),
    pytest.param(
        "en",
        "introitus",
        ["w026", "w027", "w028", "w029"],
        "w026",
        "make His praise glorious",
        id="en-introitus-w026",
    ),
    pytest.param(
        "en",
        "introitus",
        ["w050", "w051", "w052"],
        "w052",
        "Proclaim the joyful news",
        id="en-introitus-w050",
    ),
    pytest.param(
        "en",
        "epistola",
        ["w038", "w039"],
        "w039",
        "what he was like",
        id="en-epistola-w038",
    ),
    pytest.param(
        "en",
        "epistola",
        ["w051", "w052", "w053", "w054"],
        "w054",
        "having become not a forgetful hearer",
        id="en-epistola-w051",
    ),
    pytest.param(
        "en",
        "epistola",
        ["w079", "w080", "w081", "w082"],
        "w081",
        "this man’s religion is vain",
        id="en-epistola-w079",
    ),
    pytest.param(
        "en",
        "evangelium",
        ["w053", "w054", "w055", "w056", "w057"],
        "w056",
        "I will tell you plainly about the Father",
        id="en-evangelium-w053",
    ),
    pytest.param(
        "en",
        "evangelium",
        ["w066", "w067"],
        "w067",
        "I do not say",
        id="en-evangelium-w066",
    ),
    pytest.param(
        "en",
        "evangelium",
        ["w135", "w136", "w137"],
        "w137",
        "You came forth from God",
        id="en-evangelium-w135",
    ),
    pytest.param(
        "en",
        "communio",
        ["w010", "w011"],
        "w011",
        "proclaim as good news",
        id="en-communio-w010",
    ),
    pytest.param(
        "en",
        "postcommunio",
        ["w004", "w005", "w006", "w007"],
        "w007",
        "having been filled with the strength of the heavenly table",
        id="en-postcommunio-w004",
    ),
)
CARDS = (
    pytest.param(
        "pl",
        "prex",
        "derivatives",
        ["prekariat (przez francuskie précariat, częściowo od precarius)"],
        id="pl-prex-derivatives",
    ),
    pytest.param(
        "en",
        "rectus",
        "derivatives",
        ["rectitude", "correct (from rego)"],
        id="en-rectus-derivatives",
    ),
    pytest.param(
        "en",
        "fidelis",
        "note",
        "In the plural it can be used as a noun: fidéles, the faithful.",
        id="en-fidelis-note",
    ),
)
FORMULAS = {
    "pl": (
        "Chwała Ojcu i Synowi, i Duchowi Świętemu. Jak była na początku, teraz i "
        "zawsze, i na wieki wieków. Amen."
    ),
    "en": (
        "Glory be to the Father, and to the Son, and to the Holy Spirit. As it "
        "was in the beginning, is now, and ever shall be, world without end. "
        "Amen."
    ),
}
ANTIPHONS = {
    "pl": (
        "Głoście radosną wieść, niech ją usłyszą, alleluja; ogłaszajcie aż po "
        "kraniec ziemi: Pan wybawił swój lud, alleluja, alleluja."
    ),
    "en": (
        "Proclaim the joyful news, and let it be heard, alleluia; proclaim it to "
        "the end of the earth: the Lord has delivered His people, alleluia, "
        "alleluia."
    ),
}
CLAIMS = {
    "pl": (
        "Wyłącznie ciągły polski tekst doksologii odpowiadający w030–w049 opiera "
        "się na historycznym brzmieniu Gloria Patri. Zachowano słownictwo. "
        "Znormalizowano interpunkcję, wielką literę rozpoczynającą „Jak” oraz "
        "układ druku. Antyfona, werset psalmu, powtórzenie antyfony i glosy "
        "międzywierszowe nie są przypisane temu źródłu."
    ),
    "en": (
        "Only the continuous English wording corresponding to w030–w049 inherits "
        "the familiar Gloria Patri, with Holy Spirit for printed Holy Ghost. "
        "Printed speaker labels, line wrapping and the discretionary line-end "
        "hyphen are not carried into the continuous prose. The surrounding "
        "antiphon, psalm verse, reprise and individual interlinear captions are "
        "not attributed to this historical wording."
    ),
}
LATIN_GLORIA = [
    "Glória",
    "Patri",
    "et",
    "Fílio",
    "et",
    "Spirítui",
    "Sancto",
    "Sicut",
    "erat",
    "in",
    "princípio",
    "et",
    "nunc",
    "et",
    "semper",
    "et",
    "in",
    "sǽcula",
    "sæculórum",
    "Amen",
]


@pytest.fixture(scope="module")
def texts():
    return {
        part: (
            store.core(ROOT, PREFIX + part),
            {language: store.raw_layer(ROOT, language, PREFIX + part) for language in ("pl", "en")},
        )
        for part in PARTS
    }


@pytest.mark.parametrize(("part", "word", "field", "expected"), FIELDS)
def test_polish_contextual_word_field(texts, part, word, field, expected):
    assert texts[part][1]["pl"]["words"][word][field] == expected


@pytest.mark.parametrize(("language", "part", "clause"), CLAUSES)
def test_contextual_clause_in_complete_prose(texts, language, part, clause):
    assert texts[part][1][language]["segments"]["s01"]["translation"].count(clause) == 1


@pytest.mark.parametrize(("language", "part", "words", "anchor", "gloss"), GROUPS)
def test_contextual_group_keeps_members_anchor_and_caption(
    texts, language, part, words, anchor, gloss
):
    groups = texts[part][1][language]["segments"]["s01"].get("alignments", [])
    overlapping = [group for group in groups if set(group["words"]) & set(words)]
    assert overlapping == [{"words": words, "anchor": anchor, "gloss": gloss}]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_every_word_has_one_caption_realization(texts, language):
    total_words = total_segments = direct = groups = members = 0
    assert len(texts) == 9
    for part, (doc, layers) in texts.items():
        verses = [segment for segment in doc["segments"] if segment["type"] == "verse"]
        layer = layers[language]
        assert set(layer["segments"]) == {segment["id"] for segment in verses}
        assert set(layer["words"]) == {
            word["id"] for segment in verses for word in segment["words"]
        }
        for segment in verses:
            target = layer["segments"][segment["id"]]
            assert target["translation"].strip(), (language, part, segment["id"])
            realized = {}
            for group in target.get("alignments", []):
                assert group["gloss"].strip()
                assert group["anchor"] in group["words"]
                assert len(group["words"]) == len(set(group["words"]))
                assert set(group["words"]) <= {word["id"] for word in segment["words"]}
                groups += 1
                members += len(group["words"])
                for word_id in group["words"]:
                    assert word_id not in realized, (language, part, word_id)
                    assert not layer["words"][word_id].get("gloss"), (language, part, word_id)
                    realized[word_id] = group["anchor"]
            for word in segment["words"]:
                word_id = word["id"]
                if word_id not in realized:
                    assert layer["words"][word_id]["gloss"].strip(), (language, part, word_id)
                    direct += 1
                    realized[word_id] = word_id
            assert set(realized) == {word["id"] for word in segment["words"]}
            total_words += len(segment["words"])
            total_segments += 1
    assert (total_words, total_segments) == (509, 13)
    assert (direct, groups, members) == {"pl": (494, 7, 15), "en": (273, 89, 236)}[language]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_introit_reprises_antiphon_without_extending_doxology(texts, language):
    doc, layers = texts["introitus"]
    words = doc["segments"][0]["words"]
    assert [word["form"] for word in words[:17]] == [word["form"] for word in words[49:]]
    assert [word["id"] for word in words[29:49]] == [f"w{number:03}" for number in range(30, 50)]
    assert [word["form"] for word in words[29:49]] == LATIN_GLORIA
    translation = layers[language]["segments"]["s01"]["translation"]
    assert translation.count(ANTIPHONS[language]) == 2
    assert translation.startswith(ANTIPHONS[language])
    assert translation.count(FORMULAS[language]) == 1
    before, after = translation.split(FORMULAS[language])
    assert before.strip() != ANTIPHONS[language]
    assert after.strip() == ANTIPHONS[language]


@pytest.mark.parametrize(("language", "lemma", "field", "expected"), CARDS)
def test_shared_card_keeps_qualified_relation(language, lemma, field, expected):
    lexicon_path = ROOT / "languages" / language / "lexicon.json"
    lexicon = json.loads(lexicon_path.read_text(encoding="utf-8"))
    assert lexicon["entries"][lemma][field] == expected


@pytest.mark.parametrize("language", ["pl", "en"])
def test_historical_wording_basis_is_only_embedded_gloria(language):
    graph, packages = bibliography.load(ROOT)
    suffix = {"pl": "skowronek-1907", "en": "key-of-heaven-1901"}[language]
    use_id = f"use.{language}.{INTROIT}.gloria-{suffix}"
    matches = [use for use in packages[language]["uses"] if use["id"] == use_id]
    assert len(matches) == 1
    use = matches[0]
    assert use["role"] == "historical_wording_basis"
    assert use["address"] == {"kind": "word", "text": INTROIT, "word": "w030"}
    assert use["claim"] == CLAIMS[language]
    expected_edition = {
        "pl": "edition.ludwik-skowronek-droga-do-nieba-1907",
        "en": "edition.key-of-heaven-1901",
    }[language]
    assert use["edition"] == expected_edition
    evidence = bibliography.public_text_evidence(graph, packages[language])
    by_id = {record["id"]: record for record in evidence["texts"]}
    assert INTROIT in by_id
    assert "proprium.dominica-iv-post-pascha-introitus" in by_id
    entries = [entry for group in by_id[INTROIT]["source_groups"] for entry in group["entries"]]
    published = [entry for entry in entries if entry["id"] == use_id]
    assert len(published) == 1
    assert published[0]["address"] == {"kind": "word", "word": "w030"}
    assert published[0]["claim"] == CLAIMS[language]
    coverage = bibliography.evidence_coverage(ROOT, graph, packages)["languages"][language]
    assert coverage["normalized"] == {"pl": 74, "en": 212}[language]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_prayer_conclusions_keep_their_existing_segment_boundaries(texts, language):
    for part in ("collecta", "postcommunio"):
        assert texts[part][1][language]["segments"]["s02"]["translation"] == "Amen."
    secret = texts["secreta"][1][language]["segments"]
    assert secret["s01"]["translation"].endswith({"pl": "Bóg,", "en": "God,"}[language])
    ending = {"pl": "na wieki wieków.", "en": "forever and ever."}[language]
    assert secret["s02"]["translation"] == ending
    assert secret["s03"]["translation"] == "Amen."


def test_introit_literal_caption_preserves_accusative_and_dative(texts):
    doc, layers = texts["introitus"]
    words = {word["id"]: word for word in doc["segments"][0]["words"]}
    assert words["w027"]["morph"]["case"] == "acc"
    assert words["w028"]["morph"]["case"] == "dat"
    assert [layers["pl"]["words"][word]["gloss"] for word in ("w026", "w027", "w028", "w029")] == [
        "oddajcie",
        "chwałę",
        "uwielbieniu",
        "Jego",
    ]
    assert "oddajcie Mu chwałę, wysławiając Go" in layers["pl"]["segments"]["s01"]["translation"]
