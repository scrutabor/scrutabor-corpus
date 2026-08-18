"""The reader edition: it must lose nothing, and it must be deterministic."""

import gzip
import json
import shutil
from pathlib import Path

from build_reader.emit import Parses, emit, index, read_corpus, text_artifact, verify

CORPUS = Path(__file__).resolve().parent.parent


def build(tmp_path) -> Path:
    out = tmp_path / "build"
    emit(CORPUS, out)
    return out


def test_every_word_gloss_and_translation_round_trips(tmp_path):
    # The gate that makes the compression trustworthy. Without it the edition
    # is a second, quieter version of the same book.
    assert verify(CORPUS, build(tmp_path)) == []


def test_the_build_is_deterministic(tmp_path):
    first, second = tmp_path / "a", tmp_path / "b"
    emit(CORPUS, first)
    emit(CORPUS, second)
    for path in sorted(first.rglob("*.json")):
        twin = second / path.relative_to(first)
        assert path.read_bytes() == twin.read_bytes(), path.name


def test_nothing_editorial_survives(tmp_path):
    out = build(tmp_path)
    for path in out.glob("t/*.json"):
        art = json.loads(path.read_text(encoding="utf-8"))
        for gone in ("analysis_defaults", "analysis_defaults_words", "source", "status", "ids"):
            assert gone not in art, f"{path.name} still carries {gone}"
        for row in art["seg"]:
            assert "analysis" not in row
            for cell in row.get("w") or []:
                assert "analysis" not in cell


def test_the_parse_table_is_shared_and_small(tmp_path):
    out = build(tmp_path)
    table = json.loads((out / "m.json").read_text(encoding="utf-8"))
    words = sum(
        len(s.get("words") or []) for doc, _ in read_corpus(CORPUS) for s in doc["segments"]
    )
    assert len(table) < words / 10, "a table that big is not a table"


def test_the_edition_is_much_smaller_than_its_source(tmp_path):
    out = build(tmp_path)
    source = sum(
        p.stat().st_size
        for p in list(CORPUS.glob("texts/*/*.json")) + list(CORPUS.glob("glosses/*/*.json"))
    )
    made = sum(p.stat().st_size for p in out.rglob("*.json"))
    assert made < source * 0.6, f"{made} against {source} is not worth a build step"


def test_a_text_artifact_carries_both_languages(tmp_path):
    docs = read_corpus(CORPUS)
    doc, glosses = next((d, g) for d, g in docs if d["id"] == "ordinarium.credo")
    art = text_artifact(doc, glosses, Parses())
    assert set(art["about"]) == {"pl", "en"}
    spoken = [r for r in art["seg"] if r.get("w")]
    assert set(spoken[0]["g"]) == {"pl", "en"}
    assert set(spoken[0]["tr"]) == {"pl", "en"}


def test_the_index_finds_a_word_by_its_surface_form(tmp_path):
    idx = index(read_corpus(CORPUS))
    assert "credo" in idx["f"], "a form the Creed opens with must be findable"
    lemma = idx["f"]["credo"][0]
    assert idx["l"][lemma], "a lemma with no occurrences is not an index"


def test_a_posting_is_an_address_and_not_a_position(tmp_path):
    # A lemma page turns a posting into `/app/pl/<text>?w=<id>`. A position is
    # not an address: it moves the moment a word is inserted before it, which
    # is the one edit the mint exists to survive.
    docs = read_corpus(CORPUS)
    idx = index(docs)
    number, word_id = idx["l"]["dominus"][0]
    text_id = idx["t"][number]
    doc = next(d for d, _ in docs if d["id"] == text_id)
    found = [w for s in doc["segments"] for w in (s.get("words") or []) if w["id"] == word_id]
    assert found and found[0]["lemma"] == "dominus", f"{text_id}#{word_id} does not resolve"


def test_the_index_compresses_to_something_a_phone_can_hold(tmp_path):
    out = build(tmp_path)
    packed = len(gzip.compress((out / "x.json").read_bytes(), 9))
    assert packed < 120_000, "the index is what search and lemma pages both read"


def test_a_missing_gloss_layer_fails_loudly(tmp_path):
    # The edition may never quietly emit a text with one language missing.
    fake = tmp_path / "corpus"
    shutil.copytree(CORPUS / "texts", fake / "texts")
    shutil.copytree(CORPUS / "glosses", fake / "glosses")
    shutil.copytree(CORPUS / "lexicon", fake / "lexicon")
    (fake / "glosses/en/ordinarium.credo.json").unlink()
    try:
        read_corpus(fake)
    except FileNotFoundError:
        return
    raise AssertionError("a missing gloss layer must not pass silently")
