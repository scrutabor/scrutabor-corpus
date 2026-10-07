"""Advent I Gospel keeps complete clauses and the exact bounded reading."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.layers import enrich_layer, expand_core
from checks import english, interlinear, polish
from checks.raw_binding import resolve_binding
from checks.transcription import check_transcriptions
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
NAME = "dominica-i-adventus-evangelium"
TEXT = "proprium." + NAME
GROUPS = {
    "pl": [
        ("s01", ["w022", "w023"], "w022", "zamętu wywołanego szumem"),
        ("s01", ["w027", "w028"], "w027", "gdy ludzie będą mdleć"),
        ("s03", ["w054", "w055", "w056", "w057"], "w057", "gdy zaś to zacznie się dziać"),
        ("s05", ["w092", "w093"], "w093", "że to się dzieje"),
    ],
    "en": [
        ("s01", ["w006", "w007"], "w006", "to His disciples"),
        ("s01", ["w017", "w018"], "w018", "on earth"),
        ("s01", ["w027", "w028"], "w027", "people fainting"),
        ("s02", ["w050", "w051"], "w050", "great power"),
        ("s03", ["w054", "w055", "w056", "w057"], "w057", "but when these things begin to happen"),
        ("s03", ["w061", "w062"], "w061", "your heads"),
        ("s03", ["w064", "w065", "w066"], "w064", "your redemption draws near"),
        ("s06", ["w104", "w105", "w106", "w107"], "w105", "this generation will not pass away"),
        ("s07", ["w115", "w116", "w117"], "w115", "but My words"),
        ("s07", ["w118", "w119"], "w119", "will not pass away"),
    ],
}


def core():
    return json.loads((ROOT / "texts/proprium" / f"{NAME}.json").read_text())


def layer(lang):
    return json.loads((ROOT / f"languages/{lang}/texts/proprium/{NAME}.json").read_text())


def test_complete_reading_retains_assertive_amen_without_an_added_response():
    doc = core()
    assert [len(s["words"]) for s in doc["segments"]] == [40, 13, 13, 20, 13, 11, 9]
    words = [w for s in doc["segments"] for w in s["words"]]
    assert [w["id"] for w in words] == [f"w{i:03}" for i in range(1, 120)]
    assert [w["form"] for w in words[:3]] == ["In", "illo", "témpore"]
    assert [w["form"] for w in words[-2:]] == ["non", "transíbunt"]
    assert [w["id"] for w in words if w["form"] == "Amen"] == ["w100"]
    assert all((s["speaker"], s["voice"]) == ("sacerdos", "clara") for s in doc["segments"])


@pytest.mark.parametrize("lang", ["pl", "en"])
def test_minimal_groups_have_one_provider_and_preserve_every_card(lang):
    doc, data = core(), layer(lang)
    assert interlinear.check(doc, data) == []
    assert len(data["words"]) == 119
    assert sum("gloss" in w for w in data["words"].values()) == (109 if lang == "pl" else 93)
    assert sum(len(s.get("alignments", [])) for s in data["segments"].values()) == len(GROUPS[lang])
    for sid, ids, anchor, wording in GROUPS[lang]:
        expected = {"words": ids, "anchor": anchor, "gloss": wording}
        assert expected in data["segments"][sid]["alignments"]
        for wid in ids:
            assert "gloss" not in data["words"][wid]
            duplicate = deepcopy(data)
            duplicate["words"][wid]["gloss"] = "extra"
            assert interlinear.check(doc, duplicate)
            lost = deepcopy(data)
            alignment = next(a for a in lost["segments"][sid]["alignments"] if a["words"] == ids)
            alignment["words"].remove(wid)
            alignment["anchor"] = alignment["words"][0]
            assert interlinear.check(doc, lost)


def test_polish_keeps_the_present_yielding_already_and_reflexive_source():
    doc, data = core(), layer("pl")
    assert data["words"]["w017"]["gloss"] == "na"
    assert data["segments"]["s04"]["translation"] == (
        "I opowiedział im przypowieść: Spójrzcie na figowiec i wszystkie drzewa. "
        "Gdy wydają już z siebie owoc, wiecie, że lato jest blisko."
    )
    words = {w["id"]: w for s in doc["segments"] for w in s["words"]}
    assert words["w077"]["lemma"] == "produco"
    assert words["w077"]["morph"]["tense"] == "pres"
    assert [words[w]["lemma"] for w in ["w078", "w079", "w080", "w081"]] == [
        "iam",
        "ex",
        "sui",
        "fructus",
    ]
    assert "„W owym czasie”" in data["about"]
    assert polish.check(expand_core(doc), enrich_layer(doc, data)) == []


def test_english_preserves_separate_clause_subjects_and_contextual_complements():
    doc, data = core(), layer("en")
    assert {
        w: data["words"][w]["gloss"]
        for w in ["w023", "w033", "w068", "w077", "w088", "w089", "w091", "w093"]
    } == {
        "w023": "at the roaring",
        "w033": "of what",
        "w068": "He told",
        "w077": "they put forth",
        "w088": "also",
        "w089": "you",
        "w091": "you see",
        "w093": "happening",
    }
    assert english.check(expand_core(doc), enrich_layer(doc, data)) == []


@pytest.mark.parametrize(
    "wid,bad,label",
    [
        ("w091", "see", "temporal glosses"),
        ("w093", "to happen", "perception glosses"),
        ("w088", "and", "additive glosses"),
    ],
)
def test_english_reintroduced_junctions_fail_the_normal_dispatch(wid, bad, label):
    doc, data = core(), layer("en")
    data["words"][wid]["gloss"] = bad
    assert any(label in e for e in english.check(expand_core(doc), enrich_layer(doc, data)))


@pytest.mark.parametrize("lang", ["pl", "en"])
def test_all_seven_provenance_sites_name_the_current_latin_and_target(lang):
    doc, data = core(), layer(lang)
    sites = json.loads((ROOT / f"languages/{lang}/translation-provenance.json").read_text())[
        "sites"
    ]
    selected = [s for s in sites if s["text"] == TEXT]
    assert len(selected) == 7
    for site in selected:
        source = next(s for s in doc["segments"] if s["id"] == site["segment"])
        assert site["source_sha256"] == canonical_hash(source_payload(source))
        assert site["target_sha256"] == canonical_hash(
            data["segments"][site["segment"]]["translation"]
        )


def test_digital_binding_resolves_only_the_119_word_gospel_body():
    witness = ROOT / "witnesses" / TEXT / "do.txt"
    assert check_transcriptions(witness.parent) == ([], 2)
    bound = resolve_binding(witness, ROOT)
    assert bound is not None
    archive = (ROOT / "witnesses/raw/do-Adv1-0.txt").read_text().splitlines()
    assert bound.text == archive[43]
    assert len(bound.text.split()) == 119
    assert "Sequéntia" not in bound.text
    assert bound.text.split()[-1] == "transíbunt."
    assert bound.text.split()[99] == "Amen,"
    assert bound.text.split().count("Amen,") == 1
