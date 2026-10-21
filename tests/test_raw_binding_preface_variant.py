"""The Holy Spirit Preface's two-source literal reading conveys no performer."""

import copy
import hashlib
import json
import re
import shutil
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

from build_reader.bibliography import public_text_evidence
from build_reader.bibliography_bindings import (
    transcript_digest,
    validate_bindings,
    witness_subject,
)
from checks import attribute, attribution_alignment, raw_binding, transcription, witness_archive
from checks.collate import collate

ROOT = Path(__file__).resolve().parents[1]
TEXT = "ordinarium.praefatio-spiritus-sancti"
KEY = "holy-spirit-preface-vigil-variant"
WITNESS = f"witness.{TEXT}.do44667ff"
PRIMARY = f"use.{TEXT}.do44667ff"
RULE = f"use.{TEXT}.vigil-variant-rule.do44667ff"
BODY_SHA = "8ee812e51a67546d214fa1d04f0396545803ca22d4aeec478ed16724af408c32"
BINDING_SHA = "55dd3c0597fac9225e063305ebd8167799096e237aac7e475474b0a0cb28e4e0"
SOURCE_HASHES = {
    "prefaces": "cdcc5bb39df5043a85f17a6ebab0483bfad1a360fd31940878c09c67b5d22c80",
    "pentecost-vigil-epistle": "8d1675512b6403ee5dcd795d3c4deed3a9a3a29fffbe085189b1f4a7870a77f9",
}


def digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def files(root):
    return {
        path.relative_to(root): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


@pytest.fixture
def source(tmp_path):
    registry = json.loads((ROOT / raw_binding.REGISTRY).read_text())
    binding = copy.deepcopy(registry["bindings"][KEY])
    assert digest(binding) == BINDING_SHA
    registry["bindings"] = {KEY: binding}
    registry["archives"] = {key: registry["archives"][key] for key in SOURCE_HASHES}
    for key, archive in registry["archives"].items():
        original = ROOT / archive["path"]
        assert hashlib.sha256(original.read_bytes()).hexdigest() == SOURCE_HASHES[key]
        target = tmp_path / archive["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
    shutil.copytree(ROOT / "witnesses" / TEXT, tmp_path / "witnesses" / TEXT)
    path = Path("texts/ordinarium/praefatio-spiritus-sancti.json")
    (tmp_path / path).parent.mkdir(parents=True)
    shutil.copyfile(ROOT / path, tmp_path / path)
    put(tmp_path / raw_binding.REGISTRY, registry)
    graph = json.loads((ROOT / "bibliography/graph.json").read_text())
    graph["witnesses"] = [row for row in graph["witnesses"] if row["text"] == TEXT]
    graph["collations"] = [row for row in graph["collations"] if row["text"] == TEXT]
    uses = {row["use"] for row in graph["witnesses"]} | {RULE}
    graph["uses"] = [row for row in graph["uses"] if row["id"] in uses]
    return {
        "root": tmp_path,
        "registry": registry,
        "graph": graph,
        "doc": json.loads((tmp_path / path).read_text()),
        "witness": tmp_path / binding["witness"],
    }


def witness(source):
    return next(row for row in source["graph"]["witnesses"] if row["id"] == WITNESS)


def use(source, identity):
    return next(row for row in source["graph"]["uses"] if row["id"] == identity)


def resolve(source):
    return raw_binding.resolve_binding(source["witness"], source["root"])


def healthy(source):
    reading = resolve(source)
    assert reading is not None and reading.source["contract"] == "raw-reading-6"
    assert reading.spans == reading.fragments == ()
    assert hashlib.sha256(reading.text.encode()).hexdigest() == BODY_SHA
    assert len(reading.text.split()) == 66 and " hodierna die " in reading.text
    assert reading.source["archives"].keys() == SOURCE_HASHES.keys()
    assert transcription.check_transcriptions(source["witness"].parent) == ([], 1)
    assert witness_archive.check(source["root"]) == []
    assert validate_bindings(source["root"], source["graph"]) == []
    subject = witness_subject(source["root"], witness(source), source["graph"], source["doc"])
    assert subject["raw_resolution"] == reading.source
    assert set(subject["source_uses"]) == {PRIMARY, RULE}
    assert witness(source)["review"] == {"status": "pending"}
    return reading.source, subject


@contextmanager
def restored(source):
    expected = healthy(source)
    before = files(source["root"])
    graph = copy.deepcopy(source["graph"])
    doc = copy.deepcopy(source["doc"])
    registry = copy.deepcopy(source["registry"])
    originals = {
        name: (ROOT / name).read_bytes()
        for name in (
            raw_binding.REGISTRY,
            "bibliography/graph.json",
            f"witnesses/{TEXT}/do.txt",
            f"witnesses/{TEXT}/mr.txt",
            f"witnesses/{TEXT}/apparatus.json",
            "texts/ordinarium/praefatio-spiritus-sancti.json",
        )
    }
    try:
        yield
    finally:
        for relative, raw in before.items():
            (source["root"] / relative).write_bytes(raw)
        source["graph"].clear()
        source["graph"].update(copy.deepcopy(graph))
        source["doc"].clear()
        source["doc"].update(copy.deepcopy(doc))
        source["registry"].clear()
        source["registry"].update(copy.deepcopy(registry))
        assert files(source["root"]) == before
        assert source["graph"] == graph and source["doc"] == doc
        assert source["registry"] == registry
        assert healthy(source) == expected
        assert all((ROOT / name).read_bytes() == raw for name, raw in originals.items())


def save_registry(source):
    put(source["root"] / raw_binding.REGISTRY, source["registry"])


def change_line(source, which, value, *, assert_text=True):
    item = source["registry"]["bindings"][KEY][which]
    archive = source["registry"]["archives"][item["archive"]]
    path = source["root"] / archive["path"]
    lines = path.read_text().splitlines()
    lines[item["line"] - 1] = value
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    archive["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    if assert_text:
        item["text"] = value


def sync_transcript(source, text):
    source["witness"].write_text(text, encoding="utf-8")
    witness(source)["transcription_sha256"] = transcript_digest(text)


def rejected_subject(source, message):
    with pytest.raises(ValueError, match=re.escape(message)):
        witness_subject(source["root"], witness(source), source["graph"], source["doc"])
    expected = f"bibliography witness {WITNESS}: {message}"
    assert expected in validate_bindings(source["root"], source["graph"])


def test_exact_two_sources_form_one_unaccented_text_only_reading(source):
    before = files(source["root"])
    first, subject = healthy(source)
    assert first["resolved_composition"]["variant"]["raw"] == "Prefatio=Spiritu=hodierna die;"
    assert first["resolved_composition"]["template"]["line"] == 49
    assert first["resolved_composition"]["variant"]["line"] == 11
    first["binding"]["template"]["text"] = "Changed."
    first["archives"]["prefaces"]["sha256"] = "0" * 64
    assert healthy(source)[1] == subject and files(source["root"]) == before


RAW_CASES = [
    ("boolean-coordinate", "raw-reading-6 requires the exact Spiritu and Rule coordinates"),
    ("wrong-coordinate", "raw-reading-6 requires the exact Spiritu and Rule coordinates"),
    ("wrong-section", "raw-reading-6 requires the exact Spiritu and Rule coordinates"),
    ("same-archive", "raw-reading-6 requires two distinct archives"),
    ("wrong-upstream", "raw-reading-6 source role has the wrong upstream path"),
    ("wrong-hash", "archive prefaces: SHA-256 mismatch"),
    ("corrupt-rule-bytes", "archive pentecost-vigil-epistle: SHA-256 mismatch"),
    ("changed-line", "raw-reading-6 template differs from its exact source line"),
    ("missing-placeholder", "raw-reading-6 requires one literal * * placeholder in a v. text line"),
    (
        "duplicate-placeholder",
        "raw-reading-6 requires one literal * * placeholder in a v. text line",
    ),
    ("inline-marker", "raw-reading-6 requires one literal * * placeholder in a v. text line"),
    ("wrong-rule-value", "raw-reading-6 variant must be the literal Spiritu rule"),
    ("changed-rule-line", "raw-reading-6 variant differs from its exact source line"),
    ("missing-marker", "raw-binding marker and registered witness identity disagree"),
    ("missing-binding", "raw-binding marker and registered witness identity disagree"),
    ("wrong-header", "witness path declarations differ from bound evidence"),
    ("wrong-revision", "witness revision differs from its raw binding"),
    ("unsupported-revision", "raw-reading-6 requires the pinned Latin revision"),
    ("duplicate-template", "raw-reading-6 requires one complete Spiritu template line"),
    ("duplicate-rule", "raw-reading-6 requires one Prefatio assignment in the Rule section"),
    ("escaping-witness", "invalid confined path: witnesses/../outside.txt"),
    ("duplicate-witness", f"duplicate witness binding: witnesses/{TEXT}/do.txt"),
    (
        "nonobject-binding",
        f"{KEY}: expected fields ['evidence', 'reading', 'references', 'revision', 'witness']",
    ),
]


@pytest.mark.parametrize("mutation,message", RAW_CASES, ids=[row[0] for row in RAW_CASES])
def test_raw_mutations_fail_at_their_owned_diagnostic_and_restore(source, mutation, message):
    with restored(source):
        binding = source["registry"]["bindings"][KEY]
        template = binding["template"]
        if mutation == "boolean-coordinate":
            template["line"] = True
        elif mutation == "wrong-coordinate":
            template["line"] = 48
        elif mutation == "wrong-section":
            template["section"] = "Trinitate"
        elif mutation == "same-archive":
            binding["variant"]["archive"] = template["archive"]
        elif mutation == "wrong-upstream":
            source["registry"]["archives"]["prefaces"]["upstream"] = (
                "web/www/missa/Latin/Ordo/Other.txt"
            )
        elif mutation == "wrong-hash":
            source["registry"]["archives"]["prefaces"]["sha256"] = "0" * 64
        elif mutation == "corrupt-rule-bytes":
            path = (
                source["root"] / source["registry"]["archives"]["pentecost-vigil-epistle"]["path"]
            )
            path.write_bytes(path.read_bytes() + b"\n# changed\n")
        elif mutation == "changed-line":
            change_line(
                source, "template", template["text"].replace("justum", "iustum"), assert_text=False
            )
        elif mutation in {"missing-placeholder", "duplicate-placeholder", "inline-marker"}:
            replacement = {
                "missing-placeholder": "hodierna die",
                "duplicate-placeholder": "* * * *",
                "inline-marker": "* * S. Test.",
            }[mutation]
            change_line(source, "template", template["text"].replace("* *", replacement))
        elif mutation == "wrong-rule-value":
            binding["variant"]["replacement"] = "hodiérna die"
        elif mutation == "changed-rule-line":
            change_line(source, "variant", "Prefatio=Trinitate;", assert_text=False)
        elif mutation == "missing-marker":
            sync_transcript(
                source, source["witness"].read_text().replace(f"# raw-binding: {KEY}\n", "")
            )
        elif mutation == "missing-binding":
            del source["registry"]["bindings"][KEY]
        elif mutation == "wrong-header":
            sync_transcript(
                source,
                source["witness"]
                .read_text()
                .replace("[Spiritu] (lines 49-49)", "[Spiritu] (lines 48-49)"),
            )
        elif mutation == "wrong-revision":
            binding["revision"] = "0" * 40
        elif mutation == "unsupported-revision":
            binding["revision"] = "0" * 40
            for archive in source["registry"]["archives"].values():
                archive["revision"] = "0" * 40
            sync_transcript(
                source,
                source["witness"]
                .read_text()
                .replace("44667ff518b8ff1439780470828b39714f5306a2", "0" * 40),
            )
        elif mutation in {"duplicate-template", "duplicate-rule"}:
            item = binding["template" if mutation == "duplicate-template" else "variant"]
            archive = source["registry"]["archives"][item["archive"]]
            path = source["root"] / archive["path"]
            lines = path.read_text().splitlines()
            lines.insert(item["line"], item["text"])
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            archive["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        elif mutation == "escaping-witness":
            binding["witness"] = "witnesses/../outside.txt"
        elif mutation == "duplicate-witness":
            source["registry"]["bindings"]["duplicate"] = copy.deepcopy(binding)
        elif mutation == "nonobject-binding":
            source["registry"]["bindings"][KEY] = []
        else:
            raise AssertionError(mutation)
        save_registry(source)
        with pytest.raises(raw_binding.BindingError, match=re.escape(message)):
            resolve(source)
        assert any(
            message in item
            for item in transcription.check_transcriptions(source["witness"].parent)[0]
        )
        assert any(message in item for item in witness_archive.check(source["root"]))
        rejected_subject(source, message)


@pytest.mark.parametrize("mutation", ["accent", "omit", "duplicate", "reorder"])
def test_body_changes_do_not_disappear_under_whitespace_normalization(source, mutation):
    with restored(source):
        text = source["witness"].read_text()
        before, after = {
            "accent": (" hodierna die ", " hodiérna die "),
            "omit": (" Qui, ascéndens ", " ascéndens "),
            "duplicate": (" Qui, ascéndens ", " Qui, Qui, ascéndens "),
            "reorder": (" hodierna die ", " die hodierna "),
        }[mutation]
        assert text.count(before) == 1 and before != after
        sync_transcript(source, text.replace(before, after))
        message = "transcription differs from its exact derived preface reading"
        with pytest.raises(raw_binding.BindingError, match=message):
            resolve(source)
        rejected_subject(source, message)


SUBJECT_CASES = [
    ("missing-inventory", "complete explicit source_dependencies declaration required"),
    ("empty-inventory", "raw-reading-6 requires exactly template and variant-rule uses"),
    ("missing-use", "unknown source use"),
    ("wrong-binding", "declared raw binding differs from registered resolution"),
    ("template-hash-for-rule", "raw-reading-6 source-use evidence differs from its contribution"),
    ("rule-hash-for-template", "raw-reading-6 source-use evidence differs from its contribution"),
    ("swapped-hashes", "raw-reading-6 source-use evidence differs from its contribution"),
    ("reading-hash-for-both", "raw-reading-6 source-use evidence differs from its contribution"),
    ("wrong-template-role", "raw-reading-6 source-use role differs from its contribution"),
    ("wrong-rule-role", "raw-reading-6 source-use role differs from its contribution"),
    ("extra-dependency", "raw-reading-6 requires exactly template and variant-rule uses"),
]


@pytest.mark.parametrize("mutation,message", SUBJECT_CASES, ids=[row[0] for row in SUBJECT_CASES])
def test_pending_bibliography_cannot_drop_or_exchange_contributions(source, mutation, message):
    with restored(source):
        row = witness(source)
        if mutation == "missing-inventory":
            del row["source_dependencies"]
        elif mutation == "empty-inventory":
            row["source_dependencies"]["uses"] = []
        elif mutation == "missing-use":
            source["graph"]["uses"] = [
                item for item in source["graph"]["uses"] if item["id"] != RULE
            ]
        elif mutation == "wrong-binding":
            row["source_dependencies"]["raw_binding"] = "another-binding"
        elif mutation == "template-hash-for-rule":
            use(source, RULE)["evidence_sha256"] = SOURCE_HASHES["prefaces"]
        elif mutation == "rule-hash-for-template":
            use(source, PRIMARY)["evidence_sha256"] = SOURCE_HASHES["pentecost-vigil-epistle"]
        elif mutation == "swapped-hashes":
            use(source, PRIMARY)["evidence_sha256"] = SOURCE_HASHES["pentecost-vigil-epistle"]
            use(source, RULE)["evidence_sha256"] = SOURCE_HASHES["prefaces"]
        elif mutation == "reading-hash-for-both":
            value = hashlib.sha256((resolve(source).text + "\n").encode()).hexdigest()
            use(source, PRIMARY)["evidence_sha256"] = value
            use(source, RULE)["evidence_sha256"] = value
        elif mutation == "wrong-template-role":
            use(source, PRIMARY)["role"] = "direct_approved_print"
        elif mutation == "wrong-rule-role":
            use(source, RULE)["role"] = "derived_digital_collation_aid"
        elif mutation == "extra-dependency":
            extra = copy.deepcopy(use(source, RULE))
            extra["id"] += ".extra"
            source["graph"]["uses"].append(extra)
            row["source_dependencies"]["uses"].append(extra["id"])
        else:
            raise AssertionError(mutation)
        rejected_subject(source, message)


def test_text_only_tag_is_checked_before_performer_spans_or_fragments(source, monkeypatch):
    before = files(source["root"])
    original = raw_binding.resolve_binding
    calls = []

    class TextOnly:
        def __init__(self, reading):
            self.source = reading.source

        @property
        def spans(self):
            pytest.fail("text-only reading reached performer spans")

        @property
        def fragments(self):
            pytest.fail("text-only reading reached performer fragments")

    def checked(path, root):
        reading = original(path, root)
        calls.append((path.name, reading.source["contract"] if reading is not None else None))
        return TextOnly(reading) if reading is not None else None

    monkeypatch.setattr(attribute, "CORPUS", source["root"])
    monkeypatch.setattr(attribute, "resolve_binding", checked)
    with pytest.raises(raw_binding.BindingError, match="supports textual identity only"):
        attribute._source_ranges(TEXT)
    assert not attribute.span_covers(source["doc"])
    sources = attribute._actor_sources(TEXT)
    assert sources.scope == "RAW_TEXT_ONLY" and sources.units == ()
    assert attribute.marked_lines(TEXT) == []
    result = attribute.assess(source["doc"])
    assert result.scope == "RAW_TEXT_ONLY" and not result.write_eligible
    assert result.proposals == {}
    monkeypatch.setattr(sys, "argv", ["attribute", "--write"])
    assert attribute.main() == 1
    assert files(source["root"]) == before
    one_verse = copy.deepcopy(source["doc"])
    one_verse["segments"] = [
        segment for segment in one_verse["segments"] if segment["type"] == "verse"
    ]
    monkeypatch.setattr(attribution_alignment, "resolve_binding", checked)
    calls.clear()
    assert attribution_alignment.align_unmarked_reading(one_verse, source["root"]) is None
    assert ("do.txt", "raw-reading-6") in calls
    assert files(source["root"]) == before


def test_accent_apparatus_is_separate_from_mr_parentheses_and_keeps_reviews_pending(source):
    folder = source["witness"].parent
    apparatus = json.loads((folder / "apparatus.json").read_text())
    assert apparatus["summary"] == {
        "entries": 15,
        "classes": ["accent", "orthography", "punctuation"],
    }
    at = [row for row in apparatus["adjudicated"] if row["at"] == "w038"]
    assert len(at) == 2
    assert {(row["class"], tuple(row["witnesses"])) for row in at} == {
        ("accent", ("do",)),
        ("punctuation", ("mr",)),
    }
    errors, warnings, stats = collate(source["doc"], folder)
    assert errors == warnings == [] and stats["words"] == 66
    public = public_text_evidence(source["graph"])
    row = next(row for row in public["texts"] if row["id"] == TEXT)
    assert row["witnesses"] == [] and "collation" not in row
    assert all(
        row["review"] == {"status": "pending"}
        for row in source["graph"]["witnesses"] + source["graph"]["collations"]
    )


def test_per_run_snapshot_and_complete_source_subject_are_detached(source):
    before = healthy(source)
    snapshot = raw_binding.RawBindingSnapshot(source["root"])
    reading = snapshot.resolve(source["witness"])
    reading.source["resolved_composition"]["variant"]["raw"] = "Changed."
    assert snapshot.resolve(source["witness"]).source == before[0]
    with restored(source):
        archive = source["registry"]["archives"]["prefaces"]
        path = source["root"] / archive["path"]
        path.write_bytes(path.read_bytes() + b"\n")
        assert snapshot.resolve(source["witness"]).source == before[0]
        with pytest.raises(raw_binding.BindingError, match="SHA-256 mismatch"):
            resolve(source)
