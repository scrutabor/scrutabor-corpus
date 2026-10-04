"""Keep this Secret's English constructions and historical basis distinct."""

import json
from copy import deepcopy

import pytest

from build_reader import store
from checks.interlinear import effective_gloss
from checks.language_packs import check_layer
from checks.layout import CORPUS
from checks.translation_provenance import canonical_hash

TEXT = "proprium.dominica-vii-post-pentecosten-secreta"
SOURCE = "64dda22f4b0753135be1112b8bd36eab7fbb9c92586c2fc2d831c0a4b7f65d8a"
GROUPS = [
    (
        "s01",
        3,
        9,
        9,
        "through the perfection of one sacrifice have confirmed the varied sacrifices of the Law",
    ),
    ("s01", 13, 15, 15, "servants devoted to You"),
    (
        "s01",
        17,
        22,
        22,
        "sanctify it with the same blessing You bestowed on the gifts of Abel",
    ),
    ("s01", 28, 30, 30, "the honor of Your majesty"),
    ("s01", 31, 34, 32, "may contribute to the salvation of all"),
    ("s01", 36, 37, 36, "our Lord"),
    ("s01", 40, 41, 40, "Your Son"),
    ("s01", 49, 50, 49, "of the Holy Spirit"),
    ("s02", 52, 55, 54, "forever and ever"),
]


def load():
    return store.core(CORPUS, TEXT), store.raw_layer(CORPUS, "en", TEXT)


@pytest.mark.parametrize("segment,first,last,anchor,gloss", GROUPS)
def test_each_complete_construction_is_realized_once(segment, first, last, anchor, gloss):
    _, layer = load()
    members = [f"w{i:03d}" for i in range(first, last + 1)]
    groups = layer["segments"][segment].get("alignments", [])
    assert {
        "words": members,
        "anchor": f"w{anchor:03d}",
        "gloss": gloss,
    } in groups
    assert all(layer["words"][word] == {} for word in members)
    assert [effective_gloss(layer, word) for word in members if effective_gloss(layer, word)] == [
        gloss
    ]


def test_grouped_words_keep_their_identifiers_without_duplicate_captions():
    core, layer = load()
    assert check_layer(core, layer, store.layer_path(CORPUS, "en", TEXT)) == []
    assert list(layer["words"]) == [w["id"] for s in core["segments"] for w in s["words"]]
    assert len(layer["words"]) == 56
    assert sum(value == {} for value in layer["words"].values()) == 33
    assert sum(bool(value) for value in layer["words"].values()) == 23
    assert sum(len(s.get("alignments", [])) for s in layer["segments"].values()) == 9
    for word, gloss in (("w002", "who"), ("w027", "for"), ("w042", "who")):
        assert layer["words"][word] == {"gloss": gloss}


def test_deleting_a_grouped_word_is_not_an_allowed_sparse_layer():
    core, layer = load()
    grouped = [word for word, value in layer["words"].items() if value == {}]
    assert len(grouped) == 33
    for word in grouped:
        broken = deepcopy(layer)
        del broken["words"][word]
        errors = check_layer(core, broken, store.layer_path(CORPUS, "en", TEXT))
        assert any("word coverage or order differs" in error for error in errors)


def test_singular_sacrifice_and_equal_blessing_remain_explicit():
    _, layer = load()
    prose = layer["segments"]["s01"]["translation"]
    assert "receive the sacrifice from servants devoted to You" in prose
    assert "sanctify it with the same blessing You bestowed on the gifts of Abel" in prose
    assert prose.endswith("in the unity of the Holy Spirit, God,")
    assert layer["segments"]["s02"]["translation"] == "forever and ever."
    assert layer["segments"]["s03"]["translation"] == "Amen."


@pytest.mark.parametrize(
    "suffix,segment,printed,scan,leaf",
    [
        ("body", "s01", "pp.436–437", "PDF463–464", 462),
        ("expanded-conclusion", "s01", "p.29", "PDF56", 55),
        ("duration", "s02", "p.29", "PDF56", 55),
    ],
)
def test_body_and_expanded_formula_have_separate_historical_bases(
    suffix, segment, printed, scan, leaf
):
    graph = json.loads((CORPUS / "languages/en/bibliography.json").read_text())
    uses = [u for u in graph["uses"] if u["address"].get("text") == TEXT]
    assert len(uses) == 3
    item = next(u for u in uses if u["id"] == f"use.en.{TEXT}.{suffix}.husenbeth1853")
    assert item["address"] == {"kind": "segment", "text": TEXT, "segment": segment}
    assert item["role"] == "historical_wording_basis"
    assert item["edition"] == "edition.the-missal-for-the-use-of-the-laity-1853"
    assert item["digital_item"] == "item.missal-for-the-use-of-the-laity-1853.scan"
    assert item["evidence_sha256"] == SOURCE
    assert item["locator"]["printed"] == printed
    assert item["locator"]["scan"] == scan
    assert item["locator"]["page_url"] == (
        "https://archive.org/details/missal_for_use_of_laity_1853-f_c_husenbeth"
        f"/page/n{leaf}/mode/1up"
    )
    if suffix == "body":
        assert "does not print the expanded ending" in item["claim"]
    elif suffix == "expanded-conclusion":
        assert "our is supplied for nostrum in the selected Latin" in item["claim"]
    else:
        assert "not an exact quotation" in item["claim"]


def test_revised_historical_basis_does_not_promote_working_review():
    _, layer = load()
    provenance = json.loads((CORPUS / "languages/en/translation-provenance.json").read_text())
    rows = [r for r in provenance["sites"] if r["text"] == TEXT]
    assert len(rows) == 3
    relationships = store.translation_relationships(CORPUS, "en")
    for row in rows:
        segment = row["segment"]
        assert row["review"] == "working" and row["familiar_core"] is False
        assert row["target_sha256"] == canonical_hash(layer["segments"][segment]["translation"])
        if segment in ("s01", "s02"):
            assert row["origin"] == "public-domain"
            assert relationships[row["site"]] == "revised"
        else:
            assert segment == "s03" and row["origin"] == "trivial"
