"""Closed textual source plans do not approve performance or source review."""

import hashlib
import json
import shutil
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import ClassVar

import pytest

from build_reader.bibliography import public_text_evidence
from build_reader.bibliography_bindings import (
    digest,
    transcript_digest,
    validate_bindings,
    witness_subject,
)
from checks import attribute, raw_binding, raw_binding_ordo, transcription, witness_archive

ROOT = Path(__file__).resolve().parents[1]
ORACLE = json.loads((ROOT / "tests/fixtures/main-ordo-source-oracle.json").read_text())["rows"]
BY_TEXT = {row["text"]: row for row in ORACLE}
REVISION = "44667ff518b8ff1439780470828b39714f5306a2"
ARCHIVE_ID = "missa-ordo-44667ff"
ARCHIVE = {
    "upstream": "web/www/missa/Latin/Ordo/Ordo.txt",
    "revision": REVISION,
    "path": "witnesses/raw/missa-44667ff/Ordo/Ordo.txt",
    "sha256": "a7f63e8030325b809f74dd4587c649bf8eb45cdd150fc9a2817fe2a1ed6a42e3",
}


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def files(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def make_source(root, row):
    relative = row["witness"]
    path = root / relative
    path.parent.mkdir(parents=True)
    old = (ROOT / relative).read_text(encoding="utf-8")
    body = "\n".join(line for line in old.splitlines() if not line.startswith("#"))
    name = path.stem
    path.write_text(
        f"# witness: {name}\n# revision: {REVISION}\n# raw-binding: {row['id']}\n"
        f"# path: {row['path']}\n" + body + "\n",
        encoding="utf-8",
    )
    archive = root / ARCHIVE["path"]
    archive.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / ARCHIVE["path"], archive)
    registry = {
        "version": 1,
        "archives": {ARCHIVE_ID: deepcopy(ARCHIVE)},
        "bindings": {
            row["id"]: {
                "witness": relative,
                "revision": REVISION,
                "contract": "raw-reading-10",
                "profile": row["id"],
            }
        },
    }
    put(root / raw_binding.REGISTRY, registry)
    graph = json.loads((ROOT / "bibliography/graph.json").read_text())
    use = deepcopy(
        next(u for u in graph["uses"] if u["id"] == "use.ordinarium.aufer-a-nobis.do44667ff")
    )
    use.update(
        id=f"use.{row['text']}.literal-fixture",
        address={"kind": "text", "text": row["text"]},
        claim="Exact retained literal source assertion, not an independent or ritual review.",
    )
    witness = {
        "id": f"witness.{row['text']}.literal-fixture",
        "text": row["text"],
        "transcription": name,
        "use": use["id"],
        "role": "derived_comparison",
        "coverage": {"kind": "full"},
        "orthography_profile": "exact-pinned-digital",
        "independence_basis": (
            "Derived literal source selection; no independent transmission claim."
        ),
        "transcription_sha256": transcript_digest(path.read_text()),
        "source_dependencies": {"uses": [], "raw_binding": row["id"]},
        "review": {"status": "pending"},
    }
    graph["uses"], graph["witnesses"], graph["collations"] = [use], [witness], []
    relative_core = "texts/" + row["text"].replace(".", "/", 1) + ".json"
    target = root / relative_core
    target.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / relative_core, target)
    return {
        "root": root,
        "path": path,
        "row": row,
        "registry": registry,
        "graph": graph,
        "witness": witness,
        "doc": json.loads(target.read_text()),
    }


def healthy(source):
    reading = raw_binding.resolve_binding(source["path"], source["root"])
    assert reading is not None
    row = source["row"]
    assert_complete_source_payload(reading.source, row)
    assert reading.spans == reading.fragments == ()
    assert len(reading.text.split()) == row["words"]
    assert hashlib.sha256((reading.text + "\n").encode()).hexdigest() == row["body_sha256"]
    assert [p["line"] for p in reading.source["resolved_extraction"]["pieces"]] == row["lines"]
    assert reading.source["archives"] == {ARCHIVE_ID: ARCHIVE}
    assert reading.source["profile"]["witness"] == row["witness"]
    assert reading.source["profile"]["path"] == row["path"]
    assert validate_bindings(source["root"], source["graph"]) == []
    subject = witness_subject(source["root"], source["witness"], source["graph"], source["doc"])
    assert_complete_source_payload(subject["raw_resolution"], row)
    assert subject["raw_resolution"] == reading.source
    assert source["witness"]["review"] == {"status": "pending"}
    return subject


@contextmanager
def restored(source):
    disk = files(source["root"])
    graph, registry, witness = source["graph"], source["registry"], source["witness"]
    saved_graph = deepcopy(graph)
    saved_registry, saved_witness = deepcopy(registry), deepcopy(witness)
    original_path = source["path"]
    expected = healthy(source)
    try:
        yield
    finally:
        for path in source["root"].rglob("*"):
            if path.is_file() and path.relative_to(source["root"]) not in disk:
                path.unlink()
        for relative, raw in disk.items():
            path = source["root"] / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        witness.clear()
        witness.update(saved_witness)
        saved_graph["witnesses"] = [witness]
        graph.clear()
        graph.update(saved_graph)
        registry.clear()
        registry.update(saved_registry)
        source["path"] = original_path
        assert files(source["root"]) == disk
        assert healthy(source) == expected


@pytest.fixture
def source(tmp_path):
    return make_source(tmp_path, BY_TEXT["ordinarium.per-ipsum"])


@pytest.mark.parametrize("row", ORACLE, ids=[r["text"] for r in ORACLE])
def test_each_exact_literal_plan_resolves_without_source_approval(tmp_path, row):
    source = make_source(tmp_path, row)
    healthy(source)
    assert transcription.check_transcriptions(source["path"].parent) == ([], 1)
    assert witness_archive.check(source["root"]) == []
    projected = public_text_evidence(source["graph"])["texts"]
    assert len(projected) == 1 and projected[0]["witnesses"] == []
    assert "collation" not in projected[0]


def test_closed_inventory_keeps_all_physical_repetitions_and_literal_lavabo():
    assert len(ORACLE) == len(BY_TEXT) == 49
    assert sum(r["words"] for r in ORACLE) == 2199
    profiles = raw_binding_ordo.load_profiles()
    assert sum(len(p["reading"]) for p in profiles.values()) == 119
    assert sum(len(s["edits"]) for p in profiles.values() for s in p["reading"]) == 195
    for text, expected in (
        ("ordinarium.kyrie", list(range(76, 85))),
        ("ordinarium.agnus-dei", [299, 300, 301]),
        ("ordinarium.panem-caelestem", [327, 329, 330, 331, 334]),
        ("orationes.cor-iesu", [410, 411]),
        ("ordinarium.lavabo", [183, 22, 23]),
    ):
        assert BY_TEXT[text]["lines"] == expected
    lavabo = profiles[BY_TEXT["ordinarium.lavabo"]["id"]]
    assert lavabo["kind"] == "literal-composite-not-macro-expansion"
    assert any("&Gloria" in b["lines"] for b in lavabo["context"])
    assert "semper:" in lavabo["reading"][-1]["raw"]
    assert BY_TEXT["orationes.pater-noster"]["witness"].endswith("/do-missa.txt")


RAW_FAULTS = (
    "marker",
    "duplicate-marker",
    "record",
    "profile",
    "unknown-profile",
    "profile-type",
    "revision",
    "witness",
    "archive",
    "refreshed-archive",
    "upstream",
    "archive-path",
    "mixed-fields",
    "path",
    "body",
)


@pytest.mark.parametrize("fault", RAW_FAULTS)
def test_actual_identity_archive_and_body_faults_reject_and_same_copy_recovers(source, fault):
    with restored(source):
        original = files(source["root"])
        binding = source["registry"]["bindings"][source["row"]["id"]]
        path, root = source["path"], source["root"]
        if fault == "marker":
            path.write_text(path.read_text().replace(f"# raw-binding: {source['row']['id']}\n", ""))
        elif fault == "duplicate-marker":
            path.write_text(f"# raw-binding: {source['row']['id']}\n" + path.read_text())
        elif fault == "record":
            del source["registry"]["bindings"][source["row"]["id"]]
        elif fault == "profile":
            binding["profile"] = BY_TEXT["ordinarium.kyrie"]["id"]
        elif fault == "unknown-profile":
            binding["profile"] = "main-ordo-unknown"
        elif fault == "profile-type":
            binding["profile"] = True
        elif fault == "revision":
            binding["revision"] = "b5e250b0af79bc3fb4fc3ac631a622d8cb0f2a19"
            path.write_text(path.read_text().replace(REVISION, binding["revision"]))
        elif fault == "witness":
            other = root / BY_TEXT["ordinarium.kyrie"]["witness"]
            other.parent.mkdir(parents=True)
            shutil.copyfile(path, other)
            binding["witness"], source["path"] = str(other.relative_to(root)), other
        elif fault in {"archive", "refreshed-archive"}:
            archive = root / ARCHIVE["path"]
            archive.write_bytes(archive.read_bytes() + b"\n")
            if fault == "refreshed-archive":
                source["registry"]["archives"][ARCHIVE_ID]["sha256"] = hashlib.sha256(
                    archive.read_bytes()
                ).hexdigest()
        elif fault == "upstream":
            source["registry"]["archives"][ARCHIVE_ID]["upstream"] = (
                "web/www/missa/Latin/Ordo/Prayers.txt"
            )
        elif fault == "archive-path":
            source["registry"]["archives"][ARCHIVE_ID]["path"] = "witnesses/raw/../escape.txt"
        elif fault == "mixed-fields":
            binding["reading"] = []
        elif fault == "path":
            path.write_text(
                path.read_text().replace(source["row"]["path"], "Other physical source")
            )
        else:
            path.write_text(path.read_text().replace("omnis honor", "honor omnis"))
        put(root / raw_binding.REGISTRY, source["registry"])
        assert files(root) != original
        with pytest.raises(raw_binding.BindingError):
            raw_binding.resolve_binding(source["path"], root)


GRAPH_FAULTS = (
    "inventory",
    "null-binding",
    "both-missing",
    "role",
    "item",
    "item-sha",
    "item-url",
    "reading-hash",
    "foreign-address",
    "partial-address",
    "extra-use",
    "stale-review",
)


@pytest.mark.parametrize("fault", GRAPH_FAULTS)
def test_pending_source_joins_reject_faults_and_same_copy_recovers(source, fault):
    with restored(source):
        saved = digest(source["graph"])
        witness, graph = source["witness"], source["graph"]
        use = graph["uses"][0]
        item = next(r for r in graph["digital_items"] if r["id"] == use["digital_item"])
        if fault == "inventory":
            del witness["source_dependencies"]
        elif fault == "null-binding":
            witness["source_dependencies"]["raw_binding"] = None
        elif fault == "both-missing":
            path = source["path"]
            path.write_text(path.read_text().replace(f"# raw-binding: {source['row']['id']}\n", ""))
            source["registry"]["bindings"].clear()
            put(source["root"] / raw_binding.REGISTRY, source["registry"])
            witness["transcription_sha256"] = transcript_digest(path.read_text())
        elif fault == "role":
            use["role"] = "direct_approved_print"
        elif fault == "item":
            use["digital_item"] = "item.divinum-officium-horae.44667ff.prayers"
        elif fault == "item-sha":
            item["sha256"] = "0" * 64
        elif fault == "item-url":
            item["record_url"] = item["record_url"].replace("Ordo/Ordo.txt", "Ordo/Prayers.txt")
        elif fault == "reading-hash":
            use["evidence_sha256"] = source["row"]["body_sha256"]
        elif fault == "foreign-address":
            use["address"]["text"] = "ordinarium.kyrie"
        elif fault == "partial-address":
            use["address"] = {"kind": "word", "text": witness["text"], "word": "w001"}
        elif fault == "extra-use":
            extra = deepcopy(use)
            extra["id"] += ".extra"
            graph["uses"].append(extra)
            witness["source_dependencies"]["uses"] = [extra["id"]]
        else:
            witness["review"] = {"status": "reviewed", "sha256": "0" * 64}
        assert digest(graph) != saved
        assert validate_bindings(source["root"], graph)
        if fault != "stale-review":
            with pytest.raises(ValueError):
                witness_subject(source["root"], witness, graph, source["doc"])


TABLE_FAULTS = (
    "extra-key",
    "duplicate-profile",
    "boolean-offset",
    "overlap",
    "unknown-kind",
    "empty-reason",
    "missing-context",
    "reorder",
    "sacred-word",
    "cross-kind",
    "slot",
    "wait",
    "boolean-line",
    "heading-key",
    "context-overlap",
    "alternative",
    "lavabo-macro",
    "missing-Gloria-line",
    "repetition",
    "profile-id",
    "boolean-version",
)


def damaged_table(fault):
    data = json.loads(raw_binding_ordo.PROFILE_PATH.read_text())
    by_text = {p["text"]: p for p in data["profiles"]}
    if fault == "extra-key":
        data["profiles"][0]["option"] = True
    elif fault == "duplicate-profile":
        data["profiles"].append(deepcopy(data["profiles"][0]))
    elif fault in {"boolean-offset", "overlap", "unknown-kind", "empty-reason", "sacred-word"}:
        edit = data["profiles"][0]["reading"][0]["edits"][0]
        if fault == "boolean-offset":
            edit["start"] = False
        elif fault == "overlap":
            data["profiles"][0]["reading"][0]["edits"].append(deepcopy(edit))
        elif fault == "unknown-kind":
            edit["kind"] = "any-parenthesis"
        elif fault == "empty-reason":
            edit["reason"] = " "
        else:
            edit.update(start=3, end=6, text="Cor")
    elif fault == "missing-context":
        data["profiles"][0]["context"].clear()
    elif fault == "reorder":
        by_text["ordinarium.kyrie"]["reading"].reverse()
    elif fault == "cross-kind":
        edit = by_text["ordinarium.adiutorium"]["reading"][0]["edits"][-1]
        edit["replacement"] = ""
    elif fault == "slot":
        edit = by_text["ordinarium.te-igitur"]["reading"][0]["edits"][-1]
        edit["text"] = "Deus"
    elif fault == "wait":
        edit = by_text["ordinarium.memento-defunctorum"]["reading"][0]["edits"][2]
        edit["start"] -= 1
        edit["text"] = ".wait10"
    elif fault == "boolean-line":
        data["profiles"][0]["reading"][0]["line"] = False
    elif fault == "heading-key":
        data["profiles"][0]["headings"][0]["format"] = "invented"
    elif fault == "context-overlap":
        data["profiles"][0]["context"].append(deepcopy(data["profiles"][0]["context"][0]))
    elif fault == "alternative":
        by_text["ordinarium.orate-fratres"]["reading"][1]["edits"][-1]["replacement"] = "meis"
    elif fault == "lavabo-macro":
        by_text["ordinarium.lavabo"]["reading"].sort(key=lambda p: p["line"])
    elif fault == "missing-Gloria-line":
        by_text["ordinarium.lavabo"]["reading"].pop()
    elif fault == "repetition":
        by_text["ordinarium.kyrie"]["reading"].pop()
    elif fault == "profile-id":
        data["profiles"][0]["id"] = "main-ordo-unknown"
    elif fault == "boolean-version":
        data["version"] = True
    else:
        raise AssertionError(fault)
    return data


@pytest.mark.parametrize("fault", TABLE_FAULTS)
def test_pure_typed_profile_validation_rejects_and_same_copy_recovers(fault):
    good = json.loads(raw_binding_ordo.PROFILE_PATH.read_text())
    saved = deepcopy(good)
    assert len(raw_binding_ordo.validate_profiles(good)) == 49
    bad = damaged_table(fault)
    assert digest(bad) != digest(saved)
    try:
        with pytest.raises(raw_binding.BindingError):
            raw_binding_ordo.validate_profiles(bad)
    finally:
        bad.clear()
        bad.update(deepcopy(saved))
        assert bad == saved
        assert digest(bad) == digest(saved)
        assert len(raw_binding_ordo.validate_profiles(bad)) == 49


@pytest.mark.parametrize("fault", ["coordinated-table", "duplicate-JSON"])
def test_actual_table_loader_rejects_before_trusting_changed_data(
    source, tmp_path, monkeypatch, fault
):
    bad = tmp_path / "changed-profiles.json"
    if fault == "coordinated-table":
        data = json.loads(raw_binding_ordo.PROFILE_PATH.read_text())
        profile = next(p for p in data["profiles"] if p["id"] == source["row"]["id"])
        profile["reading"][0]["edits"][0]["replacement"] = "Dropped "
        profile["word_count"] += 1
        body = " ".join(
            " ".join(
                line for line in source["path"].read_text().splitlines() if not line.startswith("#")
            ).split()
        )
        changed_body = body.replace("Per Ipsum", "Dropped Per Ipsum", 1)
        profile["body_sha256"] = hashlib.sha256((changed_body + "\n").encode()).hexdigest()
        raw = json.dumps(data, ensure_ascii=False).encode()
    else:
        raw = raw_binding_ordo.PROFILE_PATH.read_bytes().replace(
            b'"version": 1,', b'"version": 1, "version": 1,', 1
        )
    assert hashlib.sha256(raw).hexdigest() != raw_binding_ordo.PROFILE_SHA256
    bad.write_bytes(raw)
    with restored(source), monkeypatch.context() as scoped:
        if fault == "coordinated-table":
            path = source["path"]
            original = path.read_text()
            changed = original.replace("Per Ipsum", "Dropped Per Ipsum", 1)
            assert changed != original
            path.write_text(changed)
            source["witness"]["transcription_sha256"] = transcript_digest(changed)
        scoped.setattr(raw_binding_ordo, "PROFILE_PATH", bad)
        with pytest.raises(raw_binding.BindingError, match="closed profile table SHA-256 mismatch"):
            raw_binding.resolve_binding(source["path"], source["root"])


def test_text_only_consumers_never_access_performer_ranges(source, monkeypatch):
    monkeypatch.setattr(attribute, "CORPUS", source["root"])
    message = "closed Ordo evidence supports textual identity only"
    with pytest.raises(raw_binding.BindingError, match=message):
        attribute.witness_ranges(source["row"]["text"])
    assert attribute._actor_sources(source["row"]["text"]).scope == "RAW_TEXT_ONLY"

    class TextOnly:
        source: ClassVar[dict[str, str]] = {"contract": "raw-reading-10"}

        @property
        def spans(self):
            pytest.fail("text-only plan reached performer spans")

        @property
        def fragments(self):
            pytest.fail("text-only plan reached performer fragments")

    monkeypatch.setattr(attribute, "resolve_binding", lambda path, root: TextOnly())
    with pytest.raises(raw_binding.BindingError, match=message):
        attribute._source_ranges(source["row"]["text"])
    assert attribute._actor_sources(source["row"]["text"]).scope == "RAW_TEXT_ONLY"


def test_returned_payload_mutation_cannot_change_next_resolution(source):
    expected = healthy(source)
    reading = raw_binding.resolve_binding(source["path"], source["root"])
    reading.source["profile"]["reading"].clear()
    reading.source["resolved_extraction"]["pieces"].clear()
    assert healthy(source) == expected


def test_actual_registry_duplicate_key_rejects_and_same_bytes_recover(source):
    with restored(source):
        path = source["root"] / raw_binding.REGISTRY
        saved = path.read_bytes()
        bad = saved.replace(b'"version": 1,', b'"version": 1, "version": 1,', 1)
        assert bad != saved
        path.write_bytes(bad)
        with pytest.raises(raw_binding.BindingError, match="duplicate JSON key"):
            raw_binding.resolve_binding(source["path"], source["root"])


def add_actual_pater_raw1(source, filename):
    """Synthetic test-only records retain the complete real bracket-source Pater."""
    root, registry = source["root"], source["registry"]
    relative = "witnesses/raw/do-44667ff/missa/Latin/Ordo/Prayers.txt"
    original = (ROOT / relative).read_bytes()
    expected = "7bf86beb01c170212fa07438de45b16b321f117013321400d65c2229c6624d9b"
    assert hashlib.sha256(original).hexdigest() == expected
    lines = original.decode("utf-8").splitlines()
    assert lines[0] == "[Pater noster]" and lines[1].startswith("v. Pater noster,")
    body = lines[1][3:]
    assert "cotidiánum" in body and body[-5:] == "Amen."
    archive = root / relative
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_bytes(original)
    key = "actor-control-pater"
    upstream = "web/www/missa/Latin/Ordo/Prayers.txt"
    registry["archives"][key] = {
        "upstream": upstream,
        "revision": REVISION,
        "path": relative,
        "sha256": expected,
    }
    witness = root / "witnesses/orationes.pater-noster" / filename
    witness.parent.mkdir(parents=True, exist_ok=True)
    witness.write_text(
        f"# witness: {witness.stem}\n# revision: {REVISION}\n# raw-binding: {key}\n"
        f"# path: {upstream} [Pater noster] (lines 2-2)\n{body}\n",
        encoding="utf-8",
    )
    registry["bindings"][key] = {
        "witness": witness.relative_to(root).as_posix(),
        "revision": REVISION,
        "evidence": [
            {
                "archive": key,
                "first": 2,
                "last": 2,
                "section": "Pater noster",
                "section_line": 1,
            }
        ],
        "references": [],
        "reading": [{"archive": key, "first": 2, "last": 2}],
    }
    put(root / raw_binding.REGISTRY, registry)
    reading = raw_binding.resolve_binding(witness, root)
    assert reading is not None and reading.source["contract"] == "raw-reading-1"
    assert reading.text == body
    assert reading.spans == ((archive, 2, 2),)
    assert len(reading.fragments) == 1 and reading.fragments[0].raw == lines[1]
    return witness, reading


def test_text_only_plan_does_not_quarantine_another_texts_actual_raw1(source, monkeypatch):
    monkeypatch.setattr(attribute, "CORPUS", source["root"])
    with restored(source):
        witness, expected = add_actual_pater_raw1(source, "actor-control.txt")
        assert source["row"]["text"] == "ordinarium.per-ipsum"
        assert attribute._actor_sources(source["row"]["text"]).scope == "RAW_TEXT_ONLY"
        other = attribute._actor_sources("orationes.pater-noster")
        assert other.scope == "SCOPED" and len(other.units) == 1 and other.reasons == ()
        assert raw_binding.resolve_binding(witness, source["root"]) == expected
        healthy(source)


@pytest.mark.parametrize("order", ["before", "after"])
def test_same_text_actual_raw1_and_text_only_plan_stay_quarantined(tmp_path, monkeypatch, order):
    source = make_source(tmp_path, BY_TEXT["orationes.pater-noster"])
    monkeypatch.setattr(attribute, "CORPUS", source["root"])
    with restored(source):
        filename = "a-control.txt" if order == "before" else "z-control.txt"
        witness, expected = add_actual_pater_raw1(source, filename)
        assert (filename < source["path"].name) == (order == "before")
        path, registry = source["path"], source["registry"]
        original = path.read_bytes()
        identity = source["row"]["id"]
        saved = registry["bindings"].pop(identity)
        path.unlink()
        put(source["root"] / raw_binding.REGISTRY, registry)
        try:
            assert not path.exists() and identity not in registry["bindings"]
            alone = attribute._actor_sources("orationes.pater-noster")
            assert alone.scope == "SCOPED" and len(alone.units) == 1 and alone.reasons == ()
            assert raw_binding.resolve_binding(witness, source["root"]) == expected
        finally:
            path.write_bytes(original)
            registry["bindings"][identity] = saved
            put(source["root"] / raw_binding.REGISTRY, registry)
            assert path.read_bytes() == original and registry["bindings"][identity] == saved
        mixed = attribute._actor_sources("orationes.pater-noster")
        assert mixed.scope == "RAW_TEXT_ONLY" and mixed.units == ()
        assert mixed.reasons == ("TEXT_ONLY_CONTRACT:do-missa.txt: raw-reading-10",)
        with pytest.raises(raw_binding.BindingError, match="supports textual identity only"):
            attribute._source_ranges("orationes.pater-noster")
        assert raw_binding.resolve_binding(witness, source["root"]) == expected
        healthy(source)


def assert_complete_source_payload(payload, row):
    assert digest(payload) == digest(row["expected_source"]), "complete raw10 source payload"


@pytest.mark.parametrize(
    "fault", ("missing-context", "missing-headings", "missing-raw", "missing-edits")
)
def test_complete_returned_payload_rejects_missing_evidence_and_restores(source, fault):
    expected = healthy(source)
    disk = files(source["root"])
    table = raw_binding_ordo.PROFILE_PATH.read_bytes()
    reading = raw_binding.resolve_binding(source["path"], source["root"])
    assert reading is not None
    payload = reading.source
    saved = deepcopy(payload)
    assert_complete_source_payload(payload, source["row"])
    try:
        if fault == "missing-context":
            del payload["profile"]["context"]
        elif fault == "missing-headings":
            del payload["profile"]["headings"]
        elif fault == "missing-raw":
            del payload["resolved_extraction"]["pieces"][0]["raw"]
        else:
            del payload["resolved_extraction"]["pieces"][0]["edits"]
        assert payload is reading.source
        assert digest(payload) != digest(saved)
        assert payload["resolved_extraction"]["text"] == saved["resolved_extraction"]["text"]
        with pytest.raises(AssertionError, match="complete raw10 source payload"):
            assert_complete_source_payload(payload, source["row"])
    finally:
        payload.clear()
        payload.update(deepcopy(saved))
        assert payload is reading.source and payload == saved
        assert_complete_source_payload(payload, source["row"])
    assert raw_binding_ordo.PROFILE_PATH.read_bytes() == table
    assert files(source["root"]) == disk
    assert healthy(source) == expected
