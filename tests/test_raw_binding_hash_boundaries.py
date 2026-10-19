"""Exact adjacent spoken context is never selected text or actor evidence."""

import copy
import hashlib
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from build_reader.bibliography_bindings import BindingError as SubjectError
from build_reader.bibliography_bindings import (
    digest,
    transcript_digest,
    validate_bindings,
    witness_subject,
)
from checks import attribute
from checks.attribution_alignment import align_unmarked_reading
from checks.raw_binding import REGISTRY, BindingError, RawBindingSnapshot, resolve_binding
from checks.transcription import check_transcriptions
from checks.witness_archive import check as check_archives

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = "missa-ordo-44667ff"
ARCHIVE_SHA = "a7f63e8030325b809f74dd4587c649bf8eb45cdd150fc9a2817fe2a1ed6a42e3"
REVISION = "44667ff518b8ff1439780470828b39714f5306a2"
TEXT = "ordinarium.iube-domine-benedicere"
KEY = "iube-boundary-test"
MUNDA = "munda-cor-meum-priest"
BODY = (
    "Jube, Dómine, benedícere. Dóminus sit in corde meo et in lábiis meis: "
    "ut digne et competénter annúntiem Evangélium suum. Amen."
)
BODY_SHA = "4bd1a7258a1e9a8382ae9ec709c28ae41cf458ecd4f86059dccbd455c087bd03"
MUNDA_SHA = "fa2f82ddd2524c9d8d20bf29d8c1ab9cc6371d1559129def4f214a41ebb11f54"


def put(root, name, value):
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value,
        encoding="utf-8",
    )
    return target


def document():
    words = BODY.split()
    return {
        "id": TEXT,
        "category": "ordinarium",
        "segments": [
            {
                "id": segment,
                "type": "verse",
                "words": [{"id": f"w{i + 1:03}", "form": words[i]} for i in range(first, last)],
            }
            for segment, first, last in [("s01", 0, 3), ("s02", 3, 19), ("s03", 19, 20)]
        ],
    }


@pytest.fixture
def source(tmp_path, monkeypatch):
    original = json.loads((ROOT / REGISTRY).read_text(encoding="utf-8"))
    archive = copy.deepcopy(original["archives"][ARCHIVE])
    raw = (ROOT / archive["path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == archive["sha256"] == ARCHIVE_SHA
    assert archive["revision"] == REVISION
    lines = raw.decode("utf-8").splitlines()
    assert lines[121] == "v. " + BODY
    assert len(lines[120][3:].split()) == 34
    assert hashlib.sha256((lines[120][3:] + "\n").encode()).hexdigest() == MUNDA_SHA
    evidence = {
        "archive": ARCHIVE,
        "first": 122,
        "last": 122,
        "section": "Evangelium",
        "section_line": 119,
        "heading": {"format": "hash-space", "text": "# Evangelium"},
        "branch": {"line": 118, "text": "!*RnD"},
        "context": [{"line": 120, "text": lines[119]}],
        "preceding_text": {"line": 121, "text": lines[120], "marker": "v"},
    }
    data = {
        "version": 1,
        "archives": {ARCHIVE: archive},
        "bindings": {
            MUNDA: copy.deepcopy(original["bindings"][MUNDA]),
            KEY: {
                "contract": "raw-reading-5",
                "witness": f"witnesses/{TEXT}/do.txt",
                "revision": REVISION,
                "evidence": [evidence],
                "references": [],
                "reading": [{"archive": ARCHIVE, "first": 122, "last": 122}],
            },
        },
    }
    raw_path = put(tmp_path, archive["path"], raw.decode("utf-8"))
    munda = data["bindings"][MUNDA]["witness"]
    put(tmp_path, munda, (ROOT / munda).read_text(encoding="utf-8"))
    witness = put(
        tmp_path,
        data["bindings"][KEY]["witness"],
        f"# witness: do\n# revision: {REVISION}\n# raw-binding: {KEY}\n"
        "# path: web/www/missa/Latin/Ordo/Ordo.txt "
        "{hash-space:Evangelium@119; branch:!*RnD@118; preceding-text:121} "
        "(lines 122-122)\n" + BODY + "\n",
    )
    put(tmp_path, REGISTRY, data)
    put(tmp_path, "texts/ordinarium/iube-domine-benedicere.json", document())
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    files = [raw_path, witness, tmp_path / REGISTRY, tmp_path / munda]
    return {
        "root": tmp_path,
        "data": data,
        "witness": witness,
        "raw": raw_path,
        "lines": lines,
        "originals": {file: file.read_bytes() for file in files},
    }


def save(source):
    put(source["root"], REGISTRY, source["data"])


def assert_positive(source):
    root, witness = source["root"], source["witness"]
    reading = resolve_binding(witness, root)
    assert reading.text == BODY and len(reading.text.split()) == 20
    assert hashlib.sha256((reading.text + "\n").encode()).hexdigest() == BODY_SHA
    assert reading.spans == ((source["raw"], 122, 122),)
    assert len(reading.fragments) == 1
    with pytest.raises(FrozenInstanceError):
        reading.fragments[0].line = 121
    assert source["lines"][105] == source["lines"][120] == source["lines"][131]
    fragment = reading.fragments[0]
    assert (fragment.line, fragment.start, fragment.end) == (122, 0, len("v. " + BODY))
    assert fragment.raw == "v. " + BODY and fragment.text == BODY
    assert fragment.whole_line and fragment.marker == "v" and not fragment.framing
    assert reading.source["contract"] == "raw-reading-5"
    assert reading.fragments[0].marker_scope_verified
    assert [f["line"] for f in reading.source["resolved_fragments"]] == [122]
    munda = resolve_binding(root / source["data"]["bindings"][MUNDA]["witness"], root)
    assert len(munda.text.split()) == 34
    assert hashlib.sha256((munda.text + "\n").encode()).hexdigest() == MUNDA_SHA
    assert munda.spans == ((source["raw"], 121, 121),)
    assert munda.source["contract"] == "raw-reading-4"
    assert "preceding_text" not in munda.source["binding"]["evidence"][0]
    assert check_transcriptions(witness.parent) == ([], 1)
    assert check_archives(root) == []
    return reading


def reject_restore(source, message):
    assert any(file.read_bytes() != raw for file, raw in source["originals"].items())
    with pytest.raises(BindingError, match=message):
        resolve_binding(source["witness"], source["root"])
    errors, count = check_transcriptions(source["witness"].parent)
    assert errors and count == 0
    assert check_archives(source["root"])
    assert attribute.marked_lines(TEXT) == []
    assert not attribute.span_covers(document())
    assert all("speaker" not in row for row in attribute.propose(document()).values())
    for file, raw in source["originals"].items():
        file.write_bytes(raw)
    source["data"] = json.loads((source["root"] / REGISTRY).read_text(encoding="utf-8"))
    assert_positive(source)


def test_actual_twenty_word_reading_keeps_previous_thirty_four_words_separate(source):
    assert_positive(source)
    old = resolve_binding(
        source["root"] / source["data"]["bindings"][MUNDA]["witness"], source["root"]
    )
    expected = {
        "contract": "raw-reading-4",
        "registry_version": 1,
        "binding_id": MUNDA,
        "transcription_sha256": hashlib.sha256(
            (source["root"] / source["data"]["bindings"][MUNDA]["witness"]).read_bytes()
        ).hexdigest(),
        "binding": source["data"]["bindings"][MUNDA],
        "archives": source["data"]["archives"],
        "resolved_fragments": [
            {
                "path": source["data"]["archives"][ARCHIVE]["path"],
                "line": 121,
                "start": 0,
                "end": len(source["lines"][120]),
                "raw": source["lines"][120],
                "text": source["lines"][120][3:],
                "marker": "v",
                "whole_line": True,
                "marker_scope_verified": True,
            }
        ],
    }
    assert old.source == expected
    with pytest.raises(FrozenInstanceError):
        old.fragments[0].line = 122


def test_textual_boundary_does_not_supply_a_priest(source):
    assert_positive(source)
    with pytest.raises(BindingError, match="textual identity only"):
        attribute.witness_ranges(TEXT)
    assert attribute.marked_lines(TEXT) == []
    assert not attribute.span_covers(document())
    assert all("speaker" not in row for row in attribute.propose(document()).values())
    assert align_unmarked_reading(document(), source["root"]) is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("line", True),
        ("line", "121"),
        ("line", 120),
        ("line", 122),
        ("line", 106),
        ("line", 132),
        ("text", ""),
        ("text", None),
        ("text", "!Fabricated rubric."),
        ("marker", "V"),
        ("marker", "S"),
        ("marker", None),
        ("marker", True),
    ],
)
def test_boundary_assertion_is_exact_and_immediately_adjacent(source, field, value):
    assert_positive(source)
    source["data"]["bindings"][KEY]["evidence"][0]["preceding_text"][field] = value
    save(source)
    reject_restore(source, "spoken-text boundary")


@pytest.mark.parametrize("value", [None, [], [{}, {}], {}, {"line": 121, "text": "v. X."}])
def test_boundary_shape_cannot_be_absent_or_incomplete(source, value):
    assert_positive(source)
    source["data"]["bindings"][KEY]["evidence"][0]["preceding_text"] = value
    save(source)
    reject_restore(source, "preceding_text: expected fields")


@pytest.mark.parametrize(
    "change,message",
    [
        ("missing-boundary", "evidence: expected fields"),
        ("extra-boundary-field", "preceding_text: expected fields"),
        ("v4-opt-in", "evidence: expected fields"),
        ("no-opt-in", "evidence: expected fields"),
        ("unknown-contract", "unsupported per-binding contract"),
        ("empty-context", "every intervening rubric"),
        ("duplicate-context", "every intervening rubric"),
        ("wrong-context", "exact rubric"),
        ("wrong-context-line", "exact rubric"),
        ("wrong-heading-occurrence", "every intervening rubric"),
        ("wrong-branch", "adjacent branch"),
        ("requiem-heading", "adjacent branch"),
        ("whole-two-lines", "spoken-text boundary"),
        ("extends-to-dialogue", "spoken-text boundary"),
        ("second-evidence", "one evidence range"),
        ("runtime-reference", "without runtime references"),
        ("fragment", "partial fragment requires raw-reading-2"),
        ("framing", "expected fields"),
        ("read-preceding", "outside textual evidence"),
        ("read-deacon", "outside textual evidence"),
        ("read-requiem", "outside textual evidence"),
        ("duplicate-reading", "omits or repeats"),
        ("empty-reading", "reading must be a nonempty"),
        ("prior-binding", "registered witness identity"),
        ("revision", "revision differs"),
        ("wrong-upstream", "only the Latin Mass Ordo"),
        ("archive-hash", "SHA-256 mismatch"),
    ],
)
def test_contract_drift_rejects_at_intended_source_guard_and_restores(source, change, message):
    assert_positive(source)
    data = source["data"]
    binding = data["bindings"][KEY]
    evidence = binding["evidence"][0]
    if change == "missing-boundary":
        del evidence["preceding_text"]
    elif change == "extra-boundary-field":
        evidence["preceding_text"]["skip"] = True
    elif change == "v4-opt-in":
        binding["contract"] = "raw-reading-4"
    elif change == "no-opt-in":
        del binding["contract"]
    elif change == "unknown-contract":
        binding["contract"] = "raw-reading-99"
    elif change == "empty-context":
        evidence["context"] = []
    elif change == "duplicate-context":
        evidence["context"] *= 2
    elif change == "wrong-context":
        evidence["context"][0]["text"] += " Changed."
    elif change == "wrong-context-line":
        evidence["context"][0]["line"] = True
    elif change == "wrong-heading-occurrence":
        evidence.update(section_line=104, branch={"line": 103, "text": "!*SnD"})
    elif change == "wrong-branch":
        evidence["branch"]["text"] = "!*SnD"
    elif change == "requiem-heading":
        evidence.update(section_line=130, branch={"line": 129, "text": "!*D "})
    elif change == "whole-two-lines":
        evidence["first"] = 121
    elif change == "extends-to-dialogue":
        evidence["last"] = 124
    elif change == "second-evidence":
        binding["evidence"] *= 2
    elif change == "runtime-reference":
        binding["references"] = [{"archive": ARCHIVE, "line": 122, "text": "&Other", "target": 0}]
    elif change == "fragment":
        evidence["fragment"] = {
            "start": 3,
            "end": 10,
            "text": "Jube, D",
            "marker": "v",
            "reason": "Invalid split",
        }
    elif change == "framing":
        binding["framing"] = []
    elif change in {"read-preceding", "read-deacon", "read-requiem"}:
        line = {"read-preceding": 121, "read-deacon": 106, "read-requiem": 132}[change]
        binding["reading"][0].update(first=line, last=line)
    elif change == "duplicate-reading":
        binding["reading"] *= 2
    elif change == "empty-reading":
        binding["reading"] = []
    elif change == "prior-binding":
        source["witness"].write_text(source["witness"].read_text().replace(KEY, MUNDA))
    elif change == "revision":
        binding["revision"] = "0" * 40
    elif change == "wrong-upstream":
        data["archives"][ARCHIVE]["upstream"] = "web/www/horas/Latin/Ordo/Ordo.txt"
    else:
        data["archives"][ARCHIVE]["sha256"] = "0" * 64
    save(source)
    reject_restore(source, message)


@pytest.mark.parametrize("contract", [None, "raw-reading-2", "raw-reading-3"])
def test_partial_or_framed_contract_does_not_invent_a_bracket_heading(source, contract):
    assert_positive(source)
    binding = source["data"]["bindings"][KEY]
    if contract is None:
        del binding["contract"]
    else:
        binding["contract"] = contract
    evidence = binding["evidence"][0]
    source["witness"].write_text(
        source["witness"]
        .read_text()
        .replace(
            "{hash-space:Evangelium@119; branch:!*RnD@118; preceding-text:121}",
            "[Evangelium]",
        )
    )
    for field in ["heading", "branch", "context", "preceding_text"]:
        del evidence[field]
    if contract == "raw-reading-3":
        # Make the tilde framing valid so rejection must be the missing bracket
        # heading, not a malformed-control error unrelated to that assertion.
        lines = list(source["lines"])
        start = len(lines[121])
        lines[121] += "~"
        source["raw"].write_text("\n".join(lines) + "\n", encoding="utf-8")
        source["data"]["archives"][ARCHIVE]["sha256"] = hashlib.sha256(
            source["raw"].read_bytes()
        ).hexdigest()
        binding["framing"] = [
            {
                "archive": ARCHIVE,
                "line": 122,
                "start": start,
                "end": start + 1,
                "text": "~",
                "kind": "terminal-continuation-tilde",
                "reason": "Exact terminal framing does not establish a bracket heading.",
            }
        ]
    save(source)
    reject_restore(source, "section does not match")


@pytest.mark.parametrize("include_preceding", [False, True])
def test_original_v4_never_gains_the_new_boundary_meaning(source, include_preceding):
    assert_positive(source)
    binding = source["data"]["bindings"][KEY]
    binding["contract"] = "raw-reading-4"
    evidence = binding["evidence"][0]
    del evidence["preceding_text"]
    source["witness"].write_text(source["witness"].read_text().replace("; preceding-text:121", ""))
    if include_preceding:
        evidence["first"] = 121
        source["witness"].write_text(source["witness"].read_text().replace("122-122", "121-122"))
        message = "omits or repeats"
    else:
        evidence["context"].append({"line": 121, "text": source["lines"][120]})
        message = "exact rubric"
    save(source)
    reject_restore(source, message)


@pytest.mark.parametrize("line", [120, 121, 122])
@pytest.mark.parametrize(
    "replacement",
    [
        "# Other",
        "[Other]",
        "!*D",
        "&Other",
        "v. ~",
        "v. Ámen. S. Other.",
        "v. ",
        "V. Ámen.",
        "v. &Other",
        "v. $Other",
        "v. @Other",
        "v. !Rubric",
        "v. [Other]",
        "v. #Other",
        "v. _",
        "v. Ámen. D. Other.",
    ],
)
def test_coherently_rehashed_source_cannot_smuggle_an_unsupported_line(source, line, replacement):
    assert_positive(source)
    lines = list(source["lines"])
    lines[line - 1] = replacement
    source["raw"].write_text("\n".join(lines) + "\n", encoding="utf-8")
    source["data"]["archives"][ARCHIVE]["sha256"] = hashlib.sha256(
        source["raw"].read_bytes()
    ).hexdigest()
    if line == 121:
        source["data"]["bindings"][KEY]["evidence"][0]["preceding_text"]["text"] = replacement
    save(source)
    if line == 120:
        message = "exact rubric"
    elif line == 122 and replacement in {"v. Ámen. S. Other.", "v. Ámen. D. Other."}:
        message = "ambiguous inline source marker"
    else:
        message = "spoken-text boundary"
    reject_restore(source, message)


@pytest.mark.parametrize(
    "old,new,message",
    [
        ("# raw-binding: " + KEY + "\n", "", "registered witness identity"),
        (
            "# raw-binding: " + KEY + "\n",
            ("# raw-binding: " + KEY + "\n") * 2,
            "registered witness identity",
        ),
        ("preceding-text:121", "preceding-text:106", "path declarations differ"),
        ("Evangelium@119", "Evangelium@104", "path declarations differ"),
        ("!*RnD@118", "!*SnD@103", "path declarations differ"),
        ("lines 122-122", "lines 121-121", "path declarations differ"),
        ("Dómine", "Domine", "transcription differs"),
        ("Jube,", "Iube,", "transcription differs"),
        ("corde meo et", "corde meo, et", "transcription differs"),
        (BODY, "", "transcription differs"),
        (BODY, BODY + " " + BODY, "transcription differs"),
        (BODY, "Amen. " + BODY, "transcription differs"),
        ("Dómine", "dómine", "transcription differs"),
        ("digne et competénter", "competénter et digne", "transcription differs"),
        ("ut digne", "digne", "transcription differs"),
        ("suum. Amen.", "suum.", "transcription differs"),
    ],
)
def test_complete_transcription_and_header_remain_exact(source, old, new, message):
    assert_positive(source)
    source["witness"].write_text(source["witness"].read_text().replace(old, new), encoding="utf-8")
    reject_restore(source, message)


def graph_for(source):
    record = {
        "id": "witness.test",
        "text": TEXT,
        "transcription": "do",
        "coverage": {"kind": "full"},
        "use": "use.test",
        "transcription_sha256": transcript_digest(source["witness"].read_text()),
        "source_dependencies": {"uses": [], "raw_binding": KEY},
        "review": {"status": "pending"},
    }
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
                "address": {"kind": "text", "text": TEXT},
                "role": "derived_digital_collation_aid",
                "edition": "edition.test",
                "digital_item": "item.test",
                "evidence_sha256": ARCHIVE_SHA,
            }
        ],
        "witnesses": [record],
        "collations": [],
    }
    return record, graph


def test_complete_subject_binds_boundary_without_promoting_review(source):
    assert_positive(source)
    record, graph = graph_for(source)
    first = witness_subject(source["root"], record, graph, document())
    assert first["raw_resolution"]["binding"]["evidence"][0]["preceding_text"]["line"] == 121
    assert first["raw_resolution"]["resolved_fragments"][0]["line"] == 122
    assert record["review"] == {"status": "pending"}
    assert validate_bindings(source["root"], graph) == []
    record["review"] = {"status": "reviewed", "sha256": digest(first)}
    assert validate_bindings(source["root"], graph) == []
    approved_graph = copy.deepcopy(graph)
    lines = list(source["lines"])
    lines[120] += " Additional context."
    source["raw"].write_text("\n".join(lines) + "\n", encoding="utf-8")
    source["data"]["archives"][ARCHIVE]["sha256"] = hashlib.sha256(
        source["raw"].read_bytes()
    ).hexdigest()
    source["data"]["bindings"][KEY]["evidence"][0]["preceding_text"]["text"] = lines[120]
    save(source)
    graph["uses"][0]["evidence_sha256"] = source["data"]["archives"][ARCHIVE]["sha256"]
    updated = witness_subject(source["root"], record, graph, document())
    assert digest(updated) != digest(first)
    assert updated["raw_resolution"]["resolved_fragments"][0]["text"] == BODY
    errors = validate_bindings(source["root"], graph)
    assert len(errors) == 1 and "reviewed subject changed" in errors[0]
    for file, raw in source["originals"].items():
        file.write_bytes(raw)
    source["data"] = json.loads((source["root"] / REGISTRY).read_text())
    graph = approved_graph
    record = graph["witnesses"][0]
    assert witness_subject(source["root"], record, graph, document()) == first
    assert validate_bindings(source["root"], graph) == []
    assert_positive(source)


@pytest.mark.parametrize(
    "change", ["wrong-binding", "munda-reading-hash", "unknown-hash", "wrong-digital-revision"]
)
def test_witness_subject_rejects_mismatched_binding_or_evidence_then_restores(source, change):
    assert_positive(source)
    record, graph = graph_for(source)
    first = witness_subject(source["root"], record, graph, document())
    if change == "wrong-binding":
        record["source_dependencies"]["raw_binding"] = MUNDA
        message = "declared raw binding differs"
    elif change == "wrong-digital-revision":
        graph["digital_items"][0]["revision"] = "0" * 40
        message = "revision or kind differs"
    else:
        graph["uses"][0]["evidence_sha256"] = (
            MUNDA_SHA if change == "munda-reading-hash" else "0" * 64
        )
        message = "neither a bound archive"
    with pytest.raises(SubjectError, match=message):
        witness_subject(source["root"], record, graph, document())
    record, graph = graph_for(source)
    assert witness_subject(source["root"], record, graph, document()) == first


def test_exact_twenty_word_reading_hash_is_an_alternative_to_full_archive_hash(source):
    record, graph = graph_for(source)
    graph["uses"][0]["evidence_sha256"] = BODY_SHA
    subject = witness_subject(source["root"], record, graph, document())
    assert subject["raw_resolution"]["contract"] == "raw-reading-5"


def test_snapshot_and_returned_subject_cannot_mix_boundary_versions(source):
    assert_positive(source)
    snapshot = RawBindingSnapshot(source["root"])
    reading = snapshot.resolve(source["witness"])
    original = copy.deepcopy(reading.source)
    reading.source["binding"]["evidence"][0]["preceding_text"]["text"] = "v. Invented."
    assert snapshot.resolve(source["witness"]).source == original
    source["raw"].write_bytes(source["raw"].read_bytes() + b"\n!Outside selection.\n")
    assert snapshot.resolve(source["witness"]).source == original
    reject_restore(source, "SHA-256 mismatch")


@pytest.mark.parametrize("line", [120, 121])
def test_rehashed_real_context_still_requires_unchanged_literal_assertion(source, line):
    assert_positive(source)
    lines = list(source["lines"])
    lines[line - 1] += " Changed context."
    source["raw"].write_text("\n".join(lines) + "\n", encoding="utf-8")
    source["data"]["archives"][ARCHIVE]["sha256"] = hashlib.sha256(
        source["raw"].read_bytes()
    ).hexdigest()
    save(source)
    reject_restore(source, "exact rubric" if line == 120 else "spoken-text boundary")


def test_previous_prayer_cannot_be_prepended_to_the_twenty_word_transcript(source):
    assert_positive(source)
    source["witness"].write_text(
        source["witness"].read_text().replace(BODY, source["lines"][120][3:] + " " + BODY),
        encoding="utf-8",
    )
    reject_restore(source, "transcription differs")


def test_boundary_requires_a_real_preceding_rubric(source):
    assert_positive(source)
    lines = list(source["lines"])
    lines[118], lines[119] = "!*RnD", "# Evangelium"
    source["raw"].write_text("\n".join(lines) + "\n", encoding="utf-8")
    source["data"]["archives"][ARCHIVE]["sha256"] = hashlib.sha256(
        source["raw"].read_bytes()
    ).hexdigest()
    evidence = source["data"]["bindings"][KEY]["evidence"][0]
    evidence.update(section_line=120, branch={"line": 119, "text": "!*RnD"}, context=[])
    source["witness"].write_text(
        source["witness"]
        .read_text()
        .replace("Evangelium@119", "Evangelium@120")
        .replace("!*RnD@118", "!*RnD@119")
    )
    save(source)
    reject_restore(source, "requires a preceding rubric")


@pytest.mark.parametrize(
    "change,message",
    [
        ("escaping-path", "invalid confined path"),
        ("unknown-archive", "unknown archive"),
        ("duplicate-json", "duplicate JSON key"),
        ("duplicate-witness", "duplicate witness binding"),
        ("archive-bytes", "SHA-256 mismatch"),
        ("version-boolean", "unsupported raw binding version"),
        ("version-unknown", "unsupported raw binding version"),
    ],
)
def test_old_identity_and_archive_guards_remain_effective_for_new_contract(source, change, message):
    assert_positive(source)
    if change == "escaping-path":
        source["data"]["archives"][ARCHIVE]["path"] = "witnesses/raw/../outside.txt"
    elif change == "unknown-archive":
        source["data"]["bindings"][KEY]["evidence"][0]["archive"] = "missing"
    elif change == "duplicate-witness":
        source["data"]["bindings"][KEY]["witness"] = source["data"]["bindings"][MUNDA]["witness"]
    elif change == "archive-bytes":
        source["raw"].write_bytes(source["raw"].read_bytes() + b"\n")
    elif change == "version-boolean":
        source["data"]["version"] = True
    elif change == "version-unknown":
        source["data"]["version"] = 2
    save(source)
    if change == "duplicate-json":
        registry = source["root"] / REGISTRY
        registry.write_text(
            registry.read_text().replace('"version": 1', '"version": 1, "version": 1', 1)
        )
    reject_restore(source, message)


# Exact Benziger 1962 transcription retained as a separate test witness.
# This fixture does not admit it or count mechanical agreement as source approval.
MR_WITNESS = (
    "# witness: mr\n"
    "# description: Missale Romanum, Benziger Brothers, New York, 1962, editio iuxta typicam\n"
    "# source: https://archive.org/details/missale-romanum-1962\n"
    "# location: printed p. 223; IA leaf n302 / one-based PDF p. 303\n"
    "# page-image: https://archive.org/details/missale-romanum-1962/page/n302/mode/1up\n"
    "# path: Ordo Missae, printed p. 223 (IA leaf n302 / one-based PDF p. 303)\n"
    "# transcribed: 2026-10-17 from the retained page image\n"
    "# orthography: exact printed spelling, accents, capitalization and punctuation; "
    "typographic line endings joined\n"
    "# context: the priest without deacon and subdeacon says this request and blessing "
    "after the separate Munda cor meum and before the Gospel greeting\n"
    "# note: rubrics, the preceding Munda and the adjacent deacon blessing are excluded\n"
    "Iube, Dómine, benedícere. Dóminus sit in corde meo, et in lábiis meis: "
    "ut digne et competénter annúntiem Evangélium suum. Amen.\n"
)


def test_alignment_checks_verified_raw5_before_performer_fragments(source, monkeypatch):
    from checks import attribution_alignment as alignment
    from checks.collate import collate

    assert_positive(source)
    original_document = document()
    assert [len(segment["words"]) for segment in original_document["segments"]] == [3, 16, 1]
    one_verse = copy.deepcopy(original_document)
    one_verse["segments"] = [
        {
            "id": "s01",
            "type": "verse",
            "words": [
                copy.deepcopy(word)
                for segment in original_document["segments"]
                for word in segment["words"]
            ],
        }
    ]
    one_verse["source"] = {"apparatus": f"witnesses/{TEXT}/apparatus.json"}
    assert [word["id"] for word in one_verse["segments"][0]["words"]] == [
        f"w{i:03}" for i in range(1, 21)
    ]
    folder = source["witness"].parent
    mr = put(source["root"], f"witnesses/{TEXT}/mr.txt", MR_WITNESS)
    assert mr.read_text(encoding="utf-8") == MR_WITNESS
    put(
        source["root"],
        f"witnesses/{TEXT}/apparatus.json",
        {
            "text": TEXT,
            "adjudicated": [
                {
                    "at": "w001",
                    "ours": "Jube,",
                    "witnesses": {"mr": "Iube,"},
                    "class": "orthography",
                    "ruling": (
                        "This test selects the exact DO spelling and retains the printed Iube."
                    ),
                },
                {
                    "at": "w008",
                    "ours": "meo",
                    "witnesses": {"mr": "meo,"},
                    "class": "punctuation",
                    "ruling": (
                        "This test retains DO without the comma and B with its printed comma."
                    ),
                },
            ],
        },
    )
    errors, warnings, stats = collate(one_verse, folder)
    assert errors == warnings == []
    assert stats["witnesses"] == 2 and stats["words"] == 20
    assert stats["orthographic"] == stats["variants_adjudicated"] == 1
    verified = resolve_binding(source["witness"], source["root"])
    assert verified.source["contract"] == "raw-reading-5"
    assert verified.text == BODY and verified.spans == ((source["raw"], 122, 122),)
    assert verified.source["binding"]["evidence"][0]["preceding_text"]["line"] == 121
    assert resolve_binding(mr, source["root"]) is None
    calls = []

    class ObservedReading:
        def __init__(self, actual):
            self.actual = actual

        def __getattr__(self, name):
            if name == "fragments":
                pytest.fail("raw5 alignment crossed the contract guard into performer fragments")
            return getattr(self.actual, name)

    observed = ObservedReading(verified)
    assert observed.source is verified.source
    assert observed.spans is verified.spans
    assert observed.text == verified.text

    def observe(witness, root):
        actual = resolve_binding(witness, root)
        calls.append((witness.name, actual.source["contract"] if actual else None))
        if actual is None:
            return None
        assert witness == source["witness"] and root == source["root"]
        assert actual == verified
        return ObservedReading(actual)

    monkeypatch.setattr(alignment, "resolve_binding", observe)
    assert alignment.align_unmarked_reading(original_document, source["root"]) is None
    assert calls == []
    assert alignment.align_unmarked_reading(one_verse, source["root"]) is None
    assert calls == [("do.txt", "raw-reading-5"), ("mr.txt", None)]
    for file, raw in source["originals"].items():
        assert file.read_bytes() == raw
    assert document() == original_document
