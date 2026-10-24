"""The selected neuter manna paradigm keeps its two existing contexts."""

import json
from pathlib import Path

import pytest
from gospel_delivery_fixture import (
    current_gospel_selected_hash,
    current_gospel_source_hash,
    without_gospel_delivery,
)

from build_reader.bibliography_bindings import digest, selected_text
from build_reader.layers import expand_core
from checks.lexicon import check_paradigm, check_text_against_lexicon, lint_lemmata
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parent.parent
PENDING = {"confidence": "high", "sources": ["editorial"], "review": "pending"}
CONTEXTS = (
    {
        "text": "proprium.corporis-christi-evangelium",
        "segment": "s05",
        "word": "w065",
        "case": "acc",
        "confirmed": ["whitakers"],
        "source_before": "23f4f8abb4f0ff98d3183e4b4fcbb0f17e6453e6a514b2a680387d2dd0575e9e",
        "source_after": "41730fa45f4936b51ae1c6147a06c834f5de31c5dd2a7c8317834116ef244391",
        "selected": "1ca2544c5e0eb28333a14c200d137beb0c55e0a69b2d245dda30459640103dbd",
        "targets": {
            "pl": "505ee7c929cb943560c11bcd03df2f28756fb92c8452b8eefd9032f5f0f421e5",
            "en": "923e7c5e64e6c4de57c07d4b92b2a0bd224a07d40138b4060bf4f461d4512b86",
        },
    },
    {
        "text": "proprium.corporis-christi-sequentia",
        "segment": "s22",
        "word": "w245",
        "case": "nom",
        "confirmed": ["whitakers", "collatinus"],
        "source_before": "1322b6764c17063c91f885d2e8d75448876e60328450058585bbe2fa4ff16306",
        "source_after": "cfa70ea64e26f1c8e84047de8051480bde7d1d64d57e59b5d21f69ec4c951aee",
        "selected": "6c6370c6ebe0f5683e05321226dc3fe95824b1e6161c884783ca3497dffcc6c9",
        "targets": {
            "pl": "e3e2f0b4ba9db86840ea91220b044db806d8e360e9cf4fea8204f20b12a43ae3",
            "en": "bc268f018770283172dcd45575743360d0f31d23b28ebc704fdd197e7c776cbd",
        },
    },
)


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def core(text_id):
    return read("texts/" + text_id.replace(".", "/", 1) + ".json")


def chosen_entry():
    return {"head": "manna", "pos": "noun", "gender": "n"}


def minimal_text():
    return {
        "id": "proprium.example",
        "segments": [
            {
                "words": [
                    {
                        "id": "w001",
                        "lemma": "manna",
                        "morph": {"pos": "noun", "case": "acc", "number": "sg", "gender": "n"},
                    }
                ]
            }
        ],
    }


def test_selected_indeclinable_entry_and_token_are_complete_without_a_number():
    entries = {"manna": chosen_entry()}
    assert lint_lemmata(entries) == []
    assert check_paradigm(entries) == []
    assert check_paradigm({"entries": entries}) == []
    assert check_text_against_lexicon(minimal_text(), entries) == []


@pytest.mark.parametrize(
    "numbered",
    [{field: value} for field in ("decl", "decl_alt") for value in (1, 2, 3, 4, 5, None)]
    + [{"decl": 1, "decl_alt": 3}, {"decl": 3, "decl_alt": 1}],
)
def test_false_present_paradigm_is_rejected_at_lemma_and_token(numbered):
    entry = dict(chosen_entry(), **numbered)
    assert any("indeclinable" in e for e in lint_lemmata({"manna": entry}))
    assert any("indeclinable" in e for e in check_paradigm({"manna": entry}))
    doc = minimal_text()
    doc["segments"][0]["words"][0]["morph"].update(numbered)
    assert any(
        "indeclinable" in e for e in check_text_against_lexicon(doc, {"manna": chosen_entry()})
    )


@pytest.mark.parametrize("head", ["manna, -æ", "manna, mannæ"])
def test_selected_head_cannot_suggest_the_distinct_feminine_paradigm(head):
    entry = dict(chosen_entry(), head=head)
    assert lint_lemmata({"manna": entry})
    assert check_paradigm({"manna": entry})


@pytest.mark.parametrize(
    "facts", [{"pos": "adv"}, {"gender": "f"}, {"gender_alt": "f"}, {"gender_pl": "f"}]
)
def test_selected_noun_identity_is_not_an_indeclinability_shortcut(facts):
    entry = dict(chosen_entry(), **facts)
    assert lint_lemmata({"manna": entry})
    assert check_paradigm({"manna": entry})
    doc = minimal_text()
    doc["segments"][0]["words"][0]["morph"].update(facts)
    assert check_text_against_lexicon(doc, {"manna": chosen_entry()})


def test_other_nouns_still_need_their_own_paradigm():
    ordinary = {"pater": {"head": "pater, patris", "pos": "noun", "gender": "m"}}
    assert any("no declension recorded" in e for e in check_paradigm(ordinary))
    ordinary["pater"]["decl"] = 3
    assert check_paradigm(ordinary) == []
    assert check_paradigm({"manna-imitation": chosen_entry()})
    # A distinct feminine entry remains possible, not an exception to all Hebrew nouns.
    feminine = {"manna-feminine": {"head": "manna, -æ", "pos": "noun", "gender": "f", "decl": 1}}
    assert lint_lemmata(feminine) == []
    assert check_paradigm(feminine) == []
    # Existing irregular/Greek/Hebrew treatment is not turned into a numbered-paradigm ban.
    for lemma, entry in {
        "Moyses": {"head": "Móyses, Móysis", "pos": "noun", "gender": "m", "decl": 3},
        "Abraham": {"head": "Ábraham", "pos": "noun", "gender": "m", "decl": 1},
    }.items():
        assert check_paradigm({lemma: entry}) == []


def test_actual_entry_has_exactly_the_two_existing_consumers():
    lemmata = read("lexicon/lemmata.json")
    entry = lemmata["entries"]["manna"]
    assert entry == chosen_entry()
    assert entry.get("analysis", lemmata["analysis_defaults"]) == PENDING
    actual = set()
    for path in (ROOT / "texts").rglob("*.json"):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for segment in doc.get("segments", []):
            for word in segment.get("words", []):
                if word.get("lemma") == "manna":
                    actual.add((doc["id"], segment["id"], word["id"]))
    assert actual == {(c["text"], c["segment"], c["word"]) for c in CONTEXTS}


@pytest.mark.parametrize("context", CONTEXTS, ids=lambda c: c["segment"])
def test_existing_form_case_and_pending_editorial_analysis_are_preserved(context):
    doc = core(context["text"])
    segment = next(s for s in doc["segments"] if s["id"] == context["segment"])
    word = next(w for w in segment["words"] if w["id"] == context["word"])
    assert word["form"] == word["lemma"] == "manna"
    assert word["morph"] == {
        "pos": "noun",
        "case": context["case"],
        "number": "sg",
        "gender": "n",
    }
    expected = {**PENDING, "sources": ["editorial", *context["confirmed"]]}
    assert doc["editorial"]["words"][word["id"]] == {"analysis": expected}
    expanded = expand_core(doc)
    token = next(
        w for s in expanded["segments"] for w in s.get("words", []) if w["id"] == context["word"]
    )
    assert token["analysis"] == expected
    # Compatible analyzer votes do not approve the editorial review or a numbered paradigm.
    assert token["analysis"]["review"] == "pending"
    assert "decl" not in token["morph"]


@pytest.mark.parametrize("context", CONTEXTS, ids=lambda c: c["segment"])
def test_annotation_change_rebinds_only_sources_not_targets_or_selected_latin(context):
    doc = core(context["text"])
    segment = next(s for s in doc["segments"] if s["id"] == context["segment"])
    assert canonical_hash(source_payload(segment)) == current_gospel_source_hash(
        context["text"], context["segment"], context["source_after"]
    )
    legacy = without_gospel_delivery(doc)
    old_segment = next(s for s in legacy["segments"] if s["id"] == context["segment"])
    next(w for w in old_segment["words"] if w["id"] == context["word"])["morph"]["decl"] = 3
    assert canonical_hash(source_payload(old_segment)) == context["source_before"]
    assert selected_text(without_gospel_delivery(doc)) == selected_text(legacy)
    assert digest(selected_text(doc)) == current_gospel_selected_hash(
        context["text"], context["selected"]
    )
    graph = read("bibliography/graph.json")
    collations = [c for c in graph["collations"] if c["text"] == context["text"]]
    assert len(collations) == 1
    assert collations[0]["selected_text_sha256"] == current_gospel_selected_hash(
        context["text"], context["selected"]
    )
    assert collations[0]["review"]["status"] == "pending"
    for language in ("pl", "en"):
        relative = context["text"].replace(".", "/", 1) + ".json"
        layer = read(f"languages/{language}/texts/{relative}")
        expected_gloss = "mannę" if language == "pl" and context["case"] == "acc" else "manna"
        assert layer["words"][context["word"]]["gloss"] == expected_gloss
        target = layer["segments"][context["segment"]]["translation"]
        assert canonical_hash(target) == context["targets"][language]
        site = f"{context['text']}.{context['segment']}.{language}"
        rows = [
            r
            for r in read(f"languages/{language}/translation-provenance.json")["sites"]
            if r["site"] == site
        ]
        assert len(rows) == 1
        row = rows[0]
        assert row["source_sha256"] == current_gospel_source_hash(
            context["text"], context["segment"], context["source_after"]
        )
        assert row["target_sha256"] == context["targets"][language]
        assert row["origin"] == "working-unsettled"
        assert row["review"] == "working"
        assert row["familiar_core"] is False
