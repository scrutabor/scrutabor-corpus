"""Keep the Collect's relative, naming and mediation constructions complete.

These are context-specific examples, not a rule that every occurrence of a
relative pronoun or possessive must use one of these English or Polish words.
"""

import json
from copy import deepcopy

import pytest

from build_reader import store
from checks.interlinear import effective_gloss
from checks.language_packs import check_layer
from checks.layout import CORPUS
from checks.translation_provenance import canonical_hash

TEXT = "proprium.sanctissimi-nominis-iesu-collecta"
SOURCE = "64dda22f4b0753135be1112b8bd36eab7fbb9c92586c2fc2d831c0a4b7f65d8a"
GROUPS = [
    ("pl", 17, 22, 20, ("my, którzy czcimy na ziemi Jego święte imię",)),
    ("pl", 23, 26, 26, ("cieszyli się także oglądaniem Go",)),
    ("en", 3, 6, 6, ("appointed Your only-begotten Son",)),
    ("en", 7, 9, 9, ("as Savior of the human race", "as the Savior of the human race")),
    ("en", 11, 13, 13, ("commanded that He be called Jesus", "commanded Him to be called Jesus")),
    ("en", 17, 22, 20, ("we who venerate His holy name on earth",)),
    ("en", 23, 26, 26, ("may also enjoy the sight of Him", "may also rejoice in beholding Him")),
    ("en", 30, 34, 31, ("this same Jesus Christ, our Lord", "the same Jesus Christ, our Lord")),
    ("en", 35, 36, 35, ("Your Son",)),
    ("en", 44, 45, 44, ("of the Holy Spirit",)),
    ("en", 47, 50, 49, ("forever and ever",)),
]


def load(language):
    return store.core(CORPUS, TEXT), store.raw_layer(CORPUS, language, TEXT)


def group_for(layer, first):
    return next(
        (
            g
            for g in layer["segments"]["s01"].get("alignments", [])
            if f"w{first:03d}" in g["words"]
        ),
        None,
    )


def assert_construction(core, layer, case):
    language, first, last, anchor, captions = case
    members = [f"w{i:03d}" for i in range(first, last + 1)]
    group = group_for(layer, first)
    assert group is not None, "The complete construction needs one caption"
    assert group["words"] == members and group["anchor"] == f"w{anchor:03d}"
    assert group["gloss"] in captions
    assert all(layer["words"][word] == {} for word in members)
    assert [effective_gloss(layer, word) for word in members if effective_gloss(layer, word)] == [
        group["gloss"]
    ]
    assert check_layer(core, layer, store.layer_path(CORPUS, language, TEXT)) == []


@pytest.mark.parametrize("case", GROUPS)
def test_complete_construction_is_realized_once(case):
    assert_construction(*load(case[0]), case)


@pytest.mark.parametrize("case", GROUPS)
def test_grammatical_alternatives_are_not_false_failures(case):
    core, layer = load(case[0])
    for caption in case[-1]:
        candidate = deepcopy(layer)
        group = group_for(candidate, case[1])
        assert group is not None
        group["gloss"] = caption
        assert_construction(core, candidate, case)


@pytest.mark.parametrize("language,members,groups", [("pl", 13, 3), ("en", 33, 9)])
def test_all_fifty_one_study_identities_and_separate_assent_remain(language, members, groups):
    core, layer = load(language)
    assert list(layer["words"]) == [w["id"] for s in core["segments"] for w in s["words"]]
    assert len(layer["words"]) == 51
    assert sum(value == {} for value in layer["words"].values()) == members
    assert len(layer["segments"]["s01"]["alignments"]) == groups
    assert layer["segments"]["s02"] == {"translation": "Amen."}
    assert layer["words"]["w051"] == {"gloss": "Amen"}
    assert check_layer(core, layer, store.layer_path(CORPUS, language, TEXT)) == []


@pytest.mark.parametrize("language", ["pl", "en"])
def test_heaven_belongs_to_enjoyment_not_to_earthly_veneration(language):
    _, layer = load(language)
    assert group_for(layer, 17)["words"][-1] == "w022"
    assert group_for(layer, 23)["words"][-1] == "w026"
    assert layer["words"]["w027"]["gloss"] == ("w" if language == "pl" else "in")
    assert layer["words"]["w028"]["gloss"] == ("niebie" if language == "pl" else "heaven")


@pytest.mark.parametrize(
    "mutation", ["missing-member", "duplicate-gloss", "wrong-referent", "missing-word"]
)
def test_relative_construction_regressions_are_rejected(mutation):
    case = GROUPS[5]
    core, layer = load("en")
    group = group_for(layer, 17)
    assert group is not None
    if mutation == "missing-member":
        group["words"].remove("w022")
    elif mutation == "duplicate-gloss":
        layer["words"]["w017"]["gloss"] = "whose"
    elif mutation == "wrong-referent":
        group["gloss"] = "we who venerate our holy name on earth"
    else:
        del layer["words"]["w017"]
    # The referent is a contextual fixture assertion, not schema inference.
    with pytest.raises((AssertionError, KeyError)):
        assert_construction(core, layer, case)


def test_conclusion_keeps_present_tense_and_contemporary_address():
    _, layer = load("en")
    for word, caption in (
        ("w037", "who"),
        ("w038", "with You"),
        ("w039", "lives"),
        ("w041", "reigns"),
    ):
        assert layer["words"][word] == {"gloss": caption}
    prose = layer["segments"]["s01"]["translation"]
    assert "commanded Him to be called Jesus" in prose
    assert (
        "we who venerate His holy name on earth may also enjoy the sight of Him in heaven" in prose
    )
    assert "Through this same Jesus Christ, our Lord, Your Son" in prose
    assert prose.endswith(
        "who lives and reigns with You in the unity of the Holy Spirit, God, forever and ever."
    )


@pytest.mark.parametrize(
    "suffix,printed,scan,leaf",
    [("body", "p.93", "PDF120", 119), ("expanded-conclusion", "p.29", "PDF56", 55)],
)
def test_body_and_conclusion_name_their_separate_historical_basis(suffix, printed, scan, leaf):
    graph = json.loads((CORPUS / "languages/en/bibliography.json").read_text())
    uses = [use for use in graph["uses"] if use["address"].get("text") == TEXT]
    assert len(uses) == 2
    use = next(use for use in uses if use["id"] == f"use.en.{TEXT}.{suffix}.husenbeth1853")
    assert use["address"] == {"kind": "segment", "text": TEXT, "segment": "s01"}
    assert use["role"] == "historical_wording_basis"
    assert use["edition"] == "edition.the-missal-for-the-use-of-the-laity-1853"
    assert use["digital_item"] == "item.missal-for-the-use-of-the-laity-1853.scan"
    assert use["evidence_sha256"] == SOURCE
    assert use["locator"]["printed"] == printed and use["locator"]["scan"] == scan
    assert use["locator"]["page_url"] == (
        f"https://archive.org/details/missal_for_use_of_laity_1853-f_c_husenbeth/page/n{leaf}/mode/1up"
    )


def test_revised_historical_origin_is_not_review_approval():
    _, layer = load("en")
    provenance = json.loads((CORPUS / "languages/en/translation-provenance.json").read_text())
    rows = [row for row in provenance["sites"] if row["text"] == TEXT]
    assert len(rows) == 2
    relationships = store.translation_relationships(CORPUS, "en")
    for row in rows:
        assert row["review"] == "working" and row["familiar_core"] is False
        assert row["target_sha256"] == canonical_hash(
            layer["segments"][row["segment"]]["translation"]
        )
        if row["segment"] == "s01":
            assert row["origin"] == "public-domain"
            assert relationships[row["site"]] == "revised"
        else:
            assert row["segment"] == "s02" and row["origin"] == "trivial"
