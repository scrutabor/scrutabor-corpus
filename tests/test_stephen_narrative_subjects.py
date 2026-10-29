"""Stephen's final narrative distinguishes the attackers from the martyr."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import emit, store
from build_reader.layers import enrich_layer, expand_core
from checks import english, interlinear, language_packs
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.sancti-stephani-protomartyris-epistola"
RELATIVE = "languages/en/texts/proprium/sancti-stephani-protomartyris-epistola.json"
SOURCE = "490e8f019f26be6a43f97b1daa5ca646ce3959c5bbec375dbe235c7993697c29"
PROSE = "85fff97ad786382a8da468f15a0853649a564e3478f90996295da8da5f4703d0"
CASES = [
    {
        "id": "attackers",
        "word": "w122",
        "lemma": "lapido",
        "number": "pl",
        "tense": "impf",
        "gloss": "they were stoning",
        "missing": "were stoning",
        "wrong": "he was stoning",
    },
    {
        "id": "stephen-cries",
        "word": "w135",
        "lemma": "clamo",
        "number": "sg",
        "tense": "perf",
        "gloss": "he cried out",
        "missing": "cried out",
        "wrong": "they cried out",
    },
    {
        "id": "stephen-sleeps",
        "word": "w149",
        "lemma": "obdormio",
        "number": "sg",
        "tense": "perf",
        "gloss": "he fell asleep",
        "missing": "fell asleep",
        "wrong": "they fell asleep",
    },
]


def native(core, layer):
    assert language_packs.check_layer(core, layer, ROOT / RELATIVE) == []
    doc, localized = expand_core(core), enrich_layer(core, layer)
    assert interlinear.check(doc, localized) == []
    assert english.check(doc, localized) == []


def assert_predicate(core, layer, case):
    words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    word = words[case["word"]]
    assert word["lemma"] == case["lemma"]
    assert {key: word["morph"][key] for key in ("person", "number", "tense", "mood", "voice")} == {
        "person": 3,
        "number": case["number"],
        "tense": case["tense"],
        "mood": "ind",
        "voice": "act",
    }, "Stephen finite source"
    assert not any(
        case["word"] in group["words"] for group in layer["segments"]["s01"].get("alignments", [])
    ), "Stephen finite direct provider"
    assert layer["words"][case["word"]]["gloss"] == case["gloss"], "Stephen finite subject"


def current():
    core, layer = store.core(ROOT, TEXT), store.raw_layer(ROOT, "en", TEXT)
    native(core, layer)
    (segment,) = core["segments"]
    words = {w["id"]: w for w in segment["words"]}
    assert len(words) == 151 and len([w for w in words if "w121" <= w <= "w151"]) == 31
    assert canonical_hash(source_payload(segment)) == SOURCE, "Stephen source binding"
    assert canonical_hash(layer["segments"]["s01"]["translation"]) == PROSE, "Stephen full prose"
    assert words["w120"]["form"] == "Saulus" and words["w120"]["post"] == "."
    assert words["w123"]["morph"]["case"] == "acc"
    assert words["w124"]["head"] == words["w126"]["head"] == "w123"
    assert words["w132"]["head"] == "w134" and words["w134"]["morph"]["case"] == "abl"
    assert words["w138"]["head"] == "w135" and words["w138"]["morph"]["case"] == "nom"
    assert words["w148"]["morph"]["tense"] == "plup"
    assert words["w148"]["morph"]["mood"] == "subj"
    assert words["w151"]["lemma"] == "dominus" and words["w150"]["head"] == "w151"
    for case in CASES:
        assert_predicate(core, layer, case)
    return core, layer


def test_final_narrative_preserves_actors_prose_and_working_binding():
    core, layer = current()
    ledger = json.loads((ROOT / "languages/en/translation-provenance.json").read_bytes())
    (row,) = [r for r in ledger["sites"] if r["site"] == TEXT + ".s01.en"]
    assert row == {
        "site": TEXT + ".s01.en",
        "text": TEXT,
        "segment": "s01",
        "language": "en",
        "familiar_core": False,
        "origin": "working-unsettled",
        "review": "working",
        "source_sha256": SOURCE,
        "target_sha256": PROSE,
    }
    native(core, layer)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
@pytest.mark.parametrize("fault", ["missing", "wrong"])
def test_actual_finite_subject_fault_fails_and_same_input_recovers(case, fault):
    core, original = current()
    changed = deepcopy(original)
    same_input = changed
    try:
        changed["words"][case["word"]]["gloss"] = case[fault]
        native(core, changed)
        with pytest.raises(AssertionError, match=r"^Stephen finite subject(?:\n|$)"):
            assert_predicate(core, changed, case)
    finally:
        changed.clear()
        changed.update(deepcopy(original))
    assert changed is same_input and changed == original
    native(core, changed)
    assert_predicate(core, changed, case)


def test_real_shared_subjects_and_petition_do_not_receive_blanket_pronouns():
    core, layer = current()
    assert layer["words"]["w004"]["gloss"] == "Stephen"
    assert layer["words"]["w009"]["gloss"] == "was working"
    assert layer["words"]["w111"]["gloss"] == "the witnesses"
    assert layer["words"]["w112"]["gloss"] == "laid down"
    assert layer["words"]["w129"]["gloss"] == "receive"
    assert layer["words"]["w132"]["gloss"] == "Kneeling"
    assert layer["words"]["w134"]["gloss"] == "on his knees"
    assert {"words": ["w147", "w148"], "anchor": "w148", "gloss": "he had said this"} in (
        layer["segments"]["s01"]["alignments"]
    )
    native(core, layer)


def test_complete_emitted_subject_faults_reject_and_exact_bytes_recover(reader_copy):
    core, layer = current()
    assert emit.verify(ROOT, reader_copy) == []
    path = reader_copy / RELATIVE
    original = path.read_bytes()
    identifiers = [w["id"] for w in core["segments"][0]["words"]]
    for case in CASES:
        artifact = json.loads(original)
        (segment,) = artifact["seg"]
        index = identifiers.index(case["word"])
        assert segment["g"][index] == case["gloss"]
        segment["g"][index] = case["wrong"]
        try:
            path.write_text(json.dumps(artifact, ensure_ascii=False), encoding="utf-8")
            assert path.read_bytes() != original
            diagnostic = f"{TEXT}: en.words.{case['word']}.gloss:"
            assert any(diagnostic in error for error in emit.verify(ROOT, reader_copy))
        finally:
            path.write_bytes(original)
        assert path.read_bytes() == original
        assert emit.verify(ROOT, reader_copy) == []
    native(core, layer)
