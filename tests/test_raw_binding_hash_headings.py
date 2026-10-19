"""An explicit hash-heading contract proves exact text, never a performer."""

import copy
import hashlib
import json

import pytest

from build_reader.bibliography_bindings import digest, transcript_digest, witness_subject
from checks import attribute
from checks.attribution_alignment import align_unmarked_reading
from checks.raw_binding import REGISTRY, BindingError, RawBindingSnapshot, resolve_binding
from checks.transcription import check_transcriptions
from checks.witness_archive import check as check_archives

REVISION = "4" * 40
UPSTREAM = "web/www/missa/Latin/Ordo/Ordo.txt"
PATH_HEADER = UPSTREAM + " {hash-space:Evangelium@119; branch:!*RnD@118} (lines 121-122)"


def put(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value,
        encoding="utf-8",
    )
    return path


def doc():
    return {
        "id": "proprium.test",
        "category": "proprium",
        "segments": [
            {
                "id": "s01",
                "type": "verse",
                "words": [
                    {"id": "w001", "form": "Ámen", "post": "."},
                    {"id": "w002", "form": "Allelúja", "post": "."},
                ],
            }
        ],
    }


def fixture(root, monkeypatch):
    lines = [""] * 133
    for heading, branch in [(104, "!*SnD"), (119, "!*RnD"), (130, "!*D")]:
        lines[heading - 2] = branch
        lines[heading - 1] = "# Evangelium"
        lines[heading] = "!Exact branch rubric."
        lines[heading + 1] = "v. Ámen."
    lines[121] = "R. Allelúja."
    raw = "\n".join(lines) + "\n"
    archive = {
        "upstream": UPSTREAM,
        "revision": REVISION,
        "path": "witnesses/raw/source/Ordo.txt",
        "sha256": hashlib.sha256(raw.encode()).hexdigest(),
    }
    evidence = {
        "archive": "test",
        "first": 121,
        "last": 122,
        "section": "Evangelium",
        "section_line": 119,
        "heading": {"format": "hash-space", "text": "# Evangelium"},
        "branch": {"line": 118, "text": "!*RnD"},
        "context": [{"line": 120, "text": "!Exact branch rubric."}],
    }
    data = {
        "version": 1,
        "archives": {"test": archive},
        "bindings": {
            "test": {
                "contract": "raw-reading-4",
                "witness": "witnesses/proprium.test/do.txt",
                "revision": REVISION,
                "evidence": [evidence],
                "references": [],
                "reading": [{"archive": "test", "first": 121, "last": 122}],
            }
        },
    }
    put(root, archive["path"], raw)
    put(root, REGISTRY, data)
    witness = put(
        root,
        data["bindings"]["test"]["witness"],
        "# witness: do\n# revision: " + REVISION + "\n# raw-binding: test\n"
        "# path: " + PATH_HEADER + "\nÁmen. Allelúja.\n",
    )
    monkeypatch.setattr(attribute, "CORPUS", root)
    return witness, data


def rejected(root, witness):
    with pytest.raises(BindingError):
        resolve_binding(witness, root)
    errors, count = check_transcriptions(witness.parent)
    assert errors and count == 0
    assert check_archives(root)
    assert attribute.marked_lines("proprium.test") == []
    assert not attribute.span_covers(doc())
    assert "speaker" not in attribute.propose(doc()).get("s01", {})


def test_hash_heading_is_exact_whole_line_text_only(tmp_path, monkeypatch):
    witness, data = fixture(tmp_path, monkeypatch)
    bound = resolve_binding(witness, tmp_path)
    assert bound.text == "Ámen. Allelúja."
    assert bound.spans == ((tmp_path / data["archives"]["test"]["path"], 121, 122),)
    assert [fragment.marker for fragment in bound.fragments] == ["v", "R"]
    assert all(fragment.whole_line and not fragment.framing for fragment in bound.fragments)
    assert bound.source["contract"] == "raw-reading-4"
    assert [fragment["raw"] for fragment in bound.source["resolved_fragments"]] == [
        "v. Ámen.",
        "R. Allelúja.",
    ]
    assert check_transcriptions(witness.parent) == ([], 1)
    assert check_archives(tmp_path) == []
    # Even a real R. in a supported textual binding does not opt into new actor semantics.
    assert attribute.marked_lines("proprium.test") == []
    assert not attribute.span_covers(doc())
    assert "speaker" not in attribute.propose(doc()).get("s01", {})
    with pytest.raises(BindingError, match="textual identity only"):
        attribute.witness_ranges("proprium.test")
    assert align_unmarked_reading(doc(), tmp_path) is None


@pytest.mark.parametrize(
    "change",
    [
        "wrong-occurrence",
        "wrong-heading",
        "wrong-format",
        "wrong-branch-line",
        "wrong-branch-text",
        "boolean-section",
        "boolean-branch",
        "boolean-context",
        "missing-context",
        "changed-context",
        "extra-context",
        "wrong-upstream",
        "hash-crossing",
        "bracket-crossing",
        "branch-crossing",
        "rubric-in-text",
        "reference-in-text",
        "tilde",
        "wrong-line",
        "reorder",
        "duplicate",
        "omit",
        "extra-evidence",
        "runtime-reference",
        "fragment",
        "framing",
        "revision",
        "archive-drift",
        "missing-marker",
        "path",
        "case",
        "punctuation",
        "missing-opt-in",
        "v2-opt-in",
        "unknown-contract",
    ],
)
def test_mutations_fail_closed_in_all_consumers(tmp_path, monkeypatch, change):
    witness, data = fixture(tmp_path, monkeypatch)
    assert resolve_binding(witness, tmp_path)
    binding = data["bindings"]["test"]
    evidence = binding["evidence"][0]
    raw = tmp_path / data["archives"]["test"]["path"]
    if change == "wrong-occurrence":
        evidence.update(section_line=104, branch={"line": 103, "text": "!*SnD"})
    elif change == "wrong-heading":
        evidence["heading"]["text"] = "# evangelium"
    elif change == "wrong-format":
        evidence["heading"]["format"] = "arbitrary"
    elif change == "wrong-branch-line":
        evidence["branch"]["line"] = 103
    elif change == "wrong-branch-text":
        evidence["branch"]["text"] = "!*SnD"
    elif change == "boolean-section":
        evidence["section_line"] = True
    elif change == "boolean-branch":
        evidence["branch"]["line"] = True
    elif change == "boolean-context":
        evidence["context"][0]["line"] = True
    elif change == "missing-context":
        evidence["context"] = []
    elif change == "changed-context":
        evidence["context"][0]["text"] += " Changed."
    elif change == "extra-context":
        evidence["context"] *= 2
    elif change == "wrong-upstream":
        data["archives"]["test"]["upstream"] = "web/www/horas/Latin/Ordo/Ordo.txt"
    elif change in {
        "hash-crossing",
        "bracket-crossing",
        "branch-crossing",
        "rubric-in-text",
        "reference-in-text",
        "tilde",
    }:
        lines = raw.read_text().splitlines()
        lines[121] = {
            "hash-crossing": "# Other",
            "bracket-crossing": "[Other]",
            "branch-crossing": "!*D",
            "rubric-in-text": "!Other rubric.",
            "reference-in-text": "&Other",
            "tilde": "R. Allelúja.~",
        }[change]
        raw.write_text("\n".join(lines) + "\n")
        data["archives"]["test"]["sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    elif change == "wrong-line":
        binding["reading"][0].update(first=106, last=106)
    elif change == "reorder":
        binding["reading"] = [
            {"archive": "test", "first": 122, "last": 122},
            {"archive": "test", "first": 121, "last": 121},
        ]
    elif change == "duplicate":
        binding["reading"] *= 2
    elif change == "omit":
        binding["reading"][0]["last"] = 121
    elif change == "extra-evidence":
        binding["evidence"] *= 2
    elif change == "runtime-reference":
        binding["references"] = [{"archive": "test", "line": 121, "text": "&Other", "target": 0}]
    elif change == "fragment":
        evidence["fragment"] = {
            "start": 3,
            "end": 8,
            "text": "Ámen.",
            "marker": "v",
            "reason": "Not whole-line.",
        }
    elif change == "framing":
        binding["framing"] = []
    elif change == "revision":
        binding["revision"] = "0" * 40
    elif change == "archive-drift":
        raw.write_bytes(raw.read_bytes() + b"changed\n")
    elif change == "missing-marker":
        witness.write_text(witness.read_text().replace("# raw-binding: test\n", ""))
    elif change == "path":
        witness.write_text(witness.read_text().replace("Evangelium@119", "Evangelium@104"))
    elif change in {"case", "punctuation"}:
        witness.write_text(
            witness.read_text().replace("\nÁmen.", "\námen." if change == "case" else "\nÁmen,")
        )
    elif change == "missing-opt-in":
        del binding["contract"]
    elif change == "v2-opt-in":
        binding["contract"] = "raw-reading-2"
    else:
        binding["contract"] = "raw-reading-99"
    put(tmp_path, REGISTRY, data)
    rejected(tmp_path, witness)


def test_altered_rubric_is_not_excused_by_an_updated_archive_hash(tmp_path, monkeypatch):
    witness, data = fixture(tmp_path, monkeypatch)
    raw = tmp_path / data["archives"]["test"]["path"]
    raw.write_text(raw.read_text().replace("!Exact branch rubric.", "!Altered branch rubric."))
    data["archives"]["test"]["sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    put(tmp_path, REGISTRY, data)
    rejected(tmp_path, witness)


def test_complete_new_source_plan_changes_subject_and_stays_snapshot_bound(tmp_path, monkeypatch):
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
    assert first["raw_resolution"]["binding"]["evidence"][0]["context"] == [
        {"line": 120, "text": "!Exact branch rubric."}
    ]
    snap = RawBindingSnapshot(tmp_path)
    original = copy.deepcopy(snap.resolve(witness).source)
    raw = tmp_path / data["archives"]["test"]["path"]
    raw.write_bytes(raw.read_bytes() + b"\n!Outside selection.\n")
    assert snap.resolve(witness).source == original
    with pytest.raises(BindingError, match="SHA-256"):
        witness_subject(tmp_path, record, graph, doc())
    data["archives"]["test"]["sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    graph["uses"][0]["evidence_sha256"] = data["archives"]["test"]["sha256"]
    put(tmp_path, REGISTRY, data)
    assert digest(witness_subject(tmp_path, record, graph, doc())) != digest(first)
    changed = snap.resolve(witness)
    changed.source["binding"]["evidence"][0]["context"].clear()
    assert snap.resolve(witness).source == original


@pytest.mark.parametrize("version", [1, 2, 3])
def test_legacy_contract_subjects_and_attribution_are_not_given_new_fields(
    tmp_path, monkeypatch, version
):
    # Exact baseline payload, not merely an equal body string.
    line = "R. Ámen.~" if version == 3 else "R. Ámen."
    raw = "[Test]\n" + line + "\n"
    archive = {
        "upstream": "web/www/missa/Latin/Tempora/Test.txt",
        "revision": REVISION,
        "path": "witnesses/raw/test.txt",
        "sha256": hashlib.sha256(raw.encode()).hexdigest(),
    }
    binding = {
        "witness": "witnesses/proprium.test/do.txt",
        "revision": REVISION,
        "evidence": [
            {"archive": "test", "first": 2, "last": 2, "section": "Test", "section_line": 1}
        ],
        "references": [],
        "reading": [{"archive": "test", "first": 2, "last": 2}],
    }
    framing = {
        "archive": "test",
        "line": 2,
        "start": len(line) - 1,
        "end": len(line),
        "text": "~",
        "kind": "terminal-continuation-tilde",
        "reason": "Exact control.",
    }
    if version > 1:
        binding["contract"] = f"raw-reading-{version}"
    if version == 3:
        binding["framing"] = [framing]
    data = {"version": 1, "archives": {"test": archive}, "bindings": {"test": binding}}
    put(tmp_path, archive["path"], raw)
    put(tmp_path, REGISTRY, data)
    witness = put(
        tmp_path,
        binding["witness"],
        "# witness: do\n# revision: "
        + REVISION
        + "\n# raw-binding: test\n# path: "
        + archive["upstream"]
        + " [Test] (lines 2-2)\nÁmen.\n",
    )
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    bound = resolve_binding(witness, tmp_path)
    expected = {
        "contract": f"raw-reading-{version}",
        "registry_version": 1,
        "binding_id": "test",
        "transcription_sha256": transcript_digest(witness.read_text()),
        "binding": binding,
        "archives": {"test": archive},
    }
    if version > 1:
        fragment = {
            "path": archive["path"],
            "line": 2,
            "start": 0,
            "end": len(line),
            "raw": line,
            "text": "Ámen.",
            "marker": "R",
            "whole_line": True,
            "marker_scope_verified": True,
        }
        if version == 3:
            fragment["framing"] = [
                {k: framing[k] for k in ["start", "end", "text", "kind", "reason"]}
            ]
        expected["resolved_fragments"] = [fragment]
    assert bound.source == expected
    assert attribute.marked_lines("proprium.test") == [("minister", attribute.flatten("Ámen."))]
    assert "heading" not in data["bindings"]["test"]["evidence"][0]


def test_source_specific_unmarked_alignment_does_not_accept_new_contract(tmp_path, monkeypatch):
    witness, data = fixture(tmp_path, monkeypatch)
    binding = data["bindings"]["test"]
    binding["evidence"][0]["last"] = binding["reading"][0]["last"] = 121
    raw = tmp_path / data["archives"]["test"]["path"]
    lines = raw.read_text().splitlines()
    lines[120] = "Ámen. Allelúja."
    raw.write_text("\n".join(lines) + "\n")
    data["archives"]["test"]["sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    put(tmp_path, REGISTRY, data)
    witness.write_text(witness.read_text().replace("lines 121-122", "lines 121-121"))
    put(tmp_path, "witnesses/proprium.test/mr.txt", "# witness: mr\nÁmen. Allelúja.\n")
    put(
        tmp_path,
        "witnesses/proprium.test/apparatus.json",
        {"text": "proprium.test", "adjudicated": []},
    )
    document = doc()
    document["source"] = {"apparatus": "witnesses/proprium.test/apparatus.json"}
    assert resolve_binding(witness, tmp_path)
    assert align_unmarked_reading(document, tmp_path) is None
    # The same exact unmarked reading is eligible under the unchanged v1 contract.
    del binding["contract"]
    for key in ["heading", "branch", "context"]:
        del binding["evidence"][0][key]
    lines[118] = "[Evangelium]"
    raw.write_text("\n".join(lines) + "\n")
    data["archives"]["test"]["sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    put(tmp_path, REGISTRY, data)
    witness.write_text(
        witness.read_text().replace("{hash-space:Evangelium@119; branch:!*RnD@118}", "[Evangelium]")
    )
    assert resolve_binding(witness, tmp_path)
    assert align_unmarked_reading(document, tmp_path) is not None
