"""Paired source punctuation preserves lexical identity and exact witness text."""

import json
from copy import deepcopy

import pytest
from test_collate import a_text, witnesses
from test_translation_provenance import initialize_all, write_text

from build_reader.emit import Table, core_artifact, expand
from checks.collate import collate, corpus_tokens
from checks.language_packs import check_core
from checks.lint import lint_text
from checks.punctuation import check_parentheses, word_faces
from checks.translation_provenance import canonical_hash, check, source_payload


def paired_text():
    doc = a_text("quem", "suscitávit", "ex", "mórtuis")
    doc["segments"][0]["parentheses"] = [{"from": "w001", "through": "w004"}]
    return doc


def test_source_surface_includes_both_marks_without_changing_words():
    doc = paired_text()
    before = deepcopy(doc)
    assert corpus_tokens(doc) == [
        ("w001", "(quem"),
        ("w002", "suscitávit"),
        ("w003", "ex"),
        ("w004", "mórtuis)"),
    ]
    assert doc == before


def test_invalid_endpoint_is_a_normal_lint_error():
    doc = paired_text()
    doc["segments"][0]["parentheses"][0]["through"] = "w999"
    errors, _ = lint_text(doc)
    assert any("parentheses" in error for error in errors)


def test_range_presence_changes_the_current_source_binding():
    segment = paired_text()["segments"][0]
    plain = deepcopy(segment)
    del plain["parentheses"]
    assert canonical_hash(source_payload(segment)) != canonical_hash(source_payload(plain))


def test_actual_reader_codec_preserves_ranges_and_every_word_object():
    core = paired_text()
    core.update(
        status="draft",
        analysis_defaults={"confidence": "medium", "review": "pending", "sources": []},
    )
    parses, analyses, citations = Table(), Table(), Table()
    artifact = core_artifact(core, core, parses, analyses, citations)
    language = {"language": "en", "about": "", "seg": [{"id": "s01", "g": [None] * 4}]}
    expanded, _ = expand(artifact, language, parses.order, analyses.order, citations.order, [])
    assert expanded["segments"][0]["parentheses"] == core["segments"][0]["parentheses"]
    assert expanded["segments"][0]["words"] == core["segments"][0]["words"]


@pytest.mark.parametrize("field,value", [("post", ".)"), ("form", "(quem")])
def test_brackets_still_cannot_be_smuggled_into_lexical_fields(field, value):
    doc = paired_text()
    doc["segments"][0]["words"][0][field] = value
    errors, _ = lint_text(doc)
    assert any("charset violation" in error or "not one trailing" in error for error in errors)


@pytest.mark.parametrize(
    "pairs",
    [
        None,
        "()",
        {},
        [],
        [None],
        ["()"],
        [{}],
        [{"from": "w001"}],
        [{"from": [], "through": "w004"}],
        [{"from": "w001", "through": {}}],
        [{"from": "w001", "through": "w999"}],
        [{"from": "w004", "through": "w001"}],
        [{"from": "w001", "through": "w004", "text": "Hic genuflectitur"}],
        [{"from": "w001", "through": "w004", "condition": "paschal"}],
        [{"from": "w001", "through": "w004", "opening": "["}],
        [{"from": "w001", "through": "w004", "closing": "before-post"}],
        [{"from": "w001", "through": "w004", "closing": None}],
        [{"from": "w001", "through": "w004", "closing": []}],
        [{"from": "w001", "through": "w004", "closing": True}],
        [{"from": "w001", "through": "w004"}] * 2,
        [{"from": "w001", "through": "w004"}, {"from": "w002", "through": "w003"}],
        [{"from": "w001", "through": "w003"}, {"from": "w002", "through": "w004"}],
        [{"from": "w001", "through": "w002"}, {"from": "w002", "through": "w004"}],
        [{"from": "w003", "through": "w004"}, {"from": "w001", "through": "w002"}],
    ],
)
def test_invalid_pair_shapes_fail_all_neutral_entry_points(tmp_path, pairs):
    doc = paired_text()
    doc["localization"] = {"about": True}
    doc["segments"][0]["parentheses"] = pairs
    assert check_parentheses(doc["segments"][0])
    assert any("parentheses" in error for error in lint_text(doc)[0])
    assert any("parentheses" in error for error in check_core(doc))
    with pytest.raises(ValueError, match="parentheses"):
        corpus_tokens(doc)
    errors, warnings, stats = collate(doc, tmp_path)
    assert errors and not warnings
    assert stats["words"] == stats["witnesses"] == 0


@pytest.mark.parametrize("post", [None, "", "..", ".)", 3, []])
def test_after_post_requires_one_existing_ordinary_mark(post):
    segment = paired_text()["segments"][0]
    segment["parentheses"][0]["closing"] = "after-post"
    if post is not None:
        segment["words"][-1]["post"] = post
    assert any("valid ordinary post" in error for error in check_parentheses(segment))


@pytest.mark.parametrize("post", list(",.;:?!"))
def test_both_closing_orders_preserve_the_existing_mark(post):
    segment = paired_text()["segments"][0]
    segment["words"][-1]["post"] = post
    default = source_payload(segment)
    assert word_faces(segment)[-1].suffix == ")" + post
    segment = deepcopy(segment)
    segment["parentheses"][0]["closing"] = "after-post"
    assert check_parentheses(segment) == []
    assert word_faces(segment)[-1].suffix == post + ")"
    assert canonical_hash(default) != canonical_hash(source_payload(segment))


def test_source_order_is_not_numeric_id_order_and_single_word_pairs_are_valid():
    segment = paired_text()["segments"][0]
    for word, wid in zip(segment["words"], ["w060", "w018", "w002", "w055"], strict=True):
        word["id"] = wid
    segment["parentheses"] = [
        {"from": "w060", "through": "w018"},
        {"from": "w055", "through": "w055"},
    ]
    assert check_parentheses(segment) == []
    assert " ".join(face.text for face in word_faces(segment)) == "(quem suscitávit) ex (mórtuis)"
    assert word_faces(segment)[0].prefix == "("
    assert word_faces(segment)[0].form == "quem"


def test_rubrics_cross_segment_retired_and_duplicate_ids_do_not_supply_endpoints():
    doc = paired_text()
    other = {
        "id": "s02",
        "type": "verse",
        "words": [{"id": "w005", "form": "Amen", "lemma": "amen", "morph": {"pos": "intj"}}],
    }
    doc["segments"].append(other)
    doc["ids"] = {"retired": {"w006": "s01"}}
    for endpoint in ("w005", "w006"):
        doc["segments"][0]["parentheses"][0]["through"] = endpoint
        assert any("same verse" in error for error in lint_text(doc)[0])
    segment = paired_text()["segments"][0]
    segment["type"] = "rubric"
    assert any("only on a verse" in error for error in check_parentheses(segment))
    segment["type"] = "verse"
    segment["words"][1]["id"] = "w001"
    assert any("unique word ids" in error for error in check_parentheses(segment))
    segment["words"] = []
    assert any("live words" in error for error in check_parentheses(segment))


def test_plain_payload_and_face_keep_the_old_exact_contract():
    segment = paired_text()["segments"][0]
    del segment["parentheses"]
    segment["words"][-1]["post"] = "."
    assert source_payload(segment) == {
        "id": "s01",
        "speaker": None,
        "voice": None,
        "words": segment["words"],
    }
    assert corpus_tokens({"segments": [segment]})[-1] == ("w004", "mórtuis.")


def test_new_punctuation_does_not_renew_existing_translation_reviews(tmp_path):
    write_text(tmp_path)
    initialize_all(tmp_path)
    path = tmp_path / "texts/orationes/test.json"
    doc = json.loads(path.read_text())
    doc["segments"][0]["parentheses"] = [{"from": "w001", "through": "w001"}]
    path.write_text(json.dumps(doc))
    errors, _ = check(tmp_path)
    assert len([error for error in errors if "stale source_sha256" in error]) == 2


def test_endpoint_change_alters_the_source_binding():
    segment = paired_text()["segments"][0]
    before = canonical_hash(source_payload(segment))
    segment["parentheses"][0]["from"] = "w002"
    assert canonical_hash(source_payload(segment)) != before


def test_apparatus_span_must_quote_parentheses_and_still_needs_real_support(tmp_path):
    doc = paired_text()
    directory = witnesses(
        tmp_path,
        {"a": "(quem suscitávit ex mórtuis)", "b": "qui surrexit"},
        [
            {
                "at": "w001",
                "through": "w004",
                "ours": "(quem suscitávit ex mórtuis)",
                "witnesses": {"b": "qui surrexit"},
                "class": "substantive-span",
                "ruling": "Retain the complete phrase attested by the first witness.",
            }
        ],
    )
    errors, _, stats = collate(doc, directory)
    assert errors == [] and stats["substantive_spans"] == 1
    path = directory / "apparatus.json"
    apparatus = json.loads(path.read_text())
    apparatus["adjudicated"][0]["ours"] = "quem suscitávit ex mórtuis"
    path.write_text(json.dumps(apparatus))
    assert any("exact complete source-token" in error for error in collate(doc, directory)[0])
