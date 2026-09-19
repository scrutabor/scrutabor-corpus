"""Exact source identity and ordered text must fail together, never downgrade."""

import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from checks import attribute
from checks.raw_binding import BindingError, load_registry, resolve_binding
from checks.transcription import check_transcriptions
from checks.witness_archive import check as check_archives

CORPUS = Path(__file__).resolve().parent.parent
REGISTRY = "witnesses/raw/bindings.json"


@pytest.fixture
def bound_corpus(tmp_path, monkeypatch):
    registry = json.loads((CORPUS / REGISTRY).read_text())
    paths = [REGISTRY]
    paths += [item["path"] for item in registry["archives"].values()]
    paths += [item["witness"] for item in registry["bindings"].values()]
    for name in paths:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CORPUS / name, destination)
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    return tmp_path, registry


def save(root, data):
    (root / REGISTRY).write_text(json.dumps(data), encoding="utf-8")


def witness(root, data, key="rosary-introit"):
    return root / data["bindings"][key]["witness"]


def header_and_body(path):
    lines = path.read_text().splitlines()
    return (
        "\n".join(line for line in lines if line.startswith("#")),
        "\n".join(line for line in lines if not line.startswith("#")),
    )


def rejected(root, path):
    with pytest.raises(BindingError):
        resolve_binding(path, root)
    errors, count = check_transcriptions(path.parent)
    assert errors and count == 0
    assert check_archives(root)
    assert attribute.marked_lines(path.parent.name) == []
    assert not attribute.span_covers({"id": path.parent.name, "segments": []})
    # The attribution writer must never receive the unmarked-celebrant fallback.
    doc = {
        "id": path.parent.name,
        "category": "proprium",
        "segments": [{"id": "s01", "type": "verse", "words": [{"id": "w001", "form": "Alienum"}]}],
    }
    assert "speaker" not in attribute.propose(doc).get("s01", {})


@pytest.mark.parametrize("key", ["rosary-introit", "transfiguration-gradual", "visitation-introit"])
def test_actual_complete_readings_and_attribution(bound_corpus, key):
    root, data = bound_corpus
    path = witness(root, data, key)
    result = resolve_binding(path, root)
    assert result is not None and result.text
    assert check_transcriptions(path.parent) == ([], 1)
    assert attribute.witness_ranges(path.parent.name) == list(result.spans)
    assert attribute.marked_lines(path.parent.name)
    assert check_archives(root) == []


def test_whitespace_only_variation_is_allowed(bound_corpus):
    root, data = bound_corpus
    path = witness(root, data)
    head, body = header_and_body(path)
    path.write_text(head + "\n\n" + body.replace(" ", "  \n "))
    assert resolve_binding(path, root) is not None


@pytest.mark.parametrize(
    "change",
    [
        "remove-marker",
        "duplicate-marker",
        "unknown-marker",
        "revision",
        "range",
        "upstream",
        "remove-path",
        "legacy-range-syntax",
    ],
)
def test_witness_header_drift_is_not_a_legacy_fallback(bound_corpus, change):
    root, data = bound_corpus
    path = witness(root, data)
    text = path.read_text()
    marker = "# raw-binding: rosary-introit\n"
    changes = {
        "remove-marker": text.replace(marker, ""),
        "duplicate-marker": marker + text,
        "unknown-marker": text.replace("raw-binding: rosary-introit", "raw-binding: unknown"),
        "revision": text.replace("# revision: 44667ff", "# revision: 0000000"),
        "range": text.replace("(lines 13-18)", "(lines 14-18)"),
        "upstream": text.replace(
            "web/www/missa/Latin/Sancti/10-07", "web/www/missa/Latin/Sancti/10-08"
        ),
        "remove-path": "\n".join(
            line for line in text.splitlines() if not line.startswith("# path:")
        ),
        "legacy-range-syntax": text.replace("(lines 13-18)", "lines 13–18"),
    }
    path.write_text(changes[change])
    rejected(root, path)


@pytest.mark.parametrize(
    "change",
    [
        "registry-missing",
        "binding-missing",
        "archive-missing",
        "duplicate-key",
        "duplicate-witness",
        "duplicate-archive",
        "wrong-version",
        "boolean-version",
        "extra-field",
    ],
)
def test_registry_identity_failures(bound_corpus, change):
    root, data = bound_corpus
    path = witness(root, data)
    if change == "registry-missing":
        (root / REGISTRY).unlink()
    elif change == "duplicate-key":
        content = (
            (root / REGISTRY).read_text().replace('"version": 1', '"version": 1, "version": 1')
        )
        (root / REGISTRY).write_text(content)
    else:
        if change == "binding-missing":
            del data["bindings"]["rosary-introit"]
        elif change == "archive-missing":
            del data["archives"]["rosary"]
        elif change == "duplicate-witness":
            data["bindings"]["another"] = copy.deepcopy(data["bindings"]["rosary-introit"])
        elif change == "duplicate-archive":
            data["archives"]["another"] = copy.deepcopy(data["archives"]["rosary"])
        elif change == "wrong-version":
            data["version"] = 2
        elif change == "boolean-version":
            data["version"] = True
        else:
            data["bindings"]["rosary-introit"]["unknown"] = 1
        save(root, data)
    rejected(root, path)


def test_deleted_registered_witness_is_an_error(bound_corpus):
    root, data = bound_corpus
    witness(root, data).unlink()
    with pytest.raises(BindingError, match="missing bound witness"):
        load_registry(root)
    assert "missing bound witness" in check_archives(root)[0]


@pytest.mark.parametrize(
    "change",
    [
        "revision",
        "hash",
        "bytes",
        "missing",
        "unknown-upstream",
        "traversal",
        "absolute",
        "symlink",
        "wrong-prayers",
        "wrong-common",
    ],
)
def test_archive_identity_and_confinement(bound_corpus, tmp_path, change):
    root, data = bound_corpus
    path = witness(root, data)
    archive = data["archives"]["rosary"]
    raw = root / archive["path"]
    if change == "revision":
        archive["revision"] = "0" * 40
    elif change == "hash":
        archive["sha256"] = "0" * 64
    elif change == "bytes":
        raw.write_bytes(raw.read_bytes() + b"\n")
    elif change == "missing":
        raw.unlink()
    elif change == "unknown-upstream":
        archive["upstream"] = "web/www/missa/Latin/Sancti/10-08.txt"
    elif change == "traversal":
        archive["path"] = "witnesses/raw/../../outside.txt"
    elif change == "absolute":
        archive["path"] = str(raw)
    elif change == "symlink":
        outside = tmp_path.parent / (tmp_path.name + "-outside.txt")
        outside.write_bytes(raw.read_bytes())
        raw.unlink()
        raw.symlink_to(outside)
    elif change == "wrong-prayers":
        prayers = root / data["archives"]["prayers"]["path"]
        prayers.write_bytes((CORPUS / "witnesses/raw/do-ordo-prayers.txt").read_bytes())
    else:
        common = root / data["archives"]["common-c11"]["path"]
        common.write_bytes((CORPUS / "witnesses/raw/do-C11-tractus-44667ff.txt").read_bytes())
        path = witness(root, data, "visitation-introit")
    save(root, data)
    rejected(root, path)


@pytest.mark.parametrize(
    "change",
    [
        "zero",
        "boolean",
        "reversed",
        "past-end",
        "section",
        "section-line",
        "reference",
        "reference-target",
        "missing-reference",
        "duplicate-reference",
        "reading-outside",
        "reading-framing",
        "unknown-archive",
        "dropped-reading",
        "extra-reading",
        "reordered-reading",
        "extra-alleluia",
    ],
)
def test_evidence_reference_and_reading_mutations(bound_corpus, change):
    root, data = bound_corpus
    key = "rosary-introit"
    binding = data["bindings"][key]
    first = binding["reading"][0]
    if change == "zero":
        first["first"] = 0
    elif change == "boolean":
        first["first"] = True
    elif change == "reversed":
        first["first"] = 15
    elif change == "past-end":
        first["last"] = 999999
    elif change == "section":
        binding["evidence"][0]["section"] = "Oratio"
    elif change == "section-line":
        binding["evidence"][0]["section_line"] = 12
    elif change == "reference":
        binding["references"][0]["text"] = "&Gloria1"
    elif change == "reference-target":
        binding["references"][0]["target"] = 0
    elif change == "missing-reference":
        binding["references"] = []
    elif change == "duplicate-reference":
        binding["references"] *= 2
    elif change == "reading-outside":
        first["first"] = first["last"] = 22
    elif change == "reading-framing":
        first["first"] = first["last"] = 17
    elif change == "unknown-archive":
        first["archive"] = "missing"
    elif change == "dropped-reading":
        binding["reading"].pop()
    elif change == "extra-reading":
        binding["reading"].append(copy.deepcopy(first))
    elif change == "reordered-reading":
        binding["reading"].reverse()
    else:
        key = "transfiguration-gradual"
        data["bindings"][key]["reading"][0]["last"] = 32
    save(root, data)
    rejected(root, witness(root, data, key))


@pytest.mark.parametrize(
    "change", ["accent", "comma", "word", "omitted", "extra", "repeated", "reordered", "empty"]
)
def test_complete_body_not_clause_membership(bound_corpus, change):
    root, data = bound_corpus
    path = witness(root, data)
    header, body = header_and_body(path)
    gloria = "Glória Patri, et Fílio, et Spirítui Sancto."
    if change == "accent":
        body = body.replace("Angeli", "Ángeli")
    elif change == "comma":
        body = body.replace("Angeli et", "Angeli, et")
    elif change == "word":
        body = body.replace("Angeli", "Sancti")
    elif change == "omitted":
        body = body.replace(gloria, "")
    elif change == "extra":
        body += " Allelúja."
    elif change == "repeated":
        body += " " + gloria
    elif change == "reordered":
        body = gloria + " " + body.replace(gloria, "")
    else:
        body = ""
    path.write_text(header + "\n\n" + body)
    rejected(root, path)


def test_nested_raw_files_are_not_witnesses(bound_corpus):
    root, _ = bound_corpus
    nested = root / "witnesses/raw/other/deep/archive.txt"
    nested.parent.mkdir(parents=True)
    nested.write_text("# raw-binding: nonexistent\nNot a witness.\n")
    assert check_archives(root) == []


def test_nested_sources_do_not_retarget_legacy_resolver(bound_corpus):
    root, _ = bound_corpus
    old = root / "witnesses/raw/do-Prayers.txt"
    old.write_text("Old untouched source.\n")
    assert attribute._raw_archive_for("Latin/Ordo/Prayers.txt") == old


def test_no_registry_and_no_marker_remains_legacy(tmp_path):
    path = tmp_path / "witnesses/example/do.txt"
    path.parent.mkdir(parents=True)
    path.write_text("# source: printed page\nAmen.\n")
    assert resolve_binding(path, tmp_path) is None


def test_explicit_sacred_parentheses_survive_attribution_projection(bound_corpus):
    root, data = bound_corpus
    path = witness(root, data)
    record = data["archives"]["rosary"]
    raw = root / record["path"]
    raw.write_text(raw.read_text().replace("Fílium Dei.", "(Fílium Dei.)"))
    record["sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    path.write_text(path.read_text().replace("Fílium Dei.", "(Fílium Dei.)"))
    save(root, data)
    bound = resolve_binding(path, root)
    assert bound is not None and "(Fílium Dei.)" in bound.text
    doc = {
        "id": path.parent.name,
        "segments": [{"type": "verse", "words": [{"id": "w001", "form": "Fílium Dei."}]}],
    }
    assert attribute.span_covers(doc)
    doc["segments"][0]["words"][0]["form"] = "Fílium alienum Dei."
    assert not attribute.span_covers(doc)
    # Punctuation is significant for the witness even when edition alignment folds it.
    path.write_text(path.read_text().replace("(Fílium Dei.)", "Fílium Dei."))
    rejected(root, path)
