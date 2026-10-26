"""The Ascension Vigil Gospel: complete pericope, context, and bound source chain."""

import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import emit, store
from build_reader import introductiones as reader_intro
from build_reader.bibliography_bindings import (
    BindingError,
    collation_subject,
    digest,
    selected_text,
    witness_subject,
)
from checks import (
    collate,
    delivery,
    interlinear,
    participation,
    prose,
    syntax,
    translation_provenance,
)
from checks import introductiones as checker_intro

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.vigilia-ascensionis-evangelium"
WITNESSES = ROOT / "witnesses" / TEXT


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def words(doc):
    return {w["id"]: w for s in doc["segments"] for w in s["words"]}


def groups(layer):
    return [a for s in layer["segments"].values() for a in s.get("alignments", [])]


@pytest.fixture
def installed():
    store.clear_caches()
    return store.load(ROOT, TEXT)


def test_actual_manifest_loading_and_complete_pericope(installed):
    doc, layers = installed
    assert set(layers) == {"pl", "en"}
    assert [s["id"] for s in doc["segments"]] == [f"s{i:02}" for i in range(1, 12)]
    assert [s["verse"] for s in doc["segments"]] == list(range(1, 12))
    ws = words(doc)
    assert list(ws) == [f"w{i:03}" for i in range(1, 179)]
    assert " ".join(w["form"] + w.get("post", "") for w in list(ws.values())[:9]) == (
        "In illo témpore: Sublevátis Iesus óculis in cælum, dixit:"
    )
    assert (
        " ".join(ws[f"w{i:03}"]["form"] + ws[f"w{i:03}"].get("post", "") for i in range(174, 179))
        == "et ego ad te vénio."
    )
    assert not any(w["form"] in {"Sancte", "Amen"} for w in ws.values())
    for language in layers:
        manifest = store.language_manifest(ROOT, language)
        assert manifest["texts"].count(TEXT) == 1
        assert manifest["titles"][TEXT]["title"]
        assert set(layers[language]["segments"]) == {s["id"] for s in doc["segments"]}


def test_all_reused_lemmas_exist_in_each_independent_dictionary(installed):
    doc, _ = installed
    lemmas = {w["lemma"] for w in words(doc).values()}
    assert len(lemmas) == 68
    neutral = read(ROOT / "lexicon" / "lemmata.json")
    assert lemmas <= neutral["entries"].keys()
    for language in ("pl", "en"):
        dictionary = read(ROOT / "languages" / language / "lexicon.json")
        assert lemmas <= dictionary["entries"].keys()


def test_formal_uncertainties_stay_pending_and_actors_are_not_inverted(installed):
    doc, _ = installed
    ws = words(doc)
    for ident in ("w011", "w028"):
        assert ws[ident]["analysis"] == {
            "confidence": "medium",
            "sources": ["editorial", "whitakers", "collatinus"],
            "review": "pending",
        }
    assert ws["w011"]["morph"]["tense"] == "perf"
    assert ws["w028"]["morph"] == {"pos": "adj", "case": "nom", "number": "sg", "gender": "n"}
    assert ws["w028"]["substantive"] is True
    assert ws["w029"]["morph"]["case"] == "acc"
    assert ws["w032"]["morph"]["person"] == 3
    assert ws["w033"]["morph"]["case"] == "dat"
    assert ws["w033"]["morph"]["number"] == "pl"
    assert ws["w058"]["morph"]["mood"] == "ind"
    assert ws["w058"]["morph"]["person"] == 1
    assert ws["w178"]["morph"]["tense"] == "pres"


def test_native_syntax_and_bounded_bad_head_recovery(installed):
    doc, _ = installed
    assert syntax.check(doc) == []
    ws = words(doc)
    assert {w: ws[w]["head"] for w in ("w089", "w147", "w152", "w156")} == {
        "w089": "w090",
        "w147": "w148",
        "w152": "w150",
        "w156": "w155",
    }
    bad = deepcopy(doc)
    words(bad)["w152"]["head"] = "w152"
    assert any("w152" in e for e in syntax.check(bad))
    words(bad)["w152"]["head"] = "w150"
    assert syntax.check(bad) == []


@pytest.mark.parametrize(
    "language,direct,members,realized", [("pl", 127, 50, 21), ("en", 97, 80, 31)]
)
def test_every_position_has_one_realization_and_all_cards_survive(
    installed, language, direct, members, realized
):
    doc, layers = installed
    layer = layers[language]
    assert interlinear.check(doc, layer) == []
    aligned = groups(layer)
    positive = [g for g in aligned if "gloss" in g]
    assert len(positive) == realized
    assert sum(len(g["words"]) for g in positive) == members
    assert sum("gloss" in row for row in layer["words"].values()) == direct
    assert [g for g in aligned if "reason" in g] == [{"words": ["w033"], "reason": "idiom"}]
    assert direct + members + 1 == 178
    assert max(len(g["words"]) for g in positive) == 6
    assert set(layer["words"]) <= set(words(doc))
    assert {w for g in aligned for w in g["words"]} | {
        w for w, fields in layer["words"].items() if "gloss" in fields
    } == set(words(doc))
    assert "note" in layer["words"]["w011"] and "note" in layer["words"]["w028"]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_native_alignment_rejects_double_realization_and_recovers(installed, language):
    doc, layers = installed
    good = layers[language]
    bad = deepcopy(good)
    bad["words"]["w033"]["gloss"] = "im" if language == "pl" else "to them"
    assert any("w033" in e for e in interlinear.check(doc, bad))
    del bad["words"]["w033"]["gloss"]
    assert interlinear.check(doc, bad) == []
    bad = deepcopy(good)
    late = next(g for g in bad["segments"]["s05"]["alignments"] if "w074" in g["words"])
    late["words"].remove("w077")
    assert interlinear.check(doc, bad)
    assert interlinear.check(doc, good) == []


@pytest.mark.parametrize(
    "language,gloss",
    [
        ("pl", "miałem u Ciebie, zanim świat istniał"),
        ("en", "I had with You before the world existed"),
    ],
)
def test_delayed_presence_belongs_to_glory_possession_not_world_existence(
    installed, language, gloss
):
    _, layers = installed
    group = next(g for g in groups(layers[language]) if "w074" in g["words"])
    assert group == {"words": [f"w{i:03}" for i in range(74, 80)], "anchor": "w074", "gloss": gloss}
    assert "gloss" in layers[language]["words"]["w073"]
    assert "w073" not in group["words"]


def test_sentence_boundaries_and_emphatic_imperative(installed):
    _, layers = installed
    assert layers["pl"]["words"]["w013"]["gloss"] == "Otocz chwałą"
    assert layers["pl"]["words"]["w136"]["gloss"] == "Nie"
    assert layers["en"]["words"]["w013"]["gloss"] == "Glorify"
    assert layers["en"]["segments"]["s05"]["translation"] == (
        "And now, Father, glorify Me Yourself in Your own presence with the glory "
        "I had with You before the world existed."
    )
    assert {
        "words": ["w066", "w067", "w068", "w069"],
        "anchor": "w066",
        "gloss": "Father, glorify Me Yourself",
    } in groups(layers["en"])


@pytest.mark.parametrize(
    "language,named,passive,departure",
    [
        ("pl", "Jezusa Chrystusa, którego posłałeś", "zostałem otoczony chwałą", "już nie"),
        ("en", "Jesus Christ, whom You have sent", "I have been glorified", "I am no longer"),
    ],
)
def test_named_object_perfect_passive_and_departure(installed, language, named, passive, departure):
    _, layers = installed
    layer = layers[language]
    assert {"words": ["w048", "w049", "w050", "w051"], "anchor": "w050", "gloss": named} in groups(
        layer
    )
    assert {"words": ["w159", "w160"], "anchor": "w159", "gloss": passive} in groups(layer)
    anchor = "w164" if language == "pl" else "w166"
    assert interlinear.effective_gloss(layer, anchor) == departure
    prose = layer["segments"]["s09"]["translation"]
    assert (
        "Nie proszę za światem, lecz za tymi"
        if language == "pl"
        else "I do not pray for the world, but for those"
    ) in prose
    last = layer["segments"]["s11"]["translation"]
    assert ("oni zaś są na świecie" if language == "pl" else "they are in the world") in last
    assert last.endswith("idę do Ciebie." if language == "pl" else "I am coming to You.")


@pytest.mark.parametrize("language", ["pl", "en"])
def test_actual_artifact_transport_preserves_all_word_cards_and_groups(installed, language):
    doc, layers = installed
    raw = store.core(ROOT, TEXT)
    tables = [emit.Table() for _ in range(4)]
    parses, analyses, shared_citations, local_citations = tables
    neutral = emit.core_artifact(doc, raw, parses, analyses, shared_citations)
    target = emit.language_artifact(doc, layers[language], local_citations)
    decoded, translated = emit.expand(neutral, target, *[table.order for table in tables])
    expected, expected_layers = emit._strip(doc, {language: layers[language]})
    assert decoded == expected and translated == expected_layers[language]
    assert list(words(decoded)) == [f"w{i:03}" for i in range(1, 179)]
    assert interlinear.check(decoded, translated) == []
    assert groups(translated) == groups(layers[language])


def test_complete_two_witness_collation_and_exact_accidentals(installed):
    doc, _ = installed
    errors, warnings, stats = collate.collate(doc, WITNESSES)
    assert errors == warnings == []
    assert {k: stats[k] for k in ("words", "witnesses", "partial", "variants_adjudicated")} == {
        "words": 178,
        "witnesses": 2,
        "partial": 0,
        "variants_adjudicated": 2,
    }
    observed = {}
    for name in ("mr", "vatican1962"):
        meta, body = collate.load_witness(WITNESSES / f"{name}.txt")
        assert meta["witness"] == name and "covers" not in meta
        observed[name] = body.split()
        assert len(observed[name]) == 178
    assert [
        (i + 1, a, b)
        for i, (a, b) in enumerate(zip(observed["mr"], observed["vatican1962"], strict=True))
        if a != b
    ] == [(41, "Ut", "ut"), (145, "mihi:", "mihi,")]


def test_native_collation_rejects_missing_ruling_and_truncated_body_then_recovers(
    installed, tmp_path
):
    doc, _ = installed
    target = tmp_path / "witnesses"
    shutil.copytree(WITNESSES, target)
    app_path = target / "apparatus.json"
    original = app_path.read_text(encoding="utf-8")
    bad = json.loads(original)
    bad["adjudicated"] = bad["adjudicated"][:1]
    app_path.write_text(json.dumps(bad), encoding="utf-8")
    assert collate.collate(doc, target)[0]
    app_path.write_text(original, encoding="utf-8")
    assert collate.collate(doc, target)[0] == []
    path = target / "vatican1962.txt"
    original = path.read_text(encoding="utf-8")
    path.write_text(original.rsplit("vénio.", 1)[0], encoding="utf-8")
    assert collate.collate(doc, target)[0]
    path.write_text(original, encoding="utf-8")
    assert collate.collate(doc, target)[0] == []


def test_actual_graph_resolves_complete_pending_source_chain(installed):
    doc, _ = installed
    graph = read(ROOT / "bibliography" / "graph.json")
    witnesses = [w for w in graph["witnesses"] if w["text"] == TEXT]
    assert len(witnesses) == 2
    bound = {}
    for witness in witnesses:
        bound[witness["id"]] = witness_subject(ROOT, witness, graph, doc)
        assert bound[witness["id"]]["contract"] == "witness-review-2"
        assert witness["review"] == {
            "status": "reviewed",
            "sha256": digest(bound[witness["id"]]),
        }
    rows = [c for c in graph["collations"] if c["text"] == TEXT]
    assert len(rows) == 1
    subject = collation_subject(ROOT, rows[0], doc, bound)
    assert subject["contract"] == "collation-review-2"
    assert rows[0]["review"] == {"status": "reviewed", "sha256": digest(subject)}
    assert rows[0]["selected_text_sha256"] == digest(selected_text(doc))
    bad = deepcopy(witnesses[0])
    bad["transcription_sha256"] = "0" * 64
    with pytest.raises(BindingError, match="transcription_sha256"):
        witness_subject(ROOT, bad, graph, doc)
    assert witness_subject(ROOT, witnesses[0], graph, doc)["contract"] == "witness-review-2"
    bad = deepcopy(rows[0])
    bad["apparatus_sha256"] = "0" * 64
    with pytest.raises(BindingError, match="apparatus_sha256"):
        collation_subject(ROOT, bad, doc, bound)
    assert collation_subject(ROOT, rows[0], doc, bound)["contract"] == "collation-review-2"


def test_all_twenty_two_provenance_rows_bind_actual_source_and_target(installed):
    raw = store.core(ROOT, TEXT)
    ledger, errors = translation_provenance.load(ROOT)
    assert errors == []
    own = {k: v for k, v in ledger.items() if k.startswith(TEXT + ".")}
    assert len(own) == 22
    for language in ("pl", "en"):
        layer = store.raw_layer(ROOT, language, TEXT)
        for segment in raw["segments"]:
            site = f"{TEXT}.{segment['id']}.{language}"
            row = own[site]
            assert row["origin"] == "working-unsettled" and row["review"] == "working"
            assert row["familiar_core"] is False
            assert row["source_sha256"] == translation_provenance.canonical_hash(
                translation_provenance.source_payload(segment)
            )
            assert row["target_sha256"] == translation_provenance.canonical_hash(
                layer["segments"][segment["id"]]["translation"]
            )
    changed = deepcopy(raw["segments"][4])
    words({"segments": [changed]})["w074"]["morph"]["tense"] = "pres"
    assert (
        translation_provenance.canonical_hash(translation_provenance.source_payload(changed))
        != (own[f"{TEXT}.s05.en"]["source_sha256"])
    )
    target = store.raw_layer(ROOT, "en", TEXT)["segments"]["s05"]["translation"]
    assert (
        translation_provenance.canonical_hash(target + " ")
        != own[f"{TEXT}.s05.en"]["target_sha256"]
    )


def test_final_gospel_delivery_is_eleven_celebrant_lines_without_participation(installed):
    doc, _ = installed
    assert tuple(len(s["words"]) for s in doc["segments"]) == (
        20,
        15,
        16,
        12,
        16,
        19,
        10,
        23,
        17,
        14,
        16,
    )
    assert delivery.GOSPEL_BODIES["vigilia-ascensionis"] == (
        20,
        15,
        16,
        12,
        16,
        19,
        10,
        23,
        17,
        14,
        16,
    )
    assert delivery.check_doc(doc) == ([], 11)
    assert participation.check_doc(doc) == ([], 0)
    for segment in doc["segments"]:
        assert (segment["speaker"], segment["voice"]) == ("sacerdos", "clara")
        assert segment["delivery"] == {"cantu": {"speaker": "sacerdos", "voice": "cantus"}}
        assert delivery.derive(doc, segment) == segment["delivery"]
        assert "participation" not in segment and participation.derive(doc, segment) == {}


@pytest.mark.parametrize(
    "fault",
    [
        "missing-override",
        "wrong-voice",
        "wrong-actor",
        "base-voice",
        "base-actor",
        "missing-segment",
        "extra-segment",
        "foreign-word",
        "unknown-gospel",
    ],
)
def test_new_gospel_delivery_rejects_bounded_damage_and_recovers(installed, fault):
    doc, _ = installed
    damaged = deepcopy(doc)
    first = damaged["segments"][0]
    if fault == "missing-override":
        del first["delivery"]
    elif fault == "wrong-voice":
        first["delivery"]["cantu"]["voice"] = "clara"
    elif fault == "wrong-actor":
        first["delivery"]["cantu"]["speaker"] = "schola"
    elif fault == "base-voice":
        first["voice"] = "submissa"
    elif fault == "base-actor":
        first["speaker"] = "minister"
    elif fault == "missing-segment":
        del damaged["segments"][5]
    elif fault == "extra-segment":
        damaged["segments"].append({**deepcopy(first), "id": "s12"})
    elif fault == "foreign-word":
        first["words"][0]["id"] = "w999"
    else:
        damaged["id"] = "proprium.vigilia-ascensionis-uninventoried-evangelium"
    assert delivery.check_doc(damaged)[0]
    if fault in {
        "base-voice",
        "base-actor",
        "missing-segment",
        "extra-segment",
        "foreign-word",
        "unknown-gospel",
    }:
        assert all(delivery.derive(damaged, s) == {} for s in damaged["segments"])
    assert delivery.check_doc(doc) == ([], 11)


def test_new_gospel_has_no_fabricated_historical_delivery_preimage(installed):
    from gospel_delivery_fixture import (
        DATA,
        current_gospel_selected_hash,
        current_gospel_source_hash,
        without_gospel_delivery,
    )

    doc, _ = installed
    assert len(DATA["source"]) == 101 and TEXT not in DATA["source"]
    assert TEXT not in DATA["selected"] and TEXT not in DATA["graph_sets"]
    assert without_gospel_delivery(doc) == doc
    assert (
        current_gospel_selected_hash(TEXT, "not-a-historical-record") == "not-a-historical-record"
    )
    assert (
        current_gospel_source_hash(TEXT, "s01", "not-a-historical-record")
        == "not-a-historical-record"
    )


def test_actual_john_heading_and_resource_binding_preserve_the_printed_limit():
    table = reader_intro.resource(ROOT)
    rows = [r for r in table["announcements"] if r["reading"] == TEXT.replace(".", "/", 1)]
    assert rows == [
        {
            "reading": "proprium/vigilia-ascensionis-evangelium",
            "unit": "sequentia-sancti-evangelii-secundum-ioannem",
            "reference": "Ioann. 17, 1-11",
            "pericope": {"book": "Ioann", "passages": [{"chapter": 17, "verses": [[1, 11]]}]},
        }
    ]
    assert table["schema_version"] == "2.0.0" and len(table["announcements"]) == 206
    unit = next(u for u in table["units"] if u["id"] == rows[0]["unit"])
    owner = store.core(ROOT, unit["text"].replace("/", ".", 1))
    segment = next(s for s in owner["segments"] if s["id"] == unit["segment"])
    assert [w["id"] for w in segment["words"]] == unit["words"]
    assert " ".join(w["form"] + w.get("post", "") for w in segment["words"]) == (
        "Sequéntia sancti Evangélii secúndum Ioánnem"
    )
    actual = store.core(ROOT, TEXT)
    assert actual["segments"][-1]["words"][-1]["id"] == "w178"
    assert actual["segments"][-1]["words"][-1]["form"] == "vénio"
    assert checker_intro.check(ROOT) == (
        [],
        {"units": 31, "events": 6, "occurrences": 14, "owner_texts": 29, "announcements": 206},
    )


@pytest.mark.parametrize("fault", ["wrong-book", "wrong-pericope", "missing-binding", "wrong-leaf"])
def test_new_john_binding_fails_native_validation_and_recovers(tmp_path, fault):
    from test_introductiones import small_corpus

    corpus = small_corpus(tmp_path)
    path = corpus / "ordo/introductiones.json"
    original = path.read_bytes()
    healthy, _ = checker_intro.check(corpus)
    assert healthy == []
    damaged = json.loads(original)
    row = next(r for r in damaged["announcements"] if r["reading"] == TEXT)
    if fault == "wrong-book":
        row["unit"] = "sequentia-sancti-evangelii-secundum-lucam"
    elif fault == "wrong-pericope":
        row["pericope"]["passages"][0]["chapter"] = 18
    elif fault == "wrong-leaf":
        row["leaf"] = 425
    else:
        damaged["announcements"].remove(row)
    path.write_text(json.dumps(damaged), encoding="utf-8")
    errors, _ = checker_intro.check(corpus)
    assert errors and any(TEXT in error for error in errors)
    with pytest.raises(ValueError, match="invalid authored library"):
        checker_intro.authored(corpus)
    path.write_bytes(original)
    assert checker_intro.check(corpus)[0] == []


@pytest.mark.parametrize(
    "language,wid,field,old_prose",
    [
        (
            "pl",
            "w011",
            "note",
            "Venit może być formą czasu teraźniejszego lub perfectum. Kontekst wskazuje na "
            "nadejście godziny; możliwe jest też odczytanie „nadchodzi”.",
        ),
        (
            "pl",
            "w028",
            "explanation",
            "Łacińskie „wszystko” oznacza tu ludzi powierzonych Synowi. Późniejsze „im” "
            "podejmuje tę samą zbiorowość; po polsku odbiorcę wyraża już „wszystkim”.",
        ),
        (
            "pl",
            "w028",
            "note",
            "Forma omne dopuszcza mianownik i biernik. Można ją odczytać jako temat podjęty "
            "później przez „im”; możliwe pozostaje przyciągnięcie do biernika zdania "
            "względnego. Sens odnosi się do ludzi, nie do rzeczy.",
        ),
        (
            "pl",
            "w071",
            "explanation",
            "Jezus prosi Ojca o chwałę u Niego samego; nie wskazuje tu innej osoby.",
        ),
        (
            "en",
            "w011",
            "note",
            "Venit can be present or perfect. The context supports the hour having arrived; "
            "“is coming” remains formally possible.",
        ),
        (
            "en",
            "w028",
            "explanation",
            "The Latin collective “all” refers to the people entrusted to the Son. The later "
            "“to them” resumes those same recipients; English already expresses them as “to "
            "all.”",
        ),
        (
            "en",
            "w028",
            "note",
            "Omne can be nominative or accusative. It may stand as a topic resumed by “to "
            "them”; attraction to the relative clause's accusative remains possible. The "
            "referent is people, not an inanimate gift.",
        ),
    ],
)
def test_own_prose_rejects_each_original_semicolon_and_recovers(
    installed, language, wid, field, old_prose
):
    _, layers = installed
    healthy = layers[language]
    assert prose.check(healthy) == []
    damaged = deepcopy(healthy)
    current = damaged["words"][wid][field]
    assert ";" not in current
    damaged["words"][wid][field] = old_prose
    assert prose.check(damaged) == [
        f"{TEXT}:{wid}.{field}.{language}: uses a semicolon — "
        "this edition's own prose has none. Use a full stop, or an 'and'"
    ]
    damaged["words"][wid][field] = current
    assert damaged == healthy
    assert prose.check(damaged) == []


@pytest.mark.parametrize("language", ["pl", "en"])
def test_scripture_semicolons_remain_outside_own_prose_rule(installed, language):
    _, layers = installed
    healthy = layers[language]
    assert prose.check(healthy) == []
    expected = {
        "pl": {
            "s04": "Ja otoczyłem Cię chwałą na ziemi; doprowadziłem do końca dzieło, "
            "które dałeś Mi do wykonania.",
            "s06": "Objawiłem Twoje imię ludziom, których dałeś Mi ze świata. "
            "Należeli do Ciebie i Mnie ich dałeś; i zachowali Twoje słowo.",
            "s10": "I wszystko, co Moje, jest Twoje, a to, co Twoje, jest Moje; i "
            "zostałem w nich otoczony chwałą.",
        },
        "en": {
            "s04": "I have glorified You on earth; I have completed the work You gave Me to do.",
            "s08": "because I have given them the words You gave Me, and they "
            "themselves have received them; they have truly recognized that I "
            "came forth from You, and they have believed that You sent Me.",
        },
    }
    assert {
        sid: segment["translation"]
        for sid, segment in healthy["segments"].items()
        if ";" in segment["translation"]
    } == expected[language]
    copied = deepcopy(healthy)
    original = copied["segments"]["s01"]["translation"]
    copied["segments"]["s01"]["translation"] = original + ";"
    assert prose.check(copied) == []
    copied["segments"]["s01"]["translation"] = original
    assert copied == healthy
    assert prose.check(copied) == []


def test_polish_help_describes_the_displayed_verbal_phrase(installed):
    _, layers = installed
    layer = layers["pl"]
    assert prose.check(layer) == []
    assert layer["words"]["w159"]["explanation"] == (
        "Jezus mówi o chwale, którą już otrzymał w tych ludziach. Dwa łacińskie "
        "słowa oddano po polsku jednym zwrotem: „zostałem otoczony chwałą”."
    )
    assert [g for g in groups(layer) if "w159" in g["words"]] == [
        {"words": ["w159", "w160"], "anchor": "w159", "gloss": "zostałem otoczony chwałą"}
    ]
