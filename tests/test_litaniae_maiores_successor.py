"""Finite Rogation caption and source-scope regressions with unchanged subject controls."""

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


FIXTURE = load("tests/fixtures/litaniae-maiores-successor.json")
COLLECT, POSTCOMMUNION = FIXTURE["texts"]
LAYERS = [(language, text) for language in ("pl", "en") for text in FIXTURE["texts"]]


def core(text):
    return load(f"texts/{text.replace('.', '/', 1)}.json")


def layer(language, text):
    return load(f"languages/{language}/texts/{text.replace('.', '/', 1)}.json")


def select(doc, path):
    for key in path:
        if isinstance(key, dict):
            (doc,) = [row for row in doc if all(row.get(k) == v for k, v in key.items())]
        else:
            doc = doc[key]
    return doc


def replace(doc, path, value):
    select(doc, path[:-1])[path[-1]] = value


def assert_scalar(doc, row):
    assert select(doc, row["selector"]) == row["after"], row["id"]


@pytest.mark.parametrize("row", FIXTURE["source_fields"], ids=lambda row: row["id"])
def test_exact_source_roles_and_descriptions(row):
    assert_scalar(load(row["path"]), row)


@pytest.mark.parametrize("row", FIXTURE["source_fields"], ids=lambda row: row["id"])
def test_predecessor_source_claim_is_rejected(row):
    doc = load(row["path"])
    assert_scalar(doc, row)
    replace(doc, row["selector"], row["before"])
    with pytest.raises(AssertionError, match=re.escape(row["id"])):
        assert_scalar(doc, row)


def assert_caption(doc, row):
    expected = row["after_alignment"]
    members = set(expected["words"])
    selected = [
        group
        for group in doc["segments"]["s01"]["alignments"]
        if members.intersection(group["words"])
    ]
    assert selected == [expected], f"{row['id']} compact group"
    assert all("gloss" not in doc["words"][word] for word in members), (
        f"{row['id']} exactly one realization"
    )


@pytest.mark.parametrize("row", FIXTURE["caption_operations"], ids=lambda row: row["id"])
def test_exact_compact_caption(row):
    assert_caption(load(row["path"]), row)


@pytest.mark.parametrize("row", FIXTURE["caption_operations"], ids=lambda row: row["id"])
def test_predecessor_caption_is_rejected(row):
    doc = load(row["path"])
    assert_caption(doc, row)
    groups = doc["segments"]["s01"]["alignments"]
    if row["id"] == "EN-C01":
        groups.remove(row["after_alignment"])
        for word, fields in row["before_words"].items():
            doc["words"][word].update(fields)
    else:
        (group,) = [group for group in groups if group == row["after_alignment"]]
        group["gloss"] = row["before_alignment"]["gloss"]
    with pytest.raises(AssertionError, match=f"{row['id']} compact group"):
        assert_caption(doc, row)


def assert_memberships(doc, localized):
    expected = Counter(word["id"] for segment in doc["segments"] for word in segment["words"])
    actual = Counter(word for word, fields in localized["words"].items() if "gloss" in fields)
    for segment in localized["segments"].values():
        for group in segment.get("alignments", []):
            assert group["anchor"] in group["words"], "group anchor is a member"
            actual.update(group["words"])
    assert actual == expected, "each canonical word exactly once"


@pytest.mark.parametrize("language,text", LAYERS)
def test_all_170_memberships_remain_complete(language, text):
    assert_memberships(core(text), layer(language, text))


@pytest.mark.parametrize("damage", ["duplicate", "missing"])
def test_membership_damage_is_rejected(damage):
    doc, localized = core(COLLECT), layer("en", COLLECT)
    assert_memberships(doc, localized)
    row = FIXTURE["caption_operations"][0]
    if damage == "duplicate":
        localized["words"]["w017"]["gloss"] = "by Your"
    else:
        localized["segments"]["s01"]["alignments"].remove(row["after_alignment"])
    with pytest.raises(AssertionError, match="each canonical word exactly once"):
        assert_memberships(doc, localized)


def test_the_three_word_exception_does_not_admit_a_clause_group():
    localized = layer("en", COLLECT)
    row = FIXTURE["caption_operations"][0]
    assert_caption(localized, row)
    groups = localized["segments"]["s01"]["alignments"]
    groups.remove(row["after_alignment"])
    groups.append(
        {
            "words": [f"w{i:03d}" for i in range(14, 21)],
            "anchor": "w020",
            "gloss": "may always be shielded by Your protection against all adversity",
        }
    )
    with pytest.raises(AssertionError, match="EN-C01 compact group"):
        assert_caption(localized, row)


def assert_english_opening(localized):
    assert localized["segments"]["s01"]["alignments"][0] == {
        "words": ["w001", "w002"],
        "anchor": "w001",
        "gloss": "Our prayers",
    }, "English caption sentence opening"


def test_caption_sentence_case_is_not_the_reordered_prose_case():
    english, polish = layer("en", POSTCOMMUNION), layer("pl", POSTCOMMUNION)
    assert_english_opening(english)
    assert english["segments"]["s01"]["translation"].startswith("Lord,")
    assert polish["segments"]["s01"]["translation"].startswith("Przychyl")
    assert polish["segments"]["s01"]["alignments"][1]["gloss"] == "przychyl się łaskawie"
    assert polish["words"]["w029"]["gloss"] == "który"
    english["segments"]["s01"]["alignments"][0]["gloss"] = "our prayers"
    with pytest.raises(AssertionError, match="English caption sentence opening"):
        assert_english_opening(english)


def assert_apparatus_binding(graph, row):
    text = row["selector"][1]["id"].removeprefix("collation.").removesuffix(".mr1962-vatican1962")
    apparatus = load(f"witnesses/{text}/apparatus.json")
    assert select(graph, row["selector"]) == digest(apparatus), f"apparatus binding {text}"


@pytest.mark.parametrize("row", FIXTURE["derived_apparatus_fields"], ids=lambda row: row["id"])
def test_description_changes_have_current_apparatus_bindings(row):
    graph = load(row["path"])
    assert_apparatus_binding(graph, row)
    replace(graph, row["selector"], row["before"])
    with pytest.raises(AssertionError, match="apparatus binding"):
        assert_apparatus_binding(graph, row)


def assert_prose(localized):
    row = FIXTURE["prose_preference"]
    assert_scalar(localized, row)


def test_separate_prose_preference_and_its_exact_inverse():
    row = FIXTURE["prose_preference"]
    localized = load(row["path"])
    assert_prose(localized)
    assert row["after"] == row["before"].replace(
        "through our consolation.", "through the consolation we receive."
    )
    replace(localized, row["selector"], row["before"])
    with pytest.raises(AssertionError, match="ROG-EN-CONS-1"):
        assert_prose(localized)


def test_the_one_updated_target_hash_is_not_a_source_or_review_change():
    row = FIXTURE["derived_prose"]
    ledger = load(row["path"])
    assert_scalar(ledger, row)
    assert row["after"] == digest(FIXTURE["prose_preference"]["after"])
    replace(ledger, row["selector"], row["before"])
    with pytest.raises(AssertionError, match="D-PROSE-EN-PC"):
        assert_scalar(ledger, row)


@pytest.mark.parametrize("row", FIXTURE["document_subjects"], ids=lambda row: row["path"])
def test_no_unlisted_word_prose_or_analysis_edit(row):
    assert digest(load(row["path"])) == row["after_sha256"]


def test_all_scoped_graph_records_keep_their_exact_pending_subjects():
    graph = load("bibliography/graph.json")
    assert len(FIXTURE["graph_records"]) == 15
    for row in FIXTURE["graph_records"]:
        record = select(graph, [row["section"], {"id": row["id"]}])
        assert digest(record) == row["sha256"], row["id"]
        if row["section"] in {"witnesses", "collations"}:
            assert record["review"] == {"status": "pending"}


def test_all_eight_prose_bindings_keep_their_working_states():
    assert len(FIXTURE["provenance_sites"]) == 8
    for expected in FIXTURE["provenance_sites"]:
        ledger = load(f"languages/{expected['language']}/translation-provenance.json")
        actual = select(ledger, ["sites", {"site": expected["site"]}])
        assert actual == expected
        localized = layer(expected["language"], expected["text"])
        prose = localized["segments"][expected["segment"]]["translation"]
        assert actual["target_sha256"] == digest(prose)
        assert actual["review"] == "working" and actual["familiar_core"] is False


@pytest.mark.parametrize("row", FIXTURE["transcripts"], ids=lambda row: row["path"])
def test_literal_composite_witnesses_are_not_retranscribed(row):
    assert hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest() == row["sha256"]
