"""The Secret's local compact expressions, referents and reader transport."""

import re
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest
from cena_secret_fixture import (
    DETAILS,
    DIRECT,
    GROUPS,
    SECRET,
    SOURCE,
    assert_secret_scope,
    assert_secret_source,
)

from build_reader import emit, store
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear
from checks import translation_provenance as provenance
from checks.language_packs import check_core, check_layer

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = {
    "actor": ("direct", "w001", "the Father", "Secret emphatic Christ subject"),
    "addressee": ("direct", "w002", "to His Son", "Secret Father addressee"),
    "petitioners": ("direct", "w003", "He asks", "Secret parenthetic petitioners"),
    "vocative": ("shared", "w006", "holy Son", "Secret compact expression: vocative"),
    "object": ("shared", "w010", "Your sacrifice", "Secret compact expression: offering object"),
    "petition": (
        "shared",
        "w012",
        "may You make acceptable",
        "Secret compact expression: third-person petition",
    ),
    "disciples": ("shared", "w015", "to Your disciples", "Secret compact expression: disciples"),
    "reflexive": (
        "shared",
        "w018",
        "in remembrance of the Father",
        "Secret compact expression: reflexive purpose",
    ),
    "hoc-fieri": ("shared", "w020", "this to do", "Secret compact expression: hoc fieri"),
    "institution": (
        "shared",
        "w023",
        "by today’s betrayal",
        "Secret compact expression: institution",
    ),
    "past": ("direct", "w024", "shows", "Secret completed showing"),
}


def subject():
    return store.core(ROOT, SECRET), store.raw_layer(ROOT, "en", SECRET)


def selected_group(layer, wid):
    groups = [a for a in layer["segments"]["s01"]["alignments"] if wid in a["words"]]
    assert len(groups) == 1, "actual compact Secret group"
    return groups[0]


def constants():
    return deepcopy((GROUPS, DIRECT, DETAILS, SOURCE, MUTATIONS))


def test_actual_compact_secret_preserves_all_words_details_and_reader_data():
    core, layer = subject()
    frozen, fixture = deepcopy((core, layer)), constants()
    assert_secret_source(core)
    assert_secret_scope(layer)
    assert check_core(core) == []
    assert check_layer(core, layer, store.layer_path(ROOT, "en", SECRET)) == []
    assert interlinear.check(core, layer) == []
    assert core["localization"]["explanations"] == {
        "w001": {"languages": ["en"]},
        "w024": {"languages": ["en"]},
    }
    polish = store.raw_layer(ROOT, "pl", SECRET)
    assert check_layer(core, polish, store.layer_path(ROOT, "pl", SECRET)) == []
    assert all("explanation" not in polish["words"][wid] for wid in DETAILS)
    ids = [w["id"] for s in core["segments"] for w in s.get("words", [])]
    assert len(ids) == 45
    providers = Counter(wid for wid in ids if layer["words"][wid].get("gloss"))
    providers.update(
        w for s in layer["segments"].values() for a in s.get("alignments", []) for w in a["words"]
    )
    assert providers == Counter(ids)
    expanded, enriched = expand_core(core), enrich_layer(core, layer)
    tables = [emit.Table() for _ in range(4)]
    artifact = emit.core_artifact(expanded, core, *tables[:3])
    language = emit.language_artifact(expanded, enriched, tables[3])
    decoded = emit.expand(artifact, language, *[table.order for table in tables])
    expected_core, expected_layers = emit._strip(expanded, {"en": enriched})
    assert decoded == (expected_core, expected_layers["en"])
    assert all(decoded[1]["words"][wid]["explanation"] == note for wid, note in DETAILS.items())
    assert (core, layer) == frozen and constants() == fixture


@pytest.mark.parametrize("case", tuple(MUTATIONS))
def test_owned_role_and_reading_mutations_are_not_structural_false_passes(case):
    core, layer = subject()
    frozen, fixture = deepcopy((core, layer)), constants()
    assert_secret_scope(layer)
    kind, wid, wrong, diagnostic = MUTATIONS[case]
    bad = deepcopy(layer)
    target = bad["words"][wid] if kind == "direct" else selected_group(bad, wid)
    previous = target["gloss"]
    assert wrong != previous
    target["gloss"] = wrong
    assert bad != layer and interlinear.check(core, bad) == []
    with pytest.raises(AssertionError, match="^" + re.escape(diagnostic) + r"(?:\n|$)"):
        assert_secret_scope(bad)
    target["gloss"] = previous
    assert bad == layer
    assert_secret_scope(bad)
    assert (core, layer) == frozen and constants() == fixture


@pytest.mark.parametrize("case", ("reddat-person", "hoc-case", "fieri-infinitive"))
def test_selected_latin_roles_are_not_changed_to_fit_a_caption(case):
    core, layer = subject()
    frozen, fixture = deepcopy((core, layer)), constants()
    assert_secret_source(core)
    wid, field, wrong = {
        "reddat-person": ("w012", "person", 2),
        "hoc-case": ("w020", "case", "nom"),
        "fieri-infinitive": ("w021", "mood", "part"),
    }[case]
    bad = deepcopy(core)
    word = next(w for s in bad["segments"] for w in s.get("words", []) if w["id"] == wid)
    previous = word["morph"][field]
    assert previous != wrong
    word["morph"][field] = wrong
    assert bad != core
    with pytest.raises(AssertionError, match="^Secret selected source roles: " + wid + r"(?:\n|$)"):
        assert_secret_source(bad)
    word["morph"][field] = previous
    assert bad == core
    assert_secret_source(bad)
    assert (core, layer) == frozen and constants() == fixture


@pytest.mark.parametrize("case", ("missing-each-compact-group", "duplicate-each-scoped-member"))
def test_actual_interlinear_checker_rejects_missing_and_duplicate_membership(case):
    core, layer = subject()
    frozen, fixture = deepcopy((core, layer)), constants()
    assert interlinear.check(core, layer) == []
    words = next(s["words"] for s in core["segments"] if s["id"] == "s01")
    positions = {w["id"]: number for number, w in enumerate(words)}
    groups = [selected_group(layer, f"w{first:03}")["words"] for first, *_ in GROUPS]
    scoped = [f"w{number:03}" for number in list(range(1, 14)) + list(range(15, 25))]
    attempts = groups if case == "missing-each-compact-group" else [[wid] for wid in scoped]
    assert len(attempts) == (8 if case == "missing-each-compact-group" else 23)
    for affected in attempts:
        bad = deepcopy(layer)
        if case == "missing-each-compact-group":
            bad["segments"]["s01"]["alignments"].remove(selected_group(bad, affected[0]))
        elif layer["words"][affected[0]].get("gloss"):
            bad["segments"]["s01"]["alignments"].append({"words": affected, "reason": "word-order"})
            bad["segments"]["s01"]["alignments"].sort(key=lambda a: positions[a["words"][0]])
        else:
            bad["words"][affected[0]]["gloss"] = "duplicate"
        assert bad != layer
        expected = Counter(
            f"{SECRET}:{wid}:en: expected exactly one direct gloss or alignment" for wid in affected
        )
        assert Counter(interlinear.check(core, bad)) == expected
        assert interlinear.check(core, layer) == []
    assert interlinear.check(core, layer) == []
    assert (core, layer) == frozen and constants() == fixture


@pytest.mark.parametrize("wid", ("w001", "w024"))
def test_english_only_help_is_required_without_manufacturing_polish_prose(wid):
    core, layer = subject()
    frozen, fixture = deepcopy((core, layer)), constants()
    assert layer["words"][wid]["explanation"] == DETAILS[wid]
    assert check_layer(core, layer, store.layer_path(ROOT, "en", SECRET)) == []
    bad = deepcopy(layer)
    del bad["words"][wid]["explanation"]
    assert bad != layer
    assert Counter(check_layer(core, bad, store.layer_path(ROOT, "en", SECRET))) == Counter(
        [f"en:{SECRET}: explanation topology differs — missing=['{wid}'] extra=[]"]
    )
    assert_secret_scope(layer)
    assert (core, layer) == frozen and constants() == fixture


def test_caption_help_does_not_promote_the_unsettled_prose_origin(monkeypatch):
    core, layer = subject()
    frozen, fixture = deepcopy((core, layer)), constants()
    site = SECRET + ".s01.en"
    recorded, errors = provenance.load(ROOT)
    assert errors == []
    row = deepcopy(recorded[site])
    assert (row["origin"], row["review"], row["familiar_core"]) == (
        "working-unsettled",
        "working",
        False,
    )
    source = next(s for s in core["segments"] if s["id"] == "s01")
    assert provenance.canonical_hash(provenance.source_payload(source)) == row["source_sha256"]
    target = layer["segments"]["s01"]["translation"]
    assert provenance.canonical_hash(target) == row["target_sha256"]
    current = {site: provenance.corpus_sites(ROOT)[site]}
    selected = {site: deepcopy(row)}
    monkeypatch.setattr(provenance, "corpus_sites", lambda _root: deepcopy(current))
    monkeypatch.setattr(provenance, "load", lambda _root: (deepcopy(selected), []))
    assert provenance.check(ROOT) == ([], {"working-unsettled": 1})
    selected[site]["review"] = "internally-reviewed"
    assert selected[site] != row
    assert provenance.check(ROOT) == (
        [site + ": unsettled origin cannot claim review=internally-reviewed"],
        {"working-unsettled": 1},
    )
    selected[site] = deepcopy(row)
    assert provenance.check(ROOT) == ([], {"working-unsettled": 1})
    assert (core, layer) == frozen and constants() == fixture
