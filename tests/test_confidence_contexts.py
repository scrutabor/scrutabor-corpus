"""Pinned confidence clauses and the two comparisons in the XIV Gradual.

These are specific contextual readings, not a general Polish-government or
translation-quality classifier. In particular, ufać + dative, ufać w +
accusative, absolute Ufaj, and historical hope constructions are not banned.
"""

import json
import unicodedata
from pathlib import Path

import pytest

from checks import interlinear
from checks.language_packs import check_layer

ROOT = Path(__file__).resolve().parents[1]
GRADUAL = "proprium.dominica-xiv-post-pentecosten-graduale"

# suffix, segment, word, form, mood, tense, number, person, focus span, PL, EN
CASES = [
    (
        "dedicatio-archibasilicae-sanctissimi-salvatoris-tractus",
        "s01",
        21,
        "confídunt",
        "ind",
        "pres",
        "pl",
        3,
        (20, 23),
        "Ci, którzy pokładają ufność w Panu",
        "Those who trust in the Lord",
    ),
    (
        "litaniae-maiores-collecta",
        "s01",
        13,
        "confídimus",
        "ind",
        "pres",
        "pl",
        1,
        (10, 13),
        "Twojej dobroci ufamy",
        # St Mark audit EN-12 (2026-10-20): word captions in Latin order, no clause group.
        "in Your compassion trust",
    ),
    (
        "dominica-i-adventus-introitus",
        "s01",
        10,
        "confído",
        "ind",
        "pres",
        "sg",
        1,
        (8, 10),
        "w Tobie pokładam ufność",
        "in You I trust",
    ),
    (
        "dominica-i-adventus-introitus",
        "s05",
        64,
        "confído",
        "ind",
        "pres",
        "sg",
        1,
        (62, 64),
        "w Tobie pokładam ufność",
        "in You I trust",
    ),
    (
        "dominica-i-adventus-offertorium",
        "s01",
        11,
        "confído",
        "ind",
        "pres",
        "sg",
        1,
        (9, 11),
        "w Tobie pokładam ufność",
        "in You I trust",
    ),
    (
        "dominica-ii-in-quadragesima-introitus",
        "s01",
        36,
        "confído",
        "ind",
        "pres",
        "sg",
        1,
        (34, 36),
        "w Tobie pokładam ufność",
        "in You I trust",
    ),
    (
        "dominica-ii-passionis-evangelium",
        "s82",
        1243,
        "confídit",
        "ind",
        "pres",
        "sg",
        3,
        (1243, 1245),
        "pokłada ufność w Bogu",
        "He trusts in God",
    ),
    (
        "dominica-iii-in-quadragesima-evangelium",
        "s01",
        136,
        "confidébat",
        "ind",
        "impf",
        "sg",
        3,
        (134, 136),
        "w której pokładał ufność",
        "in which he trusted",
    ),
    (
        "dominica-iii-in-quadragesima-introitus",
        "s01",
        35,
        "confído",
        "ind",
        "pres",
        "sg",
        1,
        (33, 35),
        "w Tobie pokładam ufność",
        "in You I trust",
    ),
    (
        "dominica-iii-post-pentecosten-introitus",
        "s01",
        37,
        "confído",
        "ind",
        "pres",
        "sg",
        1,
        (35, 37),
        "w Tobie pokładam ufność",
        "in You I trust",
    ),
    (
        "dominica-in-sexagesima-collecta",
        "s01",
        9,
        "confídimus",
        "ind",
        "pres",
        "pl",
        1,
        (5, 9),
        "w żadnym naszym uczynku nie pokładamy ufności",
        "we put no trust in any deed of our own",
    ),
    (
        "dominica-iv-in-quadragesima-tractus",
        "s01",
        2,
        "confídunt",
        "ind",
        "pres",
        "pl",
        3,
        (1, 4),
        "Ci, którzy pokładają ufność w Panu",
        "Those who trust in the Lord",
    ),
    (
        "dominica-pentecostes-sequentia",
        "s01",
        82,
        "confidéntibus",
        "part",
        "pres",
        "pl",
        None,
        (80, 82),
        "w Tobie pokładającym ufność",
        "trusting in You",
    ),
    (
        "dominica-vii-post-pentecosten-offertorium",
        "s01",
        28,
        "confidéntibus",
        "part",
        "pres",
        "pl",
        None,
        (28, 30),
        "dla pokładających ufność w Tobie",
        "for those trusting in You",
    ),
    (
        "dominica-x-post-pentecosten-evangelium",
        "s01",
        11,
        "confidébant",
        "ind",
        "impf",
        "pl",
        3,
        (9, 11),
        "w sobie pokładali ufność",
        "in themselves trusted",
    ),
    (
        "dominica-xiv-post-pentecosten-graduale",
        "s01",
        3,
        "confídere",
        "inf",
        "pres",
        None,
        None,
        (3, 5),
        "pokładać ufność w Panu",
        "to trust in the Lord",
    ),
    (
        "dominica-xiv-post-pentecosten-graduale",
        "s01",
        7,
        "confídere",
        "inf",
        "pres",
        None,
        None,
        (7, 9),
        "pokładać ufność w człowieku",
        "to trust in man",
    ),
    (
        "dominica-xviii-post-pentecosten-evangelium",
        "s01",
        29,
        "Confíde",
        "imp",
        "pres",
        "sg",
        2,
        (29, 30),
        "Ufaj synu",
        "Take courage son",
    ),
    (
        "dominica-xxii-post-pentecosten-epistola",
        "s01",
        2,
        "Confídimus",
        "ind",
        "pres",
        "pl",
        1,
        (2, 5),
        "Pokładamy ufność w Panu Jezusie",
        "We trust in the Lord Jesus",
    ),
    (
        "dominica-xxiii-post-pentecosten-evangelium",
        "s01",
        73,
        "Confíde",
        "imp",
        "pres",
        "sg",
        2,
        (73, 74),
        "Ufaj córko",
        "Take courage daughter",
    ),
    (
        "sanctae-annae-matris-beatae-mariae-virginis-epistola",
        "s01",
        12,
        "Confídit",
        "ind",
        "pres",
        "sg",
        3,
        (12, 14),
        "pokłada ufność w niej",
        "trusts in her",
    ),
    (
        "sancti-ioannis-apostoli-et-evangelistae-secreta",
        "s01",
        12,
        "confídimus",
        "ind",
        "pres",
        "pl",
        1,
        (10, 14),
        "dzięki którego opiece ufamy, że zostaniemy wyzwoleni",
        "by whose patronage we trust to be delivered",
    ),
    (
        "laudis-tibi-secreta",
        "s01",
        16,
        "confídimus",
        "ind",
        "pres",
        "pl",
        1,
        (12, 18),
        "jesteśmy uwalniani zarówno od obecnego zła jak i od przyszłego, jak ufamy",
        "are, we trust, freed from evils both present and future",
    ),
]
PRESERVED = [5, 9, 16, 18, 19, 20]


def text_id(case):
    return "proprium." + case[0]


def word_id(number):
    return f"w{number:03d}"


def read(text, language=None):
    relative = Path("texts") / (text.replace(".", "/", 1) + ".json")
    path = ROOT / relative if language is None else ROOT / "languages" / language / relative
    return json.loads(path.read_text(encoding="utf-8"))


def source_segment(doc, segment):
    return next(s for s in doc["segments"] if s["id"] == segment)


def realized(doc, layer, segment, first, last):
    """Exactly one realization per selected token; no clipped shared group."""
    assert interlinear.check(doc, layer) == []
    ids = {word_id(n) for n in range(first, last + 1)}
    groups = layer["segments"][segment].get("alignments", [])
    indexed = {wid: group for group in groups for wid in group["words"]}
    phrases = []
    words = source_segment(doc, segment)["words"]
    assert ids <= {word["id"] for word in words}
    for word in words:
        wid = word["id"]
        if wid not in ids:
            continue
        if wid in indexed:
            group = indexed[wid]
            assert set(group["words"]) <= ids
            assert group.get("gloss"), "A confidence predicate must be visibly realized"
            if wid == group["words"][0]:
                phrases.append(group["gloss"])
        else:
            phrases.append(layer["words"][wid]["gloss"])
    return " ".join(phrases)


def test_complete_confido_denominator():
    expected = {(text_id(c), c[1], word_id(c[2])) for c in CASES}
    assert len(expected) == 23 and len({c[0] for c in expected}) == 21
    forms = {
        unicodedata.normalize("NFD", c[3]).encode("ascii", "ignore").decode().lower() for c in CASES
    }
    actual = set()
    for path in (ROOT / "texts").glob("*/*.json"):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for segment in doc["segments"]:
            for word in segment.get("words", []):
                form = (
                    unicodedata.normalize("NFD", word["form"])
                    .encode("ascii", "ignore")
                    .decode()
                    .lower()
                )
                if word.get("lemma") == "confido" or form in forms:
                    actual.add((doc["id"], segment["id"], word["id"]))
    assert actual == expected


@pytest.mark.parametrize("case", CASES, ids=lambda c: f"{c[0]}:{c[1]}:{c[2]}")
def test_confido_analysis_retained(case):
    doc = read(text_id(case))
    word = next(w for w in source_segment(doc, case[1])["words"] if w["id"] == word_id(case[2]))
    assert word["lemma"] == "confido" and word["form"] == case[3]
    expected = {
        "pos": "verb",
        "conj": 3,
        "mood": case[4],
        "tense": case[5],
        "voice": "act",
    }
    if case[6] is not None:
        expected["number"] = case[6]
    if case[7] is not None:
        expected["person"] = case[7]
    if case[4] == "part":
        expected.update(case="dat", gender="m")
    assert word["morph"] == expected
    for prep in source_segment(doc, case[1])["words"]:
        if prep["id"] in {word_id(n) for n in range(case[8][0], case[8][1] + 1)} and prep[
            "lemma"
        ] in {"in", "ex"}:
            assert prep["morph"] == {"pos": "prep", "governs": "abl"}
            governed = next(
                w for w in source_segment(doc, case[1])["words"] if w["id"] == prep["head"]
            )
            assert governed["morph"]["case"] == "abl"


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("case", CASES, ids=lambda c: f"{c[0]}:{c[1]}:{c[2]}")
def test_confido_context_realization(case, language):
    doc, layer = read(text_id(case)), read(text_id(case), language)
    assert realized(doc, layer, case[1], *case[8]) == case[9 if language == "pl" else 10]


@pytest.mark.parametrize("index", PRESERVED)
def test_valid_polish_controls_preserved(index):
    case = CASES[index]
    doc, layer = read(text_id(case)), read(text_id(case), "pl")
    assert realized(doc, layer, case[1], *case[8]) == case[9]


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("first", [1, 10])
def test_gradual_comparative_predicate(language, first):
    doc, layer = read(GRADUAL), read(GRADUAL, language)
    word = next(w for w in doc["segments"][0]["words"] if w["id"] == word_id(first))
    assert word["form"] == "Bonum" and word["lemma"] == "bonus"
    assert word["morph"] == {"case": "nom", "gender": "n", "number": "sg", "pos": "adj"}
    copula = next(w for w in doc["segments"][0]["words"] if w["id"] == word_id(first + 1))
    assert copula["lemma"] == "sum" and copula["form"] == "est"
    assert copula["morph"] == {
        "mood": "ind",
        "number": "sg",
        "person": 3,
        "pos": "verb",
        "tense": "pres",
        "voice": "act",
    }
    assert realized(doc, layer, "s01", first, first + 1) == (
        "Lepiej jest" if language == "pl" else "It is better"
    )
    if language == "en":
        ids = [word_id(first), word_id(first + 1)]
        assert [
            g for g in layer["segments"]["s01"]["alignments"] if set(g["words"]) & set(ids)
        ] == [{"words": ids, "anchor": ids[1], "gloss": "It is better"}]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_complete_gradual_comparisons_and_retained_verse(language):
    doc, layer = read(GRADUAL), read(GRADUAL, language)
    assert [w["lemma"] for w in doc["segments"][0]["words"]] == [
        "bonus",
        "sum",
        "confido",
        "in",
        "dominus",
        "quam",
        "confido",
        "in",
        "homo",
        "bonus",
        "sum",
        "spero",
        "in",
        "dominus",
        "quam",
        "spero",
        "in",
        "princeps",
    ]
    expected = (
        "Lepiej jest pokładać ufność w Panu niż pokładać ufność w człowieku "
        "Lepiej jest pokładać nadzieję w Panu niż pokładać nadzieję w możnych"
        if language == "pl"
        else "It is better to trust in the Lord than to trust in man "
        "It is better to hope in the Lord than to hope in princes"
    )
    assert realized(doc, layer, "s01", 1, 18) == expected
    assert layer["segments"]["s01"]["translation"] == (
        "Lepiej ufać Panu, niż ufać człowiekowi. "
        "Lepiej pokładać nadzieję w Panu, niż pokładać nadzieję w książętach."
        if language == "pl"
        else "It is good to trust in the Lord, rather than to trust in man. "
        "It is good to hope in the Lord, rather than to hope in princes."
    )


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("number", [1, 10])
def test_gradual_positive_form_context_note(language, number):
    assert read(GRADUAL, language)["words"][word_id(number)]["note"] == (
        "„Bonum” ma formę stopnia równego, lecz w połączeniu z „quam” "
        "wyraża tu porównanie: „lepiej … niż …”."
        if language == "pl"
        else "“Bonum” is positive in form, but with “quam” it expresses a comparison here: "
        "“better … than …”."
    )


@pytest.mark.parametrize("number", [12, 16])
def test_gradual_polish_hope_register(number):
    """Pinned contemporary choice, not condemnation of every historical variant."""
    word = next(w for w in read(GRADUAL)["segments"][0]["words"] if w["id"] == word_id(number))
    assert word["lemma"] == "spero" and word["form"] == "speráre"
    assert word["morph"] == {
        "pos": "verb",
        "mood": "inf",
        "tense": "pres",
        "voice": "act",
        "conj": 1,
    }
    assert read(GRADUAL, "pl")["words"][word_id(number)]["gloss"] == "pokładać nadzieję"


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("identifier", sorted({text_id(case) for case in CASES} | {GRADUAL}))
def test_confidence_layers_match_their_core(identifier, language):
    doc, layer = read(identifier), read(identifier, language)
    category, name = identifier.split(".", 1)
    path = ROOT / "languages" / language / "texts" / category / f"{name}.json"
    assert check_layer(doc, layer, path) == []


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("number", [1, 10])
@pytest.mark.parametrize("side", ["core", "layer"])
def test_comparative_note_topology_rejects_one_sided_removal(language, number, side):
    doc, layer = read(GRADUAL), read(GRADUAL, language)
    assert doc["localization"]["notes"] == ["w001", "w010"]
    path = ROOT / "languages" / language / "texts/proprium" / f"{GRADUAL.split('.', 1)[1]}.json"
    assert check_layer(doc, layer, path) == []
    if side == "core":
        doc["localization"]["notes"].remove(word_id(number))
    else:
        del layer["words"][word_id(number)]["note"]
    errors = check_layer(doc, layer, path)
    assert len(errors) == 1
    assert "note topology differs" in errors[0] and word_id(number) in errors[0]
