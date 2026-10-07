"""Keep selected English possessives in complete, source-bound constituents.

These are reviewed local fixtures, not a rule that every Latin possessive
requires a group. Nonlocal constructions have separately reviewed contracts.
"""

import hashlib
import json
from copy import deepcopy
from itertools import pairwise

import pytest

from checks.interlinear import check, effective_gloss
from checks.language_packs import check_layer
from checks.layout import CORPUS

# slug, segment, first member, last member, analysis anchor, selected realization
SITES = [
    ("apostolorum", "s03", 14, 15, 14, "Your flock"),
    ("apostolorum", "s03", 22, 24, 23, "Your blessed Apostles"),
    ("apostolorum", "s05", 56, 57, 56, "of Your glory"),
    ("ascensionis", "s02", 24, 25, 24, "our Lord"),
    ("ascensionis", "s02", 28, 29, 28, "His resurrection"),
    ("ascensionis", "s02", 30, 32, 31, "to all His disciples"),
    ("ascensionis", "s02", 65, 66, 65, "of Your glory"),
    ("beatae-mariae-virginis-in-annuntiatione", "s05", 36, 37, 36, "Your only-begotten Son"),
    ("beatae-mariae-virginis-in-annuntiatione", "s05", 52, 53, 52, "our Lord"),
    ("beatae-mariae-virginis-in-annuntiatione", "s06", 56, 57, 56, "Your majesty"),
    ("beatae-mariae-virginis-in-assumptione", "s05", 36, 37, 36, "Your only-begotten Son"),
    ("beatae-mariae-virginis-in-assumptione", "s05", 52, 53, 52, "our Lord"),
    ("beatae-mariae-virginis-in-assumptione", "s06", 56, 57, 56, "Your majesty"),
    (
        "beatae-mariae-virginis-in-conceptione-immaculata",
        "s05",
        37,
        38,
        37,
        "Your only-begotten Son",
    ),
    ("beatae-mariae-virginis-in-conceptione-immaculata", "s05", 53, 54, 53, "our Lord"),
    ("beatae-mariae-virginis-in-conceptione-immaculata", "s06", 57, 58, 57, "Your majesty"),
    ("beatae-mariae-virginis-in-nativitate", "s05", 36, 37, 36, "Your only-begotten Son"),
    ("beatae-mariae-virginis-in-nativitate", "s05", 52, 53, 52, "our Lord"),
    ("beatae-mariae-virginis-in-nativitate", "s06", 56, 57, 56, "Your majesty"),
    ("beatae-mariae-virginis-in-transfixione", "s05", 36, 37, 36, "Your only-begotten Son"),
    ("beatae-mariae-virginis-in-transfixione", "s05", 52, 53, 52, "our Lord"),
    ("beatae-mariae-virginis-in-transfixione", "s06", 56, 57, 56, "Your majesty"),
    ("beatae-mariae-virginis-in-visitatione", "s05", 36, 37, 36, "Your only-begotten Son"),
    ("beatae-mariae-virginis-in-visitatione", "s05", 52, 53, 52, "our Lord"),
    ("beatae-mariae-virginis-in-visitatione", "s06", 56, 57, 56, "Your majesty"),
    ("beatae-mariae-virginis", "s05", 36, 37, 36, "Your only-begotten Son"),
    ("beatae-mariae-virginis", "s05", 52, 53, 52, "our Lord"),
    ("beatae-mariae-virginis", "s06", 56, 57, 56, "Your majesty"),
    ("communis", "s03", 24, 25, 24, "our Lord"),
    ("communis", "s04", 28, 29, 28, "Your majesty"),
    ("d-n-iesu-christi-regis", "s04", 23, 25, 24, "Your only-begotten Son"),
    ("d-n-iesu-christi-regis", "s04", 26, 27, 26, "our Lord"),
    ("d-n-iesu-christi-regis", "s05", 95, 96, 95, "of Your glory"),
    ("defunctorum", "s03", 24, 25, 24, "our Lord"),
    ("defunctorum", "s06", 79, 80, 79, "of Your glory"),
    ("epiphaniae", "s04", 24, 25, 24, "Your only-begotten Son"),
    ("epiphaniae", "s05", 53, 54, 53, "of Your glory"),
    ("nativitatis", "s05", 62, 63, 62, "of Your glory"),
    ("paschalis-in-die", "s01", 37, 38, 37, "our death"),
    ("paschalis-in-die", "s01", 61, 62, 61, "of Your glory"),
    ("paschalis-in-nocte", "s01", 37, 38, 37, "our death"),
    ("paschalis-in-nocte", "s01", 61, 62, 61, "of Your glory"),
    ("quadragesimae", "s04", 35, 36, 35, "our Lord"),
    ("quadragesimae", "s05", 39, 40, 39, "Your majesty"),
    ("sacratissimi-cordis-iesu", "s04", 23, 24, 23, "Your only-begotten Son"),
    ("sacratissimi-cordis-iesu", "s05", 75, 76, 75, "of Your glory"),
    ("sanctae-crucis", "s04", 48, 49, 48, "our Lord"),
    ("sanctae-crucis", "s05", 52, 53, 52, "Your majesty"),
    ("sancti-ioseph-in-festivitate", "s05", 51, 52, 51, "Your household"),
    ("sancti-ioseph-in-festivitate", "s05", 56, 57, 56, "Your only-begotten Son"),
    ("sancti-ioseph-in-festivitate", "s05", 67, 68, 67, "our Lord"),
    ("sancti-ioseph-in-festivitate", "s06", 71, 72, 71, "Your majesty"),
    ("sancti-ioseph-in-solemnitate", "s05", 51, 52, 51, "Your household"),
    ("sancti-ioseph-in-solemnitate", "s05", 56, 57, 56, "Your only-begotten Son"),
    ("sancti-ioseph-in-solemnitate", "s05", 67, 68, 67, "our Lord"),
    ("sancti-ioseph-in-solemnitate", "s06", 71, 72, 71, "Your majesty"),
    ("sanctissimae-trinitatis", "s04", 24, 26, 25, "Your only-begotten Son"),
    ("sanctissimae-trinitatis", "s05", 55, 57, 56, "about Your Son"),
    ("spiritus-sancti", "s02", 24, 25, 24, "our Lord"),
    ("spiritus-sancti", "s02", 33, 34, 33, "Your right hand"),
    ("spiritus-sancti", "s02", 61, 62, 61, "of Your glory"),
]
SLUGS = sorted({site[0] for site in SITES})
NONLOCAL_PAIRS = {
    ("apostolorum", "w034"),
    ("ascensionis", "w045"),
    ("epiphaniae", "w034"),
    ("nativitatis", "w029"),
    ("paschalis-in-die", "w023"),
    ("paschalis-in-nocte", "w023"),
}
# Reviewed clause word objects and intersecting alignments. These replace the
# earlier held-payload controls after complete-clause repair, not by deletion.
CLAUSE_CONTROLS = [
    (
        "apostolorum",
        "s04",
        28,
        39,
        "a4d8f72927e09eb7fa4e5b6e02babe4f997f30fd45831197d24cd7a9fa9fd204",
    ),
    (
        "ascensionis",
        "s02",
        42,
        48,
        "d1a2b566df44f2021554fb98fd8372689a3b050792fb2490b51a9476628ddda1",
    ),
    (
        "epiphaniae",
        "s04",
        31,
        36,
        "b4e4519466860779f9971b20daaa1594f3e0b148be2351f8af0e10df9b87d50b",
    ),
    (
        "nativitatis",
        "s04",
        27,
        34,
        "77a843f1c82c708c971ab0ede4f6f3aa16547c67f763d98d85d84ef9b977d918",
    ),
    (
        "paschalis-in-die",
        "s01",
        21,
        26,
        "f4301b47a5eaa354f389360e0b69ae665bce1eb25f65bb8b647b4abf686cd1db",
    ),
    (
        "paschalis-in-nocte",
        "s01",
        21,
        26,
        "f4301b47a5eaa354f389360e0b69ae665bce1eb25f65bb8b647b4abf686cd1db",
    ),
    (
        "d-n-iesu-christi-regis",
        "s04",
        53,
        57,
        "eb42ca77fdef2d6cf41147a6ed7fa24037932d93ee044bef9022a30570e86fd2",
    ),
    (
        "d-n-iesu-christi-regis",
        "s04",
        58,
        65,
        "6ea338ccb44ed4c113db789ad4647a148409e2489907f4718409904be277dc6d",
    ),
]
PATTERNS = {
    "our Lord": {("dominus", "noster")},
    "of Your glory": {("gloria", "tuus")},
    "Your majesty": {("maiestas", "tuus")},
    "Your flock": {("grex", "tuus")},
    "Your blessed Apostles": {("beatus", "apostolus", "tuus")},
    "His resurrection": {("resurrectio", "suus")},
    "to all His disciples": {("omnis", "discipulus", "suus")},
    "Your only-begotten Son": {("unigenitus", "tuus"), ("unigenitus", "filius", "tuus")},
    "our death": {("mors", "noster")},
    "Your household": {("familia", "tuus")},
    "Your right hand": {("dextera", "tuus")},
    "about Your Son": {("de", "filius", "tuus")},
}


def ids(first, last):
    return [f"w{i:03}" for i in range(first, last + 1)]


def load(slug):
    name = "praefatio-" + slug + ".json"
    doc = json.loads((CORPUS / "texts/ordinarium" / name).read_text())
    layer = json.loads((CORPUS / "languages/en/texts/ordinarium" / name).read_text())
    return doc, layer


def accepted(gloss):
    # Both explicitly reviewed subject-matter renderings are sound. Do not
    # encode a preference for about over of as a universal correctness rule.
    return {gloss, "of Your Son"} if gloss == "about Your Son" else {gloss}


def assert_site(doc, layer, site):
    _slug, segment, first, last, anchor, gloss = site
    members = ids(first, last)
    words = next(s["words"] for s in doc["segments"] if s["id"] == segment)
    positions = {w["id"]: i for i, w in enumerate(words)}
    chosen = [words[positions[wid]] for wid in members]
    assert [positions[wid] for wid in members] == list(
        range(positions[members[0]], positions[members[0]] + len(members))
    )
    assert tuple(w["lemma"] for w in chosen) in PATTERNS[gloss]
    possessive, head = chosen[-1], chosen[-2]
    assert possessive["head"] == head["id"]
    assert possessive["morph"]["pos"] == "adj"
    assert all(
        possessive["morph"][key] == head["morph"][key] for key in ("case", "number", "gender")
    )
    groups = layer["segments"][segment].get("alignments", [])
    touching = [g for g in groups if set(g["words"]) & set(members)]
    assert len(touching) == 1
    group = touching[0]
    assert set(group) == {"words", "anchor", "gloss"}
    assert group["words"] == members
    assert group["anchor"] == f"w{anchor:03}"
    assert group["gloss"] in accepted(gloss)
    assert all(wid in layer["words"] and "gloss" not in layer["words"][wid] for wid in members)
    assert [
        (wid, effective_gloss(layer, wid)) for wid in members if effective_gloss(layer, wid)
    ] == [(group["anchor"], group["gloss"])]


def protected_payload(layer, slug):
    """Remove only the selected new fields; retain even unexpected overlaps."""
    value = deepcopy(layer)
    for site in (s for s in SITES if s[0] == slug):
        _slug, segment, first, last, anchor, gloss = site
        members = ids(first, last)
        entry = value["segments"][segment]
        entry["alignments"] = [
            group
            for group in entry.get("alignments", [])
            if not (
                set(group) == {"words", "anchor", "gloss"}
                and group["words"] == members
                and group["anchor"] == f"w{anchor:03}"
                and group["gloss"] in accepted(gloss)
            )
        ]
        if not entry["alignments"]:
            entry.pop("alignments")
        for wid in members:
            value["words"][wid].pop("gloss", None)
    return value


def clause_payload(layer, segment, first, last):
    members = ids(first, last)
    return {
        "words": {wid: layer["words"][wid] for wid in members},
        "groups": [
            g
            for g in layer["segments"][segment].get("alignments", [])
            if set(g["words"]) & set(members)
        ],
    }


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def test_population_distinguishes_selected_and_nonlocal_pairs():
    found = set()
    for slug in SLUGS:
        doc, _ = load(slug)
        for segment in doc["segments"]:
            words = segment.get("words", [])
            for prior, word in pairwise(words):
                if (
                    word["lemma"] in {"tuus", "noster", "suus"}
                    and word["morph"]["pos"] == "adj"
                    and word.get("head") == prior["id"]
                ):
                    found.add((slug, word["id"]))
    selected = {(slug, f"w{last:03}") for slug, _, _, last, _, _ in SITES}
    assert len(SLUGS) == 23
    assert len(SITES) == len(selected) == 61
    assert selected.isdisjoint(NONLOCAL_PAIRS)
    assert len(found) == 67 and found == selected | NONLOCAL_PAIRS
    assert sum(last - first + 1 for _, _, first, last, _, _ in SITES) == 127


@pytest.mark.parametrize("site", SITES)
def test_selected_possessive_is_realized_once(site):
    doc, layer = load(site[0])
    assert_site(doc, layer, site)


@pytest.mark.parametrize("slug", SLUGS)
def test_full_layer_keeps_required_word_objects_and_valid_existing_groups(slug):
    doc, layer = load(slug)
    assert list(layer["words"]) == [w["id"] for s in doc["segments"] for w in s.get("words", [])]
    path = CORPUS / "languages/en/texts/ordinarium" / ("praefatio-" + slug + ".json")
    assert check_layer(doc, layer, path) == []
    assert check(doc, layer) == []


@pytest.mark.parametrize("slug,segment,first,last,expected", CLAUSE_CONTROLS)
def test_reviewed_clause_control_is_preserved(slug, segment, first, last, expected):
    _, layer = load(slug)
    assert digest(clause_payload(layer, segment, first, last)) == expected


def test_preposed_petitions_and_requiem_group_remain_separate():
    petitions = 0
    for slug in SLUGS:
        doc, layer = load(slug)
        for segment in doc["segments"]:
            words = segment.get("words", [])
            if any(w["lemma"] == "iubeo" for w in words):
                groups = layer["segments"][segment["id"]]["alignments"]
                assert [len(g["words"]) for g in groups] == [9, 3]
                assert [g["anchor"] for g in groups] == [words[8]["id"], words[11]["id"]]
                petitions += 1
    assert petitions == 12
    _, layer = load("defunctorum")
    group = next(g for g in layer["segments"]["s05"]["alignments"] if "w044" in g["words"])
    assert group == {
        "words": ["w044", "w045", "w046"],
        "anchor": "w046",
        "gloss": "For to Your faithful",
    }


def test_supported_subject_matter_alternative():
    site = next(s for s in SITES if s[0] == "sanctissimae-trinitatis" and s[2] == 55)
    doc, before = load(site[0])
    after = deepcopy(before)
    group = next(g for g in after["segments"][site[1]]["alignments"] if g["words"] == ids(55, 57))
    group["gloss"] = "of Your Son"
    assert_site(doc, after, site)
    assert check(doc, after) == []
    assert protected_payload(before, site[0]) == protected_payload(after, site[0])


@pytest.mark.parametrize("site", SITES)
def test_direct_gloss_reintroduction_is_rejected(site):
    doc, layer = load(site[0])
    layer["words"][f"w{site[3]:03}"]["gloss"] = "Your"
    assert any("exactly one" in error for error in check(doc, layer))
    with pytest.raises(AssertionError):
        assert_site(doc, layer, site)


@pytest.mark.parametrize("site", SITES)
def test_overlapping_realization_is_rejected(site):
    doc, layer = load(site[0])
    groups = layer["segments"][site[1]]["alignments"]
    group = next(g for g in groups if g["words"] == ids(site[2], site[3]))
    groups.append(deepcopy(group))
    assert any("overlap" in error or "more than one" in error for error in check(doc, layer))
    with pytest.raises(AssertionError):
        assert_site(doc, layer, site)


@pytest.mark.parametrize("mutation", ["reverse", "omit", "anchor", "empty", "marker", "zero"])
def test_malformed_constituent_is_rejected(mutation):
    site = SITES[0]
    doc, layer = load(site[0])
    group = next(
        g for g in layer["segments"][site[1]]["alignments"] if g["words"] == ids(site[2], site[3])
    )
    if mutation == "reverse":
        group["words"].reverse()
    elif mutation == "omit":
        group["words"].pop()
    elif mutation == "anchor":
        group["anchor"] = "w001"
    elif mutation == "empty":
        group["gloss"] = ""
    elif mutation == "marker":
        group["gloss"] = "[included]"
    else:
        group["reason"] = "word-order"
    assert check(doc, layer)
    with pytest.raises(AssertionError):
        assert_site(doc, layer, site)


@pytest.mark.parametrize("gloss", ["from Your Son", "about our Son", "about Your sons"])
def test_trinity_relation_or_referent_mutations_are_rejected(gloss):
    site = next(s for s in SITES if s[0] == "sanctissimae-trinitatis" and s[2] == 55)
    doc, layer = load(site[0])
    group = next(g for g in layer["segments"][site[1]]["alignments"] if g["words"] == ids(55, 57))
    group["gloss"] = gloss
    assert check(doc, layer) == []  # Shape alone cannot settle meaning.
    with pytest.raises(AssertionError):
        assert_site(doc, layer, site)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-word",
        "word-order",
        "prose",
        "note",
        "other-gloss",
        "existing-group",
        "unexpected-overlap",
        "top-level",
    ],
)
def test_protected_payload_mutations_are_not_hidden(mutation):
    slug = "communis"
    doc, before = load(slug)
    after = deepcopy(before)
    if mutation == "missing-word":
        del after["words"]["w024"]
    elif mutation == "word-order":
        after["words"] = dict(reversed(list(after["words"].items())))
    elif mutation == "prose":
        after["segments"]["s03"]["translation"] += " Changed."
    elif mutation == "note":
        after["words"]["w052"]["explanation"] += " Changed."
    elif mutation == "other-gloss":
        after["words"]["w001"]["gloss"] = "changed"
    elif mutation == "existing-group":
        after["segments"]["s06"]["alignments"][0]["gloss"] = "Changed."
    elif mutation == "unexpected-overlap":
        after["segments"]["s03"]["alignments"].append(
            {"words": ["w023", "w024"], "anchor": "w024", "gloss": "Christ our Lord"}
        )
    else:
        after["about"] += " Changed."
    if mutation in {"missing-word", "word-order"}:
        path = CORPUS / "languages/en/texts/ordinarium/praefatio-communis.json"
        assert any("word coverage or order" in e for e in check_layer(doc, after, path))
    else:
        assert protected_payload(before, slug) != protected_payload(after, slug)


@pytest.mark.parametrize("slug,segment,first,last,expected", CLAUSE_CONTROLS)
def test_reviewed_clause_mutation_is_detected(slug, segment, first, last, expected):
    _, layer = load(slug)
    layer["words"][f"w{first:03}"]["gloss"] = "changed"
    assert digest(clause_payload(layer, segment, first, last)) != expected
