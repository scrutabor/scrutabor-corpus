"""Possession, growth and the collect's distinct source spans stay explicit."""

import json
from pathlib import Path

import pytest

from build_reader.bibliography_bindings import digest, selected_text
from checks.interlinear import check
from checks.language_packs import check_layer
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
NAME = "dominica-vi-post-pentecosten-collecta"
TEXT = f"proprium.{NAME}"
GROUPS = [
    ("pl", 19, 20, 20, "wzrost pobożności"),
    ("pl", 27, 28, 28, "z troskliwą dobrocią"),
    ("en", 3, 8, 4, "to whom all that is best belongs"),
    ("en", 10, 11, 10, "in our hearts"),
    ("en", 19, 20, 20, "an increase of devotion"),
    ("en", 22, 25, 25, "You may nourish what is good"),
    ("en", 27, 28, 28, "with loving care"),
    ("en", 29, 32, 32, "You may guard what has been nourished"),
    ("en", 34, 35, 34, "our Lord"),
    ("en", 38, 39, 38, "Your Son"),
    ("en", 47, 48, 47, "of the Holy Spirit"),
]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def layer(language):
    return load(f"languages/{language}/texts/proprium/{NAME}.json")


@pytest.mark.parametrize("language,start,end,anchor,gloss", GROUPS)
def test_grouped_construction_has_one_gloss(language, start, end, anchor, gloss):
    data = layer(language)
    ids = [f"w{number:03}" for number in range(start, end + 1)]
    assert {"words": ids, "anchor": f"w{anchor:03}", "gloss": gloss} in data["segments"]["s01"].get(
        "alignments", []
    )
    assert all("gloss" not in data["words"][word] for word in ids)


@pytest.mark.parametrize("language,grouped", [("pl", 4), ("en", 26)])
def test_complete_realization_and_distinct_response(language, grouped):
    core = load(f"texts/proprium/{NAME}.json")
    data = layer(language)
    ids = [w["id"] for s in core["segments"] for w in s["words"]]
    assert ids == [f"w{number:03}" for number in range(1, 55)]
    assert set(data["words"]) == set(ids)
    groups = data["segments"]["s01"].get("alignments", [])
    assert sum(len(g["words"]) for g in groups) == grouped
    assert all("reason" not in g for g in groups)
    assert check(core, data) == []
    assert check_layer(core, data, ROOT / f"languages/{language}/texts/proprium/{NAME}.json") == []
    assert data["segments"]["s02"] == {"translation": "Amen."}


def test_english_belonging_not_creation_and_one_register():
    data = layer("en")
    assert data["segments"]["s01"]["translation"] == (
        "God of hosts, all that is best belongs to You. Plant love of Your name "
        "in our hearts and make our devotion grow, so that You may nourish what "
        "is good and, with loving care, preserve what You have nourished. Through "
        "our Lord Jesus Christ, Your Son, who lives and reigns with You in the "
        "unity of the Holy Spirit, God, forever and ever."
    )
    expected = {
        "w013": "of Your",
        "w040": "who",
        "w041": "with You",
        "w042": "lives",
        "w044": "reigns",
    }
    assert {key: data["words"][key]["gloss"] for key in expected} == expected


def test_polish_government_result_and_unchanged_prose():
    data = layer("pl")
    assert canonical_hash(data["segments"]["s01"]["translation"]) == (
        "94516ac23515e3c1d80bc9379f018d8d9d92a081885fe6ab654c93c3e41a7eab"
    )
    expected = {
        "w003": "do którego",
        "w004": "należy",
        "w029": "tego, co",
        "w030": "jest",
        "w031": "wypielęgnowane",
    }
    assert {key: data["words"][key]["gloss"] for key in expected} == expected


@pytest.mark.parametrize(
    "language,alternative",
    [("pl", "przez gorliwą pobożność"), ("en", "through zealous devotion to God")],
)
def test_contextual_explanation_retains_the_genuine_alternative(language, alternative):
    word = layer(language)["words"]["w027"]
    assert "pietatis studio" in word["explanation"]
    assert alternative in word["explanation"]
    assert "gloss" not in word and "note" not in word


@pytest.mark.parametrize("language", ["pl", "en"])
def test_provenance_bound_without_new_acceptance(language):
    core = load(f"texts/proprium/{NAME}.json")
    site = next(
        s
        for s in load(f"languages/{language}/translation-provenance.json")["sites"]
        if s["site"] == f"{TEXT}.s01.{language}"
    )
    assert site["source_sha256"] == canonical_hash(source_payload(core["segments"][0]))
    assert site["target_sha256"] == canonical_hash(
        layer(language)["segments"]["s01"]["translation"]
    )
    assert (site["origin"], site["review"]) == ("working-unsettled", "working")


@pytest.mark.parametrize(
    "word,selected,raw",
    [
        ("w003", "cuius", "cujus"),
        ("w036", "Iesum", "Jesum"),
        ("w037", "Christum", "Christum,"),
        ("w040", "Qui", "qui"),
        ("w048", "Sancti,", "Sancti"),
    ],
)
def test_all_digital_accidentals_recorded(word, selected, raw):
    apparatus = load(f"witnesses/{TEXT}/apparatus.json")
    entry = next(e for e in apparatus["adjudicated"] if e["at"] == word)
    assert entry["ours"] == selected and entry["witnesses"] == {"do": raw}


def test_selected_latin_and_ritual_unchanged_with_contextual_neuters():
    core = load(f"texts/proprium/{NAME}.json")
    assert (
        digest(selected_text(core))
        == "29ca03468b8e98b10ee980f8419a038657316aedc90154cf4746cd55c4614349"
    )
    words = {w["id"]: w for s in core["segments"] for w in s["words"]}
    assert words["w020"]["post"] == ";"
    for word in ("w022", "w029"):
        assert words[word]["morph"] == {"pos": "pron", "case": "nom", "number": "pl", "gender": "n"}
        assert core["editorial"]["words"][word]["analysis"] == {
            "confidence": "high",
            "sources": ["editorial", "whitakers", "collatinus"],
            "review": "pending",
        }
    assert {
        w
        for w, value in core["editorial"]["words"].items()
        if value["analysis"]["review"] == "pending"
    } == {"w001", "w006", "w008", "w011", "w013", "w017", "w018", "w022", "w024", "w029", "w035"}


def test_source_pages_expansion_and_pending_state_remain_distinct():
    graph = load("bibliography/graph.json")
    uses = {
        u["id"].removeprefix(f"use.{TEXT}."): u
        for u in graph["uses"]
        if u["address"].get("text") == TEXT
    }
    assert uses["mr1962"]["verified_on"] == "2026-09-25"
    assert "not the full expanded conclusion" in uses["mr1962"]["claim"]
    for suffix, page, sha in [
        (
            "continued-body.mr1962",
            "p. 379",
            "e99c61760982eec4427ac4b65732a529d86c3400ba63e3aa58f8246af37eb4ed",
        ),
        (
            "expanded-conclusion.mr1962",
            "p. xvii",
            "b511f3aa4016b387d2995b5089e15aa62593c04118052ef48dcc09352fcf769c",
        ),
    ]:
        assert uses[suffix]["locator"]["printed"] == page
        assert uses[suffix]["evidence_sha256"] == sha
    assert "ctóribus after pe-" in uses["continued-body.mr1962"]["claim"]
    witnesses = [w for w in graph["witnesses"] if w["text"] == TEXT]
    assert len(witnesses) == 2 and all(w["review"] == {"status": "pending"} for w in witnesses)
    collations = [c for c in graph["collations"] if c["text"] == TEXT]
    assert len(collations) == 1 and collations[0]["review"] == {"status": "pending"}
    printed = (ROOT / f"witnesses/{TEXT}/mr.txt").read_text(encoding="utf-8")
    assert "Benziger 1962 (Editio iuxta typicam)" in printed
    assert "RG 115 a is unaccented" in printed and "tuum, qui" in printed
