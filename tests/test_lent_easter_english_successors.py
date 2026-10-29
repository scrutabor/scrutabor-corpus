"""Finite food captions retain the source, complete prose and actual native inputs."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import documentary_successor_fixture as documentary
import pytest
from communicantes_prose_successor_fixture import (
    before_communicantes_bytes,
    before_communicantes_ledger,
)
from lent_easter_successor_fixture import (
    DATA,
    RULE,
    before_lent_easter_bytes,
    before_lent_easter_ledger,
)
from prayer_prose_successor_fixture import AFTER, before_prayer_prose_ledger
from requiem_successor_fixture import DATA as REQUIEM
from requiem_successor_fixture import before_requiem_bytes, before_requiem_ledger

from build_reader import emit, store
from build_reader.bibliography_bindings import digest
from checks import interlinear, translation_provenance
from checks.language_packs import check_layer
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
TEXTS = DATA["texts"]
LEDGER_FAULTS = (
    "unexpected-field",
    "other-row",
    "missing-row",
    "duplicate-row",
    "source-digest",
    "review",
)
CONCLUSION = (
    "Through our Lord Jesus Christ, Your Son, who lives and reigns with You in the "
    "unity of the Holy Spirit, God,"
)


def read(relative, root=ROOT):
    return json.loads((root / relative).read_bytes())


def subject(case):
    return store.core(ROOT, case["text"]), store.raw_layer(ROOT, "en", case["text"])


def providers(source, layer):
    groups = interlinear.alignments_for(layer, source["id"])
    shared = {word: group for group in groups for word in group["words"]}
    result = []
    for word in source["words"]:
        identity = word["id"]
        if identity in shared:
            group = shared[identity]
            if identity == group["words"][0]:
                result.append({key: group[key] for key in ("words", "anchor", "gloss")})
        else:
            result.append({"words": [identity], "gloss": layer["words"][identity]["gloss"]})
    return result


def assert_food(case, core, layer):
    """An adopted finite reading; normal structure checks cannot judge English sense."""
    assert core["id"] == case["text"], "food text identity"
    assert interlinear.check(core, layer) == [], "food provider structure"
    assert [row["id"] for row in core["segments"]] == [row["id"] for row in case["segments"]], (
        "food segment order"
    )
    for source, expected in zip(core["segments"], case["segments"], strict=True):
        identity = source["id"]
        assert canonical_hash(source_payload(source)) == expected["source_sha256"], (
            "food source signature"
        )
        assert [[word["id"], word["form"]] for word in source["words"]] == expected["words"], (
            "food source word backmap"
        )
        assert {key: source[key] for key in expected["roles"]} == expected["roles"], (
            "food source roles"
        )
        assert layer["segments"][identity]["translation"] == expected["translation"], (
            "food full prose"
        )
        assert providers(source, layer) == expected["providers"], "food caption providers"


@pytest.mark.parametrize("case", TEXTS, ids=lambda case: case["id"])
def test_food_caption_provider_backmap(case):
    core, layer = subject(case)
    assert check_layer(core, layer, store.layer_path(ROOT, "en", case["text"])) == []
    assert_food(case, core, layer)
    assert (
        hashlib.sha256(store.layer_path(ROOT, "en", case["text"]).read_bytes()).hexdigest()
        == (case["layer_after_sha256"])
    )
    for source, expected in zip(core["segments"], case["segments"], strict=True):
        assert [word for provider in providers(source, layer) for word in provider["words"]] == (
            [word[0] for word in expected["words"]]
        )


@pytest.fixture(scope="module")
def complete_reader(emitted_book):
    """The real complete edition owns the global citation-coverage check."""
    assert emit.verify(ROOT, emitted_book[0]) == []
    return emitted_book[0]


@pytest.mark.parametrize("case", TEXTS, ids=lambda case: case["id"])
@pytest.mark.usefixtures("complete_reader")
def test_native_food_caption_roundtrip(reader_copy, case):
    relative = case["text"].replace(".", "/", 1)
    artifact = read(f"texts/{relative}.json", reader_copy)
    path = reader_copy / f"languages/en/texts/{relative}.json"
    saved = path.read_bytes()
    localized = json.loads(saved)
    tables = [
        read("tables/morphology.json", reader_copy),
        read("tables/analysis.json", reader_copy),
        read("tables/citations.json", reader_copy),
        read("languages/en/citations.json", reader_copy),
    ]
    core, layer = emit.expand(artifact, localized, *tables)
    assert_food(case, core, layer)
    same_path = path
    try:
        row = next(row for row in localized["seg"] if row["id"] == "s01")
        if case["id"] == "lent-secret":
            assert row["a"][2] == {"s": 10, "n": 3, "a": 1, "g": "the restriction of bodily food"}
            row["a"][2]["g"] = "bodily food"
            where = "en.segments.s01.alignments[2].gloss:"
        else:
            assert row["g"][6:8] == ["new", "dough"]
            row["g"][6] = "a new"
            where = "en.words.w007.gloss:"
        path.write_text(json.dumps(localized, ensure_ascii=False), encoding="utf-8")
        assert path.read_bytes() != saved
        assert any(f"{case['text']}: {where}" in error for error in emit.verify(ROOT, reader_copy))
    finally:
        path.write_bytes(saved)
    assert path is same_path and path.read_bytes() == saved
    assert emit.verify(ROOT, reader_copy) == []
    restored = read(f"languages/en/texts/{relative}.json", reader_copy)
    assert_food(case, *emit.expand(artifact, restored, *tables))


@pytest.mark.parametrize("fault", ["restored-a-new", "food-restriction-lost"])
def test_finite_food_oracle_rejects_and_recovers(fault):
    case = TEXTS[1] if fault == "restored-a-new" else TEXTS[0]
    core, actual = subject(case)
    saved, same_input = deepcopy(actual), actual
    assert_food(case, core, actual)
    try:
        if fault == "restored-a-new":
            actual["words"]["w007"]["gloss"] = "a new"
        else:
            actual["segments"]["s01"]["alignments"][2]["gloss"] = "bodily food"
        assert actual != saved
        assert interlinear.check(core, actual) == []
        with pytest.raises(AssertionError, match=r"^food caption providers(?:\n|$)"):
            assert_food(case, core, actual)
        assert actual is same_input and actual != saved
    finally:
        actual.clear()
        actual.update(deepcopy(saved))
    assert actual is same_input and actual == saved
    assert_food(case, core, actual)


def test_legitimate_food_alternatives_are_not_universal_grammar_errors():
    case = TEXTS[1]
    core, actual = subject(case)
    saved, same_input = deepcopy(actual), actual
    assert_food(case, core, actual)
    try:
        # A documented shared realization has its own topology. Shape validation
        # does not select it over the adopted split caption or judge English usage.
        del actual["words"]["w007"]["gloss"]
        del actual["words"]["w008"]["gloss"]
        shared = {"words": ["w007", "w008"], "anchor": "w008", "gloss": "a new batch of dough"}
        actual["segments"]["s01"]["alignments"].insert(0, shared)
        assert interlinear.check(core, actual) == []
        assert check_layer(core, actual, store.layer_path(ROOT, "en", case["text"])) == []
        assert shared in providers(core["segments"][0], actual)
        assert actual["segments"]["s01"]["translation"] == saved["segments"]["s01"]["translation"]
    finally:
        actual.clear()
        actual.update(deepcopy(saved))
    assert actual is same_input and actual == saved
    assert_food(case, core, actual)


def test_lenten_prose_keeps_both_observances_address_and_conclusion():
    case = TEXTS[0]
    core, layer = subject(case)
    assert_food(case, core, layer)
    translation = layer["segments"]["s01"]["translation"]
    assert translation == (
        "We solemnly offer the sacrifice that opens Lent, beseeching You, O Lord, that, "
        "while limiting our meals, we may also refrain from harmful pleasures. " + CONCLUSION
    )
    assert canonical_hash(translation) == RULE["after"]["target_sha256"]
    assert canonical_hash(source_payload(core["segments"][0])) == RULE["after"]["source_sha256"]
    for case in TEXTS:
        _, actual = subject(case)
        for identity, original in case["unchanged_prose"].items():
            assert actual["segments"][identity] == original


def test_food_ledger_full_inverse_recovers_prior_frames():
    relative = RULE["relative"]
    raw = (ROOT / relative).read_bytes()
    actual = json.loads(raw)
    saved = deepcopy(actual)
    before = before_lent_easter_ledger(relative, actual)
    before_raw = before_lent_easter_bytes(relative, raw)
    comparison = before_communicantes_ledger(relative, actual)
    comparison_raw = before_communicantes_bytes(relative, raw)
    assert digest(comparison) == RULE["after_canonical_sha256"]
    assert hashlib.sha256(comparison_raw).hexdigest() == RULE["after_raw_sha256"]
    assert digest(before) == RULE["before_canonical_sha256"]
    assert hashlib.sha256(before_raw).hexdigest() == RULE["before_raw_sha256"]
    assert json.loads(before_raw) == before
    with pytest.raises(AssertionError, match=r"^Lent/Easter current ledger(?:\n|$)"):
        before_lent_easter_ledger(relative, before)
    with pytest.raises(AssertionError, match=r"^exact Lent/Easter comparison bytes(?:\n|$)"):
        before_lent_easter_bytes(relative, before_raw)
    assert [
        i
        for i, rows in enumerate(zip(comparison["sites"], before["sites"], strict=True))
        if rows[0] != rows[1]
    ] == [RULE["index"]]
    assert digest(before_requiem_ledger(relative, actual)) == AFTER["en"]
    assert digest(before_prayer_prose_ledger(relative, actual)) == documentary.AGENCY_EN_CURRENT
    assert (
        digest(documentary.before_language_successors(relative, actual))
        == (documentary.DATA["ledgers"][relative]["before_sha256"])
    )
    assert (
        hashlib.sha256(before_requiem_bytes(relative, raw)).hexdigest()
        == (REQUIEM["raw"][relative]["before_sha256"])
    )
    assert before is not actual and actual == saved and (ROOT / relative).read_bytes() == raw
    other = "languages/pl/translation-provenance.json"
    other_raw = (ROOT / other).read_bytes()
    other_value = json.loads(other_raw)
    assert before_lent_easter_ledger(other, other_value) is other_value
    assert before_lent_easter_bytes(other, other_raw) is other_raw


@pytest.mark.parametrize("fault", LEDGER_FAULTS)
def test_food_ledger_inverse_rejects_and_recovers(fault):
    relative = RULE["relative"]
    raw = (ROOT / relative).read_bytes()
    actual = json.loads(raw)
    saved, same_input = deepcopy(actual), actual
    damaged = bytearray(raw)
    same_bytes = damaged
    expected = before_lent_easter_ledger(relative, actual)
    expected_raw = before_lent_easter_bytes(relative, raw)
    try:
        row = actual["sites"][RULE["index"]]
        if fault == "unexpected-field":
            actual["unexpected"] = True
        elif fault == "other-row":
            actual["sites"][0]["unexpected"] = True
        elif fault == "missing-row":
            actual["sites"].pop(RULE["index"])
        elif fault == "duplicate-row":
            actual["sites"].append(deepcopy(row))
        elif fault == "source-digest":
            row["source_sha256"] = "0" * 64
        else:
            assert fault == "review"
            row["review"] = "internally-reviewed"
        assert actual != saved
        damaged[:] = json.dumps(actual, ensure_ascii=False).encode()
        assert json.loads(damaged) == actual
        with pytest.raises(AssertionError, match=r"^Lent/Easter current ledger(?:\n|$)"):
            before_lent_easter_ledger(relative, actual)
        with pytest.raises(AssertionError, match=r"^exact Lent/Easter comparison bytes(?:\n|$)"):
            before_lent_easter_bytes(relative, bytes(damaged))
        assert actual is same_input and actual != saved
    finally:
        actual.clear()
        actual.update(deepcopy(saved))
        damaged[:] = raw
    assert actual is same_input and actual == saved
    assert damaged is same_bytes and bytes(damaged) == raw
    assert before_lent_easter_ledger(relative, actual) == expected
    assert before_lent_easter_bytes(relative, bytes(damaged)) == expected_raw


def test_native_provenance_guard_sees_actual_bad_target_and_recovers(monkeypatch):
    recorded, errors = translation_provenance.load(ROOT)
    assert errors == []
    saved = deepcopy(recorded)
    site = RULE["after"]["site"]
    row = recorded[site]
    original = deepcopy(row)
    assert row == RULE["after"]
    calls = []

    def actual_recorded_input(corpus):
        assert corpus == ROOT
        calls.append(recorded)
        return recorded, []

    # The normal checker still reads actual current source/target expectations.
    # Only its already-loaded ledger is injected; no historical inverse is used.
    monkeypatch.setattr(translation_provenance, "load", actual_recorded_input)
    assert translation_provenance.check(ROOT)[0] == []
    try:
        row["target_sha256"] = "0" * 64
        messages, _ = translation_provenance.check(ROOT)
        assert f"{site}: stale target_sha256" in messages
        assert calls[-1] is recorded and recorded[site] is row and row != original
    finally:
        row.clear()
        row.update(deepcopy(original))
    assert recorded[site] is row and row == original and recorded == saved
    assert translation_provenance.check(ROOT)[0] == []
    assert read(RULE["relative"])["sites"][RULE["index"]] == row
