"""Short constructions and separate response boundaries in the first Requiem chants."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.layers import enrich_layer, expand_core
from checks import (
    interlinear,
    interlinear_quality,
    interlinear_sequence,
    language_packs,
    prose,
    translation_integrity,
    translation_punctuation,
)
from checks.lint import lint_gloss
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "commemoratio-omnium-fidelium-defunctorum-missa-i-"
FIXTURE = json.loads(
    (ROOT / "tests/fixtures/all-souls-first-chant-captions.json").read_text(encoding="utf-8")
)
LAYERS = (("communio", "pl"), ("communio", "en"), ("introitus", "pl"), ("introitus", "en"))
GROUPS = (
    ("communio", "w007", "Saints Your"),
    ("communio", "w009", "for ever"),
    ("communio", "w012", "are merciful"),
    ("communio", "w025", "Saints Your"),
    ("communio", "w027", "for ever"),
    ("communio", "w030", "are merciful"),
    ("introitus", "w011", "You befit a hymn"),
    ("introitus", "w024", "Your prayer"),
)
DIRECT = (
    ("introitus", "en", "w019", "shall be rendered"),
    ("introitus", "en", "w030", "shall come"),
    ("introitus", "en", "w023", "hear"),
    ("communio", "pl", "w024", "ze"),
    ("communio", "pl", "w007", "Świętymi"),
    ("communio", "pl", "w025", "Świętymi"),
)


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def load(part, language):
    slug = PREFIX + part
    core = read(f"texts/proprium/{slug}.json")
    layer = read(f"languages/{language}/texts/proprium/{slug}.json")
    return core, layer


def reviewed(core, layer):
    key = core["id"].rsplit("-", 1)[1] + "." + layer["language"]
    expected = deepcopy(FIXTURE["layers"][key])
    # These two English reprise initials have an independently scoped case rule.
    # This construction check accepts only the exact lower/upper initial pair.
    if layer["language"] == "en":
        identifier = "w014" if key.startswith("communio") else "w031"
        assert layer["words"][identifier]["gloss"] in {"rest", "Rest"}, "reviewed chant captions"
        expected["words"][identifier]["gloss"] = layer["words"][identifier]["gloss"]
    assert layer == expected, "reviewed chant captions"


def healthy(core, layer):
    path = ROOT / f"languages/{layer['language']}/texts/proprium/{core['id'].split('.', 1)[1]}.json"
    doc, enriched = expand_core(core), enrich_layer(core, layer)
    assert language_packs.check_core(core) == []
    assert language_packs.check_layer(core, layer, path) == []
    assert interlinear.check(doc, enriched) == []
    assert interlinear_quality.check(doc, enriched) == []
    assert interlinear_sequence.check(doc, enriched) == []
    assert lint_gloss(enriched, doc) == []
    assert prose.check(layer) == []
    assert translation_punctuation.check(layer) == []
    assert translation_integrity.check(doc, layer) == []
    reviewed(core, layer)


def restore(layer, saved):
    layer.clear()
    layer.update(deepcopy(saved))
    assert layer == saved


@pytest.mark.parametrize(
    "part,language",
    LAYERS,
    ids=(
        "communion-pl",
        "communion-en",
        "introit-pl",
        "introit-en",
    ),
)
def test_complete_real_layers_and_working_provenance(part, language):
    core, layer = load(part, language)
    healthy(core, layer)
    (row,) = [
        r
        for r in read(f"languages/{language}/translation-provenance.json")["sites"]
        if r["site"] == f"{core['id']}.s01.{language}"
    ]
    assert (row["origin"], row["review"], row["familiar_core"]) == (
        "working-unsettled",
        "working",
        False,
    )
    assert row["target_sha256"] == canonical_hash(layer["segments"]["s01"]["translation"])
    assert row["source_sha256"] == canonical_hash(source_payload(expand_core(core)["segments"][0]))


def test_complete_latin_and_target_memberships():
    positions = decisions = groups = members = direct = 0
    for part in ("communio", "introitus"):
        core, _ = load(part, "pl")
        words = core["segments"][0]["words"]
        assert [(w["id"], w["form"], w.get("post", "")) for w in words] == [
            tuple(w) for w in FIXTURE["latin"][part]
        ]
        positions += len(words)
        for language in ("pl", "en"):
            _, layer = load(part, language)
            healthy(core, layer)
            counts = {w["id"]: int("gloss" in layer["words"][w["id"]]) for w in words}
            for group in layer["segments"]["s01"].get("alignments", []):
                assert 2 <= len(group["words"]) <= 3 and group["anchor"] in group["words"]
                for identifier in group["words"]:
                    counts[identifier] += 1
                groups += 1
                members += len(group["words"])
            assert set(counts.values()) == {1}
            decisions += len(counts)
            direct += sum("gloss" in entry for entry in layer["words"].values())
    assert (positions, decisions, groups, members, direct) == (71, 142, 8, 17, 125)


@pytest.mark.parametrize(
    "part,start,bad",
    GROUPS,
    ids=(
        "first-possessor",
        "first-duration",
        "first-person",
        "second-possessor",
        "second-duration",
        "second-person",
        "hymn-subject",
        "my-prayer",
    ),
)
def test_actual_group_damage_is_rejected_then_same_layer_recovers(part, start, bad):
    core, layer = load(part, "en")
    healthy(core, layer)
    saved = deepcopy(layer)
    (group,) = [g for g in layer["segments"]["s01"]["alignments"] if g["words"][0] == start]
    try:
        group["gloss"] = bad
        assert layer != saved
        assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
        with pytest.raises(AssertionError, match=r"^reviewed chant captions(?:\n|$)"):
            reviewed(core, layer)
    finally:
        restore(layer, saved)
        healthy(core, layer)


@pytest.mark.parametrize(
    "part,language,identifier,bad",
    DIRECT,
    ids=(
        "vow-future",
        "flesh-future",
        "new-petition",
        "polish-response",
        "first-saints",
        "second-saints",
    ),
)
def test_actual_direct_caption_damage_and_recovery(part, language, identifier, bad):
    core, layer = load(part, language)
    healthy(core, layer)
    saved = deepcopy(layer)
    try:
        layer["words"][identifier]["gloss"] = bad
        assert layer != saved
        with pytest.raises(AssertionError, match=r"^reviewed chant captions(?:\n|$)"):
            reviewed(core, layer)
    finally:
        restore(layer, saved)
        healthy(core, layer)


@pytest.mark.parametrize("part", ("communio", "introitus"), ids=("communion", "introit"))
@pytest.mark.parametrize("fault", ("residual", "duplicate", "anchor"))
def test_actual_topology_rejects_damage_and_recovers(part, fault):
    core, layer = load(part, "en")
    healthy(core, layer)
    saved = deepcopy(layer)
    groups = layer["segments"]["s01"]["alignments"]
    try:
        if fault == "residual":
            layer["words"][groups[0]["words"][0]]["gloss"] = "duplicate"
        elif fault == "duplicate":
            groups.insert(1, deepcopy(groups[0]))
        else:
            groups[0]["anchor"] = "w001"
        assert layer != saved
        errors = interlinear.check(expand_core(core), enrich_layer(core, layer))
        required = {
            "residual": "expected exactly one direct gloss or alignment",
            "duplicate": "belongs to more than one alignment",
            "anchor": "anchor must name the source word carrying the gloss",
        }[fault]
        assert any(required in error for error in errors)
    finally:
        restore(layer, saved)
        healthy(core, layer)


@pytest.mark.parametrize("language", ("pl", "en"))
def test_created_saints_prose_case_and_recovery(language):
    core, layer = load("communio", language)
    healthy(core, layer)
    saved = deepcopy(layer)
    try:
        target = layer["segments"]["s01"]["translation"]
        layer["segments"]["s01"]["translation"] = (
            target.replace("świętych", "Świętych", 1)
            if language == "pl"
            else target.replace("saints", "Saints", 1)
        )
        assert layer != saved
        with pytest.raises(AssertionError, match=r"^reviewed chant captions(?:\n|$)"):
            reviewed(core, layer)
    finally:
        restore(layer, saved)
        healthy(core, layer)


def test_distinct_language_boundaries_and_authorized_polish_initials():
    _, pl = load("communio", "pl")
    _, en = load("communio", "en")
    assert pl["words"]["w024"]["gloss"] == "Ze"
    assert en["words"]["w024"]["gloss"] == "with"
    assert pl["words"]["w014"]["gloss"] == "Odpoczynek"
    _, introit = load("introitus", "pl")
    assert introit["words"]["w031"]["gloss"] == "Odpoczynek"
    assert pl["words"]["w008"]["gloss"] == pl["words"]["w026"]["gloss"] == "Twoimi"
    assert introit["words"]["w025"]["gloss"] == "mojej"
