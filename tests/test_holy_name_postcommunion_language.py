"""Keep the Postcommunion's offering, request and heavenly inscription distinct."""

import json
from copy import deepcopy

import pytest

from build_reader import store
from checks.interlinear import effective_gloss
from checks.language_packs import check_layer
from checks.layout import CORPUS
from checks.translation_provenance import canonical_hash

TEXT = "proprium.sanctissimi-nominis-iesu-postcommunio"
GROUPS = [
    ("pl", 9, 10, 9, ("wejrzyj łaskawie na", "wejrzyj miłościwie na")),
    ("pl", 34, 35, 35, ("racz przyjąć",)),
    ("pl", 45, 47, 47, ("z tytułu wiecznego przeznaczenia",)),
    ("pl", 51, 52, 51, ("są zapisane",)),
    ("en", 9, 10, 9, ("look graciously upon", "look with favor upon")),
    ("en", 11, 12, 11, ("our desires",)),
    (
        "en",
        17,
        29,
        29,
        (
            "which we have offered to Your majesty in honor of the name of Your Son, "
            "our Lord Jesus Christ",
        ),
    ),
    (
        "en",
        30,
        35,
        35,
        (
            "be pleased to receive with a serene and kindly countenance",
            "deign to receive with a serene and kindly countenance",
        ),
    ),
    ("en", 37, 40, 40, ("with Your grace poured into us",)),
    ("en", 45, 47, 47, ("the sign of eternal predestination",)),
    ("en", 49, 50, 49, ("our names",)),
    ("en", 51, 52, 51, ("are written",)),
    ("en", 56, 60, 57, ("this same Jesus Christ, our Lord", "the same Jesus Christ, our Lord")),
    ("en", 61, 62, 61, ("Your Son",)),
    ("en", 70, 71, 70, ("of the Holy Spirit",)),
    ("en", 73, 76, 75, ("forever and ever",)),
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
    assert group is not None, "A complete construction must have a caption"
    assert group["words"] == members and group["anchor"] == f"w{anchor:03d}"
    # These are contextual examples, not a claim that the schema judges prose.
    assert group["gloss"] in captions
    assert all(layer["words"][word] == {} for word in members)
    assert [effective_gloss(layer, word) for word in members if effective_gloss(layer, word)] == [
        group["gloss"]
    ]
    assert check_layer(core, layer, store.layer_path(CORPUS, language, TEXT)) == []


@pytest.mark.parametrize("case", GROUPS)
def test_each_complete_construction_is_realized_once(case):
    assert_construction(*load(case[0]), case)


@pytest.mark.parametrize("case", GROUPS)
def test_supported_alternative_captions_are_not_false_failures(case):
    core, layer = load(case[0])
    for caption in case[-1]:
        candidate = deepcopy(layer)
        group = group_for(candidate, case[1])
        assert group is not None
        group["gloss"] = caption
        assert_construction(core, candidate, case)


@pytest.mark.parametrize("language,members,groups", [("pl", 9, 4), ("en", 47, 12)])
def test_all_word_identities_and_separate_assent_remain(language, members, groups):
    core, layer = load(language)
    ids = [w["id"] for s in core["segments"] for w in s["words"]]
    assert list(layer["words"]) == ids == [f"w{i:03d}" for i in range(1, 78)]
    assert sum(value == {} for value in layer["words"].values()) == members
    assert len(layer["segments"]["s01"]["alignments"]) == groups
    assert layer["segments"]["s02"] == {"translation": "Amen."}
    assert layer["words"]["w077"] == {"gloss": "Amen"}
    assert check_layer(core, layer, store.layer_path(CORPUS, language, TEXT)) == []


def test_offering_relative_and_divine_reception_have_separate_predicates():
    _, layer = load("en")
    assert [layer["words"][f"w{i:03d}"]["gloss"] for i in range(14, 17)] == [
        "the sacrifice",
        "of the saving",
        "Victim",
    ]
    assert group_for(layer, 17)["words"] == [f"w{i:03d}" for i in range(17, 30)]
    assert group_for(layer, 30)["words"] == [f"w{i:03d}" for i in range(30, 36)]
    assert layer["words"]["w036"] == {"gloss": "that"}
    assert layer["words"]["w048"] == {"gloss": "we may rejoice that"}
    assert layer["words"]["w053"] == {"gloss": "in"}
    assert layer["words"]["w054"] == {"gloss": "heaven"}


@pytest.mark.parametrize(
    "mutation", ["missing-member", "duplicate-caption", "wrong-agent", "missing-member-help"]
)
def test_relative_clause_regressions_are_rejected(mutation):
    core, layer = load("en")
    group = group_for(layer, 17)
    assert group is not None
    if mutation == "missing-member":
        group["words"].remove("w027")
    elif mutation == "duplicate-caption":
        layer["words"]["w029"]["gloss"] = "we have offered"
    elif mutation == "wrong-agent":
        group["gloss"] = group["gloss"].replace("we have offered", "You have offered")
    else:
        del layer["words"]["w019"]
    with pytest.raises((AssertionError, KeyError)):
        assert_construction(core, layer, GROUPS[6])


def test_missing_polish_valency_carrier_is_rejected():
    core, layer = load("pl")
    assert_construction(core, layer, GROUPS[0])
    group_for(layer, 9)["gloss"] = "wejrzyj łaskawie"
    with pytest.raises(AssertionError):
        assert_construction(core, layer, GROUPS[0])


def test_polish_manner_and_content_link_do_not_change_the_received_prose():
    _, layer = load("pl")
    assert layer["words"]["w030"] == {"gloss": "z pogodnym"}
    assert layer["words"]["w048"] == {"gloss": "radowali się, że"}
    prose = layer["segments"]["s01"]["translation"]
    assert "z tytułu wiecznego przeznaczenia nasze imiona są zapisane w niebie" in prose
    assert canonical_hash(prose) == (
        "89b28f08aa8e697fc6bd5f095a6117032a2590c0681ae892634dbd624eba1fad"
    )


def test_english_is_a_request_not_an_unconditional_promise():
    _, layer = load("en")
    for word, gloss in [
        (5, "created"),
        (41, "under"),
        (63, "who"),
        (64, "with You"),
        (65, "lives"),
        (67, "reigns"),
    ]:
        assert layer["words"][f"w{word:03d}"] == {"gloss": gloss}
    prose = layer["segments"]["s01"]["translation"]
    assert "so that, with Your grace poured into us" in prose
    assert "under the glorious name of Jesus, the sign of eternal predestination" in prose
    assert "we may rejoice that our names are written in heaven" in prose
    assert prose.endswith(
        "who lives and reigns with You in the unity of the Holy Spirit, God, forever and ever."
    )


@pytest.mark.parametrize(
    "suffix,year,printed,pdf,leaf,digest",
    [
        (
            "body.husenbeth1853",
            1853,
            95,
            122,
            121,
            "64dda22f4b0753135be1112b8bd36eab7fbb9c92586c2fc2d831c0a4b7f65d8a",
        ),
        (
            "expanded-conclusion.husenbeth1853",
            1853,
            29,
            56,
            55,
            "64dda22f4b0753135be1112b8bd36eab7fbb9c92586c2fc2d831c0a4b7f65d8a",
        ),
        (
            "title-interpretation.laity1846",
            1846,
            584,
            614,
            613,
            "8e692b256e08350896902e55787f70c171a444d33e754f4d67e84fe000f81dd1",
        ),
    ],
)
def test_body_formula_and_interpretive_control_have_exact_distinct_sources(
    suffix, year, printed, pdf, leaf, digest
):
    graph = json.loads((CORPUS / "languages/en/bibliography.json").read_text())
    uses = [u for u in graph["uses"] if u["address"].get("text") == TEXT]
    assert len(uses) == 3
    use = next(u for u in uses if u["id"] == f"use.en.{TEXT}.{suffix}")
    assert use["address"] == {"kind": "segment", "text": TEXT, "segment": "s01"}
    assert use["role"] == "historical_wording_basis" and use["evidence_sha256"] == digest
    assert use["locator"]["printed"] == f"p.{printed}" and use["locator"]["scan"] == f"PDF{pdf}"
    archive = (
        "missal_for_use_of_laity_1853-f_c_husenbeth" if year == 1853 else "TheMissalForTheLaity"
    )
    assert (
        use["locator"]["page_url"] == f"https://archive.org/details/{archive}/page/n{leaf}/mode/1up"
    )


def test_revised_historical_basis_never_implies_review_approval():
    _, layer = load("en")
    provenance = json.loads((CORPUS / "languages/en/translation-provenance.json").read_text())
    rows = [r for r in provenance["sites"] if r["text"] == TEXT]
    assert len(rows) == 2
    relationships = store.translation_relationships(CORPUS, "en")
    for row in rows:
        assert row["review"] == "working" and row["familiar_core"] is False
        assert row["target_sha256"] == canonical_hash(
            layer["segments"][row["segment"]]["translation"]
        )
        if row["segment"] == "s01":
            assert row["origin"] == "public-domain" and relationships[row["site"]] == "revised"
        else:
            assert row["segment"] == "s02" and row["origin"] == "trivial"
