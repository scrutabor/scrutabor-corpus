"""Purification Epistle (Mal 3:1-4): contextual readings and sources."""

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
TEXT = "proprium.purificatio-beatae-mariae-virginis-epistola"
LINES = {
    "pl": (
        "To | mówi | Pan | Bóg | Oto | ja | posyłam | Anioła | mego | i | przygotuje | drogę"
        " | przed | obliczem | moim | A | natychmiast | przyjdzie | do | świątyni | swojej"
        " | Władca | którego | wy | szukacie | i | Anioł | Przymierza | którego | wy | pragniecie"
        " | Oto | przychodzi | mówi | Pan | Zastępów | lecz | kto | zdoła | pojąć | dzień"
        " | przyjścia | Jego | i | kto | ostoi się | na | widok | Jego | On | bowiem | jak | ogień"
        " | topiący | i | jak | ziele | foluszników | i | usiądzie | topiąc | i | oczyszczając"
        " | srebro | i | oczyści | synów | Lewiego | i | przecedzi | ich | jak | złoto | i | jak"
        " | srebro | i | będą | Panu | składać | ofiary | w | sprawiedliwości | I | spodoba się"
        " | Panu | ofiara | Judy | i | Jeruzalem | jak | dni | dawnych czasów | i | jak | lata"
        " | starodawne | mówi | Pan | wszechmogący"
    ),
    "en": (
        "Thus | says | the Lord | God | Behold | I | am sending | angel | My | and | shall prepare"
        " | the way | before | face | My | And | at once | will come | to | temple | His own"
        " | the Ruler | whom | you | seek | and | the Angel | of the Covenant | whom | you | desire"
        " | Behold | comes | says | the Lord | of hosts | and | who | will be able | to comprehend"
        " | the day | of the coming | His | and | who | will stand | to | see | Him"
        " | For He Himself is | like | fire | refining | and | like | herb | of fullers | and"
        " | will sit | refining | and | purifying | silver | and | will purify | the sons | of Levi"
        " | and | will refine | them | like | gold | and | like | silver | and | shall be"
        " | to the Lord | offering | sacrifices | in | justice | And | will please | the Lord"
        " | the sacrifice | of Judah | and | Jerusalem | as | the days | of old | and | as | years"
        " | ancient | says | the Lord | almighty"
    ),
}


def wid(n):
    return f"w{n:03}"


def line(doc, layer):
    """The target sequence a reader sees: one entry per direct gloss or group anchor."""
    groups = [g for s in layer["segments"].values() for g in s.get("alignments", [])]
    membership = {w: g for g in groups for w in g["words"]}
    out = []
    for segment in doc["segments"]:
        for word in segment.get("words", []):
            group = membership.get(word["id"])
            if group is None or group.get("anchor") == word["id"]:
                out.append(interlinear.effective_gloss(layer, word["id"]))
    return out


@pytest.mark.parametrize("language", ["pl", "en"])
def test_selected_complete_line(language):
    doc, layers = store.load(ROOT, TEXT)
    assert not interlinear.check(doc, layers[language])
    assert line(doc, layers[language]) == LINES[language].split(" | ")


def test_only_the_existing_english_group_and_no_zero():
    _, layers = store.load(ROOT, TEXT)
    assert not [g for s in layers["pl"]["segments"].values() for g in s.get("alignments", [])]
    groups = [g for s in layers["en"]["segments"].values() for g in s.get("alignments", [])]
    assert groups == [{"words": ["w050", "w051"], "anchor": "w050", "gloss": "For He Himself is"}]


def test_retained_latin_analyses():
    words = {w["id"]: w for w in store.core(ROOT, TEXT)["segments"][0]["words"]}
    assert words["w080"]["head"] == "w078" and words["w080"]["morph"]["mood"] == "part"
    assert words["w079"]["morph"]["case"] == "dat"
    assert (words["w047"]["lemma"], words["w048"]["morph"]["mood"]) == ("ad", "ger")
    assert (words["w092"]["morph"]["case"], words["w092"]["morph"]["number"]) == ("nom", "pl")
    assert (words["w093"]["morph"]["pos"], words["w093"]["morph"]["case"]) == ("noun", "gen")
    assert words["w097"]["head"] == "w096"
    assert words["w061"]["head"] == words["w063"]["head"] == "w060"


@pytest.mark.parametrize(
    "language,prefix", [("pl", "Czytanie formularza"), ("en", "The Epistle of")]
)
def test_localized_about(language, prefix):
    assert store.raw_layer(ROOT, language, TEXT)["about"].startswith(prefix)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_unchanged_prose_and_current_provenance(language):
    data = json.loads((ROOT / f"languages/{language}/translation-provenance.json").read_text())
    site = next(s for s in data["sites"] if s["site"] == f"{TEXT}.s01.{language}")
    prose = store.raw_layer(ROOT, language, TEXT)["segments"]["s01"]["translation"]
    assert site["target_sha256"] == canonical_hash(prose)
    core = store.core(ROOT, TEXT)
    assert site["source_sha256"] == canonical_hash(source_payload(core["segments"][0]))
    assert (site["origin"], site["review"]) == ("working-unsettled", "working")


def test_exact_raw_plan():
    bound = resolve_binding(ROOT / "witnesses" / TEXT / "do.txt", ROOT)
    assert bound is not None and bound.source["binding_id"] == "purification-epistle"
    plan = bound.source["binding"]
    assert plan["evidence"] == [
        {
            "archive": "purification-day",
            "first": 171,
            "last": 171,
            "section": "Lectio",
            "section_line": 168,
        }
    ]
    assert plan["reading"] == [{"archive": "purification-day", "first": 171, "last": 171}]
    assert plan["references"] == []
    tokens = bound.text.split()
    assert len(tokens) == 100 and (tokens[0], tokens[-1]) == ("Hæc", "omnípotens.")
    assert "Léctio" not in bound.text and "Malach" not in bound.text


def test_exact_apparatus():
    apparatus = json.loads((ROOT / "witnesses" / TEXT / "apparatus.json").read_text())
    actual = [(e["at"], e["ours"], e["witnesses"], e["class"]) for e in apparatus["adjudicated"]]
    assert actual == [
        ("w005", "Ecce", {"do": "Ecce,"}, "punctuation"),
        ("w008", "Ángelum", {"mr": "Angelum", "do": "Angelum"}, "capital-accent"),
        ("w025", "quǽritis,", {"do": "quæritis,"}, "accent"),
        ("w027", "Ángelus", {"mr": "Angelus", "do": "Angelus"}, "capital-accent"),
        ("w032", "Ecce", {"do": "Ecce,"}, "punctuation"),
        ("w043", "eius,", {"do": "ejus,"}, "orthography"),
        ("w054", "conflans,", {"do": "conflans"}, "punctuation"),
        ("w061", "conflans,", {"do": "conflans"}, "punctuation"),
        ("w073", "aurum,", {"do": "aurum"}, "punctuation"),
        ("w083", "iustítia.", {"do": "justítia."}, "orthography"),
        ("w088", "Iuda,", {"do": "Juda"}, "orthography"),
        ("w090", "Ierúsalem,", {"do": "Jerúsalem,"}, "orthography"),
        ("w093", "sǽculi,", {"do": "sǽculi"}, "punctuation"),
    ]
    assert "typical edition" not in json.dumps(apparatus)


def test_printed_identity_is_benziger_and_current_conformity():
    graph, _ = bibliography.load(ROOT)
    mr = next(u for u in graph["uses"] if u["id"] == f"use.{TEXT}.mr1962")
    assert mr["role"] == "direct_approved_print"
    assert "Benziger Brothers 1962 Editio iuxta typicam" in mr["claim"]
    assert mr["locator"]["printed"] == "pp. 466–467"
    header = (ROOT / "witnesses" / TEXT / "mr.txt").read_text()
    assert "editio iuxta typicam" in header and "typical edition" not in header
    assert "local-archive:" not in header
    editorial = store.core(ROOT, TEXT)["editorial"]
    assert "typical edition" not in editorial["notes"]
    assert "abbreviated conclusions" not in editorial["notes"]
    assert "typical-edition" not in editorial["source"]["method"]
    do = next(u for u in graph["uses"] if u["id"] == f"use.{TEXT}.do44667ff")
    assert "line 171" in do["locator"]["section"]
    assert "inherited references" not in do["locator"]["section"]


def test_pending_witness_and_collation_dependencies():
    graph, _ = bibliography.load(ROOT)
    core = store.core(ROOT, TEXT)
    witnesses = [w for w in graph["witnesses"] if w["text"] == TEXT]
    collations = [c for c in graph["collations"] if c["text"] == TEXT]
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
    contract = collation_subject(ROOT, collations[0], core, subjects)["contract"]
    assert contract == "collation-review-2"


MUTATIONS = {
    "periphrastic-participle": ("pl", {"w080": "składając"}),
    "according-to-for-in": ("pl", {"w082": "według"}),
    "adjective-for-genitive-noun": ("pl", {"w093": "dawnych"}),
    "capital-adjective": ("pl", {"w100": "Wszechmogący"}),
    "capital-hosts": ("en", {"w036": "of Hosts"}),
}


@pytest.mark.parametrize("mode", sorted(MUTATIONS))
def test_escaped_classes_pass_generic_checks_but_not_context(mode):
    """Each restored defect is accepted by the generic validators — the reason
    this file pins the contextual reading — and rejected by the line test."""
    language, changes = MUTATIONS[mode]
    doc, layers = store.load(ROOT, TEXT)
    layer = deepcopy(layers[language])
    for w, gloss in changes.items():
        layer["words"][w]["gloss"] = gloss
    assert not interlinear.check(doc, layer)
    checker = english if language == "en" else polish
    assert not checker.check(doc, layer)
    assert line(doc, layer) != LINES[language].split(" | ")


@pytest.mark.parametrize(
    "language,changes",
    [
        ("pl", {"w080": "składali"}),
        ("pl", {"w093": "wieku"}),
        ("en", {"w011": "will prepare", "w078": "will be"}),
        ("en", {"w063": "cleansing"}),
    ],
)
def test_legitimate_alternatives_remain_valid(language, changes):
    doc, layers = store.load(ROOT, TEXT)
    layer = deepcopy(layers[language])
    for w, gloss in changes.items():
        layer["words"][w]["gloss"] = gloss
    assert not interlinear.check(doc, layer)
    checker = english if language == "en" else polish
    assert not checker.check(doc, layer)
