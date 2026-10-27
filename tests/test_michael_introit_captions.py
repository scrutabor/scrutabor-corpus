"""Finite psalm constructions and source distinctions in the Michael Introit."""

import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

from build_reader import bibliography
from build_reader.bibliography_bindings import validate_bindings
from checks import collate, prose
from checks.language_packs import check_core, check_layer
from checks.translation_provenance import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads(
    (ROOT / "tests/fixtures/michael-introit-captions.json").read_text(encoding="utf-8")
)
TEXT = FIXTURE["text"]
PATH = FIXTURE["path"]
APPARATUS = f"witnesses/{TEXT}/apparatus.json"
GROUP_FAULTS = [
    (language, first, fault)
    for language in ("pl", "en")
    for first, _, _, _ in FIXTURE["groups"][language]
    for fault in ("anchor", "duplicate", "order", "member")
]
SEMANTIC_FAULTS = [
    ("pl", "w026", "są"),
    ("pl", "w017", "błogosław"),
    ("en", "w020", "to the Lord"),
    ("en", "w009", "carried out"),
    ("en", "w058", "carried out"),
    ("en", "w017", "bless"),
    ("en", "w030", "glory"),
    ("en", "w037", "as"),
    ("en", "w049", "amen"),
]
DETAILS = [
    (language, word) for language in ("pl", "en") for word in FIXTURE["explanations"][language]
]
TOPOLOGY = ["missing", "wrong-word", "wrong-language"]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def expected_groups(language):
    return [
        {
            "words": [f"w{i:03}" for i in range(first, last + 1)],
            "anchor": f"w{anchor:03}",
            "gloss": gloss,
        }
        for first, last, anchor, gloss in FIXTURE["groups"][language]
    ]


def problems(target, language):
    errors = []
    if target["segments"]["s01"].get("alignments") != expected_groups(language):
        errors.append("groups")
    direct = {word: entry["gloss"] for word, entry in target["words"].items() if "gloss" in entry}
    reprise = direct.get("w050")
    if reprise not in FIXTURE["reprise_case_successor"][language]:
        errors.append("reprise")
    else:
        direct["w050"] = FIXTURE["direct"][language]["w050"]
    if direct != FIXTURE["direct"][language]:
        errors.append("direct")
    actual = {
        word: entry["explanation"]
        for word, entry in target["words"].items()
        if "explanation" in entry
    }
    if actual != FIXTURE["explanations"][language]:
        errors.append("details")
    return errors


def healthy(core, target, language):
    assert check_core(core) == []
    assert check_layer(core, target, ROOT / f"languages/{language}/{PATH}") == []
    assert prose.check(target) == []
    assert problems(target, language) == []
    assert target["about"] == FIXTURE["about"][language]
    assert target["segments"]["s01"]["translation"] == FIXTURE["prose"][language]
    expected_words = {word: {} for word in FIXTURE["old_words"][language]}
    for word, gloss in FIXTURE["direct"][language].items():
        expected_words[word]["gloss"] = gloss
    expected_words["w050"]["gloss"] = target["words"]["w050"]["gloss"]
    for word, explanation in FIXTURE["explanations"][language].items():
        expected_words[word]["explanation"] = explanation
    assert target["words"] == expected_words
    outside = deepcopy(target)
    outside["words"] = FIXTURE["old_words"][language]
    outside["segments"]["s01"]["translation"] = FIXTURE["original_prose"][language]
    old = FIXTURE["old_alignments"][language]
    if old is None:
        del outside["segments"]["s01"]["alignments"]
    else:
        outside["segments"]["s01"]["alignments"] = old
    assert canonical_hash(outside) == FIXTURE["original_layer_sha256"][language]
    assert core["localization"] == FIXTURE["localization"]
    assert core["editorial"]["source"]["method"] == FIXTURE["method"]
    original = deepcopy(core)
    original["localization"] = FIXTURE["original_localization"]
    original["editorial"]["source"]["method"] = FIXTURE["original_method"]
    assert canonical_hash(original) == FIXTURE["original_core_sha256"]


def subject(language):
    return load(PATH), load(f"languages/{language}/{PATH}")


@pytest.mark.parametrize("language", ["pl", "en"])
def test_complete_short_constructions_and_unchanged_outside(language):
    core, target = subject(language)
    healthy(core, target, language)
    groups = expected_groups(language)
    grouped = [word for group in groups for word in group["words"]]
    assert len(grouped) == len(set(grouped)) == (4 if language == "pl" else 30)
    assert len(groups) == (2 if language == "pl" else 13)
    assert len(FIXTURE["direct"][language]) == (61 if language == "pl" else 35)
    assert set(grouped).isdisjoint(FIXTURE["direct"][language])
    assert set(grouped) | set(FIXTURE["direct"][language]) == {f"w{i:03}" for i in range(1, 66)}

    saved = deepcopy(target)
    for first, last, anchor in ((4, 5, 4), (53, 54, 53)):
        try:
            if language == "pl":
                target["words"][f"w{first:03}"]["gloss"] = "Aniołowie"
                expected_error = "direct"
            else:
                members = [f"w{i:03}" for i in range(first, last + 1)]
                matching = [
                    group
                    for group in target["segments"]["s01"]["alignments"]
                    if group["words"] == members and group["anchor"] == f"w{anchor:03}"
                ]
                assert len(matching) == 1
                matching[0]["gloss"] = "His Angels"
                expected_error = "groups"
            assert target != saved
            assert problems(target, language) == [expected_error]
            with pytest.raises(AssertionError):
                healthy(core, target, language)
        finally:
            target.clear()
            target.update(deepcopy(saved))
        assert target == saved
        healthy(core, target, language)
    try:
        target["segments"]["s01"]["translation"] = FIXTURE["original_prose"][language]
        assert target != saved
        with pytest.raises(AssertionError):
            healthy(core, target, language)
    finally:
        target.clear()
        target.update(deepcopy(saved))
    assert target == saved
    healthy(core, target, language)


@pytest.mark.parametrize(
    "language,first,fault",
    GROUP_FAULTS,
    ids=[f"{language}-{first:03}-{fault}" for language, first, fault in GROUP_FAULTS],
)
def test_exact_group_cannot_change_ownership_or_source_structure(language, first, fault):
    core, target = subject(language)
    healthy(core, target, language)
    saved = deepcopy(target)
    groups = target["segments"]["s01"]["alignments"]
    group = next(g for g in groups if g["words"][0] == f"w{first:03}")
    try:
        if fault == "anchor":
            group["anchor"] = next(word for word in group["words"] if word != group["anchor"])
        elif fault == "duplicate":
            groups.insert(groups.index(group) + 1, deepcopy(group))
        elif fault == "order":
            group["words"].reverse()
        else:
            target["words"][group["words"][0]]["gloss"] = group["gloss"]
        assert target != saved
        assert problems(target, language) == (["direct"] if fault == "member" else ["groups"])
        with pytest.raises(AssertionError):
            healthy(core, target, language)
    finally:
        target.clear()
        target.update(saved)
    assert target == saved
    healthy(core, target, language)


@pytest.mark.parametrize(
    "language,word,wrong",
    SEMANTIC_FAULTS,
    ids=[f"{language}-{word}" for language, word, _ in SEMANTIC_FAULTS],
)
def test_actual_caption_defect_is_rejected_then_same_copy_recovers(language, word, wrong):
    core, target = subject(language)
    healthy(core, target, language)
    saved = deepcopy(target)
    try:
        target["words"][word]["gloss"] = wrong
        assert target != saved and problems(target, language) == ["direct"]
        with pytest.raises(AssertionError):
            healthy(core, target, language)
    finally:
        target.clear()
        target.update(saved)
    assert target == saved
    healthy(core, target, language)


@pytest.mark.parametrize("language,word", DETAILS, ids=[f"{lang}-{word}" for lang, word in DETAILS])
def test_each_contextual_detail_rejects_changed_meaning_and_restores(language, word):
    core, target = subject(language)
    healthy(core, target, language)
    saved = deepcopy(target)
    try:
        target["words"][word]["explanation"] = "The Latin predicate names a completed past event."
        assert target != saved and problems(target, language) == ["details"]
        with pytest.raises(AssertionError):
            healthy(core, target, language)
    finally:
        target.clear()
        target.update(saved)
    assert target == saved
    healthy(core, target, language)


@pytest.mark.parametrize("fault", TOPOLOGY)
def test_real_localization_topology_cannot_lose_or_move_a_requirement(fault):
    core, target = subject("pl")
    healthy(core, target, "pl")
    saved = deepcopy(core)
    requirements = core["localization"]["explanations"]
    try:
        if fault == "missing":
            del requirements["w013"]
        elif fault == "wrong-word":
            requirements["w025"] = requirements.pop("w026")
        else:
            requirements["w013"] = {"languages": ["en"]}
        errors = check_layer(core, target, ROOT / f"languages/pl/{PATH}")
        assert core != saved and any("explanation topology differs" in error for error in errors)
        with pytest.raises(AssertionError):
            healthy(core, target, "pl")
    finally:
        core.clear()
        core.update(saved)
    assert core == saved
    healthy(core, target, "pl")


@pytest.mark.parametrize("language", ["pl", "en"])
def test_only_the_exact_separately_admitted_reprise_case_can_be_composed(language):
    core, target = subject(language)
    healthy(core, target, language)
    saved = deepcopy(target)
    try:
        for permitted in FIXTURE["reprise_case_successor"][language]:
            target["words"]["w050"]["gloss"] = permitted
            healthy(core, target, language)
        target["words"]["w050"]["gloss"] = "Obey"
        assert target != saved and problems(target, language) == ["reprise", "direct"]
        with pytest.raises(AssertionError):
            healthy(core, target, language)
    finally:
        target.clear()
        target.update(saved)
    assert target == saved
    healthy(core, target, language)


def test_polish_gloria_and_real_latin_passive_and_plural_are_preserved():
    core, target = subject("pl")
    healthy(core, target, "pl")
    for number in range(30, 50):
        word = f"w{number:03}"
        assert target["words"][word] == FIXTURE["old_words"]["pl"][word]
    words = {w["id"]: w for s in core["segments"] for w in s["words"]}
    for word in ("w013", "w062"):
        assert words[word]["morph"] == {
            "case": "acc",
            "conj": 4,
            "gender": "f",
            "number": "sg",
            "pos": "verb",
            "tense": "fut",
            "voice": "pass",
            "mood": "part",
        }
    assert words["w026"]["morph"]["number"] == "pl"
    assert words["w020"]["morph"]["case"] == words["w027"]["morph"]["case"] == "dat"


def test_printed_corrigendum_and_supplied_punctuation_are_not_fabricated_variants():
    core = load(PATH)
    apparatus = load(APPARATUS)
    assert apparatus["note"] == FIXTURE["apparatus_note"]
    assert apparatus["adjudicated"] == FIXTURE["original_apparatus_entries"]
    assert apparatus["summary"] == FIXTURE["original_apparatus_summary"]
    assert len(apparatus["adjudicated"]) == 12
    assert not any(entry["at"] in {"w015", "w044"} for entry in apparatus["adjudicated"])
    for name, digest in FIXTURE["witness_raw_sha256"].items():
        assert sha256((ROOT / f"witnesses/{TEXT}/{name}.txt").read_bytes()).hexdigest() == digest
    errors, warnings, stats = collate.collate(core, ROOT / f"witnesses/{TEXT}")
    assert errors == warnings == []
    assert (stats["words"], stats["witnesses"], stats["corrigenda"]) == (65, 2, 1)
    graph, _ = bibliography.load(ROOT)
    row = next(r for r in graph["collations"] if r["text"] == TEXT)
    expected = deepcopy(FIXTURE["collation_before"])
    expected["apparatus_sha256"] = canonical_hash(apparatus)
    assert row == expected and row["review"] == {"status": "pending"}


def test_actual_binding_rejects_stale_apparatus_digest_and_recovers_same_graph():
    graph, _ = bibliography.load(ROOT)
    assert validate_bindings(ROOT, graph) == []
    saved = deepcopy(graph)
    row = next(r for r in graph["collations"] if r["text"] == TEXT)
    try:
        row["apparatus_sha256"] = FIXTURE["original_apparatus_sha256"]
        errors = validate_bindings(ROOT, graph)
        assert graph != saved
        assert any(
            "apparatus_sha256 differs from the complete apparatus" in error for error in errors
        )
        with pytest.raises(AssertionError):
            assert validate_bindings(ROOT, graph) == []
    finally:
        graph.clear()
        graph.update(saved)
    assert graph == saved
    assert validate_bindings(ROOT, graph) == []
