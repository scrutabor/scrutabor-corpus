"""Peter and Paul: reading boundaries, referents and complete constructions."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.layers import enrich_layer, expand_core
from checks import english, interlinear, polish
from checks.raw_binding import resolve_binding

ROOT = Path(__file__).resolve().parents[1]
NAME = "sancti-petri-et-pauli-apostolorum-epistola"
TEXT = "proprium." + NAME


def core():
    return json.loads((ROOT / "texts/proprium" / f"{NAME}.json").read_text())


def layer(lang):
    return json.loads((ROOT / f"languages/{lang}/texts/proprium/{NAME}.json").read_text())


def group(data, words):
    return next(g for g in data["segments"]["s01"]["alignments"] if g["words"] == words)


def test_reading_keeps_the_complete_two_page_body():
    doc = core()
    words = doc["segments"][0]["words"]
    assert len(words) == 212
    assert [w["form"] for w in words[:3]] == ["In", "diébus", "illis"]
    assert [w["form"] for w in words[-2:]] == ["plebis", "Iudæórum"]
    assert all(w["form"] != "Amen" for w in words)
    bound = resolve_binding(ROOT / "witnesses" / TEXT / "do.txt", ROOT)
    assert bound is not None and len(bound.text.split()) == 212


def test_contextual_pronoun_genders_preserve_the_referents():
    words = {w["id"]: w for w in core()["segments"][0]["words"]}
    assert {wid: words[wid]["morph"]["gender"] for wid in ["w010", "w167", "w171"]} == {
        "w010": "m",
        "w167": "f",
        "w171": "f",
    }


def test_polish_clitic_and_accusative_subject_have_complete_realizations():
    data = layer("pl")
    assert group(data, ["w033", "w034"])["gloss"] == "Gdy go"
    assert group(data, ["w154", "w155", "w156"])["gloss"] == "że widzi widzenie"
    assert group(data, ["w076"])["reason"] == "inflection"
    assert data["words"]["w078"]["gloss"] == "spał"


def test_english_count_and_departure_have_coherent_complements():
    data = layer("en")
    assert data["words"]["w041"]["gloss"] == "detachments of four"
    assert data["words"]["w042"]["gloss"] == "soldiers"
    assert data["words"]["w183"]["gloss"] == "departed"
    assert data["words"]["w185"]["gloss"] == "from"
    assert data["words"]["w186"]["gloss"] == "him"


def test_english_motion_clauses_do_not_become_unlinked_finite_verbs():
    words = layer("en")["words"]
    assert {
        wid: words[wid]["gloss"] for wid in ["w140", "w141", "w157", "w163", "w177", "w178"]
    } == {
        "w140": "having gone out",
        "w141": "he followed",
        "w157": "Passing through",
        "w163": "they came",
        "w177": "going out",
        "w178": "they passed on",
    }


@pytest.mark.parametrize("lang", ["pl", "en"])
def test_every_shared_or_zero_member_has_exactly_one_provider(lang):
    doc, data = core(), layer(lang)
    assert interlinear.check(doc, data) == []
    for i, alignment in enumerate(data["segments"]["s01"]["alignments"]):
        for wid in alignment["words"]:
            duplicate = deepcopy(data)
            duplicate["words"][wid]["gloss"] = "duplicate"
            assert interlinear.check(doc, duplicate)
            missing = deepcopy(data)
            missing["segments"]["s01"]["alignments"][i]["words"].remove(wid)
            assert interlinear.check(doc, missing)


def test_polish_reflexive_guard_rejects_the_old_isolated_conjunction():
    doc, data = core(), layer("pl")
    assert polish.check(expand_core(doc), enrich_layer(doc, data)) == []
    bad = deepcopy(data)
    bad["segments"]["s01"]["alignments"].remove(group(bad, ["w154", "w155", "w156"]))
    for wid, value in {"w154": "że,", "w155": "widzi", "w156": "widzenie"}.items():
        bad["words"][wid]["gloss"] = value
    assert any(
        "replaces a reflexive pronoun" in error
        for error in polish.check(expand_core(doc), enrich_layer(doc, bad))
    )


@pytest.mark.parametrize(
    "wid,bad_value,diagnostic",
    [
        ("w042", "of soldiers", "quaternion glosses"),
        ("w183", "left", "departure glosses"),
    ],
)
def test_english_guard_rejects_the_old_complement_pairs(wid, bad_value, diagnostic):
    doc, data = core(), layer("en")
    assert english.check(expand_core(doc), enrich_layer(doc, data)) == []
    data["words"][wid]["gloss"] = bad_value
    assert any(
        diagnostic in error for error in english.check(expand_core(doc), enrich_layer(doc, data))
    )


@pytest.mark.parametrize("wid", ["w010", "w167", "w171"])
def test_contextual_gender_does_not_inherit_default_approval(wid):
    doc = core()
    word = next(w for w in expand_core(doc)["segments"][0]["words"] if w["id"] == wid)
    assert word["analysis"] == {
        "confidence": "high",
        "sources": ["editorial", "whitakers", "collatinus"],
        "review": "pending",
    }
    del doc["editorial"]["words"][wid]
    expanded = expand_core(doc)
    absent = next(w for w in expanded["segments"][0]["words"] if w["id"] == wid)
    assert "analysis" not in absent
    assert expanded["analysis_defaults_words"]["review"] == "accepted"


@pytest.mark.parametrize("lang", ["pl", "en"])
def test_current_provenance_is_bound_without_promoting_working_text(lang):
    from checks.translation_provenance import canonical_hash, source_payload

    sites = json.loads((ROOT / f"languages/{lang}/translation-provenance.json").read_text())[
        "sites"
    ]
    site = next(s for s in sites if s["site"] == f"{TEXT}.s01.{lang}")
    assert site["source_sha256"] == canonical_hash(source_payload(core()["segments"][0]))
    assert site["target_sha256"] == canonical_hash(layer(lang)["segments"]["s01"]["translation"])
    assert (site["origin"], site["review"], site["familiar_core"]) == (
        "working-unsettled",
        "working",
        False,
    )
