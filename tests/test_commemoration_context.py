"""Localized context prose: real input migrations, strict negatives and exact recovery.

Fixtures copy the five established authored identities, not unprepared incoming saints.
No semantic decision is inferred from a slot's reference relation.
"""

import copy
import json
import shutil
from pathlib import Path

import pytest

from build_reader import commemorationes as reader
from build_reader import store
from checks import commemorationes as checker
from checks.prose import check as check_prose
from kalendarium import commemorationes as producer

CORPUS = Path(store.__file__).resolve().parent.parent
IDS = (
    "dominica-impedita",
    "feria-adventus",
    "festum-impeditum",
    "litaniae-maiores",
    "sancta-petronilla",
)
TITLES = {
    "pl": (
        "Niedziela przeszkodzona",
        "Dzień powszedni Adwentu",
        "Święto przeszkodzone",
        "Litanie Większe",
        "Świętej Petroneli, Dziewicy",
    ),
    "en": (
        "Impeded Sunday",
        "Weekday of Advent",
        "Impeded Feast",
        "Greater Litanies",
        "Saint Petronilla, Virgin",
    ),
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@pytest.fixture
def context_corpus(tmp_path):
    corpus = tmp_path / "corpus"
    (corpus / "commemorationes").mkdir(parents=True)
    (corpus / "texts/proprium").mkdir(parents=True)
    for identity in IDS:
        source = CORPUS / "commemorationes" / f"{identity}.json"
        shutil.copyfile(source, corpus / "commemorationes" / source.name)
        for slot in read(source)["slots"]:
            if slot["text"] is not None:
                # The authored validator checks reachability, not placeholder sacred content.
                (corpus / "texts/proprium" / f"{slot['text'].split('.', 1)[1]}.json").write_text(
                    "{}"
                )
    for language in ("pl", "en"):
        directory = corpus / "languages" / language
        (directory / "commemorationes").mkdir(parents=True)
        (directory / "manifest.json").write_text("{}")
        for identity in IDS:
            source = CORPUS / "languages" / language / "commemorationes" / f"{identity}.json"
            shutil.copyfile(source, directory / "commemorationes" / source.name)
    assert checker.check(corpus)[0] == []
    return corpus


@pytest.mark.parametrize("language", ("pl", "en"))
def test_all_five_existing_title_documents_are_migrated_without_other_changes(language):
    for identity, title in zip(IDS, TITLES[language], strict=True):
        assert read(CORPUS / "languages" / language / "commemorationes" / f"{identity}.json") == {
            "commemoration_schema": "1.1.0",
            "id": identity,
            "language": language,
            "title": title,
        }


@pytest.mark.parametrize("language", ("pl", "en"))
def test_projection_keeps_absent_empty_and_replacement_distinct(context_corpus, language):
    corpus = context_corpus
    path = corpus / "languages" / language / "commemorationes/litaniae-maiores.json"
    original = path.read_bytes()
    doc = read(path)
    doc["about"] = {"secreta": "", "postcommunio": "Context-only explanation."}
    try:
        write(path, doc)
        assert checker.check(corpus)[0] == []
        expected = {
            "schema_version": "1.1.0",
            "language": language,
            "titles": [
                {
                    "id": identity,
                    "title": title,
                    **(
                        {"about": {"secreta": "", "postcommunio": "Context-only explanation."}}
                        if identity == "litaniae-maiores"
                        else {}
                    ),
                }
                for identity, title in zip(IDS, TITLES[language], strict=True)
            ],
        }
        emitted = reader.language_catalog(corpus, language)
        assert emitted == expected
        assert "collecta" not in emitted["titles"][3]["about"]
        assert "about" not in emitted["titles"][4]
        # The emitted verifier must not ask its own producer what it should have emitted.
        assert reader.verify_language_catalog(corpus, language, expected) == []
        for mutate in (
            lambda value: value["titles"][3].pop("about"),
            lambda value: value["titles"][3]["about"].pop("secreta"),
            lambda value: value["titles"][3]["about"].__setitem__("secreta", "not empty"),
            lambda value: value["titles"][4].__setitem__("about", {}),
            lambda value: value.__setitem__("schema_version", "1.0.0"),
        ):
            broken = copy.deepcopy(expected)
            mutate(broken)
            assert reader.verify_language_catalog(corpus, language, broken) == [
                f"commemorationes: languages/{language}/commemorationes.json "
                "differs from authored context catalog"
            ]
            assert reader.verify_language_catalog(corpus, language, expected) == []
    finally:
        path.write_bytes(original)
    assert path.read_bytes() == original
    assert checker.check(corpus)[0] == []
    assert "about" not in reader.language_catalog(corpus, language)["titles"][3]


@pytest.mark.parametrize("language", ("pl", "en"))
@pytest.mark.parametrize(
    "about",
    [
        None,
        [],
        "",
        {"secreta": None},
        {"secreta": 1},
        {"secreta": False},
        {"secreta": []},
        {"secreta": {}},
        {"secreta": " \n\t"},
        {"evangelium": "No."},
        {"__proto__": "No."},
    ],
    ids=[
        "null-map",
        "array-map",
        "string-map",
        "null-value",
        "number-value",
        "bool-value",
        "array-value",
        "object-value",
        "whitespace",
        "unknown-key",
        "prototype-key",
    ],
)
def test_invalid_maps_fail_before_emission_and_recover(context_corpus, language, about):
    corpus = context_corpus
    path = corpus / "languages" / language / "commemorationes/litaniae-maiores.json"
    original = path.read_bytes()
    doc = read(path)
    doc["about"] = about
    try:
        write(path, doc)
        errors, _ = checker.check(corpus)
        assert any(":about:" in error for error in errors), errors
        with pytest.raises(ValueError, match="commemorationes: invalid authored"):
            reader.language_catalog(corpus, language)
        assert reader.verify_language_catalog(corpus, language, {})
    finally:
        path.write_bytes(original)
    assert path.read_bytes() == original and checker.check(corpus)[0] == []


@pytest.mark.parametrize("language", ("pl", "en"))
@pytest.mark.parametrize(
    "mutation,diagnostic",
    [
        (lambda doc: doc.__setitem__("commemoration_schema", "1.0.0"), "commemoration_schema"),
        (lambda doc: doc.__setitem__("extra", True), "localized fields"),
        (lambda doc: doc.__setitem__("language", "unknown"), "id/language"),
        (lambda doc: doc.__setitem__("id", "unknown"), "id/language"),
    ],
)
def test_actual_identity_and_version_negatives_recover(
    context_corpus, language, mutation, diagnostic
):
    path = context_corpus / "languages" / language / "commemorationes/litaniae-maiores.json"
    original = path.read_bytes()
    doc = read(path)
    try:
        mutation(doc)
        write(path, doc)
        errors, _ = checker.check(context_corpus)
        assert any(diagnostic in error for error in errors), errors
        with pytest.raises(ValueError, match="commemorationes: invalid authored"):
            reader.language_catalog(context_corpus, language)
    finally:
        path.write_bytes(original)
    assert path.read_bytes() == original and checker.check(context_corpus)[0] == []


@pytest.mark.parametrize("language", ("pl", "en"))
def test_calendar_slot_overrides_are_not_admitted(context_corpus, language):
    path = context_corpus / "languages" / language / "commemorationes/feria-adventus.json"
    original = path.read_bytes()
    doc = read(path)
    try:
        doc["about"] = {"secreta": ""}
        write(path, doc)
        assert any(
            "unknown or calendar slot" in error for error in checker.check(context_corpus)[0]
        )
        with pytest.raises(ValueError, match="commemorationes: invalid authored"):
            reader.language_catalog(context_corpus, language)
    finally:
        path.write_bytes(original)
    assert path.read_bytes() == original and checker.check(context_corpus)[0] == []


@pytest.mark.parametrize("language", ("pl", "en"))
@pytest.mark.parametrize(
    "fragment",
    [
        '"about": {}, "about": {"secreta": ""}',
        '"about": {"secreta": "first", "secreta": ""}',
    ],
    ids=["duplicate-map", "duplicate-slot"],
)
def test_existing_duplicate_key_guard_refuses_raw_ambiguity(context_corpus, language, fragment):
    path = context_corpus / "languages" / language / "commemorationes/litaniae-maiores.json"
    original = path.read_bytes()
    try:
        path.write_text(
            original.decode("utf-8").rstrip()[:-1] + "," + fragment + "}\n", encoding="utf-8"
        )
        errors, _ = checker.check(context_corpus)
        assert any("appears 2 times" in error for error in errors), errors
        with pytest.raises(ValueError, match="appears 2 times"):
            reader.language_catalog(context_corpus, language)
        assert any(
            "appears 2 times" in error
            for error in reader.verify_language_catalog(context_corpus, language, {})
        )
    finally:
        path.write_bytes(original)
    assert path.read_bytes() == original and checker.check(context_corpus)[0] == []


def test_verifier_does_not_consult_the_emitter(context_corpus, monkeypatch):
    expected = {
        "schema_version": "1.1.0",
        "language": "en",
        "titles": [
            {"id": identity, "title": title}
            for identity, title in zip(IDS, TITLES["en"], strict=True)
        ],
    }
    monkeypatch.setattr(reader, "language_catalog", lambda *_args: {"wrong": "producer answer"})
    assert reader.verify_language_catalog(context_corpus, "en", expected) == []


@pytest.mark.parametrize("language", ("pl", "en"))
@pytest.mark.parametrize(
    "prose,diagnostic",
    [
        (
            "First; second.",
            "uses a semicolon — this edition's own prose has none. Use a full stop, or an 'and'",
        ),
        (
            "as the custom is",
            "hedges ('as the custom is') — say what the book does, or say who decides and when",
        ),
        (
            "zależnie od zwyczaju",
            "hedges ('zależnie od zwyczaju') — say what the book does, or say who decides and when",
        ),
    ],
    ids=["semicolon", "english-hedge", "polish-hedge"],
)
def test_context_own_prose_fails_at_source_and_independent_verification(
    context_corpus, language, prose, diagnostic
):
    corpus = context_corpus
    path = corpus / "languages" / language / "commemorationes/litaniae-maiores.json"
    original = path.read_bytes()
    assert checker.check(corpus)[0] == []
    healthy = reader.language_catalog(corpus, language)
    assert reader.verify_language_catalog(corpus, language, healthy) == []
    doc = read(path)
    doc["about"] = {"secreta": prose}
    matching_output = copy.deepcopy(healthy)
    next(row for row in matching_output["titles"] if row["id"] == "litaniae-maiores")["about"] = {
        "secreta": prose
    }
    expected_error = (
        f"languages/{language}/commemorationes/litaniae-maiores.json:"
        f"secreta:about.{language}: {diagnostic}"
    )
    try:
        write(path, doc)
        assert checker.check(corpus)[0] == [expected_error]
        with pytest.raises(ValueError) as caught:
            reader.language_catalog(corpus, language)
        assert str(caught.value) == (
            "commemorationes: invalid authored documents: " + expected_error
        )
        # This object matches the bad source. Equality alone cannot reject it.
        assert reader.verify_language_catalog(corpus, language, matching_output) == [expected_error]
    finally:
        path.write_bytes(original)
    assert path.read_bytes() == original
    assert checker.check(corpus)[0] == []
    assert reader.language_catalog(corpus, language) == healthy
    assert reader.verify_language_catalog(corpus, language, healthy) == []


@pytest.mark.parametrize("language", ("pl", "en"))
@pytest.mark.parametrize(
    "prose",
    ["", "A contextual explanation.", "This edition names the commemoration."],
    ids=["explicit-empty", "valid-prose", "about-not-word-help"],
)
def test_context_prose_preserves_allowed_values_and_exact_recovery(context_corpus, language, prose):
    corpus = context_corpus
    path = corpus / "languages" / language / "commemorationes/litaniae-maiores.json"
    original = path.read_bytes()
    assert checker.check(corpus)[0] == []
    healthy = reader.language_catalog(corpus, language)
    assert reader.verify_language_catalog(corpus, language, healthy) == []
    doc = read(path)
    doc["about"] = {"secreta": prose}
    try:
        write(path, doc)
        assert checker.check(corpus)[0] == []
        emitted = reader.language_catalog(corpus, language)
        row = next(row for row in emitted["titles"] if row["id"] == "litaniae-maiores")
        assert row["about"] == {"secreta": prose}
        assert reader.verify_language_catalog(corpus, language, emitted) == []
    finally:
        path.write_bytes(original)
    assert path.read_bytes() == original
    assert checker.check(corpus)[0] == []
    assert reader.language_catalog(corpus, language) == healthy
    assert reader.verify_language_catalog(corpus, language, healthy) == []


@pytest.mark.parametrize("language", ("pl", "en"))
def test_context_prose_guard_leaves_translation_punctuation_untouched(language):
    layer = {
        "text": "fixture.context",
        "language": language,
        "about": "A contextual explanation.",
        "segments": {"s01": {"translation": "First; second."}},
    }
    before = copy.deepcopy(layer)
    assert check_prose(layer) == []
    assert layer == before


@pytest.mark.parametrize("language", ("pl", "en"))
@pytest.mark.parametrize("missing_directories", (False, True), ids=["empty", "missing"])
def test_no_context_subjects_fail_closed_and_recover_exactly(
    context_corpus, language, missing_directories
):
    corpus = context_corpus
    baseline = checker.check(corpus)
    assert baseline[0] == [] and baseline[1]["commemorations"] == len(IDS)
    healthy = reader.language_catalog(corpus, language)
    assert reader.verify_language_catalog(corpus, language, healthy) == []
    assert len(producer.authored(corpus)) == len(IDS)
    directories = [
        corpus / "commemorationes",
        *(corpus / "languages" / lang / "commemorationes" for lang in ("pl", "en")),
    ]
    originals = {
        path: path.read_bytes() for directory in directories for path in directory.glob("*.json")
    }
    expected_error = "commemorationes: at least one commemoration required"
    empty_output = {"schema_version": "1.1.0", "language": language, "titles": []}
    try:
        for path in originals:
            path.unlink()
        if missing_directories:
            for directory in directories:
                directory.rmdir()
        errors, counts = checker.check(corpus)
        assert errors == [expected_error]
        assert counts == {
            "commemorations": 0,
            "slot_uses": 0,
            "proper_slots": 0,
            "reference_slots": 0,
            "calendar_slots": 0,
        }
        with pytest.raises(ValueError) as caught:
            producer.authored(corpus)
        assert str(caught.value) == (
            "commemorationes: invalid authored documents: " + expected_error
        )
        with pytest.raises(ValueError) as caught:
            reader.language_catalog(corpus, language)
        assert str(caught.value) == (
            "commemorationes: invalid authored documents: " + expected_error
        )
        # Matching empty output must not turn absence of source subjects into success.
        assert reader.verify_language_catalog(corpus, language, empty_output) == [expected_error]
        # The existing outer publication validator remains a separate rejecting boundary.
        empty_table = {
            "schema_version": producer.SCHEMA,
            "commemorations": [],
            "profiles": copy.deepcopy(producer.PROFILES),
            "situations": list(producer.SITUATIONS),
            "decisions": copy.deepcopy(producer.DECISIONS),
            "masses": ["fixture-mass"],
            "occurrences": [],
            "pairs": [],
        }
        with pytest.raises(ValueError) as caught:
            producer.validate(empty_table)
        assert str(caught.value) == expected_error
    finally:
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        for path, original in originals.items():
            path.write_bytes(original)
    assert {path: path.read_bytes() for path in originals} == originals
    assert checker.check(corpus) == baseline
    assert len(producer.authored(corpus)) == len(IDS)
    assert reader.language_catalog(corpus, language) == healthy
    assert reader.verify_language_catalog(corpus, language, healthy) == []
