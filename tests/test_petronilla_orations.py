"""Complete Petronilla orations, with explicit source and language boundaries."""

from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

from checks import delivery, language_packs, orations, participation, prose
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = json.loads((ROOT / "tests/fixtures/petronilla-orations.json").read_text(encoding="utf-8"))
TEXTS = tuple(FIXTURE["texts"])


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def core(text_id):
    return read(f"texts/{text_id.replace('.', '/', 1)}.json")


def layer(text_id, language):
    return read(f"languages/{language}/texts/{text_id.replace('.', '/', 1)}.json")


def assert_core(doc, expected):
    words = [word for segment in doc["segments"] for word in segment["words"]]
    assert words == expected["words"], "selected word analyses and stable identities"
    assert len(words) == len({word["id"] for word in words}) == 41
    boundaries = {
        segment["id"]: [word["id"] for word in segment["words"]] for segment in doc["segments"]
    }
    assert boundaries == expected["segments"], "explicit body and conclusion boundaries"
    assert doc["localization"] == expected["localization"], "bilingual note topology"
    editorial = doc["editorial"]
    assert editorial["status"] == "working-edition"
    assert editorial["analysis_defaults"] == expected["analysis_defaults"]
    assert "analysis_defaults_words" not in editorial, "words take the text default"
    assert editorial.get("words") == expected["editorial_words"], (
        "per-token sources are the measured provider confirmations"
    )


def assert_layer(doc, target, expected):
    for segment in doc["segments"]:
        members = [word["id"] for word in segment["words"]]
        localized = target["segments"][segment["id"]]
        realized = [wid for wid in members if "gloss" in target["words"][wid]]
        positions = {wid: index for index, wid in enumerate(members)}
        for group in localized.get("alignments", []):
            ids = group["words"]
            assert len(ids) >= 2 and group["anchor"] in ids, "realized group anchor"
            indices = [positions[wid] for wid in ids]
            assert indices == list(range(indices[0], indices[0] + len(ids))), "contiguous group"
            realized.extend(ids)
        assert Counter(realized) == Counter(members), "each member realized exactly once"
    assert target == expected, "exact contextual prose captions and notes"


@pytest.mark.parametrize("text_id", TEXTS)
def test_complete_source_and_current_schema(text_id):
    doc = core(text_id)
    assert_core(doc, FIXTURE["texts"][text_id])
    assert language_packs.check_core(doc) == []
    assert orations.check_doc(doc) == ([], 1)
    assert delivery.check_doc(doc)[0] == []
    assert participation.check_doc(doc)[0] == []


@pytest.mark.parametrize("text_id", TEXTS)
@pytest.mark.parametrize("language", ("en", "pl"))
def test_complete_language_card_realizations_and_prose(text_id, language):
    doc, target = core(text_id), layer(text_id, language)
    assert_layer(doc, target, FIXTURE["texts"][text_id]["layers"][language])
    path = ROOT / f"languages/{language}/texts/{text_id.replace('.', '/', 1)}.json"
    assert language_packs.check_layer(doc, target, path) == []
    assert prose.check(target) == []
    required = set(doc["localization"]["explanations"])
    assert required == {wid for wid, fields in target["words"].items() if "explanation" in fields}
    assert all(value == {} for value in doc["localization"]["explanations"].values())


@pytest.mark.parametrize("language", ("en", "pl"))
def test_fourteen_working_provenance_bindings(language):
    rows = read(f"languages/{language}/translation-provenance.json")["sites"]
    selected = [row for row in rows if row["text"] in TEXTS]
    assert selected == sorted(FIXTURE["provenance"][language], key=lambda row: row["site"])
    assert len(selected) == 7
    for row in selected:
        doc = core(row["text"])
        segment = next(seg for seg in doc["segments"] if seg["id"] == row["segment"])
        target = layer(row["text"], language)["segments"][row["segment"]]["translation"]
        assert row["source_sha256"] == canonical_hash(source_payload(segment))
        assert row["target_sha256"] == canonical_hash(target)
        assert (row["origin"], row["review"], row["familiar_core"]) == (
            "working-unsettled",
            "working",
            False,
        )


def assert_source_records(graph):
    for key, fixture_key in (
        ("uses", "source_uses"),
        ("witnesses", "pending_witnesses"),
        ("collations", "pending_collations"),
    ):
        selected = sorted(
            [
                row
                for row in graph[key]
                if (row.get("text") or row.get("address", {}).get("text")) in TEXTS
            ],
            key=lambda row: row["id"],
        )
        assert selected == FIXTURE[fixture_key], "exact source scopes and pending bindings"
    assert len(FIXTURE["source_uses"]) == 8
    assert all(
        row["review"] == {"status": "pending"}
        for row in FIXTURE["pending_witnesses"] + FIXTURE["pending_collations"]
    )
    for text_id in TEXTS:
        witnesses = [row for row in FIXTURE["pending_witnesses"] if row["text"] == text_id]
        assert len(witnesses) == 2
        for row in witnesses:
            assert len(row["source_dependencies"]["uses"]) == 1
            assert row["source_dependencies"]["raw_binding"] is None


def test_narrow_printed_source_scopes_and_pending_reviews():
    assert_source_records(read("bibliography/graph.json"))


@pytest.mark.parametrize("mutation", ("body-role", "approval", "missing-conclusion"))
def test_source_record_changes_are_rejected_and_restored(mutation):
    original = read("bibliography/graph.json")
    bad = deepcopy(original)
    if mutation == "body-role":
        use = next(row for row in bad["uses"] if row["id"] == f"use.{TEXTS[0]}.mr1962")
        use["role"] = "official_text"
    else:
        witness = next(row for row in bad["witnesses"] if row["text"] == TEXTS[0])
        if mutation == "approval":
            witness["review"] = {"status": "reviewed", "sha256": "0" * 64}
        else:
            witness["source_dependencies"]["uses"] = []
    with pytest.raises(AssertionError, match="exact source scopes and pending bindings"):
        assert_source_records(bad)
    assert_source_records(original)


def test_substantive_title_and_collective_aci_do_not_change_grammar():
    collect, secret = (core(text_id) for text_id in TEXTS)
    cwords = {word["id"]: word for segment in collect["segments"] for word in segment["words"]}
    swords = {word["id"]: word for segment in secret["segments"] for word in segment["words"]}
    assert cwords["w004"]["lemma"] == "salutaris" and cwords["w004"]["substantive"] is True
    assert cwords["w004"]["morph"]["case"] == "voc"
    assert cwords["w018"]["morph"]["voice"] == "pass"
    assert (swords["w001"]["lemma"], swords["w005"]["lemma"]) == ("acceptus", "sacratus")
    assert swords["w011"]["substantive"] is True
    assert swords["w013"]["morph"] == {"pos": "pron", "case": "acc", "number": "sg"}
    assert swords["w017"]["morph"]["tense"] == "perf"
    for words in (cwords, swords):
        assert words["w027"]["head"] == "w029"
        assert words["w036"]["morph"]["case"] == "nom"


@pytest.mark.parametrize("mutation", ("lemma", "voice", "head", "collective"))
def test_same_count_wrong_analysis_rejected_and_healthy_restored(mutation):
    text_id = TEXTS[1] if mutation == "collective" else TEXTS[0]
    original = core(text_id)
    bad = deepcopy(original)
    words = {word["id"]: word for segment in bad["segments"] for word in segment["words"]}
    if mutation == "lemma":
        words["w004"]["lemma"] = "salutare"
    elif mutation == "voice":
        words["w018"]["morph"]["voice"] = "act"
    elif mutation == "head":
        words["w027"]["head"] = "w036"
    else:
        words["w013"]["morph"]["number"] = "pl"
    with pytest.raises(AssertionError, match="selected word analyses and stable identities"):
        assert_core(bad, FIXTURE["texts"][text_id])
    assert_core(original, FIXTURE["texts"][text_id])


@pytest.mark.parametrize("mutation", ("missing", "duplicate", "predecessor"))
def test_caption_membership_and_explicit_affect_rejected_then_restored(mutation):
    text_id = TEXTS[0]
    doc, original = core(text_id), layer(text_id, "en")
    bad = deepcopy(original)
    if mutation == "missing":
        del bad["words"]["w003"]["gloss"]
    elif mutation == "duplicate":
        bad["words"]["w004"]["gloss"] = "our Savior"
    else:
        bad["segments"]["s01"]["alignments"][-1]["gloss"] = "we may be formed in reverent devotion"
    diagnostic = (
        "exact contextual prose captions and notes"
        if mutation == "predecessor"
        else "each member realized exactly once"
    )
    with pytest.raises(AssertionError, match=diagnostic):
        assert_layer(doc, bad, FIXTURE["texts"][text_id]["layers"]["en"])
    assert_layer(doc, original, FIXTURE["texts"][text_id]["layers"]["en"])


@pytest.mark.parametrize("text_id", TEXTS)
@pytest.mark.parametrize("mutation", ("boundary", "formula", "response"))
def test_split_shape_fails_closed_without_roles(text_id, mutation):
    original = core(text_id)
    bad = deepcopy(original)
    if mutation == "boundary":
        bad["segments"][0]["words"].append(bad["segments"][1]["words"].pop(0))
        diagnostic = "exact body/ending/response boundaries"
    elif mutation == "formula":
        bad["segments"][1]["words"][0]["form"] = "Pro"
        diagnostic = "complete ordinary formula and Amen"
    else:
        bad["segments"][-1]["words"][0]["form"] = "Alleluia"
        diagnostic = "complete ordinary formula and Amen"
    errors, roles = orations.structure(bad)
    assert roles == {} and any(diagnostic in error for error in errors)
    assert orations.base_attributes(bad) == {}
    assert orations.check_doc(original) == ([], 1)


def test_unlisted_prayer_cannot_inherit_the_split_exception():
    bad = deepcopy(core(TEXTS[0]))
    bad["id"] = "proprium.other-collecta"
    errors, roles = orations.structure(bad)
    assert roles == {} and any("complete body/Amen" in error for error in errors)
    assert orations.check_doc(core(TEXTS[0])) == ([], 1)


@pytest.mark.parametrize("text_id", TEXTS)
def test_response_role_mutation_is_owned_not_inferred_from_string(text_id):
    original = core(text_id)
    bad = deepcopy(original)
    bad["segments"][-1]["speaker"] = "sacerdos"
    errors, count = orations.check_doc(bad)
    assert count == 1 and any("oration speaker must be minister" in error for error in errors)
    assert orations.check_doc(original) == ([], 1)
