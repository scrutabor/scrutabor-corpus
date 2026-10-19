"""Performer writes require every owned source claim and one complete occurrence.

Synthetic local witnesses exercise scope refusal without admitting new sources.
The complete 219-word fixture separately preserves its actual variant alignment.
"""

import copy
import hashlib
import json
import sys

import pytest
import test_attribution_alignment as alignment_fixture
from test_attribution_alignment import KEY, source_checks

from checks import attribute
from checks.attribution_alignment import align_unmarked_reading
from checks.raw_binding import REGISTRY, resolve_binding

reading = alignment_fixture.reading


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n"
        if isinstance(value, dict)
        else value,
        encoding="utf-8",
    )
    return path


def document(*forms):
    return {
        "id": "ordinarium.occurrence-test",
        "category": "ordinarium",
        "segments": [
            {
                "id": "s01",
                "type": "verse",
                "speaker": "minister",
                "voice": "submissa",
                "words": [{"id": f"w{i:03d}", "form": form} for i, form in enumerate(forms, 1)],
            }
        ],
    }


def core(root, doc):
    category, slug = doc["id"].split(".", 1)
    return put(root / "texts" / category / (slug + ".json"), doc)


def snapshot(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def write(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["attribute", "--write"])
    return attribute.main()


def legacy(root, monkeypatch, layout, same_file):
    doc = document("Amen.")
    path = core(root, doc)
    first = put(root / "witnesses/raw/first.txt", "S. Amen.\n")
    if not same_file:
        put(root / "witnesses/raw/second.txt", "M. Amen.\n")
    witness = put(
        root / "witnesses" / doc["id"] / "do.txt",
        "# witness: do\n# path: first.txt (line 1)\nAmen.\n",
    )
    monkeypatch.setattr(attribute, "CORPUS", root)
    good = witness.read_bytes()
    assert resolve_binding(witness, root) is None
    assert attribute.witness_ranges(doc["id"]) == [(first, 1, 1)]
    baseline = attribute.assess(doc)
    assert baseline.scope == "SCOPED" and baseline.write_eligible
    assert baseline.proposals["s01"]["speaker"] == "sacerdos"
    second = ("first.txt" if same_file else "second.txt") + " (lines X)"
    if layout == "headers":
        declaration = "# path: first.txt (line 1)\n# path: " + second
    elif layout == "inline":
        declaration = "# path: first.txt (line 1); " + second
    else:
        assert layout == "wrapped"
        declaration = "# path: first.txt (line 1);\n#   " + second
    put(witness, "# witness: do\n" + declaration + "\nAmen.\n")
    # Positive textual transport does not excuse the second malformed claim.
    assert resolve_binding(witness, root) is None
    assert attribute.witness_ranges(doc["id"]) == [(first, 1, 1)]
    assert attribute.span_covers(doc)
    return doc, path, witness, good


@pytest.mark.parametrize(
    "layout,same_file",
    [
        ("headers", False),
        ("headers", True),
        ("inline", False),
        ("inline", True),
        ("wrapped", False),
        ("wrapped", True),
    ],
    ids=[
        "headers-other-file",
        "headers-same-file",
        "inline-other-file",
        "inline-same-file",
        "wrapped-other-file",
        "wrapped-same-file",
    ],
)
def test_mixed_legacy_claims_are_not_write_eligible(tmp_path, monkeypatch, layout, same_file):
    doc, _, _, _ = legacy(tmp_path, monkeypatch, layout, same_file)
    result = attribute.assess(doc)
    assert not result.write_eligible
    assert result.scope == "INVALID_SCOPE" and result.proposals == {}
    assert result.reasons
    assert "UNPARSED_LOCAL_SOURCE_CLAIM:do.txt" in result.reasons


@pytest.mark.parametrize("same_file", [False, True], ids=["other-file", "same-file"])
def test_mixed_legacy_writer_preserves_authored_bytes(tmp_path, monkeypatch, same_file):
    _, _, _, _ = legacy(tmp_path, monkeypatch, "headers", same_file)
    before = snapshot(tmp_path)
    status = write(monkeypatch)  # Intentionally reached before the refusal assertion.
    assert snapshot(tmp_path) == before
    assert status == 1


def test_single_legacy_source_positive_after_exact_header_restore(tmp_path, monkeypatch):
    doc, path, witness, good = legacy(tmp_path, monkeypatch, "wrapped", True)
    put(witness, good.decode("utf-8"))
    assert resolve_binding(witness, tmp_path) is None
    result = attribute.assess(doc)
    assert result.scope == "SCOPED" and result.write_eligible
    assert result.proposals == {"s01": {"speaker": "sacerdos"}}
    before = snapshot(tmp_path)
    assert write(monkeypatch) == 0
    actual = json.loads(path.read_text(encoding="utf-8"))
    expected = copy.deepcopy(doc)
    expected["segments"][0]["speaker"] = "sacerdos"
    assert actual == expected  # Unproposed voice remains submissa.
    assert {p: b for p, b in snapshot(tmp_path).items() if p != path.relative_to(tmp_path)} == {
        p: b for p, b in before.items() if p != path.relative_to(tmp_path)
    }
    once = snapshot(tmp_path)
    assert write(monkeypatch) == 0
    assert snapshot(tmp_path) == once


def fragment_source(root, monkeypatch, lines, parts):
    doc = document("Dóminus.", "Amen.")
    path = core(root, doc)
    raw = "[Prayer]\n" + "\n".join(lines) + "\n"
    revision = "4" * 40
    upstream = "web/www/missa/Latin/Tempora/Gap.txt"
    archive = {
        "upstream": upstream,
        "revision": revision,
        "path": "witnesses/raw/gap.txt",
        "sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    }
    evidence, selection, declarations = [], [], []
    for number, first, last, marker in parts:
        line = lines[number - 2]
        evidence.append(
            {
                "archive": "gap",
                "first": number,
                "last": number,
                "section": "Prayer",
                "section_line": 1,
                "fragment": {
                    "start": first,
                    "end": last,
                    "text": line[first:last],
                    "marker": marker,
                    "reason": "Synthetic exact fragment, not source approval.",
                },
            }
        )
        selection.append(
            {
                "archive": "gap",
                "first": number,
                "last": number,
                "fragment": {"start": first, "end": last},
            }
        )
        declarations.append(f"{upstream} [Prayer] (line {number}, chars {first}:{last})")
    witness = root / "witnesses" / doc["id"] / "do.txt"
    binding = {
        "contract": "raw-reading-2",
        "witness": witness.relative_to(root).as_posix(),
        "revision": revision,
        "evidence": evidence,
        "references": [],
        "reading": selection,
    }
    put(root / archive["path"], raw)
    put(root / REGISTRY, {"version": 1, "archives": {"gap": archive}, "bindings": {"gap": binding}})
    put(
        witness,
        f"# witness: do\n# revision: {revision}\n# raw-binding: gap\n"
        + "# path: "
        + "; ".join(declarations)
        + "\nDóminus. Amen.\n",
    )
    monkeypatch.setattr(attribute, "CORPUS", root)
    bound = resolve_binding(witness, root)
    assert bound is not None and bound.text == "Dóminus. Amen."
    assert bound.source["contract"] == "raw-reading-2"
    assert [(f.line, f.start, f.end, f.marker) for f in bound.fragments] == parts
    assert all(f.marker_scope_verified for f in bound.fragments)
    assert attribute.span_covers(doc)
    return doc, path, bound


def fragments(root, monkeypatch, gap):
    line = "Dóminus." + gap + "Amen."
    start = line.index("Amen.")
    ranges = [(0, 8), (start, start + 5)]
    doc, path, bound = fragment_source(
        root, monkeypatch, [line], [(2, first, last, None) for first, last in ranges]
    )
    assert [(f.start, f.end) for f in bound.fragments] == ranges
    assert all(f.marker is None and f.marker_scope_verified for f in bound.fragments)
    return doc, path


def test_unmarked_fragment_spoken_gap_is_not_write_eligible(tmp_path, monkeypatch):
    doc, _ = fragments(tmp_path, monkeypatch, " Alienum. ")
    result = attribute.assess(doc)
    assert not result.write_eligible
    assert result.scope == "COMPOSITE_TEXT_ONLY" and result.proposals == {}
    assert result.reasons
    assert "COMPOSITE_RAW_CONTEXT:do.txt" in result.reasons


def test_unmarked_fragment_gap_writer_preserves_authored_bytes(tmp_path, monkeypatch):
    _, _ = fragments(tmp_path, monkeypatch, " Alienum. ")
    before = snapshot(tmp_path)
    status = write(monkeypatch)
    assert snapshot(tmp_path) == before
    assert status == 1


def test_unmarked_whitespace_adjacent_fragments_remain_positive(tmp_path, monkeypatch):
    doc, path = fragments(tmp_path, monkeypatch, " ")
    result = attribute.assess(doc)
    assert result.scope == "SCOPED" and result.write_eligible
    assert result.proposals == {"s01": {"speaker": "sacerdos"}}
    assert write(monkeypatch) == 0
    expected = copy.deepcopy(doc)
    expected["segments"][0]["speaker"] = "sacerdos"
    assert json.loads(path.read_text(encoding="utf-8")) == expected
    once = snapshot(tmp_path)
    assert write(monkeypatch) == 0 and snapshot(tmp_path) == once


@pytest.mark.parametrize(
    "tail,head,marker,eligible",
    [
        (" Alienum.", "", None, False),
        ("", "Alienum. ", None, False),
        (" Alienum.", "Alienum. ", None, False),
        ("", "", None, True),
        (" \t", " \t", None, True),
        (" ", "S. ", "S", True),
    ],
    ids=["spoken-tail", "spoken-head", "spoken-both", "adjacent", "whitespace", "verified-marker"],
)
def test_adjacent_line_fragments_require_complete_intervening_context(
    tmp_path, monkeypatch, tail, head, marker, eligible
):
    lines = ["Dóminus." + tail, head + "Amen."]
    parts = [(2, 0, 8, None), (3, len(head), len(head) + 5, marker)]
    doc, path, bound = fragment_source(tmp_path, monkeypatch, lines, parts)
    assert bound.fragments[0].raw == "Dóminus."
    assert bound.fragments[1].raw == "Amen."
    assert bound.fragments[1].marker_scope_verified
    before = snapshot(tmp_path)
    result = attribute.assess(doc)
    status = write(monkeypatch)
    if not eligible:
        assert result.scope == "COMPOSITE_TEXT_ONLY"
        assert not result.write_eligible and result.proposals == {}
        assert "COMPOSITE_RAW_CONTEXT:do.txt" in result.reasons
        assert status == 1 and snapshot(tmp_path) == before
    else:
        assert result.scope == "SCOPED" and result.write_eligible
        assert result.proposals == {"s01": {"speaker": "sacerdos"}}
        assert status == 0
        expected = copy.deepcopy(doc)
        expected["segments"][0]["speaker"] = "sacerdos"
        assert json.loads(path.read_text(encoding="utf-8")) == expected
        assert {p: b for p, b in snapshot(tmp_path).items() if p != path.relative_to(tmp_path)} == {
            p: b for p, b in before.items() if p != path.relative_to(tmp_path)
        }
        once = snapshot(tmp_path)
        assert write(monkeypatch) == 0 and snapshot(tmp_path) == once


def alignment_conflict(reading):
    root, folder, data = reading
    doc = copy.deepcopy(data["document"])
    assert len(doc["segments"][0]["words"]) == 219
    source_checks(root, folder, doc)
    assert not attribute.span_covers(doc)
    assert attribute.assess(doc).scope == "ALIGNED"
    before = snapshot(root)
    registry = json.loads((root / REGISTRY).read_text(encoding="utf-8"))
    original_registry = (root / REGISTRY).read_bytes()
    original_apparatus = (folder / "apparatus.json").read_bytes()
    body = " ".join(line for line in data["do_witness"].splitlines() if not line.startswith("#"))
    raw = "[Evangelium]\nR. " + body + "\n"
    revision = "5" * 40
    upstream = "web/www/missa/Latin/Sancti/Occurrence-test.txt"
    raw_path = root / "witnesses/raw/occurrence-test.txt"
    other = folder / "other.txt"
    registry["archives"]["occurrence-test"] = {
        "upstream": upstream,
        "revision": revision,
        "path": raw_path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    }
    registry["bindings"]["occurrence-test"] = {
        "witness": other.relative_to(root).as_posix(),
        "revision": revision,
        "evidence": [
            {
                "archive": "occurrence-test",
                "first": 2,
                "last": 2,
                "section": "Evangelium",
                "section_line": 1,
            }
        ],
        "references": [],
        "reading": [{"archive": "occurrence-test", "first": 2, "last": 2}],
    }
    put(raw_path, raw)
    put(
        other,
        f"# witness: other\n# description: Synthetic competing performer fixture only\n"
        f"# revision: {revision}\n# raw-binding: occurrence-test\n"
        f"# path: {upstream} [Evangelium] (lines 2-2)\n{body}\n",
    )
    apparatus = copy.deepcopy(data["apparatus"])
    for entry in apparatus["adjudicated"]:
        if "do" in entry["witnesses"]:
            entry["witnesses"]["other"] = entry["witnesses"]["do"]
    put(folder / "apparatus.json", apparatus)
    put(root / REGISTRY, registry)
    bound = resolve_binding(other, root)
    assert bound is not None and bound.text == body
    assert len(bound.fragments) == 1 and bound.fragments[0].marker == "R"
    assert bound.source["contract"] == "raw-reading-1"
    source_checks(root, folder, doc)  # Genuine selected body and every exact variant still collate.
    assert not attribute.span_covers(doc)
    direct = align_unmarked_reading(doc, root)
    assert direct is not None and direct.witness_id == "do" and len(direct.words) == 219
    assert direct.source_line == 39 and direct.substantive_variants == 2
    assert resolve_binding(folder / "do.txt", root).source["binding_id"] == KEY
    return root, folder, doc, before, original_registry, original_apparatus, other, raw_path


def test_variant_alignment_cannot_hide_other_complete_raw1_owner(reading):
    _, _, doc, *_ = alignment_conflict(reading)
    result = attribute.assess(doc)
    assert not result.write_eligible
    assert result.scope == "STALE_SCOPE" and result.proposals == {}
    assert result.reasons
    assert result.reasons[0].startswith("ALIGNED_OCCURRENCE_REQUIRED:")
    assert "witnesses/raw/occurrence-test.txt:2-2" in result.reasons[0]


def test_variant_alignment_conflict_writer_preserves_authored_bytes(reading, monkeypatch):
    root, folder, doc, *_ = alignment_conflict(reading)
    doc["segments"][0].update(speaker="minister", voice="secreto")
    source_checks(root, folder, doc)
    core(root, doc)
    before = snapshot(root)
    status = write(monkeypatch)
    assert snapshot(root) == before
    assert status == 1


def test_genuine_219_alignment_restores_after_removing_only_counterexample(reading):
    root, folder, doc, before, registry, apparatus, other, raw = alignment_conflict(reading)
    other.unlink()
    raw.unlink()
    (root / REGISTRY).write_bytes(registry)
    (folder / "apparatus.json").write_bytes(apparatus)
    assert snapshot(root) == before
    source_checks(root, folder, doc)
    result = attribute.assess(doc)
    assert result.scope == "ALIGNED" and result.write_eligible
    assert result.alignment is not None and len(result.alignment.words) == 219
    assert result.alignment.substantive_variants == 2
    assert result.proposals == {"s01": {"speaker": "sacerdos", "voice": "clara"}}
