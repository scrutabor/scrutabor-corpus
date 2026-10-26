"""Require Aufer's real source inventory before testing its pending projection."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from witness_header_fixture import expected_transcript

from build_reader import bibliography
from build_reader.bibliography_bindings import (
    collation_subject,
    digest,
    selected_text,
    transcript_digest,
    witness_subject,
)
from checks import attribute, raw_binding

ROOT = Path(__file__).resolve().parents[1]
TEXT = "ordinarium.aufer-a-nobis"
KEY = "aufer-a-nobis-44667ff-inline"
REVISION = "44667ff518b8ff1439780470828b39714f5306a2"
FOLDER = f"witnesses/{TEXT}"
DO = f"witness.{TEXT}.do44667ff"
EO = f"witness.{TEXT}.handmissal-eo2025"
MR = f"witness.{TEXT}.mr1962"
COLLATION = f"collation.{TEXT}.mr1962-do44667ff-eo2025"
EXPECTED = {
    DO: ("do", f"use.{TEXT}.do44667ff", "derived_comparison"),
    EO: ("handmissal-eo", f"use.{TEXT}.handmissal-eo2025", "derived_comparison"),
    MR: ("mr", f"use.{TEXT}.mr1962", "controlling"),
}
TRANSCRIPTS = {
    "do": "0049e77347fd2d7dc1d5d22b8ec8be3b5ee487a3a2966da957e092ee165406b7",
    "handmissal-eo": "7df1f22711f5439ec72a5e32eebb9592577c4dcc2c566d23c71eb3b5cb754871",
    "mr": "f40ed12a9bb3294b195d85444c87a4bbff87cef6eea42232895bf3f7284efa6f",
}
DOCUMENT = {
    "contract": "paginated-pdf-1",
    "use": EXPECTED[EO][1],
    "digital_item": "item.extraordinaryform.handmissal-chant.2025-12-12.pdf",
    "sha256": "43e21a0356b4ab1641c8dfa3927d8e29b53f3b26f926b23080842d601e07d84d",
    "media_type": "application/pdf",
    "pdf_page": 6,
    "printed": "4",
    "region": "left-half",
    "page_image_sha256": "e554421da2c8241462b4f3d3bf46a64ee1f1a873362ff2623983da81ba3e07fe",
}
SELECTED_SHA = "03c928e81f416b9cd528201c731dcf2434030546d054e79f2d210009c83ccc0b"
APPARATUS_SHA = "9e36e854d694e8bbf1f8c23cfbdf6cc5249d1f828af8254ca83e37d07d463b3a"


def require(condition, diagnostic):
    if not condition:
        raise AssertionError(diagnostic)


def inventory(graph, registry):
    return {
        "witnesses": [w for w in graph["witnesses"] if w["text"] == TEXT],
        "collations": [c for c in graph["collations"] if c["text"] == TEXT],
        "bindings": {
            key: value
            for key, value in registry["bindings"].items()
            if key == KEY or value["witness"].startswith(FOLDER + "/")
        },
    }


def require_inventory(value):
    require(
        sorted(w["id"] for w in value["witnesses"]) == sorted(EXPECTED),
        "inventory:witness-identities",
    )
    require(
        [c["id"] for c in value["collations"]] == [COLLATION],
        "inventory:collation-identity",
    )
    require(set(value["bindings"]) == {KEY}, "inventory:raw-binding-identity")
    witnesses = {w["id"]: w for w in value["witnesses"]}
    for identifier, (name, use, role) in EXPECTED.items():
        word = witnesses[identifier]
        require(
            (word["transcription"], word["use"], word["role"]) == (name, use, role),
            "inventory:transcript-use-role",
        )
        require(word["review"] == {"status": "pending"}, "inventory:pending-witness")
        require(word["coverage"] == {"kind": "full"}, "inventory:full-coverage")
        require(
            word["transcription_sha256"]
            == (
                expected_transcript(f"{FOLDER}/mr.txt", TRANSCRIPTS[name])
                if name == "mr"
                else TRANSCRIPTS[name]
            ),
            "inventory:transcript-hash",
        )
    require(
        witnesses[DO]["source_dependencies"] == {"uses": [], "raw_binding": KEY},
        "inventory:raw-declaration",
    )
    require(
        witnesses[MR]["source_dependencies"] == {"uses": [], "raw_binding": None},
        "inventory:print-declaration",
    )
    require(
        witnesses[EO]["source_dependencies"]
        == {"uses": [], "raw_binding": None, "documents": [DOCUMENT]},
        "inventory:document-declaration",
    )
    binding = value["bindings"][KEY]
    require(
        (binding["witness"], binding["contract"], binding["revision"], binding["archive"])
        == (f"{FOLDER}/do.txt", "raw-reading-7", REVISION, "missa-ordo-44667ff"),
        "inventory:raw-source",
    )
    require(
        binding["reading"] == [{"line": n} for n in (55, 56, 58)],
        "inventory:three-spoken-lines",
    )
    (collation,) = value["collations"]
    require(collation["review"] == {"status": "pending"}, "inventory:pending-collation")
    require(sorted(collation["witnesses"]) == sorted(EXPECTED), "inventory:collation-members")
    require(
        collation["selected_text_sha256"] == SELECTED_SHA
        and collation["apparatus_sha256"] == APPARATUS_SHA
        and collation["apparatus"] == {"entries": 4, "classes": ["punctuation"]},
        "inventory:selected-and-apparatus-references",
    )


@pytest.fixture(scope="module")
def actual():
    graph, languages = bibliography.load(ROOT)
    registry = json.loads((ROOT / raw_binding.REGISTRY).read_text())
    value = inventory(graph, registry)
    require_inventory(value)
    doc = json.loads((ROOT / "texts/ordinarium/aufer-a-nobis.json").read_text())
    apparatus = json.loads((ROOT / FOLDER / "apparatus.json").read_text())
    subjects = {w["id"]: witness_subject(ROOT, w, graph, doc) for w in value["witnesses"]}
    subject = collation_subject(ROOT, value["collations"][0], doc, subjects)
    reading = raw_binding.resolve_binding(ROOT / FOLDER / "do.txt", ROOT)
    packages = {"neutral": bibliography.public_text_evidence(graph)}
    for language in ("pl", "en"):
        packages[language] = bibliography.public_text_evidence(graph, languages[language])
    return {
        "inventory": value,
        "doc": doc,
        "apparatus": apparatus,
        "subjects": subjects,
        "collation": subject,
        "reading": reading,
        "packages": packages,
    }


def test_actual_aufer_inventory_is_present_and_exact(actual):
    require_inventory(actual["inventory"])


def test_actual_aufer_subjects_bind_selected_apparatus_and_transcripts(actual):
    require(set(actual["subjects"]) == set(EXPECTED), "subjects:three-real-witnesses")
    require(
        digest(selected_text(actual["doc"])) == SELECTED_SHA
        and digest(actual["apparatus"]) == APPARATUS_SHA,
        "subjects:current-selected-and-apparatus",
    )
    source_roles = {
        DO: "derived_digital_collation_aid",
        EO: "corroborating_latin_witness",
        MR: "direct_approved_print",
    }
    for identifier, (name, use, _role) in EXPECTED.items():
        subject = actual["subjects"][identifier]
        require(subject["contract"] == "witness-review-2", "subjects:complete-inventory")
        require(subject["selected_text"] == selected_text(actual["doc"]), "subjects:selected")
        require(set(subject["source_uses"]) == {use}, "subjects:exact-source-use")
        require(
            subject["source_uses"][use]["use"]["role"] == source_roles[identifier],
            "subjects:source-use-role",
        )
        text = (ROOT / FOLDER / (name + ".txt")).read_text()
        require(
            transcript_digest(text)
            == (
                expected_transcript(f"{FOLDER}/mr.txt", TRANSCRIPTS[name])
                if name == "mr"
                else TRANSCRIPTS[name]
            ),
            "subjects:current-transcript",
        )
    require(
        actual["subjects"][DO]["raw_resolution"]["binding"] == actual["inventory"]["bindings"][KEY],
        "subjects:registered-raw-binding",
    )
    require(
        actual["subjects"][EO]["document_resolution"]["documents"] == {EXPECTED[EO][1]: DOCUMENT},
        "subjects:registered-document",
    )
    require(
        actual["collation"]["contract"] == "collation-review-2"
        and set(actual["collation"]["witnesses"]) == set(EXPECTED),
        "subjects:complete-collation",
    )


def test_actual_aufer_raw7_has_three_text_pieces_and_no_performer_transport(actual):
    reading = actual["reading"]
    require(reading is not None, "raw:actual-binding-required")
    require(reading.spans == reading.fragments == (), "raw:no-performer-transport")
    require(reading.source["binding_id"] == KEY, "raw:actual-binding-identity")
    require(reading.source["contract"] == "raw-reading-7", "raw:exact-contract")
    pieces = reading.source["resolved_extraction"]["pieces"]
    require([p["line"] for p in pieces] == [55, 56, 58], "raw:three-textual-pieces")
    require([len(p["text"].split()) for p in pieces] == [1, 20, 21], "raw:piece-word-counts")
    require(
        " ".join(" ".join(p["text"] for p in pieces).split()) == reading.text
        and len(reading.text.split()) == 42,
        "raw:complete-ordered42",
    )


def test_actual_aufer_actor_entrypoints_reject_text_only_inventory(actual, monkeypatch):
    require_inventory(actual["inventory"])
    monkeypatch.setattr(attribute, "CORPUS", ROOT)
    message = "inline-rubric evidence supports textual identity only"
    for entrypoint in (attribute._source_ranges, attribute.witness_ranges):
        with pytest.raises(raw_binding.BindingError, match=f"^{message}$") as error:
            entrypoint(TEXT)
        require(str(error.value) == message, "actor:exact-text-only-diagnostic")
    actor = attribute._actor_sources(TEXT)
    require(actor.scope == "RAW_TEXT_ONLY" and actor.units == (), "actor:closed-text-only-scope")


@pytest.mark.parametrize("package", ["neutral", "pl", "en"])
def test_actual_aufer_pending_evidence_stays_withheld(actual, package):
    require_inventory(actual["inventory"])
    rows = [r for r in actual["packages"][package]["texts"] if r["id"] == TEXT]
    require(len(rows) == 1, "projection:actual-text-required")
    require(rows[0]["witnesses"] == [] and "collation" not in rows[0], "projection:pending")
    if package == "neutral":
        uses = {e["id"] for group in rows[0]["source_groups"] for e in group["entries"]}
        require({row[1] for row in EXPECTED.values()} <= uses, "projection:retained-source-uses")


MUTANTS = [
    ("delete-witness", "inventory:witness-identities"),
    ("delete-collation", "inventory:collation-identity"),
    ("delete-raw7", "inventory:raw-binding-identity"),
    ("foreign-witness-same-count", "inventory:witness-identities"),
    ("foreign-collation-same-count", "inventory:collation-identity"),
    ("foreign-raw7-same-count", "inventory:raw-binding-identity"),
    ("lost-raw-dependency", "inventory:raw-declaration"),
    ("foreign-raw-dependency", "inventory:raw-declaration"),
    ("lost-document-dependency", "inventory:document-declaration"),
    ("foreign-document-dependency", "inventory:document-declaration"),
    ("empty-all", "inventory:witness-identities"),
]


@pytest.mark.parametrize("defect,diagnostic", MUTANTS, ids=[row[0] for row in MUTANTS])
def test_inventory_presence_and_dependency_mutants_reject_and_restore(actual, defect, diagnostic):
    original = deepcopy(actual["inventory"])
    broken = deepcopy(original)
    require_inventory(original)
    if defect == "delete-witness":
        broken["witnesses"] = [w for w in broken["witnesses"] if w["id"] != DO]
    elif defect == "delete-collation":
        broken["collations"].clear()
    elif defect == "delete-raw7":
        broken["bindings"].clear()
    elif defect == "foreign-witness-same-count":
        next(w for w in broken["witnesses"] if w["id"] == DO)["id"] += ".foreign"
    elif defect == "foreign-collation-same-count":
        broken["collations"][0]["id"] += ".foreign"
    elif defect == "foreign-raw7-same-count":
        broken["bindings"][KEY + "-foreign"] = broken["bindings"].pop(KEY)
    elif defect in {"lost-raw-dependency", "foreign-raw-dependency"}:
        row = next(w for w in broken["witnesses"] if w["id"] == DO)
        row["source_dependencies"]["raw_binding"] = (
            None if defect == "lost-raw-dependency" else KEY + "-foreign"
        )
    elif defect in {"lost-document-dependency", "foreign-document-dependency"}:
        row = next(w for w in broken["witnesses"] if w["id"] == EO)
        if defect == "lost-document-dependency":
            row["source_dependencies"].pop("documents")
        else:
            row["source_dependencies"]["documents"][0]["use"] += ".foreign"
    elif defect == "empty-all":
        broken = {"witnesses": [], "collations": [], "bindings": {}}
    else:
        raise AssertionError(defect)
    require(broken != original, "control:nonvacuous-mutation")
    with pytest.raises(AssertionError, match=f"^{diagnostic}$") as error:
        require_inventory(broken)
    require(str(error.value) == diagnostic, "control:owned-diagnostic")
    broken = deepcopy(original)
    require_inventory(broken)
    require(actual["inventory"] == original == broken, "control:restored-actual-inventory")
