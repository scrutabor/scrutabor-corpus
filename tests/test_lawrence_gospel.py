"""Keep the grain-of-wheat Gospel's source and contextual reading coherent."""

import json
from pathlib import Path

import pytest

from build_reader import bibliography
from checks import raw_binding, transcription, translation_provenance
from checks.collate import collate

ROOT = Path(__file__).resolve().parents[1]
STEM = "sancti-laurentii-martyris-evangelium"
TEXT = "proprium." + STEM
DIRECTORY = ROOT / "witnesses" / TEXT


def load(path):
    return json.loads((ROOT / path).read_bytes())


def layer(language):
    return load(f"languages/{language}/texts/proprium/{STEM}.json")


def test_inherited_gospel_preserves_the_exact_source_body():
    binding = raw_binding.resolve_binding(DIRECTORY / "do.txt", ROOT)
    assert binding is not None
    registry = raw_binding.load_registry(ROOT)
    upstream = {row["path"]: row["upstream"] for row in registry["archives"].values()}
    assert [
        (upstream[path.relative_to(ROOT).as_posix()], first, last)
        for path, first, last in binding.spans
    ] == [("web/www/missa/Latin/Sancti/02-01.txt", 60, 60)]
    assert binding.source["binding"]["references"] == [
        {"archive": "saint-lawrence", "line": 37, "text": "@Sancti/02-01", "target": 1}
    ]
    assert len(binding.text.split()) == 71
    assert binding.text.split()[4] == "Jesus"
    assert "Sequéntia" not in binding.text and "Joann" not in binding.text
    assert transcription.check_transcriptions(DIRECTORY) == ([], 1)
    assert collate(load(f"texts/proprium/{STEM}.json"), DIRECTORY)[:2] == ([], [])


@pytest.mark.parametrize(
    "word,ours,theirs,kind",
    [
        ("w005", "Iesus", "Jesus", "orthography"),
        ("w009", "amen", "amen,", "punctuation"),
        ("w052", "minístrat,", "mínistrat,", "accent"),
    ],
)
def test_all_three_source_accidentals_are_declared(word, ours, theirs, kind):
    apparatus = load(f"witnesses/{TEXT}/apparatus.json")
    assert apparatus["summary"] == {
        "entries": 3,
        "classes": ["accent", "orthography", "punctuation"],
    }
    rows = {entry["at"]: entry for entry in apparatus["adjudicated"]}
    assert set(rows) == {"w005", "w009", "w052"}
    assert (rows[word]["ours"], rows[word]["witnesses"], rows[word]["class"]) == (
        ours,
        {"do": theirs},
        kind,
    )


def test_printed_scope_and_derived_dependency_are_distinct():
    graph = load("bibliography/graph.json")
    uses = {row["id"]: row for row in graph["uses"]}
    inherited = f"use.{TEXT}.inherited-body.do44667ff"
    assert "02-01" in uses[inherited]["locator"]["section"]
    assert uses[inherited]["role"] == "derived_digital_collation_aid"
    assert (
        "independent textual transmission is not claimed" in uses[f"use.{TEXT}.do44667ff"]["claim"]
    )
    assert "Benziger 1962" in uses[f"use.{TEXT}.mr1962"]["claim"]
    assert "Benziger 1962" in load(f"texts/proprium/{STEM}.json")["editorial"]["source"]["method"]
    witnesses = {row["transcription"]: row for row in graph["witnesses"] if row["text"] == TEXT}
    assert set(witnesses) == {"do", "mr"}
    assert witnesses["do"]["source_dependencies"] == {
        "uses": [inherited],
        "raw_binding": "saint-lawrence-gospel",
    }
    assert witnesses["mr"]["source_dependencies"] == {"uses": [], "raw_binding": None}
    assert all(row["review"] == {"status": "pending"} for row in witnesses.values())
    projected = next(
        row for row in bibliography.public_text_evidence(graph)["texts"] if row["id"] == TEXT
    )
    assert projected["witnesses"] == [] and "collation" not in projected


@pytest.mark.parametrize("language,gloss", [("pl", "obumrze"), ("en", "dies")])
@pytest.mark.parametrize("first,second", [("w018", "w019"), ("w025", "w026")])
def test_each_death_predicate_has_one_minimal_realization(language, gloss, first, second):
    data = layer(language)
    groups = data["segments"]["s01"]["alignments"]
    assert len(groups) == 2
    assert {"words": [first, second], "anchor": first, "gloss": gloss} in groups
    assert "gloss" not in data["words"][first] and "gloss" not in data["words"][second]


@pytest.mark.parametrize(
    "word,gloss",
    [
        ("w007", "swoim"),
        ("w015", "padając"),
        ("w020", "ono"),
        ("w021", "samo"),
        ("w032", "życie"),
        ("w033", "swoje"),
        ("w035", "je"),
        ("w039", "życie"),
        ("w040", "swoje"),
        ("w047", "zachowuje"),
        ("w048", "je"),
    ],
)
def test_polish_context_and_complete_referent_chains(word, gloss):
    assert layer("pl")["words"][word]["gloss"] == gloss


@pytest.mark.parametrize("word,gloss", [("w044", "for"), ("w063", "will be")])
def test_english_working_register(word, gloss):
    assert layer("en")["words"][word]["gloss"] == gloss


def test_polish_prose_keeps_life_referents_and_scoped_divine_capitals():
    prose = layer("pl")["segments"]["s01"]["translation"]
    assert (
        "Kto kocha swoje życie, straci je; "
        "a kto nienawidzi swojego życia na tym świecie, zachowuje je na życie wieczne." in prose
    )
    assert "Jezus powiedział do swoich uczniów" in prose
    assert (
        "Jeśli ktoś Mi służy, niech idzie za Mną; a tam, gdzie jestem Ja, będzie też Mój sługa. "
        "Jeśli ktoś Mi posłuży, uczci go Mój Ojciec." in prose
    )


@pytest.mark.parametrize(
    "language,beginning", [("pl", "Ewangelia formularza"), ("en", "The Gospel of")]
)
def test_about_names_the_reading_in_the_target_language(language, beginning):
    assert layer(language)["about"].startswith(beginning)


def test_revised_prose_keeps_exact_working_provenance_without_promotion():
    ledger = load("languages/pl/translation-provenance.json")
    rows = [row for row in ledger["sites"] if row["site"] == TEXT + ".s01.pl"]
    assert len(rows) == 1
    row = rows[0]
    assert (row["origin"], row["review"], row["familiar_core"]) == (
        "working-unsettled",
        "working",
        False,
    )
    assert row["target_sha256"] == translation_provenance.canonical_hash(
        layer("pl")["segments"]["s01"]["translation"]
    )
    core = load(f"texts/proprium/{STEM}.json")
    assert row["source_sha256"] == translation_provenance.canonical_hash(
        translation_provenance.source_payload(core["segments"][0])
    )


def test_both_source_descriptions_match_the_complete_unexpanded_body():
    editorial = load(f"texts/proprium/{STEM}.json")["editorial"]
    for field in (editorial["notes"], editorial["source"]["method"]):
        assert "Benziger 1962 Editio iuxta typicam" in field
        assert "no shared conclusion or response" in field
        assert "framing" in field or "outside the selected boundary" in field
        assert "pending" in field
    assert "Printed rubrics and abbreviated conclusions are retained" not in editorial["notes"]
