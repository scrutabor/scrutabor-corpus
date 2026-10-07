"""Purification Introit, Gradual, Alleluia and Offertory: contextual readings and sources."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import bibliography, store
from build_reader.bibliography_bindings import collation_subject, witness_subject
from checks import english, interlinear, polish
from checks.raw_binding import resolve_binding
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
DAY = "proprium.purificatio-beatae-mariae-virginis-"
GRADUAL, ALLELUIA, OFFERTORY = DAY + "graduale", DAY + "alleluia", DAY + "offertorium"
INTROIT = "proprium.dominica-viii-post-pentecosten-introitus"
SHARED = {
    "pl": [
        "Przyjęliśmy",
        "Boże",
        "miłosierdzie",
        "Twoje",
        "w",
        "środku",
        "świątyni",
        "Twojej",
        "według",
        "imienia",
        "Twego",
        "Boże",
        "tak",
        "i",
        "chwała",
        "Twoja",
        "aż po",
        "krańce",
        "ziemi",
    ],
    "en": [
        "We have received",
        "God",
        "mercy",
        "Your",
        "in",
        "the midst",
        "of temple",
        "Your",
        "according to",
        "name",
        "Your",
        "God",
        "so",
        "also",
        "praise",
        "Your",
        "to",
        "the ends",
        "of the earth",
    ],
}
LINES = {
    (GRADUAL, "pl"): SHARED["pl"]
    + [
        "Jak",
        "słyszeliśmy",
        "tak",
        "i",
        "ujrzeliśmy",
        "w",
        "mieście",
        "Boga",
        "naszego",
        "na",
        "górze",
        "świętej",
        "Jego",
    ],
    (GRADUAL, "en"): SHARED["en"]
    + [
        "As",
        "we have heard",
        "so",
        "also",
        "we have seen",
        "in",
        "the city",
        "of God",
        "our",
        "on",
        "the mountain",
        "holy",
        "His",
    ],
    (ALLELUIA, "pl"): [
        "Alleluja",
        "alleluja",
        "Starzec",
        "Dziecię",
        "niósł",
        "Dziecię",
        "zaś",
        "starcem",
        "rządziło",
        "Alleluja",
    ],
    (ALLELUIA, "en"): [
        "Alleluia",
        "alleluia",
        "The old man",
        "was carrying the Child",
        "the Child",
        "however",
        "was ruling the old man",
        "Alleluia",
    ],
    (OFFERTORY, "pl"): [
        "Rozlana",
        "została",
        "łaska",
        "na",
        "wargach",
        "twoich",
        "dlatego",
        "pobłogosławił",
        "ciebie",
        "Bóg",
        "na",
        "wieki",
        "i",
        "na",
        "wieki",
        "wieków",
    ],
    (OFFERTORY, "en"): [
        "Poured out",
        "has been",
        "grace",
        "upon",
        "lips",
        "your",
        "therefore",
        "God has blessed you",
        "for",
        "ever",
        "and",
        "for",
        "ever",
        "and ever",
    ],
}
INTROIT_ANTIPHON = {
    "pl": SHARED["pl"] + ["sprawiedliwości", "pełna", "jest", "prawica", "Twoja"],
    "en": SHARED["en"] + ["of justice", "full", "is", "right hand", "Your"],
}
INTROIT_VERSE = {
    "pl": [
        "Wielki",
        "Pan",
        "i",
        "godny chwały",
        "bardzo",
        "w",
        "mieście",
        "Boga",
        "naszego",
        "na",
        "górze",
        "świętej",
        "Jego",
    ],
    "en": [
        "Great",
        "the Lord",
        "and",
        "praiseworthy",
        "exceedingly",
        "in",
        "the city",
        "of God",
        "our",
        "on",
        "the mountain",
        "holy",
        "His",
    ],
}
# Only agency is regrouped; Latin-order possessives and adjectives stay direct.
GROUPS = {
    GRADUAL: [],
    ALLELUIA: [
        ([4, 5], 5, "was carrying the Child"),
        ([8, 9], 9, "was ruling the old man"),
    ],
    OFFERTORY: [([8, 9, 10], 8, "God has blessed you")],
    INTROIT: [([43, 44], 43, "to the Holy Spirit")],
}


def wid(n):
    return f"w{n:03}"


def line(doc, layer, words=None):
    """The target sequence a reader sees: one entry per direct gloss or group anchor."""
    groups = [g for s in layer["segments"].values() for g in s.get("alignments", [])]
    membership = {w: g for g in groups for w in g["words"]}
    words = words or [w["id"] for s in doc["segments"] for w in s.get("words", [])]
    out = []
    for w in words:
        group = membership.get(w)
        if group is None or group.get("anchor") == w:
            out.append(interlinear.effective_gloss(layer, w))
    return out


@pytest.mark.parametrize("text,language", sorted(LINES))
def test_selected_complete_line(text, language):
    doc, layers = store.load(ROOT, text)
    assert not interlinear.check(doc, layers[language])
    assert line(doc, layers[language]) == LINES[(text, language)]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_introit_repeats_the_gradual_sentence_identically(language):
    doc, layers = store.load(ROOT, INTROIT)
    layer = layers[language]
    assert not interlinear.check(doc, layer)
    antiphon = [wid(n) for n in range(1, 25)]
    repeat = [wid(n) for n in range(58, 82)]
    verse = [wid(n) for n in range(25, 38)]
    assert line(doc, layer, antiphon) == INTROIT_ANTIPHON[language]
    assert line(doc, layer, repeat) == INTROIT_ANTIPHON[language]
    assert line(doc, layer, verse) == INTROIT_VERSE[language]
    gradual_doc, gradual_layers = store.load(ROOT, GRADUAL)
    shared = [wid(n) for n in range(1, 20)]
    assert line(doc, layer, shared) == line(gradual_doc, gradual_layers[language], shared)


@pytest.mark.parametrize("text", sorted(GROUPS))
def test_selected_minimal_english_groups(text):
    _, layers = store.load(ROOT, text)
    layer = layers["en"]
    groups = [g for s in layer["segments"].values() for g in s.get("alignments", [])]
    assert groups == [
        {"words": [wid(n) for n in numbers], "anchor": wid(anchor), "gloss": gloss}
        for numbers, anchor, gloss in GROUPS[text]
    ]
    assert all("gloss" not in layer["words"].get(w, {}) for g in groups for w in g["words"])


@pytest.mark.parametrize("text", [GRADUAL, ALLELUIA, OFFERTORY, INTROIT])
def test_polish_has_no_group_or_zero_and_english_no_zero(text):
    _, layers = store.load(ROOT, text)
    assert not [g for s in layers["pl"]["segments"].values() for g in s.get("alignments", [])]
    assert not [
        g
        for s in layers["en"]["segments"].values()
        for g in s.get("alignments", [])
        if "reason" in g
    ]


def test_retained_latin_analyses():
    for text in (GRADUAL, INTROIT):
        words = {w["id"]: w for w in store.core(ROOT, text)["segments"][0]["words"]}
        assert words["w001"]["morph"]["tense"] == "perf"
        assert (words["w002"]["morph"]["case"], words["w012"]["morph"]["case"]) == ("voc", "voc")
        assert words["w009"]["morph"] == {"governs": "acc", "pos": "prep"}
        assert words["w018"]["morph"]["case"] == "acc" and words["w018"]["morph"]["number"] == "pl"
    gradual = {w["id"]: w for w in store.core(ROOT, GRADUAL)["segments"][0]["words"]}
    assert gradual["w024"]["morph"]["tense"] == "perf"
    assert gradual["w032"]["morph"]["case"] == "gen"
    alleluia = {w["id"]: w for w in store.core(ROOT, ALLELUIA)["segments"][0]["words"]}
    assert (alleluia["w003"]["morph"]["case"], alleluia["w004"]["morph"]["case"]) == ("nom", "acc")
    assert (alleluia["w006"]["morph"]["case"], alleluia["w008"]["morph"]["case"]) == ("nom", "acc")
    assert alleluia["w005"]["morph"]["tense"] == alleluia["w009"]["morph"]["tense"] == "impf"
    offertory = {w["id"]: w for w in store.core(ROOT, OFFERTORY)["segments"][0]["words"]}
    assert (offertory["w009"]["morph"]["case"], offertory["w010"]["morph"]["case"]) == (
        "acc",
        "nom",
    )
    introit = {w["id"]: w for w in store.core(ROOT, INTROIT)["segments"][0]["words"]}
    assert introit["w020"]["morph"]["case"] == introit["w077"]["morph"]["case"] == "abl"
    assert introit["w021"]["head"] == "w023" and introit["w078"]["head"] == "w080"


@pytest.mark.parametrize(
    "text,language,prefix",
    [
        (GRADUAL, "pl", "Graduał formularza"),
        (GRADUAL, "en", "The Gradual of"),
        (ALLELUIA, "pl", "Alleluja formularza"),
        (ALLELUIA, "en", "The Alleluia of"),
        (OFFERTORY, "pl", "Offertorium formularza"),
        (OFFERTORY, "en", "The Offertory of"),
        (INTROIT, "pl", "Introit formularza"),
        (INTROIT, "en", "The Introit of"),
    ],
)
def test_localized_about(text, language, prefix):
    assert store.raw_layer(ROOT, language, text)["about"].startswith(prefix)


def test_identical_polish_prose_and_current_provenance():
    gradual = store.raw_layer(ROOT, "pl", GRADUAL)["segments"]["s01"]["translation"]
    introit = store.raw_layer(ROOT, "pl", INTROIT)["segments"]["s01"]["translation"]
    shared = (
        "Przyjęliśmy, Boże, Twoje miłosierdzie pośrodku Twojej świątyni; "
        "jak Twoje imię, Boże, tak i Twoja chwała – aż po krańce ziemi"
    )
    assert gradual.startswith(shared + ".") and introit.startswith(shared + ";")
    data = json.loads((ROOT / "languages/pl/translation-provenance.json").read_text())
    site = next(s for s in data["sites"] if s["site"] == GRADUAL + ".s01.pl")
    assert (site["origin"], site["review"]) == ("working-unsettled", "working")
    assert site["target_sha256"] == canonical_hash(gradual)
    core = store.core(ROOT, GRADUAL)
    assert site["source_sha256"] == canonical_hash(source_payload(core["segments"][0]))


@pytest.mark.parametrize(
    "text,binding,evidence,reading,references,words,first,last",
    [
        (
            GRADUAL,
            "purification-gradual",
            [
                {
                    "archive": "purification-day",
                    "first": 175,
                    "last": 176,
                    "section": "Graduale",
                    "section_line": 173,
                }
            ],
            [{"archive": "purification-day", "first": 175, "last": 176}],
            [],
            32,
            "Suscépimus,",
            "ejus.",
        ),
        (
            ALLELUIA,
            "purification-alleluia",
            [
                {
                    "archive": "purification-day",
                    "first": 177,
                    "last": 178,
                    "section": "Graduale",
                    "section_line": 173,
                }
            ],
            [{"archive": "purification-day", "first": 177, "last": 178}],
            [],
            10,
            "Allelúja,",
            "Allelúja.",
        ),
        (
            INTROIT,
            "pentecost-viii-introit",
            [
                {
                    "archive": "pentecost-viii",
                    "first": 13,
                    "last": 19,
                    "section": "Introitus",
                    "section_line": 13,
                },
                {
                    "archive": "prayers",
                    "first": 12,
                    "last": 14,
                    "section": "Gloria",
                    "section_line": 12,
                },
            ],
            [
                {"archive": "pentecost-viii", "first": 15, "last": 15},
                {"archive": "pentecost-viii", "first": 17, "last": 17},
                {"archive": "prayers", "first": 13, "last": 14},
                {"archive": "pentecost-viii", "first": 19, "last": 19},
            ],
            [{"archive": "pentecost-viii", "line": 18, "text": "&Gloria", "target": 1}],
            81,
            "Suscépimus,",
            "tua.",
        ),
    ],
)
def test_exact_raw_plans(text, binding, evidence, reading, references, words, first, last):
    bound = resolve_binding(ROOT / "witnesses" / text / "do.txt", ROOT)
    assert bound is not None and bound.source["binding_id"] == binding
    plan = bound.source["binding"]
    assert (plan["evidence"], plan["reading"], plan["references"]) == (
        evidence,
        reading,
        references,
    )
    tokens = bound.text.split()
    assert len(tokens) == words and (tokens[0], tokens[-1]) == (first, last)
    assert "V." not in bound.text and "&Gloria" not in bound.text


def test_offertory_commune_chain_is_not_falsely_bound():
    # The digital Offertory reaches Commune/C6-1 through C6b's whole-file
    # inheritance, which the raw-binding contract cannot express yet.
    assert resolve_binding(ROOT / "witnesses" / OFFERTORY / "do.txt", ROOT) is None
    graph, _ = bibliography.load(ROOT)
    do = next(
        w for w in graph["witnesses"] if w["text"] == OFFERTORY and w["transcription"] == "do"
    )
    assert "source_dependencies" not in do and do["review"] == {"status": "pending"}


@pytest.mark.parametrize("text", [GRADUAL, ALLELUIA, INTROIT])
def test_pending_witness_and_collation_dependencies(text):
    graph, _ = bibliography.load(ROOT)
    core = store.core(ROOT, text)
    witnesses = [w for w in graph["witnesses"] if w["text"] == text]
    collations = [c for c in graph["collations"] if c["text"] == text]
    assert len(witnesses) == 2 and len(collations) == 1
    subjects = {}
    for witness in witnesses:
        assert witness["review"] == {"status": "pending"}
        assert witness["source_dependencies"]["uses"] == []
        assert (witness["source_dependencies"]["raw_binding"] is None) == (
            witness["transcription"] == "mr"
        )
        subjects[witness["id"]] = witness_subject(ROOT, witness, graph, core)
    assert collations[0]["review"] == {"status": "pending"}
    assert (
        collation_subject(ROOT, collations[0], core, subjects)["contract"] == "collation-review-2"
    )


@pytest.mark.parametrize("text", [GRADUAL, ALLELUIA, OFFERTORY, INTROIT])
def test_printed_identity_is_benziger_and_current_conformity(text):
    graph, _ = bibliography.load(ROOT)
    mr = next(u for u in graph["uses"] if u["id"] == f"use.{text}.mr1962")
    assert mr["role"] == "direct_approved_print"
    assert "Benziger Brothers 1962 Editio iuxta typicam" in mr["claim"]
    assert "not original transcription genesis" in mr["claim"]
    header = (ROOT / "witnesses" / text / "mr.txt").read_text()
    assert "editio iuxta typicam" in header and "typical edition" not in header
    assert "local-archive:" not in header
    assert "typical edition" not in (ROOT / "witnesses" / text / "do.txt").read_text()
    core = store.core(ROOT, text)["editorial"]
    assert (
        "typical edition" not in core["notes"] and "typical-edition" not in core["source"]["method"]
    )
    collation = next(c for c in graph["collations"] if c["text"] == text)
    assert "typical-edition" not in collation["recension"]


def test_introit_declares_its_expanded_doxology():
    header = (ROOT / "witnesses" / INTROIT / "mr.txt").read_text()
    assert "only the cues Glória Patri and Suscépimus" in header
    assert "declared shared-formula expansion" in header
    words = [w["form"] for w in store.core(ROOT, INTROIT)["segments"][0]["words"]]
    doxology = (
        "Glória Patri, et Fílio, et Spirítui Sancto. "
        "Sicut erat in princípio, et nunc, et semper, et in sǽcula sæculórum. Amen."
    )
    assert words[37:57] == doxology.replace(",", "").replace(".", "").split()


@pytest.mark.parametrize(
    "text,expected",
    [
        (GRADUAL, [("w032", "eius.", "ejus.", "orthography")]),
        (
            ALLELUIA,
            [
                ("w001", "Allelúia,", "Allelúja,", "orthography"),
                ("w002", "allelúia.", "allelúja.", "orthography"),
                ("w004", "púerum", "Púerum", "capitalization"),
                ("w006", "puer", "Puer", "capitalization"),
                ("w010", "Allelúia.", "Allelúja.", "orthography"),
            ],
        ),
        (OFFERTORY, []),
        (
            INTROIT,
            [
                ("w020", "iustítia", "justítia", "orthography"),
                ("w037", "eius.", "ejus.", "orthography"),
                ("w077", "iustítia", "justítia", "orthography"),
            ],
        ),
    ],
)
def test_exact_apparatus(text, expected):
    apparatus = json.loads((ROOT / "witnesses" / text / "apparatus.json").read_text())
    actual = [
        (e["at"], e["ours"], e["witnesses"]["do"], e["class"]) for e in apparatus["adjudicated"]
    ]
    assert actual == expected
    assert all(
        "Benziger Brothers 1962 Editio iuxta typicam" in e["ruling"]
        for e in apparatus["adjudicated"]
    )
    assert "recorded below" not in apparatus["note"]


def _mutate(layer, text, mode):
    segment = layer["segments"]["s01"]
    groups = segment.setdefault("alignments", [])
    if mode == "split-agency":  # restore Latin-order English for portábat / regébat
        segment["alignments"] = [g for g in groups if g["anchor"] not in ("w005", "w009")]
        for w, g in {
            "w004": "the Child",
            "w005": "was carrying",
            "w006": "the Child",
            "w007": "but",
            "w008": "the old man",
            "w009": "was ruling",
        }.items():
            layer["words"][w]["gloss"] = g
    elif mode == "vocative-god":
        segment["alignments"] = [g for g in groups if g["anchor"] != "w008"]
        for w, g in {"w008": "has blessed", "w009": "you", "w010": "God"}.items():
            layer["words"][w]["gloss"] = g
    elif mode == "archaic-possessive":
        layer["words"]["w004"]["gloss"] = "Thy"
    elif mode == "silent-also":
        layer["words"]["w023"].pop("gloss")
        groups.append({"words": ["w023"], "reason": "idiom"})
        groups.sort(key=lambda g: g["words"][0])
    elif mode == "colon-capital":
        layer["words"]["w009"]["gloss"] = "According to" if text != "pl" else "Według"
    elif mode == "instrumental-fullness":
        layer["words"]["w020"]["gloss"] = "sprawiedliwością"
    return layer


@pytest.mark.parametrize(
    "text,language,mode",
    [
        (ALLELUIA, "en", "split-agency"),
        (OFFERTORY, "en", "vocative-god"),
        (GRADUAL, "en", "archaic-possessive"),
        (GRADUAL, "en", "silent-also"),
        (GRADUAL, "pl", "colon-capital"),
        (INTROIT, "pl", "instrumental-fullness"),
    ],
)
def test_escaped_classes_pass_generic_checks_but_not_context(text, language, mode):
    """Each restored defect is accepted by the generic validators — the reason
    this file pins the contextual reading — and rejected by the line test."""
    doc, layers = store.load(ROOT, text)
    layer = _mutate(deepcopy(layers[language]), language, mode)
    assert not interlinear.check(doc, layer)
    checker = english if language == "en" else polish
    assert not checker.check(doc, layer)
    expected = LINES.get((text, language)) or INTROIT_ANTIPHON[language]
    words = [wid(n) for n in range(1, 25)] if text == INTROIT else None
    assert line(doc, layer, words) != expected


@pytest.mark.parametrize(
    "text,language,changes",
    [
        (ALLELUIA, "en", {"w005": "carried the Child", "w009": "ruled the old man"}),
        (ALLELUIA, "en", {"w009": "was guiding the old man"}),
        (GRADUAL, "en", {"w014": "too", "w023": "too"}),
        (GRADUAL, "pl", {"w023": "też"}),
        (OFFERTORY, "en", {"w006": "Your", "w008": "God has blessed You"}),
    ],
)
def test_legitimate_alternatives_remain_valid(text, language, changes):
    doc, layers = store.load(ROOT, text)
    layer = deepcopy(layers[language])
    groups = {g["anchor"]: g for s in layer["segments"].values() for g in s.get("alignments", [])}
    for w, gloss in changes.items():
        if w in groups:
            groups[w]["gloss"] = gloss
        else:
            layer["words"][w]["gloss"] = gloss
    assert not interlinear.check(doc, layer)
    checker = english if language == "en" else polish
    assert not checker.check(doc, layer)


@pytest.mark.parametrize("text,pairs", [(GRADUAL, [3, 7, 10, 15]), (INTROIT, [3, 7, 10, 15, 23])])
def test_grouped_possessives_remain_a_legitimate_alternative(text, pairs):
    doc, layers = store.load(ROOT, text)
    layer = deepcopy(layers["en"])
    groups = layer["segments"]["s01"].setdefault("alignments", [])
    for n in pairs:
        ids = [wid(n), wid(n + 1)]
        noun = layer["words"][ids[0]].pop("gloss")
        assert layer["words"][ids[1]].pop("gloss") == "Your"
        gloss = noun.replace("of ", "of Your ") if noun.startswith("of ") else "Your " + noun
        groups.append({"words": ids, "anchor": ids[0], "gloss": gloss})
    groups.sort(key=lambda g: g["words"][0])
    assert not interlinear.check(doc, layer)
    assert not english.check(doc, layer)


def test_offertory_explains_its_addressee_with_a_liturgical_source():
    core = store.core(ROOT, OFFERTORY)
    assert core["localization"]["explanations"] == {"w009": {}}
    graph, _ = bibliography.load(ROOT)
    address = {"kind": "word", "text": OFFERTORY, "word": "w009"}
    uses = [u for u in graph["uses"] if u["address"] == address]
    assert [u["id"] for u in uses] == [f"use.{OFFERTORY}.addressee.lu1961"]
    assert uses[0]["role"] == "official_liturgical_context"
    assert uses[0]["locator"] == {"printed": "pp. 1365, 1258", "scan": "PDF pp. 1569, 1452"}
    for language, marker in (("pl", "o Maryi"), ("en", "of Mary")):
        words = store.raw_layer(ROOT, language, OFFERTORY)["words"]
        explanation = words["w009"]["explanation"]
        assert marker in explanation and "Elégit eam" in explanation
        assert [w for w, v in words.items() if "explanation" in v] == ["w009"]
