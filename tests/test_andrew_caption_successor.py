"""The Andrew fragrance caption keeps its own sense and neighboring uses of in."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import emit, store
from checks import interlinear, translation_provenance
from checks.language_packs import check_layer
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "tests/fixtures/andrew-caption-successor.json").read_bytes())
ANDREW = DATA["andrew"]


def read(relative, root=ROOT):
    return json.loads((root / relative).read_bytes())


def subject(text):
    return store.core(ROOT, text), store.raw_layer(ROOT, "en", text)


def providers(source, layer):
    shared = {
        word: group
        for group in interlinear.alignments_for(layer, source["id"])
        for word in group["words"]
    }
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


def assert_andrew(core, layer):
    """A finite reviewed metaphor; this is not a general rule for Latin in."""
    assert core["id"] == ANDREW["text"]
    assert [segment["id"] for segment in core["segments"]] == ["s01"]
    source = core["segments"][0]
    assert interlinear.check(core, layer) == [], "Andrew provider structure"
    assert canonical_hash(source_payload(source)) == ANDREW["source_sha256"], (
        "Andrew source signature"
    )
    assert [[word["id"], word["form"]] for word in source["words"]] == ANDREW["source_words"]
    assert {key: source[key] for key in ANDREW["roles"]} == ANDREW["roles"]
    assert layer["segments"]["s01"]["translation"] == ANDREW["translation"]
    assert interlinear.alignments_for(layer, "s01") == ANDREW["alignments"]
    assert providers(source, layer) == ANDREW["providers"], "Andrew caption providers"


def assert_context(case, core, layer):
    """Preserve these healthy phrases without admitting a universal replacement."""
    assert core["id"] == case["text"]
    assert interlinear.check(core, layer) == []
    source = next(segment for segment in core["segments"] if segment["id"] == case["segment"])
    assert canonical_hash(source_payload(source)) == case["source_sha256"]
    assert layer["segments"][case["segment"]]["translation"] == case["translation"]
    trace = providers(source, layer)
    for phrase in case["phrases"]:
        selected = [row for row in trace if set(row["words"]) & set(phrase["words"])]
        assert selected == phrase["providers"], "context caption providers"
        assert [word for row in selected for word in row["words"]] == phrase["words"]


def expanded(out, text):
    relative = text.replace(".", "/", 1)
    return emit.expand(
        read(f"texts/{relative}.json", out),
        read(f"languages/en/texts/{relative}.json", out),
        read("tables/morphology.json", out),
        read("tables/analysis.json", out),
        read("tables/citations.json", out),
        read("languages/en/citations.json", out),
    )


@pytest.fixture(scope="module")
def complete_reader(emitted_book):
    """Use the genuine complete edition and its full citation-coverage verifier."""
    assert emit.verify(ROOT, emitted_book[0]) == []
    return emitted_book[0]


def test_andrew_caption_keeps_exact_source_provider_and_provenance_backmap():
    core, layer = subject(ANDREW["text"])
    assert check_layer(core, layer, store.layer_path(ROOT, "en", ANDREW["text"])) == []
    assert_andrew(core, layer)
    assert len(ANDREW["source_words"]) == 9 and len(ANDREW["providers"]) == 7
    assert [word for row in providers(core["segments"][0], layer) for word in row["words"]] == [
        word[0] for word in ANDREW["source_words"]
    ]
    raw = store.layer_path(ROOT, "en", ANDREW["text"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ANDREW["layer_after_raw_sha256"]
    recorded, errors = translation_provenance.load(ROOT)
    assert errors == []
    row = recorded[ANDREW["provenance_row"]["site"]]
    assert row == ANDREW["provenance_row"]
    assert row["source_sha256"] == canonical_hash(source_payload(core["segments"][0]))
    assert row["target_sha256"] == canonical_hash(layer["segments"]["s01"]["translation"])


@pytest.mark.usefixtures("complete_reader")
def test_native_andrew_caption_roundtrip_rejects_old_artifact_and_recovers(reader_copy):
    assert_andrew(*expanded(reader_copy, ANDREW["text"]))
    relative = ANDREW["text"].replace(".", "/", 1)
    path = reader_copy / f"languages/en/texts/{relative}.json"
    original = path.read_bytes()
    artifact = json.loads(original)
    row = next(segment for segment in artifact["seg"] if segment["id"] == "s01")
    assert row["g"][5:8] == ["as", "a fragrance", "of sweetness"]
    try:
        row["g"][5] = "in"
        path.write_text(json.dumps(artifact, ensure_ascii=False), encoding="utf-8")
        assert path.read_bytes() != original
        assert any(
            f"{ANDREW['text']}: en.words.w006.gloss:" in error
            for error in emit.verify(ROOT, reader_copy)
        )
    finally:
        path.write_bytes(original)
    assert path.read_bytes() == original
    assert emit.verify(ROOT, reader_copy) == []
    assert_andrew(*expanded(reader_copy, ANDREW["text"]))


def test_finite_andrew_oracle_rejects_literal_in_and_recovers_same_input():
    core, actual = subject(ANDREW["text"])
    saved, same_input = deepcopy(actual), actual
    entry = actual["words"]["w006"]
    original, same_entry = deepcopy(entry), entry
    assert_andrew(core, actual)
    try:
        entry["gloss"] = "in"
        # Literal in is structurally valid; the finite meaning oracle owns this failure.
        assert interlinear.check(core, actual) == []
        assert actual is same_input and actual != saved
        with pytest.raises(AssertionError, match=r"^Andrew caption providers(?:\n|$)"):
            assert_andrew(core, actual)
    finally:
        entry.clear()
        entry.update(deepcopy(original))
    assert entry is same_entry and actual["words"]["w006"] is entry
    assert actual is same_input and actual == saved
    assert_andrew(core, actual)


def test_real_for_as_and_locative_in_contexts_keep_their_own_native_realizations(complete_reader):
    for case in DATA["controls"]:
        core, actual = subject(case["text"])
        saved, same_input = deepcopy(actual), actual
        assert check_layer(core, actual, store.layer_path(ROOT, "en", case["text"])) == []
        assert_context(case, core, actual)
        assert_context(case, *expanded(complete_reader, case["text"]))
        if case["id"] == "moses":
            entry = actual["words"]["w020"]
            wrong = "as"
        else:
            assert case["id"] == "robert"
            entry = next(
                group
                for group in interlinear.alignments_for(actual, "s01")
                if group["words"] == ["w036", "w037"]
            )
            wrong = "as the unity"
        original, same_entry = deepcopy(entry), entry
        try:
            entry["gloss"] = wrong
            assert interlinear.check(core, actual) == []
            with pytest.raises(AssertionError, match=r"^context caption providers(?:\n|$)"):
                assert_context(case, core, actual)
            assert actual is same_input and actual != saved
        finally:
            entry.clear()
            entry.update(deepcopy(original))
        assert entry is same_entry and entry == original
        assert actual is same_input and actual == saved
        assert_context(case, core, actual)
