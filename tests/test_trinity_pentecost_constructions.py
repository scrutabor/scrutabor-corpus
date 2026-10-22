"""Preserve contextual constructions and literal conclusion sources."""

import json
from pathlib import Path

import pytest

from build_reader.bibliography_bindings import digest, selected_text
from checks.collate import load_witness
from checks.translation_provenance import canonical_hash

CORPUS = Path(__file__).resolve().parents[1]
COLLECT = "proprium.sanctissimae-trinitatis-collecta"
SECRET = "proprium.sanctissimae-trinitatis-secreta"
POSTCOMMUNION = "proprium.sanctissimae-trinitatis-postcommunio"
SEQUENCE = "proprium.dominica-pentecostes-sequentia"


def load(path):
    return json.loads((CORPUS / path).read_text())


def core(tid):
    return load("texts/" + tid.replace(".", "/", 1) + ".json")


def layer(tid, language):
    return load(f"languages/{language}/texts/" + tid.replace(".", "/", 1) + ".json")


def words(tid):
    return {w["id"]: w for s in core(tid)["segments"] for w in s["words"]}


def group(tid, language, first, last):
    target = layer(tid, language)
    members = [f"w{i:03}" for i in range(first, last + 1)]
    found = [
        a
        for s in target["segments"].values()
        for a in s.get("alignments", [])
        if a["words"] == members
    ]
    assert len(found) == 1, (tid, language, members)
    assert all("gloss" not in target["words"][w] for w in members)
    return found[0]


@pytest.mark.parametrize(
    "tid,first,last,anchor,gloss",
    [
        (COLLECT, 6, 7, 6, "Your servants"),
        (COLLECT, 12, 15, 15, "to acknowledge the glory of the eternal Trinity"),
        (COLLECT, 22, 23, 22, "we ask that"),
        (COLLECT, 24, 26, 26, "by the steadfastness of that same faith"),
        (COLLECT, 27, 31, 30, "we may always be defended from all adversities"),
        (COLLECT, 33, 34, 33, "our Lord"),
        (COLLECT, 37, 38, 37, "Your Son"),
        (COLLECT, 39, 43, 41, "who lives and reigns with You"),
        (SECRET, 4, 5, 4, "our God"),
        (SECRET, 6, 10, 10, "through the invocation of Your holy name"),
        (SECRET, 11, 13, 13, "the victim of this oblation"),
        (SECRET, 17, 21, 19, "perfect our very selves as an everlasting gift to You"),
        (POSTCOMMUNION, 9, 10, 9, "our God"),
        (POSTCOMMUNION, 11, 13, 13, "the reception of this sacrament"),
        (
            POSTCOMMUNION,
            15,
            21,
            21,
            "the confession of the eternal Holy Trinity and of that same undivided Unity",
        ),
        (SEQUENCE, 7, 9, 9, "a ray of Your light"),
        (SEQUENCE, 19, 20, 19, "Best Comforter"),
        (SEQUENCE, 36, 37, 36, "most blessed Light"),
        (SEQUENCE, 39, 40, 40, "the inmost depths of the heart"),
        (SEQUENCE, 41, 42, 42, "of Your faithful"),
        (SEQUENCE, 80, 82, 82, "trusting in You"),
        (SEQUENCE, 86, 87, 87, "the reward of virtue"),
        (SEQUENCE, 89, 90, 90, "a saving end"),
    ],
)
def test_english_complete_constructions(tid, first, last, anchor, gloss):
    aligned = group(tid, "en", first, last)
    assert aligned["anchor"] == f"w{anchor:03}"
    assert aligned["gloss"] == gloss


def test_collect_relative_has_one_subject_and_preserves_granting():
    target = layer(COLLECT, "en")
    assert target["words"]["w004"]["gloss"] == "who"
    assert target["words"]["w005"]["gloss"] == "have granted"
    assert words(COLLECT)["w005"]["morph"]["person"] == 2
    assert target["words"]["w032"]["gloss"] == "Through"


def test_english_orations_keep_grant_and_emphatic_result_in_natural_prose():
    collect = layer(COLLECT, "en")["segments"]["s01"]["translation"]
    secret = layer(SECRET, "en")["segments"]["s01"]["translation"]
    assert "who have granted Your servants" in collect
    assert "we ask that" in collect
    assert "we may always be defended from all adversities" in collect
    assert "perfect our very selves as an everlasting gift to You" in secret


def test_polish_firmitas_preserves_firmness_rather_than_general_power():
    target = layer(COLLECT, "pl")
    assert target["words"]["w026"]["gloss"] == "stałością"
    assert words(COLLECT)["w026"]["lemma"] == "firmitas"
    assert words(COLLECT)["w026"]["morph"]["case"] == "abl"
    assert "dzięki stałości tej samej wiary" in target["segments"]["s01"]["translation"]
    assert "chronieni przed wszelkimi przeciwnościami" in target["segments"]["s01"]["translation"]


def test_saving_end_does_not_change_the_latin_nouns_or_invent_death():
    assert group(SEQUENCE, "pl", 89, 90)["gloss"] == "zbawienny kres"
    latin = words(SEQUENCE)
    assert latin["w089"]["lemma"] == "salus"
    assert latin["w089"]["morph"]["case"] == "gen"
    assert latin["w090"]["lemma"] == "exitus"
    assert latin["w090"]["morph"]["case"] == "acc"
    prose = layer(SEQUENCE, "en")["segments"]["s01"]["translation"]
    assert "give a saving end" in prose
    assert "give the outcome of salvation" not in prose
    assert "death" not in prose.lower()
    rows = load("languages/en/translation-provenance.json")["sites"]
    row = next(r for r in rows if r["text"] == SEQUENCE and r["segment"] == "s01")
    assert row["target_sha256"] == canonical_hash(prose)


def test_natural_captions_do_not_replace_the_saved_grammatical_forms():
    latin = words(SEQUENCE)
    assert latin["w040"]["lemma"] == "intimus"
    assert latin["w040"]["morph"]["pos"] == "adj"
    assert latin["w040"]["morph"]["number"] == "pl"
    assert latin["w082"]["morph"]["mood"] == "part"
    assert latin["w082"]["morph"]["case"] == "dat"
    assert latin["w082"]["morph"]["tense"] == "pres"


def test_polish_case_marked_order_is_not_mechanically_regrouped():
    target = layer(SECRET, "pl")
    assert target["words"]["w017"]["gloss"] == "nas samych"
    assert target["words"]["w018"]["gloss"] == "Tobie"
    assert target["words"]["w019"]["gloss"] == "uczyń doskonałym"
    assert target["words"]["w020"]["gloss"] == "darem"
    assert target["words"]["w021"]["gloss"] == "wiecznym"
    latin = words(SECRET)
    assert latin["w020"]["lemma"] == "munus"
    assert latin["w020"]["morph"]["case"] == "acc"
    assert latin["w021"]["head"] == "w020"


def test_postcommunion_subjects_remain_separate_from_the_vocative():
    latin = words(POSTCOMMUNION)
    assert latin["w013"]["morph"]["case"] == "nom"
    assert latin["w021"]["morph"]["case"] == "nom"
    target = layer(POSTCOMMUNION, "en")
    # Ad salutem expresses the intended benefit, not an English to-complement.
    assert target["words"]["w003"]["gloss"] == "for"
    assert target["words"]["w008"]["gloss"] == "Lord"
    assert not any(
        "w008" in a["words"] and "w021" in a["words"]
        for s in target["segments"].values()
        for a in s.get("alignments", [])
    )


def test_collect_literal_formula_and_house_choices_stay_distinct():
    metadata, printed = load_witness(CORPUS / "witnesses" / COLLECT / "mr.txt")
    literal = (
        "Per Dominum nostrum Iesum Christum Filium tuum, qui tecum vivit et regnat "
        "in unitate Spiritus Sancti, Deus, per omnia sæcula sæculorum. Amen;"
    )
    assert printed.endswith(literal)
    assert "RG115a" in metadata["assembly"]
    assert "Per Dóminum" not in printed
    apparatus = load(f"witnesses/{COLLECT}/apparatus.json")
    for wid in ("w033", "w037", "w038", "w039", "w045", "w046", "w050", "w051", "w052", "w053"):
        assert any(r["at"] == wid and "mr" in r["witnesses"] for r in apparatus["adjudicated"])
    assert any(
        r["at"] == "w053" and r["witnesses"] == {"mr": "Amen;"} for r in apparatus["adjudicated"]
    )
    graph = load("bibliography/graph.json")
    rg = next(r for r in graph["uses"] if r["id"] == f"use.{COLLECT}.conclusion-rg115a.mr1962")
    assert rg["address"] == {"kind": "word", "text": COLLECT, "word": "w032"}
    assert (
        rg["evidence_sha256"] == "b511f3aa4016b387d2995b5089e15aa62593c04118052ef48dcc09352fcf769c"
    )
    collation = next(r for r in graph["collations"] if r["text"] == COLLECT)
    assert collation["apparatus_sha256"] == digest(apparatus)
    assert collation["selected_text_sha256"] == digest(selected_text(core(COLLECT)))


def test_source_use_order_stays_canonical():
    uses = load("bibliography/graph.json")["uses"]
    identifiers = [row["id"] for row in uses]
    assert identifiers == sorted(set(identifiers))
