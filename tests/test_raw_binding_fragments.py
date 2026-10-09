"""Opt-in fragments preserve exact source extent through every consumer."""

import copy
import hashlib
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from build_reader.bibliography_bindings import digest
from checks import attribute
from checks.raw_binding import REGISTRY, BindingError, RawBindingSnapshot, resolve_binding
from checks.transcription import check_transcriptions
from checks.witness_archive import check as check_archives

ROOT = Path(__file__).resolve().parent.parent


def put(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value)
    return path


def fixture(root, monkeypatch, *, line="R. Ámen. Allelúja.", start=3, end=8):
    revision = "4" * 40
    raw = "[Graduale]\n" + line + "\n"
    archive = {
        "upstream": "web/www/missa/Latin/Tempora/Test.txt",
        "revision": revision,
        "path": "witnesses/raw/test.txt",
        "sha256": hashlib.sha256(raw.encode()).hexdigest(),
    }
    marker = line[0] if line[:3] in [x + ". " for x in "SMVROsmvro"] else None
    evidence = {
        "archive": "test",
        "first": 2,
        "last": 2,
        "section": "Graduale",
        "section_line": 1,
        "fragment": {
            "start": start,
            "end": end,
            "text": line[start:end],
            "marker": marker,
            "reason": "Reviewed component ends before adjacent acclamation.",
        },
    }
    body = line[start:end].strip()
    registry = {
        "version": 1,
        "archives": {"test": archive},
        "bindings": {
            "test": {
                "contract": "raw-reading-2",
                "witness": "witnesses/proprium.test/do.txt",
                "revision": revision,
                "evidence": [evidence],
                "references": [],
                "reading": [
                    {
                        "archive": "test",
                        "first": 2,
                        "last": 2,
                        "fragment": {"start": start, "end": end},
                    }
                ],
            }
        },
    }
    header = (
        f"# witness: do\n# revision: {revision}\n"
        f"# path: {archive['upstream']} [Graduale] (line 2, chars {start}:{end})\n"
        "# raw-binding: test\n"
    )
    put(root, archive["path"], raw)
    put(root, REGISTRY, registry)
    witness = put(root, registry["bindings"]["test"]["witness"], header + body + "\n")
    monkeypatch.setattr(attribute, "CORPUS", root)
    return witness, registry


def doc(text="Ámen."):
    return {
        "id": "proprium.test",
        "category": "proprium",
        "segments": [
            {
                "id": "s01",
                "type": "verse",
                "words": [
                    {"id": f"w{i:03}", "form": word} for i, word in enumerate(text.split(), 1)
                ],
            }
        ],
    }


def rejected(root, witness):
    with pytest.raises(BindingError):
        resolve_binding(witness, root)
    errors, count = check_transcriptions(witness.parent)
    assert errors and count == 0
    assert check_archives(root)
    assert attribute.marked_lines("proprium.test") == []
    assert not attribute.span_covers(doc())
    assert "speaker" not in attribute.propose(doc()).get("s01", {})


def test_synthetic_fragment_is_exact_and_marker_survives(tmp_path, monkeypatch):
    witness, data = fixture(tmp_path, monkeypatch)
    result = resolve_binding(witness, tmp_path)
    assert result.text == "Ámen." and result.spans == ()
    assert result.fragments[0].marker == "R" and result.fragments[0].raw == "Ámen."
    assert attribute.span_covers(doc())
    assert attribute.marked_lines("proprium.test") == [("minister", attribute.flatten("Ámen."))]
    assert attribute.propose(doc())["s01"]["speaker"] == "minister"
    assert not attribute.span_covers(doc("Ámen. Allelúja."))
    assert not attribute.span_covers(doc("Allelúja."))
    assert check_transcriptions(witness.parent) == ([], 1)
    assert check_archives(tmp_path) == []
    with pytest.raises(BindingError, match="whole-line"):
        attribute.witness_ranges("proprium.test")
    with pytest.raises(FrozenInstanceError):
        result.fragments[0].text = "Allelúja."
    first = digest(result.source)
    data["bindings"]["test"]["evidence"][0]["fragment"]["reason"] += " Revised rationale."
    put(tmp_path, REGISTRY, data)
    assert digest(resolve_binding(witness, tmp_path).source) != first


@pytest.mark.parametrize(
    "field,value",
    [
        ("start", True),
        ("end", False),
        ("start", -1),
        ("end", 999),
        ("start", 8),
        ("start", "3"),
        ("end", 8.0),
        ("start", None),
        ("end", []),
        ("start", 4),
        ("end", 7),
        ("start", 1),
        ("end", 2),
    ],
)
@pytest.mark.parametrize("layer", ["evidence", "reading"])
def test_coordinates_reject_types_and_split_tokens(tmp_path, monkeypatch, field, value, layer):
    witness, data = fixture(tmp_path, monkeypatch)
    assert resolve_binding(witness, tmp_path)
    data["bindings"]["test"][layer][0]["fragment"][field] = value
    put(tmp_path, REGISTRY, data)
    rejected(tmp_path, witness)


@pytest.mark.parametrize(
    "change",
    [
        "body-accent",
        "body-punctuation",
        "body-extra",
        "body-empty",
        "marker",
        "raw",
        "raw-coherent-hash",
        "assertion",
        "reason",
        "drop",
        "duplicate",
        "overlap",
        "section",
        "cross-section",
        "unknown-contract",
        "remove-opt-in",
        "remove-marker",
        "read-neighbor",
        "extra-field",
        "reference",
        "header",
        "empty-marker-only",
    ],
)
def test_fragment_claim_drift_fails_closed(tmp_path, monkeypatch, change):
    witness, data = fixture(tmp_path, monkeypatch)
    binding = data["bindings"]["test"]
    evidence = binding["evidence"][0]
    assert resolve_binding(witness, tmp_path)
    if change.startswith("body-"):
        replacement = {
            "body-accent": "Amen.",
            "body-punctuation": "Ámen!",
            "body-extra": "Ámen. Allelúja.",
            "body-empty": "",
        }[change]
        witness.write_text(witness.read_text().replace("\nÁmen.\n", "\n" + replacement + "\n"))
    elif change == "marker":
        evidence["fragment"]["marker"] = None
    elif change.startswith("raw"):
        raw = tmp_path / data["archives"]["test"]["path"]
        raw.write_text(raw.read_text().replace("R.", "S."))
        if change == "raw-coherent-hash":
            data["archives"]["test"]["sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    elif change == "assertion":
        evidence["fragment"]["text"] = "Amen."
    elif change == "reason":
        evidence["fragment"]["reason"] = ""
    elif change == "drop":
        binding["reading"] = [{"archive": "test", "first": 2, "last": 2}]
    elif change == "duplicate":
        binding["reading"] *= 2
    elif change == "overlap":
        binding["evidence"] *= 2
    elif change == "section":
        evidence["section"] = "Allelúia"
    elif change == "cross-section":
        evidence["last"] = 3
    elif change == "unknown-contract":
        binding["contract"] = "raw-reading-3"
    elif change == "remove-opt-in":
        del binding["contract"]
    elif change == "remove-marker":
        witness.write_text(witness.read_text().replace("# raw-binding: test\n", ""))
    elif change == "read-neighbor":
        binding["reading"][0]["fragment"] = {"start": 9, "end": 17}
    elif change == "extra-field":
        evidence["fragment"]["guess"] = True
    elif change == "reference":
        binding["references"] = [{"archive": "test", "line": 2, "text": "&Other", "target": 0}]
    elif change == "header":
        witness.write_text(witness.read_text().replace("chars 3:8", "chars 3:17"))
    else:
        for item in [evidence, binding["reading"][0]]:
            item["fragment"].update(start=0, end=2)
        evidence["fragment"]["text"] = "R."
    put(tmp_path, REGISTRY, data)
    rejected(tmp_path, witness)


def test_partial_snapshot_does_not_reopen_mutated_source(tmp_path, monkeypatch):
    witness, data = fixture(tmp_path, monkeypatch)
    snapshot = RawBindingSnapshot(tmp_path)
    result = snapshot.resolve(witness)
    raw = tmp_path / data["archives"]["test"]["path"]
    raw.write_text(raw.read_text().replace("R.", "S."))
    assert snapshot.resolve(witness) == result
    with pytest.raises(BindingError, match="SHA-256"):
        resolve_binding(witness, tmp_path)
    monkeypatch.setattr(attribute, "resolve_binding", lambda *_: result)
    assert attribute.span_covers(doc())
    assert attribute.marked_lines("proprium.test") == [("minister", attribute.flatten("Ámen."))]
    assert attribute.propose(doc())["s01"]["speaker"] == "minister"


def test_inline_markers_are_not_invented_as_fragment_context(tmp_path, monkeypatch):
    witness, _ = fixture(tmp_path, monkeypatch, line="R. Ámen. S. Allelúja.")
    rejected(tmp_path, witness)


def test_midline_component_after_omitted_marked_words_has_no_performer(tmp_path, monkeypatch):
    witness, _ = fixture(tmp_path, monkeypatch, line="R. Ámen. Ámen.", start=9, end=14)
    result = resolve_binding(witness, tmp_path)
    assert result.text == "Ámen." and result.fragments[0].marker == "R"
    assert not result.fragments[0].marker_scope_verified
    assert not attribute.span_covers(doc())
    assert attribute.marked_lines("proprium.test") == []
    assert "speaker" not in attribute.propose(doc()).get("s01", {})


def test_reordering_identical_text_fragments_still_fails(tmp_path, monkeypatch):
    witness, data = fixture(tmp_path, monkeypatch, line="R. Ámen. Ámen.")
    binding = data["bindings"]["test"]
    other = copy.deepcopy(binding["evidence"][0])
    other["fragment"].update(start=9, end=14, text="Ámen.")
    binding["evidence"].append(other)
    binding["reading"].append(
        {"archive": "test", "first": 2, "last": 2, "fragment": {"start": 9, "end": 14}}
    )
    witness.write_text(
        witness.read_text()
        .replace("\nÁmen.\n", "\nÁmen. Ámen.\n")
        .replace(
            "(line 2, chars 3:8)",
            "(line 2, chars 3:8); web/www/missa/Latin/Tempora/Test.txt "
            "[Graduale] (line 2, chars 9:14)",
        )
    )
    put(tmp_path, REGISTRY, data)
    assert resolve_binding(witness, tmp_path)
    binding["reading"].reverse()
    put(tmp_path, REGISTRY, data)
    rejected(tmp_path, witness)


@pytest.mark.parametrize(
    "case,archive_key,pieces,expected_words",
    [
        ("xxiii-gradual", "do-tempora-pent23-0", [(32, None), (33, (0, 71))], 24),
        ("xxiii-alleluia", "do-tempora-pent23-0", [(33, (72, 91)), (35, None)], 13),
        ("xvi-gradual", "do-tempora-pent16-0", [(32, None), (33, (0, 66))], 20),
    ],
)
def test_actual_archived_components_remain_exact(
    tmp_path, monkeypatch, case, archive_key, pieces, expected_words
):
    existing = json.loads((ROOT / REGISTRY).read_text())
    archive = existing["archives"][archive_key]
    raw = (ROOT / archive["path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == archive["sha256"]
    lines = raw.decode().splitlines()
    evidence, reading, declarations, bodies = [], [], [], []
    for number, extent in pieces:
        item = {"archive": archive_key, "first": number, "last": number}
        entry = {**item, "section": "Graduale", "section_line": 30}
        selected = lines[number - 1]
        if extent:
            start, end = extent
            selected = selected[start:end]
            item["fragment"] = {"start": start, "end": end}
            entry["fragment"] = {
                **item["fragment"],
                "text": selected,
                "marker": "V",
                "reason": "Exact chant boundary before/after adjacent Alleluia refrain "
                "on physical line33.",
            }
            locator = f"line {number}, chars {start}:{end}"
        else:
            locator = f"lines {number}-{number}"
        if selected.startswith("V. "):
            selected = selected[3:]
        evidence.append(entry)
        reading.append(item)
        bodies.append(selected)
        declarations.append(f"{archive['upstream']} [Graduale] ({locator})")
    body = " ".join(bodies)
    assert len(body.split()) == expected_words
    binding = {
        "contract": "raw-reading-2",
        "witness": "witnesses/proprium.test/do.txt",
        "revision": archive["revision"],
        "evidence": evidence,
        "references": [],
        "reading": reading,
    }
    put(tmp_path, archive["path"], raw.decode())
    put(
        tmp_path,
        REGISTRY,
        {"version": 1, "archives": {archive_key: archive}, "bindings": {case: binding}},
    )
    witness = put(
        tmp_path,
        binding["witness"],
        f"# witness: do\n# revision: {archive['revision']}\n"
        f"# path: {'; '.join(declarations)}\n# raw-binding: {case}\n{body}\n",
    )
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    result = resolve_binding(witness, tmp_path)
    assert result.text == body
    if case == "xxiii-alleluia":
        assert result.fragments[0].marker == "V"
        assert not result.fragments[0].marker_scope_verified
        assert not attribute.span_covers(doc(body))
        assert attribute.marked_lines("proprium.test") == []
        assert "speaker" not in attribute.propose(doc(body)).get("s01", {})
    else:
        assert attribute.span_covers(doc(body))
    if case.endswith("gradual"):
        assert not attribute.span_covers(doc(body + " Allelúja."))
        assert "allelu" not in " ".join(text for _, text in attribute.marked_lines("proprium.test"))
    if case == "xvi-gradual":
        assert "majestáte" in result.text and "maiestáte" not in result.text
        witness.write_text(witness.read_text().replace("majestáte", "maiestáte"))
        rejected(tmp_path, witness)


def test_partial_mixed_marker_verse_cannot_receive_priest_fallback(tmp_path, monkeypatch):
    witness, data = fixture(tmp_path, monkeypatch)
    raw = tmp_path / data["archives"]["test"]["path"]
    raw.write_text(raw.read_text() + "S. Dóminus.\n")
    data["archives"]["test"]["sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    binding = data["bindings"]["test"]
    binding["evidence"].append(
        {"archive": "test", "first": 3, "last": 3, "section": "Graduale", "section_line": 1}
    )
    binding["reading"].append({"archive": "test", "first": 3, "last": 3})
    witness.write_text(
        witness.read_text()
        .replace(
            "(line 2, chars 3:8)",
            "(line 2, chars 3:8); web/www/missa/Latin/Tempora/Test.txt [Graduale] (lines 3-3)",
        )
        .replace("\nÁmen.\n", "\nÁmen. Dóminus.\n")
    )
    put(tmp_path, REGISTRY, data)
    assert resolve_binding(witness, tmp_path)
    mixed = doc("Ámen. Dóminus.")
    assert not attribute.span_covers(mixed)
    assert "speaker" not in attribute.propose(mixed).get("s01", {})


def test_one_response_spanning_two_selected_fragments_stays_minister(tmp_path, monkeypatch):
    witness, data = fixture(tmp_path, monkeypatch, line="R. Ámen. Ámen.")
    binding = data["bindings"]["test"]
    other = copy.deepcopy(binding["evidence"][0])
    other["fragment"].update(start=9, end=14, text="Ámen.")
    binding["evidence"].append(other)
    binding["reading"].append(
        {"archive": "test", "first": 2, "last": 2, "fragment": {"start": 9, "end": 14}}
    )
    witness.write_text(
        witness.read_text()
        .replace("\nÁmen.\n", "\nÁmen. Ámen.\n")
        .replace(
            "(line 2, chars 3:8)",
            "(line 2, chars 3:8); web/www/missa/Latin/Tempora/Test.txt "
            "[Graduale] (line 2, chars 9:14)",
        )
    )
    put(tmp_path, REGISTRY, data)
    assert resolve_binding(witness, tmp_path)
    assert attribute.span_covers(doc("Ámen. Ámen."))
    assert attribute.propose(doc("Ámen. Ámen."))["s01"]["speaker"] == "minister"
    # An unrelated legacy witness cannot lend a broader or different marker.
    put(
        tmp_path,
        "witnesses/proprium.test/other.txt",
        "# path: web/www/missa/Latin/Tempora/Other.txt (lines 1-1)\nÁmen. Ámen.\n",
    )
    put(tmp_path, "witnesses/raw/do-Other.txt", "S. Ámen. Ámen. Allelúja.\n")
    assert attribute.propose(doc("Ámen. Ámen."))["s01"]["speaker"] == "minister"
    assert not attribute.span_covers(doc("Ámen. Ámen. Allelúja."))


@pytest.mark.parametrize(
    "change", [None, "missing", "wrong-target", "partial-control", "read-control", "omit-formula"]
)
def test_partial_contract_retains_exact_reference_expansion(tmp_path, monkeypatch, change):
    witness, data = fixture(tmp_path, monkeypatch)
    binding = data["bindings"]["test"]
    raw = tmp_path / data["archives"]["test"]["path"]
    raw.write_text(raw.read_text() + "&Formula\n")
    data["archives"]["test"]["sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    formula = "[Formula]\nR. Deo grátias.\n"
    archive = {
        **data["archives"]["test"],
        "path": "witnesses/raw/formula.txt",
        "upstream": "web/www/missa/Latin/Ordo/Prayers.txt",
        "sha256": hashlib.sha256(formula.encode()).hexdigest(),
    }
    data["archives"]["formula"] = archive
    put(tmp_path, archive["path"], formula)
    binding["evidence"] += [
        {"archive": "test", "first": 3, "last": 3, "section": "Graduale", "section_line": 1},
        {"archive": "formula", "first": 2, "last": 2, "section": "Formula", "section_line": 1},
    ]
    binding["references"] = [{"archive": "test", "line": 3, "text": "&Formula", "target": 2}]
    binding["reading"].append({"archive": "formula", "first": 2, "last": 2})
    witness.write_text(
        witness.read_text()
        .replace(
            "(line 2, chars 3:8)",
            "(line 2, chars 3:8); web/www/missa/Latin/Tempora/Test.txt [Graduale] (lines 3-3); "
            "web/www/missa/Latin/Ordo/Prayers.txt [Formula] (lines 2-2)",
        )
        .replace("\nÁmen.\n", "\nÁmen. Deo grátias.\n")
    )
    put(tmp_path, REGISTRY, data)
    assert resolve_binding(witness, tmp_path).text == "Ámen. Deo grátias."
    if change is None:
        return
    if change == "missing":
        binding["references"] = []
    elif change == "wrong-target":
        binding["references"][0]["target"] = 0
    elif change == "partial-control":
        binding["evidence"][1]["fragment"] = {
            "start": 0,
            "end": 8,
            "text": "&Formula",
            "marker": None,
            "reason": "Not sacred text.",
        }
    elif change == "read-control":
        binding["reading"].append({"archive": "test", "first": 3, "last": 3})
    else:
        binding["reading"].pop()
        witness.write_text(witness.read_text().replace("Ámen. Deo grátias.", "Ámen."))
    put(tmp_path, REGISTRY, data)
    rejected(tmp_path, witness)
