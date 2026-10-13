"""Exact opt-in terminal controls cannot hide text or widen source scope."""

import hashlib
import json
from dataclasses import FrozenInstanceError

import pytest

from build_reader.bibliography_bindings import digest, transcript_digest, witness_subject
from checks import attribute
from checks.raw_binding import REGISTRY, BindingError, RawBindingSnapshot, resolve_binding
from checks.transcription import check_transcriptions
from checks.witness_archive import check as check_archives

REVISION = "4" * 40


def put(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value)
    return path


def fixture(root, monkeypatch, *, line="R. Ámen.~", body="Ámen."):
    raw = "[Test]\n" + line + "\n"
    archive = {
        "upstream": "web/www/missa/Latin/Tempora/Test.txt",
        "revision": REVISION,
        "path": "witnesses/raw/test.txt",
        "sha256": hashlib.sha256(raw.encode()).hexdigest(),
    }
    evidence = {"archive": "test", "first": 2, "last": 2, "section": "Test", "section_line": 1}
    registry = {
        "version": 1,
        "archives": {"test": archive},
        "bindings": {
            "test": {
                "contract": "raw-reading-3",
                "witness": "witnesses/proprium.test/do.txt",
                "revision": REVISION,
                "evidence": [evidence],
                "references": [],
                "reading": [{"archive": "test", "first": 2, "last": 2}],
                "framing": [
                    {
                        "archive": "test",
                        "line": 2,
                        "start": len(line) - 1,
                        "end": len(line),
                        "text": "~",
                        "kind": "terminal-continuation-tilde",
                        "reason": (
                            "Reviewed digital continuation control; retain ordinary punctuation."
                        ),
                    }
                ],
            }
        },
    }
    put(root, archive["path"], raw)
    put(root, REGISTRY, registry)
    witness = put(
        root,
        registry["bindings"]["test"]["witness"],
        "# witness: do\n# revision: " + REVISION + "\n"
        "# path: " + archive["upstream"] + " [Test] (lines 2-2)\n"
        "# raw-binding: test\n" + body + "\n",
    )
    monkeypatch.setattr(attribute, "CORPUS", root)
    return witness, registry


def doc(body="Ámen."):
    return {
        "id": "proprium.test",
        "category": "proprium",
        "segments": [
            {
                "id": "s01",
                "type": "verse",
                "words": [
                    {"id": f"w{i:03}", "form": word} for i, word in enumerate(body.split(), 1)
                ],
            }
        ],
    }


def rejected(root, witness):
    with pytest.raises(BindingError):
        resolve_binding(witness, root)
    errors, checked = check_transcriptions(witness.parent)
    assert errors and checked == 0
    assert check_archives(root)
    assert attribute.marked_lines("proprium.test") == []
    assert not attribute.span_covers(doc())
    assert "speaker" not in attribute.propose(doc()).get("s01", {})


def test_exact_control_keeps_raw_extent_punctuation_and_marker(tmp_path, monkeypatch):
    witness, _ = fixture(tmp_path, monkeypatch)
    bound = resolve_binding(witness, tmp_path)
    assert bound.text == "Ámen." and bound.spans == ()
    fragment = bound.fragments[0]
    assert fragment.raw == "R. Ámen.~" and fragment.text == "Ámen."
    assert (fragment.start, fragment.end, fragment.whole_line) == (0, 9, True)
    assert fragment.marker == "R" and fragment.marker_scope_verified
    assert fragment.framing[0].text == "~" and fragment.framing[0].start == 8
    assert bound.source["resolved_fragments"][0]["raw"] == fragment.raw
    assert bound.source["resolved_fragments"][0]["framing"][0]["text"] == "~"
    assert check_transcriptions(witness.parent) == ([], 1) and check_archives(tmp_path) == []
    assert attribute.marked_lines("proprium.test") == [("minister", attribute.flatten("Ámen."))]
    assert attribute.propose(doc())["s01"]["speaker"] == "minister"
    assert not attribute.span_covers(doc("Ámen. Allelúja."))
    with pytest.raises(BindingError, match="whole-line"):
        attribute.witness_ranges("proprium.test")
    with pytest.raises(FrozenInstanceError):
        fragment.framing[0].text = "."


@pytest.mark.parametrize(
    "field,value",
    [
        ("line", True),
        ("start", False),
        ("end", True),
        ("line", 0),
        ("line", 999),
        ("start", -1),
        ("start", 99),
        ("end", 99),
        ("start", "8"),
        ("end", 9.0),
        ("text", "."),
        ("text", "n"),
        ("text", "~~"),
        ("text", ""),
        ("kind", "punctuation"),
        ("kind", None),
        ("reason", ""),
        ("reason", None),
        ("archive", "unknown"),
        ("start", 7),
        ("end", 8),
    ],
)
def test_declared_control_drift_rejects_all_consumers(tmp_path, monkeypatch, field, value):
    witness, data = fixture(tmp_path, monkeypatch)
    assert resolve_binding(witness, tmp_path)
    data["bindings"]["test"]["framing"][0][field] = value
    put(tmp_path, REGISTRY, data)
    rejected(tmp_path, witness)


@pytest.mark.parametrize(
    "change",
    [
        "missing-framing",
        "empty-framing",
        "duplicate-framing",
        "extra-framing-field",
        "v2-framing",
        "v1-framing",
        "body-tilde",
        "body-letter",
        "body-punctuation",
        "missing-marker",
        "wrong-section",
        "wrong-revision",
        "raw-drift",
        "omitted-reading",
        "duplicate-reading",
        "reference-reading",
        "fragment",
    ],
)
def test_contract_and_evidence_mutations_reject(tmp_path, monkeypatch, change):
    witness, data = fixture(tmp_path, monkeypatch)
    assert resolve_binding(witness, tmp_path)
    binding = data["bindings"]["test"]
    if change == "missing-framing":
        del binding["framing"]
    elif change == "empty-framing":
        binding["framing"] = []
    elif change == "duplicate-framing":
        binding["framing"] *= 2
    elif change == "extra-framing-field":
        binding["framing"][0]["guess"] = True
    elif change == "v2-framing":
        binding["contract"] = "raw-reading-2"
    elif change == "v1-framing":
        del binding["contract"]
    elif change.startswith("body-"):
        replacement = {"body-tilde": "Ámen.~", "body-letter": "Áme.", "body-punctuation": "Ámen"}[
            change
        ]
        witness.write_text(witness.read_text().replace("\nÁmen.\n", "\n" + replacement + "\n"))
    elif change == "missing-marker":
        witness.write_text(witness.read_text().replace("# raw-binding: test\n", ""))
    elif change == "wrong-section":
        binding["evidence"][0]["section"] = "Other"
    elif change == "wrong-revision":
        binding["revision"] = "0" * 40
    elif change == "raw-drift":
        raw = tmp_path / data["archives"]["test"]["path"]
        raw.write_bytes(raw.read_bytes() + b"changed\n")
    elif change == "omitted-reading":
        binding["reading"] = []
    elif change == "duplicate-reading":
        binding["reading"] *= 2
    elif change == "reference-reading":
        binding["references"] = [{"archive": "test", "line": 2, "text": "&Other", "target": 0}]
    else:
        binding["evidence"][0]["fragment"] = {
            "start": 0,
            "end": 8,
            "text": "R. Ámen.",
            "marker": "R",
            "reason": "Unproved strip",
        }
    put(tmp_path, REGISTRY, data)
    rejected(tmp_path, witness)


@pytest.mark.parametrize(
    "line,body",
    [
        ("R. Ámen~", "Ámen"),
        ("R. Ámen.~", "Ámen."),
        ("V. Hébraeórum;~", "Hébraeórum;"),
    ],
)
def test_attached_control_does_not_remove_letters_or_punctuation(tmp_path, monkeypatch, line, body):
    witness, _ = fixture(tmp_path, monkeypatch, line=line, body=body)
    bound = resolve_binding(witness, tmp_path)
    assert bound.text == body and bound.fragments[0].raw == line


@pytest.mark.parametrize(
    "line", ["R. Ámen~ finis", "R. Ámen ~", "R. Ámen~~", "! Rubric~", "$Call~", "[Other]~"]
)
def test_interior_standalone_or_framing_lines_cannot_be_called_text(tmp_path, monkeypatch, line):
    witness, _ = fixture(tmp_path, monkeypatch, line=line)
    rejected(tmp_path, witness)


def test_rationale_and_complete_raw_bytes_change_source_subject(tmp_path, monkeypatch):
    witness, data = fixture(tmp_path, monkeypatch)
    graph = {
        "works": [{"id": "work.divinum-officium"}],
        "editions": [{"id": "edition.test", "work": "work.divinum-officium"}],
        "digital_items": [
            {
                "id": "item.test",
                "edition": "edition.test",
                "kind": "born-digital",
                "revision": REVISION,
            }
        ],
        "uses": [
            {
                "id": "use.test",
                "address": {"kind": "text", "text": "proprium.test"},
                "role": "derived_digital_collation_aid",
                "edition": "edition.test",
                "digital_item": "item.test",
                "evidence_sha256": data["archives"]["test"]["sha256"],
            }
        ],
        "witnesses": [],
        "collations": [],
    }
    record = {
        "id": "witness.test",
        "text": "proprium.test",
        "transcription": "do",
        "coverage": {"kind": "full"},
        "use": "use.test",
        "transcription_sha256": transcript_digest(witness.read_text()),
        "source_dependencies": {"uses": [], "raw_binding": "test"},
        "review": {"status": "pending"},
    }
    graph["witnesses"] = [record]
    first = witness_subject(tmp_path, record, graph, doc())
    assert first["raw_resolution"]["contract"] == "raw-reading-3"
    assert first["raw_resolution"]["resolved_fragments"][0]["framing"][0]["text"] == "~"
    initial_hash = digest(first)
    data["bindings"]["test"]["framing"][0]["reason"] += " Clarified source reason."
    put(tmp_path, REGISTRY, data)
    assert digest(witness_subject(tmp_path, record, graph, doc())) != initial_hash
    raw = tmp_path / data["archives"]["test"]["path"]
    raw.write_bytes(raw.read_bytes() + b"\n# outside selected line\n")
    with pytest.raises(BindingError, match="SHA-256"):
        witness_subject(tmp_path, record, graph, doc())
    data["archives"]["test"]["sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    put(tmp_path, REGISTRY, data)
    graph["uses"][0]["evidence_sha256"] = data["archives"]["test"]["sha256"]
    updated = witness_subject(tmp_path, record, graph, doc())
    assert updated["raw_resolution"]["resolved_fragments"][0]["text"] == "Ámen."
    assert digest(updated) != initial_hash
    updated["raw_resolution"]["binding"]["framing"].clear()
    assert witness_subject(tmp_path, record, graph, doc())["raw_resolution"]["binding"]["framing"]


def test_snapshot_keeps_one_checked_control_plan(tmp_path, monkeypatch):
    witness, data = fixture(tmp_path, monkeypatch)
    snapshot = RawBindingSnapshot(tmp_path)
    first = snapshot.resolve(witness)
    data["bindings"]["test"]["framing"][0]["text"] = "."
    put(tmp_path, REGISTRY, data)
    assert snapshot.resolve(witness) == first
    rejected(tmp_path, witness)


def test_v2_token_boundary_remains_strict(tmp_path, monkeypatch):
    witness, data = fixture(tmp_path, monkeypatch)
    binding = data["bindings"]["test"]
    binding["contract"] = "raw-reading-2"
    del binding["framing"]
    binding["evidence"][0]["fragment"] = {
        "start": 0,
        "end": 8,
        "text": "R. Ámen.",
        "marker": "R",
        "reason": "Attempt to split attached control.",
    }
    binding["reading"][0]["fragment"] = {"start": 0, "end": 8}
    put(tmp_path, REGISTRY, data)
    with pytest.raises(BindingError, match="splits a source token"):
        resolve_binding(witness, tmp_path)


def test_literal_undeclared_tilde_cannot_evade_the_framed_contract(tmp_path, monkeypatch):
    witness, _ = fixture(tmp_path, monkeypatch, line="R. Ámen~ Ámen~", body="Ámen~ Ámen")
    with pytest.raises(BindingError, match="undeclared continuation framing"):
        resolve_binding(witness, tmp_path)


def test_inline_marker_scope_is_not_invented_by_framing(tmp_path, monkeypatch):
    witness, _ = fixture(tmp_path, monkeypatch, line="R. Ámen. S. Ámen~", body="Ámen. S. Ámen")
    with pytest.raises(BindingError, match="ambiguous inline source marker"):
        resolve_binding(witness, tmp_path)
