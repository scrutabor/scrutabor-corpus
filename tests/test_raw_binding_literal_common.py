"""The Lateran Postcommunion's literal Common reading binds three sources and no performer.

The feast file selects the Common C8 (Rank and Rule ``ex C8``) and has no Postcommunio;
the Common supplies the body and its ``$Per Dominum`` cue; the Mass Ordo prayer file
supplies the conclusion and Amen. The witness keeps the literal source readings.
"""

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
    collation_subject,
    transcript_digest,
    validate_bindings,
    witness_subject,
)
from checks import (
    attribute,
    attribution_alignment,
    raw_binding,
    raw_binding_common,
    transcription,
    witness_archive,
)
from checks.collate import collate

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.dedicatio-archibasilicae-sanctissimi-salvatoris-postcommunio"
ASCENSION = "proprium.ascensio-domini-postcommunio"
KEY = "do-proprium-dedicatio-archibasilicae-sanctissimi-salvatoris-postcommunio"
WITNESS = f"witness.{TEXT}.do44667ff"
MR = f"witness.{TEXT}.mr1962"
PRIMARY = f"use.{TEXT}.do44667ff"
SELECTION = f"use.{TEXT}.feast-selection.do44667ff"
CONCLUSION = f"use.{TEXT}.mass-conclusion.do44667ff"
COLLATION = f"collation.{TEXT}.mr1962-do44667ff"
CORE = Path("texts/proprium/dedicatio-archibasilicae-sanctissimi-salvatoris-postcommunio.json")
REVISION = "44667ff518b8ff1439780470828b39714f5306a2"
SOURCE_HASHES = {
    "common-c8": "4259d9ddd8669a6a6dcb8de2ac7bfd918e3e39a4e8fe8a5bc04b28afdb97c5c8",
    "do-sancti-11-09": "a80d47d0b5f190830ce15f3926bdc7925a5f04467d44835b461915207d4ba8f9",
    "prayers": "7bf86beb01c170212fa07438de45b16b321f117013321400d65c2229c6624d9b",
}
LITERAL = (
    "Deus, qui de vivis et electis lapídibus ætérnum majestáti tuæ prǽparas habitáculum: "
    "auxiliáre pópulo tuo supplicánti; ut, quod Ecclésiæ tuæ corporálibus próficit spátiis, "
    "spirituálibus amplificétur augméntis. Per Dóminum nostrum Jesum Christum, Fílium tuum: "
    "qui tecum vivit et regnat in unitáte Spíritus Sancti Deus, per ómnia sǽcula sæculórum. Amen."
)
# Each literal source reading and the normalized reading the former transcript carried.
NORMALIZED = [
    ("electis", "eléctis"),
    ("majestáti", "maiestáti"),
    ("Jesum", "Iesum"),
    ("qui tecum", "Qui tecum"),
    ("Sancti Deus", "Sancti, Deus"),
]
PATH = (
    "selection, context only: web/www/missa/Latin/Sancti/11-09.txt [Rank] (lines 1-2), "
    "[Rule] (lines 4-5), no [Postcommunio]; "
    "body: web/www/horas/Latin/Commune/C8.txt [Postcommunio] (lines 640-642); "
    "conclusion: web/www/missa/Latin/Ordo/Prayers.txt [Per Dominum] (lines 95-97)"
)
FIELDS = "['body', 'conclusion', 'contract', 'profile', 'revision', 'selection', 'witness']"


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def files(root):
    return {p.relative_to(root): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


@pytest.fixture
def source(tmp_path):
    registry = json.loads((ROOT / raw_binding.REGISTRY).read_text())
    binding = copy.deepcopy(registry["bindings"][KEY])
    registry["bindings"] = {KEY: binding}
    registry["archives"] = {key: registry["archives"][key] for key in SOURCE_HASHES}
    for key, archive in registry["archives"].items():
        original = ROOT / archive["path"]
        assert hashlib.sha256(original.read_bytes()).hexdigest() == SOURCE_HASHES[key]
        target = tmp_path / archive["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
    shutil.copytree(ROOT / "witnesses" / TEXT, tmp_path / "witnesses" / TEXT)
    (tmp_path / CORE).parent.mkdir(parents=True)
    shutil.copyfile(ROOT / CORE, tmp_path / CORE)
    put(tmp_path / raw_binding.REGISTRY, registry)
    graph = json.loads((ROOT / "bibliography/graph.json").read_text())
    graph["witnesses"] = [row for row in graph["witnesses"] if row["text"] == TEXT]
    graph["collations"] = [row for row in graph["collations"] if row["text"] == TEXT]
    graph["uses"] = [row for row in graph["uses"] if row["address"].get("text") == TEXT]
    return {
        "root": tmp_path,
        "registry": registry,
        "graph": graph,
        "doc": json.loads((tmp_path / CORE).read_text()),
        "witness": tmp_path / binding["witness"],
    }


def witness(source, identity=WITNESS):
    return next(row for row in source["graph"]["witnesses"] if row["id"] == identity)


def use(source, identity):
    return next(row for row in source["graph"]["uses"] if row["id"] == identity)


def resolve(source):
    return raw_binding.resolve_binding(source["witness"], source["root"])


def healthy(source):
    reading = resolve(source)
    assert reading is not None and reading.source["contract"] == "raw-reading-8"
    assert reading.spans == reading.fragments == ()
    assert reading.text == LITERAL and len(reading.text.split()) == 48
    composition = reading.source["resolved_literal_composition"]
    assert composition["text"] == LITERAL
    assert [(p["archive"], p["line"], p["remove_prefix"]) for p in composition["pieces"]] == [
        ("common-c8", 641, ""),
        ("prayers", 96, "r. "),
        ("prayers", 97, "R. "),
    ]
    assert [len(p["text"].split()) for p in composition["pieces"]] == [26, 21, 1]
    assert [(c["archive"], c["line"]) for c in composition["context"]] == [
        ("do-sancti-11-09", 1),
        ("do-sancti-11-09", 2),
        ("do-sancti-11-09", 4),
        ("do-sancti-11-09", 5),
        ("common-c8", 640),
        ("common-c8", 642),
        ("prayers", 95),
    ]
    assert {k: v["sha256"] for k, v in reading.source["archives"].items()} == SOURCE_HASHES
    assert reading.source["profile"] == raw_binding_common.profile()
    assert reading.source["profile"]["path"] == PATH
    assert transcription.check_transcriptions(source["witness"].parent) == ([], 1)
    assert witness_archive.check(source["root"]) == []
    assert validate_bindings(source["root"], source["graph"]) == []
    subject = witness_subject(source["root"], witness(source), source["graph"], source["doc"])
    assert subject["raw_resolution"] == reading.source
    assert set(subject["source_uses"]) == {PRIMARY, SELECTION, CONCLUSION}
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
            str(CORE),
            *(registry["archives"][key]["path"] for key in SOURCE_HASHES),
        )
    }
    try:
        yield
    finally:
        for path in set(files(source["root"])) - set(before):
            (source["root"] / path).unlink()
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


def sync_transcript(source, text):
    source["witness"].write_text(text, encoding="utf-8")
    witness(source)["transcription_sha256"] = transcript_digest(text)


def archive_path(source, key):
    return source["root"] / source["registry"]["archives"][key]["path"]


def rewrite_archive(source, key, change):
    """Change one archive's bytes and register its new digest honestly."""
    path = archive_path(source, key)
    lines = path.read_text(encoding="utf-8").splitlines()
    change(lines)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    source["registry"]["archives"][key]["sha256"] = digest
    return digest


def rejected_everywhere(source, message):
    with pytest.raises(raw_binding.BindingError, match=re.escape(message)):
        resolve(source)
    assert any(
        message in item for item in transcription.check_transcriptions(source["witness"].parent)[0]
    )
    assert any(message in item for item in witness_archive.check(source["root"]))
    rejected_subject(source, message)


def rejected_subject(source, message):
    with pytest.raises(ValueError, match=re.escape(message)):
        witness_subject(source["root"], witness(source), source["graph"], source["doc"])
    expected = f"bibliography witness {WITNESS}: {message}"
    assert expected in validate_bindings(source["root"], source["graph"])


def test_exact_three_sources_form_one_literal_text_only_reading(source):
    before = files(source["root"])
    first, subject = healthy(source)
    assert first["binding_id"] == KEY and first["registry_version"] == 1
    assert first["transcription_sha256"] == transcript_digest(source["witness"].read_text())
    assert set(first) == {
        "contract",
        "registry_version",
        "binding_id",
        "transcription_sha256",
        "binding",
        "archives",
        "profile",
        "resolved_literal_composition",
    }
    # Returned payloads never share mutable state with the run snapshot.
    first["binding"]["body"]["text"]["text"] = "Changed."
    first["archives"]["common-c8"]["sha256"] = "0" * 64
    first["resolved_literal_composition"]["pieces"].clear()
    assert healthy(source)[1] == subject and files(source["root"]) == before
    snapshot = raw_binding.RawBindingSnapshot(source["root"])
    reading = snapshot.resolve(source["witness"])
    reading.source["profile"]["roles"]["body"]["sha256"] = "0" * 64
    assert snapshot.resolve(source["witness"]).source == healthy(source)[0]


def test_reading_keeps_every_literal_source_difference(source):
    body = "\n".join(
        line for line in source["witness"].read_text().splitlines() if not line.startswith("#")
    )
    assert body == LITERAL
    for literal, normalized in NORMALIZED:
        assert LITERAL.count(literal) == 1 and normalized not in LITERAL
    lines = archive_path(source, "common-c8").read_text().splitlines()
    assert lines[639:644] == [
        "[Postcommunio]",
        LITERAL.split(" Per Dóminum")[0],
        "$Per Dominum",
        "",
        "[Postcommunio 2 loco]",
    ]
    prayers = archive_path(source, "prayers").read_text().splitlines()
    assert prayers[94:97] == [
        "[Per Dominum]",
        "r. " + LITERAL.split("augméntis. ")[1].removesuffix(" Amen."),
        "R. Amen.",
    ]
    feast = archive_path(source, "do-sancti-11-09").read_text().splitlines()
    assert feast[1].endswith(";;ex C8") and feast[4] == "ex C8;"
    assert not any(line.startswith("[Postcommunio") for line in feast)


RAW_CASES = [
    ("unknown-profile", "raw-reading-8 profile is not supported"),
    ("office-profile", "raw-reading-8 profile is not supported"),
    ("nonstring-profile", "raw-reading-8 profile must be a string"),
    ("extra-option", f"{KEY}: expected fields {FIELDS}"),
    (
        "extra-record-field",
        "raw-reading-8 body: expected fields ['archive', 'cue', 'heading', 'text']",
    ),
    (
        "missing-absence-proof",
        "raw-reading-8 selection: expected fields "
        "['absent_heading', 'archive', 'rank', 'rank_heading', 'rule', 'rule_heading']",
    ),
    (
        "wrong-absence-literal",
        "raw-reading-8 selection must prove the feast has no own [Postcommunio]",
    ),
    ("boolean-coordinate", "raw-reading-8 records require integer lines and strings"),
    ("swapped-roles", "raw-reading-8 selection archive has the wrong upstream path"),
    ("same-archive", "raw-reading-8 requires three distinct archives"),
    ("unknown-archive", "unknown archive: missa-commune-c8"),
    ("forged-missa-c8-path", "raw-reading-8 body archive has the wrong upstream path"),
    ("office-conclusion", "raw-reading-8 conclusion archive has the wrong upstream path"),
    ("wrong-archive-revision", "archive common-c8: revision differs from binding"),
    ("wrong-hash", "archive common-c8: SHA-256 mismatch"),
    ("corrupt-common-bytes", "archive common-c8: SHA-256 mismatch"),
    ("refreshed-common", "raw-reading-8 body requires the exact pinned archive object"),
    ("refreshed-feast", "raw-reading-8 selection requires the exact pinned archive object"),
    ("refreshed-prayers", "raw-reading-8 conclusion requires the exact pinned archive object"),
    ("forged-rank", "raw-reading-8 selection must bind the literal ex C8 Rank and Rule lines"),
    ("forged-rule", "raw-reading-8 selection must bind the literal ex C8 Rank and Rule lines"),
    ("changed-rank-line", "raw-reading-8 selection rank differs from its exact physical line"),
    ("wrong-rank-coordinate", "raw-reading-8 selection rank requires its exact pinned coordinate"),
    ("wrong-heading-literal", "raw-reading-8 selection rule_heading must be the literal [Rule]"),
    ("two-loco-heading", "raw-reading-8 body heading requires its exact pinned coordinate"),
    ("two-loco-body", "raw-reading-8 body text requires its exact pinned coordinate"),
    ("nonadjacent-cue", "raw-reading-8 body cue requires its exact pinned coordinate"),
    ("altered-cue", "raw-reading-8 body cue must be the literal $Per Dominum"),
    (
        "eiusdem-destination",
        "raw-reading-8 conclusion heading requires its exact pinned coordinate",
    ),
    (
        "missing-piece",
        "raw-reading-8 conclusion: expected fields ['amen', 'archive', 'formula', 'heading']",
    ),
    ("duplicate-piece", "raw-reading-8 conclusion amen requires its exact pinned coordinate"),
    ("reordered-pieces", "raw-reading-8 conclusion formula requires its exact pinned coordinate"),
    ("missing-prefix", "raw-reading-8 conclusion requires the literal r. and R. prefixes"),
    ("wrong-prefix", "raw-reading-8 conclusion requires the literal r. and R. prefixes"),
    ("record-electis", "raw-reading-8 body text differs from its exact physical line"),
    ("record-majestati", "raw-reading-8 body text differs from its exact physical line"),
    ("record-jesum", "raw-reading-8 conclusion formula differs from its exact physical line"),
    ("record-qui", "raw-reading-8 conclusion formula differs from its exact physical line"),
    ("record-sancti", "raw-reading-8 conclusion formula differs from its exact physical line"),
    ("missing-marker", "raw-binding marker and registered witness identity disagree"),
    ("missing-binding", "raw-binding marker and registered witness identity disagree"),
    ("wrong-header", "witness path declarations differ from bound evidence"),
    ("context-unmarked-header", "witness path declarations differ from bound evidence"),
    ("wrong-revision", "witness revision differs from its raw binding"),
    ("unsupported-revision", "raw-reading-8 requires the pinned Latin revision"),
    ("duplicate-witness", f"duplicate witness binding: witnesses/{TEXT}/do.txt"),
    ("unsupported-contract", "unsupported per-binding contract"),
    (
        "nonobject-binding",
        f"{KEY}: expected fields ['evidence', 'reading', 'references', 'revision', 'witness']",
    ),
]
RECORD_NORMALIZATIONS = {
    "record-electis": ("body", "text", "electis", "eléctis"),
    "record-majestati": ("body", "text", "majestáti", "maiestáti"),
    "record-jesum": ("conclusion", "formula", "Jesum", "Iesum"),
    "record-qui": ("conclusion", "formula", "qui tecum", "Qui tecum"),
    "record-sancti": ("conclusion", "formula", "Sancti Deus", "Sancti, Deus"),
}


@pytest.mark.parametrize("mutation,message", RAW_CASES, ids=[row[0] for row in RAW_CASES])
def test_raw_mutations_fail_at_their_owned_diagnostic_and_restore(source, mutation, message):
    with restored(source):
        binding = source["registry"]["bindings"][KEY]
        archives = source["registry"]["archives"]
        selection, body, conclusion = binding["selection"], binding["body"], binding["conclusion"]
        if mutation == "unknown-profile":
            binding["profile"] = "roman1960-latin-missa-c9-postcommunio"
        elif mutation == "office-profile":
            binding["profile"] = "roman1960-latin-horas-c8-postcommunio"
        elif mutation == "nonstring-profile":
            binding["profile"] = [binding["profile"]]
        elif mutation == "extra-option":
            binding["namespace"] = "missa"
        elif mutation == "extra-record-field":
            body["section"] = "Postcommunio"
        elif mutation == "missing-absence-proof":
            del selection["absent_heading"]
        elif mutation == "wrong-absence-literal":
            selection["absent_heading"] = "[Postcommunio 2 loco]"
        elif mutation == "boolean-coordinate":
            body["text"]["line"] = True
        elif mutation == "swapped-roles":
            selection["archive"], body["archive"] = body["archive"], selection["archive"]
        elif mutation == "same-archive":
            conclusion["archive"] = body["archive"]
        elif mutation == "unknown-archive":
            body["archive"] = "missa-commune-c8"
        elif mutation == "forged-missa-c8-path":
            archives["common-c8"]["upstream"] = "web/www/missa/Latin/Commune/C8.txt"
        elif mutation == "office-conclusion":
            archives["prayers"]["upstream"] = "web/www/horas/Latin/Psalterium/Common/Prayers.txt"
        elif mutation == "wrong-archive-revision":
            archives["common-c8"]["revision"] = "1" * 40
        elif mutation == "wrong-hash":
            archives["common-c8"]["sha256"] = "0" * 64
        elif mutation == "corrupt-common-bytes":
            path = archive_path(source, "common-c8")
            path.write_bytes(path.read_bytes() + b"\n")
        elif mutation in {"refreshed-common", "refreshed-feast", "refreshed-prayers"}:
            key = {
                "refreshed-common": "common-c8",
                "refreshed-feast": "do-sancti-11-09",
                "refreshed-prayers": "prayers",
            }[mutation]
            rewrite_archive(source, key, lambda lines: lines.append("# changed"))
        elif mutation == "forged-rank":
            selection["rank"]["text"] = selection["rank"]["text"].replace("ex C8", "ex C10")
        elif mutation == "forged-rule":
            selection["rule"]["text"] = "ex C10;"
        elif mutation == "changed-rank-line":
            selection["rank"]["text"] = "In Dedicatione;;Duplex;;5.5;;ex C8"
        elif mutation == "wrong-rank-coordinate":
            selection["rank"]["line"] = 3
        elif mutation == "wrong-heading-literal":
            selection["rule_heading"]["text"] = "[Rank]"
        elif mutation == "two-loco-heading":
            body["heading"] = {"line": 644, "text": "[Postcommunio 2 loco]"}
        elif mutation == "two-loco-body":
            lines = archive_path(source, "common-c8").read_text().splitlines()
            body["text"] = {"line": 646, "text": lines[645]}
        elif mutation == "nonadjacent-cue":
            body["cue"]["line"] = 647
        elif mutation == "altered-cue":
            body["cue"]["text"] = "$Per Dominum eiusdem"
        elif mutation == "eiusdem-destination":
            conclusion["heading"] = {"line": 99, "text": "[Per Dominum eiusdem]"}
        elif mutation == "missing-piece":
            del conclusion["amen"]
        elif mutation == "duplicate-piece":
            conclusion["amen"] = copy.deepcopy(conclusion["formula"])
        elif mutation == "reordered-pieces":
            conclusion["formula"], conclusion["amen"] = conclusion["amen"], conclusion["formula"]
        elif mutation == "missing-prefix":
            conclusion["formula"]["prefix"] = ""
        elif mutation == "wrong-prefix":
            conclusion["amen"]["prefix"] = "r. "
        elif mutation in RECORD_NORMALIZATIONS:
            role, name, literal, normalized = RECORD_NORMALIZATIONS[mutation]
            record = binding[role][name]
            assert record["text"].count(literal) == 1
            record["text"] = record["text"].replace(literal, normalized)
        elif mutation == "missing-marker":
            sync_transcript(
                source, source["witness"].read_text().replace(f"# raw-binding: {KEY}\n", "")
            )
        elif mutation == "missing-binding":
            del source["registry"]["bindings"][KEY]
        elif mutation == "wrong-header":
            sync_transcript(
                source,
                source["witness"].read_text().replace("(lines 640-642)", "(lines 644-647)"),
            )
        elif mutation == "context-unmarked-header":
            sync_transcript(
                source,
                source["witness"].read_text().replace("selection, context only: ", "selection: "),
            )
        elif mutation == "wrong-revision":
            binding["revision"] = "0" * 40
        elif mutation == "unsupported-revision":
            binding["revision"] = "0" * 40
            for archive in archives.values():
                archive["revision"] = "0" * 40
            sync_transcript(source, source["witness"].read_text().replace(REVISION, "0" * 40))
        elif mutation == "duplicate-witness":
            source["registry"]["bindings"]["duplicate"] = copy.deepcopy(binding)
        elif mutation == "unsupported-contract":
            binding["contract"] = "raw-reading-unsupported"
        elif mutation == "nonobject-binding":
            source["registry"]["bindings"][KEY] = []
        else:
            raise AssertionError(mutation)
        save_registry(source)
        rejected_everywhere(source, message)


STRUCTURE_CASES = [
    (
        "feast-own-postcommunio",
        "do-sancti-11-09",
        "raw-reading-8 selection must prove the feast has no own [Postcommunio]",
    ),
    (
        "feast-conditional-postcommunio",
        "do-sancti-11-09",
        "raw-reading-8 selection must prove the feast has no own [Postcommunio]",
    ),
    (
        "rank-continuation",
        "do-sancti-11-09",
        "raw-reading-8 selection must bind the complete Rank and Rule lines",
    ),
    (
        "second-common-postcommunio",
        "common-c8",
        "raw-reading-8 body requires the unique selected [Postcommunio] section",
    ),
    (
        "text-after-cue",
        "common-c8",
        "raw-reading-8 body must bind the complete section through its cue",
    ),
    ("framed-body", "common-c8", "raw-reading-8 body line must be unframed text"),
    (
        "text-after-amen",
        "prayers",
        "raw-reading-8 conclusion must bind the complete [Per Dominum] section",
    ),
    (
        "other-conclusion-prefix",
        "prayers",
        "raw-reading-8 conclusion requires the literal r. and R. prefixes",
    ),
]


@pytest.mark.parametrize(
    "mutation,key,message", STRUCTURE_CASES, ids=[row[0] for row in STRUCTURE_CASES]
)
def test_structure_guards_hold_even_under_a_repinned_archive(
    source, monkeypatch, mutation, key, message
):
    """The archive pin is not the only guard: each structural rule fails on its own."""
    with restored(source):
        binding = source["registry"]["bindings"][KEY]

        def change(lines):
            if mutation == "feast-own-postcommunio":
                lines.extend(["", "[Postcommunio]", "Deus, qui de vivis.", "$Per Dominum"])
            elif mutation == "feast-conditional-postcommunio":
                lines.extend(["", "[Postcommunio] (rubrica 1960)", "@Commune/C8"])
            elif mutation == "rank-continuation":
                assert lines[2] == ""
                lines[2] = "Alterum verbum."
            elif mutation == "second-common-postcommunio":
                lines.extend(["", "[Postcommunio]", "Deus, qui de vivis.", "$Per Dominum"])
            elif mutation == "text-after-cue":
                assert lines[642] == ""
                lines[642] = "Alterum verbum."
            elif mutation == "framed-body":
                lines[640] = "v. " + lines[640]
                binding["body"]["text"]["text"] = lines[640]
            elif mutation == "text-after-amen":
                assert lines[97] == ""
                lines[97] = "Alterum verbum."
            elif mutation == "other-conclusion-prefix":
                lines[95] = "v. " + lines[95][3:]
                binding["conclusion"]["formula"]["text"] = lines[95]
            else:
                raise AssertionError(mutation)

        digest = rewrite_archive(source, key, change)
        save_registry(source)
        role = {"do-sancti-11-09": "selection", "common-c8": "body", "prayers": "conclusion"}[key]
        with monkeypatch.context() as patch:
            upstream, _, records = raw_binding_common.ROLES[role]
            patch.setitem(raw_binding_common.ROLES, role, (upstream, digest, records))
            rejected_everywhere(source, message)


BODY_CASES = [
    *[
        (f"normalized-{name}", literal, normalized)
        for name, (literal, normalized) in zip(
            ("electis", "majestati", "jesum", "qui", "sancti"), NORMALIZED, strict=True
        )
    ],
    ("omitted-amen", " Amen.", ""),
    ("omitted-conclusion", " Per Dóminum nostrum", " Per Dóminum"),
    ("duplicated-clause", " auxiliáre pópulo", " auxiliáre auxiliáre pópulo"),
    ("reordered-words", "de vivis", "vivis de"),
    ("retained-prefix", " Per Dóminum", " r. Per Dóminum"),
]


@pytest.mark.parametrize("mutation,before,after", BODY_CASES, ids=[row[0] for row in BODY_CASES])
def test_body_changes_do_not_disappear_under_whitespace_normalization(
    source, mutation, before, after
):
    with restored(source):
        # The header names these readings too; only the transcribed body changes.
        text = source["witness"].read_text()
        body = text.splitlines()[-1]
        assert body == LITERAL and text.endswith("\n" + body + "\n")
        assert body.count(before) == 1 and before != after
        sync_transcript(source, text.removesuffix(body + "\n") + body.replace(before, after) + "\n")
        message = "transcription differs from its exact literal composition"
        with pytest.raises(raw_binding.BindingError, match=message):
            resolve(source)
        rejected_subject(source, message)


SUBJECT_CASES = [
    ("missing-inventory", "complete explicit source_dependencies declaration required"),
    ("empty-inventory", "raw-reading-8 requires exactly body, selection and conclusion uses"),
    ("omitted-selection", "raw-reading-8 requires exactly body, selection and conclusion uses"),
    ("omitted-conclusion", "raw-reading-8 requires exactly body, selection and conclusion uses"),
    ("extra-dependency", "raw-reading-8 requires exactly body, selection and conclusion uses"),
    ("missing-use", "unknown source use"),
    ("wrong-binding", "declared raw binding differs from registered resolution"),
    ("null-binding", "source requires its explicit exact raw binding"),
    ("feast-hash-for-body", "raw-reading-8 source-use evidence differs from its contribution"),
    ("body-hash-for-selection", "raw-reading-8 source-use evidence differs from its contribution"),
    ("swapped-hashes", "raw-reading-8 source-use evidence differs from its contribution"),
    ("reading-hash-for-body", "raw-reading-8 source-use evidence differs from its contribution"),
    ("approved-print-primary", "raw-reading-8 source-use role differs from its contribution"),
    ("selection-as-text", "raw-reading-8 source-use role differs from its contribution"),
    ("conclusion-as-rubric", "raw-reading-8 source-use role differs from its contribution"),
    ("other-revision-item", "digital item revision or kind differs from raw binding"),
]


@pytest.mark.parametrize("mutation,message", SUBJECT_CASES, ids=[row[0] for row in SUBJECT_CASES])
def test_pending_bibliography_cannot_drop_or_exchange_contributions(source, mutation, message):
    with restored(source):
        row = witness(source)
        dependencies = row["source_dependencies"]
        if mutation == "missing-inventory":
            # The pending identity path may not return early for this contract.
            del row["source_dependencies"]
        elif mutation == "empty-inventory":
            dependencies["uses"] = []
        elif mutation == "omitted-selection":
            dependencies["uses"] = [CONCLUSION]
        elif mutation == "omitted-conclusion":
            dependencies["uses"] = [SELECTION]
        elif mutation == "extra-dependency":
            extra = copy.deepcopy(use(source, SELECTION))
            extra["id"] = f"use.{TEXT}.feast-selection-extra.do44667ff"
            source["graph"]["uses"].append(extra)
            dependencies["uses"] = sorted([*dependencies["uses"], extra["id"]])
        elif mutation == "missing-use":
            source["graph"]["uses"] = [u for u in source["graph"]["uses"] if u["id"] != SELECTION]
        elif mutation == "wrong-binding":
            dependencies["raw_binding"] = "another-binding"
        elif mutation == "null-binding":
            dependencies["raw_binding"] = None
        elif mutation == "feast-hash-for-body":
            use(source, PRIMARY)["evidence_sha256"] = SOURCE_HASHES["do-sancti-11-09"]
        elif mutation == "body-hash-for-selection":
            use(source, SELECTION)["evidence_sha256"] = SOURCE_HASHES["common-c8"]
        elif mutation == "swapped-hashes":
            use(source, SELECTION)["evidence_sha256"] = SOURCE_HASHES["prayers"]
            use(source, CONCLUSION)["evidence_sha256"] = SOURCE_HASHES["do-sancti-11-09"]
        elif mutation == "reading-hash-for-body":
            value = hashlib.sha256((LITERAL + "\n").encode()).hexdigest()
            use(source, PRIMARY)["evidence_sha256"] = value
        elif mutation == "approved-print-primary":
            use(source, PRIMARY)["role"] = "direct_approved_print"
        elif mutation == "selection-as-text":
            use(source, SELECTION)["role"] = "derived_digital_collation_aid"
        elif mutation == "conclusion-as-rubric":
            use(source, CONCLUSION)["role"] = "rubric_control"
        elif mutation == "other-revision-item":
            item = next(
                i
                for i in source["graph"]["digital_items"]
                if i["id"] == use(source, PRIMARY)["digital_item"]
            )
            item["revision"] = "0" * 40
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
    message = "literal source-context evidence supports textual identity only"
    with pytest.raises(raw_binding.BindingError, match=message):
        attribute.witness_ranges(TEXT)
    monkeypatch.setattr(attribute, "resolve_binding", checked)
    with pytest.raises(raw_binding.BindingError, match=message):
        attribute._source_ranges(TEXT)
    with pytest.raises(raw_binding.BindingError, match=message):
        attribute.witness_ranges(TEXT)
    assert not attribute.span_covers(source["doc"])
    sources = attribute._actor_sources(TEXT)
    assert sources.scope == "RAW_TEXT_ONLY" and sources.units == ()
    assert sources.reasons == ("TEXT_ONLY_CONTRACT:do.txt: raw-reading-8",)
    assert attribute.marked_lines(TEXT) == []
    result = attribute.assess(source["doc"])
    assert result.scope == "RAW_TEXT_ONLY" and not result.write_eligible
    assert result.proposals == {}
    monkeypatch.setattr(sys, "argv", ["attribute", "--write"])
    assert attribute.main() == 1
    assert files(source["root"]) == before
    # Source-specific variant alignment stays contract-1 only, even for one complete verse.
    one_verse = copy.deepcopy(source["doc"])
    words = [word for segment in one_verse["segments"] for word in segment.get("words", [])]
    one_verse["segments"] = [{**one_verse["segments"][0], "words": words}]
    assert collate(one_verse, source["witness"].parent)[0] == []
    monkeypatch.setattr(attribution_alignment, "resolve_binding", checked)
    calls.clear()
    assert attribution_alignment.align_unmarked_reading(one_verse, source["root"]) is None
    assert ("do.txt", "raw-reading-8") in calls
    assert files(source["root"]) == before


def test_six_literal_differences_are_ruled_and_reviews_stay_pending(source):
    folder = source["witness"].parent
    apparatus = json.loads((folder / "apparatus.json").read_text())
    assert apparatus["summary"] == {
        "entries": 6,
        "classes": ["accent", "capitalization", "orthography", "punctuation"],
    }
    assert [
        (row["at"], row["ours"], row["witnesses"], row["class"]) for row in apparatus["adjudicated"]
    ] == [
        ("w006", "eléctis", {"do": "electis"}, "accent"),
        ("w009", "maiestáti", {"do": "majestáti"}, "orthography"),
        ("w030", "Iesum", {"do": "Jesum"}, "orthography"),
        ("w031", "Christum", {"do": "Christum,"}, "punctuation"),
        ("w034", "Qui", {"do": "qui"}, "capitalization"),
        ("w042", "Sancti,", {"do": "Sancti"}, "punctuation"),
    ]
    assert all(row["ruling"].strip() for row in apparatus["adjudicated"])
    errors, warnings, stats = collate(source["doc"], folder)
    assert errors == warnings == [] and stats["words"] == 48
    assert (stats["orthographic"], stats["variants_adjudicated"]) == (2, 4)
    subjects = {
        row["id"]: witness_subject(source["root"], row, source["graph"], source["doc"])
        for row in source["graph"]["witnesses"]
    }
    collation = next(row for row in source["graph"]["collations"] if row["id"] == COLLATION)
    subject = collation_subject(source["root"], collation, source["doc"], subjects)
    assert subject["contract"] == "collation-review-2"
    public = public_text_evidence(source["graph"])
    row = next(row for row in public["texts"] if row["id"] == TEXT)
    assert row["witnesses"] == [] and "collation" not in row
    assert all(
        row["review"] == {"status": "pending"}
        for row in source["graph"]["witnesses"] + source["graph"]["collations"]
    )


def real_graph():
    return json.loads((ROOT / "bibliography/graph.json").read_text())


def one(rows, identity):
    (row,) = [row for row in rows if row["id"] == identity]
    return row


def test_real_records_bind_the_three_contributions_and_keep_history():
    graph = real_graph()
    reading = raw_binding.resolve_binding(ROOT / "witnesses" / TEXT / "do.txt", ROOT)
    assert reading is not None and reading.text == LITERAL
    row = one(graph["witnesses"], WITNESS)
    assert row["source_dependencies"] == {"uses": [SELECTION, CONCLUSION], "raw_binding": KEY}
    assert row["orthography_profile"] == "exact-pinned-source-resolved"
    assert row["transcription_sha256"] == transcript_digest(
        (ROOT / "witnesses" / TEXT / "do.txt").read_text()
    )
    expected = {
        PRIMARY: ("derived_digital_collation_aid", "common-c8", "RETAIN_WITH_CORRECTION"),
        SELECTION: ("rubric_control", "do-sancti-11-09", "RETAIN"),
        CONCLUSION: ("derived_digital_collation_aid", "prayers", "RETAIN"),
    }
    for identity, (role, archive, decision) in expected.items():
        record = one(graph["uses"], identity)
        assert (record["role"], record["evidence_sha256"], record["decision"]) == (
            role,
            SOURCE_HASHES[archive],
            decision,
        )
        assert record["verified_on"] == "2026-10-22"
        assert record["address"] == {"kind": "text", "text": TEXT}
    assert "Common C8" in one(graph["uses"], PRIMARY)["claim"]
    assert "not a normative printed rubric" in one(graph["uses"], SELECTION)["claim"]
    doc = json.loads((ROOT / CORE).read_text())
    subject = witness_subject(ROOT, row, graph, doc)
    assert subject["raw_resolution"]["contract"] == "raw-reading-8"
    headers = [
        line
        for line in (ROOT / "witnesses" / TEXT / "do.txt").read_text().splitlines()
        if line.startswith("#")
    ]
    assert "# fetched: 2026-08-31" in headers
    assert f"# path: {PATH}" in headers and f"# raw-binding: {KEY}" in headers
    assert any(
        line.startswith("# correction: 2026-10-07 this line formerly claimed") for line in headers
    )
    assert (
        "# orthography: exact source spelling, accents, capitalization, and punctuation" in headers
    )
    for record in [*graph["witnesses"], *graph["collations"]]:
        if record["text"] == TEXT:
            assert record["review"] == {"status": "pending"}
    entries = {
        entry["id"]
        for group in one(public_text_evidence(graph)["texts"], TEXT)["source_groups"]
        for entry in group["entries"]
    }
    assert {PRIMARY, SELECTION, CONCLUSION} <= entries


PAGES = {
    "formula": "b511f3aa4016b387d2995b5089e15aa62593c04118052ef48dcc09352fcf769c",
    "variants": "db99d725287dbdb233ff9c22c94cd027ec6b5105f2f64817ec828778805ff132",
    "prefix": "38c3d082c3cf4e7f82f87cf9f87595e62e3765cb625c1305005f1435cc985774",
}


@pytest.mark.parametrize("text_id", [ASCENSION, TEXT])
def test_real_mr_conclusion_supplements_are_exact_and_pending(text_id):
    graph = real_graph()
    mr = one(graph["witnesses"], f"witness.{text_id}.mr1962")
    expected = sorted(f"use.{text_id}.conclusion-{suffix}.mr1962" for suffix in PAGES)
    assert mr["source_dependencies"] == {"uses": expected, "raw_binding": None}
    assert mr["orthography_profile"] == "proper-body-and-declared-shared-conclusion"
    assert mr["transcription_sha256"] == transcript_digest(
        (ROOT / "witnesses" / text_id / "mr.txt").read_text()
    )
    for suffix, digest in PAGES.items():
        record = one(graph["uses"], f"use.{text_id}.conclusion-{suffix}.mr1962")
        assert record["evidence_sha256"] == digest
        assert record["edition"] == "edition.missale-romanum.1962-typica"
    assert one(graph["uses"], f"use.{text_id}.mr1962")["role"] == "direct_approved_print"
    category, slug = text_id.split(".", 1)
    doc = json.loads((ROOT / "texts" / category / f"{slug}.json").read_text())
    subject = witness_subject(ROOT, mr, graph, doc)
    assert subject["contract"] == "witness-review-2" and subject["raw_resolution"] is None
    assert set(subject["source_uses"]) == {mr["use"], *expected}
    for record in [*graph["witnesses"], *graph["collations"]]:
        if record["text"] == text_id:
            assert record["review"] == {"status": "pending"}
    if text_id == ASCENSION:
        do = one(graph["witnesses"], f"witness.{text_id}.do44667ff")
        assert (
            witness_subject(ROOT, do, graph, doc)["raw_resolution"]["contract"] == "raw-reading-1"
        )
