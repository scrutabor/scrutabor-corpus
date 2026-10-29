"""Dies irae patients and stanza onsets retain their finite source backmaps."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
import test_dies_irae_contextual_captions as historical
from dies_irae_caption_fixture import DATA as HISTORICAL
from dies_irae_caption_fixture import restore_dies_irae_layer
from dies_irae_government_fixture import DATA, before_dies_irae_government_layer, canonical

from build_reader import emit, store
from checks import interlinear, language_packs, prose
from checks.translation_provenance import canonical_hash, source_payload

CORPUS = Path(__file__).resolve().parents[1]
LANGUAGES = ("en", "pl")
CASES = DATA["cases"]
SEMANTIC_MUTANTS = (
    ("en-s12-suppliant", "spare to me as supplicant"),
    ("pl-s12-suppliant", "błagającemu"),
    ("pl-s19-guilty-person", "jemu"),
)
ARTIFACT_MUTANTS = (
    ("en", "s12", "w130", "spare to me as supplicant"),
    ("pl", "s19", "w200", "jemu"),
    ("pl", "s03", "w024", "trąba"),
)


def read(relative, root=CORPUS):
    return json.loads((root / relative).read_text(encoding="utf-8"))


def subject(language):
    raw = (CORPUS / DATA["core_path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == DATA["core_raw_sha256"]
    return json.loads(raw), store.raw_layer(CORPUS, language, DATA["text"])


def source_segment(core, identity):
    return next(row for row in core["segments"] if row["id"] == identity)


def source_words(core, identity):
    # The checking/reader view adds analysis metadata; source fields remain exact.
    return [
        {key: value for key, value in word.items() if key != "analysis"}
        for word in source_segment(core, identity)["words"]
    ]


def provider_trace(core, layer, identity):
    groups = interlinear.alignments_for(layer, identity)
    shared = {word: group for group in groups for word in group["words"]}
    trace = []
    for word in source_segment(core, identity)["words"]:
        word_id = word["id"]
        if word_id in shared:
            group = shared[word_id]
            if word_id == group["words"][0]:
                trace.append({key: group[key] for key in ("words", "anchor", "gloss")})
        else:
            trace.append(
                {
                    "words": [word_id],
                    "anchor": word_id,
                    "gloss": layer["words"][word_id]["gloss"],
                }
            )
    return trace


def assert_case(case, core, layer):
    assert interlinear.check(core, layer) == [], "Dies irae provider structure"
    assert source_words(core, case["segment"]) == case["source_words"], "Dies irae source backmap"
    assert provider_trace(core, layer, case["segment"]) == case["providers"], (
        "Dies irae patient providers"
    )
    assert layer["segments"][case["segment"]]["translation"] == case["translation"], (
        "Dies irae full clause"
    )


def assert_onsets(core, layer):
    for row in DATA["polish_onsets"]:
        assert source_words(core, row["segment"])[0] == row["source_word"]
        assert provider_trace(core, layer, row["segment"])[0] == row["provider"], (
            "Dies irae Polish stanza onset"
        )


def preserved(layer):
    return {
        "about": layer["about"],
        "segments": {
            sid: {key: value for key, value in row.items() if key != "alignments"}
            for sid, row in layer["segments"].items()
        },
        "word_help": {
            wid: {key: value for key, value in row.items() if key != "gloss"}
            for wid, row in layer["words"].items()
        },
    }


def assert_current(core, layer):
    language = layer["language"]
    assert language_packs.check_core(core) == []
    assert language_packs.check_layer(core, layer, CORPUS / DATA["layers"][language]["path"]) == []
    assert interlinear.check(core, layer) == []
    assert prose.check(layer) == []
    for case in CASES:
        if case["language"] == language:
            assert_case(case, core, layer)
    if language == "pl":
        assert_onsets(core, layer)
    assert canonical(preserved(layer)) == DATA["layers"][language]["preserved_sha256"], (
        "Dies irae unchanged prose and help"
    )
    before_dies_irae_government_layer(layer)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_patient_providers_keep_the_complete_stanza_and_exact_source_members(case):
    core, layer = subject(case["language"])
    assert_case(case, core, layer)
    assert [
        word
        for provider in provider_trace(core, layer, case["segment"])
        for word in provider["words"]
    ] == [word["id"] for word in case["source_words"]]


def test_all_nineteen_polish_onsets_keep_their_exact_source_and_provider():
    core, layer = subject("pl")
    assert len(DATA["polish_onsets"]) == 19
    assert_onsets(core, layer)
    assert_current(core, layer)


@pytest.mark.parametrize("language", LANGUAGES)
def test_two_exact_comparison_inverses_preserve_every_historical_constant(language):
    core, layer = subject(language)
    saved = deepcopy(layer)
    rules = deepcopy(DATA)
    old_fixture = deepcopy(HISTORICAL)
    predecessor = before_dies_irae_government_layer(layer)
    assert predecessor is not layer
    assert canonical(predecessor) == DATA["layers"][language]["before_canonical_sha256"]
    old_predecessor = restore_dies_irae_layer(layer)
    assert canonical(old_predecessor) == HISTORICAL["before_canonical"][language]
    assert old_predecessor is not layer and layer == saved
    assert rules == DATA and old_fixture == HISTORICAL
    assert_current(core, layer)


@pytest.mark.parametrize("language", LANGUAGES)
def test_historical_guard_passes_actual_candidate_to_native_checks(monkeypatch, language):
    core, layer = subject(language)
    saved = deepcopy(layer)
    seen = []
    real_pack = language_packs.check_layer
    real_alignment = interlinear.check
    real_prose = prose.check

    def pack(current_core, current_layer, path):
        assert current_core is core and current_layer is layer
        assert canonical(current_layer) == DATA["layers"][language]["after_canonical_sha256"]
        seen.append("pack")
        return real_pack(current_core, current_layer, path)

    def alignment(current_core, current_layer):
        assert current_layer["lang"] == language
        for case in CASES:
            if case["language"] == language:
                assert (
                    provider_trace(current_core, current_layer, case["segment"])
                    == (case["providers"])
                )
        seen.append("alignment")
        return real_alignment(current_core, current_layer)

    def prose_check(current_layer):
        assert current_layer is layer
        seen.append("prose")
        return real_prose(current_layer)

    monkeypatch.setattr(historical.language_packs, "check_layer", pack)
    monkeypatch.setattr(historical.interlinear, "check", alignment)
    monkeypatch.setattr(historical.prose, "check", prose_check)
    historical.healthy(core, layer)
    assert seen == ["pack", "alignment", "prose"]
    assert layer == saved


@pytest.mark.parametrize("case_id,wrong", SEMANTIC_MUTANTS, ids=[r[0] for r in SEMANTIC_MUTANTS])
def test_structurally_valid_patient_regression_fails_then_same_input_recovers(case_id, wrong):
    case = next(row for row in CASES if row["id"] == case_id)
    core, original = subject(case["language"])
    changed = deepcopy(original)
    same_input = changed
    assert_current(core, changed)
    try:
        if case["language"] == "en":
            changed["segments"]["s12"]["alignments"][0]["gloss"] = wrong
        else:
            word = "w129" if case["segment"] == "s12" else "w200"
            changed["words"][word]["gloss"] = wrong
        assert changed != original
        assert interlinear.check(core, changed) == []
        with pytest.raises(AssertionError, match=r"^Dies irae patient providers(?:\n|$)"):
            assert_case(case, core, changed)
    finally:
        changed.clear()
        changed.update(deepcopy(original))
    assert changed is same_input and changed == original
    assert_current(core, changed)


def test_lost_polish_stanza_capital_fails_then_same_input_recovers():
    core, original = subject("pl")
    changed = deepcopy(original)
    same_input = changed
    try:
        changed["words"]["w024"]["gloss"] = "trąba"
        assert interlinear.check(core, changed) == []
        with pytest.raises(AssertionError, match=r"^Dies irae Polish stanza onset(?:\n|$)"):
            assert_onsets(core, changed)
    finally:
        changed.clear()
        changed.update(deepcopy(original))
    assert changed is same_input and changed == original
    assert_current(core, changed)


@pytest.mark.parametrize("fault", ["duplicate-direct", "missing-member"])
def test_real_english_group_fault_reaches_native_checker_and_same_input_recovers(fault):
    core, original = subject("en")
    changed = deepcopy(original)
    same_input = changed
    try:
        if fault == "duplicate-direct":
            changed["words"]["w129"]["gloss"] = "the suppliant"
        else:
            changed["segments"]["s12"]["alignments"][0]["words"].remove("w129")
        assert changed != original
        assert f"{DATA['text']}:w129:en: expected exactly one direct gloss or alignment" in (
            interlinear.check(core, changed)
        )
    finally:
        changed.clear()
        changed.update(deepcopy(original))
    assert changed is same_input and changed == original
    assert_current(core, changed)


def test_missing_polish_patient_reaches_native_checker_and_same_input_recovers():
    core, original = subject("pl")
    changed = deepcopy(original)
    same_input = changed
    try:
        del changed["words"]["w129"]["gloss"]
        assert f"{DATA['text']}:w129:pl: expected exactly one direct gloss or alignment" in (
            interlinear.check(core, changed)
        )
    finally:
        changed.clear()
        changed.update(deepcopy(original))
    assert changed is same_input and changed == original
    assert_current(core, changed)


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize(
    "fault", ["missing-word", "prose", "help", "outside-caption", "extra-field"]
)
def test_exact_copy_inverse_rejects_unrelated_changes_then_same_input_recovers(language, fault):
    core, original = subject(language)
    changed = deepcopy(original)
    same_input = changed
    try:
        if fault == "missing-word":
            del changed["words"]["w129"]
        elif fault == "prose":
            changed["segments"]["s08"]["translation"] += " Amen."
        elif fault == "help":
            changed["words"]["w071"]["explanation"] += " Extra."
        elif fault == "outside-caption":
            changed["words"]["w001"]["gloss"] += " extra"
        else:
            changed["words"]["w129"]["unexpected"] = "extra"
        assert changed != original
        with pytest.raises(AssertionError, match=r"^reviewed Dies irae whole predecessor layer$"):
            restore_dies_irae_layer(changed)
    finally:
        changed.clear()
        changed.update(deepcopy(original))
    assert changed is same_input and changed == original
    assert_current(core, changed)


@pytest.mark.parametrize("language", LANGUAGES)
def test_all_prose_source_target_provenance_rows_remain_exact_and_working(language):
    core, layer = subject(language)
    ledger = read(f"languages/{language}/translation-provenance.json")
    rows = [row for row in ledger["sites"] if row["site"].startswith(DATA["text"] + ".")]
    assert rows == HISTORICAL["provenance"][language] and len(rows) == 19
    for segment in core["segments"]:
        site = f"{DATA['text']}.{segment['id']}.{language}"
        (row,) = [item for item in rows if item["site"] == site]
        assert row["source_sha256"] == canonical_hash(source_payload(segment))
        assert row["target_sha256"] == canonical_hash(
            layer["segments"][segment["id"]]["translation"]
        )
        assert (row["origin"], row["review"], row["familiar_core"]) == (
            "working-unsettled",
            "working",
            False,
        )
    assert_current(core, layer)


@pytest.mark.parametrize("control", DATA["controls"], ids=lambda row: row["id"])
def test_dative_controls_are_finite_and_do_not_ban_other_predicates(control):
    core = store.core(CORPUS, control["text"])
    layer = store.raw_layer(CORPUS, control["language"], control["text"])
    assert source_words(core, control["segment"]) == control["source_words"]
    assert provider_trace(core, layer, control["segment"]) == control["providers"]
    assert layer["segments"][control["segment"]]["translation"] == control["translation"]
    assert interlinear.check(core, layer) == []
    if control["text"] != DATA["text"]:
        comparison = before_dies_irae_government_layer(layer)
        assert comparison is not layer and comparison == layer


@pytest.fixture(scope="module")
def complete_reader_projection(emitted_book):
    assert emit.verify(CORPUS, emitted_book[0]) == []


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.usefixtures("complete_reader_projection")
def test_actual_whole_book_reader_roundtrip_retains_current_providers(reader_out, language):
    core_artifact = read(DATA["core_path"], reader_out)
    layer_artifact = read(DATA["layers"][language]["path"], reader_out)
    core, layer = emit.expand(
        core_artifact,
        layer_artifact,
        read("tables/morphology.json", reader_out),
        read("tables/analysis.json", reader_out),
        read("tables/citations.json", reader_out),
        read(f"languages/{language}/citations.json", reader_out),
    )
    for case in CASES:
        if case["language"] == language:
            assert_case(case, core, layer)
    if language == "pl":
        assert_onsets(core, layer)


@pytest.mark.parametrize(
    "language,segment,word,wrong",
    ARTIFACT_MUTANTS,
    ids=[f"{lang}-{word}" for lang, _segment, word, _wrong in ARTIFACT_MUTANTS],
)
def test_actual_complete_reader_rejects_caption_regression_then_recovers(
    reader_copy, language, segment, word, wrong
):
    assert emit.verify(CORPUS, reader_copy) == []
    path = reader_copy / DATA["layers"][language]["path"]
    original = path.read_bytes()
    artifact = json.loads(original)
    row = next(item for item in artifact["seg"] if item["id"] == segment)
    if language == "en":
        assert row["a"] == [{"s": 7, "n": 2, "a": 1, "g": "spare the suppliant"}]
        row["a"][0]["g"] = wrong
        difference = f"en.segments.{segment}.alignments[0].gloss:"
    else:
        core, _layer = subject(language)
        ids = [token["id"] for token in source_segment(core, segment)["words"]]
        row["g"][ids.index(word)] = wrong
        difference = f"pl.words.{word}.gloss:"
    try:
        path.write_text(json.dumps(artifact, ensure_ascii=False), encoding="utf-8")
        assert path.read_bytes() != original
        errors = emit.verify(CORPUS, reader_copy)
        assert any(f"{DATA['text']}: {difference}" in error for error in errors)
    finally:
        path.write_bytes(original)
    assert path.read_bytes() == original
    assert emit.verify(CORPUS, reader_copy) == []
