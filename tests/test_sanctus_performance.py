"""The single body retains two independently sourced ritual actions."""

import copy
import json
from pathlib import Path

import pytest

from build_reader import bibliography, emit
from build_reader.participation_performance import verify
from checks.participation import check_doc, derive
from checks.participation_performance import publication_errors, source_fields
from checks.translation_provenance import source_payload

CORPUS = Path(__file__).resolve().parent.parent
PERFORMANCE = {"speaker": "schola", "voice": "cantus", "source": "DMS 25 b; 26"}
ROWS = ["s02", "s03", "s04", "s05", "s06"]


def subject():
    return json.loads((CORPUS / "texts/ordinarium/sanctus.json").read_text(encoding="utf-8"))


def test_actual_source_body_has_five_supplements_and_no_new_words():
    doc = subject()
    assert check_doc(doc)[0] == []
    assert [s["id"] for s in doc["segments"]] == ["s01", *ROWS]
    words = [w for s in doc["segments"] for w in s.get("words", [])]
    assert [w["id"] for w in words] == [f"w{i:03}" for i in range(1, 26)]
    for segment in doc["segments"][1:]:
        assert segment["speaker"] == "sacerdos"
        assert segment["voice"] == "clara"
        assert segment["delivery"] == {"cantu": {"voice": "secreto"}}
        assert segment["participation"] == derive(doc, segment)
        assert segment["participation"]["cantu"] == {
            "gradus": 2,
            "source": "DMS 25 b",
            "performance": PERFORMANCE,
        }
        assert segment["participation"]["lecta"] == {"gradus": 3, "source": "DMS 31 c"}


@pytest.mark.parametrize("identity", ROWS)
@pytest.mark.parametrize("mutation", ["drop", "actor", "voice", "source", "extra", "conditional"])
def test_each_canonical_descriptor_is_mandatory_and_closed(identity, mutation):
    doc = subject()
    row = next(s for s in doc["segments"] if s["id"] == identity)
    grant = row["participation"]["cantu"]
    if mutation == "drop":
        del grant["performance"]
    elif mutation == "conditional":
        grant["conditional"] = True
    else:
        key = {"actor": "speaker", "voice": "voice", "source": "source", "extra": "extra"}[mutation]
        grant["performance"][key] = "invalid"
    assert check_doc(doc)[0]


@pytest.mark.parametrize(
    "mutation", ["drop-all", "base", "delivery", "word", "row", "rubric", "lecta"]
)
def test_canonical_boundary_rejects_source_or_role_drift(mutation):
    doc = subject()
    row = doc["segments"][1]
    if mutation == "drop-all":
        for segment in doc["segments"][1:]:
            del segment["participation"]["cantu"]["performance"]
    elif mutation == "base":
        row["speaker"] = "schola"
    elif mutation == "delivery":
        row["delivery"] = {"cantu": {"speaker": "schola", "voice": "cantus"}}
    elif mutation == "word":
        row["words"][0]["id"] = "w999"
    elif mutation == "row":
        doc["segments"].pop()
    elif mutation == "rubric":
        doc["segments"][0]["participation"] = copy.deepcopy(row["participation"])
    else:
        row["participation"]["lecta"]["performance"] = copy.deepcopy(PERFORMANCE)
    assert check_doc(doc)[0]


def test_other_ordinary_and_proper_rules_do_not_gain_the_supplement():
    for name in ["ordinarium/credo", "proprium/dominica-i-adventus-introitus"]:
        doc = json.loads((CORPUS / f"texts/{name}.json").read_text(encoding="utf-8"))
        for segment in doc["segments"]:
            assert all("performance" not in p for p in derive(doc, segment).values())


def test_producer_rejects_wholly_dropped_or_out_of_scope_feature():
    doc = subject()
    assert publication_errors(doc) == []
    for segment in doc["segments"][1:]:
        del segment["participation"]["cantu"]["performance"]
    assert len(publication_errors(doc)) == 10
    other = subject()
    other["id"] = "ordinarium.other"
    assert len(publication_errors(other)) == 5


def test_new_ritual_source_claim_is_bound_but_legacy_payload_is_unchanged():
    from build_reader.bibliography_bindings import selected_text

    doc = subject()
    row = doc["segments"][1]
    before = copy.deepcopy(row)
    del before["participation"]["cantu"]["performance"]
    assert source_fields(before) == {}
    new = source_payload(row)
    old = source_payload(before)
    assert new.pop("participation_performance") == {
        "cantu": {"source": "DMS 25 b", "performance": PERFORMANCE}
    }
    assert new == old
    bound = selected_text(doc)
    assert all("participation_performance" in s for s in bound["segments"][1:])


def test_actual_reader_supplement_and_full_round_trip(reader_out):
    manifest = json.loads((reader_out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "6.8.0"
    assert verify(reader_out, manifest) == []
    assert emit.verify(CORPUS, reader_out) == []


@pytest.mark.parametrize(
    "mutation",
    ["drop-all", "drop-one", "source", "base", "row", "lecta", "wrong-clara", "drop-delivery"],
)
def test_full_artifact_gate_rejects_dropped_or_changed_performance(reader_copy, mutation):
    path = reader_copy / "texts/ordinarium/sanctus.json"
    original = path.read_bytes()
    artifact = json.loads(original)
    manifest = json.loads((reader_copy / "manifest.json").read_text(encoding="utf-8"))
    graph, languages = bibliography.load(CORPUS)
    projection = bibliography.ReaderCitationProjection(CORPUS, graph, languages)
    assert verify(reader_copy, manifest) == []
    assert emit.verify_edition_artifacts(CORPUS, reader_copy, graph, projection) == []
    row = artifact["seg"][1]
    if mutation == "drop-all":
        for segment in artifact["seg"][1:]:
            del segment["participation"]["cantu"]["performance"]
    elif mutation == "drop-one":
        del row["participation"]["cantu"]["performance"]
    elif mutation == "source":
        row["participation"]["cantu"]["performance"]["source"] = "DMS 31 c"
    elif mutation == "base":
        row["speaker"] = "schola"
    elif mutation == "row":
        artifact["seg"].pop()
    elif mutation == "wrong-clara":
        row["delivery"]["cantu"]["voice"] = "clara"
    elif mutation == "drop-delivery":
        del row["delivery"]
    else:
        row["participation"]["lecta"]["performance"] = PERFORMANCE
    assert artifact != json.loads(original)
    expected = (
        "s02: published priestly base changed"
        if mutation in {"base", "wrong-clara", "drop-delivery"}
        else "performance artifact must retain all six Sanctus rows"
        if mutation == "row"
        else "s02: published performance differs or is absent"
    )
    try:
        path.write_text(json.dumps(artifact, ensure_ascii=False), encoding="utf-8")
        assert expected in verify(reader_copy, manifest)
        assert expected in emit.verify_edition_artifacts(CORPUS, reader_copy, graph, projection)
    finally:
        path.write_bytes(original)
    assert verify(reader_copy, manifest) == []
    assert emit.verify_edition_artifacts(CORPUS, reader_copy, graph, projection) == []
