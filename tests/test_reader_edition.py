"""The reader edition: it must lose nothing, and it must be deterministic."""

import gzip
import json
from pathlib import Path

from build_reader.emit import Table, emit, expand, index, read_corpus, text_artifact, verify

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


def test_nothing_a_reader_never_sees_survives(tmp_path):
    # The apparatus, the mint and the editorial notes are written for someone
    # reading a diff. They are the whole reason the authored corpus and the
    # shipped one are different documents.
    out = build(tmp_path)
    for path in out.glob("t/*.json"):
        art = json.loads(path.read_text(encoding="utf-8"))
        for gone in ("source", "ids", "notes", "schema_version"):
            assert gone not in art, f"{path.name} still carries {gone}"


def test_what_a_reader_is_shown_does_survive(tmp_path):
    # The other half, and the one the first draft got wrong: it dropped the
    # analysis and every citation, which are exactly what the word panel and
    # the source notes render. An edition that ships the doubt and withholds
    # the note of it is not the edition this corpus claims to be.
    out = build(tmp_path)
    art = json.loads((out / "t/orationes.pater-noster.json").read_text(encoding="utf-8"))
    assert isinstance(art["ad"], int), "the analysis default is an index into the table"
    assert art["st"], "the working-edition label travels with the text"

    citations = json.loads((out / "c.json").read_text(encoding="utf-8"))
    seen = 0
    for path in out.glob("t/*.json"):
        text = json.loads(path.read_text(encoding="utf-8"))
        for key in ("ac",):
            for indices in (text.get(key) or {}).values():
                seen += len(indices)
                assert all(citations[i]["title"] for i in indices)
        for row in text["seg"]:
            for key in ("tc", "nc"):
                for indices in (row.get(key) or {}).values():
                    seen += len(indices)
                    assert all(citations[i]["title"] for i in indices)
            for byword in (row.get("fc") or {}).values():
                for indices in byword.values():
                    seen += len(indices)
                    assert all(citations[i]["title"] for i in indices)
    assert seen > 1000, f"the source notes did not survive the build ({seen} references)"


def test_the_tables_are_tables_and_not_lists_of_everything(tmp_path):
    out = build(tmp_path)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    words = sum(
        len(s.get("words") or []) for doc, _ in read_corpus(CORPUS) for s in doc["segments"]
    )
    assert manifest["analyses"] < 50, "an analysis has a handful of shapes, not one per word"
    assert manifest["citations"] < words / 10, "the same works are cited over and over"


def test_the_edition_expands_back_into_what_the_corpus_stores(tmp_path):
    # `verify` runs this over all 111 texts; this states the property in one
    # place so that what the round trip means is readable without reading it.
    out = build(tmp_path)
    tables = [
        json.loads((out / f"{name}.json").read_text(encoding="utf-8")) for name in ("m", "a", "c")
    ]
    doc, glosses = next((d, g) for d, g in read_corpus(CORPUS) if d["id"] == "ordinarium.credo")
    art = json.loads((out / "t/ordinarium.credo.json").read_text(encoding="utf-8"))
    got_doc, got_glosses = expand(art, *tables)
    assert got_doc["segments"] == doc["segments"]
    assert got_glosses["pl"]["words"] == glosses["pl"]["words"]


def test_the_parse_table_is_shared_and_small(tmp_path):
    out = build(tmp_path)
    table = json.loads((out / "m.json").read_text(encoding="utf-8"))
    words = sum(
        len(s.get("words") or []) for doc, _ in read_corpus(CORPUS) for s in doc["segments"]
    )
    assert len(table) < words / 10, "a table that big is not a table"


def test_the_edition_is_much_smaller_than_its_source(tmp_path):
    # The texts and the tables they are addressed through, against the texts
    # they came from. kal.json is left out on purpose: the calendar is derived
    # from the rubrics and not from the corpus, so it has no counterpart on the
    # other side of this comparison and would only make the ratio meaningless.
    out = build(tmp_path)
    source = sum(p.stat().st_size for p in CORPUS.glob("texts/*/*.json"))
    made = sum(p.stat().st_size for p in out.rglob("*.json") if p.name != "kal.json")
    assert made < source * 0.65, f"{made} against {source} is not worth a build step"


def test_the_saving_is_in_the_bytes_parsed_and_not_the_bytes_sent(tmp_path):
    # STATED, because it is a surprise and would otherwise be assumed the
    # other way. The authored corpus repeats one parse object at every one of
    # 6,143 words, and gzip is very good at exactly that -- so compressed, the
    # edition is no smaller than the corpus it came from, and by a little it
    # is larger, the indices being less repetitive than what they replaced.
    #
    # The saving that is real is the one a phone feels: 39% fewer bytes to
    # parse, and 412 parse objects on the heap where the corpus has 6,143,
    # because `expand` hands out the SAME object rather than a copy of it.
    # The download is made small by not shipping 1,961 prerendered pages,
    # which is a different lever and lives in the app.
    def packed(paths) -> int:
        return len(gzip.compress(b"".join(p.read_bytes() for p in sorted(paths)), 9))

    out = build(tmp_path)
    assert packed(out.rglob("*.json")) > packed(CORPUS.glob("texts/*/*.json")) * 0.9


def test_a_text_artifact_carries_both_languages(tmp_path):
    docs = read_corpus(CORPUS)
    doc, glosses = next((d, g) for d, g in docs if d["id"] == "ordinarium.credo")
    art = text_artifact(doc, glosses, Table(), Table(), Table())
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


def test_a_word_that_loses_a_language_is_caught(tmp_path):
    # The languages share a document now, so a missing gloss is a missing key
    # rather than a missing file. It must still be loud, and the check that
    # has always said so must still say it.
    import json

    from build_reader.merge import split
    from checks.lint import lint_gloss

    doc = json.loads((CORPUS / "texts/ordinarium/credo.json").read_text(encoding="utf-8"))
    for segment in doc["segments"]:
        for word in segment.get("words") or []:
            (word.get("gloss") or {}).pop("en", None)
    text, layers = split(doc)
    errors = lint_gloss(layers["en"], text)
    assert errors and "no gloss" in errors[0], errors[:1]


def test_the_edition_carries_the_calendar_a_reader_can_look_today_up_in(tmp_path):
    # Decision #6: apps never implement movable-feast logic. Three readers are
    # coming, and a rule implemented three times becomes three rules.
    out = build(tmp_path)
    kal = json.loads((out / "kal.json").read_text(encoding="utf-8"))
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    first, last = manifest["kalendarium"]
    assert first == 2026 and last == 2101, (
        "the span decision #6 fixed, plus the year that ends 2100"
    )
    assert set(kal["y"]) == {str(y) for y in range(first, last + 1)}

    rows = kal["y"]["2026"]
    assert rows == sorted(rows), "a reader looks a date up by walking forward"
    assert kal["f"][rows[0][1]] == "dominica-i-adventus", "the year opens where the year opens"
    for row in rows:
        _when, formulary, season, dies_class, position = row
        assert kal["f"][formulary] and kal["s"][season]
        assert dies_class in (1, 2)
        assert kal["f"][position]

    # The whole point of shipping it: a date resolves without arithmetic.
    by_date = {row[0]: row for row in kal["y"]["2026"]}
    assert kal["f"][by_date["2026-04-05"][1]] == "dominica-resurrectionis"
    assert kal["f"][by_date["2025-11-30"][1]] == "dominica-i-adventus"


def test_the_calendar_costs_almost_nothing_to_ship(tmp_path):
    out = build(tmp_path)
    packed = len(gzip.compress((out / "kal.json").read_bytes(), 9))
    assert packed < 40_000, "seventy-six years of Sundays is not a large object"
