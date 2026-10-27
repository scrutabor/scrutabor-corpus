"""The Canon petition retains short phrases, passive patients and its complete prose."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.layers import expand_core
from checks import interlinear, interlinear_quality, language_packs, prose
from checks.translation_provenance import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
TEXT = "ordinarium.hanc-igitur"
LANGUAGES = ("pl", "en")
MUTANTS = (
    ("passive", "Hanc passive source"),
    ("patient", "Hanc shared patient"),
    ("genitive", "Hanc compositional genitive"),
    ("ownership", "Hanc divine possessive"),
    ("passive-caption", "Hanc passive caption contributions"),
    ("caption-genitive", "Hanc exact short groups"),
    ("note", "Hanc exact note and word contributions"),
    ("duplicate", "Hanc once-only group contribution"),
    ("prose", "Hanc preserved outside fields"),
    ("provenance", "Hanc unchanged provenance"),
)
CASES = tuple((language, fault, message) for language in LANGUAGES for fault, message in MUTANTS)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def load(language):
    relative = Path("texts/ordinarium/hanc-igitur.json")
    core = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    layer = json.loads((ROOT / "languages" / language / relative).read_text(encoding="utf-8"))
    rows = json.loads(
        (ROOT / "languages" / language / "translation-provenance.json").read_text(encoding="utf-8")
    )["sites"]
    selected = [row for row in rows if row["text"] == TEXT]
    fixture = json.loads(
        (ROOT / "tests/fixtures/hanc-igitur-captions.json").read_text(encoding="utf-8")
    )
    return core, layer, selected, fixture


def assert_hanc(core, layer, rows, fixture):
    language = layer["language"]
    expected = fixture["languages"][language]
    words = {word["id"]: word for segment in core["segments"] for word in segment.get("words", [])}
    require(core["id"] == layer["text"] == fixture["text"] == TEXT, "Hanc identity")
    require(
        all(
            {key: words[word]["morph"].get(key) for key in ("pos", "mood", "tense", "voice")}
            == {"pos": "verb", "mood": "inf", "tense": "pres", "voice": "pass"}
            for word in ("w027", "w034")
        ),
        "Hanc passive source",
    )
    require(
        words["w026"]["lemma"] == "nos"
        and words["w026"]["morph"] == {"pos": "pron", "case": "acc", "number": "pl"},
        "Hanc shared patient",
    )
    require(
        words["w030"]["lemma"] == "electus"
        and words["w030"]["substantive"] is True
        and words["w030"]["morph"]["case"] == "gen"
        and words["w033"]["lemma"] == "grex"
        and words["w033"]["morph"]["case"] == "abl"
        and words["w029"]["head"] == "w033",
        "Hanc compositional genitive",
    )
    require(
        words["w031"]["lemma"] == "tuus"
        and words["w031"]["head"] == "w030"
        and words["w031"]["morph"] == {"pos": "adj", "case": "gen", "number": "pl", "gender": "m"},
        "Hanc divine possessive",
    )
    require(
        all(
            layer["words"][word].get("gloss") == expected["word_after"][word]["gloss"]
            for word in ("w027", "w034")
        ),
        "Hanc passive caption contributions",
    )
    for sid, groups in expected["groups_after"].items():
        require(layer["segments"][sid].get("alignments") == groups, "Hanc exact short groups")
        require(
            all("gloss" not in layer["words"][word] for group in groups for word in group["words"]),
            "Hanc once-only group contribution",
        )
    require(
        all(layer["words"][word] == value for word, value in expected["word_after"].items()),
        "Hanc exact note and word contributions",
    )
    restored = deepcopy(layer)
    for word, before in expected["word_before"].items():
        restored["words"][word] = deepcopy(before)
    for sid, before in expected["groups_before"].items():
        if before is None:
            del restored["segments"][sid]["alignments"]
        else:
            restored["segments"][sid]["alignments"] = deepcopy(before)
    require(
        canonical_hash(restored) == expected["baseline_layer_sha256"],
        "Hanc preserved outside fields",
    )
    require(
        core["localization"] == {"about": True, "explanations": {"w032": {}}},
        "Hanc declared bilingual explanation",
    )
    restored_core = deepcopy(core)
    del restored_core["localization"]["explanations"]
    require(
        canonical_hash(restored_core) == fixture["core_sha256"],
        "Hanc complete source outside declared note unchanged",
    )
    require(rows == expected["provenance"], "Hanc unchanged provenance")


def assert_healthy(core, layer, rows, fixture):
    assert_hanc(core, layer, rows, fixture)
    assert language_packs.check_core(core) == []
    path = ROOT / "languages" / layer["language"] / "texts/ordinarium/hanc-igitur.json"
    assert language_packs.check_layer(core, layer, path) == []
    assert interlinear.check(expand_core(core), layer) == []
    assert interlinear_quality.check(expand_core(core), layer) == []
    assert prose.check(layer) == []
    for segment in layer["segments"].values():
        for group in segment.get("alignments", []):
            for word in group["words"]:
                assert interlinear.effective_gloss(layer, word) == (
                    group["gloss"] if word == group["anchor"] else ""
                )


@pytest.mark.parametrize("language", LANGUAGES)
def test_current_short_phrases_preserve_source_prose_and_origin(language):
    assert_healthy(*load(language))


@pytest.mark.parametrize(
    "language,fault,message", CASES, ids=[f"{language}-{fault}" for language, fault, _ in CASES]
)
def test_changed_copy_is_rejected_then_restored(language, fault, message):
    original = load(language)
    core, layer, rows, fixture = deepcopy(original)
    saved = deepcopy((core, layer, rows))
    assert_healthy(core, layer, rows, fixture)
    words = {word["id"]: word for segment in core["segments"] for word in segment.get("words", [])}
    if fault == "passive":
        words["w027"]["morph"]["voice"] = "act"
    elif fault == "patient":
        words["w026"]["morph"]["number"] = "sg"
    elif fault == "genitive":
        words["w030"]["morph"]["case"] = "acc"
    elif fault == "ownership":
        words["w031"]["lemma"] = "noster"
    elif fault == "passive-caption":
        layer["words"]["w027"]["gloss"] = "to rescue" if language == "en" else "ratujący"
    elif fault == "caption-genitive":
        group = next(
            group
            for group in layer["segments"]["s03"]["alignments"]
            if group["words"] == ["w030", "w031"]
        )
        group["gloss"] = "Your owners" if language == "en" else "Twoi właściciele"
    elif fault == "note":
        layer["words"]["w032"]["explanation"] = (
            "The chosen ones own the flock."
            if language == "en"
            else "Wybrani są właścicielami trzody."
        )
    elif fault == "duplicate":
        layer["words"]["w030"]["gloss"] = "chosen" if language == "en" else "wybrani"
    elif fault == "prose":
        layer["segments"]["s03"]["translation"] += "!"
    elif fault == "provenance":
        rows[0]["review"] = "working" if rows[0]["review"] != "working" else "internally-reviewed"
    else:
        raise AssertionError("unknown Hanc fault")
    assert canonical_hash((core, layer, rows)) != canonical_hash(saved)
    try:
        with pytest.raises(AssertionError, match=message):
            assert_hanc(core, layer, rows, fixture)
    finally:
        core.clear()
        core.update(deepcopy(saved[0]))
        layer.clear()
        layer.update(deepcopy(saved[1]))
        rows[:] = deepcopy(saved[2])
    assert (core, layer, rows) == saved
    assert_healthy(core, layer, rows, fixture)
    assert original == load(language)


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("fault", ("missing", "wrong-token", "language-scope"))
def test_explanation_declaration_rejects_fault_then_restores(language, fault):
    original = load(language)
    core, layer, rows, fixture = deepcopy(original)
    saved = deepcopy(core)
    path = ROOT / "languages" / language / "texts/ordinarium/hanc-igitur.json"
    assert_healthy(core, layer, rows, fixture)
    if fault == "missing":
        del core["localization"]["explanations"]
    elif fault == "wrong-token":
        core["localization"]["explanations"] = {"w031": {}}
    else:
        other = "en" if language == "pl" else "pl"
        core["localization"]["explanations"]["w032"] = {"languages": [other]}
    assert canonical_hash(core) != canonical_hash(saved)
    missing = "['w031']" if fault == "wrong-token" else "[]"
    expected = f"{language}:{TEXT}: explanation topology differs — missing={missing} extra=['w032']"
    try:
        assert language_packs.check_core(core) == []
        assert language_packs.check_layer(core, layer, path) == [expected]
    finally:
        core.clear()
        core.update(deepcopy(saved))
    assert core == saved
    assert_healthy(core, layer, rows, fixture)
    assert original == load(language)


@pytest.mark.parametrize(
    "slug,word",
    [("hanc-igitur", "w032"), ("hanc-igitur-in-cena-domini", "w052")],
    ids=["ordinary", "holy-thursday"],
)
def test_actual_hanc_explanation_rejects_semicolon_and_restores(slug, word):
    path = ROOT / "languages/en/texts/ordinarium" / f"{slug}.json"
    target = json.loads(path.read_text(encoding="utf-8"))
    original = deepcopy(target)
    assert prose.check(target) == []
    before = target["words"][word]["explanation"]
    current = "flock”. The phrase “of Your"
    predecessor = "flock”; “of Your"
    assert before.count(current) == 1
    changed = before.replace(current, predecessor)
    assert changed != before and changed.count(";") == 1
    target["words"][word]["explanation"] = changed
    assert target != original
    expected = (
        f"ordinarium.{slug}:{word}.explanation.en: uses a semicolon — "
        "this edition's own prose has none. Use a full stop, or an 'and'"
    )
    try:
        assert prose.check(target) == [expected]
    finally:
        target.clear()
        target.update(deepcopy(original))
    assert target == original
    assert prose.check(target) == []
