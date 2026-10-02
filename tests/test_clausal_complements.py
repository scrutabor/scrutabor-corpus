"""A clause complement does not lend its external case to its relative subject."""

from copy import deepcopy

import pytest

from build_reader.emit import SCHEMA, Table, core_artifact, expand, language_artifact
from checks.language_packs import check_core
from checks.syntax import check, coverage
from checks.translation_provenance import source_payload


def subject_clause():
    return {
        "id": "test.relative",
        "localization": {"about": True, "explanations": {"w1": {}, "w2": {}}},
        "segments": [
            {
                "id": "s01",
                "type": "verse",
                "words": [
                    {
                        "id": "w1",
                        "form": "secundum",
                        "lemma": "secundum",
                        "morph": {"pos": "prep", "governs": "acc"},
                        "clause_head": "w2",
                    },
                    {
                        "id": "w2",
                        "form": "quod",
                        "lemma": "qui",
                        "morph": {"pos": "pron", "case": "nom", "number": "sg", "gender": "n"},
                        "head": "w4",
                    },
                    {
                        "id": "w3",
                        "form": "dictum",
                        "lemma": "dico",
                        "morph": {
                            "pos": "verb",
                            "mood": "part",
                            "tense": "perf",
                            "voice": "pass",
                            "case": "nom",
                            "number": "sg",
                            "gender": "n",
                        },
                        "head": "w2",
                    },
                    {
                        "id": "w4",
                        "form": "est",
                        "lemma": "sum",
                        "morph": {
                            "pos": "verb",
                            "mood": "ind",
                            "tense": "pres",
                            "voice": "act",
                            "number": "sg",
                            "person": 3,
                        },
                    },
                ],
            }
        ],
    }


def test_subject_relative_has_its_own_case_not_the_external_accusative():
    value = subject_clause()
    assert check(value) == []
    assert check_core(value) == []
    assert coverage(value) == (2, 2)


@pytest.mark.parametrize("lemma,form", [("dico", "dictum"), ("scribo", "scriptum")])
def test_a_passive_predicate_is_not_a_text_or_lemma_specific_exception(lemma, form):
    value = subject_clause()
    value["segments"][0]["words"][2].update(lemma=lemma, form=form)
    assert check(value) == []


@pytest.mark.parametrize(
    "index,field,replacement",
    [
        (0, "clause_head", "missing"),
        (0, "clause_head", "w3"),
        (0, "clause_head", None),
        (0, "clause_head", ["w2"]),
        (0, "lemma", "cum"),
        (0, "head", "w2"),
        (0, "head", None),
        (0, "substantive", True),
        (0, "ellipsis", "subject"),
        (0, "post", "."),
        (1, "post", ","),
        (2, "post", ";"),
        (1, "lemma", "is"),
        (1, "head", "w3"),
        (2, "head", "w4"),
        (2, "substantive", True),
        (2, "ellipsis", "subject"),
        (3, "lemma", "dico"),
    ],
)
def test_clausal_complement_is_not_a_government_bypass(index, field, replacement):
    value = subject_clause()
    value["segments"][0]["words"][index][field] = replacement
    assert check(value)


@pytest.mark.parametrize(
    "index,field,replacement",
    [
        (0, "pos", "adv"),
        (0, "governs", "abl"),
        (1, "pos", "noun"),
        (1, "case", "acc"),
        (1, "number", "pl"),
        (1, "gender", "m"),
        (2, "pos", "adj"),
        (2, "mood", "inf"),
        (2, "tense", "pres"),
        (2, "voice", "act"),
        (2, "case", "acc"),
        (2, "gender", "m"),
        (2, "number", "pl"),
        (3, "pos", "noun"),
        (3, "mood", "inf"),
        (3, "tense", "fut"),
        (3, "voice", "pass"),
        (3, "number", "pl"),
        (3, "person", 1),
    ],
)
def test_every_feature_of_the_supported_clause_is_checked(index, field, replacement):
    value = subject_clause()
    value["segments"][0]["words"][index]["morph"][field] = replacement
    assert check(value)


def test_an_expressed_antecedent_requires_ordinary_government():
    value = subject_clause()
    words = value["segments"][0]["words"]
    words.insert(
        1,
        {
            "id": "w0",
            "form": "id",
            "lemma": "is",
            "morph": {"pos": "pron", "case": "acc", "number": "sg", "gender": "n"},
        },
    )
    assert check(value)
    words[0].pop("clause_head")
    words[0]["head"] = "w0"
    assert check(value) == []


def test_an_unrelated_or_cross_segment_verb_does_not_supply_a_clause():
    value = subject_clause()
    words = value["segments"][0]["words"]
    words.insert(3, {"id": "w0", "form": "hodie", "lemma": "hodie", "morph": {"pos": "adv"}})
    assert check(value)
    value = subject_clause()
    auxiliary = value["segments"][0]["words"].pop()
    value["segments"].append({"id": "s02", "type": "verse", "words": [auxiliary]})
    assert check(value)


@pytest.mark.parametrize("word_id", ["w1", "w2"])
def test_the_preposition_and_relative_need_contextual_explanations(word_id):
    value = subject_clause()
    del value["localization"]["explanations"][word_id]
    assert any("clausal complement" in error for error in check_core(value))


def test_ordinary_preposition_government_stays_strict():
    value = subject_clause()
    word = value["segments"][0]["words"][0]
    word["head"] = word.pop("clause_head")
    assert any("governs" in error for error in check(value))


def test_clause_relation_is_source_bearing_and_absence_changes_no_legacy_payload():
    segment = subject_clause()["segments"][0]
    before = deepcopy(segment)
    del before["words"][0]["clause_head"]
    old = source_payload(before)
    current = source_payload(segment)
    assert current != old
    assert current["words"][0].pop("clause_head") == "w2"
    assert current == old


def test_clause_field_cannot_be_hidden_on_a_nonpreposition():
    value = subject_clause()
    value["segments"][0]["words"][1]["clause_head"] = "w4"
    assert check(value)


def test_clause_relation_survives_reader_transport_without_inventing_an_antecedent():
    assert SCHEMA == "5.8.0"
    stored = subject_clause()
    doc = deepcopy(stored)
    doc.pop("localization")
    doc.update(status="working", analysis_defaults={"review": "pending"})
    layer = {
        "lang": "pl",
        "about": "Test",
        "words": {word["id"]: {"gloss": word["form"]} for word in doc["segments"][0]["words"]},
    }
    parses, analyses, citations, local_citations = (Table() for _ in range(4))
    compact = core_artifact(doc, stored, parses, analyses, citations)
    local = language_artifact(doc, layer, local_citations)

    def decode(value):
        return expand(
            value, local, parses.order, analyses.order, citations.order, local_citations.order
        )[0]

    assert compact["seg"][0]["w"][0]["ch"] == "w2"
    assert "h" not in compact["seg"][0]["w"][0]
    assert decode(compact) == doc
    assert len(decode(compact)["segments"][0]["words"]) == 4
    missing = deepcopy(compact)
    del missing["seg"][0]["w"][0]["ch"]
    assert decode(missing) != doc
    assert check(decode(missing))
    redirected = deepcopy(compact)
    redirected["seg"][0]["w"][0]["ch"] = "w3"
    assert check(decode(redirected))


@pytest.mark.parametrize(
    "preposition,case,relative", [("in", "abl", "quo"), ("per", "acc", "quem")]
)
def test_a_relative_really_governed_by_a_preposition_keeps_ordinary_case(
    preposition, case, relative
):
    value = subject_clause()
    words = value["segments"][0]["words"]
    words[:] = words[:2]
    words[0].update(form=preposition, lemma=preposition, morph={"pos": "prep", "governs": case})
    words[0]["head"] = words[0].pop("clause_head")
    words[1].update(
        form=relative, morph={"pos": "pron", "case": case, "number": "sg", "gender": "m"}
    )
    del words[1]["head"]
    assert check(value) == []
    words[1]["morph"]["case"] = "nom"
    assert any("governs" in error for error in check(value))


@pytest.mark.parametrize(
    "first,last",
    [("w1", "w1"), ("w1", "w3"), ("w2", "w2"), ("w2", "w3"), ("w2", "w4"), ("w4", "w4")],
)
def test_parentheses_cannot_split_the_declared_clause(first, last):
    value = subject_clause()
    value["segments"][0]["parentheses"] = [{"from": first, "through": last}]
    assert check(value)


@pytest.mark.parametrize(
    "pair",
    [
        {"from": "w1", "through": "w4"},
        {"from": "w0", "through": "w5"},
        {"from": "w0", "through": "w0"},
        {"from": "w5", "through": "w5"},
        {"from": "w1", "through": "w4", "closing": "after-post"},
    ],
)
def test_whole_clause_enclosing_and_unrelated_parentheses_are_not_boundaries(pair):
    value = subject_clause()
    segment = value["segments"][0]
    words = segment["words"]
    words.insert(0, {"id": "w0", "form": "hodie", "lemma": "hodie", "morph": {"pos": "adv"}})
    words.append({"id": "w5", "form": "etiam", "lemma": "etiam", "morph": {"pos": "adv"}})
    words[-2]["post"] = "."
    segment["parentheses"] = [pair]
    assert check_core(value) == []
    assert check(value) == []


@pytest.mark.parametrize(
    "pairs", [[], None, [{"from": "w2", "through": "missing"}], [{"from": "w4", "through": "w1"}]]
)
def test_invalid_parenthesis_metadata_cannot_validate_a_clause(pairs):
    value = subject_clause()
    value["segments"][0]["parentheses"] = pairs
    assert check(value)
