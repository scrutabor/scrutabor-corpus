"""Guard two contextual Polish preface readings, not universal case translations."""

import hashlib
import json
from copy import deepcopy
from typing import Any

import pytest

from checks.interlinear import check, effective_gloss
from checks.language_packs import check_layer
from checks.layout import CORPUS, formatted
from checks.translation_provenance import canonical_hash, source_payload

# Whole-layer restoration protects every unselected field. Supported contextual
# alternatives below are separate from the exact selected editorial wording.
FIXTURES: dict[str, Any] = {
    "direct": {
        "apostolorum": {
            "w014": "trzody",
            "w015": "Twej",
            "w022": "błogosławionych",
            "w024": "Twych",
        },
        "defunctorum": {"w044": "Twoim", "w046": "wiernym", "w048": "życie"},
    },
    "group": {
        "words": ["w025", "w026", "w027"],
        "anchor": "w027",
        "gloss": "otaczał ją nieustanną opieką",
    },
    "baselines": {
        "apostolorum": {
            "segment": "s03",
            "before_sha256": "6a4acdb7276d7297aba3eb726098a3c8c6340ca136a10be3d8db343f0aae74c2",
            # Covers the s01 hand rubric (lower-case præfationis, p. 225) and the edition name.
            "core_digest": "cdaf030f35949c5efc3084da616d7c5e15c8950e021a38749eea1b4a401b0263",
            "english_digest": "16eca2ad6f9d3a24ed41061f98610d26b80000b6eeca0b929013564b5a23defb",
            "words": {
                "w014": {"gloss": "trzodę"},
                "w015": {"gloss": "Twą"},
                "w022": {"gloss": "błogosławione"},
                "w024": {"gloss": "Twe"},
                "w025": {"gloss": "nieustanną"},
                "w026": {"gloss": "opieką"},
                "w027": {"gloss": "zachowywał"},
            },
            "context": {
                "w009": "Ciebie",
                "w010": "Panie",
                "w011": "błagalnie",
                "w012": "błagać",
                "w013": "abyś",
                "w014": "trzodę",
                "w015": "Twą",
                "w016": "Pasterzu",
                "w017": "wieczny",
                "w018": "nie",
                "w019": "opuszczał",
                "w020": "lecz",
                "w021": "przez",
                "w022": "błogosławione",
                "w023": "Apostołów",
                "w024": "Twe",
                "w025": "nieustanną",
                "w026": "opieką",
                "w027": "zachowywał",
            },
            "provenance": {
                "site": "ordinarium.praefatio-apostolorum.s03.pl",
                "text": "ordinarium.praefatio-apostolorum",
                "segment": "s03",
                "language": "pl",
                "familiar_core": False,
                "origin": "working-unsettled",
                "review": "working",
                "source_sha256": "e9ed5c6104014df99d705873f135d5776f35ccb90f07a6d3e031fbfa8e1c8ce3",
                "target_sha256": "d115e6f50ee1473d4c4cf0ece9c9b7b9b635b88a54ca66d4db0019b0edd31b4e",
            },
            "prose": (
                "Ciebie, Panie, pokornie błagać, abyś, Pasterzu wieczny, nie opuszczał swojej "
                "trzody, lecz przez swoich błogosławionych Apostołów strzegł jej nieustanną osłoną:"
            ),
            "complete_core_words": 61,
        },
        "defunctorum": {
            "segment": "s05",
            "before_sha256": "393e9002e25378b23669a34f3c179ebe45f799ad1c4cc501e7145779326e5496",
            # Covers the s01 hand rubric (lower-case præfationis, p. 225) and the edition name.
            "core_digest": "9680fdba10efaee8be16101f3da6cd2412aace184136335788307a55457be4d2",
            "english_digest": "c438ebaa034fc9a948f33dfe748d5e15dbcaaaf5d8f1b10c425d89d270aa3c10",
            "words": {
                "w044": {"gloss": "Twoich"},
                "w046": {"gloss": "wiernych"},
                "w048": {"gloss": "Życie"},
            },
            "context": {
                "w044": "Twoich",
                "w045": "bowiem",
                "w046": "wiernych",
                "w047": "Panie",
                "w048": "Życie",
                "w049": "zmienia się",
                "w050": "nie",
                "w051": "zostaje odebrane",
                "w052": "i",
                "w053": "gdy się rozpadnie",
                "w054": "ziemskiego",
                "w055": "tego",
                "w056": "pobytu",
                "w057": "dom",
                "w058": "wieczne",
                "w059": "w",
                "w060": "niebie",
                "w061": "mieszkanie",
                "w062": "jest przygotowane",
            },
            "provenance": {
                "site": "ordinarium.praefatio-defunctorum.s05.pl",
                "text": "ordinarium.praefatio-defunctorum",
                "segment": "s05",
                "language": "pl",
                "familiar_core": False,
                "origin": "working-unsettled",
                "review": "working",
                "source_sha256": "97b75d97377b3fc836973b30a286d9a3d60fcc43a37bb992a4ac208ce163d747",
                "target_sha256": "12b450bceb619caeb82e5a3920c4d0ace64265a3f65458e23ce5365f6be75286",
            },
            "prose": (
                "Twoim wiernym bowiem, Panie, życie zostaje zmienione, a nie odebrane, "
                "i gdy rozpadnie się dom tego ziemskiego pobytu, zostaje im przygotowane "
                "wieczne mieszkanie w niebiosach."
            ),
            "complete_core_words": 84,
        },
    },
}
DIRECT = FIXTURES["direct"]
GROUP = FIXTURES["group"]
BASELINES = FIXTURES["baselines"]
SLUGS = sorted(BASELINES)
SITES = [(slug, wid, gloss) for slug, words in DIRECT.items() for wid, gloss in words.items()]


def load(slug):
    name = "praefatio-" + slug + ".json"
    core = json.loads((CORPUS / "texts/ordinarium" / name).read_text())
    pl = json.loads((CORPUS / "languages/pl/texts/ordinarium" / name).read_text())
    en = json.loads((CORPUS / "languages/en/texts/ordinarium" / name).read_text())
    return core, pl, en


def prepare(layer, slug):
    """Create an explicit selected fixture for independent mutation controls."""
    result = deepcopy(layer)
    for wid, gloss in DIRECT[slug].items():
        result["words"][wid]["gloss"] = gloss
    if slug == "apostolorum":
        result["segments"]["s03"]["alignments"] = [deepcopy(GROUP)]
        for wid in GROUP["words"]:
            result["words"][wid].pop("gloss", None)
    return result


def assert_group(core, layer):
    segment = next(s for s in core["segments"] if s["id"] == "s03")
    assert [w["id"] for w in segment["words"]][-3:] == GROUP["words"]
    touching = [
        group
        for group in layer["segments"]["s03"].get("alignments", [])
        if set(group["words"]) & set(GROUP["words"])
    ]
    assert touching == [GROUP]
    assert all(w in layer["words"] and "gloss" not in layer["words"][w] for w in GROUP["words"])
    assert [
        (w, effective_gloss(layer, w)) for w in GROUP["words"] if effective_gloss(layer, w)
    ] == [("w027", GROUP["gloss"])]
    assert check(core, layer) == []


def assert_context(core, layer, slug):
    """Finite reviewed alternatives, not an automatic Polish grammar judge."""
    assert check(core, layer) == []
    current = {w: layer["words"][w].get("gloss") for w in BASELINES[slug]["context"]}
    expected = BASELINES[slug]["context"] | DIRECT[slug]
    if slug == "apostolorum":
        for wid in ("w015", "w024", *GROUP["words"]):
            del current[wid]
            del expected[wid]
        assert current == expected
        assert layer["words"]["w015"]["gloss"] in {"Twej", "Twojej"}
        assert layer["words"]["w024"]["gloss"] in {"Twych", "Twoich"}
        if layer["segments"]["s03"].get("alignments"):
            assert_group(core, layer)
        else:
            assert layer["words"]["w025"]["gloss"] == "nieustanną"
            assert layer["words"]["w026"]["gloss"] == "opieką"
            assert layer["words"]["w027"]["gloss"] in {"strzegł", "ją zachowywał"}
    else:
        for wid in ("w044", "w046"):
            del current[wid]
            del expected[wid]
        assert current == expected
        # A fronted genitive possessor is licensed; the dative is our clarity
        # choice, not a rule requiring the target language to copy Latin case.
        assert (layer["words"]["w044"]["gloss"], layer["words"]["w046"]["gloss"]) in {
            ("Twoim", "wiernym"),
            ("Twoich", "wiernych"),
        }


def assert_protected(core, layer, slug):
    restored = deepcopy(layer)
    assert list(restored["words"]) == [
        w["id"] for segment in core["segments"] for w in segment.get("words", [])
    ]
    for wid, gloss in DIRECT[slug].items():
        assert restored["words"][wid]["gloss"] == gloss
        restored["words"][wid]["gloss"] = BASELINES[slug]["words"][wid]["gloss"]
    if slug == "apostolorum":
        assert_group(core, restored)
        restored["segments"]["s03"]["alignments"].remove(GROUP)
        assert restored["segments"]["s03"]["alignments"] == []
        del restored["segments"]["s03"]["alignments"]
        for wid in GROUP["words"]:
            restored["words"][wid]["gloss"] = BASELINES[slug]["words"][wid]["gloss"]
    assert (
        hashlib.sha256(formatted(restored).encode()).hexdigest() == BASELINES[slug]["before_sha256"]
    )


def assert_prose_provenance(core, layer, record, slug):
    expected = BASELINES[slug]
    assert record == expected["provenance"]
    segment = next(s for s in core["segments"] if s["id"] == expected["segment"])
    prose = layer["segments"][expected["segment"]]["translation"]
    assert prose == expected["prose"]
    assert record["source_sha256"] == canonical_hash(source_payload(segment))
    assert record["target_sha256"] == canonical_hash(prose)


def assert_source_and_english(core, english, slug):
    assert canonical_hash(core) == BASELINES[slug]["core_digest"]
    assert canonical_hash(english) == BASELINES[slug]["english_digest"]


def test_scoped_population():
    assert len(SITES) == 7 and len(GROUP["words"]) == 3
    assert sum(len(v["context"]) for v in BASELINES.values()) == 38
    assert sum(len(v["words"]) for v in BASELINES.values()) == 10
    assert sum(v["complete_core_words"] for v in BASELINES.values()) == 145


def test_all_thirty_eight_members_have_the_selected_realization():
    direct, grouped = 0, []
    for slug in SLUGS:
        core, layer, _ = load(slug)
        assert check(core, layer) == []
        context = BASELINES[slug]["context"]
        direct += sum("gloss" in layer["words"][wid] for wid in context)
        grouped.extend(
            (slug, wid)
            for group in layer["segments"][BASELINES[slug]["segment"]].get("alignments", [])
            for wid in group["words"]
        )
    assert direct == 35
    assert grouped == [("apostolorum", wid) for wid in GROUP["words"]]


@pytest.mark.parametrize("slug,wid,gloss", SITES)
def test_selected_direct_reading(slug, wid, gloss):
    _, layer, _ = load(slug)
    assert layer["words"][wid]["gloss"] == gloss


def test_selected_protection_is_one_complete_expression():
    core, layer, _ = load("apostolorum")
    assert_group(core, layer)


@pytest.mark.parametrize("slug", SLUGS)
def test_full_context_preserves_government_and_referents(slug):
    core, layer, _ = load(slug)
    assert_context(core, layer, slug)


@pytest.mark.parametrize("slug", SLUGS)
def test_every_unselected_layer_field_is_preserved(slug):
    core, layer, _ = load(slug)
    assert_protected(core, layer, slug)


@pytest.mark.parametrize("slug", SLUGS)
def test_complete_shape_and_canonical_layout(slug):
    core, layer, _ = load(slug)
    path = CORPUS / "languages/pl/texts/ordinarium" / ("praefatio-" + slug + ".json")
    assert check_layer(core, layer, path) == []
    assert check(core, layer) == []
    assert path.read_text() == formatted(layer)


@pytest.mark.parametrize("slug", SLUGS)
def test_core_and_english_stay_unchanged(slug):
    core, _, english = load(slug)
    assert_source_and_english(core, english, slug)


@pytest.mark.parametrize("slug", SLUGS)
@pytest.mark.parametrize("changed_layer", ["core", "english"])
def test_changes_outside_polish_are_rejected(slug, changed_layer):
    core, _, english = load(slug)
    if changed_layer == "core":
        next(s for s in core["segments"] if s.get("words"))["words"][0]["lemma"] = "other"
    else:
        english["words"]["w001"]["gloss"] += " extra"
    with pytest.raises(AssertionError):
        assert_source_and_english(core, english, slug)


@pytest.mark.parametrize("slug", SLUGS)
def test_prose_and_working_provenance_stay_unchanged(slug):
    core, layer, _ = load(slug)
    provenance = json.loads((CORPUS / "languages/pl/translation-provenance.json").read_text())
    record = next(
        r for r in provenance["sites"] if r["site"] == BASELINES[slug]["provenance"]["site"]
    )
    assert_prose_provenance(core, layer, record, slug)


@pytest.mark.parametrize(
    "alternative", ["strzegł", "ją zachowywał", "Twojej", "Twoich", "genitive"]
)
def test_supported_contextual_alternative_is_not_a_semantic_error(alternative):
    slug = "defunctorum" if alternative == "genitive" else "apostolorum"
    core, layer, _ = load(slug)
    layer = prepare(layer, slug)
    if alternative in {"strzegł", "ją zachowywał"}:
        del layer["segments"]["s03"]["alignments"]
        for wid, gloss in zip(GROUP["words"], ["nieustanną", "opieką", alternative], strict=True):
            layer["words"][wid]["gloss"] = gloss
    elif alternative == "genitive":
        layer["words"]["w044"]["gloss"] = "Twoich"
        layer["words"]["w046"]["gloss"] = "wiernych"
    else:
        layer["words"]["w015" if alternative == "Twojej" else "w024"]["gloss"] = alternative
    assert_context(core, layer, slug)
    # Still a different editorial choice, requiring review before integration.
    with pytest.raises(AssertionError):
        assert_protected(core, layer, slug)


BAD_CONTEXT = [
    ("apostolorum", "w013", "abyśmy"),
    ("apostolorum", "w014", "trzodę"),
    ("apostolorum", "w015", "Twą"),
    ("apostolorum", "w018", "i"),
    ("apostolorum", "w019", "opuszcza"),
    ("apostolorum", "w020", "i"),
    ("apostolorum", "w021", "dla"),
    ("apostolorum", "w022", "błogosławione"),
    ("apostolorum", "w023", "Apostołowie"),
    ("apostolorum", "w024", "Twe"),
    ("defunctorum", "w044", "Twoich"),
    ("defunctorum", "w046", "wiernych"),
    ("defunctorum", "w048", "Życie"),
    ("defunctorum", "w049", "zmienia"),
    ("defunctorum", "w050", "i"),
    ("defunctorum", "w051", "zostaje odmienione"),
    ("defunctorum", "w053", "gdy rozpadnie"),
    ("defunctorum", "w054", "ziemski"),
    ("defunctorum", "w058", "wieczny"),
    ("defunctorum", "w062", "jest porównane"),
]


@pytest.mark.parametrize("slug,wid,wrong", BAD_CONTEXT)
def test_wrong_local_relation_is_rejected(slug, wid, wrong):
    core, layer, _ = load(slug)
    layer = prepare(layer, slug)
    layer["words"][wid]["gloss"] = wrong
    with pytest.raises(AssertionError):
        assert_context(core, layer, slug)


@pytest.mark.parametrize(
    "wrong",
    [
        "otoczył ją nieustanną opieką",
        "otaczał ją opieką",
        "otaczał ich nieustanną opieką",
        "otaczał się nieustanną opieką",
        "otaczali ją nieustanną opieką",
        "nie otaczał jej nieustanną opieką",
        "okrążał ją nieustannie",
        "zajmował się nią nieustannie",
    ],
)
def test_protection_does_not_drop_object_continuity_or_guarding(wrong):
    core, layer, _ = load("apostolorum")
    layer = prepare(layer, "apostolorum")
    layer["segments"]["s03"]["alignments"][0]["gloss"] = wrong
    with pytest.raises(AssertionError):
        assert_context(core, layer, "apostolorum")


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_member",
        "duplicate_member",
        "reordered",
        "outside_member",
        "wrong_anchor",
        "duplicate_group",
        "cross_segment",
        "missing_group",
        "extra_group",
        "direct_duplicate",
        "missing_word_object",
        "extra_group_metadata",
    ],
)
def test_membership_regression_is_rejected(mutation):
    core, layer, _ = load("apostolorum")
    layer = prepare(layer, "apostolorum")
    groups = layer["segments"]["s03"]["alignments"]
    group = groups[0]
    if mutation == "missing_member":
        group["words"].pop(0)
    elif mutation == "duplicate_member":
        group["words"].append("w027")
    elif mutation == "reordered":
        group["words"].reverse()
    elif mutation == "outside_member":
        group["words"].insert(0, "w024")
    elif mutation == "wrong_anchor":
        group["anchor"] = "w025"
    elif mutation == "duplicate_group":
        groups.append(deepcopy(group))
    elif mutation == "cross_segment":
        layer["segments"]["s04"]["alignments"] = [groups.pop()]
    elif mutation == "missing_group":
        groups.clear()
    elif mutation == "extra_group":
        groups.append({"words": ["w009", "w010"], "anchor": "w009", "gloss": "Ciebie Panie"})
        for wid in ("w009", "w010"):
            layer["words"][wid].pop("gloss")
    elif mutation == "direct_duplicate":
        layer["words"]["w026"]["gloss"] = "opieką"
    elif mutation == "missing_word_object":
        del layer["words"]["w026"]
    else:
        group["note"] = "extra"
    with pytest.raises(AssertionError):
        assert_protected(core, layer, "apostolorum")


@pytest.mark.parametrize("slug", SLUGS)
@pytest.mark.parametrize(
    "mutation", ["prose", "about", "unrelated_gloss", "word_note", "word_order", "segment_note"]
)
def test_unrelated_payload_is_not_hidden_by_restoration(slug, mutation):
    core, layer, _ = load(slug)
    layer = prepare(layer, slug)
    if mutation == "prose":
        layer["segments"][BASELINES[slug]["segment"]]["translation"] += " Dodatek."
    elif mutation == "about":
        layer["about"] += " Dodatek."
    elif mutation == "unrelated_gloss":
        layer["words"]["w001"]["gloss"] += " dodatek"
    elif mutation == "word_note":
        layer["words"]["w025" if slug == "apostolorum" else "w044"]["explanation"] = "Dodatek."
    elif mutation == "word_order":
        value = layer["words"].pop("w001")
        layer["words"]["w001"] = value
    else:
        layer["segments"][BASELINES[slug]["segment"]]["note"] = "Dodatek."
    with pytest.raises(AssertionError):
        assert_protected(core, layer, slug)


@pytest.mark.parametrize("slug", SLUGS)
@pytest.mark.parametrize(
    "field,wrong",
    [
        ("origin", "own"),
        ("review", "approved"),
        ("familiar_core", True),
        ("source_sha256", "0" * 64),
        ("target_sha256", "0" * 64),
    ],
)
def test_provenance_cannot_be_resealed(slug, field, wrong):
    core, layer, _ = load(slug)
    record = deepcopy(BASELINES[slug]["provenance"])
    record[field] = wrong
    with pytest.raises(AssertionError):
        assert_prose_provenance(core, layer, record, slug)
