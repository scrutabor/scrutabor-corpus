"""Readable Latin/context controls for the two Corpus Christi English chants.

These bounded wording oracles protect edited constructions, not an automatic
semantic verdict. All negative controls damage copies of the real documents;
the same copies must pass again after exact restoration.
"""

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest
from lauda_sion_fixture import predecessor_core, predecessor_layer

ROOT = Path(__file__).resolve().parents[1]
GRADUAL = "corporis-christi-graduale"
SEQUENCE = "corporis-christi-sequentia"

# Each row is a small construction, with its actual Latin forms, case and head.
# The external preposition/governor is deliberately not swallowed by a group.
GROUPS = [
    (
        GRADUAL,
        "s01",
        ("w013", "w014"),
        "w013",
        "due time",
        ("témpore", "opportúno"),
        ("abl", "abl"),
        (None, "w013"),
    ),
    (
        GRADUAL,
        "s02",
        ("w017", "w018"),
        "w017",
        "Your hand",
        ("manum", "tuam"),
        ("acc", "acc"),
        (None, "w017"),
    ),
    (
        SEQUENCE,
        "s02",
        ("w018", "w019"),
        "w019",
        "than all praise",
        ("omni", "laude"),
        ("abl", "abl"),
        ("w019", None),
    ),
    (
        SEQUENCE,
        "s02",
        ("w020", "w021", "w022"),
        "w022",
        "nor can you praise enough",
        ("nec", "laudáre", "súfficis"),
        (None, None, None),
        (None, None, None),
    ),
    (
        SEQUENCE,
        "s03",
        ("w023", "w024", "w025"),
        "w024",
        "The theme of special praise",
        ("Laudis", "thema", "speciális"),
        ("gen", "nom", "gen"),
        (None, None, "w023"),
    ),
    (
        SEQUENCE,
        "s04",
        ("w034", "w035", "w036"),
        "w035",
        "the table of the holy supper",
        ("sacræ", "mensa", "cenæ"),
        ("gen", "abl", "gen"),
        ("w036", None, None),
    ),
    (
        SEQUENCE,
        "s04",
        ("w037", "w038", "w039"),
        "w037",
        "to the company of twelve brethren",
        ("turbæ", "fratrum", "duodénæ"),
        ("dat", "gen", "dat"),
        (None, None, "w037"),
    ),
    (
        SEQUENCE,
        "s07",
        ("w068", "w069"),
        "w069",
        "of the new King",
        ("novi", "Regis"),
        ("gen", "gen"),
        ("w069", None),
    ),
    (
        SEQUENCE,
        "s07",
        ("w072", "w073"),
        "w073",
        "of the new law",
        ("novæ", "legis"),
        ("gen", "gen"),
        ("w073", None),
    ),
    (
        SEQUENCE,
        "s10",
        ("w097", "w098"),
        "w098",
        "by sacred precepts",
        ("sacris", "institútis"),
        ("abl", "abl"),
        ("w098", None),
    ),
    (
        SEQUENCE,
        "s12",
        ("w127", "w128"),
        "w128",
        "the order of things",
        ("rerum", "órdinem"),
        ("gen", "acc"),
        (None, None),
    ),
    (
        SEQUENCE,
        "s18",
        ("w188", "w189"),
        "w189",
        "of equal reception",
        ("paris", "sumptiónis"),
        ("gen", "gen"),
        ("w189", None),
    ),
    (
        SEQUENCE,
        "s21",
        ("w232", "w233"),
        "w233",
        "not to be cast",
        ("non", "mitténdus"),
        (None, "nom"),
        (None, "w230"),
    ),
    (
        SEQUENCE,
        "s24",
        ("w285", "w286"),
        "w286",
        "of the holy citizens",
        ("sanctórum", "cívium"),
        ("gen", "gen"),
        ("w286", None),
    ),
]

PROSE = [
    (GRADUAL, "s01", "The eyes of all hope in You, O Lord, and You give them food in due season."),
    (GRADUAL, "s02", "You open Your hand and fill every living creature with blessing."),
    (
        SEQUENCE,
        "s01",
        "Praise, O Zion, your Savior; praise your Leader and Shepherd in hymns and canticles.",
    ),
    (
        SEQUENCE,
        "s02",
        "Dare as much as you can, for He is greater than all praise, "
        "and you cannot praise Him enough.",
    ),
    (
        SEQUENCE,
        "s03",
        "The theme of special praise, the living and life-giving Bread, is set forth today.",
    ),
    (
        SEQUENCE,
        "s12",
        "What you do not comprehend or see, a courageous faith confirms "
        "beyond the ordinary course of nature.",
    ),
    (
        SEQUENCE,
        "s13",
        "Beneath different appearances—different only as signs, not in reality—"
        "extraordinary realities lie hidden.",
    ),
    (
        SEQUENCE,
        "s19",
        "When at last the Sacrament is broken, do not waver, but remember: "
        "as much lies beneath the fragment as is covered by the whole.",
    ),
    (
        SEQUENCE,
        "s24",
        "You who know and can do all things, who feed us mortals here: "
        "make us there Your table companions, fellow heirs, and comrades of the holy citizens. "
        "Amen. Alleluia.",
    ),
]

# Explicit readthrough starts, not a general "capitalize every segment" rule.
STARTS = {
    GRADUAL: ("Eyes", "You open"),
    SEQUENCE: (
        "Praise",
        "As much as",
        "The theme of special praise",
        "Him",
        "Let be",
        "For a solemn day",
        "At",
        "The old",
        "What",
        "Taught",
        "A dogma",
        "What",
        "Beneath",
        "Flesh",
        "By",
        "Receives",
        "Receive",
        "Death",
        "When broken",
        "No",
        "Behold",
        "In",
        "Good",
        "You",
    ),
}
CONTINUATIONS = [
    (GRADUAL, "s01", "w007", "and"),
    (GRADUAL, "s02", "w019", "and"),
    (SEQUENCE, "s01", "w004", "praise"),
    (SEQUENCE, "s02", "w013", "you can"),
    (SEQUENCE, "s05", "w046", "let be"),
    (SEQUENCE, "s06", "w059", "which"),
    (SEQUENCE, "s12", "w120", "what"),
    (SEQUENCE, "s22", "w238", "when"),
    (SEQUENCE, "s24", "w268", "who"),
    (SEQUENCE, "s24", "w273", "who"),
]


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


@pytest.fixture
def chants():
    values = {
        short: (
            read(f"texts/proprium/{short}.json"),
            read(f"languages/en/texts/proprium/{short}.json"),
        )
        for short in (GRADUAL, SEQUENCE)
    }
    core, layer = values[SEQUENCE]
    values[SEQUENCE] = (predecessor_core(core, layer), predecessor_layer(core, layer))
    return values


def words(core, segment):
    return next(part["words"] for part in core["segments"] if part["id"] == segment)


def realizations(core, layer):
    """Reject missing/duplicate/foreign members rather than selecting first matches."""
    captions, counts = {}, Counter()
    identifiers = [word["id"] for part in core["segments"] for word in part["words"]]
    assert set(layer["words"]) == set(identifiers), "word inventory"
    for part in core["segments"]:
        order = [word["id"] for word in part["words"]]
        previous_end = -1
        for group in layer["segments"][part["id"]].get("alignments", []):
            members = group["words"]
            assert 2 <= len(members) <= 3 and len(set(members)) == len(members), "group members"
            assert all(member in order for member in members), "segment confinement"
            indices = [order.index(member) for member in members]
            assert indices == list(range(indices[0], indices[0] + len(indices))), "contiguity"
            assert indices[0] > previous_end, "group order"
            previous_end = indices[-1]
            assert group["anchor"] in members and group.get("gloss"), "realized group"
            for member in members:
                captions[member] = group["gloss"]
                counts[member] += 1
        for word in part["words"]:
            gloss = layer["words"][word["id"]].get("gloss")
            if gloss is not None:
                assert isinstance(gloss, str) and gloss, "direct caption"
                captions[word["id"]] = gloss
                counts[word["id"]] += 1
    assert counts == Counter(identifiers), "one realization per word"
    return captions


def assert_group(core, layer, row):
    _, segment, members, anchor, gloss, forms, cases, heads = row
    selected = {word["id"]: word for word in words(core, segment)}
    assert tuple(selected[member]["form"] for member in members) == forms, "Latin forms"
    actual_cases = tuple(selected[member]["morph"].get("case") for member in members)
    assert actual_cases == cases, "Latin cases"
    assert tuple(selected[member].get("head") for member in members) == heads, "Latin attachment"
    matching = [
        group
        for group in layer["segments"][segment].get("alignments", [])
        if group["words"] == list(members)
    ]
    assert matching == [{"words": list(members), "anchor": anchor, "gloss": gloss}], "construction"
    assert all("gloss" not in layer["words"][member] for member in members), "residual gloss"
    realizations(core, layer)


def assert_prose(layer, segment, expected):
    assert layer["segments"][segment]["translation"] == expected, "clause meaning"


def assert_case(core, layer):
    short = core["id"].split(".", 1)[1]
    captions = realizations(core, layer)
    actual_starts = tuple(captions[part["words"][0]["id"]] for part in core["segments"])
    assert actual_starts == STARTS[short], "sentence starts"
    for text, _, member, expected in CONTINUATIONS:
        if text == short:
            assert captions[member] == expected, "continuation"
    if short == SEQUENCE:
        assert (captions["w287"], captions["w288"]) == ("Amen", "Alleluia"), "response starts"
        assert (captions["w254"], captions["w259"], captions["w267"], captions["w278"]) == (
            "You",
            "You",
            "You",
            "Your",
        ), "divine referent"
        assert captions["w248"] == "Shepherd", "Christ title"


@pytest.mark.parametrize("row", GROUPS, ids=[f"{r[0]}-{r[1]}-{r[2][0]}" for r in GROUPS])
def test_short_constructions_keep_their_latin_government(chants, row):
    assert_group(*chants[row[0]], row)


@pytest.mark.parametrize("short,segment,expected", PROSE, ids=[f"{r[0]}-{r[1]}" for r in PROSE])
def test_complete_edited_clauses_retain_their_meaning(chants, short, segment, expected):
    assert_prose(chants[short][1], segment, expected)


@pytest.mark.parametrize("short", [GRADUAL, SEQUENCE])
def test_sentence_starts_referents_and_real_continuations(chants, short):
    assert_case(*chants[short])


def test_every_word_is_realized_once_without_losing_the_original_scope(chants):
    assert [
        (len(core["segments"]), len(realizations(core, layer))) for core, layer in chants.values()
    ] == [(2, 23), (24, 288)]
    assert (
        sum(
            len(part.get("alignments", []))
            for _, layer in chants.values()
            for part in layer["segments"].values()
        )
        == 20
    )


def test_single_gerundive_negation_and_correlative_neither_nor(chants):
    core, layer = chants[SEQUENCE]
    row = next(row for row in GROUPS if row[2] == ("w232", "w233"))
    assert_group(core, layer, row)
    verb = next(word for word in words(core, "s21") if word["id"] == "w233")
    assert {key: verb["morph"][key] for key in ("mood", "tense", "voice", "case")} == {
        "mood": "part",
        "tense": "fut",
        "voice": "pass",
        "case": "nom",
    }
    assert verb["lemma"] == "mitto" and verb["head"] == "w230"
    assert (layer["words"]["w217"]["gloss"], layer["words"]["w219"]["gloss"]) == ("neither", "nor")


def test_comparison_adequacy_and_savior_referent(chants):
    core, layer = chants[SEQUENCE]
    name = next(word for word in words(core, "s01") if word["id"] == "w002")
    assert (name["form"], name["lemma"]) == ("Sion", "Sion")
    assert layer["words"]["w002"]["gloss"] == "Zion"
    source = {word["id"]: word for word in words(core, "s02")}
    assert source["w017"]["morph"]["degree"] == "comp"
    assert (source["w021"]["morph"]["mood"], source["w022"]["lemma"]) == ("inf", "sufficio")
    assert layer["words"]["w017"]["explanation"] == (
        "“Greater” describes the Savior praised in the preceding stanza. "
        "The subject and verb are understood: “for He is greater than all praise.”"
    )


def test_company_agreement_and_means_of_instruction_are_not_doubled(chants):
    core, layer = chants[SEQUENCE]
    source = {word["id"]: word for part in core["segments"] for word in part["words"]}
    assert {key: source["w039"]["morph"][key] for key in ("case", "number", "gender")} == {
        "case": "dat",
        "number": "sg",
        "gender": "f",
    }
    assert source["w039"]["head"] == "w037"
    assert source["w096"]["lemma"] == "doceo"
    assert {key: source["w096"]["morph"][key] for key in ("mood", "tense", "voice")} == {
        "mood": "part",
        "tense": "perf",
        "voice": "pass",
    }
    for member in ("w097", "w098"):
        assert {key: source[member]["morph"][key] for key in ("case", "number", "gender")} == {
            "case": "abl",
            "number": "pl",
            "gender": "n",
        }
    captions = realizations(core, layer)
    assert captions["w096"] == "Taught" and captions["w097"] == "by sacred precepts"


def assert_sign_and_reality(core, layer):
    source = {word["id"]: word for part in core["segments"] for word in part["words"]}
    assert tuple(source[word]["lemma"] for word in ("w130", "w132", "w136", "w138")) == (
        "diversus",
        "signum",
        "res",
        "res",
    )
    assert source["w130"]["head"] == "w131"
    assert source["w149"]["lemma"] == "uterque" and source["w149"]["morph"]["number"] == "sg"
    assert (layer["words"]["w132"]["gloss"], layer["words"]["w136"]["gloss"]) == (
        "in signs",
        "in reality",
    ), "sign/reality contrast"
    assert_prose(layer, "s13", next(row[2] for row in PROSE if row[:2] == (SEQUENCE, "s13")))
    assert_prose(
        layer,
        "s14",
        "The Flesh is food and the Blood is drink; "
        "yet Christ remains whole beneath either species.",
    )


def test_sign_difference_does_not_make_christ_merely_symbolic_or_partial(chants):
    assert_sign_and_reality(*chants[SEQUENCE])


@pytest.mark.parametrize(
    "damage",
    [
        "comparison",
        "adequacy",
        "double-negative",
        "omit-non",
        "duplicate-member",
        "wrong-anchor",
        "foreign-member",
        "residual-gloss",
        "displaced-modifier",
        "double-of",
        "gerundive-force",
    ],
)
def test_damaged_construction_fails_and_the_same_copy_recovers(chants, damage):
    rows = {row[2][0]: row for row in GROUPS if row[0] == SEQUENCE}
    first = {
        "comparison": "w018",
        "adequacy": "w020",
        "displaced-modifier": "w034",
        "double-of": "w068",
    }.get(damage, "w232")
    row = rows[first]
    core, original = chants[SEQUENCE]
    changed = deepcopy(original)
    assert_group(core, changed, row)
    group = next(
        group
        for group in changed["segments"][row[1]]["alignments"]
        if group["words"] == list(row[2])
    )
    if damage == "comparison":
        group["gloss"] = "all praise"
    elif damage == "adequacy":
        group["gloss"] = "nor can you praise"
    elif damage == "double-negative":
        changed["segments"][row[1]]["alignments"].remove(group)
        changed["words"]["w232"]["gloss"] = "not"
        changed["words"]["w233"]["gloss"] = "not to be cast"
    elif damage == "omit-non":
        group["words"].remove("w232")
    elif damage == "duplicate-member":
        group["words"].append("w232")
    elif damage == "wrong-anchor":
        group["anchor"] = "w232"
    elif damage == "foreign-member":
        group["words"].append("w239")
    elif damage == "residual-gloss":
        changed["words"]["w232"]["gloss"] = "not"
    elif damage == "displaced-modifier":
        group["words"] = ["w033", "w034", "w035"]
    elif damage == "double-of":
        group["gloss"] = "of new of the King"
    else:
        group["gloss"] = "not cast"
    with pytest.raises(AssertionError, match=r"construction|residual gloss"):
        assert_group(core, changed, row)
    changed.clear()
    changed.update(deepcopy(original))
    assert changed == original
    assert_group(core, changed, row)


@pytest.mark.parametrize("damage", ["initial", "continuation", "human-you", "divine-you", "amen"])
def test_case_damage_fails_and_the_same_copy_recovers(chants, damage):
    core, original = chants[SEQUENCE]
    changed = deepcopy(original)
    member, value = {
        "initial": ("w001", "praise"),
        "continuation": ("w268", "Who"),
        "human-you": ("w013", "You can"),
        "divine-you": ("w278", "your"),
        "amen": ("w287", "amen"),
    }[damage]
    assert_case(core, changed)
    changed["words"][member]["gloss"] = value
    diagnostic = "sentence starts|continuation|divine referent|response starts"
    with pytest.raises(AssertionError, match=diagnostic):
        assert_case(core, changed)
    changed.clear()
    changed.update(deepcopy(original))
    assert changed == original
    assert_case(core, changed)


@pytest.mark.parametrize("damage", ["merely-symbolic", "different-christs", "missing-contrast"])
def test_presence_contrast_damage_fails_and_the_same_copy_recovers(chants, damage):
    core, original = chants[SEQUENCE]
    changed = deepcopy(original)
    assert_sign_and_reality(core, changed)
    if damage == "merely-symbolic":
        changed["segments"]["s13"]["translation"] = (
            "Beneath the appearances are only symbols, not realities."
        )
    elif damage == "different-christs":
        changed["segments"]["s14"]["translation"] = (
            "Different parts of Christ remain beneath the two species."
        )
    else:
        changed["words"]["w136"]["gloss"] = "realities"
    with pytest.raises(AssertionError, match=r"clause meaning|sign/reality contrast"):
        assert_sign_and_reality(core, changed)
    changed.clear()
    changed.update(deepcopy(original))
    assert changed == original
    assert_sign_and_reality(core, changed)
