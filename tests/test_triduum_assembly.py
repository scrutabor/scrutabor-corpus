"""Printed Thursday/Vigil boundaries, full source bodies and failing controls."""

import copy
import json
import shutil
from pathlib import Path

import pytest

from build_reader import emit, store
from build_reader.bibliography import validate
from build_reader.bibliography_bindings import digest, selected_text, transcript_digest
from build_reader.layers import expand_core
from build_reader.participation_performance import verify as verify_performance
from checks.delivery import check_doc as delivery_errors
from checks.interlinear import check as interlinear_errors
from checks.lavabo_omissions import errors as assembly_errors
from checks.lexicon import check_text_against_lexicon
from checks.participation import check_doc as participation_errors
from checks.translation_basis import check as basis_errors
from checks.translation_provenance import check as provenance_errors
from checks.triduum_assembly import AGNUS, MASSES, agnus_errors

CORPUS = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((Path(__file__).with_name("triduum_fixture.json")).read_text())
THURSDAY, VIGIL = MASSES
EXPECTED = {
    THURSDAY: [
        {"text": "ordinarium.lavabo", "segments": ["s09", "s10"], "reason": "lavabo-doxology"},
        {"text": "ordinarium.qui-dixisti", "reason": "triduum-peace-prayer"},
    ],
    VIGIL: [
        {"text": "ordinarium.agnus-dei", "reason": "vigil-agnus-dei"},
        {"text": "ordinarium.qui-dixisti", "reason": "triduum-peace-prayer"},
    ],
}


def read(relative, corpus=CORPUS):
    return json.loads((corpus / relative).read_text())


def body():
    return read("texts/ordinarium/agnus-dei-in-cena-domini.json")


def form(mass):
    return read(f"formularies/temporale/{mass}.json")


def test_actual_printed_recension_has_three_distinct_complete_sets_of_cards():
    doc = body()
    assert doc["id"] == FIXTURE["text"] == AGNUS
    assert agnus_errors(doc) == []
    assert [s["id"] for s in doc["segments"]] == ["s01", "s02", "s03"]
    assert [
        " ".join(w.get("pre", "") + w["form"] + w.get("post", "") for w in s["words"])
        for s in doc["segments"]
    ] == FIXTURE["lines"]
    words = [w for s in doc["segments"] for w in s["words"]]
    assert len(words) == FIXTURE["word_count"] == 24
    assert [w["id"] for w in words] == [f"w{i:03}" for i in range(1, 25)]
    assert doc["ids"] == {"next": 25, "segments": {"next": 4}}
    assert check_text_against_lexicon(doc, read("lexicon/lemmata.json")["entries"]) == []
    for index in range(3):
        row = words[index * 8 : (index + 1) * 8]
        assert [w["lemma"] for w in row] == [
            "agnus",
            "deus",
            "qui",
            "tollo",
            "peccatum",
            "mundus",
            "misereor",
            "nos",
        ]
        assert row[0]["morph"]["case"] == "nom"
        assert row[3]["morph"]["person"] == 2
        assert row[4]["morph"]["number"] == "pl"
        assert row[6]["morph"]["voice"] == "dep"
        assert row[6]["morph"]["mood"] == "imp"
        assert row[7]["morph"] == {"pos": "pron", "case": "dat", "number": "pl"}


@pytest.mark.parametrize("language", ["pl", "en"])
def test_each_language_retains_supported_formula_and_all_24_token_realizations(language):
    doc = body()
    layer = read(f"languages/{language}/texts/ordinarium/agnus-dei-in-cena-domini.json")
    assert interlinear_errors(doc, layer) == []
    title = read(f"languages/{language}/manifest.json")["titles"][AGNUS]["title"]
    assert title == (
        "Baranku Boży w Wielki Czwartek" if language == "pl" else "Lamb of God — Holy Thursday"
    )
    assert len(layer["words"]) == 24
    assert list(layer["words"]) == [f"w{i:03}" for i in range(1, 25)]
    assert [layer["segments"][s]["translation"] for s in ("s01", "s02", "s03")] == [
        FIXTURE["translations"][language]
    ] * 3
    for i in range(3):
        assert layer["words"][f"w{i * 8 + 1:03}"]["explanation"]
        if language == "en":
            assert layer["segments"][f"s{i + 1:02}"]["alignments"] == [
                {
                    "words": [f"w{i * 8 + 3:03}", f"w{i * 8 + 4:03}"],
                    "anchor": f"w{i * 8 + 4:03}",
                    "gloss": "You who take away",
                }
            ]
    assert provenance_errors(CORPUS)[0] == []
    assert basis_errors(CORPUS)[0] == []


def test_independent_prints_and_language_bases_keep_narrow_unsealed_claims():
    graph = read("bibliography/graph.json")
    assert validate(CORPUS) == []
    witnesses = [w for w in graph["witnesses"] if w["text"] == AGNUS]
    assert {w["transcription"] for w in witnesses} == {"mr", "vatican"}
    for witness in witnesses:
        assert witness["review"] == {"status": "pending"}
        assert "no independent underlying textual tradition" in witness["independence_basis"]
        transcript = (CORPUS / f"witnesses/{AGNUS}/{witness['transcription']}.txt").read_text()
        assert transcript_digest(transcript) == witness["transcription_sha256"]
        assert [line for line in transcript.splitlines() if not line.startswith("#")] == FIXTURE[
            "lines"
        ]
    (collation,) = [c for c in graph["collations"] if c["text"] == AGNUS]
    assert collation["selected_text_sha256"] == digest(selected_text(body()))
    assert collation["apparatus_sha256"] == digest(read(f"witnesses/{AGNUS}/apparatus.json"))
    assert collation["apparatus"] == {"entries": 0, "classes": []}
    assert collation["review"] == {"status": "pending"}
    for language in ("pl", "en"):
        bases = [
            u
            for u in read(f"languages/{language}/bibliography.json")["uses"]
            if u.get("address", {}).get("text") == AGNUS
        ]
        assert len(bases) == 3
        assert {u["address"]["segment"] for u in bases} == {"s01", "s02", "s03"}
        assert all(u["role"] == "historical_wording_basis" for u in bases)
        assert all("legacy_refs" not in u for u in bases)
        assert {u["edition"] for u in bases} == {
            "edition.pamiatka-missyi-dla-ludu-katolickiego-1903"
            if language == "pl"
            else "edition.the-missal-for-the-laity-1846"
        }


@pytest.mark.parametrize("mass", MASSES)
def test_actual_assemblies_omit_only_printed_exceptions_and_keep_preparations(mass):
    doc = form(mass)
    before = copy.deepcopy(doc)
    assert assembly_errors(doc, CORPUS) == []
    assert doc["formulary_schema"] == "1.6.0"
    assert doc["ordinary_omissions"] == EXPECTED[mass]
    assert not set(FIXTURE["retained"]) & {d["text"] for d in doc["ordinary_omissions"]}
    agni = [c for c in doc["components"] if c["role"] == "agnus-dei"]
    assert agni == (
        [{"key": "agnus-dei", "role": "agnus-dei", "text": AGNUS, "relation": "shared"}]
        if mass == THURSDAY
        else []
    )
    assert doc == before


@pytest.mark.parametrize("mass", MASSES)
@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "null",
        "empty",
        "wrong-reason",
        "extra-key",
        "segments",
        "duplicate",
        "reorder",
        "pax",
        "haec",
        "fili",
        "perceptio",
        "blessing",
        "last-gospel",
        "schema",
        "identity",
        "observance",
        "collection",
        "season",
        "calendar",
        "component-null",
        "component-extra",
        "component-ordinary",
        "component-reference",
        "component-wrong-position",
    ],
)
def test_closed_descriptors_and_components_reject_malformed_or_counterexample_mass(mass, fault):
    doc = form(mass)
    saved = copy.deepcopy(doc)
    if fault == "missing":
        del doc["ordinary_omissions"]
    elif fault in {"null", "empty"}:
        doc["ordinary_omissions"] = None if fault == "null" else []
    elif fault == "wrong-reason":
        doc["ordinary_omissions"][-1]["reason"] = "requiem-peace-prayer"
    elif fault == "extra-key":
        doc["ordinary_omissions"][-1]["season"] = "paschale"
    elif fault == "segments":
        doc["ordinary_omissions"][-1]["segments"] = ["s01"]
    elif fault == "duplicate":
        doc["ordinary_omissions"].append(copy.deepcopy(doc["ordinary_omissions"][-1]))
    elif fault == "reorder":
        doc["ordinary_omissions"].reverse()
    elif fault in {"pax", "haec", "fili", "perceptio", "blessing", "last-gospel"}:
        doc["ordinary_omissions"].append(
            {
                "text": "ordinarium."
                + {
                    "pax": "pax-domini",
                    "haec": "haec-commixtio",
                    "fili": "fili-dei-vivi",
                    "perceptio": "perceptio-corporis",
                    "blessing": "benedictio",
                    "last-gospel": "evangelium-ultimum",
                }[fault],
                "reason": "triduum-peace-prayer",
            }
        )
    elif fault == "schema":
        doc["formulary_schema"] = "1.5.0"
    elif fault in {"identity", "observance", "collection", "season", "calendar"}:
        key = "id" if fault == "identity" else fault
        doc[key] = {} if fault == "calendar" else "other"
    elif fault == "component-null":
        doc["components"] = None
    else:
        component = {"key": "agnus-dei", "role": "agnus-dei", "text": AGNUS, "relation": "shared"}
        if mass == THURSDAY:
            row = next(c for c in doc["components"] if c["role"] == "agnus-dei")
            if fault == "component-extra":
                row["condition"] = {"season": "paschale"}
            elif fault == "component-ordinary":
                row["text"] = "ordinarium.agnus-dei"
            elif fault == "component-reference":
                row["relation"] = "reference"
            else:
                doc["components"].remove(row)
                doc["components"].insert(0, row)
        else:
            doc["components"].append(component)
    assert doc != saved
    assert assembly_errors(doc, CORPUS)
    doc.clear()
    doc.update(saved)
    assert assembly_errors(doc, CORPUS) == []


@pytest.mark.parametrize(
    "fault",
    [
        "third-peace",
        "requiem",
        "missing",
        "duplicate-id",
        "reordered",
        "punctuation",
        "accent",
        "id-counter",
        "speaker",
        "voice",
        "delivery",
        "performance",
        "degree",
        "rows-null",
        "row-null",
        "words-null",
        "word-null",
    ],
)
def test_actual_agnus_corruptions_fail_then_the_same_object_recovers(fault):
    doc = body()
    saved = copy.deepcopy(doc)
    row = doc["segments"][-1]
    if fault == "third-peace":
        row["words"][-2]["form"] = "dona"
    elif fault == "requiem":
        row["words"][-1]["form"] = "réquiem"
    elif fault == "missing":
        row["words"].pop()
    elif fault == "duplicate-id":
        row["words"][0]["id"] = "w001"
    elif fault == "reordered":
        doc["segments"].reverse()
    elif fault == "punctuation":
        row["words"][-1]["post"] = "!"
    elif fault == "accent":
        row["words"][-2]["form"] = "miserere"
    elif fault == "id-counter":
        doc["ids"]["next"] = 26
    elif fault in {"speaker", "voice"}:
        row[fault] = "schola" if fault == "speaker" else "cantus"
    elif fault == "delivery":
        del row["delivery"]
    elif fault == "performance":
        del row["participation"]["cantu"]["performance"]
    elif fault == "degree":
        row["participation"]["lecta"]["gradus"] = 1
    elif fault == "rows-null":
        doc["segments"] = None
    elif fault == "row-null":
        doc["segments"][-1] = None
    elif fault == "words-null":
        row["words"] = None
    else:
        row["words"][-1] = None
    assert agnus_errors(doc)
    doc.clear()
    doc.update(saved)
    assert agnus_errors(doc) == []
    assert delivery_errors(doc)[0] == []
    assert participation_errors(doc)[0] == []


@pytest.mark.parametrize(
    "target",
    [
        "agnus-dei",
        "qui-dixisti",
        "pax-domini",
        "haec-commixtio",
        "fili-dei-vivi",
        "perceptio-corporis",
    ],
)
def test_whole_omitted_and_retained_targets_are_validated_before_emission(tmp_path, target):
    path = tmp_path / f"texts/ordinarium/{target}.json"
    path.parent.mkdir(parents=True)
    for source in (CORPUS / "texts/ordinarium").glob("*.json"):
        shutil.copyfile(source, path.parent / source.name)
    good = path.read_bytes()
    doc = read(f"texts/ordinarium/{target}.json", tmp_path)
    row = next(s for s in doc["segments"] if s.get("words"))
    row["words"][0]["form"] = "Changed"
    path.write_text(json.dumps(doc))
    for mass in MASSES:
        assert any("Triduum target" in e for e in assembly_errors(form(mass), tmp_path))
    path.write_bytes(good)
    for mass in MASSES:
        assert assembly_errors(form(mass), tmp_path) == []


def test_protocol_projection_and_actual_reader_keep_all_three_word_sets(reader_out):
    manifest = read("manifest.json", reader_out)
    assert manifest["schema_version"] == "6.12.0"
    catalog = read("formularies.json", reader_out)
    assert catalog["schema_version"] == "1.6.0"
    for mass in MASSES:
        row = next(f for f in catalog["formularies"] if f["id"] == mass)
        assert row["ordinary_omissions"] == [
            {**d, "text": d["text"].replace(".", "/", 1)} for d in EXPECTED[mass]
        ]
    compact = read("texts/ordinarium/agnus-dei-in-cena-domini.json", reader_out)
    morphology = read("tables/morphology.json", reader_out)
    # The complete generic round trip also checks every card's stable id.
    assert emit.verify(CORPUS, reader_out) == []
    assert verify_performance(reader_out, manifest) == []
    assert compact["id"] == AGNUS
    assert [r["id"] for r in compact["seg"]] == ["s01", "s02", "s03"]
    assert sum(len(r["w"]) for r in compact["seg"]) == 24
    assert morphology
    assert expand_core(store.core(CORPUS, AGNUS))["id"] == AGNUS


@pytest.mark.parametrize("mass", MASSES)
def test_producer_refuses_a_changed_authored_prescription_before_writing(monkeypatch, mass):
    good = form(mass)
    bad = copy.deepcopy(good)
    bad["ordinary_omissions"][-1]["text"] = "ordinarium.pax-domini"
    monkeypatch.setattr(emit.store, "formularies", lambda corpus: [bad])
    with pytest.raises(ValueError, match="exact Triduum prescriptions"):
        emit.formulary_catalog(CORPUS)
    bad.clear()
    bad.update(good)
    assert emit.formulary_catalog(CORPUS)["formularies"][0]["id"] == mass


@pytest.mark.parametrize("mass", ["dominica-resurrectionis", "dominica-i-passionis"])
def test_unrelated_real_masses_cannot_acquire_the_triduum_prescription(mass):
    doc = form(mass)
    assert assembly_errors(doc, CORPUS) == []
    good = copy.deepcopy(doc)
    doc.setdefault("ordinary_omissions", []).append(copy.deepcopy(EXPECTED[VIGIL][-1]))
    assert assembly_errors(doc, CORPUS)
    doc.clear()
    doc.update(good)
    assert assembly_errors(doc, CORPUS) == []


@pytest.mark.parametrize("fault", ["missing-third", "missing-performance", "priest-singing"])
def test_independent_artifact_guard_rejects_changed_thursday_performance(reader_copy, fault):
    manifest = read("manifest.json", reader_copy)
    path = reader_copy / "texts/ordinarium/agnus-dei-in-cena-domini.json"
    original = path.read_bytes()
    artifact = json.loads(original)
    if fault == "missing-third":
        artifact["seg"].pop()
    elif fault == "missing-performance":
        del artifact["seg"][-1]["participation"]["cantu"]["performance"]
    else:
        artifact["seg"][-1]["delivery"]["cantu"]["voice"] = "cantus"
    try:
        path.write_text(json.dumps(artifact))
        errors = verify_performance(reader_copy, manifest)
        assert any(AGNUS in error for error in errors)
    finally:
        path.write_bytes(original)
    assert verify_performance(reader_copy, manifest) == []


def test_previous_reader_protocol_cannot_claim_the_expanded_prescription_set(reader_out):
    manifest = read("manifest.json", reader_out)
    manifest["schema_version"] = "6.10.0"
    assert verify_performance(reader_out, manifest) == [
        "participation performance requires reader 6.12.0"
    ]


@pytest.mark.parametrize(
    "language,normal,condition",
    [
        (
            "pl",
            "Wieczorna Msza jest zwykle uroczysta lub śpiewana.",
            "Jeśli zezwolono na Mszę czytaną,",
        ),
        ("en", "The evening Mass is normally solemn or sung.", "When a Low Mass is permitted,"),
    ],
)
def test_about_qualifies_low_mass_without_turning_delivery_into_permission(
    language, normal, condition
):
    layer = read(f"languages/{language}/texts/ordinarium/agnus-dei-in-cena-domini.json")
    assert normal in layer["about"]
    assert condition in layer["about"]
    assert not any(
        sentence.lstrip().startswith(("He ", "His ")) for sentence in layer["about"].split(". ")
    )
