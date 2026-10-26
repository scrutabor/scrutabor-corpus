"""Local chant referents, translation origins, and measured analysis declarations."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import store
from checks import interlinear
from checks.translation_provenance import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
VISITATION = "proprium.visitatio-beatae-mariae-virginis-offertorium"
EASTER = (
    "proprium.dominica-ii-post-pascha-alleluia",
    "proprium.dominica-ii-post-pascha-offertorium",
    "proprium.dominica-ii-post-pascha-communio",
)
INTROIT = "proprium.dominica-ii-post-pascha-introitus"
GOSPEL = "proprium.vigilia-ascensionis-evangelium"
EPISTLE = "proprium.sanctorum-simonis-et-iudae-apostolorum-epistola"
BOTH = ["editorial", "whitakers", "collatinus"]
VISITATION_PROSE = (
    "Blessed are you, Virgin Mary, who carried the Creator of all things; "
    "you gave birth to Him who made you, and you remain a virgin forever."
)
VISITATION_GROUPS = [
    {"words": ["w001", "w002"], "anchor": "w002", "gloss": "Blessed are you"},
    {
        "words": ["w006", "w007", "w008"],
        "anchor": "w007",
        "gloss": "carried the Creator of all things",
    },
    {"words": ["w011", "w012"], "anchor": "w012", "gloss": "made you"},
    {"words": ["w014", "w015"], "anchor": "w015", "gloss": "forever"},
]
VISITATION_DIRECT = {
    "w003": "Virgin",
    "w004": "Mary",
    "w005": "who",
    "w009": "you gave birth to",
    "w010": "Him who",
    "w013": "and",
    "w016": "you remain",
    "w017": "a virgin",
}
SITE_HASHES = {
    "proprium.dominica-ii-post-pascha-alleluia": (
        "a2530b68f3f38e2f6e6a36d3a6bac9a5abd2eae556d81decd96dbf7744e92fc9",
        "84f8fc5a63cd2682a194428c3a5016ad53eeb0baa103a6a969b3232209e4aa59",
    ),
    "proprium.dominica-ii-post-pascha-communio": (
        "53a27a234d80e2fec58400c88d96b8bcaa289f9dcf66ed2bde713284f7495e18",
        "2bf6f1d4ed1aa11fdccfe8cfbb65303aa8c34b7c43f57ae73dc4253cbdb1c278",
    ),
    "proprium.dominica-ii-post-pascha-introitus": (
        "5989aa65fd47c4fd0435f8462d1aee9d0400d4a364d85b845a3d9bf30936cdde",
        "0e32b6be4cc4df1fa247d7748cc3013059bf9589174b262ae3b2837d26feeb45",
    ),
    "proprium.dominica-ii-post-pascha-offertorium": (
        "f76d90f3bde6e1d9bd83fcfdf77583ec8df4997597ee9c82e86f44f8786f5a4a",
        "147c26f09d70426870f9d06f2ded1b11577483f77392203e4b4d1319c4c2b97d",
    ),
    "proprium.visitatio-beatae-mariae-virginis-offertorium": (
        "30fcad0300142dc1bd6a4d015bbad91a8e825629de09dce62b08e8b34f24010e",
        "98aa8cf65580a6d62c6572951ce9fb8f6f199cc2c9a74924a57e57fe57e24381",
    ),
}


def origin_record(text):
    table = json.loads((ROOT / "languages/en/translation-provenance.json").read_bytes())
    rows = [row for row in table["sites"] if row["site"] == text + ".s01.en"]
    assert len(rows) == 1
    return rows[0]


def assert_origin(record, text, origin):
    source, target = SITE_HASHES[text]
    expected = {
        "site": text + ".s01.en",
        "text": text,
        "segment": "s01",
        "language": "en",
        "familiar_core": False,
        "origin": origin,
        "review": "working",
        "source_sha256": source,
        "target_sha256": target,
    }
    assert canonical_hash(record) == canonical_hash(expected), "local translation provenance"


def assert_visitation(layer):
    assert layer["segments"]["s01"]["translation"] == VISITATION_PROSE
    assert layer["segments"]["s01"]["alignments"] == VISITATION_GROUPS, "Visitation captions"
    assert {
        word: row["gloss"] for word, row in layer["words"].items() if "gloss" in row
    } == VISITATION_DIRECT, "Visitation captions"
    members = [word for group in VISITATION_GROUPS for word in group["words"]]
    assert len(members) == 9 and len(set(members)) == 9
    assert sorted([*VISITATION_DIRECT, *members]) == [f"w{i:03}" for i in range(1, 18)]
    assert all(not layer["words"][word].get("gloss") for word in members)


def word_map(doc):
    return {word["id"]: word for segment in doc["segments"] for word in segment["words"]}


def analysis(doc, word):
    return word.get("analysis") or doc.get("analysis_defaults_words") or doc["analysis_defaults"]


def assert_gospel_sources(doc):
    words = word_map(doc)
    assert list(words) == [f"w{i:03}" for i in range(1, 179)]
    for ident, word in words.items():
        expected = (
            ["editorial"]
            if ident == "w071"
            else ["editorial", "collatinus"]
            if ident == "w106"
            else BOTH
        )
        assert analysis(doc, word)["sources"] == expected, "Gospel measured sources"
    for ident in ("w011", "w028"):
        row = analysis(doc, words[ident])
        assert row["confidence"] == "medium", "Gospel uncertainty"
        assert row["review"] == "pending", "Gospel uncertainty"


def test_visitation_complete_realization_distinguishes_carrying_and_birth():
    layer = store.raw_layer(ROOT, "en", VISITATION)
    assert_visitation(layer)
    assert interlinear.check(store.core(ROOT, VISITATION), layer) == []


@pytest.mark.parametrize("fault", ["beatitude", "carrying", "birth", "duration"])
def test_visitation_local_caption_error_is_rejected_and_restored(fault):
    original = store.raw_layer(ROOT, "en", VISITATION)
    assert_visitation(original)
    changed = deepcopy(original)
    if fault == "birth":
        changed["words"]["w009"]["gloss"] = "you carried"
    else:
        index, wrong = {
            "beatitude": (0, "Blessed"),
            "carrying": (1, "the Creator carried you"),
            "duration": (3, "once"),
        }[fault]
        changed["segments"]["s01"]["alignments"][index]["gloss"] = wrong
    assert changed != original
    assert interlinear.check(store.core(ROOT, VISITATION), changed) == []
    try:
        with pytest.raises(AssertionError, match="Visitation captions"):
            assert_visitation(changed)
    finally:
        changed.clear()
        changed.update(deepcopy(original))
    assert changed == original
    assert_visitation(changed)
    assert interlinear.check(store.core(ROOT, VISITATION), changed) == []


def test_visitation_target_change_preserves_the_whole_origin_record():
    row = origin_record(VISITATION)
    assert_origin(row, VISITATION, "working-unsettled")
    prose = store.raw_layer(ROOT, "en", VISITATION)["segments"]["s01"]["translation"]
    assert row["target_sha256"] == canonical_hash(prose)


@pytest.mark.parametrize("field", ["origin", "review", "familiar_core"])
def test_visitation_target_change_does_not_promote_origin_or_review(field):
    original = origin_record(VISITATION)
    assert_origin(original, VISITATION, "working-unsettled")
    changed = deepcopy(original)
    changed[field] = {"origin": "own", "review": "internally-reviewed", "familiar_core": 0}[field]
    assert canonical_hash(changed) != canonical_hash(original)
    try:
        with pytest.raises(AssertionError, match="local translation provenance"):
            assert_origin(changed, VISITATION, "working-unsettled")
    finally:
        changed.clear()
        changed.update(deepcopy(original))
    assert canonical_hash(changed) == canonical_hash(original)
    assert_origin(changed, VISITATION, "working-unsettled")


@pytest.mark.parametrize("text", EASTER, ids=["alleluia", "offertory", "communion"])
def test_three_easter_chant_origins_keep_exact_source_target_and_review(text):
    row = origin_record(text)
    assert_origin(row, text, "own")
    prose = store.raw_layer(ROOT, "en", text)["segments"]["s01"]["translation"]
    assert row["target_sha256"] == canonical_hash(prose)


@pytest.mark.parametrize("text", EASTER, ids=["alleluia", "offertory", "communion"])
def test_three_easter_origin_records_reject_and_restore_the_prior_label(text):
    original = origin_record(text)
    assert_origin(original, text, "own")
    changed = deepcopy(original)
    changed["origin"] = "working-unsettled"
    assert changed != original
    try:
        with pytest.raises(AssertionError, match="local translation provenance"):
            assert_origin(changed, text, "own")
    finally:
        changed["origin"] = original["origin"]
    assert changed == original
    assert_origin(changed, text, "own")


def test_mixed_easter_introit_does_not_inherit_a_whole_segment_origin():
    assert_origin(origin_record(INTROIT), INTROIT, "working-unsettled")


@pytest.mark.parametrize("ident", ["w053", "w056"])
def test_epistle_distributive_pronouns_keep_their_measured_sources_and_review(ident):
    doc, _ = store.load(ROOT, EPISTLE)
    row = analysis(doc, word_map(doc)[ident])
    assert row == {"confidence": "high", "sources": BOTH, "review": "pending"}


def test_gospel_sources_keep_the_actual_absence_singleton_and_two_uncertainties():
    doc, _ = store.load(ROOT, GOSPEL)
    assert_gospel_sources(doc)


@pytest.mark.parametrize(
    "ident,field,value,message",
    [
        ("w071", "sources", ["editorial", "whitakers"], "Gospel measured sources"),
        ("w106", "sources", BOTH, "Gospel measured sources"),
        ("w001", "sources", ["editorial", "collatinus"], "Gospel measured sources"),
        ("w011", "confidence", "high", "Gospel uncertainty"),
        ("w028", "review", "accepted", "Gospel uncertainty"),
    ],
    ids=["unconfirmed", "singleton", "missing-confirmer", "medium", "pending"],
)
def test_gospel_wrong_credit_or_review_is_rejected_and_restored(ident, field, value, message):
    original, _ = store.load(ROOT, GOSPEL)
    assert_gospel_sources(original)
    changed = deepcopy(original)
    word = word_map(changed)[ident]
    present = "analysis" in word
    previous = deepcopy(word.get("analysis"))
    row = deepcopy(analysis(changed, word))
    row[field] = deepcopy(value)
    word["analysis"] = row
    assert changed != original
    try:
        with pytest.raises(AssertionError, match=message):
            assert_gospel_sources(changed)
    finally:
        if present:
            word["analysis"] = previous
        else:
            del word["analysis"]
    assert changed == original
    assert_gospel_sources(changed)
