"""The reader edition: it must lose nothing, and it must be deterministic."""

import gzip
import json
from pathlib import Path

from build_reader.emit import (
    REGISTRY,
    Table,
    core_artifact,
    emit,
    expand,
    index,
    language_artifact,
    language_index,
    language_lexicon_differences,
    normalize_latin,
    normalize_search,
    read_corpus,
    tokenize_search,
    update_registry,
    verify,
)

CORPUS = Path(__file__).resolve().parent.parent


def build(tmp_path) -> Path:
    out = tmp_path / "build"
    emit(CORPUS, out)
    return out


def test_every_word_gloss_and_translation_round_trips(tmp_path):
    # The gate that makes the compression trustworthy. Without it the edition
    # is a second, quieter version of the same book.
    assert verify(CORPUS, build(tmp_path)) == []


def test_a_partial_language_pack_needs_only_its_covered_lemmas():
    docs = [
        (
            {
                "id": "orationes.alpha",
                "segments": [{"words": [{"lemma": "pater"}]}],
            },
            {},
        ),
        (
            {
                "id": "orationes.beta",
                "segments": [{"words": [{"lemma": "mater"}]}],
            },
            {},
        ),
    ]
    heads = {"mater": {}, "pater": {}}
    assert language_lexicon_differences(docs, {"orationes.alpha"}, {"pater": {}}, heads) == (
        set(),
        set(),
    )
    missing, unknown = language_lexicon_differences(
        docs, {"orationes.alpha"}, {"mater": {}, "ghost": {}}, heads
    )
    assert missing == {"pater"}
    assert unknown == {"ghost"}


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
    for path in out.glob("texts/*/*.json"):
        art = json.loads(path.read_text(encoding="utf-8"))
        for gone in ("source", "ids", "notes", "schema_version"):
            assert gone not in art, f"{path.name} still carries {gone}"


def test_what_a_reader_is_shown_does_survive(tmp_path):
    # The other half, and the one the first draft got wrong: it dropped the
    # analysis and every citation, which are exactly what the word panel and
    # the source notes render. An edition that ships the doubt and withholds
    # the note of it is not the edition this corpus claims to be.
    out = build(tmp_path)
    art = json.loads((out / "texts/orationes/pater-noster.json").read_text(encoding="utf-8"))
    assert isinstance(art["ad"], int), "the analysis default is an index into the table"
    assert art["st"], "the working-edition label travels with the text"

    citations = json.loads((out / "tables/citations.json").read_text(encoding="utf-8"))
    seen = 0
    for path in out.glob("texts/*/*.json"):
        text = json.loads(path.read_text(encoding="utf-8"))
        if indices := text.get("ac"):
            seen += len(indices)
            assert all(citations[i]["title"] for i in indices)
        for row in text["seg"]:
            if indices := row.get("nc"):
                seen += len(indices)
                assert all(citations[i]["title"] for i in indices)
            for indices in (row.get("ec") or {}).values():
                seen += len(indices)
                assert all(citations[i]["title"] for i in indices)
    for language in ("pl", "en"):
        language_citations = json.loads(
            (out / f"languages/{language}/citations.json").read_text(encoding="utf-8")
        )
        for path in out.glob(f"languages/{language}/texts/*/*.json"):
            text = json.loads(path.read_text(encoding="utf-8"))
            for row in text["seg"]:
                if indices := row.get("tc"):
                    seen += len(indices)
                    assert all(language_citations[i]["title"] for i in indices)
    assert seen > 1000, f"the source notes did not survive the build ({seen} references)"


def test_rejected_citation_attachments_do_not_reach_the_reader(tmp_path):
    out = build(tmp_path)
    shared = json.loads((out / "tables/citations.json").read_text(encoding="utf-8"))
    pl = json.loads((out / "languages/pl/citations.json").read_text(encoding="utf-8"))

    ave = json.loads((out / "texts/orationes/ave-maria.json").read_text(encoding="utf-8"))
    assert "w001" not in (ave["seg"][0].get("ec") or {})

    aufer = json.loads((out / "texts/ordinarium/aufer-a-nobis.json").read_text(encoding="utf-8"))
    assert "nc" not in next(row for row in aufer["seg"] if row["id"] == "s01")

    te_igitur = json.loads(
        (out / "languages/pl/texts/ordinarium/te-igitur.json").read_text(encoding="utf-8")
    )
    assert "tc" not in next(row for row in te_igitur["seg"] if row["id"] == "s02")

    heads = json.loads((out / "lexicon/heads.json").read_text(encoding="utf-8"))["entries"]
    assert "note_citations" not in heads["Abel"]["localization"]

    gloria = json.loads(
        (out / "languages/pl/texts/ordinarium/gloria.json").read_text(encoding="utf-8")
    )
    retained = next(row for row in gloria["seg"] if row["id"] == "s12")["tc"]
    assert any(
        pl[index]["title"] == "Pamiątka Missyi dla ludu katolickiego (1903)" for index in retained
    )
    assert all(value is None or "legacy_ref" not in value for value in [*shared, *pl])


def test_reader_build_names_evidence_coverage_and_rejected_exposure(tmp_path):
    written = emit(CORPUS, tmp_path / "build")
    assert written["citation_projection"] == {
        "legacy": 2776,
        "mapped": 2044,
        "kept": 2044,
        "excluded": 732,
        "unresolved": 0,
        "rejected_exposed": 0,
    }
    assert written["evidence_coverage"] == {
        "neutral": {"normalized": 56, "texts": 156},
        "languages": {
            "en": {"normalized": 108, "effective": 142, "texts": 156},
            "pl": {"normalized": 72, "effective": 107, "texts": 156},
        },
    }


def test_translation_relationship_travels_only_with_its_language_text(tmp_path):
    out = build(tmp_path)
    pl = json.loads(
        (out / "languages/pl/texts/orationes/benedic-domine.json").read_text(encoding="utf-8")
    )
    base = json.loads((out / "texts/orationes/benedic-domine.json").read_text(encoding="utf-8"))
    assert {row.get("tb") for row in pl["seg"]} == {"traditional-composite"}
    assert all("tb" not in row for row in base["seg"])


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
    parses = json.loads((out / "tables/morphology.json").read_text(encoding="utf-8"))
    analyses = json.loads((out / "tables/analysis.json").read_text(encoding="utf-8"))
    citations = json.loads((out / "tables/citations.json").read_text(encoding="utf-8"))
    pl_citations = json.loads((out / "languages/pl/citations.json").read_text(encoding="utf-8"))
    doc, glosses = next((d, g) for d, g in read_corpus(CORPUS) if d["id"] == "ordinarium.credo")
    art = json.loads((out / "texts/ordinarium/credo.json").read_text(encoding="utf-8"))
    localized = json.loads(
        (out / "languages/pl/texts/ordinarium/credo.json").read_text(encoding="utf-8")
    )
    got_doc, got_gloss = expand(art, localized, parses, analyses, citations, pl_citations)
    assert got_doc["segments"] == doc["segments"]
    assert got_gloss["words"] == glosses["pl"]["words"]


def test_the_parse_table_is_shared_and_small(tmp_path):
    out = build(tmp_path)
    table = json.loads((out / "tables/morphology.json").read_text(encoding="utf-8"))
    words = sum(
        len(s.get("words") or []) for doc, _ in read_corpus(CORPUS) for s in doc["segments"]
    )
    assert len(table) < words / 10, "a table that big is not a table"


def test_the_edition_is_much_smaller_than_its_source(tmp_path):
    # The texts, source graph and the tables they are addressed through, against
    # the authored data they came from. calendar.json is left out on purpose: the
    # calendar is derived from the rubrics and has no authored counterpart.
    out = build(tmp_path)
    source = (
        sum(p.stat().st_size for p in CORPUS.glob("texts/*/*.json"))
        + sum(p.stat().st_size for p in CORPUS.glob("languages/*/texts/*/*.json"))
        + (CORPUS / "bibliography" / "graph.json").stat().st_size
        + sum(p.stat().st_size for p in CORPUS.glob("languages/*/bibliography.json"))
    )
    artifacts = [p for p in out.rglob("*.json") if p.name != "calendar.json"]
    localized_search = [
        p
        for p in artifacts
        if p.name == "concordance.json" and "languages" in p.relative_to(out).parts
    ]
    reader = sum(p.stat().st_size for p in artifacts if p not in localized_search)
    made = sum(p.stat().st_size for p in artifacts)
    assert reader < source * 0.72, f"{reader} against {source} is not worth a build step"
    assert made < source * 0.76, f"localized search made the edition too large: {made}"


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
    authored = list(CORPUS.glob("texts/*/*.json")) + list(CORPUS.glob("languages/*/texts/*/*.json"))
    assert packed(out.rglob("*.json")) > packed(authored) * 0.9


def test_base_and_language_artifacts_are_independently_loadable(tmp_path):
    from build_reader import store

    docs = read_corpus(CORPUS)
    doc, glosses = next((d, g) for d, g in docs if d["id"] == "ordinarium.credo")
    base = core_artifact(doc, store.core(CORPUS, doc["id"]), Table(), Table(), Table())
    pl = language_artifact(doc, glosses["pl"], Table())
    en = language_artifact(doc, glosses["en"], Table())
    assert "about" not in base
    assert pl["language"] == "pl" and en["language"] == "en"
    pl_translation = next(row["tr"] for row in pl["seg"] if "tr" in row)
    en_translation = next(row["tr"] for row in en["seg"] if "tr" in row)
    assert pl_translation != en_translation
    assert "g" not in base["seg"][0]


def test_the_index_finds_a_word_by_its_surface_form(tmp_path):
    idx = index(read_corpus(CORPUS))
    assert "credo" in idx["latin"]["forms"], "a form the Creed opens with must be findable"
    assert idx["latin"]["forms"]["credo"], "a form points directly at occurrences"
    assert idx["latin"]["lemmata"]["credo"], "a lemma has its own occurrence list"


def test_search_forms_ignore_case_accents_and_typed_out_ligatures():
    assert normalize_latin("DÓMINUS") == "dominus"
    assert normalize_latin("cælos") == "caelos"


def test_search_keys_expand_the_accented_ligature():
    # ǽ (U+01FD) is precomposed: expanding ligatures before decomposition
    # misses it and a bare æ survives into the key, so the doxology's own
    # sǽcula and every collect's quǽsumus cannot be found as typed.
    assert normalize_latin("sǽcula") == "saecula"
    assert normalize_latin("quǽsumus") == "quaesumus"
    assert normalize_latin("Galilǽæ") == "galilaeae"
    assert normalize_latin("Ǽthiops") == "aethiops"
    assert normalize_latin("fœ́deris") == "foederis"
    assert tokenize_search("in sǽcula sæculórum") == ["in", "saecula", "saeculorum"]


def test_the_emitted_vectors_are_the_normalizers_truth(tmp_path):
    # The vectors are hand-authored expected outputs, shipped in the edition
    # so the app can assert its own normalizers against the identical pairs.
    from build_reader.emit import NORMALIZATION_VECTORS

    for probe, expected in NORMALIZATION_VECTORS["latin"]:
        assert normalize_latin(probe) == expected, probe
    for probe, expected in NORMALIZATION_VECTORS["search"]:
        assert normalize_search(probe) == expected, probe
    out = build(tmp_path)
    emitted = json.loads((out / "normalization.json").read_text(encoding="utf-8"))
    assert emitted == NORMALIZATION_VECTORS
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["base"]["normalization"] == "normalization.json"


def test_normalization_is_idempotent():
    # A key fed back through the normalizer must not change again; the ǽ
    # defect was exactly a non-idempotent pipeline.
    for probe in ("sǽcula", "Galilǽæ", "cælos", "fœ́deris", "DÓMINUS", "Najświętszą"):
        latin = normalize_latin(probe)
        assert normalize_latin(latin) == latin
        search = normalize_search(probe)
        assert normalize_search(search) == search


def test_target_search_ignores_case_diacritics_and_polish_l_stroke():
    pious = "Duszo Chrystusowa"
    assert normalize_search(pious) == normalize_search(pious.upper())
    assert tokenize_search("Najświętsza Panno") == ["najswietsza", "panno"]
    assert tokenize_search("Królowo niebios") == ["krolowo", "niebios"]


def test_a_posting_is_an_address_and_not_a_position(tmp_path):
    # A lemma page turns a posting into `/app/pl/<text>?w=<id>`. A position is
    # not an address: it moves the moment a word is inserted before it, which
    # is the one edit the mint exists to survive.
    docs = read_corpus(CORPUS)
    registry = json.loads((REGISTRY / "texts.json").read_text(encoding="utf-8"))
    idx = index(docs, registry)
    number, segment_id, word_id, position = idx["latin"]["lemmata"]["dominus"][0]
    text_id = idx["texts"][number]
    doc = next(d for d, _ in docs if d["id"] == text_id)
    found = [w for s in doc["segments"] for w in (s.get("words") or []) if w["id"] == word_id]
    assert found and found[0]["lemma"] == "dominus", f"{text_id}#{word_id} does not resolve"
    segment = next(segment for segment in doc["segments"] if segment["id"] == segment_id)
    assert segment["words"][position]["id"] == word_id


def test_language_index_finds_a_piously_capitalized_prayer_title_phrase():
    docs = read_corpus(CORPUS)
    registry = json.loads((REGISTRY / "texts.json").read_text(encoding="utf-8"))
    idx = language_index(docs, "pl", registry)
    number = idx["texts"].index("orationes.anima-christi")
    duszo = idx["terms"]["duszo"]
    chrystusowa = idx["terms"]["chrystusowa"]
    assert [number, "s01", 0] in duszo
    assert [number, "s01", 1] in chrystusowa


def test_the_index_compresses_to_something_a_phone_can_hold(tmp_path):
    out = build(tmp_path)
    packed = len(gzip.compress((out / "concordance.json").read_bytes(), 9))
    assert packed < 150_000, "the index is what search and lemma pages both read"


def test_language_indexes_are_small_and_independently_packaged(tmp_path):
    out = build(tmp_path)
    for language in ("pl", "en"):
        path = out / f"languages/{language}/concordance.json"
        packed = len(gzip.compress(path.read_bytes(), 9))
        assert packed < 100_000, f"{language} search index is too large ({packed})"
        manifest = json.loads(
            (out / f"languages/{language}/manifest.json").read_text(encoding="utf-8")
        )
        assert manifest["concordance"] == f"languages/{language}/concordance.json"


def test_registry_is_current(tmp_path, monkeypatch):
    # Currency only: zero pending appends. The append-only property itself is
    # held by checks.identity.check_registry_history as an exact-prefix
    # comparison against git, mutation-tested in tests/test_identity.py.
    # Updating a copy may rewrite whitespace, but a current corpus appends no
    # identities and therefore cannot silently renumber a shipped address.
    copied = tmp_path / "registry"
    copied.mkdir()
    for path in REGISTRY.glob("*.json"):
        (copied / path.name).write_bytes(path.read_bytes())
    monkeypatch.setattr("build_reader.emit.REGISTRY", copied)
    assert update_registry(CORPUS) == {
        "morphology": 0,
        "analysis": 0,
        "citations": 0,
        "texts": 0,
    }


def test_generated_json_has_descriptive_paths_and_logical_lines(tmp_path):
    out = build(tmp_path)
    expected = {
        "manifest.json",
        "concordance.json",
        "lexicon/heads.json",
        "languages/pl/manifest.json",
        "languages/pl/lexicon.json",
        "languages/pl/concordance.json",
        "languages/pl/citations.json",
        "languages/pl/texts/ordinarium/credo.json",
        "calendar.json",
        "tables/morphology.json",
        "tables/analysis.json",
        "tables/citations.json",
        "texts/ordinarium/credo.json",
    }
    paths = {str(path.relative_to(out)) for path in out.rglob("*.json")}
    assert expected <= paths
    assert not ({"m.json", "a.json", "c.json", "x.json", "lex.json", "kal.json"} & paths)
    for relative in expected:
        body = (out / relative).read_text(encoding="utf-8")
        assert body.endswith("\n") and body.count("\n") > 2, relative


def test_a_word_that_loses_a_language_is_caught(tmp_path):
    from build_reader import store
    from checks.language_packs import check_layer

    core = store.core(CORPUS, "ordinarium.credo")
    layer = store.raw_layer(CORPUS, "en", "ordinarium.credo")
    layer["words"].pop(next(iter(layer["words"])))
    errors = check_layer(core, layer, store.layer_path(CORPUS, "en", "ordinarium.credo"))
    assert errors and "word coverage" in errors[0], errors[:1]


def test_the_edition_carries_the_calendar_a_reader_can_look_today_up_in(tmp_path):
    # Decision #6: apps never implement movable-feast logic. Three readers are
    # coming, and a rule implemented three times becomes three rules.
    out = build(tmp_path)
    kal = json.loads((out / "calendar.json").read_text(encoding="utf-8"))
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    first, last = manifest["kalendarium"]
    assert first == 2026 and last == 2101, (
        "the span decision #6 fixed, plus the year that ends 2100"
    )
    assert set(kal["years"]) == {str(y) for y in range(first, last + 1)}

    rows = kal["years"]["2026"]
    assert rows == sorted(rows), "a reader looks a date up by walking forward"
    assert kal["formularies"][rows[0][1]] == "dominica-i-adventus", (
        "the year opens where the year opens"
    )
    for row in rows:
        _when, formulary, season, dies_class, position = row
        assert kal["formularies"][formulary] and kal["seasons"][season]
        assert dies_class in (1, 2)
        assert kal["formularies"][position]

    # The whole point of shipping it: a date resolves without arithmetic.
    by_date = {row[0]: row for row in kal["years"]["2026"]}
    assert kal["formularies"][by_date["2026-04-05"][1]] == "dominica-resurrectionis"
    assert kal["formularies"][by_date["2025-11-30"][1]] == "dominica-i-adventus"


def test_the_calendar_costs_almost_nothing_to_ship(tmp_path):
    out = build(tmp_path)
    packed = len(gzip.compress((out / "calendar.json").read_bytes(), 9))
    assert packed < 40_000, "seventy-six years of Sundays is not a large object"


def test_retired_segments_reach_the_edition_and_verify_guards_them(tmp_path):
    # A retired segment id must travel with the text, so the app can resolve
    # an old `?s=` link to the surviving verse — and the round-trip cannot
    # see it (its source, `ids`, is a declared drop), so `verify` holds the
    # emitted map against the mint explicitly. Both directions are proved:
    # the map is emitted, and a divergent map fails the gate.
    docs = read_corpus(CORPUS)
    sample = docs[0][0]
    from build_reader import store

    retired_doc = json.loads(json.dumps(sample))
    live = retired_doc["segments"][0]["id"]
    retired_doc["ids"]["segments"]["retired"] = {"s90": live}
    artifact = core_artifact(
        retired_doc, store.core(CORPUS, sample["id"]), Table(), Table(), Table()
    )
    assert artifact["rs"] == {"s90": live}
    plain = core_artifact(sample, store.core(CORPUS, sample["id"]), Table(), Table(), Table())
    assert "rs" not in plain

    out = build(tmp_path)
    assert verify(CORPUS, out) == []
    victim = out / "texts" / Path(*sample["id"].split(".")).with_suffix(".json")
    mutated = json.loads(victim.read_text(encoding="utf-8"))
    mutated["rs"] = {"s90": live}
    victim.write_text(json.dumps(mutated, ensure_ascii=False), encoding="utf-8")
    errors = verify(CORPUS, out)
    assert any("retired segments differ" in e for e in errors), errors


def test_retired_words_reach_the_edition_and_verify_guards_them(tmp_path):
    docs = read_corpus(CORPUS)
    sample = docs[0][0]
    from build_reader import store

    retired_doc = json.loads(json.dumps(sample))
    live = retired_doc["segments"][0]["id"]
    retired_doc["ids"]["retired"] = {"w900": live}
    artifact = core_artifact(
        retired_doc, store.core(CORPUS, sample["id"]), Table(), Table(), Table()
    )
    assert artifact["rw"] == {"w900": live}
    plain = core_artifact(sample, store.core(CORPUS, sample["id"]), Table(), Table(), Table())
    assert "rw" not in plain

    out = build(tmp_path)
    assert verify(CORPUS, out) == []
    victim = out / "texts" / Path(*sample["id"].split(".")).with_suffix(".json")
    mutated = json.loads(victim.read_text(encoding="utf-8"))
    mutated["rw"] = {"w900": live}
    victim.write_text(json.dumps(mutated, ensure_ascii=False), encoding="utf-8")
    errors = verify(CORPUS, out)
    assert any("retired words differ" in e for e in errors), errors


def test_verify_catches_what_the_round_trip_cannot(tmp_path):
    # Fault injection, one artifact class at a time. Every probe below passed
    # a round-trip-only verify when the review ran them; each must now fail.
    import shutil

    clean = build(tmp_path)
    assert verify(CORPUS, clean) == []

    def broken(mutate, name):
        out = tmp_path / name
        shutil.copytree(clean, out)
        mutate(out)
        return verify(CORPUS, out)

    def emptied_concordance(out):
        p = out / "concordance.json"
        c = json.loads(p.read_text(encoding="utf-8"))
        c["latin"] = {"lemmata": {}, "forms": {}}
        p.write_text(json.dumps(c), encoding="utf-8")

    assert any("index is empty" in e for e in broken(emptied_concordance, "b1"))

    def rotated_texts(out):
        p = out / "concordance.json"
        c = json.loads(p.read_text(encoding="utf-8"))
        c["texts"] = c["texts"][1:] + c["texts"][:1]
        p.write_text(json.dumps(c), encoding="utf-8")

    assert any("not the registry" in e for e in broken(rotated_texts, "b2"))

    def emptied_language_terms(out):
        p = out / "languages/pl/concordance.json"
        c = json.loads(p.read_text(encoding="utf-8"))
        c["terms"] = {}
        p.write_text(json.dumps(c), encoding="utf-8")

    assert any("translation index is empty" in e for e in broken(emptied_language_terms, "b3"))

    def repointed_posting(out):
        p = out / "concordance.json"
        c = json.loads(p.read_text(encoding="utf-8"))
        key = next(iter(c["latin"]["forms"]))
        c["latin"]["forms"][key][0][2] = "w999"
        p.write_text(json.dumps(c), encoding="utf-8")

    assert any("missing word" in e for e in broken(repointed_posting, "b4"))

    def emptied_lexicon(out):
        (out / "lexicon/heads.json").write_text('{"entries":{}}', encoding="utf-8")

    assert any("lexicon: heads" in e for e in broken(emptied_lexicon, "b5"))

    def emptied_year(out):
        p = out / "calendar.json"
        c = json.loads(p.read_text(encoding="utf-8"))
        year = next(iter(c["years"]))
        c["years"][year] = []
        p.write_text(json.dumps(c), encoding="utf-8")

    assert any("missing or empty" in e for e in broken(emptied_year, "b6"))

    def dropped_declared_file(out):
        (out / "calendar.json").unlink()

    assert any("declared and not written" in e for e in broken(dropped_declared_file, "b7"))

    def stray_file(out):
        (out / "extra.json").write_text("{}", encoding="utf-8")

    assert any("no manifest declares" in e for e in broken(stray_file, "b8"))

    def altered_vectors(out):
        p = out / "normalization.json"
        v = json.loads(p.read_text(encoding="utf-8"))
        v["latin"][0][1] = "sæcula"
        p.write_text(json.dumps(v), encoding="utf-8")

    assert any("authored vectors" in e for e in broken(altered_vectors, "b9"))

    def dropped_latin_posting(out):
        p = out / "concordance.json"
        c = json.loads(p.read_text(encoding="utf-8"))
        key = next(key for key, postings in c["latin"]["forms"].items() if len(postings) > 1)
        c["latin"]["forms"][key].pop()
        p.write_text(json.dumps(c), encoding="utf-8")

    assert any("emitted index" in e for e in broken(dropped_latin_posting, "b10"))

    def rotated_language_texts(out):
        p = out / "languages/pl/concordance.json"
        c = json.loads(p.read_text(encoding="utf-8"))
        c["texts"] = c["texts"][1:] + c["texts"][:1]
        p.write_text(json.dumps(c), encoding="utf-8")

    assert any("emitted translation index" in e for e in broken(rotated_language_texts, "b11"))

    def dropped_language_posting(out):
        p = out / "languages/pl/concordance.json"
        c = json.loads(p.read_text(encoding="utf-8"))
        key = next(key for key, postings in c["terms"].items() if len(postings) > 1)
        c["terms"][key].pop()
        p.write_text(json.dumps(c), encoding="utf-8")

    assert any("emitted translation index" in e for e in broken(dropped_language_posting, "b12"))

    def altered_head(out):
        p = out / "lexicon/heads.json"
        lexicon = json.loads(p.read_text(encoding="utf-8"))
        key = next(iter(lexicon["entries"]))
        lexicon["entries"][key]["lemma"] = "corruptum"
        p.write_text(json.dumps(lexicon), encoding="utf-8")

    assert any("emitted heads" in e for e in broken(altered_head, "b13"))

    def altered_localized_entry(out):
        p = out / "languages/pl/lexicon.json"
        lexicon = json.loads(p.read_text(encoding="utf-8"))
        key = next(iter(lexicon["entries"]))
        entry = lexicon["entries"][key]
        field = next(iter(entry))
        entry[field] = "uszkodzone"
        p.write_text(json.dumps(lexicon), encoding="utf-8")

    assert any("emitted localized lexicon" in e for e in broken(altered_localized_entry, "b14"))

    def altered_calendar_row(out):
        p = out / "calendar.json"
        calendar = json.loads(p.read_text(encoding="utf-8"))
        year = next(iter(calendar["years"]))
        calendar["years"][year][0][3] = 99
        p.write_text(json.dumps(calendar), encoding="utf-8")

    assert any("emitted calendar" in e for e in broken(altered_calendar_row, "b15"))
