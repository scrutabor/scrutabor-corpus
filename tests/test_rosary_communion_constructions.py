"""Rosary Communion: complete meaning, narrow groups and recoverable faults."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from rosary_communion_fixture import (
    DATA,
    TEXT,
    healthy_rosary,
    predecessor_rosary_core,
    predecessor_rosary_layer,
    predecessor_rosary_wording,
    reviewed_rosary,
    rosary_opening_case,
)

from build_reader import emit, store
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
FORMS = (
    "Floréte",
    "flores",
    "quasi",
    "lílium",
    "et",
    "date",
    "odórem",
    "et",
    "frondéte",
    "in",
    "grátiam",
    "collaudáte",
    "cánticum",
    "et",
    "benedícite",
    "Dóminum",
    "in",
    "opéribus",
    "suis",
)
LITERAL = {
    "pl": [
        (["w001", "w002"], "Wydawajcie kwiaty", "Pozbądźcie się kwiatów"),
        (["w009", "w010", "w011"], "wypuszczajcie piękne liście", "dziękujcie za liście"),
        (["w012", "w013"], "wznoście pieśń chwały", "chwalcie tę pieśń"),
    ],
    "en": [
        (["w001", "w002"], "Put forth blossoms", "Throw away blossoms"),
        (["w009", "w010", "w011"], "put forth lovely leaves", "enter a state of grace"),
        (["w012", "w013"], "sing a song of praise", "praise the composition"),
        (["w018", "w019"], "His works", "your own works"),
    ],
}
PROSE = {
    "pl": (
        "Wydawajcie kwiaty jak lilia, roztaczajcie woń i wypuszczajcie piękne liście; "
        "wznoście pieśń chwały i błogosławcie Pana w Jego dziełach."
    ),
    "en": (
        "Put forth blossoms like the lily, give forth fragrance and put forth lovely leaves; "
        "sing a song of praise and bless the Lord in His works."
    ),
}
GROUPS = [
    pytest.param(lang, members, gloss, wrong, id=f"{lang}-{members[0]}")
    for lang, rows in LITERAL.items()
    for members, gloss, wrong in rows
]
KEEP = {
    "pl": {
        "w003": "jak",
        "w004": "lilia",
        "w005": "i",
        "w006": "roztaczajcie",
        "w007": "woń",
        "w008": "i",
        "w014": "i",
        "w015": "błogosławcie",
        "w016": "Pana",
        "w017": "w",
        "w018": "dziełach",
        "w019": "Jego",
    },
    "en": {
        "w003": "like",
        "w004": "the lily",
        "w005": "and",
        "w006": "yield",
        "w007": "fragrance",
        "w008": "and",
        "w014": "and",
        "w015": "bless",
        "w016": "the Lord",
        "w017": "in",
    },
}
KEEPS = [
    pytest.param(lang, wid, value, id=f"{lang}-{wid}")
    for lang, entries in KEEP.items()
    for wid, value in entries.items()
]
NOTE_WORDS = ["w002", "w011", "w012", "w019"]


def load(language):
    return store.core(ROOT, TEXT), store.raw_layer(ROOT, language, TEXT)


def exact_group(layer, members, gloss):
    groups = layer["segments"]["s01"]["alignments"]
    touching = [g for g in groups if set(g["words"]) & set(members)]
    expected = [{"words": members, "anchor": members[0], "gloss": gloss}]
    assert touching == expected, "Rosary semantic group"
    assert all("gloss" not in layer["words"][wid] for wid in members), "Rosary semantic group"


def meaning(core, layer):
    words = core["segments"][0]["words"]
    assert tuple(w["form"] for w in words) == FORMS, "Rosary source stream"
    assert [words[i]["morph"]["case"] for i in (1, 3)] == ["acc", "nom"], "Rosary adopted parse"
    assert words[9]["morph"]["governs"] == "acc", "Rosary adopted parse"
    assert words[16]["morph"]["governs"] == "abl", "Rosary adopted parse"
    assert all(
        words[i]["morph"]["mood"] == "imp"
        and words[i]["morph"]["person"] == 2
        and words[i]["morph"]["number"] == "pl"
        for i in (0, 5, 8, 11, 14)
    )
    for members, gloss, _ in LITERAL[layer["language"]]:
        exact_group(layer, members, gloss)
    for wid, value in KEEP[layer["language"]].items():
        assert layer["words"][wid]["gloss"] == value, "Rosary retained caption"
    assert layer["segments"]["s01"]["translation"] == PROSE[layer["language"]], "Rosary full prose"
    for wid in NOTE_WORDS:
        expected = DATA["layers"][layer["language"]]["after"]["words"][wid]["explanation"]
        assert layer["words"][wid]["explanation"] == expected, "Rosary contextual help"


def compact(core, layer):
    doc, localized = expand_core(core), enrich_layer(core, layer)
    tables = [emit.Table() for _ in range(4)]
    return (
        emit.core_artifact(doc, core, *tables[:3]),
        emit.language_artifact(doc, localized, tables[3]),
        [table.order for table in tables],
    )


@pytest.mark.parametrize("language", ["pl", "en"])
def test_whole_current_subject_reader_and_historical_copies(language):
    core, layer = load(language)
    saved = deepcopy((core, layer, DATA))
    healthy_rosary(core, layer)
    meaning(core, layer)
    reviewed_rosary(core, layer)
    assert predecessor_rosary_core(core) == DATA["core_before"]
    assert predecessor_rosary_layer(layer) == DATA["layers"][language]["before"]
    assert core["editorial"] == DATA["core_before"]["editorial"]
    ids = [f"w{i:03}" for i in range(1, 20)]
    assert list(layer["words"]) == ids
    assert layer["words"] == DATA["layers"][language]["after"]["words"]
    for wid in ids:
        groups = [g for g in layer["segments"]["s01"]["alignments"] if wid in g["words"]]
        assert ("gloss" in layer["words"][wid]) + len(groups) == 1
    ledger = json.loads((ROOT / "languages" / language / "translation-provenance.json").read_text())
    (row,) = [r for r in ledger["sites"] if r["site"] == f"{TEXT}.s01.{language}"]
    assert row == DATA["layers"][language]["row_after"]
    assert row["source_sha256"] == canonical_hash(source_payload(core["segments"][0]))
    assert row["target_sha256"] == canonical_hash(PROSE[language])
    old, target = predecessor_rosary_wording(row, PROSE[language])
    assert old == DATA["layers"][language]["row_before"]
    assert canonical_hash(target) == old["target_sha256"]
    base, artifact, tables = compact(core, layer)
    want, layers = emit._strip(expand_core(core), {language: enrich_layer(core, layer)})
    assert emit.expand(base, artifact, *tables) == (want, layers[language])
    _, decoded = emit.expand(base, artifact, *tables)
    for members, gloss, _ in LITERAL[language]:
        exact_group(decoded, members, gloss)
    assert (core, layer, DATA) == saved


@pytest.mark.parametrize("language,members,gloss,wrong", GROUPS)
@pytest.mark.parametrize("fault", ["residual", "duplicate", "reversed", "outside-anchor"])
def test_actual_native_group_fault_and_same_layer_recovery(language, members, gloss, wrong, fault):
    core, layer = load(language)
    healthy_rosary(core, layer)
    exact_group(layer, members, gloss)
    saved = deepcopy(layer)
    groups = layer["segments"]["s01"]["alignments"]
    group = next(g for g in groups if g["words"] == members)
    try:
        if fault == "residual":
            layer["words"][members[0]]["gloss"] = "control"
            message = "expected exactly one direct gloss or alignment"
        elif fault == "duplicate":
            groups.insert(groups.index(group) + 1, deepcopy(group))
            message = "belongs to more than one alignment"
        elif fault == "reversed":
            group["words"].reverse()
            message = "contiguous and in source order"
        else:
            group["anchor"] = "w007" if "w007" not in members else "w008"
            message = "anchor must name the source word carrying the gloss"
        assert layer != saved
        assert any(message in e for e in interlinear.check(core, layer))
        path = store.layer_path(ROOT, language, TEXT)
        assert any(message in e for e in language_packs.check_layer(core, layer, path))
    finally:
        layer.clear()
        layer.update(saved)
    healthy_rosary(core, layer)
    meaning(core, layer)


@pytest.mark.parametrize("language,members,gloss,wrong", GROUPS)
def test_valid_shape_does_not_approve_wrong_meaning(language, members, gloss, wrong):
    core, layer = load(language)
    healthy_rosary(core, layer)
    saved = deepcopy(layer)
    group = next(g for g in layer["segments"]["s01"]["alignments"] if g["words"] == members)
    try:
        group["gloss"] = wrong
        assert layer != saved
        healthy_rosary(core, layer)
        with pytest.raises(AssertionError, match=r"^Rosary semantic group(?:\n|$)"):
            exact_group(layer, members, gloss)
    finally:
        layer.clear()
        layer.update(saved)
    healthy_rosary(core, layer)
    meaning(core, layer)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_foliage_group_cannot_steal_its_conjunction(language):
    core, layer = load(language)
    healthy_rosary(core, layer)
    saved = deepcopy(layer)
    members, gloss, _ = LITERAL[language][1]
    group = next(g for g in layer["segments"]["s01"]["alignments"] if g["words"] == members)
    try:
        del layer["words"]["w008"]["gloss"]
        group["words"].insert(0, "w008")
        healthy_rosary(core, layer)
        with pytest.raises(AssertionError, match=r"^Rosary semantic group(?:\n|$)"):
            exact_group(layer, members, gloss)
    finally:
        layer.clear()
        layer.update(saved)
    healthy_rosary(core, layer)
    meaning(core, layer)


@pytest.mark.parametrize("language,members,gloss,wrong", GROUPS)
@pytest.mark.parametrize("fault", ["gloss", "anchor"])
def test_actual_compact_group_corruption_and_recovery(language, members, gloss, wrong, fault):
    core, layer = load(language)
    healthy_rosary(core, layer)
    base, artifact, tables = compact(core, layer)
    saved = deepcopy(artifact)
    cell = next(g for g in artifact["seg"][0]["a"] if g["s"] == int(members[0][1:]) - 1)
    try:
        cell["g" if fault == "gloss" else "a"] = wrong if fault == "gloss" else 1
        assert artifact != saved
        _, decoded = emit.expand(base, artifact, *tables)
        assert interlinear.check(core, decoded) == []
        with pytest.raises(AssertionError, match=r"^Rosary semantic group(?:\n|$)"):
            exact_group(decoded, members, gloss)
    finally:
        artifact.clear()
        artifact.update(saved)
    _, decoded = emit.expand(base, artifact, *tables)
    exact_group(decoded, members, gloss)


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("word", ["w002", "w004", "w010", "w017"])
def test_contextual_case_contrast_does_not_retag_every_in_or_neuter(language, word):
    core, layer = load(language)
    healthy_rosary(core, layer)
    saved = deepcopy(core)
    token = next(w for w in core["segments"][0]["words"] if w["id"] == word)
    try:
        field = "case" if word in ("w002", "w004") else "governs"
        token["morph"][field] = {"w002": "voc", "w004": "acc", "w010": "abl", "w017": "acc"}[word]
        assert core != saved
        assert language_packs.check_core(core) == []
        with pytest.raises(AssertionError, match=r"^Rosary adopted parse(?:\n|$)"):
            meaning(core, layer)
    finally:
        core.clear()
        core.update(saved)
    healthy_rosary(core, layer)
    meaning(core, layer)


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("word", NOTE_WORDS)
@pytest.mark.parametrize("fault", ["declaration", "language-scope", "localized-note"])
def test_actual_explanation_topology_fault_and_recovery(language, word, fault):
    core, layer = load(language)
    healthy_rosary(core, layer)
    saved_core, saved_layer = deepcopy(core), deepcopy(layer)
    try:
        if fault == "declaration":
            del core["localization"]["explanations"][word]
        elif fault == "language-scope":
            other = "en" if language == "pl" else "pl"
            core["localization"]["explanations"][word]["languages"] = [other]
        else:
            del layer["words"][word]["explanation"]
        assert (core, layer) != (saved_core, saved_layer)
        errors = language_packs.check_layer(core, layer, store.layer_path(ROOT, language, TEXT))
        assert any("explanation topology differs" in e for e in errors)
    finally:
        core.clear()
        core.update(saved_core)
        layer.clear()
        layer.update(saved_layer)
    healthy_rosary(core, layer)
    meaning(core, layer)


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("fault", ["prose", "help", "extra-layer", "extra-core"])
def test_whole_comparison_never_hides_unadmitted_context(language, fault):
    core, layer = load(language)
    healthy_rosary(core, layer)
    reviewed_rosary(core, layer)
    saved_core, saved_layer = deepcopy(core), deepcopy(layer)
    try:
        if fault == "prose":
            old = DATA["layers"][language]["before"]["segments"]["s01"]["translation"]
            layer["segments"]["s01"]["translation"] = old
        elif fault == "help":
            wrong = {
                "pl": "Zaimek odnosi się do ludzi.",
                "en": "The possessive refers to the people.",
            }
            layer["words"]["w019"]["explanation"] = wrong[language]
        elif fault == "extra-layer":
            layer["about"] += " Added."
        else:
            core["editorial"]["notes"] += " Added."
        healthy_rosary(core, layer)
        message = "complete Rosary core" if fault == "extra-core" else "complete Rosary layer"
        with pytest.raises(AssertionError, match=rf"^{message}(?:\n|$)"):
            if fault == "extra-core":
                predecessor_rosary_core(core)
            else:
                predecessor_rosary_layer(layer)
    finally:
        core.clear()
        core.update(saved_core)
        layer.clear()
        layer.update(saved_layer)
    healthy_rosary(core, layer)
    reviewed_rosary(core, layer)


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("fault", ["missing", "wrong", "extra", "target"])
def test_complete_current_wording_guard_and_same_object_recovery(language, fault):
    core, layer = load(language)
    healthy_rosary(core, layer)
    reviewed_rosary(core, layer)
    ledger = json.loads((ROOT / "languages" / language / "translation-provenance.json").read_text())
    (row,) = [r for r in ledger["sites"] if r["site"] == f"{TEXT}.s01.{language}"]
    assert row == DATA["layers"][language]["row_after"]
    saved_ledger = deepcopy(ledger)
    saved = deepcopy(row)
    target = layer["segments"]["s01"]["translation"]
    saved_target = target
    predecessor_rosary_wording(row, target)
    try:
        if fault == "missing":
            del row["source_sha256"]
        elif fault == "wrong":
            row["target_sha256"] = "0" * 64
        elif fault == "extra":
            row["extra"] = True
        else:
            target += " Added."
        assert row != saved or target != PROSE[language]
        with pytest.raises(AssertionError, match=r"^unchanged wording(?:\n|$)"):
            predecessor_rosary_wording(row, target)
    finally:
        row.clear()
        row.update(saved)
        target = saved_target
    assert row == saved
    assert ledger == saved_ledger
    assert next(r for r in ledger["sites"] if r["site"] == row["site"]) is row
    predecessor_rosary_wording(row, target)
    healthy_rosary(core, layer)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_opening_fixture_is_guarded_without_changing_old_case_identity(language):
    case = DATA["opening_rows"][language]
    fixture = json.loads((ROOT / "tests/fixtures/caption-opening-cases.json").read_text())
    (row,) = [r for r in fixture["first_openings"] if r[0] == language and r[1] == TEXT]
    assert row == case["before"]
    assert rosary_opening_case(row) == case["after"]
    for index, value in [(5, "changed"), (4, "w002"), (6, ["wrong"])]:
        saved = deepcopy(row)
        try:
            row[index] = value
            with pytest.raises(AssertionError, match=r"^historical Rosary opening(?:\n|$)"):
                rosary_opening_case(row)
        finally:
            row[:] = saved
        assert rosary_opening_case(row) == case["after"]


@pytest.mark.parametrize("language,word,value", KEEPS)
def test_every_retained_direct_caption_rejects_a_changed_copy(language, word, value):
    core, layer = load(language)
    healthy_rosary(core, layer)
    meaning(core, layer)
    saved = deepcopy(layer)
    try:
        layer["words"][word]["gloss"] = "control"
        assert value != "control" and layer != saved
        healthy_rosary(core, layer)
        with pytest.raises(AssertionError, match=r"^Rosary retained caption(?:\n|$)"):
            meaning(core, layer)
    finally:
        layer.clear()
        layer.update(saved)
    healthy_rosary(core, layer)
    meaning(core, layer)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_current_opening_requires_its_own_capital_after_the_wording_successor(language):
    core, layer = load(language)
    healthy_rosary(core, layer)
    members, gloss, _ = LITERAL[language][0]
    saved = deepcopy(layer)
    group = layer["segments"]["s01"]["alignments"][0]
    try:
        group["gloss"] = gloss[0].lower() + gloss[1:]
        assert layer != saved
        healthy_rosary(core, layer)
        with pytest.raises(AssertionError, match=r"^Rosary semantic group(?:\n|$)"):
            exact_group(layer, members, gloss)
    finally:
        layer.clear()
        layer.update(saved)
    healthy_rosary(core, layer)
    meaning(core, layer)
