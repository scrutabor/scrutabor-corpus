"""Selected Marian chant content, complete token coverage and pending provenance.

These are bounded wording regressions, not universal translation rules or
source/translation approvals. The historical relabel fixture remains evidence.
"""

import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest
from marian_chant_fixture import FIXTURE, expected_marian_row

from checks import prose
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
LAYERS = FIXTURE["layers"]
SITES = sorted(LAYERS)
SEVEN = "proprium.septem-dolorum-beatae-mariae-virginis-offertorium"
IMMACULATE = "proprium.immaculata-conceptio-graduale"
ASSUMPTION = "proprium.assumptio-beatae-mariae-virginis-offertorium"
STEWARD = "proprium.dominica-viii-post-pentecosten-evangelium"
HISTORICAL = "tests/fixtures/own-relabel-2026-10-20-round-2.json"


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def core(text):
    return read("texts/" + text.replace(".", "/", 1) + ".json")


def layer(site):
    text, _segment, language = site.rsplit(".", 2)
    return read(f"languages/{language}/texts/" + text.replace(".", "/", 1) + ".json")


def assert_memberships(document, ids):
    """Count actual source-order IDs, not numeric ID ranges or visible labels."""
    assert set(document["words"]) == set(ids), "canonical word identities"
    counts = Counter(wid for wid, word in document["words"].items() if "gloss" in word)
    positions = {wid: i for i, wid in enumerate(ids)}
    for group in document["segments"]["s01"].get("alignments", []):
        members = group["words"]
        assert 2 <= len(members) <= 3, "selected compact construction"
        assert all(wid in positions for wid in members), "canonical group members"
        start = positions[members[0]]
        assert ids[start : start + len(members)] == members, "contiguous source order"
        assert group["anchor"] in members, "anchor belongs to construction"
        counts.update(members)
    assert counts == Counter(ids), "exactly one realization per canonical word"


def assert_target(site, target):
    assert canonical_hash(target) == LAYERS[site]["target_after"], "complete selected prose"


def assert_captions(site, document):
    expected = LAYERS[site]
    assert {wid: w["gloss"] for wid, w in document["words"].items() if "gloss" in w} == (
        expected["direct"]
    ), "selected direct captions"
    assert document["segments"]["s01"].get("alignments", []) == expected["alignments"], (
        "selected minimal constructions"
    )


def assert_working(site, row):
    text, segment, language = site.rsplit(".", 2)
    assert (row["site"], row["text"], row["segment"], row["language"]) == (
        site,
        text,
        segment,
        language,
    ), "site identity"
    assert (row["origin"], row["review"], row["familiar_core"]) == (
        "working-unsettled",
        "working",
        False,
    ), "working wording, not approval"
    assert row["source_sha256"] == FIXTURE["source"][text]["sha256"], "selected Latin identity"
    assert row["target_sha256"] == LAYERS[site]["target_after"], "selected target identity"


@pytest.mark.parametrize("site", SITES)
def test_complete_selected_layer_and_all_canonical_memberships(site):
    document = layer(site)
    text, segment, language = site.rsplit(".", 2)
    expected = LAYERS[site]
    raw = core(text)
    source = next(s for s in raw["segments"] if s["id"] == segment)
    ids = [w["id"] for w in source["words"]]
    assert ids == FIXTURE["source"][text]["ids"]
    assert canonical_hash(source_payload(source)) == FIXTURE["source"][text]["sha256"]
    assert (document["text"], document["language"]) == (text, language)
    assert set(document["segments"]) == {"s01"}
    assert document["about"] == expected["about"]
    assert_memberships(document, ids)
    assert_captions(site, document)
    assert document["segments"][segment]["translation"] == expected["translation"]
    assert_target(site, document["segments"][segment]["translation"])
    words = {wid: {} for wid in ids}
    for wid, gloss in expected["direct"].items():
        words[wid]["gloss"] = gloss
    for wid, explanation in expected["explanations"].items():
        words[wid]["explanation"] = explanation
    assert document["words"] == words, "complete selected word details"
    assert prose.check(document) == [], "actual own-prose checker"


def test_bounded_inventory_and_five_changed_prose_hashes_one_retained():
    assert len(SITES) == 6 and len(FIXTURE["source"]) == 3
    assert sorted(len(s["ids"]) for s in FIXTURE["source"].values()) == [12, 21, 24]
    assert sum(len(FIXTURE["source"][site.rsplit(".", 2)[0]]["ids"]) for site in SITES) == 114
    assert sum(len(v["direct"]) for v in LAYERS.values()) == 73
    assert sum(len(v["alignments"]) for v in LAYERS.values()) == 20
    unchanged = {site for site, v in LAYERS.items() if v["target_before"] == v["target_after"]}
    assert unchanged == {SEVEN + ".s01.pl"}
    for site, expected in LAYERS.items():
        assert canonical_hash(expected["translation_before"]) == expected["target_before"]
        assert_target(site, expected["translation"])
        if site not in unchanged:
            with pytest.raises(AssertionError, match=r"^complete selected prose(?:\n|$)"):
                assert_target(site, expected["translation_before"])


@pytest.mark.parametrize("site", SITES)
def test_all_six_provenance_rows_remain_working(site):
    language = site.rsplit(".", 1)[1]
    row = next(
        r
        for r in read(f"languages/{language}/translation-provenance.json")["sites"]
        if r["site"] == site
    )
    assert_working(site, row)
    for field, value, message in (
        ("origin", "own", "working wording, not approval"),
        ("origin", "public-domain", "working wording, not approval"),
        ("review", "internally-reviewed", "working wording, not approval"),
        ("familiar_core", True, "working wording, not approval"),
        ("source_sha256", "0" * 64, "selected Latin identity"),
        ("target_sha256", LAYERS[site]["target_before"], "selected target identity"),
    ):
        damaged = deepcopy(row)
        damaged[field] = value
        if damaged != row:
            with pytest.raises(AssertionError, match="^" + message + r"(?:\n|$)"):
                assert_working(site, damaged)


@pytest.mark.parametrize("text", sorted(FIXTURE["source"]))
def test_explicit_bilingual_explanation_topology_and_pending_sources(text):
    raw = core(text)
    assert raw["localization"] == FIXTURE["neutral_localization"][text]
    declared = raw["localization"].get("explanations", {})
    actual = {}
    for language in ("en", "pl"):
        document = layer(f"{text}.s01.{language}")
        for wid, word in document["words"].items():
            if "explanation" in word:
                actual.setdefault(wid, []).append(language)
    assert actual == {wid: value["languages"] for wid, value in declared.items()}
    assert raw["editorial"]["status"] == "working-edition"
    witnesses = [w for w in read("bibliography/graph.json")["witnesses"] if w["text"] == text]
    assert {w["transcription"] for w in witnesses} == {"mr", "do"}
    assert len(witnesses) == 2
    assert all(w["review"]["status"] == "pending" for w in witnesses)


def test_six_explanations_at_three_addresses_not_approval():
    assert sum(len(v["explanations"]) for v in LAYERS.values()) == 6
    assert (
        sum(len(v.get("explanations", {})) for v in FIXTURE["neutral_localization"].values()) == 3
    )
    assert core(SEVEN)["segments"][0]["words"][5]["morph"]["tense"] == "futperf"
    en, pl = layer(SEVEN + ".s01.en"), layer(SEVEN + ".s01.pl")
    assert en["words"]["w021"]["gloss"] == "you stand"
    assert pl["words"]["w021"]["gloss"] == "staniesz"
    assert "may He turn His wrath away" in en["segments"]["s01"]["translation"]
    assert "The Lord is to turn His wrath" in en["words"]["w014"]["explanation"]
    assert "Pan ma odwrócić gniew" in pl["words"]["w014"]["explanation"]
    assert en["words"]["w021"]["explanation"].endswith("“when you stand.”")
    assert pl["words"]["w021"]["explanation"].endswith("„gdy staniesz”.")
    # Pin this occurrence, not a corpus-wide capitalization rule.
    assert pl["words"]["w016"]["gloss"] == "swój"


@pytest.mark.parametrize(
    "case",
    FIXTURE["explanation_punctuation_predecessors"],
    ids=lambda c: c["site"].rsplit(".", 1)[1] + "-" + c["word"],
)
def test_actual_prose_check_rejects_exact_semicolon_predecessors(case):
    document = layer(case["site"])
    assert prose.check(document) == []
    damaged = deepcopy(document)
    damaged["words"][case["word"]]["explanation"] = case["before"]
    errors = prose.check(damaged)
    assert any(case["word"] + ".explanation." in e and "uses a semicolon" in e for e in errors)


@pytest.mark.parametrize("damage", ("missing", "duplicate", "clause-wide"))
def test_membership_controls_reject_missing_duplicate_or_oversized_group(damage):
    site = ASSUMPTION + ".s01.en"
    document = layer(site)
    ids = FIXTURE["source"][ASSUMPTION]["ids"]
    assert_memberships(document, ids)
    damaged = deepcopy(document)
    if damage == "missing":
        del damaged["words"]["w001"]["gloss"]
    elif damage == "duplicate":
        damaged["words"]["w008"]["gloss"] = "seed"
    else:
        damaged["segments"]["s01"]["alignments"] = [
            {"words": ids, "anchor": "w002", "gloss": LAYERS[site]["translation"]}
        ]
        for word in damaged["words"].values():
            word.pop("gloss", None)
    message = (
        "selected compact construction"
        if damage == "clause-wide"
        else "exactly one realization per canonical word"
    )
    with pytest.raises(AssertionError, match="^" + message + r"(?:\n|$)"):
        assert_memberships(damaged, ids)


@pytest.mark.parametrize(
    "site,word,predecessor",
    (
        (SEVEN + ".s01.pl", "w011", "dobra"),
        (IMMACULATE + ".s01.pl", "w009", "najwyższego"),
        (IMMACULATE + ".s01.pl", "w012", "niewiasty"),
        (ASSUMPTION + ".s01.en", "w001", "enmity"),
        (ASSUMPTION + ".s01.pl", "w002", "położę"),
    ),
)
def test_exact_caption_predecessors_do_not_reenter(site, word, predecessor):
    document = layer(site)
    assert_captions(site, document)
    damaged = deepcopy(document)
    damaged["words"][word]["gloss"] = predecessor
    with pytest.raises(AssertionError, match=r"^selected direct captions(?:\n|$)"):
        assert_captions(site, damaged)


@pytest.mark.parametrize(
    "site,word,wrong",
    (
        (SEVEN + ".s01.en", "w021", "You stand"),
        (SEVEN + ".s01.pl", "w021", "stałaś"),
        (ASSUMPTION + ".s01.en", "w002", "I would put"),
    ),
)
def test_selected_human_referent_and_future_caption_controls(site, word, wrong):
    document = layer(site)
    assert_captions(site, document)
    damaged = deepcopy(document)
    damaged["words"][word]["gloss"] = wrong
    with pytest.raises(AssertionError, match=r"^selected direct captions(?:\n|$)"):
        assert_captions(site, damaged)


@pytest.mark.parametrize(
    "language,expected",
    (("en", ["your seed", "her Seed"]), ("pl", ["twoim potomstwem", "jej Potomstwem"])),
)
def test_offspring_possessors_keep_separate_minimal_groups(language, expected):
    site = f"{ASSUMPTION}.s01.{language}"
    document = layer(site)
    groups = [
        g
        for g in document["segments"]["s01"]["alignments"]
        if "w008" in g["words"] or "w011" in g["words"]
    ]
    assert [g["words"] for g in groups] == [["w008", "w009"], ["w011", "w012"]]
    assert [g["gloss"] for g in groups] == expected
    damaged = deepcopy(document)
    named = [
        g
        for g in damaged["segments"]["s01"]["alignments"]
        if "w008" in g["words"] or "w011" in g["words"]
    ]
    named[0]["gloss"], named[1]["gloss"] = named[1]["gloss"], named[0]["gloss"]
    with pytest.raises(AssertionError, match=r"^selected minimal constructions(?:\n|$)"):
        assert_captions(site, damaged)


@pytest.mark.parametrize("language,expected", (("pl", "dobra"), ("en", "goods")))
def test_favorable_speech_does_not_ban_the_stewards_actual_goods(language, expected):
    words = {w["id"]: w for w in core(STEWARD)["segments"][0]["words"]}
    assert [words[w]["lemma"] for w in ("w024", "w025", "w026")] == ["dissipo", "bonus", "ipse"]
    assert words["w025"]["substantive"] is True
    steward = layer(f"{STEWARD}.s01.{language}")
    assert steward["words"]["w025"]["gloss"] == expected
    seven = layer(f"{SEVEN}.s01.{language}")
    assert seven["words"]["w011"]["gloss"] == (
        "to, co dobre" if language == "pl" else "good things"
    )
    assert ("to, co dobre" if language == "pl" else "in our favor") in (
        seven["segments"]["s01"]["translation"]
    )


def test_exact_historical_successors_preserve_the_406_row_fixture():
    path = ROOT / HISTORICAL
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        "fdac228d4570ff49322e0cee998f0e036bd2228122e02cad05e643f15a7cba50"
    )
    historical = read(HISTORICAL)["sites"]
    frozen = deepcopy(historical)
    assert len(historical) == 406
    intersection = set(historical) & set(SITES)
    assert intersection == {SEVEN + ".s01.en", IMMACULATE + ".s01.en", ASSUMPTION + ".s01.pl"}
    successors = {site: expected_marian_row(row, site) for site, row in historical.items()}
    assert {site for site in historical if historical[site] != successors[site]} == intersection
    for site in SITES:
        row = {
            "origin": "working-unsettled",
            "review": "working",
            "target_sha256": LAYERS[site]["target_before"],
            "familiar_core": False,
        }
        expected = expected_marian_row(row, site)
        assert expected["target_sha256"] == LAYERS[site]["target_after"]
        assert {k: v for k, v in row.items() if k != "target_sha256"} == {
            k: v for k, v in expected.items() if k != "target_sha256"
        }
        row["target_sha256"] = "0" * 64
        with pytest.raises(AssertionError, match=r"^historical chant target(?:\n|$)"):
            expected_marian_row(row, site)
    assert historical == frozen
