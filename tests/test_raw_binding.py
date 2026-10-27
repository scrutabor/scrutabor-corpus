"""Exact source identity and ordered text must fail together, never downgrade."""

import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from checks import attribute
from checks.raw_binding import BindingError, RawBindingSnapshot, load_registry, resolve_binding
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


def test_returned_raw_closure_cannot_mutate_a_validation_snapshot(bound_corpus):
    root, data = bound_corpus
    snapshot = RawBindingSnapshot(root)
    path = witness(root, data, "pentecost-vi-collect")
    first = snapshot.resolve(path)
    assert first is not None
    original = copy.deepcopy(first.source)
    assert set(original["archives"]) == {"pentecost-vi", "prayers"}
    assert original["binding"] == data["bindings"]["pentecost-vi-collect"]
    first.source["binding"]["reading"].clear()
    first.source["archives"]["prayers"]["sha256"] = "0" * 64
    again = snapshot.resolve(path)
    assert again is not None and again.source == original


def test_snapshot_is_per_run_not_a_process_global_file_cache(bound_corpus):
    root, data = bound_corpus
    path = witness(root, data)
    snapshot = RawBindingSnapshot(root)
    original = snapshot.resolve(path)
    assert original is not None
    archive = root / data["archives"]["rosary"]["path"]
    archive.write_bytes(archive.read_bytes() + b"\n# changed later\n")
    # The old run returns only its old checked contents, not a mixed new claim.
    assert snapshot.resolve(path) == original
    with pytest.raises(BindingError, match="SHA-256 mismatch"):
        resolve_binding(path, root)


def test_registry_is_not_reloaded_between_resolution_and_source_subject(bound_corpus):
    root, data = bound_corpus
    path = witness(root, data)
    snapshot = RawBindingSnapshot(root)
    data["bindings"]["rosary-introit"]["reading"].clear()
    save(root, data)
    reading = snapshot.resolve(path)
    assert reading is not None and reading.source["binding"]["reading"]
    with pytest.raises(BindingError, match="nonempty"):
        resolve_binding(path, root)


def test_raw_in_boundary_symlink_remains_allowed_and_byte_checked(bound_corpus):
    root, data = bound_corpus
    path = root / data["archives"]["rosary"]["path"]
    destination = path.with_suffix(".retained")
    path.rename(destination)
    path.symlink_to(destination)
    assert resolve_binding(witness(root, data), root) is not None
    destination.write_bytes(destination.read_bytes() + b"changed")
    with pytest.raises(BindingError, match="SHA-256 mismatch"):
        resolve_binding(witness(root, data), root)


def test_raw_registry_cannot_escape_its_boundary_via_symlink(bound_corpus):
    root, data = bound_corpus
    registry = root / REGISTRY
    outside = root / "outside-registry.json"
    registry.rename(outside)
    registry.symlink_to(outside)
    with pytest.raises(BindingError, match="escapes"):
        resolve_binding(witness(root, data), root)


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


@pytest.mark.parametrize(
    "key",
    [
        "rosary-introit",
        "transfiguration-gradual",
        "visitation-introit",
        "pentecost-xxii-postcommunion",
        "pentecost-xiii-postcommunion",
    ],
)
def test_actual_complete_readings_and_attribution(bound_corpus, key):
    root, data = bound_corpus
    path = witness(root, data, key)
    result = resolve_binding(path, root)
    assert result is not None and result.text
    assert check_transcriptions(path.parent) == ([], 1)
    assert attribute.witness_ranges(path.parent.name) == list(result.spans)
    if key == "transfiguration-gradual":
        # One contiguous physical reading retains its actual marker candidates.
        assert attribute.marked_lines(path.parent.name)
    else:
        # A complete expanded text is not one performer occurrence.
        assert attribute.marked_lines(path.parent.name) == []
        category, slug = path.parent.name.split(".", 1)
        doc = json.loads((CORPUS / "texts" / category / f"{slug}.json").read_text())
        assessment = attribute.assess(doc)
        assert assessment.scope == "COMPOSITE_TEXT_ONLY"
        assert not assessment.write_eligible and assessment.proposals == {}
        assert assessment.reasons == ("COMPOSITE_RAW_READING:do.txt",)
    assert check_archives(root) == []


@pytest.mark.parametrize(
    "change", ["missing", "wrong-name", "wrong-target", "wrong-book", "read-control"]
)
@pytest.mark.parametrize("key", ["pentecost-xxii-postcommunion", "pentecost-xiii-postcommunion"])
def test_shared_prayer_reference_is_exact_and_not_sacred_text(bound_corpus, change, key):
    root, data = bound_corpus
    binding = data["bindings"][key]
    # A mutation must begin from a verified complete positive control.
    assert resolve_binding(witness(root, data, key), root) is not None
    if change == "missing":
        binding["references"] = []
    elif change == "wrong-name":
        binding["references"][0]["text"] = (
            "$Per Dominum" if binding["references"][0]["text"] == "$Qui vivis" else "$Qui vivis"
        )
    elif change == "wrong-target":
        binding["references"][0]["target"] = 0
    elif change == "wrong-book":
        data["archives"]["prayers"]["upstream"] = "web/www/horas/Latin/Ordo/Prayers.txt"
        path = witness(root, data, key)
        path.write_text(
            path.read_text().replace(
                "web/www/missa/Latin/Ordo/Prayers.txt",
                "web/www/horas/Latin/Ordo/Prayers.txt",
            )
        )
    else:
        binding["reading"][0]["last"] = binding["references"][0]["line"]
    save(root, data)
    rejected(root, witness(root, data, key))


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
        "segments": [
            {"id": "s01", "type": "verse", "words": [{"id": "w001", "form": "Fílium Dei."}]}
        ],
    }
    assert attribute.span_covers(doc)
    doc["segments"][0]["words"][0]["form"] = "Fílium alienum Dei."
    assert not attribute.span_covers(doc)
    # Punctuation is significant for the witness even when edition alignment folds it.
    path.write_text(path.read_text().replace("(Fílium Dei.)", "Fílium Dei."))
    rejected(root, path)


HISTORICAL_COMMON = "advent-marian-common-21cb2d37"
HISTORICAL_CALLER = "advent-iv-21cb2d37"
HISTORICAL_BINDING = "advent-iv-communio"


@pytest.fixture
def historical_mass_common(tmp_path):
    original = json.loads((CORPUS / REGISTRY).read_text(encoding="utf-8"))
    binding = copy.deepcopy(original["bindings"][HISTORICAL_BINDING])
    assert binding["revision"] == "21cb2d370337ec1fd668e96d035622b4296c32cb"
    archives = {item["archive"] for item in binding["evidence"]}
    assert archives == {HISTORICAL_COMMON, HISTORICAL_CALLER}
    data = {
        "version": original["version"],
        "archives": {key: copy.deepcopy(original["archives"][key]) for key in sorted(archives)},
        "bindings": {HISTORICAL_BINDING: binding},
    }
    assert data["archives"][HISTORICAL_COMMON] == {
        "upstream": "obsolete/missa/Latin/Commune/C10a.txt",
        "revision": "21cb2d370337ec1fd668e96d035622b4296c32cb",
        "path": "witnesses/raw/do-21cb2d37/obsolete/missa/Latin/Commune/C10a.txt",
        "sha256": "ba94e58d62dfe7c7e294bd33f373c3f7a66b8c5b7038108492000b4fe5f7ca0b",
    }
    paths = [item["path"] for item in data["archives"].values()] + [binding["witness"]]
    for name in paths:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CORPUS / name, destination)
    save(tmp_path, data)
    return tmp_path, data, tmp_path / binding["witness"]


def historical_state(root, data):
    names = [REGISTRY, data["bindings"][HISTORICAL_BINDING]["witness"]]
    names += [item["path"] for item in data["archives"].values()]
    return copy.deepcopy(data), {name: (root / name).read_bytes() for name in names}


def restore_historical_state(root, data, saved):
    original, files = saved
    data.clear()
    data.update(copy.deepcopy(original))
    for name, raw in files.items():
        (root / name).write_bytes(raw)
    assert data == original
    assert all((root / name).read_bytes() == raw for name, raw in files.items())
    assert load_registry(root) == original


@pytest.mark.parametrize("key", ("rosary", "annunciation-common"), ids=("missa", "horas"))
def test_existing_raw_upstream_roots_keep_their_actual_records(bound_corpus, key):
    root, data = bound_corpus
    assert load_registry(root) == data
    assert data["archives"][key]["upstream"].startswith("web/www/")


def test_actual_historical_mass_common_and_caller_resolve_together(historical_mass_common):
    root, data, path = historical_mass_common
    assert load_registry(root) == data
    result = resolve_binding(path, root)
    assert result is not None
    assert result.text == (
        "Ecce, Virgo concípiet et páriet fílium: et vocábitur nomen ejus Emmánuel."
    )
    assert result.source["binding"] == data["bindings"][HISTORICAL_BINDING]
    assert result.source["archives"] == data["archives"]
    assert check_transcriptions(path.parent) == ([], 1)


HISTORICAL_BAD_UPSTREAMS = (
    ("other-product", "obsolete/horas/Latin/Commune/C10a.txt"),
    ("other-language", "obsolete/missa/English/Commune/C10a.txt"),
    ("escape-language", "obsolete/missa/Latin/../../English/C10a.txt"),
    ("parent-component", "obsolete/missa/Latin/Commune/../C10a.txt"),
    ("absolute", "/obsolete/missa/Latin/Commune/C10a.txt"),
    ("double-separator", "obsolete/missa/Latin//Commune/C10a.txt"),
    ("dot-component", "obsolete/missa/Latin/./Commune/C10a.txt"),
    ("backslashes", r"obsolete\missa\Latin\Commune\C10a.txt"),
    ("query", "obsolete/missa/Latin/Commune/C10a.txt?raw=1"),
    ("fragment", "obsolete/missa/Latin/Commune/C10a.txt#source"),
    ("suffix", "obsolete/missa/Latin/Commune/C10a.txt/extra"),
    ("whitespace", "obsolete/missa/Latin/Commune/C10a.txt "),
)


@pytest.mark.parametrize(
    "case", HISTORICAL_BAD_UPSTREAMS, ids=[row[0] for row in HISTORICAL_BAD_UPSTREAMS]
)
def test_historical_root_does_not_accept_other_or_noncanonical_paths(historical_mass_common, case):
    root, data, path = historical_mass_common
    healthy = resolve_binding(path, root)
    assert healthy is not None
    saved = historical_state(root, data)
    upstream = case[1]
    try:
        data["archives"][HISTORICAL_COMMON]["upstream"] = upstream
        assert data != saved[0]
        save(root, data)
        with pytest.raises(BindingError) as caught:
            load_registry(root)
        assert str(caught.value) == f"invalid upstream path: {upstream}"
    finally:
        restore_historical_state(root, data, saved)
        assert resolve_binding(path, root) == healthy


HISTORICAL_BAD_LOCAL_PATHS = (
    ("traversal", "witnesses/raw/../../escape.txt"),
    ("absolute", "/private/tmp/unrelated-source.txt"),
    ("noncanonical", "witnesses/raw//historical/C10a.txt"),
    ("backslashes", r"witnesses/raw\historical\C10a.txt"),
)


@pytest.mark.parametrize(
    "case", HISTORICAL_BAD_LOCAL_PATHS, ids=[row[0] for row in HISTORICAL_BAD_LOCAL_PATHS]
)
def test_historical_archive_still_requires_a_confined_local_path(historical_mass_common, case):
    root, data, path = historical_mass_common
    healthy = resolve_binding(path, root)
    assert healthy is not None
    saved = historical_state(root, data)
    try:
        data["archives"][HISTORICAL_COMMON]["path"] = case[1]
        assert data != saved[0]
        save(root, data)
        with pytest.raises(BindingError) as caught:
            load_registry(root)
        assert str(caught.value) == f"invalid confined path: {case[1]}"
    finally:
        restore_historical_state(root, data, saved)
        assert resolve_binding(path, root) == healthy


@pytest.mark.parametrize(
    "change", ("revision", "hash", "bytes", "missing", "reference", "selector", "duplicate")
)
def test_historical_allowance_preserves_identity_hash_and_reference_guards(
    historical_mass_common, change
):
    root, data, path = historical_mass_common
    healthy = resolve_binding(path, root)
    assert healthy is not None
    saved = historical_state(root, data)
    common = data["archives"][HISTORICAL_COMMON]
    raw = root / common["path"]
    binding = data["bindings"][HISTORICAL_BINDING]
    try:
        if change == "revision":
            common["revision"] = "0" * 40
            expected = f"archive {HISTORICAL_COMMON}: revision differs from binding"
        elif change == "hash":
            common["sha256"] = "0" * 64
            expected = f"archive {HISTORICAL_COMMON}: SHA-256 mismatch"
        elif change == "bytes":
            raw.write_bytes(raw.read_bytes() + b"\n# appended outside the selected range\n")
            expected = f"archive {HISTORICAL_COMMON}: SHA-256 mismatch"
        elif change == "missing":
            raw.unlink()
            expected = f"unreadable archive {HISTORICAL_COMMON}: "
        elif change == "reference":
            binding["references"].clear()
            expected = "incomplete source reference coverage"
        elif change == "selector":
            caller = data["archives"][HISTORICAL_CALLER]
            original = root / caller["path"]
            body = original.read_bytes()
            assert body.count(b"@Commune/C10a:Communio") == 1
            changed = body.replace(b"@Commune/C10a:Communio", b"@Commune/C10a:Oratio")
            original.write_bytes(changed)
            caller["sha256"] = hashlib.sha256(changed).hexdigest()
            binding["references"][0]["text"] = "@Commune/C10a:Oratio"
            expected = "reference points to a different source or section"
        else:
            data["archives"]["duplicate-historical"] = copy.deepcopy(common)
            expected = "duplicate archive identity or local path: duplicate-historical"
        assert data != saved[0] or any(
            not (root / name).exists() or (root / name).read_bytes() != value
            for name, value in saved[1].items()
        )
        save(root, data)
        with pytest.raises(BindingError) as caught:
            resolve_binding(path, root)
        if change == "missing":
            assert str(caught.value).startswith(expected)
        else:
            assert str(caught.value) == expected
    finally:
        restore_historical_state(root, data, saved)
        assert resolve_binding(path, root) == healthy
