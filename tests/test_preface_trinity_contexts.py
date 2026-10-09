"""Guard the selected Trinity constructions, not universal lexical equivalents."""

import hashlib
import json
from copy import deepcopy
from typing import Any

import pytest
from preface_glory_fixture import (
    EN_AFTER,
    current_english_rows,
    restore_glory_core,
    restore_glory_layer,
)

from checks.interlinear import check, effective_gloss
from checks.language_packs import check_layer
from checks.layout import CORPUS, formatted
from checks.translation_provenance import canonical_hash, source_payload

# Exact selected fields and whole-layer inverses keep unrelated payload intact.
FIXTURES: dict[str, Any] = {
    "text": "ordinarium.praefatio-sanctissimae-trinitatis",
    "name": "praefatio-sanctissimae-trinitatis.json",
    # Covers the s01 hand rubric (lower-case præfationis, p. 225) and the edition name.
    "core_digest": "75402b28b2a921eb3067334659750ae19ea37d0f0ae8ae7c21682f5c07fb343c",
    "groups": {
        "pl": [
            {
                "segment": "s04",
                "words": ["w038", "w039", "w040"],
                "anchor": "w039",
                "gloss": "pojedynczości jednej osoby",
            },
            {
                "segment": "s04",
                "words": ["w043", "w044", "w045"],
                "anchor": "w044",
                "gloss": "Trójcy jednej istoty",
            },
        ],
        "en": [
            {
                "segment": "s02",
                "words": ["w010", "w011", "w012", "w013", "w014", "w015"],
                "anchor": "w015",
                "gloss": "always and everywhere give thanks to You",
            },
            {
                "segment": "s04",
                "words": ["w028", "w029"],
                "anchor": "w028",
                "gloss": "the Holy Spirit",
            },
            {
                "segment": "s04",
                "words": ["w030", "w031", "w032"],
                "anchor": "w031",
                "gloss": "are one God",
            },
            {
                "segment": "s04",
                "words": ["w033", "w034", "w035"],
                "anchor": "w034",
                "gloss": "are one Lord",
            },
            {
                "segment": "s04",
                "words": ["w038", "w039", "w040"],
                "anchor": "w039",
                "gloss": "the singleness of one Person",
            },
            {
                "segment": "s04",
                "words": ["w043", "w044", "w045"],
                "anchor": "w044",
                "gloss": "the Trinity of one substance",
            },
            {
                "segment": "s05",
                "words": ["w060", "w061"],
                "anchor": "w060",
                "gloss": "the Holy Spirit",
            },
            {
                "segment": "s06",
                "words": ["w069", "w070", "w071"],
                "anchor": "w071",
                "gloss": "of the true and eternal Godhead",
            },
            {
                "segment": "s06",
                "words": ["w083", "w084"],
                "anchor": "w083",
                "gloss": "equality may be adored",
            },
            {
                "segment": "s07",
                "words": ["w086", "w087", "w088", "w089", "w090", "w091", "w092", "w093"],
                "anchor": "w086",
                "gloss": "the Angels and Archangels, and also the Cherubim and Seraphim, praise",
            },
            {
                "segment": "s07",
                "words": ["w095", "w096"],
                "anchor": "w096",
                "gloss": "do not cease",
            },
            {
                "segment": "s07",
                "words": ["w099", "w100"],
                "anchor": "w100",
                "gloss": "with one voice",
            },
        ],
    },
    "baselines": {
        "pl": {
            "before_sha256": "e1ab8cb0d6b659c69a2f342f43a926f33a7e0b9c6dd36f5a05cbde4213c6b6e4",
            "before_digest": "6bb535a02a210965c2b01a044f728f4dee0adca25962d425a1cdbfbad1983270",
            "words": {
                "w038": {"gloss": "jednej"},
                "w039": {"gloss": "pojedynczości"},
                "w040": {"gloss": "osoby"},
                "w043": {"gloss": "jednej"},
                "w044": {"gloss": "Trójcy"},
                "w045": {"gloss": "istoty"},
                "w046": {"gloss": "które"},
                "w053": {"gloss": "wierzymy"},
                "w065": {"gloss": "pojmujemy"},
            },
            "groups": {"s01": [], "s02": [], "s03": [], "s04": [], "s05": [], "s06": [], "s07": []},
        },
        "en": {
            "before_sha256": "063a0f8000361af8e011c8ef145b4125c4f6a5a2e426eb2246dddc55d5bd03d1",
            "before_digest": "18e85ee11ea180a304e4b1061d83781ad4fa87f13e29b71b7a5fb1ae6f03fdf0",
            "words": {
                "w002": {"gloss": "right"},
                "w003": {"gloss": "and"},
                "w004": {"gloss": "just"},
                "w005": {"gloss": "is"},
                "w010": {"gloss": "to You"},
                "w011": {"gloss": "always"},
                "w012": {"gloss": "and"},
                "w013": {"gloss": "everywhere"},
                "w014": {"gloss": "thanks"},
                "w015": {"gloss": "give"},
                "w028": {"gloss": "Spirit"},
                "w029": {"gloss": "Holy"},
                "w030": {"gloss": "one"},
                "w031": {"gloss": "are"},
                "w032": {"gloss": "God"},
                "w033": {"gloss": "one"},
                "w034": {"gloss": "are"},
                "w035": {"gloss": "the Lord"},
                "w038": {"gloss": "of one"},
                "w039": {"gloss": "oneness"},
                "w040": {"gloss": "of a person"},
                "w043": {"gloss": "of one"},
                "w044": {"gloss": "Trinity"},
                "w045": {"gloss": "substance"},
                "w060": {"gloss": "Spirit"},
                "w061": {"gloss": "Holy"},
                "w069": {"gloss": "of the true"},
                "w070": {"gloss": "and eternal"},
                "w071": {"gloss": "of the Godhead"},
                "w072": {"gloss": "and"},
                "w083": {"gloss": "may be adored"},
                "w084": {"gloss": "equality"},
                "w086": {"gloss": "praise"},
                "w087": {"gloss": "Angels"},
                "w088": {"gloss": "and"},
                "w089": {"gloss": "Archangels"},
                "w090": {"gloss": "the Cherubim"},
                "w091": {"gloss": "also"},
                "w092": {"gloss": "and"},
                "w093": {"gloss": "Seraphim"},
                "w095": {"gloss": "not"},
                "w096": {"gloss": "cease"},
                "w099": {"gloss": "one"},
                "w100": {"gloss": "voice"},
            },
            "groups": {
                "s01": [],
                "s02": [],
                "s03": [],
                "s04": [
                    {
                        "words": ["w024", "w025", "w026"],
                        "anchor": "w025",
                        "gloss": "Your only-begotten Son",
                    }
                ],
                "s05": [
                    {"words": ["w046", "w047"], "anchor": "w046", "gloss": "For what"},
                    {"words": ["w051", "w052"], "anchor": "w051", "gloss": "by Your revelation"},
                    {
                        "words": ["w055", "w056", "w057"],
                        "anchor": "w056",
                        "gloss": "of Your Son",
                    },
                ],
                "s06": [],
                "s07": [],
            },
        },
    },
    "zero": {"segment": "s06", "words": ["w072"], "reason": "idiom"},
    "direct": {"w046": "co", "w053": "przyjmujemy za prawdę", "w065": "uznajemy za prawdę"},
    "prose": {
        "segment": "s05",
        "before": "Co bowiem dzięki Twemu objawieniu wierzymy o Twojej chwale, to samo "
        "pojmujemy o Twoim Synu i to samo o Duchu Świętym, bez różnicy wynikającej z "
        "odrębności.",
        "after": "Co bowiem dzięki Twemu objawieniu przyjmujemy za prawdę o Twojej chwale, to "
        "samo uznajemy za prawdę o Twoim Synu i to samo o Duchu Świętym, nie czyniąc "
        "przy tym żadnej różnicy.",
    },
    "provenance_before": [
        {
            "site": "ordinarium.praefatio-sanctissimae-trinitatis.s02.pl",
            "text": "ordinarium.praefatio-sanctissimae-trinitatis",
            "segment": "s02",
            "language": "pl",
            "familiar_core": False,
            "origin": "working-unsettled",
            "review": "working",
            "source_sha256": "8c9076f9752b55e10487dbe93eb61de015c356ae49ffb7c930053593857d82f1",
            "target_sha256": "8b16aca5cbe5be40c86d1f38668e2aa9f6e22b41d00d095832ecb228295d7e87",
        },
        {
            "site": "ordinarium.praefatio-sanctissimae-trinitatis.s03.pl",
            "text": "ordinarium.praefatio-sanctissimae-trinitatis",
            "segment": "s03",
            "language": "pl",
            "familiar_core": False,
            "origin": "own",
            "review": "working",
            "source_sha256": "3664aac9ffe6561f3ab0e02c52162da9571225025e57eae1f12e9571c0ef9875",
            "target_sha256": "91a37ef371475266fbc80c8ca9040ef241c487d8790358e7f912b94c3e791d3e",
        },
        {
            "site": "ordinarium.praefatio-sanctissimae-trinitatis.s04.pl",
            "text": "ordinarium.praefatio-sanctissimae-trinitatis",
            "segment": "s04",
            "language": "pl",
            "familiar_core": False,
            "origin": "working-unsettled",
            "review": "working",
            "source_sha256": "6a4e75f69ee37b55f3009b60744102dd888cf3760043c031728d055353d707bb",
            "target_sha256": "26d10fbf1bd2d5f76d85b79c945b2a5970b2decbcbc2f04e49f8f0b175bed101",
        },
        {
            "site": "ordinarium.praefatio-sanctissimae-trinitatis.s05.pl",
            "text": "ordinarium.praefatio-sanctissimae-trinitatis",
            "segment": "s05",
            "language": "pl",
            "familiar_core": False,
            "origin": "own",
            "review": "internally-reviewed",
            "source_sha256": "88d4fe9af744ad39978d27b4f8f6e137fd42d0cea4205ff8b89f551165587bd3",
            "target_sha256": "3a10998f24df7df7621d43315a8728c71368687d0788b6e7931e2fa4de21addd",
        },
        {
            "site": "ordinarium.praefatio-sanctissimae-trinitatis.s06.pl",
            "text": "ordinarium.praefatio-sanctissimae-trinitatis",
            "segment": "s06",
            "language": "pl",
            "familiar_core": False,
            "origin": "own",
            "review": "internally-reviewed",
            "source_sha256": "dffd54f73569fddef503d0ef0da7f36b2f1ca28205f8546b4f4a57fabe8ca4c5",
            "target_sha256": "f14842523f2db1832b2e3ec9f5bf998fc0e7c6a15701b8901218cb921361c8bf",
        },
        {
            "site": "ordinarium.praefatio-sanctissimae-trinitatis.s07.pl",
            "text": "ordinarium.praefatio-sanctissimae-trinitatis",
            "segment": "s07",
            "language": "pl",
            "familiar_core": False,
            "origin": "working-unsettled",
            "review": "working",
            "source_sha256": "f7e87b11f9f8ec4ab1d8c6c3c5491ceed9122c6790e0738e5c01a1fd23ca7927",
            "target_sha256": "a1e1b7f1651189f53ad0fe72e061052ebb783e88a6e7c879f2e73c89ffc8ec08",
        },
    ],
    "english_provenance": [
        {
            "site": "ordinarium.praefatio-sanctissimae-trinitatis.s02.en",
            "text": "ordinarium.praefatio-sanctissimae-trinitatis",
            "segment": "s02",
            "language": "en",
            "familiar_core": False,
            "origin": "own",
            "review": "internally-reviewed",
            "source_sha256": "8c9076f9752b55e10487dbe93eb61de015c356ae49ffb7c930053593857d82f1",
            "target_sha256": "c34c943f2192bfa2999b49a06a34335d2202b8eac2a010677488aa919dc01f66",
        },
        {
            "site": "ordinarium.praefatio-sanctissimae-trinitatis.s03.en",
            "text": "ordinarium.praefatio-sanctissimae-trinitatis",
            "segment": "s03",
            "language": "en",
            "familiar_core": False,
            "origin": "own",
            "review": "working",
            "source_sha256": "3664aac9ffe6561f3ab0e02c52162da9571225025e57eae1f12e9571c0ef9875",
            "target_sha256": "c5716b9311e977322382fc0faabbacd2dc0e70f578302155d99a3dd92a86d350",
        },
        {
            "site": "ordinarium.praefatio-sanctissimae-trinitatis.s04.en",
            "text": "ordinarium.praefatio-sanctissimae-trinitatis",
            "segment": "s04",
            "language": "en",
            "familiar_core": False,
            "origin": "working-unsettled",
            "review": "working",
            "source_sha256": "6a4e75f69ee37b55f3009b60744102dd888cf3760043c031728d055353d707bb",
            "target_sha256": "d359faf697b2dc33041bcbf727a8270cc1b34aaa257b36884028a1399693abce",
        },
        {
            "site": "ordinarium.praefatio-sanctissimae-trinitatis.s05.en",
            "text": "ordinarium.praefatio-sanctissimae-trinitatis",
            "segment": "s05",
            "language": "en",
            "familiar_core": False,
            "origin": "own",
            "review": "internally-reviewed",
            "source_sha256": "88d4fe9af744ad39978d27b4f8f6e137fd42d0cea4205ff8b89f551165587bd3",
            "target_sha256": "211bb5426c165670683385a1e09ad3236040ac51a015f0fe46951a3e8056ddfa",
        },
        {
            "site": "ordinarium.praefatio-sanctissimae-trinitatis.s06.en",
            "text": "ordinarium.praefatio-sanctissimae-trinitatis",
            "segment": "s06",
            "language": "en",
            "familiar_core": False,
            "origin": "working-unsettled",
            "review": "working",
            "source_sha256": "dffd54f73569fddef503d0ef0da7f36b2f1ca28205f8546b4f4a57fabe8ca4c5",
            "target_sha256": "c929b1088b99bf6136e8828aaadb9f3bff83320a843688246025c094c2f487b5",
        },
        {
            "site": "ordinarium.praefatio-sanctissimae-trinitatis.s07.en",
            "text": "ordinarium.praefatio-sanctissimae-trinitatis",
            "segment": "s07",
            "language": "en",
            "familiar_core": False,
            "origin": "own",
            "review": "working",
            "source_sha256": "f7e87b11f9f8ec4ab1d8c6c3c5491ceed9122c6790e0738e5c01a1fd23ca7927",
            "target_sha256": "16c8150a5aa170f9e79877c948275f2b15de0d263229984ef9728d79bd4111ff",
        },
    ],
    "target_hash": "6191ca961d7105a0cf032f15e704a455b89c658aab264b96e8403dba74d9815f",
}

GROUPS = FIXTURES["groups"]
BASELINES = FIXTURES["baselines"]
ZERO = FIXTURES["zero"]
DIRECT = FIXTURES["direct"]
PROSE = FIXTURES["prose"]
SITES = [(language, group) for language, groups in GROUPS.items() for group in groups]


def load(language):
    core = json.loads((CORPUS / "texts/ordinarium" / FIXTURES["name"]).read_text())
    path = CORPUS / f"languages/{language}/texts/ordinarium" / FIXTURES["name"]
    return core, json.loads(path.read_text())


def group_value(site):
    return {key: deepcopy(value) for key, value in site.items() if key != "segment"}


def touching(layer, site):
    return [
        group
        for group in layer["segments"][site["segment"]].get("alignments", [])
        if set(group["words"]) & set(site["words"])
    ]


def supported(site):
    # A reviewed alternative is not the currently selected editorial spelling.
    values = {site["gloss"]}
    if site["gloss"] == "the singleness of one Person":
        values.add("the oneness of one Person")
    return values


def assert_group(core, layer, site, *, alternatives=False):
    groups = touching(layer, site)
    assert len(groups) == 1
    group = groups[0]
    assert set(group) == {"words", "anchor", "gloss"}
    assert group["words"] == site["words"] and group["anchor"] == site["anchor"]
    assert group["gloss"] in (supported(site) if alternatives else {site["gloss"]})
    words = next(s["words"] for s in core["segments"] if s["id"] == site["segment"])
    positions = [next(i for i, w in enumerate(words) if w["id"] == wid) for wid in site["words"]]
    assert positions == list(range(positions[0], positions[0] + len(positions)))
    assert all(w in layer["words"] and "gloss" not in layer["words"][w] for w in site["words"])
    assert [(w, effective_gloss(layer, w)) for w in site["words"] if effective_gloss(layer, w)] == [
        (group["anchor"], group["gloss"])
    ]


def assert_zero(layer):
    assert touching(layer, ZERO) == [group_value(ZERO)]
    assert "w072" in layer["words"] and "gloss" not in layer["words"]["w072"]
    assert effective_gloss(layer, "w072") == ""
    # Its correlative role survives in the three-member enumeration, not a
    # general permission to suppress either conjunction or a theological noun.
    for wid, gloss in {
        "w075": "distinction",
        "w076": "and",
        "w079": "unity",
        "w080": "and",
    }.items():
        assert layer["words"][wid]["gloss"] == gloss


def prepare(layer, language):
    """A selected fixture for counterexamples, not a validator of live data."""
    result = deepcopy(layer)
    for site in GROUPS[language] + ([ZERO] if language == "en" else []):
        entry = result["segments"][site["segment"]]
        entry["alignments"] = [
            g for g in entry.get("alignments", []) if not set(g["words"]) & set(site["words"])
        ]
        entry["alignments"].append(group_value(site))
        entry["alignments"].sort(key=lambda g: g["words"][0])
        for wid in site["words"]:
            result["words"][wid].pop("gloss", None)
    if language == "pl":
        for wid, value in DIRECT.items():
            result["words"][wid]["gloss"] = value
        result["segments"]["s05"]["translation"] = PROSE["after"]
    return result


def restore(core, layer, language, *, alternatives=False):
    """Reverse exactly the selected fields; preserve every unexpected field."""
    result = restore_glory_layer(layer, language)
    assert list(result["words"]) == [w["id"] for s in core["segments"] for w in s.get("words", [])]
    for site in GROUPS[language]:
        assert_group(core, result, site, alternatives=alternatives)
        result["segments"][site["segment"]]["alignments"].remove(touching(result, site)[0])
        for wid in site["words"]:
            result["words"][wid]["gloss"] = BASELINES[language]["words"][wid]["gloss"]
    if language == "en":
        assert_zero(result)
        result["segments"]["s06"]["alignments"].remove(group_value(ZERO))
        result["words"]["w072"]["gloss"] = BASELINES["en"]["words"]["w072"]["gloss"]
    else:
        for wid, value in DIRECT.items():
            assert result["words"][wid]["gloss"] == value
            result["words"][wid]["gloss"] = BASELINES["pl"]["words"][wid]["gloss"]
        assert result["segments"]["s05"]["translation"] == PROSE["after"]
        result["segments"]["s05"]["translation"] = PROSE["before"]
    for sid, original in BASELINES[language]["groups"].items():
        current = result["segments"][sid]
        assert current.get("alignments", []) == original
        if not original:
            current.pop("alignments", None)
    assert (
        hashlib.sha256(formatted(result).encode()).hexdigest()
        == BASELINES[language]["before_sha256"]
    )
    return result


SUPPORTED_GOVERNMENT = {
    ("co", "przyjmujemy za prawdę", "uznajemy za prawdę"),
    ("w co", "wierzymy", "uznajemy za prawdę"),
    ("w co", "wierzymy", "sądzimy"),
}
FORMAL_PROSE = (
    "To bowiem, w co dzięki Twemu objawieniu wierzymy o Twojej chwale, "
    "uznajemy również za prawdę o Twoim Synu i o Duchu Świętym, nie czyniąc żadnej różnicy."
)


def assert_supported_polish(layer, prose):
    """Finite contextual alternatives, not a general Polish grammar engine."""
    assert (
        tuple(layer["words"][w]["gloss"] for w in ("w046", "w053", "w065")) in SUPPORTED_GOVERNMENT
    )
    assert layer["words"]["w054"]["gloss"] == layer["words"]["w058"]["gloss"] == "to samo"
    assert layer["words"]["w051"]["gloss"] == "dzięki objawieniu"
    assert layer["words"]["w052"]["gloss"] == "Twojemu"
    assert prose in {PROSE["after"], FORMAL_PROSE}


def expected_records():
    result = deepcopy(FIXTURES["provenance_before"])
    row = next(r for r in result if r["segment"] == "s05")
    row["target_sha256"] = canonical_hash(PROSE["after"])
    row["review"] = "working"
    return result


def assert_provenance(core, layer, records, english_records):
    assert records == expected_records()
    assert english_records == current_english_rows(FIXTURES["english_provenance"])
    row = next(r for r in records if r["segment"] == "s05")
    segment = next(s for s in core["segments"] if s["id"] == "s05")
    assert row["source_sha256"] == canonical_hash(source_payload(segment))
    assert row["target_sha256"] == canonical_hash(layer["segments"]["s05"]["translation"])
    assert row["target_sha256"] == FIXTURES["target_hash"]
    assert row["origin"] == "own" and row["review"] == "working" and row["familiar_core"] is False


def test_exact_bounded_population():
    assert len(GROUPS["en"]) == 12 and sum(len(g["words"]) for g in GROUPS["en"]) == 39
    assert len(GROUPS["pl"]) == 2 and sum(len(g["words"]) for g in GROUPS["pl"]) == 6
    assert len(BASELINES["en"]["words"]) == 44 and len(BASELINES["pl"]["words"]) == 9
    assert sum(len(g) for g in BASELINES["en"]["groups"].values()) == 4
    assert sum(len(v["words"]) for g in BASELINES["en"]["groups"].values() for v in g) == 10
    assert set(DIRECT) == {"w046", "w053", "w065"} and ZERO["words"] == ["w072"]


def test_latin_relations_and_all_source_objects_remain_exact():
    core, _ = load("en")
    assert canonical_hash(restore_glory_core(core)) == FIXTURES["core_digest"]
    words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    assert len(words) == 101
    for adjective, noun in (("w038", "w040"), ("w043", "w045")):
        assert words[adjective]["head"] == noun
        assert words[adjective]["morph"]["case"] == words[noun]["morph"]["case"] == "gen"
    assert words["w051"]["head"] == "w052" and words["w051"]["morph"]["voice"] == "act"
    assert words["w052"]["morph"]["case"] == "abl"
    assert all(words[w]["morph"]["case"] == "nom" for w in ("w075", "w079", "w084"))
    assert words["w083"]["morph"]["voice"] == "pass"
    assert words["w085"]["morph"]["case"] == "acc" and words["w086"]["morph"]["voice"] == "act"
    assert all(words[w]["morph"]["case"] == "nom" for w in ("w087", "w089", "w090", "w093"))


@pytest.mark.parametrize("language,site", SITES)
def test_selected_group_has_one_complete_realization(language, site):
    core, layer = load(language)
    assert_group(core, layer, site)


def test_initial_correlative_has_only_its_declared_zero():
    _, layer = load("en")
    assert_zero(layer)


@pytest.mark.parametrize("wid,value", DIRECT.items())
def test_selected_polish_direct_gloss(wid, value):
    _, layer = load("pl")
    assert layer["words"][wid]["gloss"] == value


@pytest.mark.parametrize("language", ["pl", "en"])
def test_complete_layer_restores_to_exact_prechange_bytes(language):
    core, layer = load(language)
    restore(core, layer, language)
    path = CORPUS / f"languages/{language}/texts/ordinarium" / FIXTURES["name"]
    assert check(core, layer) == [] and check_layer(core, layer, path) == []
    assert formatted(layer) == path.read_text()


def test_selected_polish_prose_and_revelation_relation():
    _, layer = load("pl")
    assert layer["segments"]["s05"]["translation"] == PROSE["after"]
    assert layer["segments"]["s05"]["translation"].count("to samo") == 2
    assert_supported_polish(layer, layer["segments"]["s05"]["translation"])


def test_provenance_preserves_the_two_bounded_target_revisions():
    core, layer = load("pl")

    def sites(language):
        data = json.loads(
            (CORPUS / f"languages/{language}/translation-provenance.json").read_text()
        )
        return [r for r in data["sites"] if r["text"] == FIXTURES["text"]]

    assert_provenance(core, layer, sites("pl"), sites("en"))


@pytest.mark.parametrize("language,site", SITES)
@pytest.mark.parametrize(
    "mutation", ["duplicate", "missing-member", "order", "anchor", "direct", "missing-object"]
)
def test_structural_mutations_are_rejected(language, site, mutation):
    core, original = load(language)
    layer = prepare(original, language)
    group = touching(layer, site)[0]
    if mutation == "duplicate":
        layer["segments"][site["segment"]]["alignments"].append(deepcopy(group))
    elif mutation == "missing-member":
        group["words"].remove(site["words"][-1])
    elif mutation == "order":
        group["words"].reverse()
    elif mutation == "anchor":
        group["anchor"] = "w101"
    elif mutation == "direct":
        layer["words"][site["words"][0]]["gloss"] = "again"
    else:
        del layer["words"][site["words"][0]]
    assert check(core, layer) or check_layer(core, layer, CORPUS / "fixture.json")
    with pytest.raises((AssertionError, KeyError)):
        restore(core, layer, language)


@pytest.mark.parametrize(
    "mutation", ["reason", "gloss", "anchor", "drop", "direct", "next-and", "subject"]
)
def test_zero_is_not_a_license_to_erase_another_unit(mutation):
    core, old = load("en")
    layer = prepare(old, "en")
    zero = touching(layer, ZERO)[0]
    if mutation == "reason":
        zero["reason"] = "word-order"
    elif mutation == "gloss":
        zero["gloss"] = "and"
    elif mutation == "anchor":
        zero["anchor"] = "w072"
    elif mutation == "drop":
        layer["segments"]["s06"]["alignments"].remove(zero)
    elif mutation == "direct":
        layer["words"]["w072"]["gloss"] = "and"
    elif mutation == "next-and":
        layer["words"]["w076"]["gloss"] = ""
    else:
        layer["words"]["w075"]["gloss"] = ""
    with pytest.raises((AssertionError, KeyError)):
        restore(core, layer, "en")


SEMANTIC_MUTATIONS = [
    ("en", "w038", "one singleness of a Person"),
    ("en", "w043", "one Trinity of substances"),
    ("pl", "w038", "jednej pojedynczości osoby"),
    ("pl", "w043", "jednej Trójcy istoty"),
    ("en", "w083", "equality may adore"),
    ("en", "w083", "only equality may be adored"),
    ("en", "w095", "cease"),
    ("en", "w099", "with many voices"),
    ("en", "w030", "is one God"),
]
for order in ("Angels", "Archangels", "Cherubim", "Seraphim"):
    SEMANTIC_MUTATIONS.append(
        (
            "en",
            "w086",
            "the Angels and Archangels, and also the Cherubim and Seraphim, praise".replace(
                order, ""
            ),
        )
    )


@pytest.mark.parametrize("language,first,gloss", SEMANTIC_MUTATIONS)
def test_shape_correct_semantic_counterexamples_are_rejected(language, first, gloss):
    core, old = load(language)
    layer = prepare(old, language)
    site = next(s for s in GROUPS[language] if s["words"][0] == first)
    touching(layer, site)[0]["gloss"] = gloss
    assert check(core, layer) == []
    with pytest.raises(AssertionError):
        restore(core, layer, language)


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize(
    "mutation", ["prose", "note", "word", "about", "status", "order", "existing", "extra"]
)
def test_unselected_payload_cannot_be_masked_by_restoration(language, mutation):
    core, old = load(language)
    layer = prepare(old, language)
    if mutation == "prose":
        layer["segments"]["s07"]["translation"] += " Changed."
    elif mutation == "note":
        layer["words"]["w038"]["explanation"] = "Changed."
    elif mutation == "word":
        layer["words"]["w001"]["gloss"] += " Changed."
    elif mutation == "about":
        layer["about"] += " Changed."
    elif mutation == "status":
        layer["status"] = "accepted"
    elif mutation == "order":
        layer["words"]["w001"] = layer["words"].pop("w001")
    elif mutation == "existing":
        if language == "en":
            layer["segments"]["s05"]["alignments"][1]["gloss"] = "by our revelation"
        else:
            layer["words"]["w054"]["gloss"] = "something else"
    else:
        layer["segments"]["s06"].setdefault("alignments", []).append(
            {"words": ["w075"], "reason": "idiom"}
        )
    with pytest.raises((AssertionError, KeyError)):
        restore(core, layer, language)


@pytest.mark.parametrize(
    "before,after",
    [
        ("przyjmujemy za prawdę", "wiemy"),
        ("uznajemy za prawdę", "czujemy"),
        ("dzięki Twemu objawieniu", "dzięki temu, że Cię objawiono"),
        ("to samo o Duchu", "coś innego o Duchu"),
        ("nie czyniąc przy tym żadnej różnicy", "negując wszelką odrębność Osób"),
    ],
)
def test_polish_prose_sense_and_scope_counterexamples(before, after):
    _, original = load("pl")
    layer = prepare(original, "pl")
    changed = PROSE["after"].replace(before, after)
    assert changed != PROSE["after"]
    with pytest.raises(AssertionError):
        assert_supported_polish(layer, changed)


@pytest.mark.parametrize(
    "field,value",
    [
        ("origin", "working-unsettled"),
        ("review", "internally-reviewed"),
        ("familiar_core", True),
        ("source_sha256", "0" * 64),
        ("target_sha256", "0" * 64),
    ],
)
def test_provenance_changes_cannot_promote_or_misbind_the_paragraph(field, value):
    core, old = load("pl")
    layer = prepare(old, "pl")
    records = expected_records()
    next(r for r in records if r["segment"] == "s05")[field] = value
    with pytest.raises(AssertionError):
        assert_provenance(
            core, layer, records, current_english_rows(FIXTURES["english_provenance"])
        )


def test_every_other_provenance_site_rejects_unsupported_promotion():
    core, old = load("pl")
    layer = prepare(old, "pl")
    english = current_english_rows(FIXTURES["english_provenance"])
    for language, original in (("pl", expected_records()), ("en", english)):
        for index, row in enumerate(original):
            if language == "pl" and row["segment"] == "s05":
                continue
            changed = deepcopy(original)
            changed[index]["review"] = "accepted"
            pl = changed if language == "pl" else expected_records()
            en = changed if language == "en" else english
            with pytest.raises(AssertionError):
                assert_provenance(core, layer, pl, en)


def test_supported_oneness_alternative_is_not_a_semantic_ban():
    core, old = load("en")
    layer = prepare(old, "en")
    site = next(s for s in GROUPS["en"] if s["words"][0] == "w038")
    touching(layer, site)[0]["gloss"] = "the oneness of one Person"
    assert_group(core, layer, site, alternatives=True)
    restore(core, layer, "en", alternatives=True)


@pytest.mark.parametrize("triple", sorted(SUPPORTED_GOVERNMENT))
def test_formal_polish_alternatives_are_not_automatically_errors(triple):
    _, old = load("pl")
    layer = prepare(old, "pl")
    for wid, gloss in zip(("w046", "w053", "w065"), triple, strict=True):
        layer["words"][wid]["gloss"] = gloss
    assert_supported_polish(layer, FORMAL_PROSE)


def test_unchanged_formal_english_and_polish_antecedent_are_retained():
    _, en = load("en")
    _, pl = load("pl")
    assert en["words"]["w048"]["gloss"] == en["words"]["w059"]["gloss"] == "of"
    assert en["words"]["w065"]["gloss"] == "we understand"
    assert en["segments"]["s05"]["translation"] == EN_AFTER
    assert pl["segments"]["s07"]["translation"].startswith("Tę równość")
