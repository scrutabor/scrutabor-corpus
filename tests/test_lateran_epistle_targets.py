"""Finite bilingual lesson captions, prose and their actual reader projection."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from lateran_epistle_fixture import (
    DATA,
    TEXT,
    assert_caption,
    before_lateran_rows,
    before_lateran_targets,
)

from build_reader import emit, store
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs, prose
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ["pl", "en"]
WORDS = [f"w{i:03}" for i in range(1, 83)]
DECISIONS = [pytest.param(lang, wid, id=f"{lang}-{wid}") for lang in LANGUAGES for wid in WORDS]


def load(language):
    return store.core(ROOT, TEXT), store.raw_layer(ROOT, language, TEXT)


def healthy(core, layer):
    assert language_packs.check_core(core) == []
    assert (
        language_packs.check_layer(core, layer, store.layer_path(ROOT, layer["language"], TEXT))
        == []
    )
    assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
    assert prose.check(layer) == []


def captions(layer, language):
    for wid in WORDS:
        assert_caption(layer, language, wid)


def exact_prose(layer, language):
    assert layer["segments"]["s01"]["translation"] == DATA["layers"][language]["prose"], (
        "Lateran complete prose"
    )


def compact(core, layer):
    doc, target = expand_core(core), enrich_layer(core, layer)
    tables = [emit.Table() for _ in range(4)]
    return (
        emit.core_artifact(doc, core, *tables[:3]),
        emit.language_artifact(doc, target, tables[3]),
        [t.order for t in tables],
    )


@pytest.mark.parametrize("language", LANGUAGES)
def test_current_native_source_payload_whole_layer_and_reader(language):
    core, layer = load(language)
    saved = deepcopy((core, layer, DATA))
    healthy(core, layer)
    assert len(core["segments"]) == 1
    assert [w["id"] for w in core["segments"][0]["words"]] == WORDS
    assert canonical_hash(source_payload(core["segments"][0])) == DATA["source_sha256"]
    assert canonical_hash(layer) == DATA["layers"][language]["after_sha256"]
    captions(layer, language)
    exact_prose(layer, language)
    assert (
        canonical_hash(before_lateran_targets(layer))
        == (DATA["layers"][language]["negative_sha256"])
    )
    base, target, tables = compact(core, layer)
    wanted_core, wanted = emit._strip(expand_core(core), {language: enrich_layer(core, layer)})
    decoded_core, decoded = emit.expand(base, target, *tables)
    assert (decoded_core, decoded) == (wanted_core, wanted[language])
    captions(decoded, language)
    exact_prose(decoded, language)
    assert (core, layer, DATA) == saved


@pytest.mark.parametrize("language,wid", DECISIONS)
def test_every_bilingual_literal_realization_including_keeps(language, wid):
    _, layer = load(language)
    assert_caption(layer, language, wid)


SEMANTIC = [
    ("future-dwelling", "en", "w033", "He shall dwell"),
    ("future-people", "en", "w040", "shall be"),
    ("future-God", "en", "w046", "shall be"),
    ("negative-inversion", "en", "w068", "there will be"),
    ("future-negative", "en", "w060", "shall not be"),
    ("bride-possessor", "en", "w018", "for His husband"),
    ("tear-subject", "en", "w050", "God will be wiped away"),
    ("eyes-possessor", "en", "w055", "His eyes"),
    ("resultative-scope", "en", "w080", "I make new things"),
    ("substantive-former", "pl", "w071", "dawni"),
    ("negative-scope", "pl", "w068", "będzie"),
    ("predicate-case", "pl", "w038", "lud"),
]


@pytest.mark.parametrize("name,language,wid,value", SEMANTIC, ids=[r[0] for r in SEMANTIC])
def test_literal_contract_rejects_structurally_valid_wrong_readings_then_recovers(
    name, language, wid, value
):
    core, layer = load(language)
    healthy(core, layer)
    assert_caption(layer, language, wid)
    group = next(
        (g for g in layer["segments"]["s01"].get("alignments", []) if wid in g["words"]), None
    )
    entry = group if group is not None else layer["words"][wid]
    saved = deepcopy(entry)
    try:
        assert entry["gloss"] != value
        entry["gloss"] = value
        healthy(core, layer)
        with pytest.raises(AssertionError, match=r"^Lateran literal realization(?:\n|$)"):
            assert_caption(layer, language, wid)
    finally:
        entry.clear()
        entry.update(saved)
        assert entry == saved
        healthy(core, layer)
        captions(layer, language)


NATIVE = [
    ("pl-direct-missing", "pl", "missing"),
    ("en-direct-missing", "en", "missing"),
    ("en-group-provider-duplicate", "en", "duplicate"),
    ("en-group-missing", "en", "group"),
    ("en-anchor-outside", "en", "anchor"),
    ("en-foreign-member", "en", "foreign"),
]


@pytest.mark.parametrize("name,language,fault", NATIVE, ids=[r[0] for r in NATIVE])
def test_real_native_rejection_and_same_layer_recovery(name, language, fault):
    core, layer = load(language)
    saved = deepcopy(layer)
    healthy(core, layer)
    try:
        diagnostic = "expected exactly one direct gloss or alignment"
        if fault == "missing":
            del layer["words"]["w001"]["gloss"]
        elif fault == "duplicate":
            layer["words"]["w050"]["gloss"] = "God"
        else:
            groups = layer["segments"]["s01"]["alignments"]
            group = next(g for g in groups if g["anchor"] == "w050")
            if fault == "group":
                groups.remove(group)
            elif fault == "anchor":
                group["anchor"] = "w049"
                diagnostic = "anchor must name the source word carrying the gloss"
            else:
                group["words"][1] = "w999"
                diagnostic = "alignment names a word outside this segment"
        assert layer != saved
        assert any(diagnostic in e for e in interlinear.check(expand_core(core), layer))
        assert any(
            diagnostic in e
            for e in language_packs.check_layer(core, layer, store.layer_path(ROOT, language, TEXT))
        )
    finally:
        layer.clear()
        layer.update(saved)
        assert layer == saved
        healthy(core, layer)
        captions(layer, language)


READER = [
    ("pl-substantive", "pl", "direct"),
    ("en-negative-order", "en", "direct"),
    ("en-subject", "en", "group"),
    ("en-subject-anchor", "en", "anchor"),
    ("en-subject-missing", "en", "missing"),
    ("en-prose", "en", "prose"),
]


@pytest.mark.parametrize("name,language,fault", READER, ids=[r[0] for r in READER])
def test_actual_compact_reader_damage_and_same_artifact_recovery(name, language, fault):
    core, layer = load(language)
    healthy(core, layer)
    base, target, tables = compact(core, layer)
    saved = deepcopy(target)
    _, decoded = emit.expand(base, target, *tables)
    captions(decoded, language)
    exact_prose(decoded, language)
    cell = target["seg"][0]
    try:
        if fault == "direct":
            position = 70 if language == "pl" else 67
            cell["g"][position] = "pierwsi" if language == "pl" else "there will be"
        elif fault == "prose":
            cell["tr"] = DATA["layers"]["en"]["before_prose"]
        else:
            group = next(g for g in cell["a"] if g["s"] == 49)
            if fault == "group":
                group["g"] = "God will be wiped away"
            elif fault == "anchor":
                group["a"] = 1
            else:
                cell["a"].remove(group)
        assert target != saved
        _, decoded = emit.expand(base, target, *tables)
        diagnostic = "Lateran complete prose" if fault == "prose" else "Lateran literal realization"
        with pytest.raises(AssertionError) as caught:
            exact_prose(decoded, language) if fault == "prose" else captions(decoded, language)
        assert str(caught.value).splitlines()[0] == diagnostic
    finally:
        target.clear()
        target.update(saved)
        assert target == saved
        _, decoded = emit.expand(base, target, *tables)
        captions(decoded, language)
        exact_prose(decoded, language)
        healthy(core, layer)


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("fault", ["missing", "wrong", "extra"])
def test_exact_comparison_inverse_rejects_unaccounted_changes(language, fault):
    core, layer = load(language)
    saved = deepcopy(layer)
    before_lateran_targets(layer)
    try:
        if fault == "missing":
            del layer["words"]["w001"]
        elif fault == "wrong":
            layer["about"] += " Changed."
        else:
            layer["words"]["w001"]["extra"] = True
        with pytest.raises(AssertionError, match=r"^complete Lateran target layer(?:\n|$)"):
            before_lateran_targets(layer)
    finally:
        layer.clear()
        layer.update(saved)
        healthy(core, layer)
        before_lateran_targets(layer)


def assert_row(core, layer, row, language):
    assert row == DATA["ledger"][language]["after"], "Lateran provenance row"
    assert row["source_sha256"] == canonical_hash(source_payload(core["segments"][0]))
    assert row["target_sha256"] == canonical_hash(layer["segments"]["s01"]["translation"])


@pytest.mark.parametrize("language", LANGUAGES)
def test_provenance_and_negative_predecessor_keep_exact_statuses(language):
    core, layer = load(language)
    ledger = json.loads((ROOT / f"languages/{language}/translation-provenance.json").read_text())
    rows = [r for r in ledger["sites"] if r["text"] == TEXT]
    assert len(rows) == 1
    assert_row(core, layer, rows[0], language)
    assert before_lateran_rows(rows) == [DATA["ledger"][language]["before"]]


@pytest.mark.parametrize("field", ["target_sha256", "source_sha256", "origin", "review", "extra"])
def test_exact_english_row_rejects_changed_fields_and_recovers(field):
    core, layer = load("en")
    ledger = json.loads((ROOT / "languages/en/translation-provenance.json").read_text())
    row = next(r for r in ledger["sites"] if r["site"] == DATA["ledger"]["en"]["after"]["site"])
    rows, saved = [row], deepcopy(row)
    assert_row(core, layer, row, "en")
    try:
        row[field] = "wrong"
        with pytest.raises(AssertionError, match=r"^Lateran provenance row(?:\n|$)"):
            assert_row(core, layer, row, "en")
        with pytest.raises(AssertionError, match=r"^complete Lateran target provenance(?:\n|$)"):
            before_lateran_rows(rows)
    finally:
        row.clear()
        row.update(saved)
        assert rows[0] is row and row == saved
        assert_row(core, layer, row, "en")
        assert before_lateran_rows(rows) == [DATA["ledger"]["en"]["before"]]


@pytest.mark.parametrize("index", range(7))
def test_each_old_prose_phrase_is_rejected_without_a_global_grammar_rule(index):
    core, layer = load("en")
    entry = layer["segments"]["s01"]
    saved = deepcopy(entry)
    old, new = DATA["prose_replacements"][index]
    exact_prose(layer, "en")
    try:
        assert entry["translation"].count(new) == 1
        entry["translation"] = entry["translation"].replace(new, old)
        healthy(core, layer)
        with pytest.raises(AssertionError, match=r"^Lateran complete prose(?:\n|$)"):
            exact_prose(layer, "en")
    finally:
        entry.clear()
        entry.update(saved)
        assert layer["segments"]["s01"] is entry and entry == saved
        healthy(core, layer)
        exact_prose(layer, "en")
