"""Specific lexical senses and an embedded doxology retain their distinct scope."""

import json
from pathlib import Path

import pytest

from build_reader import bibliography, store
from checks import translation_provenance

ROOT = Path(__file__).resolve().parents[1]
INTROIT = "proprium.dominica-iv-post-pascha-introitus"

# None denotes an absent optional field, not a JSON null value.
CARD_FIELDS = (
    pytest.param(
        "pl",
        "efficio",
        "senses",
        ["czynić", "sprawiać", "stawać się (w stronie biernej)"],
        id="pl-efficio-senses",
    ),
    pytest.param(
        "pl",
        "video",
        "senses",
        ["widzieć", "ujrzeć", "wydawać się (w stronie biernej)", "ukazać się (w stronie biernej)"],
        id="pl-video-senses",
    ),
    pytest.param(
        "pl",
        "vir",
        "note",
        "Zwykle oznacza mężczyznę lub męża. W niektórych uogólnieniach odnosi się także "
        "do człowieka. Znaczenie ustala kontekst.",
        id="pl-vir-note",
    ),
    pytest.param("pl", "datum", "derivatives", ["data (od do)"], id="pl-datum-derivatives"),
    pytest.param(
        "pl", "dico", "derivatives", ["dykcja", "dyktando", "werdykt"], id="pl-dico-derivatives"
    ),
    pytest.param("pl", "frater", "derivatives", ["fraternizować się"], id="pl-frater-derivatives"),
    pytest.param("pl", "annuntio", "derivatives", None, id="pl-annuntio-derivatives"),
    pytest.param("pl", "cognosco", "derivatives", ["rekognicja"], id="pl-cognosco-derivatives"),
    pytest.param("pl", "interrogo", "derivatives", None, id="pl-interrogo-derivatives"),
    pytest.param("pl", "iudico", "derivatives", None, id="pl-iudico-derivatives"),
    pytest.param("pl", "summus", "derivatives", ["suma"], id="pl-summus-derivatives"),
    pytest.param(
        "en",
        "efficio",
        "senses",
        ["to make", "to become (in the passive)", "to bring about, accomplish"],
        id="en-efficio-senses",
    ),
    pytest.param(
        "en",
        "video",
        "senses",
        ["to see, behold", "to see to, take heed", "to seem, appear (in the passive)"],
        id="en-video-senses",
    ),
    pytest.param(
        "en",
        "vir",
        "note",
        "Vir usually means a man. In some contexts it refers more broadly to human beings. "
        "Homo is the general word for a human being.",
        id="en-vir-note",
    ),
    pytest.param(
        "en", "datum", "derivatives", ["data", "date (from do)"], id="en-datum-derivatives"
    ),
    pytest.param(
        "en", "dico", "derivatives", ["diction", "dictate", "verdict"], id="en-dico-derivatives"
    ),
    pytest.param(
        "en",
        "alleluia",
        "derivatives",
        ["hallelujah (from Hebrew hallelu-Yah)"],
        id="en-alleluia-derivatives",
    ),
)
GLORIA_USES = {
    "en": {
        "id": "use.en.proprium.dominica-iv-post-pascha-introitus.gloria-key-of-heaven-1901",
        "edition": "edition.key-of-heaven-1901",
        "digital_item": "item.key-of-heaven-1901.wikimedia-commons",
        "role": "historical_wording_basis",
        "address": {
            "kind": "word",
            "text": "proprium.dominica-iv-post-pascha-introitus",
            "word": "w028",
        },
        "claim": (
            "Only the continuous English wording corresponding to w028–w047 inherits the familiar "
            "Gloria Patri, with Holy Spirit for printed Holy Ghost. Printed speaker labels, "
            "line wrapping and the discretionary line-end hyphen are not carried into the "
            "continuous prose. The surrounding antiphon, psalm verse, reprise and individual "
            "interlinear captions are not attributed to this historical wording."
        ),
        "decision": "RETAIN_WITH_CORRECTION",
    },
    "pl": {
        "id": "use.pl.proprium.dominica-iv-post-pascha-introitus.gloria-skowronek-1907",
        "edition": "edition.ludwik-skowronek-droga-do-nieba-1907",
        "digital_item": "item.ludwik-skowronek-droga-do-nieba-1907.sbc",
        "role": "historical_wording_basis",
        "address": {
            "kind": "word",
            "text": "proprium.dominica-iv-post-pascha-introitus",
            "word": "w028",
        },
        "claim": (
            "Wyłącznie ciągły polski tekst doksologii odpowiadający w028–w047 opiera się na "
            "historycznym brzmieniu Gloria Patri. Zachowano słownictwo. "
            "Znormalizowano interpunkcję, wielką literę rozpoczynającą „Jak” oraz układ druku. "
            "Antyfona, werset psalmu, "
            "powtórzenie antyfony i glosy międzywierszowe nie są przypisane temu źródłu."
        ),
        "decision": "RETAIN_WITH_CORRECTION",
    },
}
FORMULAS = {
    "pl": (
        "Chwała Ojcu i Synowi, i Duchowi Świętemu. Jak była na początku, teraz i zawsze, "
        "i na wieki wieków. Amen."
    ),
    "en": (
        "Glory be to the Father, and to the Son, and to the Holy Spirit. "
        "As it was in the beginning, is now, and ever shall be, world without end. Amen."
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
def lexicons():
    return {
        language: json.loads((ROOT / "languages" / language / "lexicon.json").read_text())
        for language in ("pl", "en")
    }


@pytest.mark.parametrize(("language", "lemma", "field", "expected"), CARD_FIELDS)
def test_reviewed_card_field_keeps_its_specific_meaning(language, lemma, field, expected, lexicons):
    entry = lexicons[language]["entries"][lemma]
    if expected is None:
        assert field not in entry
    else:
        assert entry[field] == expected


@pytest.fixture(scope="module")
def embedded_gloria():
    graph, packages = bibliography.load(ROOT)
    recorded, errors = translation_provenance.load(ROOT)
    assert errors == []
    doc, layers = store.load(ROOT, INTROIT)
    return graph, packages, recorded, doc, layers, translation_provenance.corpus_sites(ROOT)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_embedded_gloria_has_only_its_word_scoped_wording_basis(language, embedded_gloria):
    graph, packages, recorded, doc, layers, current = embedded_gloria
    expected = GLORIA_USES[language]
    matches = [use for use in packages[language]["uses"] if use["id"] == expected["id"]]
    assert len(matches) == 1
    use = matches[0]
    assert {key: use[key] for key in expected} == expected
    assert use["address"] == {"kind": "word", "text": INTROIT, "word": "w028"}

    words = [word for segment in doc["segments"] for word in segment.get("words", [])]
    span = words[27:47]
    assert [word["id"] for word in span] == [f"w{number:03}" for number in range(28, 48)]
    assert [word["form"] for word in span] == LATIN_GLORIA
    target = layers[language]["segments"]["s01"]["translation"]
    assert target.count(FORMULAS[language]) == 1
    before, after = target.split(FORMULAS[language])
    assert before.strip() and after.strip()

    site = f"{INTROIT}.s01.{language}"
    assert recorded[site]["origin"] == "working-unsettled"
    assert recorded[site]["familiar_core"] is (language == "pl")
    assert translation_provenance.protected(INTROIT, language, "s01") is (language == "pl")
    assert current[site]["has_wording_citations"] is False
    assert recorded[site]["target_sha256"] == translation_provenance.canonical_hash(target)
    assert recorded[site]["source_sha256"] == current[site]["source_sha256"]

    evidence = bibliography.public_text_evidence(graph, packages[language])
    record = next(row for row in evidence["texts"] if row["id"] == INTROIT)
    published = [
        entry
        for group in record["source_groups"]
        for entry in group["entries"]
        if entry["id"] == expected["id"]
    ]
    assert len(published) == 1
    assert published[0]["address"] == {"kind": "word", "word": "w028"}
    assert published[0]["claim"] == expected["claim"]
